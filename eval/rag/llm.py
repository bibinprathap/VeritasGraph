"""Minimal Ollama chat client shared by the naive-RAG adapter and the judge.

Kept deliberately thin and dependency-light (mirrors
``studio_api.graphrag_engine.GraphRAGEngine._chat``). A module-level
``ChatFn`` type lets tests inject a fake callable so nothing here needs a live
Ollama server.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional

import httpx

# A chat function maps (model, messages, temperature) -> response text.
ChatFn = Callable[[str, List[Dict[str, str]], float], str]


def _ollama_base() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    if not host.startswith("http"):
        host = f"http://{host}"
    return host.rstrip("/")


def ollama_chat(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    *,
    num_predict: Optional[int] = None,
    timeout: float = 180.0,
) -> str:
    """Call Ollama ``/api/chat`` (non-streaming) and return the message content."""
    body: Dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if num_predict is not None:
        body["options"] = {"temperature": temperature, "num_predict": num_predict}  # type: ignore[index]
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{_ollama_base()}/api/chat", json=body)
        resp.raise_for_status()
        result = resp.json()
    return (result.get("message") or {}).get("content", "")
