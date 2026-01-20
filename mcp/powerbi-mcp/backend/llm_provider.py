"""
LLM Provider abstraction for Ollama and OpenAI-compatible endpoints
"""
import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """Abstraction layer for LLM providers"""
    
    def __init__(self):
        self.llm: Optional[BaseChatModel] = None
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize the LLM based on provider setting"""
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "ollama":
            logger.info(f"Initializing Ollama LLM: {settings.OLLAMA_MODEL}")
            self.llm = ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=settings.TEMPERATURE,
            )
        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY must be set when using OpenAI provider")
            
            logger.info(f"Initializing OpenAI-compatible LLM: {settings.OPENAI_MODEL}")
            self.llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                temperature=settings.TEMPERATURE,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider}. Use 'ollama' or 'openai'")
    
    def get_llm(self) -> BaseChatModel:
        """Get the initialized LLM instance"""
        if self.llm is None:
            self._initialize_llm()
        return self.llm
    
    def update_provider(self, provider: str, **kwargs) -> None:
        """Update LLM provider at runtime"""
        settings.LLM_PROVIDER = provider.lower()
        
        if provider.lower() == "ollama":
            settings.OLLAMA_BASE_URL = kwargs.get("base_url", settings.OLLAMA_BASE_URL)
            settings.OLLAMA_MODEL = kwargs.get("model", settings.OLLAMA_MODEL)
        elif provider.lower() == "openai":
            settings.OPENAI_API_KEY = kwargs.get("api_key", settings.OPENAI_API_KEY)
            settings.OPENAI_BASE_URL = kwargs.get("base_url", settings.OPENAI_BASE_URL)
            settings.OPENAI_MODEL = kwargs.get("model", settings.OPENAI_MODEL)
        
        self._initialize_llm()


# Global LLM provider instance
llm_provider = LLMProvider()

