import os
import unittest
import time

from veritasreason.semantic_extract import NERExtractor, RelationExtractor

# Use environment variable for API key
_GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_TEST_API_KEY")
@unittest.skipUnless(_GROQ_KEY, "Groq key not set; skipping live integration test")
class TestGroqRelationsIntegration(unittest.TestCase):
    def setUp(self):
        self.api_key = _GROQ_KEY
        self.model = "llama-3.1-8b-instant"
        # Short, unambiguous finance snippet
        self.text_short = (
            "Apple reported revenue of $4.4 billion in Q1 2024 and provided guidance for FY 2025."
        )
        # Longer text to exercise chunking and ensure no hang
        self.text_long = (
            "Apple reported revenue of $4.4 billion in Q1 2024. "
            "The company also reported growth of 12% year-over-year and provided guidance for FY 2025. "
            "Microsoft reported revenue of $6.1 billion in Q2 2024 and expects sequential growth. "
            "NVIDIA reported record revenue in 2024 Q1 and guided for higher revenue in Q2 2024. "
        ) * 20  # expand length

    def _extract_entities(self, text):
        ner = NERExtractor(
            method="llm",
            provider="groq",
            llm_model=self.model,
            api_key=self.api_key,
            temperature=0.0,
        )
        entities = ner.extract_entities(text, entity_types=["ORGANIZATION", "MONEY", "DATE", "EVENT", "PERCENT"])
        self.assertIsInstance(entities, list)
        return entities

    def test_relations_short_text(self):
        entities = self._extract_entities(self.text_short)
        self.assertGreater(len(entities), 0, "NER should extract entities for short text")

        relation_extractor = RelationExtractor(
            method="llm",
            relation_types=[
                "HAS_REVENUE",
                "HAS_GROWTH",
                "PROVIDES_GUIDANCE",
                "IN_QUARTER",
                "FOR_PERIOD",
                "RELATED_TO",
            ],
            provider="groq",
            llm_model=self.model,
            api_key=self.api_key,
            temperature=0.0,
            verbose=True,
        )

        start = time.time()
        relations = relation_extractor.extract_relations(text=self.text_short, entities=entities)
        elapsed = time.time() - start

        self.assertIsInstance(relations, list)
        # Ensure call completes reasonably fast (network dependent; allow generous bound)
        self.assertLess(elapsed, 60, f"Extraction took too long: {elapsed:.2f}s")
        # Do not strictly assert >0 as model output may vary, but log for diagnostics
        if relations:
            sample = relations[0]
            self.assertTrue(hasattr(sample, "subject") and hasattr(sample, "predicate") and hasattr(sample, "object"))

    def test_relations_long_text_chunking(self):
        entities = self._extract_entities(self.text_long)
        self.assertGreater(len(entities), 0, "NER should extract entities for long text")

        relation_extractor = RelationExtractor(
            method="llm",
            relation_types=["RELATED_TO", "HAS_REVENUE", "IN_QUARTER"],
            provider="groq",
            llm_model=self.model,
            api_key=self.api_key,
            temperature=0.0,
            verbose=True,
        )

        start = time.time()
        relations = relation_extractor.extract_relations(text=self.text_long, entities=entities)
        elapsed = time.time() - start

        self.assertIsInstance(relations, list)
        # Ensure completion (chunked path) and no hang
        self.assertLess(elapsed, 120, f"Chunked extraction took too long: {elapsed:.2f}s")
        if relations:
            for r in relations[:3]:
                self.assertTrue(hasattr(r, "subject") and hasattr(r, "predicate") and hasattr(r, "object"))


if __name__ == "__main__":
    unittest.main()
