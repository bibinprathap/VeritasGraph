"""
Temporal Normalizer

Deterministic resolution of temporal phrases extracted from text into
UTC datetime intervals. Zero LLM calls — pure regex and date arithmetic.

Usage::

    from veritasreason.kg import TemporalNormalizer
    from datetime import datetime, timezone

    tn = TemporalNormalizer(reference_date=datetime(2025, 3, 25, tzinfo=timezone.utc))
    start, end = tn.normalize("Q2 2021")   # → (2021-04-01, 2021-06-30)
    start, end = tn.normalize("last year") # → (2024-01-01, 2024-12-31)
    info = tn.normalize_phrase("expiry date")  # → {"maps_to": "valid_until", ...}
"""

from __future__ import annotations

import calendar
import logging
import re
import warnings
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple

from dateutil.relativedelta import relativedelta

from ..utils.exceptions import TemporalAmbiguityWarning

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled regex patterns for structured date formats
# ---------------------------------------------------------------------------

_RE_YEAR_ONLY = re.compile(r"^\s*(\d{4})\s*$")
_RE_MONTH_YEAR_WORD = re.compile(
    r"^\s*(january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\s*$",
    re.IGNORECASE,
)
_RE_YEAR_MONTH_ISO = re.compile(r"^\s*(\d{4})-(\d{1,2})\s*$")
_RE_QUARTER = re.compile(r"^\s*Q([1-4])\s+(\d{4})\s*$", re.IGNORECASE)
_RE_AMBIGUOUS_SLASH = re.compile(r"^\s*\d{1,2}/\d{1,2}/\d{4}\s*$")

_MONTH_NAMES: Dict[str, int] = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_QUARTER_BOUNDS: Dict[int, Tuple[int, int, int, int]] = {
    # quarter → (from_month, from_day, until_month, until_day)
    1: (1, 1, 3, 31),
    2: (4, 1, 6, 30),
    3: (7, 1, 9, 30),
    4: (10, 1, 12, 31),
}


# ---------------------------------------------------------------------------
# Small date-arithmetic helpers
# ---------------------------------------------------------------------------

def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _this_quarter(ref: datetime) -> Tuple[datetime, datetime]:
    q = (ref.month - 1) // 3 + 1
    fm, fd, um, ud = _QUARTER_BOUNDS[q]
    return _utc(ref.year, fm, fd), _utc(ref.year, um, ud)


def _last_quarter(ref: datetime) -> Tuple[datetime, datetime]:
    q = (ref.month - 1) // 3 + 1
    prev_q = q - 1 if q > 1 else 4
    year = ref.year if q > 1 else ref.year - 1
    fm, fd, um, ud = _QUARTER_BOUNDS[prev_q]
    return _utc(year, fm, fd), _utc(year, um, ud)


def _last_month(ref: datetime) -> Tuple[datetime, datetime]:
    first = ref.replace(day=1) - relativedelta(months=1)
    last_day = _last_day_of_month(first.year, first.month)
    return _utc(first.year, first.month, 1), _utc(first.year, first.month, last_day)


# ---------------------------------------------------------------------------
# Default phrase map
# ---------------------------------------------------------------------------
# Keys: lowercase canonical phrases (or regex patterns prefixed with "r:").
# Values: callables (ref: datetime) → (valid_from, valid_until).
#
# Domain-specific terms that carry no self-contained date (e.g. "approval date")
# return (ref, ref) as a placeholder so callers can distinguish
# "known temporal term, date needs context" from "unrecognised phrase".
# ---------------------------------------------------------------------------

def _phrase_entry(maps_to: str, type_: str, **extra: Any) -> Dict[str, Any]:
    return {"maps_to": maps_to, "type": type_, **extra}


# Phrase map entries also carry metadata for normalize_phrase()
_DEFAULT_PHRASE_META: Dict[str, Dict[str, Any]] = {
    # ── Relative references ─────────────────────────────────────────────
    "last year":        _phrase_entry("valid_from", "relative"),
    "this year":        _phrase_entry("valid_from", "relative"),
    "last quarter":     _phrase_entry("valid_from", "relative"),
    "this quarter":     _phrase_entry("valid_from", "relative"),
    "last month":       _phrase_entry("valid_from", "relative"),
    "this month":       _phrase_entry("valid_from", "relative"),
    "three months ago": _phrase_entry("valid_from", "relative"),
    "six months ago":   _phrase_entry("valid_from", "relative"),
    "two years ago":    _phrase_entry("valid_from", "relative"),
    # ── General / Policy ────────────────────────────────────────────────
    "r:effective\\s+(as\\s+of|from|beginning|date)":
        _phrase_entry("valid_from", "start", domain=["General", "Policy"]),
    "in force until":
        _phrase_entry("valid_until", "end", domain=["Policy", "Regulatory"]),
    "retroactive to":
        _phrase_entry("valid_from", "start", retroactive=True, domain=["Regulatory", "Finance"]),
    "sunset clause":
        _phrase_entry("valid_until", "sunset", domain=["Policy"]),
    # ── Healthcare / Drug Discovery ──────────────────────────────────────
    "approval date":
        _phrase_entry("valid_from", "start", domain=["Healthcare", "Drug Discovery"]),
    "expiry date":
        _phrase_entry("valid_until", "end", domain=["Healthcare", "Supply Chain"]),
    "market authorization":
        _phrase_entry("valid_from", "start", domain=["Drug Discovery", "Healthcare"]),
    # ── Cybersecurity ────────────────────────────────────────────────────
    "incident window":
        _phrase_entry("window", "window", domain=["Cybersecurity"]),
    "campaign period":
        _phrase_entry("window", "window", domain=["Cybersecurity"]),
    # ── Supply Chain ─────────────────────────────────────────────────────
    "certification valid through":
        _phrase_entry("valid_until", "end", domain=["Supply Chain"]),
    # ── Finance ──────────────────────────────────────────────────────────
    "trading halt":
        _phrase_entry("window", "window", domain=["Finance"]),
    # ── Energy ───────────────────────────────────────────────────────────
    "commissioned date":
        _phrase_entry("valid_from", "start", domain=["Energy"]),
    "decommissioned date":
        _phrase_entry("valid_until", "end", domain=["Energy"]),
}

# Separate callable map for date resolution (subset of the above)
def _build_default_callable_map() -> Dict[str, Callable[[datetime], Tuple[datetime, datetime]]]:
    return {
        "last year": lambda ref: (
            _utc(ref.year - 1, 1, 1),
            _utc(ref.year - 1, 12, 31),
        ),
        "this year": lambda ref: (
            _utc(ref.year, 1, 1),
            _utc(ref.year, 12, 31),
        ),
        "last quarter": _last_quarter,
        "this quarter": _this_quarter,
        "last month": _last_month,
        "this month": lambda ref: (
            _utc(ref.year, ref.month, 1),
            _utc(ref.year, ref.month, _last_day_of_month(ref.year, ref.month)),
        ),
        "three months ago": lambda ref: (
            (ref - relativedelta(months=3)).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            ((ref - relativedelta(months=3)).replace(day=1) + relativedelta(months=1) - relativedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
        ),
        "six months ago": lambda ref: (
            (ref - relativedelta(months=6)).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            ((ref - relativedelta(months=6)).replace(day=1) + relativedelta(months=1) - relativedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
        ),
        "two years ago": lambda ref: (
            _utc(ref.year - 2, 1, 1),
            _utc(ref.year - 2, 12, 31),
        ),
    }


# ---------------------------------------------------------------------------
# TemporalNormalizer
# ---------------------------------------------------------------------------

class TemporalNormalizer:
    """
    Deterministic resolution of temporal phrases into UTC datetime intervals.

    Zero LLM calls. All resolution is done via regex patterns and Python
    date arithmetic (``dateutil.relativedelta``).

    Args:
        reference_date: Anchor for relative phrases like "last year". When
            ``None`` and a relative phrase is encountered, :meth:`normalize`
            raises :class:`ValueError`.
        phrase_map: Optional dict that extends or overrides the default
            domain phrase map. Keys are lowercase phrases (or regex patterns
            prefixed with ``"r:"``). Values are callables
            ``(reference_date: datetime) -> (start: datetime, end: datetime)``.
    """

    def __init__(
        self,
        reference_date: Optional[datetime] = None,
        phrase_map: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.reference_date = reference_date
        # Build the callable resolution map (relative dates + user overrides)
        self._callable_map: Dict[str, Callable[[datetime], Tuple[datetime, datetime]]] = (
            _build_default_callable_map()
        )
        if phrase_map:
            self._callable_map.update(phrase_map)
        # Phrase metadata map (for normalize_phrase)
        self._phrase_meta: Dict[str, Dict[str, Any]] = {**_DEFAULT_PHRASE_META}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, value: Optional[str]) -> Optional[Tuple[datetime, datetime]]:
        """
        Resolve a temporal string to a ``(valid_from, valid_until)`` interval.

        Resolution order:
        1. ``None`` / empty → ``None``
        2. ISO 8601 full datetime / date → point interval ``(dt, dt)``
        3. Partial date patterns: year-only, month+year, quarter+year
        4. Ambiguous slash-date (``DD/MM/YYYY`` vs ``MM/DD/YYYY``) →
           issues :class:`~veritasreason.utils.exceptions.TemporalAmbiguityWarning`
           and returns ``None``
        5. Phrase map / domain phrase lookup
        6. Relative phrase via callable map (requires ``reference_date``)
        7. Unparseable → ``None`` (debug log, never raises)

        Returns:
            Tuple of UTC datetimes ``(start, end)`` or ``None``.
        """
        if value is None:
            return None
        value_stripped = value.strip()
        if not value_stripped:
            return None

        # 1. ISO 8601 parse
        iso_result = self._try_iso(value_stripped)
        if iso_result is not None:
            return iso_result

        # 2. Partial date patterns
        partial_result = self._try_partial_date(value_stripped)
        if partial_result is not None:
            return partial_result

        # 3. Ambiguous slash date — warn, return None
        if _RE_AMBIGUOUS_SLASH.match(value_stripped):
            warnings.warn(
                f"Temporal expression {value_stripped!r} is ambiguous (day/month ordering unknown). "
                "Provide locale or use ISO 8601 format (YYYY-MM-DD).",
                TemporalAmbiguityWarning,
                stacklevel=2,
            )
            return None

        # 4. Relative phrase / callable map
        callable_result = self._try_callable(value_stripped)
        if callable_result is not None:
            return callable_result

        logger.debug("Could not parse temporal value: %r", value_stripped)
        return None

    def normalize_phrase(self, phrase: str) -> Optional[Dict[str, Any]]:
        """
        Look up a temporal phrase in the domain phrase map.

        Checks exact match first, then regex patterns (keys prefixed with
        ``"r:"``). Returns the metadata dict if matched, ``None`` otherwise.

        Args:
            phrase: Lowercase phrase to look up (case-insensitive internally).

        Returns:
            Dict with at minimum ``{"maps_to": ..., "type": ...}`` or ``None``.
        """
        normalized = phrase.strip().lower()

        # Exact match
        if normalized in self._phrase_meta:
            return self._phrase_meta[normalized]

        # Regex pattern match (keys prefixed with "r:")
        for key, meta in self._phrase_meta.items():
            if key.startswith("r:"):
                pattern = key[2:]
                if re.search(pattern, normalized, re.IGNORECASE):
                    return meta

        logger.debug("Unrecognized temporal phrase: %r", phrase)
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _try_iso(self, value: str) -> Optional[Tuple[datetime, datetime]]:
        """Attempt ISO 8601 parse. Returns point interval on success."""
        normalized = value
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (dt, dt)
        except ValueError:
            return None

    def _try_partial_date(self, value: str) -> Optional[Tuple[datetime, datetime]]:
        """Try partial date patterns: YYYY, Month YYYY, YYYY-MM, Q[1-4] YYYY."""
        # Year only
        m = _RE_YEAR_ONLY.match(value)
        if m:
            year = int(m.group(1))
            return _utc(year, 1, 1), _utc(year, 12, 31)

        # Month YYYY (word)
        m = _RE_MONTH_YEAR_WORD.match(value)
        if m:
            month = _MONTH_NAMES[m.group(1).lower()]
            year = int(m.group(2))
            last = _last_day_of_month(year, month)
            return _utc(year, month, 1), _utc(year, month, last)

        # YYYY-MM (ISO partial)
        m = _RE_YEAR_MONTH_ISO.match(value)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            if 1 <= month <= 12:
                last = _last_day_of_month(year, month)
                return _utc(year, month, 1), _utc(year, month, last)

        # Q[1-4] YYYY
        m = _RE_QUARTER.match(value)
        if m:
            q, year = int(m.group(1)), int(m.group(2))
            fm, fd, um, ud = _QUARTER_BOUNDS[q]
            return _utc(year, fm, fd), _utc(year, um, ud)

        return None

    def _try_callable(self, value: str) -> Optional[Tuple[datetime, datetime]]:
        """Try the relative phrase callable map."""
        key = value.lower()

        # Exact match
        if key in self._callable_map:
            if self.reference_date is None:
                raise ValueError(
                    f"reference_date is required to resolve relative temporal expression: {value!r}"
                )
            return self._callable_map[key](self.reference_date)

        # Regex pattern match (keys prefixed with "r:")
        for map_key, fn in self._callable_map.items():
            if map_key.startswith("r:"):
                pattern = map_key[2:]
                if re.search(pattern, key, re.IGNORECASE):
                    if self.reference_date is None:
                        raise ValueError(
                            f"reference_date is required to resolve relative temporal expression: {value!r}"
                        )
                    return fn(self.reference_date)

        return None
