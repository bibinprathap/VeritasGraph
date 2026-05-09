import pytest

from veritasreason.visualization.kg_visualizer import KGVisualizer


@pytest.mark.benchmark(group="graph_layouyt")
@pytest.mark.parametrize("layout", ["circular", "force"])
@pytest.mark.parametrize("size", [100])
def test_network_layout_performance(benchmark, generate_knowledge_graph, layout, size):
    """
    Compares layout algorithm.
    """
    viz = KGVisualizer(layout=layout, force_layout_iterations=50)
    graph = generate_knowledge_graph(n_nodes=size)

    def run():
        return viz.visualize_network(graph, output="interactive")

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="graph_structure")
def test_matrix_view_rendering(benchmark, generate_knowledge_graph):
    """
    Benchmarks the creation of an adjacent/relationship matrix.
    """
    viz = KGVisualizer()
    graph = generate_knowledge_graph(n_nodes=500)

    def run():
        return viz.visualize_relationship_matrix(graph, output="interactive")

    benchmark.pedantic(run, iterations=1, rounds=5)
