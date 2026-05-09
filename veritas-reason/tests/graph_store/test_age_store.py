"""
Tests for Apache AGE Store Module

Tests cover:
    - Node CRUD (create, read, update, delete)
    - Relationship CRUD
    - Query execution
    - Graph traversal (get_neighbors, shortest_path)
    - Transaction rollback on error
    - Multi-label handling
    - ID separation (AGE internal vs semantic)
    - Input validation / sanitisation
    - Stats retrieval
    - Index creation

The psycopg2 database layer is fully mocked to enable offline testing.
"""

import json
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

# ---------------------------------------------------------------------------
# Mock psycopg2 before importing the module under test so that ``PSYCOPG2_AVAILABLE``
# is ``True`` inside age_store.
# ---------------------------------------------------------------------------
import sys

_mock_psycopg2 = MagicMock()
_mock_psycopg2_extras = MagicMock()
sys.modules["psycopg2"] = _mock_psycopg2
sys.modules["psycopg2.extras"] = _mock_psycopg2_extras

# Evict any cached import of age_store so it re-imports with our mock psycopg2,
# even if other tests already loaded veritasreason (which would have cached the module
# with its original psycopg2 binding, making the sys.modules patch above a no-op).
for _key in list(sys.modules.keys()):
    if "veritasreason" in _key and "age_store" in _key:
        del sys.modules[_key]

from veritasreason.graph_store.age_store import (
    ApacheAgeStore,
    _edge_to_rel_dict,
    _parse_agtype,
    _props_to_cypher_literal,
    _sanitize_label,
    _sanitize_rel_type,
    _value_to_cypher_literal,
    _vertex_to_node_dict,
)
from veritasreason.utils.exceptions import ProcessingError, ValidationError


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _make_vertex_agtype(vid: int, label: str, props: Dict[str, Any]) -> str:
    """Return a string mimicking AGE agtype vertex output."""
    obj = {"id": vid, "label": label, "properties": props}
    return json.dumps(obj) + "::vertex"


def _make_edge_agtype(
    eid: int, label: str, start_id: int, end_id: int, props: Dict[str, Any]
) -> str:
    """Return a string mimicking AGE agtype edge output."""
    obj = {
        "id": eid,
        "label": label,
        "start_id": start_id,
        "end_id": end_id,
        "properties": props,
    }
    return json.dumps(obj) + "::edge"


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------

class TestHelpers(unittest.TestCase):
    """Tests for module-level helper functions."""

    # -- _sanitize_label --------------------------------------------------

    def test_sanitize_label_valid(self):
        self.assertEqual(_sanitize_label("Person"), "Person")
        self.assertEqual(_sanitize_label("_hidden"), "_hidden")
        self.assertEqual(_sanitize_label("Rel_Type2"), "Rel_Type2")

    def test_sanitize_label_invalid(self):
        with self.assertRaises(ValidationError):
            _sanitize_label("123bad")
        with self.assertRaises(ValidationError):
            _sanitize_label("no spaces")
        with self.assertRaises(ValidationError):
            _sanitize_label("no-dashes")

    # -- _sanitize_rel_type -----------------------------------------------

    def test_sanitize_rel_type_valid(self):
        self.assertEqual(_sanitize_rel_type("KNOWS"), "KNOWS")

    def test_sanitize_rel_type_invalid(self):
        with self.assertRaises(ValidationError):
            _sanitize_rel_type("bad type!")

    # -- _value_to_cypher_literal -----------------------------------------

    def test_literal_none(self):
        self.assertEqual(_value_to_cypher_literal(None), "null")

    def test_literal_bool(self):
        self.assertEqual(_value_to_cypher_literal(True), "true")
        self.assertEqual(_value_to_cypher_literal(False), "false")

    def test_literal_int(self):
        self.assertEqual(_value_to_cypher_literal(42), "42")

    def test_literal_float(self):
        self.assertIn("3.14", _value_to_cypher_literal(3.14))

    def test_literal_string(self):
        self.assertEqual(_value_to_cypher_literal("hello"), "'hello'")

    def test_literal_string_escape(self):
        result = _value_to_cypher_literal("it's a \"test\"")
        self.assertIn("\\'", result)

    def test_literal_list(self):
        result = _value_to_cypher_literal([1, "a"])
        self.assertEqual(result, "[1, 'a']")

    def test_literal_dict(self):
        result = _value_to_cypher_literal({"x": 1})
        self.assertEqual(result, "{x: 1}")

    # -- _props_to_cypher_literal -----------------------------------------

    def test_props_empty(self):
        self.assertEqual(_props_to_cypher_literal({}), "{}")

    def test_props_simple(self):
        result = _props_to_cypher_literal({"name": "Alice", "age": 30})
        self.assertIn("name: 'Alice'", result)
        self.assertIn("age: 30", result)

    def test_props_invalid_key(self):
        with self.assertRaises(ValidationError):
            _props_to_cypher_literal({"bad key!": 1})

    # -- _parse_agtype ----------------------------------------------------

    def test_parse_agtype_none(self):
        self.assertIsNone(_parse_agtype(None))

    def test_parse_agtype_vertex(self):
        text = '{"id": 1, "label": "Person", "properties": {"name": "Alice"}}::vertex'
        result = _parse_agtype(text)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["label"], "Person")

    def test_parse_agtype_edge(self):
        text = '{"id": 10, "label": "KNOWS", "start_id": 1, "end_id": 2, "properties": {}}::edge'
        result = _parse_agtype(text)
        self.assertEqual(result["id"], 10)
        self.assertEqual(result["start_id"], 1)

    def test_parse_agtype_numeric(self):
        self.assertEqual(_parse_agtype("42::numeric"), 42)
        self.assertEqual(_parse_agtype("3.14::float"), 3.14)

    def test_parse_agtype_boolean(self):
        self.assertTrue(_parse_agtype("true::boolean"))
        self.assertFalse(_parse_agtype("false::boolean"))

    def test_parse_agtype_plain_json(self):
        self.assertEqual(_parse_agtype('{"a": 1}'), {"a": 1})

    def test_parse_agtype_non_string(self):
        self.assertEqual(_parse_agtype(99), 99)

    # -- _vertex_to_node_dict ---------------------------------------------

    def test_vertex_to_node_dict_basic(self):
        vertex = {"id": 5, "label": "Person", "properties": {"name": "Alice"}}
        result = _vertex_to_node_dict(vertex)
        self.assertEqual(result["id"], 5)
        self.assertEqual(result["labels"], ["Person"])
        self.assertEqual(result["properties"]["name"], "Alice")

    def test_vertex_to_node_dict_extra_labels(self):
        vertex = {
            "id": 7,
            "label": "Person",
            "properties": {"name": "Bob", "labels": ["Employee", "Admin"]},
        }
        result = _vertex_to_node_dict(vertex)
        self.assertEqual(result["labels"], ["Person", "Employee", "Admin"])
        # 'labels' property should be removed from properties
        self.assertNotIn("labels", result["properties"])

    def test_vertex_to_node_dict_non_dict(self):
        result = _vertex_to_node_dict("not a dict")
        self.assertIsNone(result["id"])

    # -- _edge_to_rel_dict ------------------------------------------------

    def test_edge_to_rel_dict_basic(self):
        edge = {
            "id": 10,
            "label": "KNOWS",
            "start_id": 1,
            "end_id": 2,
            "properties": {"since": 2020},
        }
        result = _edge_to_rel_dict(edge)
        self.assertEqual(result["id"], 10)
        self.assertEqual(result["type"], "KNOWS")
        self.assertEqual(result["start_node_id"], 1)
        self.assertEqual(result["end_node_id"], 2)
        self.assertEqual(result["properties"]["since"], 2020)

    def test_edge_to_rel_dict_non_dict(self):
        result = _edge_to_rel_dict(42)
        self.assertIsNone(result["id"])


# ---------------------------------------------------------------------------
# Unit tests — ApacheAgeStore with mocked DB
# ---------------------------------------------------------------------------

class TestApacheAgeStore(unittest.TestCase):
    """Tests for ApacheAgeStore with a fully mocked psycopg2 connection."""

    def setUp(self):
        """Set up a store with a mocked PostgreSQL connection."""
        self.mock_conn = MagicMock()
        self.mock_conn.closed = False
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=self.mock_cursor
        )
        self.mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Patch psycopg2.connect to return the mock connection
        _mock_psycopg2.connect.return_value = self.mock_conn

        self.store = ApacheAgeStore(
            connection_string="host=localhost dbname=testdb user=test password=test",
            graph_name="test_graph",
        )
        # Simulate a successful connect (graph already exists)
        self.mock_cursor.fetchone.return_value = (1,)  # graph exists
        self.store.connect()
        # Reset mock call history after connect
        self.mock_cursor.reset_mock()
        self.mock_conn.reset_mock()
        self.mock_conn.closed = False

    def tearDown(self):
        self.store.close()

    # -- connect ----------------------------------------------------------

    def test_connect_creates_extension_and_graph(self):
        """connect() should run idempotent setup commands."""
        store = ApacheAgeStore(
            connection_string="host=localhost dbname=agedb user=test",
            graph_name="new_graph",
        )
        # Graph does NOT exist yet
        self.mock_cursor.fetchone.return_value = (0,)

        result = store.connect()
        self.assertTrue(result)

        # Verify setup SQL was executed
        executed = [
            str(c) for c in self.mock_cursor.execute.call_args_list
        ]
        setup_text = " ".join(executed)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS age", setup_text)
        self.assertIn("LOAD 'age'", setup_text)
        self.assertIn("search_path", setup_text)
        self.assertIn("create_graph", setup_text)

    def test_connect_idempotent_existing_graph(self):
        """connect() should skip create_graph if graph already exists."""
        store = ApacheAgeStore(
            connection_string="host=localhost dbname=agedb user=test",
            graph_name="existing_graph",
        )
        self.mock_cursor.fetchone.return_value = (1,)  # graph exists

        result = store.connect()
        self.assertTrue(result)

        executed = [
            str(c) for c in self.mock_cursor.execute.call_args_list
        ]
        setup_text = " ".join(executed)
        # create_graph should NOT be called (graph count=1)
        self.assertNotIn("create_graph", setup_text.split("ag_graph")[1] if "ag_graph" in setup_text else "")

    # -- create_node ------------------------------------------------------

    def test_create_node_single_label(self):
        """create_node with one label should use it as AGE label."""
        vertex_str = _make_vertex_agtype(100, "Person", {"name": "Alice"})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        node = self.store.create_node(
            labels=["Person"], properties={"name": "Alice"}
        )

        self.assertEqual(node["id"], 100)
        self.assertEqual(node["labels"], ["Person"])
        self.assertEqual(node["properties"]["name"], "Alice")

    def test_create_node_multiple_labels(self):
        """Additional labels beyond the first are stored as property array."""
        vertex_str = _make_vertex_agtype(
            101, "Person", {"name": "Bob", "labels": ["Employee", "Admin"]}
        )
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        node = self.store.create_node(
            labels=["Person", "Employee", "Admin"],
            properties={"name": "Bob"},
        )

        self.assertEqual(node["id"], 101)
        self.assertIn("Person", node["labels"])
        self.assertIn("Employee", node["labels"])
        self.assertIn("Admin", node["labels"])
        # 'labels' property should be moved out of properties
        self.assertNotIn("labels", node["properties"])

    def test_create_node_with_veritasreason_id(self):
        """veritasreason_id in properties should be preserved."""
        vertex_str = _make_vertex_agtype(
            102, "Entity", {"veritasreason_id": "abc-123", "value": "test"}
        )
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        node = self.store.create_node(
            labels=["Entity"],
            properties={"veritasreason_id": "abc-123", "value": "test"},
        )

        self.assertEqual(node["id"], 102)  # AGE internal ID
        self.assertEqual(node["properties"]["veritasreason_id"], "abc-123")

    def test_create_node_empty_labels_raises(self):
        """create_node with empty labels should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_node(labels=[], properties={"name": "X"})

    def test_create_node_invalid_label_raises(self):
        """create_node with invalid label should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_node(labels=["bad label!"], properties={})

    # -- create_nodes -----------------------------------------------------

    def test_create_nodes_batch(self):
        """create_nodes should create multiple nodes."""
        responses = [
            [(_make_vertex_agtype(200, "Person", {"name": "A"}),)],
            [(_make_vertex_agtype(201, "Person", {"name": "B"}),)],
        ]
        self.mock_cursor.fetchall.side_effect = responses

        nodes_data = [
            {"labels": ["Person"], "properties": {"name": "A"}},
            {"labels": ["Person"], "properties": {"name": "B"}},
        ]
        result = self.store.create_nodes(nodes_data)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 200)
        self.assertEqual(result[1]["id"], 201)

    # -- get_node ---------------------------------------------------------

    def test_get_node_found(self):
        vertex_str = _make_vertex_agtype(100, "Person", {"name": "Alice"})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        node = self.store.get_node(100)

        self.assertIsNotNone(node)
        self.assertEqual(node["id"], 100)
        self.assertEqual(node["properties"]["name"], "Alice")

    def test_get_node_not_found(self):
        self.mock_cursor.fetchall.return_value = []

        node = self.store.get_node(999)
        self.assertIsNone(node)

    # -- get_nodes --------------------------------------------------------

    def test_get_nodes_with_label_filter(self):
        vertex_str = _make_vertex_agtype(100, "Person", {"name": "Alice"})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        nodes = self.store.get_nodes(labels=["Person"])

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["labels"], ["Person"])

    def test_get_nodes_with_property_filter(self):
        vertex_str = _make_vertex_agtype(100, "Person", {"name": "Alice"})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        nodes = self.store.get_nodes(properties={"name": "Alice"})
        self.assertEqual(len(nodes), 1)

    def test_get_nodes_empty(self):
        self.mock_cursor.fetchall.return_value = []
        nodes = self.store.get_nodes()
        self.assertEqual(nodes, [])

    # -- update_node ------------------------------------------------------

    def test_update_node_merge(self):
        vertex_str = _make_vertex_agtype(100, "Person", {"name": "Alice", "age": 31})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        node = self.store.update_node(100, {"age": 31}, merge=True)

        self.assertEqual(node["id"], 100)
        self.assertEqual(node["properties"]["age"], 31)
        self.assertEqual(node["properties"]["name"], "Alice")

        # Verify the Cypher used += for merge
        executed_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("+=", executed_sql)

    def test_update_node_replace(self):
        vertex_str = _make_vertex_agtype(100, "Person", {"age": 31})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        node = self.store.update_node(100, {"age": 31}, merge=False)
        self.assertEqual(node["properties"]["age"], 31)

        # Verify SET n = (not +=) for replace
        executed_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("SET n =", executed_sql)
        self.assertNotIn("+=", executed_sql)

    def test_update_node_not_found(self):
        self.mock_cursor.fetchall.return_value = []

        with self.assertRaises(ProcessingError):
            self.store.update_node(999, {"age": 31})

    # -- delete_node ------------------------------------------------------

    def test_delete_node_detach(self):
        self.mock_cursor.fetchall.return_value = []

        result = self.store.delete_node(100, detach=True)
        self.assertTrue(result)

        executed_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("DETACH DELETE", executed_sql)

    def test_delete_node_no_detach(self):
        self.mock_cursor.fetchall.return_value = []

        result = self.store.delete_node(100, detach=False)
        self.assertTrue(result)

        executed_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("DELETE", executed_sql)
        self.assertNotIn("DETACH", executed_sql)

    # -- create_relationship ----------------------------------------------

    def test_create_relationship(self):
        edge_str = _make_edge_agtype(500, "KNOWS", 100, 200, {"since": 2023})
        self.mock_cursor.fetchall.return_value = [(edge_str,)]

        rel = self.store.create_relationship(100, 200, "KNOWS", {"since": 2023})

        self.assertEqual(rel["id"], 500)
        self.assertEqual(rel["type"], "KNOWS")
        self.assertEqual(rel["start_node_id"], 100)
        self.assertEqual(rel["end_node_id"], 200)
        self.assertEqual(rel["properties"]["since"], 2023)

    def test_create_relationship_no_properties(self):
        edge_str = _make_edge_agtype(501, "FOLLOWS", 100, 200, {})
        self.mock_cursor.fetchall.return_value = [(edge_str,)]

        rel = self.store.create_relationship(100, 200, "FOLLOWS")
        self.assertEqual(rel["type"], "FOLLOWS")
        self.assertEqual(rel["properties"], {})

    def test_create_relationship_invalid_type_raises(self):
        with self.assertRaises(ValidationError):
            self.store.create_relationship(100, 200, "BAD TYPE!")

    # -- get_relationships ------------------------------------------------

    def test_get_relationships_outgoing(self):
        edge_str = _make_edge_agtype(500, "KNOWS", 100, 200, {})
        self.mock_cursor.fetchall.return_value = [(edge_str,)]

        rels = self.store.get_relationships(
            node_id=100, rel_type="KNOWS", direction="out"
        )

        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]["type"], "KNOWS")

    def test_get_relationships_incoming(self):
        edge_str = _make_edge_agtype(501, "KNOWS", 200, 100, {})
        self.mock_cursor.fetchall.return_value = [(edge_str,)]

        rels = self.store.get_relationships(
            node_id=100, direction="in"
        )
        self.assertEqual(len(rels), 1)

    def test_get_relationships_all(self):
        self.mock_cursor.fetchall.return_value = []
        rels = self.store.get_relationships()
        self.assertEqual(rels, [])

    # -- delete_relationship ----------------------------------------------

    def test_delete_relationship(self):
        self.mock_cursor.fetchall.return_value = []

        result = self.store.delete_relationship(500)
        self.assertTrue(result)

    # -- execute_query ----------------------------------------------------

    def test_execute_query_basic(self):
        """execute_query should return Neo4jStore-compatible result dict."""
        self.mock_cursor.description = [("n",)]
        vertex_str = _make_vertex_agtype(100, "Person", {"name": "Alice"})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        result = self.store.execute_query(
            "MATCH (n:Person) RETURN n", cols="n agtype"
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(result["records"]), 1)
        self.assertIn("keys", result)
        self.assertIn("metadata", result)
        self.assertEqual(result["metadata"]["query"], "MATCH (n:Person) RETURN n")

    def test_execute_query_with_parameters(self):
        """Parameters should be substituted as safe literals."""
        self.mock_cursor.description = [("count",)]
        self.mock_cursor.fetchall.return_value = [("5::numeric",)]

        result = self.store.execute_query(
            "MATCH (n) WHERE n.age > $min_age RETURN count(n) AS count",
            parameters={"min_age": 25},
            cols="count agtype",
        )

        self.assertTrue(result["success"])
        # Check the SQL that was executed contained the literal, not $min_age
        executed_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("25", executed_sql)
        self.assertNotIn("$min_age", executed_sql)

    def test_execute_query_empty_result(self):
        self.mock_cursor.description = []
        self.mock_cursor.fetchall.return_value = []

        result = self.store.execute_query("MATCH (n) RETURN n", cols="n agtype")
        self.assertTrue(result["success"])
        self.assertEqual(result["records"], [])

    # -- get_neighbors ----------------------------------------------------

    def test_get_neighbors_out(self):
        vertex_str = _make_vertex_agtype(200, "Person", {"name": "Bob"})
        self.mock_cursor.fetchall.return_value = [(vertex_str,)]

        neighbors = self.store.get_neighbors(
            node_id=100, rel_type="KNOWS", direction="out", depth=2
        )

        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0]["id"], 200)

    def test_get_neighbors_both(self):
        self.mock_cursor.fetchall.return_value = []
        neighbors = self.store.get_neighbors(node_id=100)
        self.assertEqual(neighbors, [])

    # -- shortest_path ----------------------------------------------------

    def test_shortest_path_found(self):
        """When a path is found, it should be returned as dict with nodes/relationships."""
        path_list = [
            {"id": 1, "label": "Person", "properties": {"name": "A"}},
            {"id": 10, "label": "KNOWS", "start_id": 1, "end_id": 2, "properties": {}},
            {"id": 2, "label": "Person", "properties": {"name": "B"}},
        ]
        path_str = json.dumps(path_list) + "::path"
        self.mock_cursor.fetchall.return_value = [(path_str,)]

        result = self.store.shortest_path(1, 2)

        self.assertIsNotNone(result)
        self.assertEqual(result["length"], 1)
        self.assertEqual(len(result["nodes"]), 2)
        self.assertEqual(len(result["relationships"]), 1)

    def test_shortest_path_not_found(self):
        self.mock_cursor.fetchall.return_value = []

        result = self.store.shortest_path(1, 999)
        self.assertIsNone(result)

    # -- create_index -----------------------------------------------------

    def test_create_index(self):
        result = self.store.create_index("Person", "name", "btree")
        self.assertTrue(result)

        executed_sql = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("CREATE INDEX IF NOT EXISTS", executed_sql)
        self.assertIn("Person", executed_sql)
        self.assertIn("name", executed_sql)

    def test_create_index_invalid_property_raises(self):
        with self.assertRaises(ValidationError):
            self.store.create_index("Person", "bad name!", "btree")

    # -- get_stats --------------------------------------------------------

    def test_get_stats(self):
        """get_stats should return structured dict."""
        # Mock call sequence:
        # 1. node count cypher → fetchall
        # 2. relationship count cypher → fetchall
        # 3. label catalog query → fetchall (pg cursor)
        #    then per-label cypher → fetchall
        # 4. edge type catalog query → fetchall (pg cursor)
        #    then per-type cypher → fetchall

        call_count = [0]
        fetch_responses = [
            [("42::numeric",)],   # node count
            [("10::numeric",)],   # relationship count
            [("5::numeric",)],    # label count for Person
            [("10::numeric",)],   # edge count for KNOWS
        ]
        cursor_fetch_responses = [
            (1,),                  # ensure_connection: ag_graph check (not used here)
            [("Person",)],        # label catalog
            [("KNOWS",)],         # edge type catalog
        ]

        def mock_fetchall():
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(fetch_responses):
                return fetch_responses[idx]
            return []

        def mock_cursor_fetchall():
            # Returns for the catalog queries
            if not hasattr(mock_cursor_fetchall, "_idx"):
                mock_cursor_fetchall._idx = 0
            idx = mock_cursor_fetchall._idx
            mock_cursor_fetchall._idx += 1
            if idx < len(cursor_fetch_responses):
                return cursor_fetch_responses[idx]
            return []

        self.mock_cursor.fetchall.side_effect = mock_fetchall
        self.mock_cursor.fetchone.return_value = (1,)

        stats = self.store.get_stats()

        self.assertIn("node_count", stats)
        self.assertIn("relationship_count", stats)
        self.assertIn("label_counts", stats)
        self.assertIn("relationship_type_counts", stats)

    # -- Transaction rollback ---------------------------------------------

    def test_cypher_execution_rollback_on_error(self):
        """If a query fails, the connection should be rolled back."""
        self.mock_cursor.execute.side_effect = Exception("SQL error")

        with self.assertRaises(ProcessingError):
            self.store.get_node(100)

        self.mock_conn.rollback.assert_called()

    def test_create_node_db_error_raises(self):
        """Database errors during create_node should raise ProcessingError."""
        self.mock_cursor.execute.side_effect = Exception("Disk full")

        with self.assertRaises(ProcessingError):
            self.store.create_node(["Test"], {"key": "val"})

    # -- close ------------------------------------------------------------

    def test_close(self):
        self.store.close()
        self.assertIsNone(self.store._conn)

    def test_close_idempotent(self):
        """Calling close() twice should not raise."""
        self.store.close()
        self.store.close()  # Should not raise


# ---------------------------------------------------------------------------
# Integration-style test with GraphStore facade
# ---------------------------------------------------------------------------

class TestGraphStoreFacadeAge(unittest.TestCase):
    """Test that GraphStore(backend='age') initialises ApacheAgeStore."""

    @patch("veritasreason.graph_store.age_store.ApacheAgeStore", autospec=True)
    def test_age_backend_initialisation(self, MockAgeStore):
        """GraphStore should instantiate ApacheAgeStore for 'age' backend."""
        from veritasreason.graph_store.graph_store import GraphStore

        mock_instance = MagicMock()
        MockAgeStore.return_value = mock_instance

        store = GraphStore(backend="age")
        self.assertIs(store._store_backend, mock_instance)

    @patch("veritasreason.graph_store.age_store.ApacheAgeStore", autospec=True)
    def test_apache_age_backend_alias(self, MockAgeStore):
        """GraphStore should accept 'apache_age' as backend alias."""
        from veritasreason.graph_store.graph_store import GraphStore

        mock_instance = MagicMock()
        MockAgeStore.return_value = mock_instance

        store = GraphStore(backend="apache_age")
        self.assertIs(store._store_backend, mock_instance)


# ---------------------------------------------------------------------------
# Return format conformance tests
# ---------------------------------------------------------------------------

class TestReturnFormatConformance(unittest.TestCase):
    """Verify that returned dicts match Neo4jStore structure exactly."""

    def test_node_return_keys(self):
        vertex = {"id": 1, "label": "X", "properties": {"a": 1}}
        result = _vertex_to_node_dict(vertex)
        self.assertSetEqual(set(result.keys()), {"id", "labels", "properties"})

    def test_relationship_return_keys(self):
        edge = {"id": 1, "label": "R", "start_id": 2, "end_id": 3, "properties": {}}
        result = _edge_to_rel_dict(edge)
        self.assertSetEqual(
            set(result.keys()),
            {"id", "type", "start_node_id", "end_node_id", "properties"},
        )


if __name__ == "__main__":
    unittest.main()
