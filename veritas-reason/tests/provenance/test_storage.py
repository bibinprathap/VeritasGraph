"""
Test Provenance Storage Backends

Tests for InMemoryStorage and SQLiteStorage backends.
"""

import pytest
import tempfile
import os
from veritasreason.provenance.schemas import ProvenanceEntry
from veritasreason.provenance.storage import InMemoryStorage, SQLiteStorage


class TestInMemoryStorage:
    """Test InMemoryStorage backend."""
    
    def test_store_and_retrieve(self):
        """Test storing and retrieving entries."""
        storage = InMemoryStorage()
        
        entry = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        
        storage.store(entry)
        retrieved = storage.retrieve("entity_1")
        
        assert retrieved is not None
        assert retrieved.entity_id == "entity_1"
    
    def test_retrieve_nonexistent(self):
        """Test retrieving non-existent entry."""
        storage = InMemoryStorage()
        
        retrieved = storage.retrieve("nonexistent")
        
        assert retrieved is None
    
    def test_retrieve_all(self):
        """Test retrieving all entries."""
        storage = InMemoryStorage()
        
        entry1 = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        entry2 = ProvenanceEntry(
            entity_id="entity_2",
            entity_type="chunk",
            activity_id="chunking"
        )
        
        storage.store(entry1)
        storage.store(entry2)
        
        all_entries = storage.retrieve_all()
        
        assert len(all_entries) == 2
    
    def test_retrieve_by_type(self):
        """Test retrieving entries by type."""
        storage = InMemoryStorage()
        
        entry1 = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        entry2 = ProvenanceEntry(
            entity_id="chunk_1",
            entity_type="chunk",
            activity_id="chunking"
        )
        
        storage.store(entry1)
        storage.store(entry2)
        
        entities = storage.retrieve_all(entity_type="entity")
        
        assert len(entities) == 1
        assert entities[0].entity_type == "entity"
    
    def test_trace_lineage(self):
        """Test tracing lineage."""
        storage = InMemoryStorage()
        
        # Create parent-child chain
        entry1 = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        entry2 = ProvenanceEntry(
            entity_id="entity_2",
            entity_type="entity",
            activity_id="transformation",
            parent_entity_id="entity_1"
        )
        entry3 = ProvenanceEntry(
            entity_id="entity_3",
            entity_type="entity",
            activity_id="transformation",
            parent_entity_id="entity_2"
        )
        
        storage.store(entry1)
        storage.store(entry2)
        storage.store(entry3)
        
        lineage = storage.trace_lineage("entity_3")
        
        assert len(lineage) == 3
        entity_ids = [e.entity_id for e in lineage]
        assert "entity_1" in entity_ids
        assert "entity_2" in entity_ids
        assert "entity_3" in entity_ids
    
    def test_clear(self):
        """Test clearing storage."""
        storage = InMemoryStorage()
        
        entry = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        
        storage.store(entry)
        count = storage.clear()
        
        assert count == 1
        assert len(storage.retrieve_all()) == 0


class TestSQLiteStorage:
    """Test SQLiteStorage backend."""
    
    def test_store_and_retrieve(self):
        """Test storing and retrieving entries."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            storage = SQLiteStorage(db_path)
            
            entry = ProvenanceEntry(
                entity_id="entity_1",
                entity_type="entity",
                activity_id="extraction"
            )
            
            storage.store(entry)
            retrieved = storage.retrieve("entity_1")
            
            assert retrieved is not None
            assert retrieved.entity_id == "entity_1"
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_persistence(self):
        """Test data persistence across connections."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            # Store entry
            storage1 = SQLiteStorage(db_path)
            entry = ProvenanceEntry(
                entity_id="entity_1",
                entity_type="entity",
                activity_id="extraction"
            )
            storage1.store(entry)
            
            # Retrieve with new connection
            storage2 = SQLiteStorage(db_path)
            retrieved = storage2.retrieve("entity_1")
            
            assert retrieved is not None
            assert retrieved.entity_id == "entity_1"
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_trace_lineage(self):
        """Test tracing lineage in SQLite."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name
        
        try:
            storage = SQLiteStorage(db_path)
            
            # Create parent-child chain
            entry1 = ProvenanceEntry(
                entity_id="entity_1",
                entity_type="entity",
                activity_id="extraction"
            )
            entry2 = ProvenanceEntry(
                entity_id="entity_2",
                entity_type="entity",
                activity_id="transformation",
                parent_entity_id="entity_1"
            )
            
            storage.store(entry1)
            storage.store(entry2)
            
            lineage = storage.trace_lineage("entity_2")
            
            assert len(lineage) == 2
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
