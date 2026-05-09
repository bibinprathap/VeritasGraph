import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.semantic_extract.ner_extractor import NERExtractor
from veritasreason.semantic_extract.ner_extractor import Entity as NEREntity
from veritasreason.semantic_extract.relation_extractor import RelationExtractor
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor
from veritasreason.semantic_extract.event_detector import EventDetector
from veritasreason.semantic_extract.semantic_analyzer import SemanticAnalyzer
from veritasreason.semantic_extract.semantic_network_extractor import SemanticNetworkExtractor
from veritasreason.semantic_extract.named_entity_recognizer import Entity
from veritasreason.semantic_extract.relation_extractor import Relation

class TestExtractors(unittest.TestCase):
    
    def test_ner_extractor_initialization(self):
        """Test NERExtractor initialization and circular import resolution"""
        try:
            extractor = NERExtractor(method="pattern")
            self.assertIsNotNone(extractor)
        except ImportError as e:
            self.fail(f"NERExtractor initialization failed with ImportError: {e}")

    def test_relation_extractor_initialization(self):
        """Test RelationExtractor initialization and circular import resolution"""
        try:
            extractor = RelationExtractor(method="pattern")
            self.assertIsNotNone(extractor)
        except ImportError as e:
            self.fail(f"RelationExtractor initialization failed with ImportError: {e}")

    def test_triplet_extractor_initialization(self):
        """Test TripletExtractor initialization and circular import resolution"""
        try:
            extractor = TripletExtractor(method="pattern")
            self.assertIsNotNone(extractor)
        except ImportError as e:
            self.fail(f"TripletExtractor initialization failed with ImportError: {e}")

    @patch("veritasreason.semantic_extract.methods.get_entity_method")
    def test_ner_extraction(self, mock_get_method):
        """Test NER extraction call"""
        mock_method = MagicMock()
        mock_method.extract_entities.return_value = []
        mock_get_method.return_value = mock_method
        
        extractor = NERExtractor(method="pattern")
        entities = extractor.extract_entities("Test text")
        
        self.assertIsInstance(entities, list)
        mock_get_method.assert_called()

    @patch("veritasreason.semantic_extract.methods.get_entity_method")
    def test_ner_extraction_batch_via_extract_entities(self, mock_get_method):
        mock_method = MagicMock()
        mock_method.extract_entities.return_value = []
        mock_get_method.return_value = mock_method

        extractor = NERExtractor(method="pattern")
        results = extractor.extract_entities(
            ["Test text 1", "Test text 2"],
        )

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, list) for r in results))

    @patch("veritasreason.semantic_extract.methods.get_relation_method")
    def test_relation_extraction(self, mock_get_method):
        """Test relation extraction call"""
        mock_method = MagicMock()
        mock_method.extract_relations.return_value = []
        mock_get_method.return_value = mock_method
        
        extractor = RelationExtractor(method="pattern")
        entities = [Entity(text="A", label="PERSON", start_char=0, end_char=1), Entity(text="B", label="PERSON", start_char=5, end_char=6)]
        relations = extractor.extract_relations("A knows B", entities)
        
        self.assertIsInstance(relations, list)
        mock_get_method.assert_called()

    @patch("veritasreason.semantic_extract.methods.get_relation_method")
    def test_relation_extraction_batch_via_extract_relations(self, mock_get_method):
        mock_method = MagicMock()
        mock_method.extract_relations.return_value = []
        mock_get_method.return_value = mock_method

        extractor = RelationExtractor(method="pattern")
        texts = ["A knows B", "A knows B"]
        entities = [NEREntity(text="A", label="PERSON", start_char=0, end_char=1, confidence=1.0)]

        results = extractor.extract_relations(texts, entities)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, list) for r in results))

    @patch("veritasreason.semantic_extract.methods.get_triplet_method")
    def test_triplet_extraction(self, mock_get_method):
        """Test triplet extraction call"""
        mock_method = MagicMock()
        mock_method.extract_triplets.return_value = []
        mock_get_method.return_value = mock_method
        
        extractor = TripletExtractor(method="pattern")
        entities = [Entity(text="A", label="PERSON", start_char=0, end_char=1)]
        relations = [Relation(subject=entities[0], object=entities[0], predicate="knows")]
        
        triplets = extractor.extract_triplets("A knows A", entities, relations)
        
        self.assertIsInstance(triplets, list)
        mock_get_method.assert_called()

    @patch("veritasreason.semantic_extract.methods.get_triplet_method")
    def test_triplet_extraction_batch_via_extract_triplets(self, mock_get_method):
        mock_method = MagicMock()
        mock_method.extract_triplets.return_value = []
        mock_get_method.return_value = mock_method

        extractor = TripletExtractor(method="pattern")
        texts = ["A knows A", "A knows A"]
        entities_batch = [[NEREntity(text="A", label="PERSON", start_char=0, end_char=1, confidence=1.0)] for _ in texts]
        relations_batch = [[] for _ in texts]

        results = extractor.extract_triplets(
            texts,
            entities=entities_batch,
            relations=relations_batch,
        )

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, list) for r in results))

    def test_event_detector_batch_via_detect_events(self):
        detector = EventDetector()
        texts = ["Apple acquired Beats in 2014.", "Google announced a partnership in 2023."]
        results = detector.detect_events(texts)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, list) for r in results))

    def test_semantic_analyzer_batch_parallel(self):
        analyzer = SemanticAnalyzer()
        texts = ["A short sentence.", "Another short sentence."]
        results = analyzer.analyze(texts)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, dict) for r in results))

    def test_semantic_network_batch_via_extract_network(self):
        extractor = SemanticNetworkExtractor()
        texts = ["A knows B.", "C knows D."]
        entities_batch = [[] for _ in texts]
        relations_batch = [[] for _ in texts]
        results = extractor.extract_network(
            texts,
            entities=entities_batch,
            relations=relations_batch,
        )
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)

if __name__ == "__main__":
    unittest.main()
