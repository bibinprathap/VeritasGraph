import time
from unittest.mock import MagicMock, patch

import pytest

from veritasreason.pipeline.parallelism_manager import ParallelismManager, Task
from veritasreason.pipeline.resource_scheduler import ResourceScheduler


# ~~ Fixtures ~~
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
        "veritasreason.pipeline.parallelism_manager.get_progress_tracker",
        return_value=mock_tracker,
    ):
        yield


def blocking_task(duration):
    """Simulates a task that waits for I/O (like a DB query or API call)."""
    time.sleep(duration)
    return True


@pytest.fixture
def thread_manager():
    return ParallelismManager(max_workers=4, use_processes=False)


@pytest.fixture
def process_manager():
    return ParallelismManager(max_workers=4, use_processes=True)


# ~~ BENCHMARKS ~~


def test_parallel_vs_serial_io(benchmark, thread_manager):
    """
    Runs 4 tasks that sleep for 0.1s.
    """
    tasks = [
        Task(task_id=f"t{i}", handler=blocking_task, args=(0.1,)) for i in range(4)
    ]

    def op():
        return thread_manager.execute_parallel(tasks)

    benchmark.pedantic(op, iterations=1, rounds=5)


def test_thread_pool_overhead(benchmark, thread_manager):
    """
    Measures the raw cost of spinning up threads for zero-work tasks.
    """
    # No-op handler
    noop = lambda: None
    tasks = [Task(task_id=f"t{i}", handler=noop) for i in range(100)]

    def op():
        return thread_manager.execute_parallel(tasks)

    benchmark.pedantic(op, iterations=5, rounds=10)


def test_process_pool_overhead(benchmark, process_manager):
    """
    Measures overhead of ProcessPoolExecutor
    """
    noop = lambda: None
    tasks = [Task(task_id=f"t{i}", handler=noop) for i in range(10)]

    def op():
        return process_manager.execute_parallel(tasks)

    benchmark.pedantic(op, iterations=1, rounds=5)
