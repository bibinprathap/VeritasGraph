"""Pydantic-validated JSON output from any OpenAI-compatible server.

The mode is chosen by probing, not by model name: ``json_schema`` first, then
``json_object``, then plain prompting with the schema in the instructions. The
working mode is cached per (endpoint, model). Invalid output is sent back once
or twice with the validation errors.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from veritasgraph.llm.client import ChatClient, LLMError, Message

T = TypeVar("T", bound=BaseModel)
MODES = ("json_schema", "json_object", "prompt")
_MODE_CACHE: Dict[Tuple[str, str], str] = {}
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(text: str) -> str:
    text = _FENCE.sub("", text.strip())
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


def _response_format(mode: str, schema: Type[BaseModel]) -> Dict | None:
    if mode == "json_schema":
        return {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": True},
        }
    if mode == "json_object":
        return {"type": "json_object"}
    return None


def _with_schema_hint(messages: List[Message], schema: Type[BaseModel]) -> List[Message]:
    hint = (
        "Reply with a single JSON object and nothing else. It must validate against this "
        f"JSON Schema:\n{json.dumps(schema.model_json_schema())}"
    )
    return [*messages, {"role": "user", "content": hint}]


def structured(client: ChatClient, messages: List[Message], schema: Type[T], *, retries: int = 2) -> T:
    key = (client.ep.base_url, client.ep.model)
    modes = [_MODE_CACHE[key]] if key in _MODE_CACHE else list(MODES)
    for mode in modes:
        msgs = messages if mode == "json_schema" else _with_schema_hint(messages, schema)
        fmt = _response_format(mode, schema)
        try:
            text = client.complete(msgs, response_format=fmt)
        except LLMError as exc:
            if exc.status in (400, 422) and mode != "prompt":
                continue  # server does not support this mode; try the next
            raise
        _MODE_CACHE[key] = mode
        for attempt in range(retries + 1):
            try:
                return schema.model_validate_json(_extract_json(text))
            except ValidationError as err:
                if attempt == retries:
                    raise LLMError(f"{schema.__name__}: output did not validate after {retries + 1} tries") from err
                problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in err.errors()[:5])
                msgs = [
                    *msgs,
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": f"That JSON is invalid ({problems}). Reply with corrected JSON only."},
                ]
                text = client.complete(msgs, response_format=fmt)
    raise LLMError(f"No structured-output mode worked for {client.ep.model}")
