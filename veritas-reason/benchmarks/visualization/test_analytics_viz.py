import random

import pytest

from veritasreason.visualization.analytics_visualizer import AnalyticsVisualizer


@pytest.mark.benchmark(group="analytics_charts")
def test_centrality_ranking_sort_and_render(benchmark):
    """
    Benchmarks sorting a large centrality dictionary
    and rendering the Top N bar chart.
    """
    viz = AnalyticsVisualizer()

    # Generate 5000 node scores
    centrality_data = {
        "centrality": {f"node_{i}": random.random() for i in range(5000)}
    }

    def run():
        return viz.visualize_centrality_rankings(
            centrality_data, centrality_type="degree", top_n=50, output="interactive"
        )

    benchmark.pedantic(run, iterations=1, rounds=10)
