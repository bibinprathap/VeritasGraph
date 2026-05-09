import random
import uuid
from typing import Any, Dict, List

import numpy as np
import pytest

# Data Generators


@pytest.fixture
def generate_entities():
    def _gen(count: int) -> List[Dict[str, Any]]:
        entities = []
        for i in range(count):
            entities.append(
                {
                    "id": f"e_{i}",
                    "text": f"Entity Number {i}",
                    "type": random.choice(
                        ["person", "Organization", "Location", "Event"]
                    ),
                    "confidence": random.uniform(0.7, 1.0),
                    "metadata": {"source": "doc_1.txt", "page": 1},
                }
            )

        return entities

    return _gen


@pytest.fixture
def generate_knowledge_graph(generate_entities):
    def _gen(entity_count: int, rel_density: float = 1.5) -> Dict[str, Any]:
        entities = generate_entities(entity_count)
        relationships = []
        rel_count = int(entity_count * rel_density)

        for i in range(rel_count):
            src = random.choice(entities)
            tgt = random.choice(entities)
            relationships.append(
                {
                    "id": f"r_{i}",
                    "source_id": src["id"],
                    "target_id": tgt["id"],
                    "type": " RELATED_TO",
                    "confidence": 0.9,
                    "metadata": {"extractor": "v1"},
                }
            )

        return {
            "entities": entities,
            "relationships": relationships,
            "metadata": {"generated_at": "2026-02-05"},
        }

    return _gen


@pytest.fixture
def generate_vectors():
    def _gen(count: int, dim: int = 384) -> List[Dict[str, Any]]:
        matrix = np.random.rand(count, dim).astype(np.float32)

        data = []

        for i in range(count):
            data.append(
                {
                    "id": f"vec_{i}",
                    "vector": matrix[i].tolist(),
                    "text": f"Text {i}",
                    "metadata": {"model": "bert"},
                }
            )
        return data

    return _gen
