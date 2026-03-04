"""
OpenAI-Compatible API Configuration Module

This module provides configuration utilities for connecting to OpenAI, Azure OpenAI,
and any OpenAI-compatible API endpoints (e.g., Ollama, LM Studio, Groq, Together AI, etc.)

Environment Variables:
    GRAPHRAG_API_KEY: API key for the LLM provider
    GRAPHRAG_API_TYPE: API type ('openai' or 'azure'), defaults to 'openai'
    GRAPHRAG_LLM_MODEL: Model name for chat completions
    GRAPHRAG_LLM_API_BASE: Base URL for LLM API
    GRAPHRAG_EMBEDDING_MODEL: Model name for embeddings
    GRAPHRAG_EMBEDDING_API_BASE: Base URL for embedding API
    GRAPHRAG_MAX_RETRIES: Maximum retry attempts (default: 10)
    
Azure-specific:
    GRAPHRAG_API_VERSION: Azure API version
    GRAPHRAG_DEPLOYMENT_NAME: Azure deployment name for LLM
    GRAPHRAG_EMBEDDING_DEPLOYMENT_NAME: Azure deployment name for embeddings
    
Optional:
    GRAPHRAG_ORGANIZATION: OpenAI organization ID
    GRAPHRAG_EMBEDDING_API_KEY: Separate API key for embeddings (if different)
    GRAPHRAG_EMBEDDING_API_TYPE: Separate API type for embeddings
"""

import os
from graphrag.query.llm.oai.typing import OpenaiApiType


def get_api_type() -> OpenaiApiType:
    """
    Determine the API type based on environment variables.
    Supports: OpenAI, Azure OpenAI, and any OpenAI-compatible API.
    
    Set GRAPHRAG_API_TYPE to 'azure' for Azure OpenAI, otherwise defaults to OpenAI-compatible.
    
    Returns:
        OpenaiApiType: The API type enum value
    """
    api_type_str = os.environ.get("GRAPHRAG_API_TYPE", "openai").lower()
    if api_type_str == "azure":
        return OpenaiApiType.AzureOpenAI
    return OpenaiApiType.OpenAI


def get_llm_config() -> dict:
    """
    Get LLM configuration from environment variables.
    Supports OpenAI, Azure OpenAI, and OpenAI-compatible APIs.
    
    Returns:
        dict: Configuration dictionary with keys:
            - api_key: API key for authentication
            - api_base: Base URL for the API
            - model: Model name to use
            - api_type: OpenaiApiType enum value
            - max_retries: Maximum number of retries
            - api_version: (Azure only) API version
            - deployment_name: (Azure only) Deployment name
            - organization: (Optional) Organization ID
    """
    api_type = get_api_type()
    
    config = {
        "api_key": os.environ["GRAPHRAG_API_KEY"],
        "api_base": os.environ.get("GRAPHRAG_LLM_API_BASE", "https://api.openai.com/v1"),
        "model": os.environ.get("GRAPHRAG_LLM_MODEL", "gpt-4-turbo-preview"),
        "api_type": api_type,
        "max_retries": int(os.environ.get("GRAPHRAG_MAX_RETRIES", "10")),
    }
    
    # Azure-specific configuration
    if api_type == OpenaiApiType.AzureOpenAI:
        config["api_version"] = os.environ.get("GRAPHRAG_API_VERSION", "2024-02-15-preview")
        config["deployment_name"] = os.environ.get("GRAPHRAG_DEPLOYMENT_NAME", config["model"])
    
    # Optional: Organization ID for OpenAI
    org_id = os.environ.get("GRAPHRAG_ORGANIZATION")
    if org_id:
        config["organization"] = org_id
    
    return config


def get_embedding_config() -> dict:
    """
    Get embedding configuration from environment variables.
    Supports OpenAI, Azure OpenAI, and OpenAI-compatible APIs.
    
    Allows separate configuration for embeddings (useful for hybrid setups,
    e.g., using Groq for LLM and Ollama for embeddings).
    
    Returns:
        dict: Configuration dictionary with keys:
            - api_key: API key for authentication
            - api_base: Base URL for the API
            - model: Model name to use
            - api_type: OpenaiApiType enum value
            - max_retries: Maximum number of retries
            - deployment_name: Deployment name (required for Azure, model name for others)
            - api_version: (Azure only) API version
    """
    api_type = get_api_type()
    
    # Allow separate API type for embeddings (useful for hybrid setups)
    embedding_api_type_str = os.environ.get("GRAPHRAG_EMBEDDING_API_TYPE", "").lower()
    if embedding_api_type_str == "azure":
        embedding_api_type = OpenaiApiType.AzureOpenAI
    elif embedding_api_type_str == "openai":
        embedding_api_type = OpenaiApiType.OpenAI
    else:
        embedding_api_type = api_type  # Default to same as LLM
    
    config = {
        "api_key": os.environ.get("GRAPHRAG_EMBEDDING_API_KEY", os.environ["GRAPHRAG_API_KEY"]),
        "api_base": os.environ.get("GRAPHRAG_EMBEDDING_API_BASE", "https://api.openai.com/v1"),
        "model": os.environ.get("GRAPHRAG_EMBEDDING_MODEL", "text-embedding-3-small"),
        "api_type": embedding_api_type,
        "max_retries": int(os.environ.get("GRAPHRAG_MAX_RETRIES", "10")),
    }
    
    # Azure-specific configuration
    if embedding_api_type == OpenaiApiType.AzureOpenAI:
        config["api_version"] = os.environ.get(
            "GRAPHRAG_EMBEDDING_API_VERSION", 
            os.environ.get("GRAPHRAG_API_VERSION", "2024-02-15-preview")
        )
        config["deployment_name"] = os.environ.get("GRAPHRAG_EMBEDDING_DEPLOYMENT_NAME", config["model"])
    else:
        config["deployment_name"] = config["model"]
    
    return config


def validate_config() -> tuple[bool, list[str]]:
    """
    Validate that required environment variables are set.
    
    Returns:
        tuple: (is_valid, list of error messages)
    """
    errors = []
    
    if not os.environ.get("GRAPHRAG_API_KEY"):
        errors.append("GRAPHRAG_API_KEY is required")
    
    api_type = os.environ.get("GRAPHRAG_API_TYPE", "openai").lower()
    if api_type == "azure":
        if not os.environ.get("GRAPHRAG_DEPLOYMENT_NAME"):
            errors.append("GRAPHRAG_DEPLOYMENT_NAME is required for Azure OpenAI")
    
    return len(errors) == 0, errors


def print_config_summary():
    """Print a summary of the current configuration (for debugging)."""
    api_type = get_api_type()
    llm_config = get_llm_config()
    embedding_config = get_embedding_config()
    
    print("=" * 50)
    print("GraphRAG Configuration Summary")
    print("=" * 50)
    print(f"API Type: {api_type.value}")
    print(f"LLM Model: {llm_config['model']}")
    print(f"LLM API Base: {llm_config['api_base']}")
    print(f"Embedding Model: {embedding_config['model']}")
    print(f"Embedding API Base: {embedding_config['api_base']}")
    print("=" * 50)
