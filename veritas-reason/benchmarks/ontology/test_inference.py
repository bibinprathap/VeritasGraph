import pytest

from veritasreason.ontology.class_inferrer import ClassInferrer
from veritasreason.ontology.property_generator import PropertyGenerator


@pytest.mark.benchmark(group="class_Inference")
@pytest.mark.parametrize("entity_count", [1000, 5000])
def test_class_inference_scaling(benchmark, generate_ontology_data, entity_count):
    """
    Benchmarks grouping and threshold logic in ClassInferrer.
    """

    data = generate_ontology_data(entity_count=entity_count)
    inferrer = ClassInferrer(min_occurrences=2)

    def run():
        return inferrer.infer_classes(data["entities"])

    benchmark.pedantic(run, iterations=1, rounds=5)


@pytest.mark.benchmark(group="property_inference")
@pytest.mark.parametrize("size", [(1000, 1500)])
def test_property_inference_scaling(benchmark, generate_ontology_data, size):
    """
    Benchmarks: PropertyGenerator
    """

    e_count, _ = size
    data = generate_ontology_data(entity_count=e_count)

    inferrer = ClassInferrer()
    classes = inferrer.infer_classes(data["entities"])

    prop_gen = PropertyGenerator()

    def run():
        return prop_gen.infer_properties(
            entities=data["entities"],
            relationships=data["relationships"],
            classes=classes,
        )

    benchmark.pedantic(run, iterations=1, rounds=5)


def test_hierarchy_circular_detection(benchmark):
    """
    Benchmarks the DFS cycle detection in ClassInferrer.
    """

    inferrer = ClassInferrer()

    # Create a deep chain A -> B -> C ... -> Z

    chain_length = 200
    classes = []

    for i in range(chain_length):
        cls = {
            "name": f"Class_{i}",
            "subClassOf": f"Class_{i+1}" if i < chain_length - 1 else None,
        }
        classes.append(cls)

    def run():
        return inferrer.validate_classes(classes)

    benchmark.pedantic(run, iterations=1, rounds=10)
