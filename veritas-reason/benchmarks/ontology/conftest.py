import random
import string
from unittest.mock import MagicMock, patch

import pytest

# Data generators


def _random_str(length=8):
    return "".join(random.choices(string.ascii_letters, k=length))


@pytest.fixture
def generate_ontology_data():
    """
    Generates a synthetic dataset of entities and relationships
    designed to triger class and property inference class.
    """

    def _generate(entity_count: int, relationship_density: float = 1.5):

        num_classes = max(5, entity_count // 50)
        class_names = [f"Class_{_random_str(4)}" for _ in range(num_classes)]

        entities = []

        for i in range(entity_count):
            cls = random.choice(class_names)

            props = {
                f"prop_{_random_str(3)}": random.choice([10, "text", 1.5, True])
                for _ in range(random.randint(1, 5))
            }

            entity = {
                "id": f"e_{i}",
                "type": cls,
                "name": f"Entity_{i}",
                "confidence": 0.95,
                **props,
            }

            entities.append(entity)

        relationships = []
        rel_count = int(entity_count * relationship_density)
        rel_types = ["relatedTo", "hasPart", "worksFor", "contains", "memberOf"]

        for _ in range(rel_count):
            src = random.choice(entities)
            tgt = random.choice(entities)
            rel = {
                "source": src["name"],
                "target": tgt["name"],
                "type": random.choice(rel_types),
                "source_type": src["type"],
                "target_type": tgt["type"],
                "confidence": 0.8,
            }
            relationships.append(rel)

        return {"entities": entities, "relationships": relationships}

    return _generate


@pytest.fixture
def large_ontology_definition(generate_ontology_data):
    """Pre-calculates a structured ontology
    definition dictionary.
    """
    from veritasreason.ontology.ontology_generator import OntologyGenerator

    data = generate_ontology_data(entity_count=1000)

    # Mocking validation in 6-step pipeline to speed up setup

    with patch(
        "veritasreason.ontology.ontology_validator.OntologyValidator.validate"
    ) as mock_val:
        mock_val.return_value.valid = True
        gen = OntologyGenerator()

        return gen.generate_ontology(data, validate=False)
