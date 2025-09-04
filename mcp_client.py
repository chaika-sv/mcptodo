import asyncio
import json
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_task_manager():
    """Test MCP TaskManager server"""

    # Server parameters (путь к вашему серверу)
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],  # путь к вашему серверу
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Инициализация
            await session.initialize()

            print("🚀 MCP TaskManager Client - Testing Started")
            print("=" * 50)

            try:
                # Тест 1: Добавление задач
                print("\n📝 Test 1: Adding tasks")
                result1 = await session.call_tool("add_task", {"title": "Buy groceries"})
                print(f"Add task 1: {result1.content[0].text}")

                result2 = await session.call_tool("add_task", {"title": "Write code"})
                print(f"Add task 2: {result2.content[0].text}")

                result3 = await session.call_tool("add_task", {"title": "Read book"})
                print(f"Add task 3: {result3.content[0].text}")

                # Тест 2: Список задач
                print("\n📋 Test 2: List all tasks")
                result = await session.call_tool("list_tasks", {})
                tasks_data = json.loads(result.content[0].text)
                print(f"All tasks: {json.dumps(tasks_data, indent=2)}")

                # Тест 3: Удаление задачи
                print("\n🗑️  Test 3: Delete task")
                result = await session.call_tool("delete_task", {"id": 2})
                print(f"Delete task 2: {result.content[0].text}")

                # Тест 4: Список после удаления
                print("\n📋 Test 4: List after deletion")
                result = await session.call_tool("list_tasks", {})
                tasks_data = json.loads(result.content[0].text)
                print(f"Tasks after deletion: {json.dumps(tasks_data, indent=2)}")

                # Тест 5: Ошибки валидации
                print("\n❌ Test 5: Error handling")

                # Пустой заголовок
                result = await session.call_tool("add_task", {"title": ""})
                print(f"Empty title: {result.content[0].text}")

                # Неверный ID для удаления
                result = await session.call_tool("delete_task", {"id": 999})
                print(f"Invalid ID: {result.content[0].text}")

                # Некорректный ID
                result = await session.call_tool("delete_task", {"id": -1})
                print(f"Negative ID: {result.content[0].text}")

                print("\n✅ All tests completed!")

            except Exception as e:
                logger.error(f"Test failed: {e}")
                print(f"❌ Error: {e}")


def main():
    """Main function"""
    try:
        asyncio.run(test_task_manager())
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
    except Exception as e:
        logger.error(f"Client error: {e}")
        print(f"❌ Client error: {e}")


if __name__ == "__main__":
    main()