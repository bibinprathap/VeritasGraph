
import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritasreason.semantic_extract.triplet_extractor import (
    TripletExtractor, Triplet, TripletValidator, RDFSerializer, TripletQualityChecker
)
from veritasreason.semantic_extract.ner_extractor import Entity
from veritasreason.semantic_extract.relation_extractor import Relation

class TestSemanticExtractTriplets(unittest.TestCase):

    def setUp(self):
        self.entities = [
            Entity(text="Steve Jobs", label="PERSON", start_char=0, end_char=10),
            Entity(text="Apple", label="ORG", start_char=19, end_char=24)
        ]
        self.relations = [
            Relation(
                subject=self.entities[0],
                predicate="founded",
                object=self.entities[1],
                confidence=0.9,
                context="Steve Jobs founded Apple."
            )
        ]
        self.triplets = [
            Triplet(subject="Steve_Jobs", predicate="founded", object="Apple", confidence=0.9),
            Triplet(subject="Apple", predicate="located_in", object="Cupertino", confidence=0.8)
        ]

    # --- Triplet Extractor Tests ---

    def test_triplet_extractor_init(self):
        """Test TripletExtractor initialization"""
        extractor = TripletExtractor()
        self.assertIsNotNone(extractor.triplet_validator)
        self.assertIsNotNone(extractor.rdf_serializer)
        self.assertIsNotNone(extractor.quality_checker)

    def test_triplet_extractor_extract_from_relations(self):
        """Test extracting triplets by converting relations (fallback/default)"""
        extractor = TripletExtractor(method=[]) # No specific method, force fallback
        
        # Mocking progress tracker to avoid console clutter/errors
        extractor.progress_tracker = MagicMock()
        
        triplets = extractor.extract_triplets(
            text="Steve Jobs founded Apple.",
            entities=self.entities,
            relations=self.relations
        )
        
        self.assertEqual(len(triplets), 1)
        # Predicate is formatted as URI
        self.assertTrue(triplets[0].predicate.endswith("founded") or triplets[0].predicate == "founded")
        # Check URI formatting (simple implementation in _format_uri)
        # "Steve Jobs" -> "Steve_Jobs", prepended with http://example.org/ if not http
        self.assertIn("Steve_Jobs", triplets[0].subject)

    # --- Triplet Validator Tests ---

    def test_triplet_validator_valid(self):
        """Test TripletValidator with valid triplet"""
        validator = TripletValidator()
        triplet = Triplet(subject="S", predicate="P", object="O", confidence=0.9)
        self.assertTrue(validator.validate_triplet(triplet))

    def test_triplet_validator_invalid_structure(self):
        """Test TripletValidator with missing fields"""
        validator = TripletValidator()
        triplet = Triplet(subject="", predicate="P", object="O") # Empty subject
        self.assertFalse(validator.validate_triplet(triplet))

    def test_triplet_validator_low_confidence(self):
        """Test TripletValidator confidence threshold"""
        validator = TripletValidator()
        triplet = Triplet(subject="S", predicate="P", object="O", confidence=0.4)
        self.assertFalse(validator.validate_triplet(triplet, min_confidence=0.5))

    # --- RDF Serializer Tests ---

    def test_rdf_serializer_turtle(self):
        """Test RDF serialization to Turtle"""
        serializer = RDFSerializer()
        output = serializer.serialize_to_rdf(self.triplets, format="turtle")
        self.assertIn("@prefix", output)
        self.assertIn("Steve_Jobs", output)
        self.assertIn("founded", output)
        self.assertIn("Apple", output)
        self.assertTrue(output.strip().endswith("."))

    def test_rdf_serializer_ntriples(self):
        """Test RDF serialization to N-Triples"""
        serializer = RDFSerializer()
        output = serializer.serialize_to_rdf(self.triplets, format="ntriples")
        self.assertNotIn("@prefix", output)
        self.assertIn("<Steve_Jobs>", output)
        self.assertIn("<founded>", output)

    def test_rdf_serializer_jsonld(self):
        """Test RDF serialization to JSON-LD"""
        serializer = RDFSerializer()
        output = serializer.serialize_to_rdf(self.triplets, format="jsonld")
        import json
        data = json.loads(output)
        self.assertIn("@graph", data)
        self.assertEqual(len(data["@graph"]), 2)

    def test_rdf_serializer_xml(self):
        """Test RDF serialization to XML"""
        serializer = RDFSerializer()
        output = serializer.serialize_to_rdf(self.triplets, format="xml")
        self.assertIn("rdf:RDF", output)
        self.assertIn("rdf:Description", output)

    # --- Triplet Quality Checker Tests ---

    def test_triplet_quality_checker_assess(self):
        """Test TripletQualityChecker assessment"""
        checker = TripletQualityChecker()
        triplet = Triplet(subject="S", predicate="P", object="O", confidence=0.85)
        assessment = checker.assess_triplet_quality(triplet)
        
        self.assertEqual(assessment["confidence"], 0.85)
        self.assertEqual(assessment["completeness"], 1.0)
        self.assertEqual(assessment["quality_score"], 0.85)

    def test_triplet_quality_checker_stats(self):
        """Test TripletQualityChecker statistics"""
        checker = TripletQualityChecker()
        stats = checker.calculate_quality_scores(self.triplets)
        
        # Implementation returns average_score, min_score, max_score, high_quality, medium_quality, low_quality
        self.assertIn("average_score", stats)
        self.assertIn("high_quality", stats) # 0.9 and 0.8 are >= 0.8
        self.assertEqual(stats["high_quality"], 2)

if __name__ == '__main__':
    unittest.main()
