from dataclasses import dataclass, field
from typing import Any, Dict, List
from unittest.mock import patch

import numpy as np
import pytest

from veritasreason.context.agent_context import AgentContext
from veritasreason.context.agent_memory import AgentMemory
from veritasreason.context.context_graph import ContextGraph
from veritasreason.context.context_retriever import ContextRetriever, RetrievedContext
from veritasreason.context.entity_linker import EntityLinker

# Infra


class NullTracker:
    """
    Stateless dummy tracker.
    """

    def start_tracking(self, *args, **kwargs):
        return "dummy_id"

    def update_tracking(self, *args, **kwargs):
        pass

    def stop_tracking(self, *args, **kwargs):
        pass

    def register_pipeline_modules(self, *args, **kwargs):
        pass

    def clear_pipeline_context(self, *args, **kwargs):
        pass

    def update_progress(self, *args, **kwargs):
        pass

    @property
    def enabled(self):
        return False

    @enabled.setter
    def enabled(self, value):
        pass


# ~~ MOCK STORES ~~


class MockVectorStore:
    """
    A feather VectorStore sim that does no math.
    We want to measure the MANAGER overhead.
    """

    def __init__(self):
        self.vectors = {}
        self.dim = 384

    def embed(self, text):
        return np.random.rand(self.dim).tolist()

    def add(self, items):
        for item in items:
            self.vectors[item.memory_id] = item

    def search(self, query, limit=5):
        class MockResult:
            def __init__(self, i):
                self.id = f"mem_{i}"
                self.content = f"Content for result {i} matching {query[:10]}"
                self.score = 0.9 - (i * 0.05)
                self.metadata = {"type": "test"}

        return [MockResult(i) for i in range(limit)]


def create_dense_graph(node_count):
    """
    Creates a ContextGraph with 'Small World' Topology.
    Used to stress-test BFS traversal scaling.
    """
    graph = ContextGraph()

    graph.progress_tracker = NullTracker()

    # Create nodes
    nodes = [
        {
            "id": f"node_{i}",
            "type": "concept",
            "properties": {"content": f"Concept {i}"},
        }
        for i in range(node_count)
    ]
    graph.add_nodes(nodes)

    # Create Edges (Chain + Hub + Random)
    edges = []
    for i in range(node_count):
        # Chain
        if i < node_count - 1:
            edges.append(
                {"source_id": f"node_{i}", "target_id": f"node_{i+1}", "type": "next"}
            )
        # Hub
        if i > 0:
            edges.append(
                {"source_id": "node_0", "target_id": f"node_{i}", "type": "hub_link"}
            )
        # Rando
        if i % 5 == 0 and i + 5 < node_count:
            edges.append(
                {
                    "source_id": f"node_{i}",
                    "target_id": f"node_{i+5}",
                    "type": "cross_link",
                }
            )

    graph.add_edges(edges)
    return graph


def create_populated_memory(item_count):
    """Creates an AgentMemory populated with N items."""
    vs = MockVectorStore()
    memory = AgentMemory(vector_store=vs)
    memory.progress_tracker = NullTracker()

    for i in range(item_count):
        mem_id = f"setup_mem_{i}"
        from datetime import datetime

        from veritasreason.context.agent_memory import MemoryItem

        memory.memory_items[mem_id] = MemoryItem(
            content=f"History item {i}",
            timestamp=datetime.now(),
            memory_id=mem_id,
            metadata={"type": "chat"},
        )
        memory.memory_index.append(mem_id)

    return memory


# ~~ BENCHMARKS ~~


@pytest.mark.parametrize("graph_size", [100, 1000])
@pytest.mark.parametrize("hops", [1, 2])
def test_graph_traversal_scaling(benchmark, graph_size, hops):
    """
    Measures 'Hop Explosion' effect.
    Retrieving multi-hop neighbors on a dense graph.
    """
    graph = create_dense_graph(graph_size)

    def op():
        # Start from'Hub' node which's celebrity, meaning
        # connected to everyone
        return graph.get_neighbors("node_0", hops=hops)

    benchmark.pedantic(op, iterations=5, rounds=5)


@pytest.mark.parametrize("memory_count", [100, 1000])
def test_retriever_ranking_throughput(benchmark, memory_count):
    """
    Measures CPU cost of merging and ranking results.
    """
    retriever = ContextRetriever(
        vector_store=MockVectorStore(),
        memory_store=create_populated_memory(10),
        knowledge_graph=None,
        hybrid_alpha=0.5,
    )
    retriever.progress_tracker = NullTracker()

    results = []
    for i in range(memory_count):
        results.append(
            RetrievedContext(
                content=f"Vector Item {i}",
                score=np.random.random(),
                source=f"vector:{i}",
            )
        )
        results.append(
            RetrievedContext(
                content=f"Graph Item {i}",
                score=np.random.random(),
                source=f"graph:{i}",
                metadata={"node_id": f"node_{i}"},
            )
        )

    def op():
        return retriever._rank_and_merge(results, "query context")

    benchmark.pedantic(op, iterations=5, rounds=10)


@pytest.mark.parametrize("registry_size", [100, 1000])
def test_entity_linking_speed(benchmark, registry_size):
    """
    Measures O(N) linear scan speed in `find_similar_entities`.
    """
    linker = EntityLinker()
    linker.progress_tracker = NullTracker()

    mock_kg = {"entities": []}
    for i in range(registry_size):
        mock_kg["entities"].append(
            {"id": f"ent_{i}", "text": f"Entity Number {i}", "type": "TEST"}
        )
    linker.knowledge_graph = mock_kg

    input_text = "I am looking for Entity Number 50 in the database."

    def op():
        return linker.find_similar_entities(input_text, threshold=0.1)

    benchmark.pedantic(op, iterations=5, rounds=5)


@pytest.mark.parametrize("batch_size", [1, 10, 50])
def test_agent_store_throughput(benchmark, batch_size):
    """
    'store' pipeline test.
    """
    vs = MockVectorStore()
    context = AgentContext(vector_store=vs)
    context._memory.progress_tracker = NullTracker()

    inputs = [f"Memory item {i} for storage test" for i in range(batch_size)]

    def op():
        return context.batch_store(inputs)

    benchmark.pedantic(op, iterations=5, rounds=5)
