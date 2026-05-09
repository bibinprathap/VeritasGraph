"""
Integration Tests for Provenance Module

Tests end-to-end integration of provenance tracking across all modules.
"""

import pytest
from veritasreason.provenance import ProvenanceManager
from veritasreason.kg import ProvenanceTracker as KGTracker
from veritasreason.split import ProvenanceTracker as SplitTracker
from veritasreason.split.semantic_chunker import Chunk


class TestEndToEndProvenance:
    """Test end-to-end provenance tracking."""
    
    def test_unified_manager_basic_flow(self):
        """Test basic flow with unified manager."""
        prov_mgr = ProvenanceManager()
        
        # Track entity
        prov_mgr.track_entity("entity_1", source="doc_1")
        
        # Track chunk
        prov_mgr.track_chunk("chunk_1", source_document="doc_1")
        
        # Verify both tracked
        entity_prov = prov_mgr.get_provenance("entity_1")
        chunk_prov = prov_mgr.get_provenance("chunk_1")
        
        assert entity_prov is not None
        assert chunk_prov is not None
    
    def test_kg_to_unified_integration(self):
        """Test kg.ProvenanceTracker uses unified backend."""
        kg_tracker = KGTracker()
        
        # Track with kg tracker
        kg_tracker.track_entity("kg_entity_1", source="kg_doc_1")
        
        # Verify it was tracked
        lineage = kg_tracker.get_lineage("kg_entity_1")
        
        assert lineage is not None
        assert "sources" in lineage
    
    def test_split_to_unified_integration(self):
        """Test split.ProvenanceTracker uses unified backend."""
        split_tracker = SplitTracker()
        
        chunk = Chunk(
            text="Test chunk",
            start_index=0,
            end_index=10,
            metadata={}
        )
        chunk.id = "split_chunk_1"
        
        # Track with split tracker
        split_tracker.track_chunk(chunk, source_document="split_doc_1")
        
        # Verify it was tracked
        prov = split_tracker.get_provenance("split_chunk_1")
        
        assert prov is not None
        assert prov.chunk_id == "split_chunk_1"
    
    def test_cross_module_lineage(self):
        """Test lineage tracing across modules."""
        prov_mgr = ProvenanceManager()
        
        # Track document
        prov_mgr.track_entity(
            entity_id="doc_1",
            source="original_source.pdf",
            entity_type="document"
        )
        
        # Track chunk from document
        prov_mgr.track_chunk(
            chunk_id="chunk_1",
            source_document="doc_1",
            parent_chunk_id="doc_1"
        )
        
        # Track entity from chunk
        prov_mgr.track_entity(
            entity_id="entity_1",
            source="chunk_1",
            entity_type="entity"
        )
        
        # Trace lineage
        lineage = prov_mgr.get_lineage("entity_1")
        
        assert lineage is not None
        assert len(lineage.get("source_documents", [])) > 0


class TestPerformance:
    """Test performance of provenance tracking."""
    
    def test_bulk_entity_tracking(self):
        """Test tracking many entities."""
        prov_mgr = ProvenanceManager()
        
        # Track 1000 entities
        entities = [{"id": f"entity_{i}"} for i in range(1000)]
        count = prov_mgr.track_entities_batch(entities, source="bulk_doc")
        
        assert count == 1000
    
    def test_bulk_chunk_tracking(self):
        """Test tracking many chunks."""
        prov_mgr = ProvenanceManager()
        
        # Track 1000 chunks
        chunks = [
            {"id": f"chunk_{i}", "start_index": i*100, "end_index": (i+1)*100}
            for i in range(1000)
        ]
        count = prov_mgr.track_chunks_batch(chunks, source_document="bulk_doc")
        
        assert count == 1000
    
    def test_lineage_tracing_performance(self):
        """Test lineage tracing with deep chains."""
        prov_mgr = ProvenanceManager()
        
        # Create chain of 100 entities
        for i in range(100):
            parent_id = f"entity_{i-1}" if i > 0 else None
            prov_mgr.track_entity(
                entity_id=f"entity_{i}",
                source=f"doc_{i}",
                metadata={"parent": parent_id}
            )
        
        # Trace lineage (should be fast)
        lineage = prov_mgr.get_lineage("entity_99")
        
        assert lineage is not None


class TestDataIntegrity:
    """Test data integrity and checksums."""
    
    def test_checksum_generation(self):
        """Test that checksums are generated."""
        prov_mgr = ProvenanceManager()
        
        entry = prov_mgr.track_entity(
            entity_id="integrity_test",
            source="test_doc"
        )
        
        assert entry.checksum is not None
        assert len(entry.checksum) == 64  # SHA-256 hex length
    
    def test_checksum_verification(self):
        """Test checksum verification."""
        from veritasreason.provenance import compute_checksum, verify_checksum
        
        prov_mgr = ProvenanceManager()
        
        entry = prov_mgr.track_entity(
            entity_id="verify_test",
            source="test_doc"
        )
        
        # Verify checksum
        is_valid = verify_checksum(entry)
        assert is_valid is True


class TestStorageBackends:
    """Test different storage backends."""
    
    def test_in_memory_storage(self):
        """Test in-memory storage backend."""
        from veritasreason.provenance import InMemoryStorage
        
        storage = InMemoryStorage()
        prov_mgr = ProvenanceManager(storage=storage)
        
        prov_mgr.track_entity("mem_entity_1", source="mem_doc_1")
        
        prov = prov_mgr.get_provenance("mem_entity_1")
        assert prov is not None
    
    def test_sqlite_storage(self):
        """Test SQLite storage backend."""
        import tempfile
        import os
        from veritasreason.provenance import SQLiteStorage
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            storage = SQLiteStorage(db_path)
            prov_mgr = ProvenanceManager(storage=storage)
            
            prov_mgr.track_entity("sql_entity_1", source="sql_doc_1")
            
            # Verify persistence
            prov_mgr2 = ProvenanceManager(storage_path=db_path)
            prov = prov_mgr2.get_provenance("sql_entity_1")
            
            assert prov is not None
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestErrorHandling:
    """Test error handling and graceful degradation."""
    
    def test_missing_entity_returns_none(self):
        """Test that missing entity returns None."""
        prov_mgr = ProvenanceManager()
        
        prov = prov_mgr.get_provenance("nonexistent")
        
        assert prov is None
    
    def test_empty_lineage_returns_empty_dict(self):
        """Test that empty lineage returns empty dict."""
        prov_mgr = ProvenanceManager()
        
        lineage = prov_mgr.get_lineage("nonexistent")
        
        assert lineage == {}
    
    def test_graceful_failure_on_invalid_data(self):
        """Test graceful handling of invalid data."""
        prov_mgr = ProvenanceManager()
        
        # Should not raise exception
        try:
            prov_mgr.track_entity("", source="")
            success = True
        except Exception:
            success = False
        
        assert success is True


class TestStatistics:
    """Test provenance statistics."""
    
    def test_get_statistics(self):
        """Test getting provenance statistics."""
        prov_mgr = ProvenanceManager()
        
        # Track various entities
        prov_mgr.track_entity("entity_1", source="doc_1")
        prov_mgr.track_entity("entity_2", source="doc_1")
        prov_mgr.track_chunk("chunk_1", source_document="doc_1")
        
        stats = prov_mgr.get_statistics()
        
        assert "total_entries" in stats
        assert "entity_types" in stats
        assert stats["total_entries"] >= 3
    
    def test_clear_provenance(self):
        """Test clearing provenance data."""
        prov_mgr = ProvenanceManager()
        
        prov_mgr.track_entity("entity_1", source="doc_1")
        prov_mgr.track_entity("entity_2", source="doc_1")
        
        count = prov_mgr.clear()
        
        assert count >= 2
        
        # Verify cleared
        prov = prov_mgr.get_provenance("entity_1")
        assert prov is None
