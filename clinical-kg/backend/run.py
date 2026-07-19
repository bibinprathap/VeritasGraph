#!/usr/bin/env python
"""Convenience launcher for the clinical-kg API.

    python run.py            # serves on http://127.0.0.1:8300
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("CKG_PORT", "8300"))
    uvicorn.run("clinical_kg.api:app", host="127.0.0.1", port=port, log_level="info")
