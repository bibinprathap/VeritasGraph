from unittest.mock import MagicMock, patch

import pytest

from veritasreason.deduplication.merge_strategy import MergeStrategy, MergeStrategyManager

# Fixtures


@pytest.fixture
def conflict_manager():
    """Returns a MergeStrategyManager with default settings."""
    return MergeStrategyManager()


@pytest.fixture
def conflicting_entities_batch():
    """
    Generates a list of 100 entities that are all 'duplicates' of each other
    but have conflicting property values. This forces the resolution logic to run hard.
    """
    entities = []
    for i in range(100):
        entities.append(
            {
                "id": "e_1",
                "name": f"Entity Name {i}",
                "type": "Person",
                "confidence": 0.5 + (i * 0.005),
                "properties": {
                    "age": 20 + i,
                    "email": f"user{i}@example.com",
                    "status": "active" if i % 2 == 0 else "inactive",
                },
                "relationships": [
                    {"source": "e_1", "target": f"other_{i}", "type": "knows"}
                ],
            }
        )
    return entities


# Benchmarks


def test_strategy_keep_highest_confidence(
    benchmark, conflict_manager, conflicting_entities_batch
):
    """
    Benchmarks 'KEEP_HIGHEST_CONFIDENCE'.
    """

    def op():
        return conflict_manager.merge_entities(
            conflicting_entities_batch, strategy=MergeStrategy.KEEP_HIGHEST_CONFIDENCE
        )

    benchmark.pedantic(op, iterations=10, rounds=10)


def test_strategy_merge_all(benchmark, conflict_manager, conflicting_entities_batch):
    """
    Benchmarks 'MERGE_ALL'.
    """

    def op():
        return conflict_manager.merge_entities(
            conflicting_entities_batch, strategy=MergeStrategy.MERGE_ALL
        )

    benchmark.pedantic(op, iterations=10, rounds=10)


def test_property_resolution_overhead(benchmark, conflict_manager):
    """
    Micro-benchmark for the inner _resolve_property_conflict logic.
    """

    def op():
        return conflict_manager._resolve_property_conflict(
            "age", 25, 30, MergeStrategy.KEEP_MOST_COMPLETE
        )

    benchmark.pedantic(op, iterations=1000, rounds=20)
