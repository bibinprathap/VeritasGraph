import unittest
from unittest.mock import MagicMock, patch
from veritasreason.graph_store import methods
from veritasreason.graph_store.registry import method_registry

class TestGraphStoreMethods(unittest.TestCase):
    def setUp(self):
        # Reset global store
        methods._reset_store()
        
        # Mock GraphStore
        self.mock_store = MagicMock()
        self.mock_store_patcher = patch('veritasreason.graph_store.methods.GraphStore', return_value=self.mock_store)
        self.MockGraphStore = self.mock_store_patcher.start()

    def tearDown(self):
        self.mock_store_patcher.stop()
        methods._reset_store()
        
        # Unregister custom methods if any
        method_registry.unregister("node", "custom_create")

    def test_create_node_default(self):
        # Setup
        labels = ["Person"]
        props = {"name": "Alice"}
        self.mock_store.create_node.return_value = {"id": 1, "labels": labels, "properties": props}

        # Execute
        result = methods.create_node(labels, props)

        # Verify
        self.mock_store.create_node.assert_called_once_with(labels, props)
        self.assertEqual(result["id"], 1)

    def test_create_node_custom(self):
        # Register custom method
        mock_custom = MagicMock(return_value={"id": 99, "custom": True})
        method_registry.register("node", "custom_create", mock_custom)

        # Execute
        result = methods.create_node(["Person"], {"name": "Bob"}, method="custom_create")

        # Verify
        mock_custom.assert_called_once()
        self.mock_store.create_node.assert_not_called()
        self.assertEqual(result["id"], 99)

    def test_execute_query_default(self):
        # Setup
        query = "MATCH (n) RETURN n"
        self.mock_store.execute_query.return_value = {"records": []}

        # Execute
        result = methods.execute_query(query)

        # Verify
        self.mock_store.execute_query.assert_called_once_with(query, None)

if __name__ == '__main__':
    unittest.main()