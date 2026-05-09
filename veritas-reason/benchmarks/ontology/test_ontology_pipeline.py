from unittest.mock import MagicMock, patch

import pytest

from veritasreason.ontology.ontology_generator import OntologyGenerator


@pytest.mark.benchmark(group="full_pipeline")
@pytest.mark.parametrize("entity_count", [1000])
def test_e2e_ontology_generation(benchmark, generate_ontology_data, entity_count):
    """
    Benchmarks complete 6-stage pipeline
    """

    data = generate_ontology_data(entity_count)
    generator = OntologyGenerator()

    with patch(
        "veritasreason.ontology.ontology_validator.OntologyValidator.validate"
    ) as mock_val:
        mock_val.return_value.valid = True

        def run():
            return generator.generate_ontology(data, validate=True)

        benchmark.pedantic(run, iterations=1, rounds=5)


def test_associative_class_creation(benchmark):
    """
    Benchmarks the creation of complex N-ary relationships.
    """
    from veritasreason.ontology.associative_class import AssociativeClassBuilder

    builder = AssociativeClassBuilder()

    def run():
        for i in range(50):
            builder.create_position_class(
                person_class=f"Person_{i}",
                organization_class=f"Org_{i}",
                role_class=f"Role_{i}",
                name=f"Position_{i}",
            )

    benchmark.pedantic(run, iterations=1, rounds=10)
