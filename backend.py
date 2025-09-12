from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List, Dict
from pydantic import BaseModel
from fastapi.responses import FileResponse
import asyncio
from mcp_client_llm import TaskManagerAgent, AgentConfig, ModelProvider  # твой существующий код агента
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TaskManager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

DB_PATH = "tasks.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def get_index():
    return FileResponse("index.html")

@app.get("/tasks", response_model=List[Dict])
def list_tasks():
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


# ======== ЧАТ ========
class ChatRequest(BaseModel):
    message: str

# Инициализация агента при старте FastAPI
agent_config = AgentConfig(model_provider=ModelProvider.OPENROUTER)  # или deepseek
agent = TaskManagerAgent(agent_config)


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not agent.is_ready:
        return {"response": "❌ Агент не готов."}
    response = await agent.process_message(request.message)
    return {"response": response}

@app.on_event("startup")
async def startup_event():
    # Инициализация агента при старте FastAPI
    initialized = await agent.initialize()
    if not initialized:
        print("❌ Агент MCP не удалось инициализировать")
