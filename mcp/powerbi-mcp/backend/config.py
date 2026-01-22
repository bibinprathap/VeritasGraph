"""
Configuration management for the backend API
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


# Get project root (2 levels up from backend/config.py)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_TITLE: str = "Power BI Natural Language Query API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Convert natural language queries to DAX and execute against Power BI"
    DEBUG: bool = False
    
    # MCP Server Settings
    MCP_SERVER_PATH: str = str(PROJECT_ROOT / "src" / "server.py")
    MCP_PYTHON_PATH: str = str(PROJECT_ROOT / "src")
    MCP_PYTHON_COMMAND: str = "python"
    
    # LLM Provider Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" or "openai"
    
    # Ollama Settings (for local development)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    
    # OpenAI-Compatible Settings (for production)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # LangChain/LangGraph Settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "15"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0"))  # Low temperature for deterministic DAX
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = str(ENV_FILE)  # Use .env at project root
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

