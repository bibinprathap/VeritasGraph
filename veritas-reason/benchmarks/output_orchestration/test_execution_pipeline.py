from unittest.mock import MagicMock, patch

import pytest

from veritasreason.pipeline.execution_engine import ExecutionEngine
from veritasreason.pipeline.pipeline_builder import PipelineBuilder, StepStatus
from veritasreason.pipeline.resource_scheduler import ResourceScheduler


# ~~ Fixtures
@pytest.fixture(autouse=True)
def kill_hardware_checks():
    with patch.object(ResourceScheduler, "_initialize_resources", return_value=None):
        yield


@pytest.fixture(autouse=True)
def kill_logging():
    with patch("veritasreason.utils.logging.get_logger"):
        yield


@pytest.fixture(autouse=True)
def kill_tracker():
    mock_tracker = MagicMock()
    mock_tracker.enabled = False
    with patch(
        "veritasreason.pipeline.execution_engine.get_progress_tracker",
        return_value=mock_tracker,
    ):
        yield


def create_pipeline(size):
    """Helper to generate pipelines of random size."""
    builder = PipelineBuilder()
    builder.progress_tracker = MagicMock()
    builder.progress_tracker.enabled = False
    handler = lambda x, **k: x

    builder.add_step("start", "dummy", handler=handler)
    for i in range(1, size):
        builder.add_step(f"step_{i}", "dummy", handler=handler)
        builder.connect_steps("start" if i == 1 else f"step_{i-1}", f"step_{i}")

    return builder.build(f"bench_pipe_{size}")


# ~~ Benchmarks ~~


@pytest.mark.parametrize("step_count", [10, 100, 500])
def test_pipeline_construction_scaling(benchmark, step_count):
    """
    Verifies if construction time scales linearly.
    """

    def op():
        builder = PipelineBuilder()
        builder.progress_tracker = MagicMock()
        for i in range(step_count):
            builder.add_step(f"s{i}", "t")
        return builder.build()

    benchmark.pedantic(op, iterations=5, rounds=5)


@pytest.mark.parametrize("step_count", [10, 100])
def test_execution_overhead_scaling(benchmark, step_count):
    """
    Measures per-step overhead as it gets more complex
    """
    engine = ExecutionEngine()
    pipeline = create_pipeline(step_count)

    def setup_run():
        for step in pipeline.steps:
            step.status = StepStatus.PENDING
            step.result = None
        return (pipeline,), {"data": {"val": 1}}

    def op(pipeline, data):
        return engine.execute_pipeline(pipeline, data=data)

    benchmark.pedantic(op, setup=setup_run, iterations=1, rounds=10)


@pytest.mark.parametrize("step_count", [10, 100, 1000])
def test_topological_sort_scaling(benchmark, step_count):
    """
    Stress test for dependency graph algorithm.
    """
    engine = ExecutionEngine()
    pipeline = create_pipeline(step_count)

    benchmark.pedantic(
        lambda: engine._topological_sort(pipeline.steps), iterations=20, rounds=10
    )
