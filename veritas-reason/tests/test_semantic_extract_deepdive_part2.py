import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritasreason.semantic_extract.named_entity_recognizer import (
    NamedEntityRecognizer, EntityClassifier, EntityConfidenceScorer, CustomEntityDetector
)
from veritasreason.semantic_extract.ner_extractor import NERExtractor, Entity
from veritasreason.semantic_extract.relation_extractor import RelationExtractor, Relation
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor, Triplet
from veritasreason.semantic_extract.event_detector import EventDetector, Event
from veritasreason.semantic_extract.semantic_analyzer import SemanticAnalyzer, SemanticRole
from veritasreason.semantic_extract.methods import (
    extract_entities_regex, extract_entities_rules,
    extract_relations_regex, extract_relations_dependency,
    extract_triplets_rules
)

pytestmark = pytest.mark.integration

class TestSemanticExtractDeepDivePart2(unittest.TestCase):

    def setUp(self):
        self.text = "Steve Jobs founded Apple Inc. in 1976."
        self.entities = [
            Entity(text="Steve Jobs", label="PERSON", start_char=0, end_char=10),
            Entity(text="Apple Inc.", label="ORG", start_char=19, end_char=29),
            Entity(text="1976", label="DATE", start_char=33, end_char=37)
        ]

    # --- Entity Classifier Tests ---

    def test_entity_classifier(self):
        """Test EntityClassifier type classification"""
        classifier = EntityClassifier()
        
        # Test type normalization
        e1 = Entity(text="Steve", label="PER", start_char=0, end_char=5)
        type1 = classifier.classify_entity_type(e1)
        self.assertEqual(type1, "PERSON")
        
        e2 = Entity(text="Apple", label="ORGANIZATION", start_char=0, end_char=5)
        type2 = classifier.classify_entity_type(e2)
        self.assertEqual(type2, "ORG")
        
        e3 = Entity(text="Unknown", label="CUSTOM", start_char=0, end_char=7)
        type3 = classifier.classify_entity_type(e3)
        self.assertEqual(type3, "CUSTOM")

    def test_entity_classifier_disambiguation(self):
        """Test EntityClassifier disambiguation"""
        classifier = EntityClassifier()
        
        target = Entity(text="Apple", label="ORG", start_char=0, end_char=5)
        candidates = [
            Entity(text="Apple", label="FRUIT", start_char=0, end_char=5, confidence=0.6),
            Entity(text="Apple", label="ORG", start_char=0, end_char=5, confidence=0.9),
            Entity(text="Apple", label="ORG", start_char=0, end_char=5, confidence=0.5)
        ]
        
        best = classifier.disambiguate_entity(target, candidates)
        self.assertIsNotNone(best)
        self.assertEqual(best.label, "ORG")
        self.assertEqual(best.confidence, 0.9)

    # --- Entity Confidence Scorer Tests ---

    def test_entity_confidence_scorer(self):
        """Test EntityConfidenceScorer"""
        scorer = EntityConfidenceScorer()
        
        # Test scoring adjustments
        e1 = Entity(text="s", label="PERSON", start_char=0, end_char=1) # Too short
        scored_e1 = scorer.score_entities([e1])[0]
        self.assertLess(scored_e1.confidence, 1.0)
        
        e2 = Entity(text="steve jobs", label="PERSON", start_char=0, end_char=10) # Lowercase person
        scored_e2 = scorer.score_entities([e2])[0]
        self.assertLess(scored_e2.confidence, 1.0)
        
        e3 = Entity(text="1999", label="DATE", start_char=0, end_char=4) # Digit date
        # Should be boosted (capped at 1.0)
        scored_e3 = scorer.score_entities([e3])[0]
        self.assertLessEqual(scored_e3.confidence, 1.0)

    # --- Custom Entity Detector Tests ---

    def test_custom_entity_detector(self):
        """Test CustomEntityDetector"""
        config = {
            "patterns": {
                "PROJECT": r"Project\s+[A-Z]\w+"
            }
        }
        detector = CustomEntityDetector(**config)
        text = "We are working on Project Apollo and Project Gemini."
        
        entities = detector.detect_custom_entities(text, "PROJECT")
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].text, "Project Apollo")
        self.assertEqual(entities[0].label, "PROJECT")
        self.assertEqual(entities[1].text, "Project Gemini")

    # --- Method Implementation Tests ---

    def test_extract_entities_regex(self):
        """Test regex-based entity extraction"""
        text = "Contact support@example.com or admin@test.org"
        patterns = {"EMAIL": r"[\w\.-]+@[\w\.-]+"}
        
        entities = extract_entities_regex(text, patterns=patterns)
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].label, "EMAIL")
        self.assertEqual(entities[0].text, "support@example.com")

    def test_extract_entities_rules(self):
        """Test rule-based entity extraction (sentence start rule)"""
        text = "Alice went to the park. Bob stayed home."
        # Assuming rule: Capitalized word at start of sentence is PERSON
        entities = extract_entities_rules(text)
        
        # This depends on exact implementation details in methods.py
        # Current impl: Checks first word of sentence
        names = [e.text for e in entities]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

    def test_extract_relations_regex(self):
        """Test regex-based relation extraction"""
        text = "London is located in UK"
        entities = [
            Entity(text="London", label="GPE", start_char=0, end_char=6),
            Entity(text="UK", label="GPE", start_char=21, end_char=23)
        ]
        
        relations = extract_relations_regex(text, entities)
        self.assertTrue(len(relations) > 0)
        self.assertEqual(relations[0].predicate, "located_in")

    @patch("veritasreason.semantic_extract.methods.SPACY_AVAILABLE", False)
    @patch("veritasreason.semantic_extract.methods.extract_relations_pattern")
    def test_extract_relations_dependency_fallback(self, mock_pattern):
        """Test dependency extraction fallback when spaCy is missing"""
        mock_pattern.return_value = []
        extract_relations_dependency("text", [])
        mock_pattern.assert_called_once()

    def test_extract_triplets_rules(self):
        """Test rule-based triplet extraction"""
        text = "Steve founded Apple"
        entities = [
            Entity(text="Steve", label="PERSON", start_char=0, end_char=5),
            Entity(text="Apple", label="ORG", start_char=14, end_char=19)
        ]
        
        triplets = extract_triplets_rules(text, entities)
        self.assertTrue(len(triplets) > 0)
        self.assertEqual(triplets[0].predicate, "founded")
        self.assertEqual(triplets[0].subject, "Steve")
        self.assertEqual(triplets[0].object, "Apple")

    # --- Event Detector Tests ---

    def test_event_detector_basic(self):
        """Test EventDetector basic flow"""
        # EventDetector uses internal patterns, so we test with text matching those patterns
        # Patterns include: founded, acquired, launched, etc.
        text = "Apple was founded by Steve Jobs in 1976."
        
        # Mock _extract_participants to avoid complex logic and potential flake
        # or just let it run if it's simple. It looks simple in the code.
        # But we must be careful.
        
        detector = EventDetector()
        events = detector.detect_events(text)
        
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[0].event_type, "founded")
        # Check if participants were extracted (simple capitalization rule)
        # "Steve" and "Jobs" should be captured.
        # The logic captures capitalized words > 2 chars.
        # "Apple" (if in context), "Steve", "Jobs" might be captured.
        
        # We'll check if "Steve" or "Jobs" is in participants list
        participants = events[0].participants
        self.assertTrue(any("Steve" in p for p in participants) or any("Jobs" in p for p in participants))

    # --- Semantic Analyzer Tests ---

    def test_semantic_analyzer_similarity(self):
        """Test SemanticAnalyzer similarity"""
        analyzer = SemanticAnalyzer()
        # Jaccard similarity
        s1 = "apple banana"
        s2 = "apple orange"
        score = analyzer.calculate_similarity(s1, s2, method="jaccard")
        # intersection: apple (1), union: apple, banana, orange (3) -> 1/3 ~ 0.33
        self.assertAlmostEqual(score, 1/3)

    # --- Coreference Resolver Tests ---

    def test_coreference_resolver_pronouns(self):
        """Test CoreferenceResolver pronoun resolution"""
        from veritasreason.semantic_extract.coreference_resolver import CoreferenceResolver, Mention
        
        resolver = CoreferenceResolver()
        
        # "Steve Jobs founded Apple. He was the CEO."
        # We need to manually construct mentions because we are testing the resolver logic
        # independent of the entity extractor for this unit test
        
        mentions = [
            Mention(text="Steve Jobs", start_char=0, end_char=10, mention_type="entity", entity_id="e1"),
            Mention(text="Apple", start_char=19, end_char=24, mention_type="entity", entity_id="e2"),
            Mention(text="He", start_char=26, end_char=28, mention_type="pronoun")
        ]
        
        text = "Steve Jobs founded Apple. He was the CEO."
        
        # Use the pronoun resolver directly or via main resolver
        resolutions = resolver.pronoun_resolver.resolve_pronouns(text, mentions)
        
        self.assertTrue(len(resolutions) > 0)
        # Should resolve "He" to "Steve Jobs" (closest preceding entity)
        self.assertEqual(resolutions[0][0], "He")
        self.assertEqual(resolutions[0][1], "Steve Jobs")

if __name__ == "__main__":
    unittest.main()
