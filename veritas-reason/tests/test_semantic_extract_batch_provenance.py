
print("Starting tests module...")
import unittest
from unittest.mock import MagicMock, patch
try:
    from veritasreason.semantic_extract.semantic_network_extractor import SemanticNetworkExtractor, SemanticNetwork, SemanticNode, SemanticEdge
    from veritasreason.semantic_extract.event_detector import EventDetector, Event
    from veritasreason.semantic_extract.semantic_analyzer import SemanticAnalyzer
    from veritasreason.semantic_extract.coreference_resolver import CoreferenceResolver, CoreferenceChain, Mention
    from veritasreason.semantic_extract.ner_extractor import Entity
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")

class TestSemanticExtractBatch(unittest.TestCase):

    def setUp(self):
        # Mock progress tracker to avoid console spam
        self.tracker_patcher = patch('veritasreason.utils.progress_tracker.get_progress_tracker')
        self.mock_tracker_cls = self.tracker_patcher.start()
        self.mock_tracker = self.mock_tracker_cls.return_value
        self.mock_tracker.enabled = True
        self.mock_tracker.start_tracking.return_value = "tracking_id"

    def tearDown(self):
        self.tracker_patcher.stop()

    def test_semantic_network_batch(self):
        print("Running test_semantic_network_batch")
        from copy import deepcopy
        extractor = SemanticNetworkExtractor()
        
        # Mock extract_network
        mock_network = SemanticNetwork(
            nodes=[SemanticNode(id="1", label="test", type="test", metadata={})],
            edges=[SemanticEdge(source="1", target="1", label="self", metadata={})],
            metadata={}
        )
        # Use side_effect to return a fresh copy each time
        extractor.extract_network = MagicMock(side_effect=lambda *args, **kwargs: deepcopy(mock_network))
        
        # Test input
        docs = [{"content": "doc1", "id": "doc_1"}, {"content": "doc2", "id": "doc_2"}]
        
        # Run batch
        results = extractor.extract(docs)
        
        self.assertEqual(len(results), 2)
        # Check provenance
        self.assertEqual(results[0].metadata["batch_index"], 0)
        self.assertEqual(results[0].metadata["document_id"], "doc_1")
        self.assertEqual(results[0].nodes[0].metadata["batch_index"], 0)
        self.assertEqual(results[0].nodes[0].metadata["document_id"], "doc_1")
        
        self.assertEqual(results[1].metadata["batch_index"], 1)
        self.assertEqual(results[1].metadata["document_id"], "doc_2")

    def test_event_detector_batch(self):
        print("Running test_event_detector_batch")
        detector = EventDetector()
        
        # Mock detect_events
        mock_event = Event(
            text="event", event_type="test", start_char=0, end_char=5
        )
        detector.detect_events = MagicMock(return_value=[mock_event])
        
        docs = [{"content": "doc1", "id": "doc_1"}]
        
        results = detector.extract(docs)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0]), 1)
        self.assertEqual(results[0][0].metadata["batch_index"], 0)
        self.assertEqual(results[0][0].metadata["document_id"], "doc_1")

    def test_semantic_analyzer_batch(self):
        print("Running test_semantic_analyzer_batch")
        analyzer = SemanticAnalyzer()
        
        # Mock analyze_semantics
        mock_result = {
            "text": "test",
            "semantic_roles": [{"word": "test", "role": "agent"}]
        }
        analyzer.analyze_semantics = MagicMock(return_value=mock_result)
        
        docs = [{"content": "doc1", "id": "doc_1"}]
        
        results = analyzer.analyze(docs)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["batch_index"], 0)
        self.assertEqual(results[0]["document_id"], "doc_1")
        self.assertEqual(results[0]["semantic_roles"][0]["metadata"]["batch_index"], 0)
        self.assertEqual(results[0]["semantic_roles"][0]["metadata"]["document_id"], "doc_1")

    def test_coreference_resolver_batch(self):
        print("Running test_coreference_resolver_batch")
        resolver = CoreferenceResolver()
        
        # Mock resolve_coreferences
        mock_mention = Mention(text="he", start_char=0, end_char=2, mention_type="pronoun")
        mock_chain = CoreferenceChain(
            mentions=[mock_mention],
            representative=mock_mention
        )
        resolver.resolve_coreferences = MagicMock(return_value=[mock_chain])
        
        docs = [{"content": "doc1", "id": "doc_1"}]
        
        results = resolver.resolve(docs)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].mentions[0].metadata["batch_index"], 0)
        self.assertEqual(results[0][0].mentions[0].metadata["document_id"], "doc_1")
        self.assertEqual(results[0][0].representative.metadata["batch_index"], 0)
        self.assertEqual(results[0][0].representative.metadata["document_id"], "doc_1")

if __name__ == '__main__':
    print("Running main...")
    unittest.main()
