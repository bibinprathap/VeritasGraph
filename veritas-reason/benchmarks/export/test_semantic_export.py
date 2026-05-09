import pytest

from veritasreason.export.lpg_exporter import LPGExporter
from veritasreason.export.owl_exporter import OWLExporter
from veritasreason.export.rdf_exporter import RDFExporter


@pytest.mark.benchmark(group="semantic_serialization")
@pytest.mark.parametrize("format", ["turtle", "rdfxml"])
def test_rdf_serialization_formats(benchmark, generate_knowledge_graph, format):
    kg = generate_knowledge_graph(1000)
    exporter = RDFExporter()
    rdf_data = exporter.serializer.convert_kg_to_rdf(kg)

    def run():
        return exporter.export_to_rdf(rdf_data, format=format)

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="graph_db_export")
def test_lpg_cypher_generation(benchmark, generate_knowledge_graph):
    kg = generate_knowledge_graph(2000)
    exporter = LPGExporter(batch_size=1000, include_indexes=False)

    def run():
        return exporter._generate_cypher_queries(kg)

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="semantic_serialization")
def test_owl_xml_generation(benchmark, tmp_path):
    ontology = {
        "name": "BenchmarkOntology",
        "classes": [{"name": f"Class{i}"} for i in range(500)],
        "object_properties": [{"name": f"Prop{i}"} for i in range(200)],
    }
    exporter = OWLExporter()
    output_file = tmp_path / "ontology.xml"

    def run():
        exporter.export(ontology, output_file, format="owl-xml")

    benchmark.pedantic(run, iterations=1, rounds=5)
