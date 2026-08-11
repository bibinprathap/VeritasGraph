"""Evidence fusion & scoring (Validation Layer).

Combines the CV signals, the VLM verification, external corroboration and the
location match into a single, tunable **validation score**, then maps it to an
outcome (see the README validation table and ``02_why_this_architecture.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import config
from .cv_service import Detection
from .external_sources import Corroboration


@dataclass
class FusionResult:
    score: float
    outcome: str
    reasons: List[str] = field(default_factory=list)
    signals: Dict[str, float] = field(default_factory=dict)


def _location_signal(location: Optional[Dict[str, Any]]) -> float:
    if not location:
        return 0.0
    if location.get("lat") is not None and location.get("lon") is not None:
        return 1.0
    if location.get("zone") or location.get("text"):
        return 0.5
    return 0.0


def fuse(
    incident_code: str,
    cv_labels: List[str],
    detections: List[Detection],
    vlm_confidence: float,
    location: Optional[Dict[str, Any]],
    corroboration: Corroboration,
    *,
    vlm_available: bool = True,
) -> FusionResult:
    """Fuse all evidence into a validation score and outcome."""
    wanted = {c.lower() for c in cv_labels}
    photo_cv = max(
        (d.confidence for d in detections if d.label.lower() in wanted),
        default=0.0,
    )
    signals = {
        "citizen_photo_cv": photo_cv,
        "vlm_verify": vlm_confidence,
        "cctv_cv": corroboration.cctv_confidence or 0.0,
        "sensor_telemetry": corroboration.sensor_signal or 0.0,
        "location_match": _location_signal(location),
    }

    w = config.FUSION_WEIGHTS
    score = sum(w[k] * signals[k] for k in w)

    reasons: List[str] = []
    if photo_cv > 0:
        reasons.append(f"Photo shows expected objects (conf {photo_cv:.2f}).")
    else:
        reasons.append("Photo did not clearly show the reported objects.")
    reasons.append(f"Claim verification confidence {vlm_confidence:.2f}.")
    reasons.extend(corroboration.details)

    # --- Graceful-degradation caps -----------------------------------------
    if not corroboration.available():
        score = min(score, config.CAP_NO_CORROBORATION)
        reasons.append("No external corroboration available — capped at needs-review.")
    if not vlm_available:
        score = min(score, config.CAP_YOLO_ONLY)
        reasons.append("VLM verifier unavailable — detector-only score capped.")

    if score >= config.THRESHOLD_AUTO:
        outcome = config.Outcome.AUTO_VALIDATED
    elif score >= config.THRESHOLD_REVIEW:
        outcome = config.Outcome.NEEDS_REVIEW
    else:
        outcome = config.Outcome.REJECTED

    return FusionResult(round(score, 4), outcome, reasons, {k: round(v, 4) for k, v in signals.items()})
