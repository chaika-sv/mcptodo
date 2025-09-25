# task_nodes.py

from typing import TypedDict, Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

# Состояние для графа
class TaskState(TypedDict):
    description: str
    priority: Optional[str]
    due_date: Optional[str]
    category: Optional[str]
    task: Optional[Dict[str, Any]]
    confirmation: Optional[str]


# --- Узлы графа ---
async def priority_node(state: TaskState, llm) -> TaskState:
    """
    Определение приоритета задачи: low | normal | high
    """
    prompt = f"""
    Ты помощник для управления задачами.
    Определи приоритет следующей задачи:

    Задача: "{state['description']}"

    Приоритет нужно нормализовать в одно из значений:
    low, normal, high.

    Верни только слово с приоритетом.
    """
    result = await llm.call(prompt)
    state["priority"] = result.strip().lower()
    return state


async def due_date_node(state: TaskState, llm) -> TaskState:
    """
    Определение даты выполнения задачи (LLM).
    """
    prompt = f"""
    Ты помощник для управления задачами.
    Определи дату и время выполнения из описания задачи, если они указаны.

    Задача: "{state['description']}"

    Верни дату/время в формате ISO 8601 (ГГГГ-ММ-ДД ЧЧ:ММ), 
    либо "null", если даты нет.
    """
    result = await llm.call(prompt)
    state["due_date"] = result.strip()
    return state


async def category_node(state: TaskState, llm) -> TaskState:
    """
    Определение категории задачи.
    """
    prompt = f"""
    Ты помощник для управления задачами.
    Отнеси задачу к одной из категорий:
    ["work", "personal", "shopping", "health", "other"]

    Задача: "{state['description']}"

    Верни только название категории.
    """
    result = await llm.call(prompt)
    state["category"] = result.strip().lower()
    return state


async def assemble_task_node(state: TaskState) -> TaskState:
    """
    Собирает итоговую задачу из всех полей.
    """
    state["task"] = {
        "description": state["description"],
        "priority": state.get("priority"),
        "due_date": state.get("due_date"),
        "category": state.get("category"),
    }
    return state


async def confirmation_node(state: TaskState) -> TaskState:
    """
    Формирует подтверждение для пользователя.
    """
    task = state.get("task", {})
    state["confirmation"] = (
        f"✅ Задача создана:\n"
        f"- Описание: {task.get('description')}\n"
        f"- Приоритет: {task.get('priority')}\n"
        f"- Срок: {task.get('due_date')}\n"
        f"- Категория: {task.get('category')}"
    )
    return state
