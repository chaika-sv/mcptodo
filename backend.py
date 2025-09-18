from fastapi import FastAPI
import sqlite3
from typing import List, Dict
from pydantic import BaseModel
from fastapi.responses import FileResponse
from mcp_client_llm import TaskManagerAgent, AgentConfig, ModelProvider  # твой существующий код агента
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TaskManager API")

DB_PATH = "tasks.db"

# Инициализация агента при старте FastAPI
agent_config = AgentConfig(model_provider=ModelProvider.OPENROUTER)  # или deepseek
agent = TaskManagerAgent(agent_config)



def get_db_connection():
    """
    Создаёт и возвращает подключение к базе данных SQLite.

    Returns:
        sqlite3.Connection: Подключение к базе с включённым режимом
        возврата строк как словарей (sqlite3.Row).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def get_index():
    """
    Возвращает главный HTML-файл интерфейса.

    Returns:
        FileResponse: Файл index.html для отображения в браузере.
    """
    return FileResponse("index.html")




@app.get("/tasks", response_model=List[Dict])
def list_tasks():
    """
    Получает список всех задач с информацией о приоритете, категории и статусе.

    Returns:
        List[Dict]: Список задач с полями:
            - id, title, description, created_at (и другие из таблицы tasks)
            - priority (название приоритета)
            - category (название категории)
            - status (название статуса)

        В случае ошибки возвращает {"error": <сообщение>}.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, 
                       p.name AS priority_name,
                       c.name AS category_name,
                       s.name AS status_name
                FROM tasks t
                LEFT JOIN priorities p ON t.priority_id = p.id
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN statuses s ON t.status_id = s.id
                ORDER BY t.created_at
            """)
            rows = cursor.fetchall()
            tasks = []
            for row in rows:
                task = dict(row)
                task['priority'] = task.pop('priority_name')
                task['category'] = task.pop('category_name')
                task['status'] = task.pop('status_name')
                tasks.append(task)
            return tasks
    except Exception as e:
        return {"error": str(e)}



class ChatRequest(BaseModel):
    """
    Модель запроса для чата с агентом.

    Атрибуты:
        message (str): Текстовое сообщение пользователя.
    """
    message: str





@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Обрабатывает сообщение пользователя через LLM-агента.

    Args:
        request (ChatRequest): Объект с текстовым сообщением.

    Returns:
        dict: Ответ в формате {"response": <строка>}:
            - текст ответа агента, если агент готов;
            - сообщение об ошибке, если агент не инициализирован.
    """
    if not agent.is_ready:
        return {"response": "❌ Агент не готов."}
    response = await agent.process_message(request.message)
    return {"response": response}



@app.on_event("startup")
async def startup_event():
    """
    Хук FastAPI: инициализация MCP-агента при запуске приложения.

    Если агент не удалось инициализировать, выводит сообщение об ошибке в консоль.
    """
    initialized = await agent.initialize()
    if not initialized:
        print("❌ Агент MCP не удалось инициализировать")
