import pytest

from veritasreason.ontology.namespace_manager import NamespaceManager
from veritasreason.ontology.reuse_manager import ReuseManager


def test_namespace_iri_generation(benchmark):
    """
    High-throughput test for IRI Generation.
    """
    manager = NamespaceManager(base_uri="https://veritasreason.dev/bench/")
    names = [f"EntityName_{i}" for i in range(1000)]

    def run():
        for name in names:
            manager.generate_class_iri(name)

    benchmark.pedantic(run, iterations=1, rounds=20)


def test_ontology_merging(benchmark, large_ontology_definition):
    """
    Benchmarks merging two large entities together.
    """
    manager = ReuseManager()
    target = large_ontology_definition.copy()
    source = large_ontology_definition.copy()

    new_classes = []

    for c in source["classes"]:
        base_id = c.get("uri") or c.get("name") or "UnkownEntity"
        new_c = c.copy()
        new_c["uri"] = f"{base_id}_merged"
        new_classes.append(new_c)

    source["classes"] = new_classes

    def run():
        t_copy = target.copy()
        return manager.merge_ontology_data(t_copy, source, overwrite=False)

    benchmark.pedantic(run, iterations=1, rounds=10)
