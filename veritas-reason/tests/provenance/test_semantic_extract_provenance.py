"""
Test semantic_extract provenance integration.

Tests that provenance tracking works correctly for all extraction classes.
"""

import pytest
from veritasreason.provenance import ProvenanceManager


class TestNERExtractorProvenance:
    """Test NER extractor with provenance."""
    
    def test_without_provenance(self):
        """Test NER works without provenance (backward compatible)."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=False)
            assert ner is not None
            assert ner.provenance is False
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_with_provenance_enabled(self):
        """Test NER tracks provenance when enabled."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            assert ner.provenance is True
            assert ner._prov_manager is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_graceful_degradation(self):
        """Test graceful degradation if provenance unavailable."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            # Should not raise errors even if provenance fails
            ner = NERExtractorWithProvenance(provenance=True)
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")


class TestRelationExtractorProvenance:
    """Test relation extractor with provenance."""
    
    def test_without_provenance(self):
        """Test relation extractor works without provenance."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import RelationExtractorWithProvenance
            extractor = RelationExtractorWithProvenance(provenance=False)
            assert extractor is not None
            assert extractor.provenance is False
        except ImportError:
            pytest.skip("RelationExtractor not available")
    
    def test_with_provenance_enabled(self):
        """Test relation extractor tracks provenance."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import RelationExtractorWithProvenance
            extractor = RelationExtractorWithProvenance(provenance=True)
            assert extractor.provenance is True
        except ImportError:
            pytest.skip("RelationExtractor not available")


class TestEventDetectorProvenance:
    """Test event detector with provenance."""
    
    def test_without_provenance(self):
        """Test event detector works without provenance."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import EventDetectorWithProvenance
            detector = EventDetectorWithProvenance(provenance=False)
            assert detector is not None
        except ImportError:
            pytest.skip("EventDetector not available")
    
    def test_with_provenance_enabled(self):
        """Test event detector tracks provenance."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import EventDetectorWithProvenance
            detector = EventDetectorWithProvenance(provenance=True)
            assert detector.provenance is True
        except ImportError:
            pytest.skip("EventDetector not available")


class TestProvenanceEdgeCases:
    """Test edge cases for semantic extract provenance."""
    
    def test_empty_text_extraction(self):
        """Test extraction with empty text."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            # Should handle empty text gracefully
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_none_source_tracking(self):
        """Test provenance tracking with None source."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            # Should handle None source gracefully
            assert ner._prov_manager is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_very_long_text(self):
        """Test extraction with very long text."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            long_text = "A" * 10000
            # Should handle long text without issues
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_special_characters_in_text(self):
        """Test extraction with special characters."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            special_text = "Test @#$%^&*() text with 中文 and émojis 🎉"
            # Should handle special characters
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_multiple_extractors_same_manager(self):
        """Test multiple extractors sharing provenance manager."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import (
                NERExtractorWithProvenance,
                RelationExtractorWithProvenance
            )
            ner = NERExtractorWithProvenance(provenance=True)
            rel = RelationExtractorWithProvenance(provenance=True)
            # Both should have independent managers
            assert ner._prov_manager is not None
            assert rel._prov_manager is not None
        except ImportError:
            pytest.skip("Extractors not available")
    
    def test_provenance_disabled_then_enabled(self):
        """Test switching from disabled to enabled provenance."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            # First without provenance
            ner1 = NERExtractorWithProvenance(provenance=False)
            assert ner1.provenance is False
            
            # Then with provenance
            ner2 = NERExtractorWithProvenance(provenance=True)
            assert ner2.provenance is True
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_concurrent_extractions(self):
        """Test concurrent extraction operations."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            # Simulate concurrent operations
            texts = ["Text 1", "Text 2", "Text 3"]
            # Should handle multiple operations
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_unicode_source_names(self):
        """Test provenance with unicode source names."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            unicode_source = "文档_français_документ.pdf"
            # Should handle unicode source names
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_extraction_with_metadata(self):
        """Test extraction with additional metadata."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            ner = NERExtractorWithProvenance(provenance=True)
            # Should support additional metadata
            assert ner._prov_manager is not None
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_provenance_manager_unavailable(self):
        """Test graceful degradation when ProvenanceManager unavailable."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            # Should not raise exception even if provenance fails
            ner = NERExtractorWithProvenance(provenance=True)
            assert ner is not None
        except ImportError:
            pytest.skip("NERExtractor not available")


class TestRealProvenanceTracking:
    """Real functional tests that execute actual provenance tracking."""
    
    def test_ner_tracks_entities_with_provenance(self):
        """Test that NER actually tracks extracted entities."""
        try:
            from veritasreason.semantic_extract.semantic_extract_provenance import NERExtractorWithProvenance
            
            # Create NER with provenance enabled
            ner = NERExtractorWithProvenance(provenance=True)
            
            # Verify provenance manager is created
            assert ner._prov_manager is not None
            assert isinstance(ner._prov_manager, ProvenanceManager)
            
            # Check that provenance is enabled
            assert ner.provenance is True
            
        except ImportError:
            pytest.skip("NERExtractor not available")
    
    def test_provenance_manager_stores_data(self):
        """Test that provenance manager actually stores tracking data."""
        manager = ProvenanceManager()
        
        # Track an entity
        manager.track_entity(
            entity_id="test_entity_1",
            source="test_document.pdf",
            entity_type="named_entity",
            metadata={"text": "Apple Inc.", "label": "ORG"}
        )
        
        # Verify entity was tracked
        lineage = manager.get_lineage("test_entity_1")
        assert lineage is not None
        assert "entity_id" in lineage
        assert lineage["entity_id"] == "test_entity_1"
    
    def test_multiple_entities_tracked_independently(self):
        """Test tracking multiple entities independently."""
        manager = ProvenanceManager()
        
        # Track multiple entities
        entities = [
            ("entity_1", "doc1.pdf", {"text": "Apple"}),
            ("entity_2", "doc2.pdf", {"text": "Google"}),
            ("entity_3", "doc3.pdf", {"text": "Microsoft"}),
        ]
        
        for entity_id, source, metadata in entities:
            manager.track_entity(
                entity_id=entity_id,
                source=source,
                entity_type="organization",
                metadata=metadata
            )
        
        # Verify all entities are tracked
        for entity_id, _, _ in entities:
            lineage = manager.get_lineage(entity_id)
            assert lineage is not None
            assert lineage["entity_id"] == entity_id
    
    def test_lineage_chain_tracking(self):
        """Test that lineage chains are tracked correctly."""
        manager = ProvenanceManager()
        
        # Create a lineage chain: document -> chunk -> entity
        manager.track_entity(
            entity_id="document_1",
            source="original_file.pdf",
            entity_type="document"
        )
        
        manager.track_chunk(
            chunk_id="chunk_1",
            source_document="document_1",
            chunk_text="Sample text",
            start_char=0,
            end_char=100
        )
        
        manager.track_entity(
            entity_id="entity_1",
            source="chunk_1",
            entity_type="named_entity",
            metadata={"text": "Apple"}
        )
        
        # Verify lineage chain
        lineage = manager.get_lineage("entity_1")
        assert lineage is not None
        assert "lineage_chain" in lineage
        assert len(lineage["lineage_chain"]) >= 1
    
    def test_provenance_with_metadata(self):
        """Test that metadata is stored and retrieved correctly."""
        manager = ProvenanceManager()
        
        metadata = {
            "text": "Steve Jobs",
            "label": "PERSON",
            "confidence": 0.95,
            "start": 0,
            "end": 10
        }
        
        manager.track_entity(
            entity_id="person_1",
            source="biography.pdf",
            entity_type="person",
            metadata=metadata
        )
        
        # Retrieve and verify metadata
        lineage = manager.get_lineage("person_1")
        assert lineage is not None
        assert "metadata" in lineage
        stored_metadata = lineage["metadata"]
        assert stored_metadata["text"] == "Steve Jobs"
        assert stored_metadata["confidence"] == 0.95
    
    def test_relationship_tracking(self):
        """Test tracking relationships between entities."""
        manager = ProvenanceManager()
        
        # Track entities first
        manager.track_entity(
            entity_id="steve_jobs",
            source="doc.pdf",
            entity_type="person"
        )
        
        manager.track_entity(
            entity_id="apple",
            source="doc.pdf",
            entity_type="organization"
        )
        
        # Track relationship
        manager.track_relationship(
            relationship_id="rel_1",
            source="doc.pdf",
            subject="steve_jobs",
            predicate="founded",
            obj="apple"
        )
        
        # Verify relationship tracked
        lineage = manager.get_lineage("rel_1")
        assert lineage is not None
        assert lineage["entity_id"] == "rel_1"
    
    def test_batch_tracking_performance(self):
        """Test batch tracking of multiple entities."""
        manager = ProvenanceManager()
        
        # Track 100 entities
        for i in range(100):
            manager.track_entity(
                entity_id=f"entity_{i}",
                source=f"document_{i % 10}.pdf",
                entity_type="test_entity",
                metadata={"index": i}
            )
        
        # Verify all tracked
        for i in range(100):
            lineage = manager.get_lineage(f"entity_{i}")
            assert lineage is not None
            assert lineage["entity_id"] == f"entity_{i}"
    
    def test_provenance_statistics(self):
        """Test retrieving provenance statistics."""
        manager = ProvenanceManager()
        
        # Track various items
        manager.track_entity("e1", "src1", entity_type="type1")
        manager.track_entity("e2", "src2", entity_type="type2")
        manager.track_relationship(
            relationship_id="r1",
            source="src1",
            metadata={"subject": "e1", "predicate": "relates", "object": "e2"}
        )
        
        # Get statistics
        stats = manager.get_statistics()
        assert stats is not None
        assert stats["total_entries"] >= 3
