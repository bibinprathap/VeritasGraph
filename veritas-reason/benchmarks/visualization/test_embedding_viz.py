import numpy as np
import pytest

from veritasreason.visualization.embedding_visualizer import EmbeddingVisualizer


@pytest.mark.benchmark(group="embedding_projection")
@pytest.mark.parametrize("method", ["pca", "tsne"])
@pytest.mark.parametrize("n_samples", [500])
def test_projection_calculation_overhead(
    benchmark, generate_embeddings, method, n_samples
):
    """
    Measures the combined cost of:
    1. Dimensionality Reduction (Math)
    2. Plotly Trace Construction (Object creation)
    """

    viz = EmbeddingVisualizer()
    embeddings = generate_embeddings(n_samples=n_samples, n_features=128)
    labels = [f"Label {i}" for i in range(n_samples)]

    def run():
        return viz.visualize_2d_projection(
            embeddings, labels=labels, method=method, output="interactive"
        )

    rounds = 5 if method == "tsne" else 10
    benchmark.pedantic(run, iterations=1, rounds=rounds)


@pytest.mark.benchmark(group="embedding_heatmap")
def test_similarity_heatmap_generation(benchmark, generate_embeddings):
    """
    Benchmarks O(N^2) similarity matrix calculation
    and heatmap renderin.
    """

    viz = EmbeddingVisualizer()
    embeddings = generate_embeddings(n_samples=500, n_features=64)

    def run():
        return viz.visualize_similarity_heatmap(embeddings, output="interactive")

    benchmark.pedantic(run, iterations=1, rounds=5)
