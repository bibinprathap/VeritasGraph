import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from veritasreason.triplet_store.bulk_loader import BulkLoader
from veritasreason.triplet_store.jena_store import JenaStore
from veritasreason.triplet_store.triplet_store import TripletStore

# ~~ Mocking ~~
# We basically define a facile Triplet class for creating ds devoid of fat AI models


@dataclass
class SimpleTriplet:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0


# ~~ Fixtures ~~
@pytest.fixture
def triplet_batch():
    """Generates 1000 triplets."""
    return [
        SimpleTriplet(
            subject=f"http://gandhara.org/entity/{i}",
            predicate="http://gandhara.org/relation/knows",
            object=f"http://example.org/entity/{i+1}",
        )
        for i in range(1000)
    ]


@pytest.fixture
def large_knowledge_graph_dict():
    """
    Generates a large dict (1000 ent) to test parsing
    logic in `TripletStore.store()`
    """
    entities = [
        {
            "id": f"ent_{i}",
            "type": "Person",
            "properties": {"name": f"Person {i}", "age": 60},
        }
        for i in range(1000)
    ]
    relationships = [
        {"source": f"ent_{i}", "target": f"ent_{i+1}", "type": "KNOWS"}
        for i in range(999)
    ]

    return {"entities": entities, "relationships": relationships}


@pytest.fixture
def in_memory_store():
    """Returns a real JenaStore using RDFLib (In-Mmeory)."""

    store = JenaStore(endpoint=None)
    if store.graph is None:
        pytest.fail("JenaStore failed to initialize rdflib graph.")
    if hasattr(store, "progress_tracker"):
        store.progress_tracker = MagicMock()

    return store


# ~~ Benchmarks ~~


def test_rdflib_insert_throughput(benchmark, in_memory_store, triplet_batch):
    """
    Benchmarks raw Write Speed to in-memory RDF graph.
    Is our baseline
    """

    def op():
        in_memory_store.add_triplets(triplet_batch)

    benchmark(op)

    assert len(in_memory_store.graph) >= 1000


def test_triplet_conversion_overhead(benchmark, large_knowledge_graph_dict):
    """
    Benchmarks the `store()` method in TripletStore.
    This tests Python logic that converts a Dict -> Triplet objects.
    """

    with patch("veritasreason.triplet_store.blazegraph_store.BlazegraphStore") as mockBE:
        mock_instance = mockBE.return_value
        mock_instance.add_triplets.return_value = {"success": True}

        manager = TripletStore(backend="blazegraph")
        if hasattr(manager, "progress_tracker"):
            manager.progress_tracker = MagicMock()

        def op():
            manager.store(
                knowledge_graph=large_knowledge_graph_dict,
                ontology={"classes": [], "properties": []},
            )

        benchmark(op)


def test_bulk_loader_logic(benchmark, triplet_batch):
    """
    Benchmarks teh BulkLoader class.
    Measures the overhead of batching, retries and progress tracking.
    """

    loader = BulkLoader(batch_size=100)
    if hasattr(loader, "progress_tracker"):
        loader.progress_tracker = MagicMock()

    mock_store = MagicMock()
    mock_store.add_triplets.return_value = {"success": True}

    def op():
        return loader.load_triplets(triplet_batch, mock_store)

    result = benchmark(op)
    assert result.total_batches == 10


def test_sparql_query_performance(benchmark, in_memory_store, triplet_batch):
    """
    Benchamrks SPARQL query execution speed on 1000 items.
    """

    in_memory_store.add_triplets(triplet_batch)

    query = "SELECT ?s ?o WHERE { ?s <http://gandhara.org/relation/knows> ?o } LIMIT 50"

    def op():
        return in_memory_store.execute_sparql(query)

    result = benchmark(op)
    assert result["success"] is True
    assert len(result["bindings"]) == 50
