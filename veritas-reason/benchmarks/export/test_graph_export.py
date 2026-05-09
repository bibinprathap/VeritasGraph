import pytest

from veritasreason.export.graph_exporter import GraphExporter


@pytest.mark.benchmark(group="vis_export")
@pytest.mark.parametrize("format", ["graphml", "gexf"])
def test_graph_conversion_overhead(
    benchmark, tmp_path, generate_knowledge_graph, format
):
    """
    Measures the cost of converting internal KG structure to XML-based graph formats.
    Includes dictionary traversal and XML string building.
    """
    kg = generate_knowledge_graph(2000)
    exporter = GraphExporter(format=format)
    output_file = tmp_path / f"graph.{format}"

    def run():
        exporter.export_knowledge_graph(kg, output_file)

    benchmark(run)
