import pytest

from veritasreason.context.context_graph import ContextGraph
from veritasreason.context.entity_linker import EntityLinker


@pytest.mark.benchmark(group="entity_linkiing")
@pytest.mark.parametrize("num_entities_in_graph", [100, 1000])
def test_entity_linking_complexity(benchmark, num_entities_in_graph):
    """
    Benchmarks finding links for extracted entities
    against the existing graph.
    """

    graph = ContextGraph()
    nodes = [
        {"id": f"e_{i}", "type": "Entity", "properties": {"content": f"Entity {i}"}}
        for i in range(num_entities_in_graph)
    ]
    graph.add_nodes(nodes)

    graph_dict = graph.to_dict()

    linker = EntityLinker(knowledge_graph=graph_dict, similarity_threshold=0.7)

    # Simulate extraction
    extracted_entities = [{"text": f"Entity {i}", "type": "Entity"} for i in range(5)]

    def run():
        return linker.link("dummy text", entities=extracted_entities)

    benchmark.pedantic(run, iterations=1, rounds=5)
