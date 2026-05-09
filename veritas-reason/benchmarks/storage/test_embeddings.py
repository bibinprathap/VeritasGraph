from typing import Generator, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from veritasreason.embeddings.embedding_generator import EmbeddingGenerator
from veritasreason.embeddings.graph_embedding_manager import GraphEmbeddingManager
from veritasreason.embeddings.pooling_strategies import PoolingStrategyFactory
from veritasreason.embeddings.text_embedder import TextEmbedder


# Infra Mocks
@pytest.fixture(autouse=True)
def kill_io_overhead():
    """Silences logging and tracker globally."""
    with patch("veritasreason.utils.logging.get_logger"), patch(
        "veritasreason.utils.progress_tracker.get_progress_tracker"
    ) as mock_tracker:

        tracker = MagicMock()
        tracker.enabled = False
        tracker._start_tracking.return_value = "dummy_id"
        mock_tracker.return_value = tracker

        with patch(
            "veritasreason.embeddings.text_embedder.get_progress_tracker",
            return_value=tracker,
        ):
            yield


# __ Model Mocks __


class MockSentenceTransformer:
    """
    Simulates ST.encode without loading the fat model itself.
    """

    def __init__(self, dim=384):
        self.dim = dim

    def encode(
        self, sentences: List[str], normalize_embeddings=True, **kwargs
    ) -> np.ndarray:
        count = len(sentences)
        return np.random.rand(count, self.dim).astype(np.float32)

    def get_sentence_embedding_dimension(self):
        return self.dim


class MockFastEmbed:
    """
    Simulates FastEmbed.embed generator behavior.
    """

    def __init__(self, dim=384):
        self.dim = dim

    def embed(self, documents: List[str]) -> Generator[np.ndarray, None, None]:
        for _ in documents:
            yield np.random.rand(self.dim).astype(np.float32)


# ~~ Fixtures ~~
@pytest.fixture
def text_embedder_st():
    """
    Text embedder configured with SentenceTransformer
    """
    embedder = TextEmbedder(method="sentence_transformers", model_name="mock-bert")
    embedder.model = MockSentenceTransformer()
    embedder.progress_tracker = MagicMock()
    embedder.progress_tracker.enabled = False

    return embedder


@pytest.fixture
def text_embedder_fast():
    """
    Text Embedder cofnigures with Mock FastEmbed.
    """

    embedder = TextEmbedder(method="fastembed", model_name="mock-bge")
    embedder.fastembed_model = MockFastEmbed()
    embedder.progress_tracker = MagicMock()
    embedder.progress_tracker.enabled = False
    return embedder


# ~~ Benchmarks


@pytest.mark.parametrize("strategy", ["mean", "max", "cls", "attention"])
def test_pooling_math_speed(benchmark, strategy):
    """
    Measures the raw NumPy speed of pooling strategies.
    Scenario: Pooling a batch of 128 token embeddings.
    """

    embeddings = np.random.rand(128, 768).astype(np.float32)
    pooler = PoolingStrategyFactory.create(strategy)

    benchmark.pedantic(lambda: pooler.pool(embeddings), iterations=1000, rounds=100)


def test_hierarchical_pooling_overhead(benchmark):
    """
    Measures the overhead of two-step hierarchical pooling.
    """

    embeddings = np.random.rand(1000, 768).astype(np.float32)
    pooler = PoolingStrategyFactory.create("hierarchical", chunk_size=100)

    benchmark.pedantic(lambda: pooler.pool(embeddings), iterations=500, rounds=50)


def test_st_wrapper_overhead(benchmark, text_embedder_st):
    """
    Measures overhead of TextEmbedder wrapper around SentenceTransformers.
    """

    text = "This is a whatever we are doing here since idk"

    benchmark.pedantic(
        lambda: text_embedder_st.embed_text(text), iterations=1000, rounds=20
    )


def test_fastembed_generator_consumption(benchmark, text_embedder_fast):
    """
    Measures the cost of consuming the FastEmbed generator
    and converting to Array.
    """
    texts = [f"Sentence {i}" for i in range(20)]

    benchmark.pedantic(
        lambda: text_embedder_fast.embed_batch(texts), iterations=100, rounds=20
    )


@pytest.mark.parametrize("batch_size", [10, 100, 1000])
def test_batch_processing_pipeline(benchmark, batch_size, text_embedder_st):
    """
    Measures the full EmbeddingGenerator pipeline:
    Input validation -> Type detection -> Batching -> Mock Model -> Error handling.
    """

    generator = EmbeddingGenerator()

    generator.text_embedder = text_embedder_st
    generator.progress_tracker = MagicMock()
    generator.progress_tracker.enabled = False

    data = [f"Item {i}" for i in range(batch_size)]

    benchmark.pedantic(lambda: generator.process_batch(data), iterations=5, rounds=10)


@pytest.mark.parametrize("count", [100, 1000])
def test_graph_embedding_prep(benchmark, count, text_embedder_st):
    """
    Measures how fast we can reshape dict for GraphDBs
    """
    manager = GraphEmbeddingManager()
    manager.embedding_generator.text_embedder = text_embedder_st

    manager.embedding_generator.generate_embeddings = MagicMock(
        return_value=np.random.rand(count, 384).astype(np.float32)
    )

    entities = [{"id": f"e{i}", "text": f"Entity{i}"} for i in range(count)]

    def op():
        return manager.prepare_for_graph_db(entities, backend="neo4j")

    benchmark.pedantic(op, iterations=10, rounds=10)
