import pytest


# Data factories
@pytest.fixture
def node_batch():
    """Generates 1000 nodes for graph"""
    return [
        {
            "id": f"node_{i}",
            "type": "Concept",
            "properties": {"name": f"Concept {i}", "weight": i / 1000},
        }
        for i in range(1000)
    ]


@pytest.fixture
def edge_batch():
    """Generates 1000 edges connection to the nodes."""
    return [
        {
            "source_id": f"node_{i}",
            "target_id": f"node_{i + 1}",
            "type": "related to",
            "weight": 0.5,
        }
        for i in range(999)
    ]


@pytest.fixture
def conversation_data():
    """Simulates a large conversation log"""
    entities = [{"text": f"Entity_{i}", "type": "topic"} for i in range(50)]

    return [
        {
            "id": "conv_1",
            "content": "This is a conversation about banking.",
            "entities": entities,
            "relationships": [],
        }
    ]
