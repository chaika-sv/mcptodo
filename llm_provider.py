# llm_provider.py
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any
import logging

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Доступные провайдеры моделей"""
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


@dataclass
class AgentConfig:
    """
    Конфигурация агента — хранит настройки моделей и общие флаги.
    """
    model_provider: ModelProvider = ModelProvider.OPENROUTER
    use_memory: bool = True

    model_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "ollama": {
            "model_name": "qwen2.5:32b",
            "base_url": "http://localhost:11434",
            "temperature": 0.0
        },
        "openrouter": {
            "model_name": "openai/gpt-4o-mini",
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1",
            "temperature": 0.0
        },
        "openai": {
            "model_name": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
            "temperature": 0.0
        },
        "deepseek": {
            "model_name": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
            "temperature": 0.0
        }
    })

    def validate(self) -> None:
        """Проверка корректности конфигурации (и наличия API-ключей, если требуется)."""
        config = self.model_configs.get(self.model_provider.value)
        if not config:
            raise ValueError(f"Неподдерживаемый провайдер: {self.model_provider}")

        api_key_env = config.get("api_key_env")
        if api_key_env and not os.getenv(api_key_env):
            raise ValueError(f"Отсутствует переменная окружения: {api_key_env}")

    def get_mcp_config(self) -> Dict[str, Any]:
        """
        Возвращает конфиг для MultiServerMCPClient.
        """
        return {
            "taskmanager": {
                "command": "python",
                "args": ["mcp_server.py"],
                "transport": "stdio"
            }
        }


class ModelFactory:
    """Фабрика для создания инстанса модели по AgentConfig."""

    @staticmethod
    def create_model(config: AgentConfig):
        provider = config.model_provider.value
        model_config = config.model_configs[provider]

        logger.info(f"Создание модели {provider}: {model_config['model_name']}")

        if provider == "ollama":
            return ChatOllama(
                model=model_config["model_name"],
                base_url=model_config["base_url"],
                temperature=model_config["temperature"]
            )

        elif provider in ["openrouter", "openai"]:
            api_key = os.getenv(model_config.get("api_key_env", ""))
            return ChatOpenAI(
                model=model_config["model_name"],
                api_key=api_key,
                base_url=model_config.get("base_url"),
                temperature=model_config["temperature"]
            )

        elif provider == "deepseek":
            api_key = os.getenv(model_config.get("api_key_env", ""))
            return ChatDeepSeek(
                model=model_config["model_name"],
                api_key=api_key,
                temperature=model_config["temperature"]
            )

        else:
            raise ValueError(f"Неизвестный провайдер: {provider}")
