"""
LLM Providers Module

This module provides clean, intuitive imports for LLM providers used in VeritasReason.
It wraps the underlying provider functionality from veritasreason.semantic_extract.providers
to provide a cleaner API.

Supported Providers:
    - Groq: Groq API for fast inference
    - OpenAI: OpenAI API (GPT-3.5, GPT-4, etc.)
    - HuggingFaceLLM: HuggingFace Transformers for local LLM inference
    - LiteLLM: Unified interface to 100+ LLM providers (OpenAI, Anthropic, Groq, Azure, Bedrock, Vertex AI, etc.)

Example Usage:
    >>> from veritasreason.llms import Groq, OpenAI, HuggingFaceLLM, LiteLLM
    >>> 
    >>> # Groq provider
    >>> groq = Groq(model="llama-3.1-8b-instant", api_key="your-key")
    >>> response = groq.generate("Hello, world!")
    >>> 
    >>> # OpenAI provider
    >>> openai = OpenAI(model="gpt-4", api_key="your-key")
    >>> response = openai.generate("Hello, world!")
    >>> 
    >>> # HuggingFace LLM provider
    >>> hf = HuggingFaceLLM(model_name="gpt2")
    >>> response = hf.generate("Hello, world!")
    >>> 
    >>> # LiteLLM provider (supports 100+ LLMs)
    >>> llm = LiteLLM(model="openai/gpt-4o", api_key="your-key")
    >>> response = llm.generate("Hello, world!")
    >>> # Or use other providers via LiteLLM
    >>> llm = LiteLLM(model="anthropic/claude-sonnet-4-20250514")
    >>> response = llm.generate("Hello, world!")

Author: VeritasReason Contributors
License: MIT
"""

from .groq import Groq
from .openai import OpenAI
from .huggingface import HuggingFaceLLM
from .litellm import LiteLLM

__all__ = ["Groq", "OpenAI", "HuggingFaceLLM", "LiteLLM"]

