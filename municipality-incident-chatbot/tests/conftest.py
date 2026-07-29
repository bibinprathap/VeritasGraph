"""Test fixtures for the municipality chatbot.

Isolates the VeritasGraph snapshot into a temp dir BEFORE the app (and thus the
engine) is imported, so tests never touch real Studio/municipality data.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 1) Isolate data dir before any app import triggers the engine module.
_TMP_DATA = Path(tempfile.mkdtemp(prefix="muni-test-"))
os.environ["MUNI_DATA_DIR"] = str(_TMP_DATA)
os.environ["MUNI_CV_BACKEND"] = "sim"

# 2) Make the standalone app package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from app.case_service import CaseService  # noqa: E402
from app.cv_service import VisionService, SimulatedBackend  # noqa: E402
from app.external_sources import ExternalSources  # noqa: E402
from app.knowledge_graph import MunicipalKnowledgeGraph  # noqa: E402
from app.orchestrator import IncidentChatbot  # noqa: E402


@pytest.fixture(scope="session")
def kg() -> MunicipalKnowledgeGraph:
    return MunicipalKnowledgeGraph()


@pytest.fixture
def cases(tmp_path) -> CaseService:
    return CaseService(store_path=tmp_path / "cases.json")


@pytest.fixture
def vision() -> VisionService:
    return VisionService(backend=SimulatedBackend())


@pytest.fixture
def chatbot(kg, cases, vision) -> IncidentChatbot:
    return IncidentChatbot(
        kg=kg, vision=vision, external=ExternalSources(), cases=cases
    )


@pytest.fixture
def make_photo(tmp_path):
    """Create a fake photo file with a scripted CV-detection sidecar."""

    def _make(name: str, detections):
        img = tmp_path / name
        img.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
        sidecar = tmp_path / f"{name}.cv.json"
        sidecar.write_text(
            __import__("json").dumps({"detections": detections})
        )
        return str(img)

    return _make
