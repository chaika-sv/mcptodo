import logging
import sqlite3
from mcp.server.fastmcp import FastMCP
from setup import setup_database
import dateparser
import re

# Init server
mcp = FastMCP("TaskManager")

# ===== LOGGING SETTINGS =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ===== DATABASE HELPERS =====
def get_db_connection():
    """Создает подключение к БД с row_factory"""
    conn = sqlite3.connect('tasks.db')
    conn.row_factory = sqlite3.Row
    return conn


def parse_due_date(raw_due: str | None) -> str | None:
    """
    Преобразует текстовую дату в ISO-формат.

    Функция пытается распознать дату и время из строки.
    Если во входной строке указано время суток ("утром", "вечером", "night" и т.п.),
    оно подставляется автоматически. Если время явно не указано, возвращается только дата.

    Args:
        raw_due (str | None): текстовое представление даты и/или времени.

    Returns:
        str | None: ISO-строка даты/времени, например "2025-09-18" или "2025-09-18T18:00:00".
                    Возвращает None, если строку не удалось распознать.
    """
    if not raw_due:
        return None

    text = raw_due.strip().lower()

    # словарь для времён суток
    time_overrides = {
        "утром": (9, 0),
        "днём": (13, 0),
        "днем": (13, 0),  # без ё
        "вечером": (18, 0),
        "ночью": (23, 0),
        "morning": (9, 0),
        "afternoon": (13, 0),
        "evening": (18, 0),
        "night": (23, 0),
    }

    # Ищем в строке ключевые слова для времени суток, сохраняем их в переменную matched_time и чистим строку от слова, чтобы парсер мог распознать дату
    matched_time = None
    for word, (h, m) in time_overrides.items():
        if word in text:
            matched_time = (h, m)
            text = text.replace(word, "").strip()  # убираем слово, чтобы parser понял дату
            break

    # Распознаём то, что осталось от даты (например, слова типа "завтра", "5 сентября")
    parsed = dateparser.parse(
        text,
        languages=["ru", "en"],
        settings={
            "PREFER_DATES_FROM": "future",
            "PREFER_DAY_OF_MONTH": "current",
            "RETURN_AS_TIMEZONE_AWARE": False,
        }
    )

    if not parsed:
        logger.warning(f"Unrecognized due_date: {raw_due}")
        return None

    # Если нашли время суток, подставляем его вручную
    if matched_time:
        parsed = parsed.replace(hour=matched_time[0], minute=matched_time[1])
        return parsed.isoformat()

    # Проверяем, было ли указано во входе время явно
    time_pattern = r"\b\d{1,2}[:.]\d{2}\b"
    if re.search(time_pattern, raw_due):
        return parsed.isoformat()

    # Иначе возвращаем только дату
    return parsed.date().isoformat()




@mcp.tool()
def add_task(
    title: str,
    description: str | None = None,
    due_date: str | None = None,
    priority_id: int | None = None,
    category_id: int | None = None,
    status_id: int | None = None,
    started_at: str | None = None,
    completed_at: str | None = None
) -> dict:
    """
    Добавляет новую задачу в базу данных.

    Функция создаёт запись в таблице `tasks` с указанными полями, фильтруя пустые значения.
    Поле `due_date` автоматически парсится через `parse_due_date`.
    После добавления возвращается полная информация о созданной задаче.

    Args:
        title (str): заголовок задачи (обязательное поле, не может быть пустым)
        description (str | None, optional): описание задачи
        due_date (str | None, optional): срок выполнения в виде строки
        priority_id (int | None, optional): идентификатор приоритета
        category_id (int | None, optional): идентификатор категории
        status_id (int | None, optional): идентификатор статуса
        started_at (str | None, optional): дата начала задачи
        completed_at (str | None, optional): дата завершения задачи

    Returns:
        dict: результат операции:
            - {"status": "success", "data": {...}} — если задача успешно добавлена, содержит все поля новой задачи
            - {"status": "error", "error": str} — если произошла ошибка (например, пустой заголовок или проблема с БД)
    """

    try:
        if not title or not title.strip():
            logger.warning("Attempted to add task with empty title")
            return {"status": "error", "error": "Task title cannot be empty"}

        # обязательные и опциональные поля
        data: dict[str, object] = {
            "title": title.strip(),
            "description": description,
            "due_date": parse_due_date(due_date),
            "priority_id": priority_id,
            "category_id": category_id,
            "status_id": status_id,
            "started_at": started_at,
            "completed_at": completed_at,
        }

        # фильтруем None
        data = {k: v for k, v in data.items() if v is not None}

        fields = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        values = list(data.values())

        sql = f"INSERT INTO tasks ({fields}) VALUES ({placeholders})"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            task_id = cursor.lastrowid

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            task = dict(row)

            logger.info(f"Added task: {task['id']} - {task['title']}")
            return {"status": "success", "data": task}

    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return {"status": "error", "error": str(e)}


@mcp.tool()
def list_tasks():
    """
    Получает список всех задач из базы данных.

    Функция выполняет запрос к таблице `tasks`, сортируя задачи по дате создания.
    Возвращает список задач в виде словарей вместе с количеством найденных записей.

    Returns:
        dict: результат операции с полями:
            - "status": "success" или "error"
            - "tasks": список задач (каждая задача — словарь), присутствует только при успешном выполнении
            - "count": количество найденных задач, присутствует только при успешном выполнении
            - "message": текст ошибки, присутствует только при неудаче
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY created_at")
            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]

            logger.info(f"Retrieving all tasks: {len(tasks)} found")
            return {"status": "success", "tasks": tasks, "count": len(tasks)}

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return {"status": "error", "message": "Failed to retrieve tasks"}



@mcp.tool()
def search_tasks(query: str):
    """
    Выполняет поиск задач по тексту в заголовках и описаниях.

    Функция ищет совпадения в таблице `tasks`, игнорируя регистр,
    и возвращает список задач с расширенной информацией о приоритете, категории и статусе.

    Args:
        query (str): строка поиска. Не может быть пустой.

    Returns:
        dict: результат операции с полями:
            - "status": "success" или "error"
            - "tasks": список найденных задач (каждая задача — словарь с полями title, description, priority, category, status и др.)
            - "count": количество найденных задач
            - "query": использованная строка поиска
            - "message": текст ошибки, присутствует только при неудаче
    """
    try:
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return {"status": "error", "message": "Search query cannot be empty"}

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Поиск по title и description (case-insensitive)
            search_pattern = f"%{query.strip()}%"
            cursor.execute("""
                SELECT t.*, p.name as priority_name, c.name as category_name, s.name as status_name
                FROM tasks t
                LEFT JOIN priorities p ON t.priority_id = p.id
                LEFT JOIN categories c ON t.category_id = c.id  
                LEFT JOIN statuses s ON t.status_id = s.id
                WHERE LOWER(t.title) LIKE LOWER(?) OR LOWER(t.description) LIKE LOWER(?)
                ORDER BY t.id
            """, (search_pattern, search_pattern))

            rows = cursor.fetchall()
            tasks = []
            for row in rows:
                task = dict(row)
                # Добавляем читаемые названия
                task['priority'] = task['priority_name']
                task['category'] = task['category_name']
                task['status'] = task['status_name']
                tasks.append(task)

            logger.info(f"Search query '{query}': found {len(tasks)} tasks")
            return {
                "status": "success",
                "tasks": tasks,
                "count": len(tasks),
                "query": query.strip()
            }

    except Exception as e:
        logger.error(f"Error searching tasks: {e}")
        return {"status": "error", "message": "Failed to search tasks"}


@mcp.tool()
def edit_task(search_query: str, title: str = None, description: str = None,
              priority: str = None, category: str = None, status: str = None, due_date: str = None):
    """
    Редактирует существующую задачу, найденную по строке поиска.

    Функция ищет задачи, соответствующие `search_query`.
    - Если задача не найдена — возвращает ошибку.
    - Если найдено несколько задач — возвращает список и предлагает уточнить запрос.
    - Если найдена одна задача — обновляет указанные поля и возвращает обновлённую запись.

    Args:
        search_query (str): строка для поиска задачи (обязательное поле)
        title (str, optional): новый заголовок задачи
        description (str, optional): новое описание задачи
        priority (str, optional): новое название приоритета
        category (str, optional): новое название категории
        status (str, optional): новое название статуса
        due_date (str, optional): новая дата выполнения (строка)

    Returns:
        dict: результат операции с возможными полями:
            - "status": "success", "error" или "multiple_found"
            - "message": текстовое описание результата или ошибки
            - "task": обновлённая задача (при успешном обновлении одной задачи)
            - "tasks": список задач (если найдено несколько совпадений)
            - "count": количество найденных задач (если несколько совпадений)
    """
    try:
        if not search_query or not search_query.strip():
            return {"status": "error", "message": "Search query cannot be empty"}

        # Сначала ищем задачи
        search_result = search_tasks(search_query.strip())
        if search_result["status"] != "success":
            return search_result

        found_tasks = search_result["tasks"]

        # Если задач не найдено
        if len(found_tasks) == 0:
            return {
                "status": "error",
                "message": f"No tasks found matching '{search_query}'"
            }

        # Если найдено несколько задач - просим уточнить
        if len(found_tasks) > 1:
            return {
                "status": "multiple_found",
                "message": f"Found {len(found_tasks)} tasks matching '{search_query}'. Please be more specific.",
                "tasks": found_tasks,
                "count": len(found_tasks)
            }

        # Найдена одна задача - редактируем
        task_to_edit = found_tasks[0]
        task_id = task_to_edit['id']

        with get_db_connection() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            # Подготавливаем обновления
            if title is not None:
                updates.append("title = ?")
                params.append(title.strip())

            if description is not None:
                updates.append("description = ?")
                params.append(description.strip() if description.strip() else None)

            # Для priority, category, status нужно найти ID по имени
            if priority is not None:
                cursor.execute("SELECT id FROM priorities WHERE LOWER(name) = LOWER(?)", (priority.strip(),))
                priority_row = cursor.fetchone()
                if priority_row:
                    updates.append("priority_id = ?")
                    params.append(priority_row[0])
                else:
                    return {"status": "error", "message": f"Priority '{priority}' not found"}

            if category is not None:
                cursor.execute("SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (category.strip(),))
                category_row = cursor.fetchone()
                if category_row:
                    updates.append("category_id = ?")
                    params.append(category_row[0])
                else:
                    return {"status": "error", "message": f"Category '{category}' not found"}

            if status is not None:
                cursor.execute("SELECT id FROM statuses WHERE LOWER(name) = LOWER(?)", (status.strip(),))
                status_row = cursor.fetchone()
                if status_row:
                    updates.append("status_id = ?")
                    params.append(status_row[0])
                else:
                    return {"status": "error", "message": f"Status '{status}' not found"}

            if due_date is not None:
                updates.append("due_date = ?")
                params.append(due_date.strip() if due_date.strip() else None)

            # Если нет изменений
            if not updates:
                return {"status": "error", "message": "No fields to update provided"}

            # Выполняем обновление
            params.append(task_id)
            update_query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(update_query, params)

            # Получаем обновленную задачу
            cursor.execute("""
                SELECT t.*, p.name as priority_name, c.name as category_name, s.name as status_name
                FROM tasks t
                LEFT JOIN priorities p ON t.priority_id = p.id
                LEFT JOIN categories c ON t.category_id = c.id  
                LEFT JOIN statuses s ON t.status_id = s.id
                WHERE t.id = ?
            """, (task_id,))

            row = cursor.fetchone()
            updated_task = dict(row)
            updated_task['priority'] = updated_task['priority_name']
            updated_task['category'] = updated_task['category_name']
            updated_task['status'] = updated_task['status_name']

            logger.info(f"Updated task {task_id}: '{updated_task['title']}'")
            return {
                "status": "success",
                "message": f"Task '{updated_task['title']}' updated successfully",
                "task": updated_task
            }

    except Exception as e:
        logger.error(f"Error editing task: {e}")
        return {"status": "error", "message": "Failed to edit task"}



@mcp.tool()
def delete_task(id: int):
    """
    Удаляет задачу по её ID.

    Функция проверяет корректность переданного ID, существование задачи и выполняет её удаление из таблицы `tasks`.

    Args:
        id (int): идентификатор задачи, которую нужно удалить. Должен быть положительным числом.

    Returns:
        dict: результат операции с полями:
            - "status": "success" или "error"
            - "message": текст сообщения о результате или ошибке
            - "id": ID удалённой задачи (только при успешном удалении)
    """
    try:
        # Валидация ID
        if not isinstance(id, int) or id <= 0:
            logger.warning(f"Invalid task ID provided: {id}")
            return {"status": "error", "message": "Invalid task ID"}

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Проверяем существование задачи
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (id,))
            if cursor.fetchone()[0] == 0:
                logger.warning(f"Task with ID {id} not found")
                return {"status": "error", "message": f"Task with ID {id} not found"}

            # Удаляем задачу
            cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))

            logger.info(f"Deleted task with ID: {id}")
            return {"status": "success", "message": f"Task {id} deleted", "id": id}

    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return {"status": "error", "message": "Failed to delete task"}


def main():
    try:
        logger.info("Starting MCP TaskManager server...")

        # Инициализируем БД
        if not setup_database():
            logger.error("Failed to initialize database")
            return

        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise


if __name__ == "__main__":
    main()