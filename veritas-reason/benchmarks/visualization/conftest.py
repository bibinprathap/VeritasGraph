import random
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# Data Generators
@pytest.fixture
def generate_embeddings():
    """Generates synthetic high-dim embeddings."""

    def _gen(n_samples: int, n_features: int = 768):
        return np.random.rand(n_samples, n_features).astype(np.float32)

    return _gen


@pytest.fixture
def generate_knowledge_graph():
    """Generates synthetic Knowledge Graph dictionary."""

    def _gen(n_nodes: int, density: float = 0.05):
        entities = [
            {
                "id": f"e_{i}",
                "label": f"Entity_{i}",
                "type": random.choice(["Person", "Organization", "Location", "Event"]),
                "metadata": {"score": random.random()},
            }
            for i in range(n_nodes)
        ]

        relationships = []
        n_edges = int(n_nodes * (n_nodes - 1) * density)
        # Capping edges for safety
        n_edges = min(n_edges, n_nodes * 5)

        for i in range(n_edges):
            src = random.randint(0, n_nodes - 1)
            tgt = random.randint(0, n_nodes - 1)

            if src != tgt:
                relationships.append(
                    {
                        "source": f"e_{src}",
                        "target": f"e_{tgt}",
                        "type": "related_to",
                        "metadata": {"weight": random.random()},
                    }
                )

        return {"entities": entities, "relationships": relationships}

    return _gen


@pytest.fixture
def generate_temporal_data(generate_knowledge_graph):
    """Generates synthetic temporal graph snapshots."""

    def _gen(n_snapshots: int, n_nodes: int):
        timestamps_map = {}
        base_kg = generate_knowledge_graph(n_nodes)
        entities = base_kg["entities"]

        all_years = list(range(2020, 2020 + n_snapshots))
        for ent in entities:
            start = random.randint(0, len(all_years) - 2)
            duration = random.randint(1, len(all_years) - start)
            timestamps_map[ent["id"]] = all_years[start : start + duration]

        return {
            "entities": entities,
            "relationships": base_kg["relationships"],
            "timestamps": timestamps_map,
        }

    return _gen
