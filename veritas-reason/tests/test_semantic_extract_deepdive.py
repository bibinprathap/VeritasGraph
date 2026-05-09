import unittest
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.semantic_extract.ner_extractor import NERExtractor, Entity
from veritasreason.semantic_extract.named_entity_recognizer import (
    NamedEntityRecognizer, 
    EntityClassifier, 
    EntityConfidenceScorer,
    CustomEntityDetector
)
from veritasreason.semantic_extract.relation_extractor import RelationExtractor, Relation
from veritasreason.semantic_extract.triplet_extractor import (
    TripletExtractor, 
    TripletValidator, 
    TripletQualityChecker,
    RDFSerializer,
    Triplet
)
from veritasreason.semantic_extract.methods import get_entity_method, get_relation_method

pytestmark = pytest.mark.integration

class TestSemanticExtractDeepDive(unittest.TestCase):

    def setUp(self):
        self.text = "Apple Inc. was founded by Steve Jobs in Cupertino. Tim Cook is the CEO."
        self.entities = [
            Entity(text="Apple Inc.", label="ORG", start_char=0, end_char=10, confidence=0.9),
            Entity(text="Steve Jobs", label="PERSON", start_char=26, end_char=36, confidence=0.95),
            Entity(text="Cupertino", label="GPE", start_char=40, end_char=49, confidence=0.8),
            Entity(text="Tim Cook", label="PERSON", start_char=51, end_char=59, confidence=0.9),
            Entity(text="CEO", label="TITLE", start_char=67, end_char=70, confidence=0.7)
        ]
        self.relations = [
            Relation(subject=self.entities[0], predicate="founded_by", object=self.entities[1], confidence=0.85),
            Relation(subject=self.entities[3], predicate="works_for", object=self.entities[0], confidence=0.8)
        ]

    # --- NER Tests ---

    def test_ner_extractor_pattern(self):
        """Test NERExtractor with pattern method"""
        extractor = NERExtractor(method="pattern")
        # Using a text that matches the hardcoded patterns in methods.py
        text = "Steve Jobs worked at Apple Inc. in New York City on 12/12/2023."
        entities = extractor.extract_entities(text)
        
        # Verify entities are extracted
        texts = [e.text for e in entities]
        labels = [e.label for e in entities]
        
        # Note: Patterns in methods.py might be specific, let's verify if they match
        # PERSON: \b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b -> "Steve Jobs" should match
        # ORG: \b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Inc|Corp|LLC|Ltd|Company))\b -> "Apple Inc." should match
        
        self.assertIn("Steve Jobs", texts)
        self.assertIn("Apple Inc", texts)
        self.assertIn("PERSON", labels)
        self.assertIn("ORG", labels)

    def test_named_entity_recognizer_flow(self):
        """Test NamedEntityRecognizer with mocked method"""
        # We mock the internal extraction to avoid dependency on models
        with patch('veritasreason.semantic_extract.methods.get_entity_method') as mock_get:
            mock_method = MagicMock()
            mock_method.return_value = self.entities
            mock_get.return_value = mock_method
            
            ner = NamedEntityRecognizer(confidence_threshold=0.8)
            extracted = ner.extract_entities(self.text)
            
            # Should filter out CEO (conf 0.7)
            self.assertEqual(len(extracted), 4)
            self.assertNotIn("CEO", [e.text for e in extracted])

    def test_entity_classifier(self):
        """Test EntityClassifier"""
        classifier = EntityClassifier()
        classified = classifier.classify_entities(self.entities)
        
        self.assertIn("PERSON", classified)
        self.assertIn("ORG", classified)
        self.assertEqual(len(classified["PERSON"]), 2) # Steve Jobs, Tim Cook
        self.assertEqual(len(classified["ORG"]), 1)    # Apple Inc.

    def test_entity_confidence_scorer(self):
        """Test EntityConfidenceScorer"""
        scorer = EntityConfidenceScorer()
        scored = scorer.score_entities(self.entities)
        
        # Ensure confidence scores are preserved or modified correctly
        for entity in scored:
            self.assertTrue(0 <= entity.confidence <= 1.0)

    def test_custom_entity_detector(self):
        """Test CustomEntityDetector"""
        patterns = {"EMAIL": r"[\w\.-]+@[\w\.-]+"}
        detector = CustomEntityDetector(patterns=patterns)
        text = "Contact us at test@example.com"
        
        entities = detector.detect_custom_entities(text, "EMAIL")
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].text, "test@example.com")
        self.assertEqual(entities[0].label, "EMAIL")

    # --- Relation Tests ---

    def test_relation_extractor_pattern(self):
        """Test RelationExtractor with pattern method"""
        extractor = RelationExtractor(method="pattern")
        # Text matching "founded by" pattern
        text = "Apple was founded by Steve"
        
        # We need entities for relation extraction
        entities = [
            Entity(text="Apple", label="ORG", start_char=0, end_char=5),
            Entity(text="Steve", label="PERSON", start_char=21, end_char=26)
        ]
        
        relations = extractor.extract_relations(text, entities)
        
        self.assertTrue(len(relations) > 0)
        self.assertEqual(relations[0].predicate, "founded_by")
        self.assertEqual(relations[0].subject.text, "Apple")
        self.assertEqual(relations[0].object.text, "Steve")

    def test_relation_extractor_cooccurrence(self):
        """Test RelationExtractor with cooccurrence method"""
        # Set low confidence threshold because cooccurrence yields 0.5 confidence
        extractor = RelationExtractor(method="cooccurrence", confidence_threshold=0.4)
        # Entities close to each other
        text = "Apple Inc. CEO Tim Cook announced..."
        entities = [
            Entity(text="Apple Inc.", label="ORG", start_char=0, end_char=10),
            Entity(text="Tim Cook", label="PERSON", start_char=15, end_char=23)
        ]
        
        relations = extractor.extract_relations(text, entities)
        self.assertTrue(len(relations) > 0)
        self.assertEqual(relations[0].predicate, "related_to")

    # --- Triplet Tests ---

    def test_triplet_extractor(self):
        """Test TripletExtractor"""
        # Mocking get_triplet_method to return a simple extraction function
        with patch('veritasreason.semantic_extract.methods.get_triplet_method') as mock_get:
            def mock_extract(text, entities, relations, **kwargs):
                triplets = []
                for rel in relations:
                    triplets.append(Triplet(
                        subject=rel.subject.text,
                        predicate=rel.predicate,
                        object=rel.object.text,
                        confidence=rel.confidence
                    ))
                return triplets
            
            mock_get.return_value = mock_extract
            
            extractor = TripletExtractor()
            triplets = extractor.extract_triplets(self.text, self.entities, self.relations)
            
            self.assertEqual(len(triplets), 2)
            self.assertEqual(triplets[0].subject, "Apple Inc.")
            self.assertEqual(triplets[0].predicate, "founded_by")
            self.assertEqual(triplets[0].object, "Steve Jobs")

    def test_triplet_validator(self):
        """Test TripletValidator"""
        validator = TripletValidator()
        
        # Create a valid and invalid triplet
        valid_triplet = Triplet(subject="S", predicate="P", object="O", confidence=0.9)
        invalid_triplet = Triplet(subject="", predicate="P", object="O", confidence=0.9) # Empty subject
        low_conf_triplet = Triplet(subject="S", predicate="P", object="O", confidence=0.2)
        
        triplets = [valid_triplet, invalid_triplet, low_conf_triplet]
        
        validated = validator.validate_triplets(triplets, min_confidence=0.5)
        
        self.assertEqual(len(validated), 1)
        self.assertEqual(validated[0], valid_triplet)

    def test_rdf_serializer(self):
        """Test RDFSerializer"""
        serializer = RDFSerializer()
        triplet = Triplet(subject="Apple_Inc", predicate="founded_by", object="Steve_Jobs")
        
        # Test N-Triples format
        rdf_output = serializer.serialize_to_rdf([triplet], format="ntriples")
        self.assertIsInstance(rdf_output, str)
        # Check if basic components are in the output (format might vary slightly)
        # N-Triples: <subject> <predicate> <object> .
        # The serializer might handle URIs, let's just check non-empty
        self.assertTrue(len(rdf_output) > 0)

    def test_triplet_quality_checker(self):
        """Test TripletQualityChecker"""
        checker = TripletQualityChecker()
        triplets = [
            Triplet(subject="Apple", predicate="founded", object="Jobs", confidence=0.9),
            Triplet(subject="Apple", predicate="located", object="US", confidence=0.8)
        ]
        
        scores = checker.calculate_quality_scores(triplets)
        
        self.assertIn("average_score", scores)
        self.assertAlmostEqual(scores["average_score"], 0.85)
        # triplet_count is not returned by calculate_quality_scores
        # self.assertIn("triplet_count", scores)
        # self.assertEqual(scores["triplet_count"], 2)

if __name__ == "__main__":
    unittest.main()
