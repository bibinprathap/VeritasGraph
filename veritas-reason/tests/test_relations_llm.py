import unittest

from veritasreason.semantic_extract.methods import extract_relations_llm
from veritasreason.semantic_extract.ner_extractor import Entity


class FakeProvider:
    def __init__(self, typed_payload=None, structured_payload=None):
        self._typed_payload = typed_payload
        self._structured_payload = structured_payload

    def is_available(self):
        return True

    # Simulate typed output return: can be dict or an object with relations
    def generate_typed(self, prompt, schema, **kwargs):
        return self._typed_payload if self._typed_payload is not None else {"relations": []}

    def generate_structured(self, prompt, **kwargs):
        return self._structured_payload if self._structured_payload is not None else {"relations": []}


class TestLLMRelationExtraction(unittest.TestCase):
    def setUp(self):
        # Minimal realistic text and entities
        self.text = "Apple reported revenue of $4.4 billion in Q1 2024."
        self.entities = [
            Entity(text="Apple", label="ORGANIZATION", start_char=0, end_char=5, confidence=0.99),
            Entity(text="$4.4 billion", label="MONEY", start_char=26, end_char=39, confidence=0.99),
            Entity(text="Q1 2024", label="DATE", start_char=43, end_char=51, confidence=0.99),
        ]

    def _monkeypatch_provider(self, provider_instance):
        # Monkeypatch create_provider used by extract_relations_llm
        import veritasreason.semantic_extract.methods as methods
        self._orig_create_provider = methods.create_provider

        def _fake_create_provider(provider, model=None, **kwargs):
            return provider_instance

        methods.create_provider = _fake_create_provider

    def tearDown(self):
        # Restore original create_provider if patched
        try:
            import veritasreason.semantic_extract.methods as methods
            if hasattr(self, "_orig_create_provider"):
                methods.create_provider = self._orig_create_provider
        except Exception:
            pass

    def test_typed_relations_parsed(self):
        # Typed returns a dict compatible with parser
        typed_payload = {
            "relations": [
                {
                    "subject": "Apple",
                    "predicate": "HAS_REVENUE",
                    "object": "$4.4 billion",
                    "confidence": 0.92,
                },
                {
                    "subject": "Apple",
                    "predicate": "IN_QUARTER",
                    "object": "Q1 2024",
                    "confidence": 0.9,
                },
            ]
        }
        fake = FakeProvider(typed_payload=typed_payload)
        self._monkeypatch_provider(fake)

        rels = extract_relations_llm(
            text=self.text,
            entities=self.entities,
            provider="groq",
            model="llama-3.1-8b-instant",
            relation_types=["HAS_REVENUE", "IN_QUARTER"],
            verbose=True,
        )
        self.assertGreaterEqual(len(rels), 2, "Expected at least two relations from typed payload")
        preds = {(r.subject.text, r.predicate, r.object.text) for r in rels}
        self.assertIn(("Apple", "HAS_REVENUE", "$4.4 billion"), preds)
        self.assertIn(("Apple", "IN_QUARTER", "Q1 2024"), preds)

    def test_structured_fallback_used(self):
        # Typed returns zero, structured has content
        typed_payload = {"relations": []}
        structured_payload = {
            "relations": [
                {
                    "subject": "Apple",
                    "predicate": "HAS_REVENUE",
                    "object": "$4.4 billion",
                    "confidence": 0.88,
                }
            ]
        }
        fake = FakeProvider(typed_payload=typed_payload, structured_payload=structured_payload)
        self._monkeypatch_provider(fake)

        rels = extract_relations_llm(
            text=self.text,
            entities=self.entities,
            provider="groq",
            model="llama-3.1-8b-instant",
            relation_types=["HAS_REVENUE"],
            verbose=True,
        )
        self.assertEqual(len(rels), 1, "Expected fallback to structured JSON to yield one relation")
        r = rels[0]
        self.assertEqual(r.subject.text, "Apple")
        self.assertEqual(r.object.text, "$4.4 billion")
        self.assertEqual(r.predicate, "HAS_REVENUE")


if __name__ == "__main__":
    unittest.main()
