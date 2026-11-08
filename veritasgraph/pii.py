"""PII detection and policy for ingested text.

``VERITASGRAPH_PII_POLICY`` controls ingestion:

* ``tag`` (default) — store text as-is, flag the source and every entity
  extracted from it with the PII categories found;
* ``redact_before_extract`` — replace PII with ``[REDACTED:<kind>]`` before the
  text reaches the LLM or the store;
* ``reject`` — refuse documents that contain PII;
* ``off`` — no scanning.

Reads are redacted for callers below ``VERITASGRAPH_PII_REVEAL_ROLE`` (default
``editor``), so a viewer token or a read-only MCP client never receives flagged
text verbatim.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

POLICIES = ("off", "tag", "redact_before_extract", "reject")
_ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}

_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    (
        "phone",
        re.compile(r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\w)"),
    ),
    ("ip_address", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
]


class PIIRejected(ValueError):
    pass


def policy() -> str:
    value = os.getenv("VERITASGRAPH_PII_POLICY", "tag").strip().lower()
    if value not in POLICIES:
        raise RuntimeError(f"VERITASGRAPH_PII_POLICY must be one of {POLICIES}")
    return value


def reveal_role() -> str:
    value = os.getenv("VERITASGRAPH_PII_REVEAL_ROLE", "editor").strip().lower()
    return value if value in _ROLE_RANK else "editor"


def can_see_pii(role: str) -> bool:
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK[reveal_role()]


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _matches(text: str) -> List[Tuple[str, int, int]]:
    found: List[Tuple[str, int, int]] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(text or ""):
            if kind == "credit_card":
                digits = re.sub(r"\D", "", m.group(0))
                if not (13 <= len(digits) <= 19 and _luhn(digits)):
                    continue
            if any(s < m.end() and m.start() < e for _, s, e in found):
                continue  # already covered by an earlier, more specific pattern
            found.append((kind, m.start(), m.end()))
    return found


def scan(text: str) -> List[str]:
    """Sorted PII categories present in ``text``."""
    return sorted({kind for kind, _, _ in _matches(text)})


def redact(text: str) -> str:
    if not text:
        return text
    out = text
    for kind, start, end in sorted(_matches(text), key=lambda m: m[1], reverse=True):
        out = out[:start] + f"[REDACTED:{kind}]" + out[end:]
    return out


def prepare_chunk(chunk: str) -> Tuple[str, List[str]]:
    """Apply the ingestion policy to one chunk: ``(text_to_use, flags)``."""
    mode = policy()
    if mode == "off":
        return chunk, []
    flags = scan(chunk)
    if not flags:
        return chunk, []
    if mode == "reject":
        raise PIIRejected(f"Document contains PII ({', '.join(flags)}); policy is 'reject'.")
    if mode == "redact_before_extract":
        return redact(chunk), flags
    return chunk, flags


# --------------------------------------------------------------------------- #
# Read-side redaction
# --------------------------------------------------------------------------- #
_TEXT_FIELDS = ("text", "description", "answer")


def _redact_item(item: Any) -> Any:
    if isinstance(item, dict):
        flagged = bool(item.get("pii_flags"))
        out = {}
        for k, v in item.items():
            if k in _TEXT_FIELDS and isinstance(v, str) and (flagged or k == "answer"):
                out[k] = redact(v)
            else:
                out[k] = _redact_item(v)
        return out
    if isinstance(item, list):
        return [_redact_item(v) for v in item]
    return item


def redact_payload(payload: Any, role: str) -> Any:
    """Redact flagged text (and free-text answers) unless ``role`` may see PII."""
    if can_see_pii(role):
        return payload
    return _redact_item(payload)


def redact_answer_payload(payload: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Like :func:`redact_payload`, but citations are always scanned: an answer
    built from flagged sources must not leak them to a viewer."""
    if can_see_pii(role):
        return payload
    out = _redact_item(payload)
    out["citations"] = [{**c, "text": redact(c.get("text", ""))} for c in out.get("citations", [])]
    return out
