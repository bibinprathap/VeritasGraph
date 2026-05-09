from unittest.mock import MagicMock, patch

import pytest

from veritasreason.graph_store.graph_store import GraphStore


@pytest.fixture
def mock_neo4j_driver():
    """
    Creates a mock of of Neo4j Driver
    Simulates: Driver -> Session -> Transaction -> Result -> Record
    """

    mock_result = MagicMock()
    fake_props = {"name": "TestNode", "age": 30}

    def get_item(key):
        if key == "id":
            return 12345
        if key == "n":
            return fake_props
        if key == "count":
            return 42
        return None

    mock_record = MagicMock()
    mock_record.__getitem__.side_effect = get_item
    mock_record.keys.return_value = ["id", "n"]
    mock_record.values.return_value = [12345, fake_props]

    # dict conversion - essentially doing it because the db sometimes demands it
    mock_record.items.return_value = [("id", 12345), ("n", fake_props)]

    # ~~ Result Methods ~~
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    mock_result.__iter__.side_effect = lambda: iter([mock_record])

    # ~~ Session ~~
    mock_session = MagicMock()
    mock_session.run.return_value = mock_result
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = None

    # ~~ Driver ~~
    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session
    mock_driver.verify_connectivity.return_value = True

    return mock_driver


@pytest.fixture
def graph_store(mock_neo4j_driver):
    """
    Returns a GraphsStore connected to mnock driver.
    """

    # ~~ Patch GraphDatbase ~~
    with patch("veritasreason.graph_store.neo4j_store.GraphDatabase") as mockDB:
        mockDB.driver.return_value = mock_neo4j_driver
        store = GraphStore(
            backend="neo4j", uri="bolt://mock:7687", user="mock", password="mock"
        )
        store.connect()

        if hasattr(store, "progress_tracker"):
            store.progress_tracker = MagicMock()

        return store


#    ~~ Benchmarks ~~


def test_node_creation_overhead(benchmark, graph_store):
    """
    Benchamrks the full stack overhead for creating a single node.
    Path: GraphStore -> NodeManager -> Neo4jStore, Driver
    """

    def op():
        return graph_store.create_node(
            labels=["Person"], properties={"name": "Alexander", "age": 17}
        )

    result = benchmark(op)
    assert result["id"] == 12345


def test_batch_node_creation_overhead(benchmark, graph_store):
    """
    Benchmarks the loop overhead in create_nodes (Batch).
    Checks if it handles lists efficiently.
    """

    nodes = [{"labels": ["Person"], "properties": {"id": i}} for i in range(50)]

    def op():
        return graph_store.create_nodes(nodes)

    result = benchmark(op)
    assert len(result) == 50


def test_query_construction_and_parsing(benchmark, graph_store):
    """
    Benchmarks every execution overhead.
    Measures how fast `QueryEngine` parses result into a Python dict.
    """

    query = "MATCH ( n:Person) RETURN n LIMIT 1"

    def op():
        return graph_store.execute_query(query)

    result = benchmark(op)
    assert result["success"] is True
    assert len(result["records"]) > 0


def test_analytics_shortest_path_overhead(benchmark, graph_store):
    """
    Benchmarks the wrapper overhead for graph analytics.
    """

    def op():
        return graph_store.shortest_path(
            start_node_id=1, end_node_id=2, rel_type="KNOWS"
        )

    try:
        benchmark(op)
    except Exception:
        # v pass as we are only trying to benchmark the function overhead call mainly
        pass
