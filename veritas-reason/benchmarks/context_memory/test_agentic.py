from unittest.mock import MagicMock, patch

import pytest

from veritasreason.context.agent_context import AgentContext
from veritasreason.context.context_retriever import RetrievedContext

# Fixtures


@pytest.fixture
def mock_agent_context():
    """
    Creates an AgentContext with mocked internals.
    """
    vector_store = MagicMock()
    knowledge_graph = MagicMock()

    with patch("veritasreason.context.agent_context.AgentMemory") as MockMemory, patch(
        "veritasreason.context.agent_context.ContextRetriever"
    ) as MockRetriever:

        ctx = AgentContext(vector_store=vector_store, knowledge_graph=knowledge_graph)

        # Internal mocks

        ctx._memory = MockMemory.return_value
        ctx._retriever = MockRetriever.return_value

        return ctx


# Benchmarks


def test_router_overhead(benchmark, mock_agent_context):
    """
    Benchmarks the logic that decides between Vector vs Graph retrieval.
    """

    mock_agent_context._retriever.retrieve.return_value = []

    def op():
        return mock_agent_context.retrieve("test query", use_graph=None)

    benchmark.pedantic(op, iterations=50, rounds=20)


def test_result_conversion_throughput(benchmark, mock_agent_context):
    """
    Benchmarks converting internal RetrievedContext objects to Dicts.
    """

    fake_results = [
        RetrievedContext(
            content=f"Result {i}",
            score=0.9,
            source="graph:node_1",
            metadata={"type": "fact"},
            related_entities=[{"id": "e1", "name": "Entity"}],
            related_relationships=[{"source": "e1", "target": "e2"}],
        )
        for i in range(100)
    ]
    mock_agent_context._retriever.retrieve.return_value = fake_results

    def op():
        return mock_agent_context.retrieve("test", use_graph=True)

    benchmark.pedantic(op, iterations=20, rounds=10)


def test_store_orchestration_overhead(benchmark, mock_agent_context):
    """
    Benchmarks the 'store' method's logic for routing documents.
    """
    docs = [{"content": f"Doc {i}", "metadata": {"id": i}} for i in range(50)]

    # Mock the internal storage to return immediately
    mock_agent_context._memory.store.return_value = "mem_id"
    mock_agent_context._build_graph_from_documents = MagicMock(return_value={})

    def op():
        return mock_agent_context.store(docs, extract_entities=False)

    benchmark.pedantic(op, iterations=10, rounds=10)
