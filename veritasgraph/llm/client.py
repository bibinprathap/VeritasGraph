"""OpenAI-compatible chat client (Ollama /v1, vLLM, llama.cpp server, TGI)."""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, List, Optional

import httpx

from veritasgraph.llm.config import Endpoint
from veritasgraph.llm.netpolicy import assert_local_endpoint

log = logging.getLogger("veritasgraph.llm")

RETRIES = 3
Message = Dict[str, str]


class LLMError(RuntimeError):
    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


class _Http:
    """Shared retrying POST for every role."""

    def __init__(self, ep: Endpoint, transport: Optional[httpx.BaseTransport] = None) -> None:
        assert_local_endpoint(ep.base_url)
        self.ep = ep
        headers = {"Authorization": f"Bearer {ep.api_key}"} if ep.api_key else {}
        self._http = httpx.Client(
            base_url=ep.base_url, headers=headers, timeout=ep.timeout_s, transport=transport
        )

    def post(self, path: str, body: Dict[str, Any]) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(RETRIES):
            try:
                resp = self._http.post(path, json=body)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = exc
            else:
                if resp.status_code != 429 and resp.status_code < 500:
                    return resp
                last = LLMError(f"{path} returned {resp.status_code}", resp.status_code)
            time.sleep(min(2**attempt, 8) + random.random() / 2)
        raise LLMError(f"{self.ep.role} endpoint failed after {RETRIES} attempts: {last}") from last

    def close(self) -> None:
        self._http.close()


class ChatClient(_Http):
    def complete(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        body: Dict[str, Any] = {
            "model": self.ep.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            **self.ep.extra_body,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        if response_format:
            body["response_format"] = response_format
        resp = self.post("/chat/completions", body)
        if resp.status_code >= 400:
            # Never echo the request body: it may contain schema samples.
            raise LLMError(f"chat completion rejected ({resp.status_code})", resp.status_code)
        choice = (resp.json().get("choices") or [{}])[0]
        return (choice.get("message") or {}).get("content") or ""
