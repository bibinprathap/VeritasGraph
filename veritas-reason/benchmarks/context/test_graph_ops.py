import pytest

from veritasreason.context.context_graph import ContextGraph


@pytest.mark.benchmark(group="graph_traversal")
@pytest.mark.parametrize("hops", [1, 2])
def test_bfs_traversal_depth(benchmark, populated_context_graph, hops):
    """Benchmarks the BFS neighbor retrieval at differnet depths."""
    graph = populated_context_graph(n_nodes=2000)
    start_node = list(graph.nodes.keys())[0]

    def run():
        return graph.get_neighbors(start_node, hops=hops)

    benchmark.pedantic(run, iterations=5, rounds=10)


@pytest.mark.benchmark(group="graph_construction")
@pytest.mark.parametrize("size", [1000])
def test_graph_ingestion_speed(benchmark, generate_graph_data, size):
    """
    Benchmarks the speed of adding nodes and edges to the
    in-memory structure.
    """

    nodes, edges = generate_graph_data(n_nodes=size)

    def run():
        graph = ContextGraph()
        graph.add_nodes(nodes)
        graph.add_edges(edges)

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="graph_query")
def test_graph_keyword_search(benchmark, populated_context_graph):
    """
    Benchmarks the linear scan keyword search over graph nodes.
    """
    graph = populated_context_graph(n_nodes=2000)

    def run():
        return graph.query("Node content 500")

    benchmark.pedantic(run, iterations=5, rounds=10)
