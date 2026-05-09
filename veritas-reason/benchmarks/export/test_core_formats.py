import pytest

from veritasreason.export.csv_exporter import CSVExporter
from veritasreason.export.json_exporter import JSONExporter
from veritasreason.export.yaml_exporter import SemanticNetworkYAMLExporter


@pytest.mark.benchmark(group="structured_export")
@pytest.mark.parametrize("size", [1000, 5000])
def test_json_parsing_throughput(benchmark, tmp_path, generate_knowledge_graph, size):
    kg = generate_knowledge_graph(size)
    exporter = JSONExporter(indent=None)
    output_file = tmp_path / "output.json"

    def run():
        exporter.export(kg, output_file)

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="structured_export")
def test_csv_entity_export(benchmark, tmp_path, generate_entities):
    entities = generate_entities(5000)
    exporter = CSVExporter()
    output_file = tmp_path / "entities.csv"

    def run():
        exporter.export_entities(entities, output_file)

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="structured_export")
def test_yaml_serialization_overhead(benchmark, tmp_path, generate_knowledge_graph):
    kg = generate_knowledge_graph(500)
    exporter = SemanticNetworkYAMLExporter()
    output_file = tmp_path / "output.yaml"

    def run():
        exporter.export(kg, output_file)

    benchmark.pedantic(run, iterations=1, rounds=5)
