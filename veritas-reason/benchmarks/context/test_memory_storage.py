import pytest

from veritasreason.context.agent_memory import AgentMemory


@pytest.mark.benchmark(group="memory_io")
def test_memory_storage_overhead(benchmark, mock_vector_store):
    """
    Benchmarks storing a memory item.
    """
    memory = AgentMemory(vector_store=mock_vector_store)
    content = "This is nothing burger for benchmarking this memory thingy."
    metadata = {"type": "conversation", "user": "u_1"}

    def run():
        return memory.store(content, metadata=metadata)

    benchmark.pedantic(run, iterations=10, rounds=10)


@pytest.mark.benchmark(group="memory_io")
def test_short_term_pruning(benchmark, mock_vector_store):
    """
    Benchmarks the pruning logic when short-term memory
    limit is hit.
    """

    def setup_overfilled_memory():
        memory = AgentMemory(vector_store=mock_vector_store, short_term_limit=50)
        # Pre-fill
        for i in range(55):
            memory.store(f"filler memory {i}")
        return (memory,), {}

    def run_prune(mem_instance):
        mem_instance.store("Trigger Pruning")

    benchmark.pedantic(
        target=run_prune, setup=setup_overfilled_memory, iterations=1, rounds=20
    )
