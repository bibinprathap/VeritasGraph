
import pytest
import sys

from veritasreason.semantic_extract.ner_extractor import NERExtractor, Entity
from veritasreason.semantic_extract.relation_extractor import RelationExtractor, Relation
from veritasreason.semantic_extract.triplet_extractor import TripletExtractor

class TestRobustnessFallback:
    
    def test_ner_last_resort_fallback(self):
        """Test that NER extractor finds entities even in obscure text via last resort."""
        extractor = NERExtractor()
        
        # Text with single capitalized word that shouldn't match PERSON pattern (requires 2+ words)
        text = "Zylophone"
        
        entities = extractor.extract_entities(text)
        
        assert len(entities) > 0, "Should have extracted at least one entity via last resort"
        # Check if they are the capitalized words
        texts = [e.text for e in entities]
        assert "Zylophone" in texts
        
        # Verify metadata
        for e in entities:
            assert e.metadata is not None
            assert "extraction_method" in e.metadata
            # Should be last_resort_pattern
            assert e.metadata["extraction_method"] == "last_resort_pattern"
    
    def test_relation_last_resort_fallback(self):
        """Test that Relation extractor creates adjacency relations when no patterns match."""
        extractor = RelationExtractor()
        
        # Create entities far apart to avoid "co_occurrence" fallback which triggers < 100 chars
        padding = " " * 105
        text = f"Alpha{padding}Beta{padding}Gamma"
        
        # Alpha at start
        e1_start = 0
        e1_end = 5
        
        # Beta after padding
        e2_start = e1_end + 105
        e2_end = e2_start + 4
        
        # Gamma after padding
        e3_start = e2_end + 105
        e3_end = e3_start + 5
        
        e1 = Entity(text="Alpha", label="UNKNOWN", start_char=e1_start, end_char=e1_end)
        e2 = Entity(text="Beta", label="UNKNOWN", start_char=e2_start, end_char=e2_end)
        e3 = Entity(text="Gamma", label="UNKNOWN", start_char=e3_start, end_char=e3_end)
        
        entities = [e1, e2, e3]
        
        # This text has no "is a", "works for", etc. patterns.
        # And entities are too far for co-occurrence (< 100).
        # It should trigger the last resort adjacency fallback.
        relations = extractor.extract_relations(text, entities)
        
        assert len(relations) > 0, "Should have extracted relations via last resort"
        
        # Expect relations between adjacent entities: Alpha->Beta, Beta->Gamma
        pairs = [(r.subject.text, r.object.text) for r in relations]
        assert ("Alpha", "Beta") in pairs
        assert ("Beta", "Gamma") in pairs
        
        # Verify metadata
        for r in relations:
            assert r.metadata is not None
            assert "extraction_method" in r.metadata
            assert r.metadata.get("extraction_method") == "last_resort_adjacency"

    def test_triplet_fallback_conversion(self):
        """Test that Triplet extractor falls back to converting relations if extraction fails."""
        # Setup mocks or use real classes
        ner = NERExtractor() # We'll just pass entities directly
        rel_extractor = RelationExtractor()
        triplet_extractor = TripletExtractor()
        
        text = "Alpha is connected to Beta."
        e1 = Entity(text="Alpha", label="Thing", start_char=0, end_char=5)
        e2 = Entity(text="Beta", label="Thing", start_char=22, end_char=26)
        entities = [e1, e2]
        
        # Create a relation manually to ensure we have one to convert
        relation = Relation(
            subject=e1,
            predicate="connected_to",
            object=e2,
            confidence=0.9,
            context=text
        )
        
        # We want to test the fallback in extract_triplets.
        # Since we can't easily force the primary triplet method to return empty without mocking,
        # we can pass the relations explicitly and rely on the fact that standard triplet extraction
        # might not support "connected_to" if it relies on strict patterns, or we can use a method that fails.
        
        # However, the triplet extractor calls relation extractor internally if not provided.
        # Let's test the flow where we provide relations.
        
        triplets = triplet_extractor.extract_triplets(text, entities=entities, relations=[relation])
        
        assert len(triplets) > 0
        assert triplets[0].subject == "Alpha"
        assert triplets[0].object == "Beta"
        assert triplets[0].predicate == "connected_to"
        
    def test_batch_metadata_propagation(self):
        """Verify batch_index and document_id are propagated in batch mode with fallbacks."""
        ner = NERExtractor()
        
        docs = [
            {"content": "First doc", "id": "doc_1"},
            {"content": "Second doc", "id": "doc_2"}
        ]
        
        # These docs are simple, might trigger fallback or simple patterns
        results = ner.extract(docs)
        
        assert len(results) == 2
        
        # Check first doc results
        for e in results[0]:
            assert e.metadata["batch_index"] == 0
            assert e.metadata["document_id"] == "doc_1"
            
        # Check second doc results
        for e in results[1]:
            assert e.metadata["batch_index"] == 1
            assert e.metadata["document_id"] == "doc_2"

if __name__ == "__main__":
    # Manually run if executed as script
    t = TestRobustnessFallback()
    try:
        t.test_ner_last_resort_fallback()
        print("NER Fallback Test Passed")
        t.test_relation_last_resort_fallback()
        print("Relation Fallback Test Passed")
        t.test_triplet_fallback_conversion()
        print("Triplet Fallback Test Passed")
        t.test_batch_metadata_propagation()
        print("Batch Metadata Test Passed")
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
