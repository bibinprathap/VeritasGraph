"""Central configuration: paths, fusion weights, thresholds.

Everything here is data/config so it can be tuned without touching logic
(see ``03_how_to_modify.md`` §6).
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent

# Isolated data dir so the municipality graph never clobbers the Studio graph.
DATA_DIR = Path(os.getenv("MUNI_DATA_DIR", str(PROJECT_ROOT / "data")))

# --------------------------------------------------------------------------- #
# LLM (VeritasGraph uses Ollama by default for grounded generation).
# The knowledge-graph routing in this app is deterministic and does NOT require
# an LLM; the model is only used if you enable LLM-generated answers.
# --------------------------------------------------------------------------- #
LLM_MODEL = os.getenv("VERITASGRAPH_MODEL", "qwen3:latest")
USE_LLM_ANSWERS = os.getenv("MUNI_USE_LLM", "0").strip() in {"1", "true", "yes"}

# --------------------------------------------------------------------------- #
# Computer-vision backend: "sim" (deterministic, offline) or "yolo".
# --------------------------------------------------------------------------- #
CV_BACKEND = os.getenv("MUNI_CV_BACKEND", "sim").strip().lower()
YOLO_WEIGHTS = os.getenv("MUNI_YOLO_WEIGHTS", "yolov8n.pt")

# --------------------------------------------------------------------------- #
# Evidence-fusion weights (see 02_why_this_architecture.md).
# --------------------------------------------------------------------------- #
FUSION_WEIGHTS = {
    "citizen_photo_cv": 0.35,  # object detection on the citizen's photo
    "vlm_verify": 0.15,        # vision-language "does it show the claim" check
    "cctv_cv": 0.25,           # detection on a corroborating CCTV frame
    "sensor_telemetry": 0.15,  # IoT sensor signal (e.g. bin fill level)
    "location_match": 0.10,    # GPS / jurisdiction match
}

# Validation-score thresholds -> outcome.
THRESHOLD_AUTO = float(os.getenv("MUNI_THRESHOLD_AUTO", "0.75"))
THRESHOLD_REVIEW = float(os.getenv("MUNI_THRESHOLD_REVIEW", "0.45"))

# Score caps for graceful degradation.
CAP_NO_CORROBORATION = 0.65  # applied when no CCTV/sensor evidence is available
CAP_YOLO_ONLY = 0.75         # applied when the VLM verifier is unavailable

# Duplicate detection window (hours) for same category at same location.
DEDUP_WINDOW_HOURS = 24


class Outcome:
    """Validation outcomes (see README validation table)."""

    AUTO_VALIDATED = "AUTO_VALIDATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"
