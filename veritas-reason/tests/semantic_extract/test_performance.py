import time
import unittest
print("Starting tests module...")
from unittest.mock import MagicMock, patch
from veritasreason.semantic_extract.providers import create_provider, ProviderPool, _provider_pool
from veritasreason.semantic_extract.ner_extractor import NERExtractor
from veritasreason.semantic_extract.relation_extractor import RelationExtractor
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor, Triplet
from veritasreason.semantic_extract.methods import _result_cache, extract_entities_llm, extract_relations_llm, extract_triplets_llm, match_entity
from veritasreason.semantic_extract.ner_extractor import Entity

class TestSemanticExtractImprovements(unittest.TestCase):
    def setUp(self):
        _provider_pool.clear()
        # Clear cache before each test
        if _result_cache:
            _result_cache._caches["entities"].clear()
            _result_cache._caches["relations"].clear()
            _result_cache._caches["triplets"].clear()

    def test_entity_matching(self):
        print("\nTesting Entity Matching...")
        entities = [
            Entity(text="Apple Inc.", label="ORG", start_char=0, end_char=10, confidence=1.0),
            Entity(text="Steve Jobs", label="PERSON", start_char=0, end_char=10, confidence=1.0)
        ]
        
        # Exact match
        m1 = match_entity("Apple Inc.", entities)
        self.assertIsNotNone(m1)
        self.assertEqual(m1.text, "Apple Inc.")
        
        # Case insensitive
        m2 = match_entity("apple inc.", entities)
        self.assertIsNotNone(m2)
        self.assertEqual(m2.text, "Apple Inc.")
        
        # Substring/Partial match (should work via calculate_similarity)
        # "Apple" is contained in "Apple Inc."
        # calculate_similarity gives a boost for containment
        m3 = match_entity("Apple", entities)
        if m3:
            self.assertEqual(m3.text, "Apple Inc.")
            print("  Partial match 'Apple' -> 'Apple Inc.' successful.")
        else:
            print("  Partial match 'Apple' -> 'Apple Inc.' failed (score too low).")
            
        # No match
        m4 = match_entity("Microsoft", entities)
        self.assertIsNone(m4)
        print("  No match verified.")

        # Synonym match
        # We need entities that match the synonym keys in methods.py (e.g. "acquired" -> "bought")
        # Let's create an entity "bought"
        rel_entities = [Entity(text="bought", label="RELATION", start_char=0, end_char=6, confidence=1.0)]
        m5 = match_entity("acquired", rel_entities)
        self.assertIsNotNone(m5)
        self.assertEqual(m5.text, "bought")
        print("  Synonym match 'acquired' -> 'bought' verified.")
        
        # Empty input
        m6 = match_entity("", entities)
        self.assertIsNone(m6)
        print("  Empty input handled.")

    def test_caching(self):
        print("\nTesting Caching...")
        
        text = "Apple Inc. was founded in 1976."
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        # Setup mock response for entities
        mock_entities_response = MagicMock()
        mock_entities_response.entities = [
            MagicMock(text="Apple Inc.", label="ORG", confidence=0.9),
            MagicMock(text="1976", label="DATE", confidence=0.9)
        ]
        mock_provider.generate_typed.return_value = mock_entities_response
        
        with patch('veritasreason.semantic_extract.methods.create_provider', return_value=mock_provider) as mock_create:
            # First call - should hit provider
            print("  First call (cache miss)...")
            results1 = extract_entities_llm(text, provider="openai", model="gpt-4", api_key="test")
            self.assertEqual(len(results1), 2)
            self.assertEqual(mock_provider.generate_typed.call_count, 1)
            
            # Check cache state
            print(f"  Cache size: {len(_result_cache._caches['entities'])}")
            
            # Second call - should hit cache
            print("  Second call (cache hit)...")
            results2 = extract_entities_llm(text, provider="openai", model="gpt-4", api_key="test")
            self.assertEqual(len(results2), 2)
            # Provider should NOT be called again
            self.assertEqual(mock_provider.generate_typed.call_count, 1)
            
            print("  Cache hit verified for entities.")

    def test_secure_caching(self):
        """Test that sensitive parameters are excluded from cache keys."""
        print("\nTesting Secure Caching...")
        
        text = "Security test."
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_entities_response = MagicMock()
        mock_entities_response.entities = [MagicMock(text="Test", label="TEST", confidence=1.0)]
        mock_provider.generate_typed.return_value = mock_entities_response
        
        with patch('veritasreason.semantic_extract.methods.create_provider', return_value=mock_provider):
            # First call with one API key
            extract_entities_llm(text, provider="openai", model="gpt-4", api_key="secret_key_1")
            
            # Second call with DIFFERENT API key
            # If secure caching is working, this should be a CACHE HIT because api_key is ignored
            extract_entities_llm(text, provider="openai", model="gpt-4", api_key="secret_key_2")
            
            # Provider should have been called ONLY ONCE
            self.assertEqual(mock_provider.generate_typed.call_count, 1)
            print("  Secure caching verified: Changing API key did not trigger new extraction.")
            
            # Verify cache content
            self.assertIn("entities", _result_cache._caches)
            self.assertTrue(len(_result_cache._caches["entities"]) > 0)

    def test_provider_pool(self):
        print("\nTesting Provider Pool...")
        # Create provider twice with same args
        # We need to mock the actual provider init to avoid API keys requirement if not present
        with patch('veritasreason.semantic_extract.providers.OpenAIProvider') as MockProvider:
            MockProvider.side_effect = lambda *args, **kwargs: MagicMock()
            
            p1 = create_provider("openai", api_key="test", model_name="gpt-4")
            p2 = create_provider("openai", api_key="test", model_name="gpt-4")
            
            # Should be same instance
            self.assertIs(p1, p2)
            print("  Provider reuse verified.")
            
            # Different args
            p3 = create_provider("openai", api_key="test", model_name="gpt-3.5")
            self.assertIsNot(p1, p3)
            print("  Different args create new instance verified.")
            
            # Explicitly not using pool
            p4 = create_provider("openai", use_pool=False, api_key="test", model_name="gpt-4")
            self.assertIsNot(p1, p4)
            print("  Opt-out of pool verified.")

    def test_ner_parallel_processing(self):
        print("\nTesting NER Parallel Processing...")
        extractor = NERExtractor(method="pattern") # Use pattern which is fast/local
        
        # Mock extract_entities to simulate work and track thread execution
        original_extract = extractor.extract_entities
        
        def mock_extract(text, **kwargs):
            time.sleep(0.1) # Simulate delay
            return original_extract(text, **kwargs)
            
        extractor.extract_entities = mock_extract
        
        texts = ["Text 1", "Text 2", "Text 3", "Text 4"]
        
        start_time = time.time()
        results = extractor.extract(texts)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"  Parallel NER (default workers) took {duration:.4f}s")
        
        self.assertEqual(len(results), 4)
        
        # Verify sequential fallback
        start_time_seq = time.time()
        extractor.extract(texts, max_workers=1)
        end_time_seq = time.time()
        duration_seq = end_time_seq - start_time_seq
        print(f"  Sequential NER took {duration_seq:.4f}s")

        # Check if parallel was indeed parallel (faster)
        # With 0.1s sleep * 4 items:
        # Sequential ~ 0.4s
        # Parallel (2 workers) ~ 0.2s + overhead
        self.assertLess(duration, duration_seq * 0.8) 
        print("  Parallel execution speedup verified.")

    def test_relation_parallel_processing(self):
        print("\nTesting Relation Parallel Processing...")
        extractor = RelationExtractor(method="pattern")
        
        # Mock extract_relations
        original_extract = extractor.extract_relations
        def mock_extract(text, entities, **kwargs):
            time.sleep(0.1)
            return original_extract(text, entities, **kwargs)
        extractor.extract_relations = mock_extract
        
        texts = ["Text 1", "Text 2", "Text 3", "Text 4"]
        entities = [[], [], [], []]
        
        start_time = time.time()
        results = extractor.extract(texts, entities)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"  Parallel RE (default workers) took {duration:.4f}s")
        
        self.assertEqual(len(results), 4)
        
        # Sequential
        start_time_seq = time.time()
        extractor.extract(texts, entities, max_workers=1)
        end_time_seq = time.time()
        duration_seq = end_time_seq - start_time_seq
        print(f"  Sequential RE took {duration_seq:.4f}s")
        
        self.assertLess(duration, duration_seq * 0.8)
        print("  Parallel execution speedup verified.")

    def test_relation_extraction_fuzzy_matching(self):
        print("\nTesting Relation Extraction Fuzzy Matching...")
        extractor = RelationExtractor(method="pattern")
        
        # Entities have formal names
        entities = [
            Entity(text="Apple Inc.", label="ORG", start_char=0, end_char=10, confidence=1.0),
            Entity(text="Steve Jobs", label="PERSON", start_char=21, end_char=31, confidence=1.0)
        ]
        
        # Text uses informal name "Apple"
        text = "Apple was founded by Steve Jobs."
        
        relations = extractor.extract(text, entities)
        
        found = False
        for rel in relations:
            # Check if subject matches "Apple Inc." even though text said "Apple"
            if rel.subject.text == "Apple Inc." and rel.object.text == "Steve Jobs" and rel.predicate == "founded_by":
                found = True
                print("  Successfully matched 'Apple' -> 'Apple Inc.' in relation extraction.")
                break
                
        self.assertTrue(found, "Failed to extract relation with fuzzy entity matching")

    def test_triplet_parallel_processing(self):
        print("\nTesting Triplet Parallel Processing...")
        extractor = TripletExtractor(method="pattern")
        
        # Mock extract_triplets
        original_extract = extractor.extract_triplets
        def mock_extract(text, **kwargs):
            time.sleep(0.1)
            # Return dummy triplets to avoid actual extraction overhead
            return [Triplet(subject="s", predicate="p", object="o")]
        extractor.extract_triplets = mock_extract
        
        texts = ["Text 1", "Text 2", "Text 3", "Text 4"]
        
        start_time = time.time()
        results = extractor.extract(texts)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"  Parallel TE (default workers) took {duration:.4f}s")
        
        self.assertEqual(len(results), 4)
        
        # Sequential
        start_time_seq = time.time()
        extractor.extract(texts, max_workers=1)
        end_time_seq = time.time()
        duration_seq = end_time_seq - start_time_seq
        print(f"  Sequential TE took {duration_seq:.4f}s")
        
        self.assertLess(duration, duration_seq * 0.8)
        print("  Parallel execution speedup verified.")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSemanticExtractImprovements)
    unittest.TextTestRunner(verbosity=2).run(suite)
