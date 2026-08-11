"""Case registration service + duplicate detection (Services & Data Layer).

Persists cases to a local JSON store (the "system of record" stand-in). Swap
:class:`CaseService` for a ServiceNow / Dynamics adapter behind the same
interface without touching the orchestrator (see ``03_how_to_modify.md`` §7).
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config


def _geo_key(location: Optional[Dict[str, Any]]) -> str:
    """Coarse location key used for duplicate detection."""
    if not location:
        return "unknown"
    if location.get("lat") is not None and location.get("lon") is not None:
        # ~100m bucket (3 decimal places).
        return f"{round(float(location['lat']), 3)},{round(float(location['lon']), 3)}"
    return str(location.get("zone") or location.get("text") or "unknown").lower()


class CaseService:
    def __init__(self, store_path: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self.store_path = store_path or (config.DATA_DIR / "cases.json")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._cases: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if self.store_path.is_file():
            try:
                return json.loads(self.store_path.read_text())
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self) -> None:
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._cases, indent=2))
        tmp.replace(self.store_path)

    # ------------------------------------------------------------------ #
    def find_duplicate(
        self, incident_code: str, location: Optional[Dict[str, Any]],
        window_hours: int = config.DEDUP_WINDOW_HOURS,
    ) -> Optional[Dict[str, Any]]:
        key = _geo_key(location)
        if key == "unknown":
            return None
        cutoff = time.time() - window_hours * 3600
        with self._lock:
            for case in reversed(self._cases):
                if (
                    case["incident_code"] == incident_code
                    and case["location_key"] == key
                    and case["created_at"] >= cutoff
                    and case["status"] != config.Outcome.REJECTED
                ):
                    return case
        return None

    def register(
        self,
        incident_code: str,
        department: str,
        location: Optional[Dict[str, Any]],
        outcome: str,
        validation_score: float,
        evidence: Dict[str, Any],
        reporter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            year = time.strftime("%Y")
            seq = len(self._cases) + 1
            case = {
                "id": f"MUN-{year}-{seq:06d}",
                "incident_code": incident_code,
                "department": department,
                "location": location,
                "location_key": _geo_key(location),
                "status": outcome,
                "validation_score": validation_score,
                "evidence": evidence,
                "reporter": reporter or None,
                "created_at": time.time(),
            }
            self._cases.append(case)
            self._save()
            return case

    def get(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return next((c for c in self._cases if c["id"] == case_id), None)

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._cases)

    def clear(self) -> None:
        """Remove all cases (used by the demo/E2E reset endpoint)."""
        with self._lock:
            self._cases = []
            self._save()
