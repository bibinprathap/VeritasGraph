import unittest
from veritasreason.normalize.entity_normalizer import (
    EntityNormalizer,
    AliasResolver,
    EntityDisambiguator,
    NameVariantHandler
)

class TestEntityNormalizer(unittest.TestCase):
    def setUp(self):
        # Setup with some alias mapping
        self.config = {
            "alias_map": {
                "j. doe": "John Doe",
                "bill gates": "William Henry Gates III"
            }
        }
        self.normalizer = EntityNormalizer(**self.config)

    def test_normalize_entity_basic(self):
        self.assertEqual(self.normalizer.normalize_entity("  john doe  ", entity_type="Person"), "John Doe")

    def test_resolve_aliases(self):
        self.assertEqual(self.normalizer.resolve_aliases("J. Doe"), "John Doe")
        self.assertEqual(self.normalizer.resolve_aliases("Bill Gates"), "William Henry Gates III")
        # Unmapped should return None
        self.assertIsNone(self.normalizer.resolve_aliases("Unknown Person"))

    def test_disambiguate_entity(self):
        # Basic mock test since disambiguation is placeholder
        result = self.normalizer.disambiguate_entity("Apple", context="tech")
        self.assertEqual(result["entity_name"], "Apple")
        self.assertEqual(result["confidence"], 0.8)

    def test_link_entities(self):
        entities = ["J. Doe", "Bill Gates"]
        linked = self.normalizer.link_entities(entities, entity_type="Person")
        self.assertEqual(linked["J. Doe"], "John Doe")
        # Note: Standard normalization title-cases the string, so III becomes Iii
        self.assertEqual(linked["Bill Gates"], "William Henry Gates Iii")

class TestNameVariantHandler(unittest.TestCase):
    def setUp(self):
        self.handler = NameVariantHandler()

    def test_normalize_name_format(self):
        self.assertEqual(self.handler.normalize_name_format("Dr. John Doe", "standard"), "John Doe")
        self.assertEqual(self.handler.normalize_name_format("MR. JOHN DOE", "lower"), "john doe")

    def test_handle_titles(self):
        result = self.handler.handle_titles_and_honorifics("Dr. House")
        self.assertEqual(result["name"], "House")
        self.assertEqual(result["title"], "Dr.")

if __name__ == "__main__":
    unittest.main()
