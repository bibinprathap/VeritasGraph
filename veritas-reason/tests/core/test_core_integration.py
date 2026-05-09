import pytest

from veritasreason.core import VeritasReason
from veritasreason.core.methods import (
    initialize_framework,
    get_status,
    run_pipeline,
    build_knowledge_base,
)


pytestmark = pytest.mark.integration


class DummyPipeline:
    def __init__(self):
        self.executed_with = None

    def execute(self, data):
        self.executed_with = data
        return {"value": data}


def test_initialize_and_get_status_integration():
    framework = initialize_framework()
    status = get_status(framework=framework, method="summary")
    assert status["state"] in {"ready", "running", "initializing"}
    assert "health" in status
    framework.shutdown(graceful=True)


def test_veritasreason_run_pipeline_with_dummy_pipeline():
    pipeline = DummyPipeline()
    framework = VeritasReason()
    framework.initialize()
    data = {"input": "value"}
    result = framework.run_pipeline(pipeline, data)
    assert result["success"] is True
    assert result["output"] == {"value": data}
    assert pipeline.executed_with == data
    framework.shutdown(graceful=True)


def test_core_methods_run_pipeline_with_dummy_pipeline():
    pipeline = DummyPipeline()
    data = "sample"
    result = run_pipeline(pipeline, data)
    assert result["success"] is True
    assert result["output"] == {"value": data}


def test_framework_build_knowledge_base_end_to_end(tmp_path):
    source_path = tmp_path / "sample_e2e_framework.txt"
    source_path.write_text("Apple Inc. is a technology company.")
    framework = VeritasReason()
    result = framework.build_knowledge_base(
        sources=[str(source_path)],
        embeddings=False,
        graph=False,
        pipeline={
            "name": "e2e_pipeline",
            "steps": [
                {"name": "step1", "type": "default", "config": {}},
            ],
        },
    )
    stats = result["statistics"]
    assert stats["sources_processed"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is True
    framework.shutdown(graceful=True)


def test_core_methods_build_knowledge_base_end_to_end(tmp_path):
    source_path = tmp_path / "sample_e2e_core_methods.txt"
    source_path.write_text("Tim Cook leads Apple.")
    result = build_knowledge_base(
        sources=str(source_path),
        method="minimal",
        embeddings=False,
        graph=False,
        pipeline={"steps": ["step1", "step2"]},
    )
    stats = result["statistics"]
    assert stats["sources_processed"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is True



