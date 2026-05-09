import unittest
import os
from datetime import datetime, timezone

import pytest

from veritasreason.normalize import methods
from veritasreason.normalize.config import normalize_config

pytestmark = pytest.mark.integration

class TestNormalizeIntegration(unittest.TestCase):
    def test_normalize_text_integration(self):
        text = "Hello   World"
        # Test default
        normalized = methods.normalize_text(text)
        self.assertEqual(normalized, "Hello World")
        
        # Test with kwargs
        normalized_lower = methods.normalize_text(text, case="lower")
        self.assertEqual(normalized_lower, "hello world")

    def test_normalize_date_integration(self):
        date_str = "2023-01-01"
        # Default ISO
        normalized = methods.normalize_date(date_str)
        self.assertEqual(normalized, "2023-01-01T00:00:00+00:00")
        
        # Relative
        relative = methods.normalize_date("yesterday", method="relative")
        # Just check it returns a datetime or iso string depending on implementation
        # methods.normalize_date implementation:
        # returns normalizer.normalize_date(...) which returns str (ISO) usually
        self.assertIsInstance(relative, str) 

    def test_normalize_number_integration(self):
        # Default
        num = methods.normalize_number("1,234.56")
        self.assertEqual(num, 1234.56)
        
        # Quantity
        qty = methods.normalize_quantity("1 km")
        self.assertEqual(qty["value"], 1.0)
        self.assertEqual(qty["unit"], "kilometer")

    def test_normalize_entity_integration(self):
        entity = "  john   doe  "
        normalized = methods.normalize_entity(entity, entity_type="Person")
        self.assertEqual(normalized, "John Doe")

    def test_clean_data_integration(self):
        dataset = [
            {"id": 1, "val": "A"},
            {"id": 1, "val": "A"},
            {"id": 2, "val": "B"}
        ]
        # Clean duplicates
        # Note: clean_data default duplicate_criteria key_fields might need setting if we want robust test
        # But simple exact duplicate should be caught if default works
        cleaned = methods.clean_data(
            dataset, 
            remove_duplicates=True,
            duplicate_criteria={"key_fields": ["id", "val"]}
        )
        self.assertEqual(len(cleaned), 2)

    def test_config_override(self):
        # Test that kwargs override config
        # normalize_text uses config.get_method_config("text").update(kwargs)
        
        # By default case might be "preserve" (or whatever is in config)
        # Let's force it via kwargs
        res = methods.normalize_text("HELLO", case="lower")
        self.assertEqual(res, "hello")

    def test_registry_custom_method(self):
        # Register a custom method
        from veritasreason.normalize.registry import method_registry
        
        def custom_text_normalizer(text, **kwargs):
            return "CUSTOM: " + text
            
        method_registry.register("text", "my_custom", custom_text_normalizer)
        
        res = methods.normalize_text("hello", method="my_custom")
        self.assertEqual(res, "CUSTOM: hello")
        
        # Clean up
        # Registry doesn't seem to have unregister, but it's a dict wrapper usually or we can leave it
        # method_registry is a MethodRegistry instance.
        # It has _methods dict.
        method_registry._methods["text"].pop("my_custom", None)

if __name__ == "__main__":
    unittest.main()
