import pytest

from veritasreason.ontology.owl_generator import OWLGenerator


@pytest.mark.benchmark(group="serialization")
@pytest.mark.parametrize("format", ["turtle", "xml"])
def test_owl_serialization_formats(benchmark, large_ontology_definition, format):
    """Benchmarks the cost of serializing the ontology
    to different string formats.
    """
    generator = OWLGenerator()

    def run():
        return generator.generate_owl(large_ontology_definition, format=format)

    benchmark.pedantic(run, iterations=1, rounds=5)


def test_rdflib_graph_construction(benchmark, large_ontology_definition):
    """
    Benchmarks the creation of rdflib.Graph object.
    """
    generator = OWLGenerator()

    def run():
        if hasattr(generator, "_generate_with_rdflib"):
            return generator._generate_with_rdflib(
                large_ontology_definition, format="turtle"
            )
        return generator.generate_owl(large_ontology_definition)

    benchmark.pedantic(run, iterations=1, rounds=5)
