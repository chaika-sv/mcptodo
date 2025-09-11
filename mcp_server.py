import logging
import sqlite3
from mcp.server.fastmcp import FastMCP
from setup import setup_database

# Init server
mcp = FastMCP("TaskManager")

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
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


@mcp.tool()
def add_task(
    title: str,
    description: str = None,
    due_date: str = None,
    priority_id: int = None,
    category_id: int = None,
    status_id: int = None,
    started_at: str = None,
    completed_at: str = None
):
    """Add task with full support of fields"""
    try:
        if not title or not title.strip():
            logger.warning("Attempted to add task with empty title")
            return {"status": "error", "message": "Task title cannot be empty"}

        fields = ["title"]
        values = [title.strip()]

        # Опциональные поля
        optional_fields = {
            "description": description,
            "due_date": due_date,
            "priority_id": priority_id,
            "category_id": category_id,
            "status_id": status_id,
            "started_at": started_at,
            "completed_at": completed_at
        }

        for field, value in optional_fields.items():
            if value is not None:
                fields.append(field)
                values.append(value)

        placeholders = ", ".join("?" for _ in fields)
        sql = f"INSERT INTO tasks ({', '.join(fields)}) VALUES ({placeholders})"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            task_id = cursor.lastrowid

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            task = dict(row)

            logger.info(f"Added task: {task['id']} - {task['title']}")
            return {"status": "success", "task": task}

    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return {"status": "error", "message": "Failed to add task"}


@mcp.tool()
def list_tasks():
    """Return all tasks with all fields"""
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
def delete_task(id: int):
    """Delete task by ID"""
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
    """Main function with proper error handling"""
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