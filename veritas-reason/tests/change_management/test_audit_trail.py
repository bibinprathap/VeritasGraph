import pytest
from veritasreason.context.context_graph import ContextGraph
from veritasreason.change_management.managers import TemporalVersionManager, ProcessingError
from veritasreason.utils.exceptions import ValidationError

@pytest.fixture
def setup_env():
    """Fixture to provide a clean graph and manager for each test."""
    graph = ContextGraph()
    manager = TemporalVersionManager() 
    manager.attach_to_graph(graph)
    return graph, manager

def test_audit_trail_records_mutations(setup_env):
    graph, manager = setup_env
    graph.add_node("user_1", "person", content="Alice")
    graph.add_node_attribute("user_1", {"age": 30})


    history = manager.get_node_history("user_1")
    assert len(history) == 2
    assert history[0]["operation"] == "ADD_NODE"
    assert history[1]["operation"] == "UPDATE_NODE"
    assert history[1]["payload"]["properties"]["age"] == 30

def test_version_tagging_and_retrieval(setup_env):
    graph, manager = setup_env
    graph.add_node("node_1", "concept", content="Test")
    

    manager.create_snapshot(
        graph.to_dict(), 
        version_label="v1.0", 
        author="test@example.com", 
        description="Test Release"
    )

    manager.tag_version("v1.0", "production-ready")
    

    tags = manager.list_tags()
    assert "production-ready" in tags
    assert tags["production-ready"] == "v1.0"
    history = manager.get_node_history("node_1")
    assert history[0]["version_label"] == "v1.0"

def test_tagging_nonexistent_version_fails(setup_env):
    _, manager = setup_env
    
    with pytest.raises(Exception):
        manager.tag_version("v99.0", "invalid-tag")

def test_rollback_protection_enforcement(setup_env):
    graph, manager = setup_env
    graph.add_node("node_1", "concept")
    
    manager.create_snapshot(
        graph.to_dict(), 
        version_label="v1.0", 
        author="test@example.com", 
        description="Test"
    )

    with pytest.raises(ProcessingError, match="Rollback protection active"):
        manager.restore_snapshot(graph, "v1.0")

    success = manager.restore_snapshot(graph, "v1.0", require_confirmation=False)
    assert success is True
    assert len(graph.nodes) == 1

def test_restore_snapshot_does_not_record_replay_mutations(setup_env):
    graph, manager = setup_env
    graph.add_node("node_1", "concept")
    manager.create_snapshot(
        graph.to_dict(),
        version_label="v1.0",
        author="test@example.com",
        description="Initial snapshot",
    )
    graph.add_node_attribute("node_1", {"status": "changed"})

    history_before_restore = manager.get_node_history("node_1")
    assert len(history_before_restore) == 2

    manager.restore_snapshot(graph, "v1.0", require_confirmation=False)

    history_after_restore = manager.get_node_history("node_1")
    assert len(history_after_restore) == 2
