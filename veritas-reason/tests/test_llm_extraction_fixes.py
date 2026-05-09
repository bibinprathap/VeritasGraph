import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os
import importlib

# Add parent directory to sys.path to import veritasreason
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PARENT_DIR)

# Import modules
import veritasreason.utils.exceptions
import veritasreason.semantic_extract.methods
import veritasreason.semantic_extract.triplet_extractor

from veritasreason.semantic_extract.methods import extract_entities_llm, extract_relations_llm, extract_triplets_llm
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor, Triplet
from veritasreason.semantic_extract.ner_extractor import Entity
from veritasreason.utils.exceptions import ProcessingError

print(f"\nDEBUG: PARENT_DIR: {PARENT_DIR}")
print(f"DEBUG: sys.path[0]: {sys.path[0]}")
print(f"DEBUG: veritasreason.semantic_extract.methods file: {veritasreason.semantic_extract.methods.__file__}")
print(f"DEBUG: veritasreason.semantic_extract.triplet_extractor file: {veritasreason.semantic_extract.triplet_extractor.__file__}")

class TestLLMExtractionFixes(unittest.TestCase):

    @patch('veritasreason.semantic_extract.methods.create_provider')
    def test_raise_by_default(self, mock_create):
        """Test that methods raise ProcessingError by default on failure."""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.generate_typed.side_effect = ProcessingError("LLM Error")
        mock_create.return_value = mock_llm

        try:
            extract_entities_llm("test text", provider="openai")
            self.fail("ProcessingError not raised")
        except ProcessingError as e:
            pass

    @patch('veritasreason.semantic_extract.methods.create_provider')
    def test_silent_fail_parameter(self, mock_create):
        """Test that silent_fail=True returns empty list instead of raising."""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.generate_typed.side_effect = Exception("LLM Error")
        mock_create.return_value = mock_llm

        entities = extract_entities_llm("test text", provider="openai", silent_fail=True)
        self.assertEqual(entities, [])

    @patch('veritasreason.semantic_extract.methods.create_provider')
    def test_empty_text_validation(self, mock_create):
        """Test that empty text raises error or returns [] based on silent_fail."""
        with self.assertRaises(ProcessingError):
            extract_entities_llm("", provider="openai")
        
        self.assertEqual(extract_entities_llm("", provider="openai", silent_fail=True), [])

    def test_triplet_extractor_shadowing_fix(self):
        """Test that TripletExtractor.validate_triplets is not shadowed by an attribute."""
        extractor = TripletExtractor(validate=True)
        
        # DEBUG
        import inspect
        source = inspect.getsource(extractor.__init__)
        print(f"\nTripletExtractor.__init__ source snippet:\n{source[:200]}")
        
        self.assertTrue(callable(extractor.validate_triplets), "validate_triplets should be a method, not a bool")
        
        # Test delegation
        triplets = [Triplet(subject="s", predicate="p", object="o", confidence=0.1)]
        validated = extractor.validate_triplets(triplets, min_confidence=0.5)
        self.assertEqual(len(validated), 0)

    @patch('veritasreason.semantic_extract.methods.create_provider')
    def test_chunking_detection(self, mock_create):
        """Test that long text triggers chunking."""
        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.generate_typed.return_value = MagicMock(entities=[]) # Mock response
        mock_create.return_value = mock_llm

        long_text = "This is a long text that should be chunked into multiple pieces."
        with patch('veritasreason.semantic_extract.methods._extract_entities_chunked') as mock_chunked:
            mock_chunked.return_value = []
            extract_entities_llm(long_text, max_text_length=10)
            mock_chunked.assert_called_once()

    @patch('veritasreason.semantic_extract.methods.create_provider')
    def test_relation_extraction_validation(self, mock_create):
        """Test that relation extraction validates entities list."""
        with self.assertRaises(ProcessingError):
            extract_relations_llm("text", entities=[], provider="openai")

if __name__ == '__main__':
    unittest.main()
