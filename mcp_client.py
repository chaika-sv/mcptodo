# mcp_client.py
import asyncio
import logging
import os

from dotenv import load_dotenv
from typing import Optional, Dict, Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from llm_provider import AgentConfig, ModelFactory, ModelProvider
from task_utils import retry_on_failure

# ==== ЛОГГИРОВАНИЕ ====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_client_llm.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class TaskManagerAgent:
    """AI-агент для работы с задачами."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent = None
        self.checkpointer = None
        self.mcp_client = None
        self.tools = []
        self._initialized = False

        logger.info(f"Создан агент с провайдером: {config.model_provider.value}")

    @property
    def is_ready(self) -> bool:
        return self._initialized and self.agent is not None

    async def initialize(self) -> bool:
        if self._initialized:
            logger.warning("Агент уже инициализирован")
            return True

        logger.info("Инициализация агента...")

        try:
            # валидация конфигурации
            self.config.validate()

            # инициализация mcp клиента (с retry)
            await self._init_mcp_client()

            # создание модели через фабрику
            model = ModelFactory.create_model(self.config)

            # создание checkpointer (memory)
            if self.config.use_memory:
                self.checkpointer = InMemorySaver()
                logger.info("Память агента включена")

            # создание react-агента
            self.agent = create_react_agent(
                model=model,
                tools=self.tools,
                checkpointer=self.checkpointer,
                prompt=self._get_system_prompt()
            )

            self._initialized = True
            logger.info("✅ Агент успешно инициализирован")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False

    @retry_on_failure()
    async def _init_mcp_client(self):
        """Инициализация MCP клиента и загрузка инструментов"""
        self.mcp_client = MultiServerMCPClient(self.config.get_mcp_config())
        self.tools = await self.mcp_client.get_tools()

        if not self.tools:
            raise Exception("Нет доступных MCP инструментов")

        logger.info(f"Загружено {len(self.tools)} инструментов")
        for tool in self.tools:
            logger.info(f"  • {tool.name}")

    def _get_system_prompt(self) -> str:
        """Системный промпт для агента — оставил как в оригинале."""
        return (
            "Ты полезный AI-ассистент для работы с задачами пользователя. "
            "Выполняй запросы пользователя точно и эффективно. "
            "При создании, редактировании и удалении задач подтверждай успешное выполнение. "
            "Предоставляй подробную информацию о действиях. "
            "При ошибках объясняй причину и предлагай решения."
            "Не вычисляй даты самостоятельно. Если пользователь использует относительные выражения (завтра, послезавтра и т.п.), то в поле даты отправляй это выражение как есть."
        )

    @retry_on_failure()
    async def process_message(self, user_input: str, thread_id: str = "default") -> str:
        """Обработка сообщения пользователя через react-агента (ainvoke)."""
        if not self.is_ready:
            return "❌ Агент не готов. Попробуйте переинициализировать."

        try:
            config = {"configurable": {"thread_id": thread_id}}
            message_input = {"messages": [HumanMessage(content=user_input)]}

            response = await self.agent.ainvoke(message_input, config)
            # ожидаем структуру как в оригинале
            return response["messages"][-1].content

        except Exception as e:
            error_msg = f"❌ Ошибка обработки: {e}"
            logger.error(error_msg)
            return error_msg

    def get_status(self) -> Dict[str, Any]:
        """Информация о состоянии агента (для команды status)."""
        return {
            "initialized": self._initialized,
            "model_provider": self.config.model_provider.value,
            "memory_enabled": self.config.use_memory,
            "tools_count": len(self.tools)
        }


class InteractiveChat:
    """Интерактивный чат."""

    def __init__(self, agent: TaskManagerAgent):
        self.agent = agent
        self.thread_id = "main"

    def get_user_input(self) -> Optional[str]:
        try:
            user_input = input("\n> ").strip()

            if user_input.lower() in ['quit', 'exit', 'выход']:
                return None
            elif user_input.lower() == 'clear':
                self.thread_id = f"thread_{asyncio.get_event_loop().time()}"
                print("💭 История очищена")
                return ""
            elif user_input.lower() == 'status':
                status = self.agent.get_status()
                print(f"📊 Статус: {status}")
                return ""
            elif not user_input:
                return ""

            return user_input

        except (KeyboardInterrupt, EOFError):
            return None

    async def run(self):
        print("🤖 AI-агент готов к работе! (quit для выхода, status для статуса, clear для очистки)")

        while True:
            user_input = self.get_user_input()

            if user_input is None:
                break
            elif user_input == "":
                continue

            response = await self.agent.process_message(user_input, self.thread_id)
            print(f"\n{response}")

        print("\n👋 До свидания!")


async def main():
    load_dotenv()

    try:
        config = AgentConfig(
            model_provider=ModelProvider(os.getenv("MODEL_PROVIDER", "openrouter"))
        )

        agent = TaskManagerAgent(config)

        if not await agent.initialize():
            logger.error("❌ Не удалось инициализировать агента")
            return

        chat = InteractiveChat(agent)
        await chat.run()

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

    logger.info("🏁 Завершение работы")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
