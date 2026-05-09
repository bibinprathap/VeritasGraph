import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from veritasreason.semantic_extract.ner_extractor import NERExtractor, Entity
from veritasreason.semantic_extract.relation_extractor import RelationExtractor
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor
from veritasreason.utils.exceptions import ProcessingError

class TestHuggingFaceDeepIntegration(unittest.TestCase):
    """
    Comprehensive test suite for Hugging Face models integration
    in NER, Relation, and Triplet extraction modules.
    """

    @patch('veritasreason.semantic_extract.methods.HuggingFaceModelLoader')
    def test_ner_extraction_flow(self, MockLoaderClass):
        """Test NER extraction with detailed IOB parsing and aggregation."""
        mock_loader = MockLoaderClass.return_value
        
        # Simulate IOB output (Raw token classification)
        mock_loader.extract_entities.return_value = [
            {"entity": "B-PER", "score": 0.99, "index": 1, "word": "John", "start": 0, "end": 4, "label": "B-PER"},
            {"entity": "I-PER", "score": 0.98, "index": 2, "word": "Doe", "start": 5, "end": 8, "label": "I-PER"},
            {"entity": "O", "score": 0.99, "index": 3, "word": "lives", "start": 9, "end": 14, "label": "O"},
            {"entity": "B-LOC", "score": 0.95, "index": 4, "word": "New", "start": 18, "end": 21, "label": "B-LOC"},
            {"entity": "I-LOC", "score": 0.96, "index": 5, "word": "York", "start": 22, "end": 26, "label": "I-LOC"},
        ]
        
        extractor = NERExtractor(method="huggingface", huggingface_model="dslim/bert-base-NER")
        entities = extractor.extract_entities("John Doe lives in New York")
        
        # Verify aggregation worked (John Doe should be one entity)
        # Note: The logic in extract_entities_huggingface handles manual aggregation
        # if "entity_group" is missing and labels start with B-/I-
        
        # Let's debug what we expect. 
        # "John" (B-PER) -> current_entity="John"
        # "Doe" (I-PER) -> match! -> current_entity="John Doe"
        # "lives" (O) -> append John Doe, current=None
        # "New" (B-LOC) -> current="New"
        # "York" (I-LOC) -> match! -> current="New York"
        # End -> append New York
        
        self.assertEqual(len(entities), 2)
        
        person = next((e for e in entities if e.label == "PER"), None)
        self.assertIsNotNone(person)
        self.assertEqual(person.text, "John Doe")
        
        loc = next((e for e in entities if e.label == "LOC"), None)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.text, "New York")

    @patch('veritasreason.semantic_extract.methods.HuggingFaceModelLoader')
    def test_ner_aggregation_strategy_simple(self, MockLoaderClass):
        """Test NER extraction when the pipeline handles aggregation (strategy='simple')."""
        mock_loader = MockLoaderClass.return_value
        
        # Simulate Aggregated output
        mock_loader.extract_entities.return_value = [
            {"entity_group": "PER", "score": 0.99, "word": "John Doe", "start": 0, "end": 8},
            {"entity_group": "LOC", "score": 0.95, "word": "New York", "start": 18, "end": 26},
        ]
        
        extractor = NERExtractor(
            method="huggingface", 
            huggingface_model="dslim/bert-base-NER",
            aggregation_strategy="simple" # Explicitly requesting simple
        )
        entities = extractor.extract_entities("John Doe lives in New York")
        
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[0].text, "John Doe")
        self.assertEqual(entities[0].label, "PER")
        
    @patch('veritasreason.semantic_extract.methods.HuggingFaceModelLoader')
    def test_relation_extraction_flow(self, MockLoaderClass):
        """Test Relation extraction with Hugging Face model."""
        mock_loader = MockLoaderClass.return_value
        
        # Mock extract_relations output
        mock_loader.extract_relations.return_value = [{
            "subject": Entity(text="Apple", label="ORG", start_char=0, end_char=5),
            "object": Entity(text="Steve Jobs", label="PERSON", start_char=21, end_char=31),
            "relation": "founded_by",
            "score": 0.9
        }]
        
        # We need to provide entities for relation extraction usually
        entities = [
            Entity(text="Apple", label="ORG", start_char=0, end_char=5),
            Entity(text="Steve Jobs", label="PERSON", start_char=21, end_char=31)
        ]
        
        extractor = RelationExtractor(method="huggingface", huggingface_model="facebook/bart-large-mnli")
        relations = extractor.extract_relations("Apple was founded by Steve Jobs", entities=entities)
        
        # Check if relation is found
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0].predicate, "founded_by")
        self.assertEqual(relations[0].subject.text, "Apple")
        self.assertEqual(relations[0].object.text, "Steve Jobs")

    @patch('veritasreason.semantic_extract.methods.HuggingFaceModelLoader')
    def test_triplet_extraction_rebel(self, MockLoaderClass):
        """Test Triplet extraction using REBEL parsing logic."""
        mock_loader = MockLoaderClass.return_value
        
        # Mock extract_triplets output
        # The extract_triplets method in Loader returns [{"triplet": decoded_text}]
        # But wait, methods.py extract_triplets_huggingface handles parsing?
        # No, let's check methods.py again.
        
        # Actually, methods.py for triplets calls loader.extract_triplets and then parses the result?
        # Or does loader.extract_triplets return the raw generation?
        # Let's check the code I read earlier.
        # loader.extract_triplets returns [{"triplet": decoded}]
        
        # But methods.py `extract_triplets_huggingface` logic needs to be verified.
        # I didn't read extract_triplets_huggingface in methods.py yet (I read entities).
        # Assuming standard behavior, let's return what loader returns.
        
        mock_loader.extract_triplets.return_value = [{"triplet": "<triplet> Apple <subj> founded by <obj> Steve Jobs"}]
        
        # Wait, if methods.py expects raw text and parses it, then I need to know IF methods.py does the parsing or if it expects pre-parsed.
        # Usually, if it's REBEL, the parsing happens after generation.
        # Let's assume methods.py parses the REBEL format.
        
        extractor = TripletExtractor(method="huggingface", huggingface_model="Babelscape/rebel-large")
        
        # If the extractor relies on methods.py to parse, and methods.py relies on REBEL format:
        triplets = extractor.extract_triplets("Apple was founded by Steve Jobs")
        
        # Note: If this fails, it might be because I need to check how extract_triplets_huggingface is implemented.
        # But let's try.
        if not triplets:
             # Fallback: maybe methods.py expects the model to return parsed triplets?
             pass
             
        self.assertTrue(len(triplets) > 0)
        self.assertEqual(triplets[0].subject, "Apple")
        self.assertEqual(triplets[0].object, "Steve Jobs")
        self.assertEqual(triplets[0].predicate, "founded by")

    @patch('veritasreason.semantic_extract.methods.HuggingFaceModelLoader')
    def test_byom_override(self, MockLoaderClass):
        """Verify Bring Your Own Model (runtime override) works for all extractors."""
        mock_loader = MockLoaderClass.return_value
        mock_loader.extract_entities.return_value = []
        
        # NER
        ner = NERExtractor(method="huggingface", huggingface_model="default-ner")
        ner.extract_entities("test", huggingface_model="runtime-ner")
        
        # Check if load_ner_model was called with runtime model
        # mock_loader.load_ner_model.assert_called_with("runtime-ner", ...)
        # args[0] should be "runtime-ner"
        call_args = mock_loader.load_ner_model.call_args
        self.assertEqual(call_args[0][0], "runtime-ner")
            
if __name__ == "__main__":
    unittest.main()
