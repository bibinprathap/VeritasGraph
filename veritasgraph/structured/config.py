from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import List, Optional


def dsn() -> Optional[str]:
    value = os.environ.get("VG_STRUCTURED_DSN", "").strip()
    return value or None


def enabled() -> bool:
    return dsn() is not None


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, "").strip() or default)


def row_cap() -> int:
    return _int("VG_STRUCTURED_ROW_CAP", 1000)


def statement_timeout_s() -> int:
    return _int("VG_STRUCTURED_STATEMENT_TIMEOUT_S", 30)


def sample_rows() -> int:
    return _int("VG_STRUCTURED_SAMPLE_ROWS", 50)


def auto_migrate() -> bool:
    return os.environ.get("VG_STRUCTURED_AUTO_MIGRATE", "1").strip() != "0"


def allowed_networks() -> List[ipaddress._BaseNetwork]:
    raw = os.environ.get("VG_STRUCTURED_ALLOWED_NETWORKS", "")
    return [ipaddress.ip_network(x.strip(), strict=False) for x in raw.split(",") if x.strip()]


def file_root() -> Optional[Path]:
    raw = os.environ.get("VG_STRUCTURED_FILE_ROOT", "").strip()
    return Path(raw).resolve() if raw else None


def ask_min_similarity() -> float:
    return float(os.environ.get("VG_ASK_MIN_SIMILARITY", "0.5"))


def ask_coverage_enabled() -> bool:
    return os.environ.get("VG_ASK_COVERAGE", "on").strip().lower() != "off"
