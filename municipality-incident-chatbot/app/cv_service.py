"""Computer-vision validation service (Validation Layer).

Implements the two-stage CV design from ``02_why_this_architecture.md`` §3:

* a **detector** (YOLO) answering *"what objects are present"*, and
* a **verifier** (VLM) answering *"does this image depict the claimed problem"*.

Two backends are provided:

* :class:`SimulatedBackend` — deterministic, offline. Detections come from a
  ``<image>.cv.json`` sidecar if present, otherwise from tokens in the file
  name. This lets the whole pipeline (and the test suite) run without GPUs,
  model weights, or network access.
* :class:`YoloBackend` — real object detection via ``ultralytics`` (opt-in with
  ``MUNI_CV_BACKEND=yolo``). COCO classes are mapped onto municipal CV labels.

Both backends honour the same contract (see ``03_how_to_modify.md`` §2), so the
rest of the system never changes when you swap models.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: List[float] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"label": self.label, "confidence": round(self.confidence, 4), "bbox": self.bbox}


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #
class SimulatedBackend:
    """Deterministic detector for offline runs and tests."""

    name = "sim"

    def detect(self, image_path: str, candidate_labels: List[str]) -> List[Detection]:
        # 1) Sidecar file wins (lets callers/tests script exact detections).
        sidecar = Path(f"{image_path}.cv.json")
        if sidecar.is_file():
            try:
                data = json.loads(sidecar.read_text())
                return [
                    Detection(d["label"], float(d.get("confidence", 0.9)), d.get("bbox", []))
                    for d in data.get("detections", [])
                ]
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        # 2) Infer from file-name tokens (e.g. "garbage_overflow_01.jpg").
        stem = Path(image_path).name.lower()
        detections: List[Detection] = []
        for label in candidate_labels:
            token = str(label).lower()
            if token and token.replace("_", "") in stem.replace("_", "").replace("-", ""):
                detections.append(Detection(token, 0.9, [0, 0, 100, 100]))
        return detections


class YoloBackend:
    """Real YOLO detector (ultralytics). COCO labels -> municipal labels."""

    name = "yolo"

    # Map municipal CV labels to the COCO classes YOLO knows.
    _COCO_ALIASES = {
        "car": {"car"}, "truck": {"truck"}, "bus": {"bus"},
        "motorcycle": {"motorcycle"}, "person": {"person"}, "crowd": {"person"},
        # trash/garbage have no COCO class -> require the VLM verifier or a
        # custom-trained detector (see 03_how_to_modify.md §2).
    }

    def __init__(self, weights: str = config.YOLO_WEIGHTS) -> None:
        from ultralytics import YOLO  # imported lazily; heavy dependency

        self._model = YOLO(weights)

    def detect(self, image_path: str, candidate_labels: List[str]) -> List[Detection]:
        results = self._model(image_path, verbose=False)
        wanted = {c.lower() for c in candidate_labels}
        coco_wanted = set()
        for label in wanted:
            coco_wanted |= self._COCO_ALIASES.get(label, {label})
        detections: List[Detection] = []
        for res in results:
            names = res.names
            for box in res.boxes:
                coco = names[int(box.cls)].lower()
                if coco in coco_wanted:
                    # Report using the municipal label the caller asked for.
                    muni = next(
                        (m for m in wanted if coco in self._COCO_ALIASES.get(m, {m})),
                        coco,
                    )
                    detections.append(
                        Detection(muni, float(box.conf), [float(x) for x in box.xywh[0]])
                    )
        return detections


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #
class VisionService:
    """Detector + verifier facade used by the orchestrator."""

    def __init__(self, backend: Optional[Any] = None) -> None:
        self.backend = backend or self._make_backend()

    @staticmethod
    def _make_backend() -> Any:
        if config.CV_BACKEND == "yolo":
            try:
                return YoloBackend()
            except Exception:  # noqa: BLE001 - ultralytics/weights missing
                # Fall back so the system degrades gracefully instead of failing.
                return SimulatedBackend()
        return SimulatedBackend()

    @property
    def vlm_available(self) -> bool:
        # The simulated verifier is always available; a real VLM would be
        # probed here (see 03_how_to_modify.md §2).
        return True

    def analyze(self, image_path: str, candidate_labels: List[str]) -> List[Detection]:
        """Stage 1 — object detection."""
        if not image_path or not os.path.exists(image_path):
            return []
        return self.backend.detect(image_path, list(candidate_labels))

    def verify_claim(
        self, image_path: str, incident_label: str,
        detections: List[Detection], cv_labels: List[str],
    ) -> float:
        """Stage 2 — VLM claim verification.

        Simulated: high confidence when the detector found an object matching the
        category, low otherwise. A real VLM would receive the image + the claim
        prompt and return a grounded confidence.
        """
        wanted = {c.lower() for c in cv_labels}
        matched = [d for d in detections if d.label.lower() in wanted]
        if not matched:
            return 0.2
        return min(0.95, 0.6 + 0.35 * max(d.confidence for d in matched))
