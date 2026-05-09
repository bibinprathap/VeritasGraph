from unittest.mock import MagicMock

import pytest

from veritasreason.context.context_graph import ContextGraph


def test_bulk_node_insertion(benchmark, node_batch):
    """
    Benchmarks the overhead of adding nodes to in-memory graph.

    """

    def setup_graph():
        return (ContextGraph(),), {}

    def run(graph_instance):
        graph_instance.add_nodes(node_batch)

    benchmark.pedantic(target=run, setup=setup_graph, rounds=50, iterations=1)


def test_bulk_edge_insertion(benchmark, node_batch, edge_batch):
    """
    Benchmarks adding edges.
    """

    def setup_graph_with_nodes():
        g = ContextGraph()
        g.add_nodes(node_batch)
        return (g,), {}

    def run(graph_instance):
        graph_instance.add_edges(edge_batch)

    benchmark.pedantic(
        target=run, setup=setup_graph_with_nodes, rounds=50, iterations=1
    )


def test_conversation_to_graph_conversion(benchmark, conversation_data):
    """
    Benchmarks parsing conversation dicts into graph structures.
    """

    def setup_clean_builder():
        g = ContextGraph()
        g.entity_linker = MagicMock()
        return (g,), {}

    def run(graph_instance):
        return graph_instance.build_from_conversations(
            conversation_data, link_entities=False
        )

    benchmark.pedantic(target=run, setup=setup_clean_builder, rounds=20, iterations=1)
