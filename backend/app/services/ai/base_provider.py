from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'openai', 'fallback')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model (e.g. 'gemini-3.8-flash')."""
        pass

    @abstractmethod
    async def generate_understanding(
        self, prompt: str, system_instruction: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Generate structured JSON dataset understanding from prompt.
        Must return parsed Python dictionary conforming to expected schema.
        """
        pass

    @abstractmethod
    async def generate_json(
        self, prompt: str, system_instruction: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response from prompt and system instruction.
        Must return parsed Python dictionary.
        """
        pass

