import logging
import asyncio
from mcp.server.fastmcp import FastMCP
import json

# Init server
mcp = FastMCP("TaskManager")

# Init tasks list
tasks = []

# Logging config
logging.basicConfig(
    level=logging.INFO,  # Изменено с DEBUG на INFO для production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@mcp.tool()
def add_task(title: str):
    """Add task to list"""
    try:
        # Валидация входных данных
        if not title or not title.strip():
            logger.warning("Attempted to add task with empty title")
            return {"status": "error", "message": "Task title cannot be empty"}

        task = {"id": len(tasks) + 1, "title": title.strip(), "done": False}
        tasks.append(task)
        logger.info(f"Added task: {task['id']} - {task['title']}")
        return {"status": "success", "task": task}

    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return {"status": "error", "message": "Failed to add task"}

@mcp.tool()
def list_tasks():
    """Return all tasks"""
    try:
        logger.info("Retrieving all tasks")
        return {"status": "success", "tasks": tasks, "count": len(tasks)}

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return {"status": "error", "message": "Failed to retrieve tasks"}


@mcp.tool()
def delete_task(id: int):
    """Delete task by ID"""
    global tasks  # Перенесено в начало функции

    try:
        # Валидация ID
        if not isinstance(id, int) or id <= 0:
            logger.warning(f"Invalid task ID provided: {id}")
            return {"status": "error", "message": "Invalid task ID"}

        # Проверяем существование задачи
        task_exists = any(task["id"] == id for task in tasks)
        if not task_exists:
            logger.warning(f"Task with ID {id} not found")
            return {"status": "error", "message": f"Task with ID {id} not found"}

        tasks = [task for task in tasks if task["id"] != id]
        logger.info(f"Deleted task with ID: {id}")
        return {"status": "success", "message": f"Task {id} deleted", "id": id}

    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return {"status": "error", "message": "Failed to delete task"}


def main():
    """Main function with proper error handling"""
    try:
        logger.info("Starting MCP TaskManager server...")
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise

if __name__ == "__main__":
    main()


