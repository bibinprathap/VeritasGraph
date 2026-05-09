"""
Temporal data model helpers for knowledge graph relationships.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from ..utils.exceptions import TemporalValidationError


class TemporalBound(Enum):
    """Sentinel bounds for open-ended temporal intervals."""

    OPEN = "OPEN"


def _default_recorded_at() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BiTemporalFact:
    """
    Backward-compatible wrapper around existing relationship dictionaries.

    Design note:
    Facts continue to live as plain relationship dicts in the graph. This wrapper
    is only used internally for normalization so existing callers can keep
    reading and writing `valid_from` / `valid_until` directly.
    """

    valid_from: Optional[datetime]
    valid_until: Optional[datetime | TemporalBound]
    recorded_at: datetime = field(default_factory=_default_recorded_at)
    superseded_at: datetime | TemporalBound = TemporalBound.OPEN

    @classmethod
    def from_relationship(cls, relationship: Dict[str, Any]) -> "BiTemporalFact":
        valid_until_raw = relationship.get("valid_until", TemporalBound.OPEN)
        if valid_until_raw is None:
            valid_until_raw = TemporalBound.OPEN

        valid_from = parse_temporal_value(relationship.get("valid_from"))
        recorded_at_raw = relationship.get("recorded_at")
        superseded_at_raw = relationship.get("superseded_at", TemporalBound.OPEN)

        return cls(
            valid_from=valid_from,
            valid_until=parse_temporal_bound(valid_until_raw),
            recorded_at=parse_temporal_value(recorded_at_raw) if recorded_at_raw is not None else (valid_from or _default_recorded_at()),
            superseded_at=parse_temporal_bound(superseded_at_raw, default=TemporalBound.OPEN),
        )

    def to_relationship_fields(self) -> Dict[str, Any]:
        return {
            "valid_from": serialize_temporal_value(self.valid_from),
            "valid_until": serialize_temporal_bound(self.valid_until),
            "recorded_at": serialize_temporal_value(self.recorded_at),
            "superseded_at": serialize_temporal_bound(self.superseded_at),
        }


def _coerce_iso_like_string(value: str) -> str:
    match = re.match(
        r"^(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?P<rest>.*)$",
        value.strip(),
    )
    if not match:
        return value.strip()

    month = int(match.group("month"))
    day = int(match.group("day"))
    rest = match.group("rest")
    return f"{match.group('year')}-{month:02d}-{day:02d}{rest}"


def parse_temporal_value(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, timezone.utc)
    elif isinstance(value, str):
        normalized = _coerce_iso_like_string(value)
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise TemporalValidationError(
                "Invalid temporal value",
                temporal_context={"value": value},
            ) from exc
    else:
        raise TemporalValidationError(
            "Unsupported temporal value type",
            temporal_context={"value": value, "type": type(value).__name__},
        )

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_temporal_bound(
    value: Any,
    *,
    default: Optional[datetime | TemporalBound] = None,
) -> Optional[datetime | TemporalBound]:
    if value is None:
        return default
    if value == TemporalBound.OPEN or value == TemporalBound.OPEN.value:
        return TemporalBound.OPEN
    return parse_temporal_value(value)


def serialize_temporal_value(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize_temporal_bound(value: Optional[datetime | TemporalBound]) -> Optional[str]:
    if value in (None, TemporalBound.OPEN):
        return None
    return serialize_temporal_value(value)


def deserialize_relationship_temporal_fields(relationship: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(relationship)
    fact = BiTemporalFact.from_relationship(normalized)
    normalized.update(fact.to_relationship_fields())
    if fact.valid_until is TemporalBound.OPEN:
        normalized["valid_until"] = TemporalBound.OPEN
    if fact.superseded_at is TemporalBound.OPEN:
        normalized["superseded_at"] = TemporalBound.OPEN
    return normalized


def relationship_to_json_ready(relationship: Dict[str, Any]) -> Dict[str, Any]:
    json_ready = dict(relationship)
    for field in ("valid_from", "recorded_at"):
        if field in json_ready:
            json_ready[field] = serialize_temporal_value(parse_temporal_value(json_ready[field]))
    for field in ("valid_until", "superseded_at"):
        if field in json_ready:
            json_ready[field] = serialize_temporal_bound(parse_temporal_bound(json_ready[field]))
    return json_ready


def temporal_structure_to_json_ready(value: Any) -> Any:
    """Recursively convert temporal values into JSON-safe primitives."""
    if isinstance(value, dict):
        return {key: temporal_structure_to_json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [temporal_structure_to_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [temporal_structure_to_json_ready(item) for item in value]
    if value is TemporalBound.OPEN:
        return None
    if isinstance(value, datetime):
        return serialize_temporal_value(value)
    return value


def dumps_relationship_json(relationship: Dict[str, Any]) -> str:
    return json.dumps(relationship_to_json_ready(relationship))
