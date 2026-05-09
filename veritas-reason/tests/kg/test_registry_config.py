import unittest
import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.kg.registry import MethodRegistry
from veritasreason.kg.config import KGConfig

class TestMethodRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = MethodRegistry()
        # Clean up registry for testing
        self.registry.clear("test_task")

    def test_register_and_get(self):
        def dummy_method():
            return "ok"
        
        self.registry.register("test_task", "dummy", dummy_method)
        retrieved = self.registry.get("test_task", "dummy")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved(), "ok")

    def test_list_all(self):
        def m1(): pass
        def m2(): pass
        
        self.registry.register("test_task", "m1", m1)
        self.registry.register("test_task", "m2", m2)
        
        all_methods = self.registry.list_all("test_task")
        self.assertIn("m1", all_methods["test_task"])
        self.assertIn("m2", all_methods["test_task"])

    def test_unregister(self):
        def m1(): pass
        self.registry.register("test_task", "m1", m1)
        self.registry.unregister("test_task", "m1")
        self.assertIsNone(self.registry.get("test_task", "m1"))


class TestKGConfig(unittest.TestCase):
    def setUp(self):
        self.config = KGConfig()

    def test_set_get(self):
        self.config.set("my_key", 123)
        self.assertEqual(self.config.get("my_key"), 123)
        self.assertEqual(self.config.get("non_existent", "default"), "default")

    def test_method_config(self):
        self.config.set_method_config("build", param="value")
        cfg = self.config.get_method_config("build")
        self.assertEqual(cfg["param"], "value")

if __name__ == "__main__":
    unittest.main()
