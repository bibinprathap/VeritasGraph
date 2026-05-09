from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from veritasreason.vector_store.faiss_store import FAISSStore
from veritasreason.vector_store.vector_store import VectorStore

# Fixtures


@pytest.fixture
def vector_dim():
    return 768


@pytest.fixture
def random_vectors(vector_dim):
    """Generates a batch of 10,000 rando vectors."""
    count = 10000
    vectors = np.random.rand(count, vector_dim).astype(np.float32)
    return vectors


@pytest.fixture
def populated_store(random_vectors, vector_dim):
    """
    Returns a FAISS store bred with data.
    """

    store = FAISSStore(dimension=vector_dim)
    if hasattr(store, "progress_tracker"):
        store.progress_tracker = MagicMock()
    store.create_index(index_type="flat")
    store.add_vectors(random_vectors)
    return store


# Benchmarks


def test_faiss_insert_throughput(benchmark, random_vectors, vector_dim):
    """
    Benchmarks raw Write speed to FAISS
    """
    store = FAISSStore(dimension=vector_dim)
    if hasattr(store, "progress_tracker"):
        store.progress_tracker = MagicMock()
    store.create_index(index_type="flat")

    def insert_op():
        store.add_vectors(random_vectors)

    benchmark(insert_op)

    assert len(store.index.vector_ids) >= 10000


def test_faiss_search_latency(benchmark, populated_store, vector_dim):
    """
    Benchmarks Read/Search speed
    """

    query = np.random.rand(1, vector_dim).astype(np.float32)
    results = benchmark(populated_store.search_similar, query_vector=query, k=10)
    assert len(results) == 10


def test_vector_storage_manager_overhead(benchmark, random_vectors, vector_dim):
    """
    Benchmarks the overhead of the VectorStore class
    """
    with patch(
        "veritasreason.vector_store.vector_store.EmbeddingGenerator"
    ) as MockEmbedder:
        manager = VectorStore(backend="faiss", dimension=vector_dim)
        if hasattr(manager, "progress_tracker"):
            manager.progress_tracker = MagicMock()

        def store_op():
            manager.store_vectors(random_vectors)

        benchmark(store_op)

        # Check vectors were stored - handle both in-memory and backend stores
        if hasattr(manager, 'vectors'):
            # In-memory backend
            assert len(manager.vectors) >= 10000
        elif hasattr(manager, '_backend_store') and hasattr(manager._backend_store, 'vector_ids'):
            # Backend store (like FAISS)
            assert len(manager._backend_store.vector_ids) >= 10000
        else:
            # For other backends, just ensure no errors occurred
            pass
