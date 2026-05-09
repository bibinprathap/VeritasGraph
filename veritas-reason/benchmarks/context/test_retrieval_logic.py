import pytest

from veritasreason.context.agent_memory import AgentMemory
from veritasreason.context.context_retriever import ContextRetriever, RetrievedContext


@pytest.mark.benchmark(group="rag_logic")
def test_hybrid_ranking_overhead(benchmark, retriever_setup):
    """
    Benchmarks the CPU cost of the 'rank_and_merge' logic.
    """

    query = "test_query"

    # Dummy results to sim inputs
    raw_results = [
        RetrievedContext(content=f"Vec {i}", score=0.9 - i * 0.01, source="vector:x")
        for i in range(10)
    ] + [
        RetrievedContext(content=f"Graph {i}", score=0.8 - i * 0.01, source="graph:y")
        for i in range(10)
    ]

    def run():
        return retriever_setup._rank_and_merge(raw_results, query)

    benchmark.pedantic(run, iterations=10, rounds=20)


@pytest.mark.benchmark(group="rag_logic")
@pytest.mark.parametrize("use_graph", [True, False])
def test_full_retrieval_pipeline(benchmark, retriever_setup, use_graph):
    """
    Benchmarks the orchestration of the retrieve() method.
    """

    def run():
        return retriever_setup.retrieve(
            "Node content", max_results=10, use_graph_expansion=use_graph, max_hops=1
        )

    benchmark.pedantic(run, iterations=1, rounds=5)
