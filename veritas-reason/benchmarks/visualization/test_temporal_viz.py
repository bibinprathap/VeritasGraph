import pytest

from veritasreason.visualization.temporal_visualizer import TemporalVisualizer


@pytest.mark.benchmark(group="temporal_animation")
def test_network_evolution_frames(benchmark, generate_temporal_data):
    """
    Measures the cost of generating animation frames for Plotly.
    """

    temporal_data = generate_temporal_data(n_snapshots=5, n_nodes=100)
    viz = TemporalVisualizer()

    def run():
        return viz.visualize_network_evolution(temporal_data, output="interactive")

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="temporal_dashboard")
def test_temporal_dashboard_assembly(benchmark, generate_temporal_data):
    """
    Benchmarks the creation of a multi-subplot dashboard.
    """
    temporal_data = generate_temporal_data(n_snapshots=20, n_nodes=200)
    viz = TemporalVisualizer()

    metrics = {
        "Accuracy": [0.5 + i * 0.02 for i in range(20)],
        "Loss": [1.0 - i * 0.04 for i in range(20)],
    }

    def run():
        return viz.visualize_temporal_dashboard(
            temporal_data, metrics=metrics, output="interactive"
        )

    benchmark.pedantic(run, iterations=1, rounds=5)
