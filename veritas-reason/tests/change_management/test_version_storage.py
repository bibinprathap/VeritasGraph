"""
Tests for the Version Storage module.

This module tests the storage abstraction layer and concrete implementations
for persistent version management.
"""

import os
import tempfile
import pytest
from pathlib import Path

from veritasreason.change_management import (
    VersionStorage, InMemoryVersionStorage, SQLiteVersionStorage,
    compute_checksum, verify_checksum
)
from veritasreason.utils.exceptions import ValidationError, ProcessingError


class TestInMemoryVersionStorage:
    """Test cases for InMemoryVersionStorage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryVersionStorage()
        self.sample_snapshot = {
            "label": "v1.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "author": "alice@company.com",
            "description": "Initial version",
            "checksum": "abc123",
            "entities": [{"id": "1", "name": "Entity1"}],
            "relationships": [{"source": "1", "target": "2", "type": "relates"}],
            "metadata": {"version": "1.0"}
        }
    
    def test_save_and_get_snapshot(self):
        """Test saving and retrieving a snapshot."""
        self.storage.save(self.sample_snapshot)
        retrieved = self.storage.get("v1.0")
        
        assert retrieved is not None
        assert retrieved["label"] == "v1.0"
        assert retrieved["author"] == "alice@company.com"
        assert len(retrieved["entities"]) == 1
    
    def test_save_snapshot_without_label_raises_error(self):
        """Test that saving snapshot without label raises ValidationError."""
        invalid_snapshot = self.sample_snapshot.copy()
        del invalid_snapshot["label"]
        
        with pytest.raises(ValidationError, match="Snapshot must have a 'label' field"):
            self.storage.save(invalid_snapshot)
    
    def test_save_duplicate_label_raises_error(self):
        """Test that saving duplicate label raises ValidationError."""
        self.storage.save(self.sample_snapshot)
        
        with pytest.raises(ValidationError, match="Version 'v1.0' already exists"):
            self.storage.save(self.sample_snapshot)
    
    def test_get_nonexistent_snapshot_returns_none(self):
        """Test that getting nonexistent snapshot returns None."""
        result = self.storage.get("nonexistent")
        assert result is None
    
    def test_list_all_empty_storage(self):
        """Test listing all snapshots from empty storage."""
        result = self.storage.list_all()
        assert result == []
    
    def test_list_all_with_snapshots(self):
        """Test listing all snapshots with data."""
        self.storage.save(self.sample_snapshot)
        
        snapshot2 = self.sample_snapshot.copy()
        snapshot2["label"] = "v2.0"
        self.storage.save(snapshot2)
        
        result = self.storage.list_all()
        assert len(result) == 2
        
        labels = [item["label"] for item in result]
        assert "v1.0" in labels
        assert "v2.0" in labels
        
        # Check metadata structure
        for item in result:
            assert "entity_count" in item
            assert "relationship_count" in item
            assert item["entity_count"] == 1
            assert item["relationship_count"] == 1
    
    def test_exists_method(self):
        """Test the exists method."""
        assert not self.storage.exists("v1.0")
        
        self.storage.save(self.sample_snapshot)
        assert self.storage.exists("v1.0")
        assert not self.storage.exists("v2.0")
    
    def test_delete_method(self):
        """Test the delete method."""
        # Delete non-existent returns False
        assert not self.storage.delete("nonexistent")
        
        # Save and delete existing returns True
        self.storage.save(self.sample_snapshot)
        assert self.storage.delete("v1.0")
        assert not self.storage.exists("v1.0")
    
    def test_data_isolation(self):
        """Test that returned data is isolated from internal storage."""
        self.storage.save(self.sample_snapshot)
        retrieved = self.storage.get("v1.0")
        
        # Modify retrieved data
        retrieved["entities"].append({"id": "2", "name": "Entity2"})
        
        # Original should be unchanged
        retrieved_again = self.storage.get("v1.0")
        assert len(retrieved_again["entities"]) == 1


class TestSQLiteVersionStorage:
    """Test cases for SQLiteVersionStorage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_versions.db")
        self.storage = SQLiteVersionStorage(self.db_path)
        
        self.sample_snapshot = {
            "label": "v1.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "author": "alice@company.com",
            "description": "Initial version",
            "checksum": "abc123",
            "entities": [{"id": "1", "name": "Entity1"}],
            "relationships": [{"source": "1", "target": "2", "type": "relates"}],
            "metadata": {"version": "1.0"}
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_database_initialization(self):
        """Test that database is properly initialized."""
        assert os.path.exists(self.db_path)
        
        # Verify table exists
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='versions'")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
    
    def test_save_and_get_snapshot(self):
        """Test saving and retrieving a snapshot from SQLite."""
        self.storage.save(self.sample_snapshot)
        retrieved = self.storage.get("v1.0")
        
        assert retrieved is not None
        assert retrieved["label"] == "v1.0"
        assert retrieved["author"] == "alice@company.com"
        assert len(retrieved["entities"]) == 1
        assert retrieved["entities"][0]["name"] == "Entity1"
    
    def test_save_duplicate_label_raises_error(self):
        """Test that saving duplicate label raises ValidationError."""
        self.storage.save(self.sample_snapshot)
        
        with pytest.raises(ValidationError, match="Version 'v1.0' already exists"):
            self.storage.save(self.sample_snapshot)
    
    def test_persistence_across_instances(self):
        """Test that data persists across storage instances."""
        # Save with first instance
        self.storage.save(self.sample_snapshot)
        
        # Create new instance and retrieve
        new_storage = SQLiteVersionStorage(self.db_path)
        retrieved = new_storage.get("v1.0")
        
        assert retrieved is not None
        assert retrieved["label"] == "v1.0"
    
    def test_list_all_with_ordering(self):
        """Test that list_all returns items ordered by timestamp."""
        # Save multiple snapshots
        snapshot1 = self.sample_snapshot.copy()
        snapshot1["timestamp"] = "2024-01-15T10:30:00Z"
        
        snapshot2 = self.sample_snapshot.copy()
        snapshot2["label"] = "v2.0"
        snapshot2["timestamp"] = "2024-01-15T11:30:00Z"
        
        self.storage.save(snapshot1)
        self.storage.save(snapshot2)
        
        result = self.storage.list_all()
        assert len(result) == 2
        
        # Should be ordered by timestamp DESC (newest first)
        assert result[0]["label"] == "v2.0"
        assert result[1]["label"] == "v1.0"
    
    def test_exists_method(self):
        """Test the exists method with SQLite."""
        assert not self.storage.exists("v1.0")
        
        self.storage.save(self.sample_snapshot)
        assert self.storage.exists("v1.0")
    
    def test_delete_method(self):
        """Test the delete method with SQLite."""
        # Delete non-existent returns False
        assert not self.storage.delete("nonexistent")
        
        # Save and delete existing returns True
        self.storage.save(self.sample_snapshot)
        assert self.storage.delete("v1.0")
        assert not self.storage.exists("v1.0")
    
    def test_directory_creation(self):
        """Test that storage creates directories if they don't exist."""
        nested_path = os.path.join(self.temp_dir, "nested", "path", "versions.db")
        storage = SQLiteVersionStorage(nested_path)
        
        assert os.path.exists(nested_path)
        
        # Clean up
        os.remove(nested_path)
        os.rmdir(os.path.dirname(nested_path))
        os.rmdir(os.path.dirname(os.path.dirname(nested_path)))


class TestChecksumUtilities:
    """Test cases for checksum computation and verification."""
    
    def test_compute_checksum_deterministic(self):
        """Test that checksum computation is deterministic."""
        data = {
            "entities": [{"id": "1", "name": "Entity1"}],
            "relationships": [{"source": "1", "target": "2"}],
            "metadata": {"version": "1.0"}
        }
        
        checksum1 = compute_checksum(data)
        checksum2 = compute_checksum(data)
        
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 hex length
    
    def test_compute_checksum_different_data(self):
        """Test that different data produces different checksums."""
        data1 = {"entities": [{"id": "1", "name": "Entity1"}]}
        data2 = {"entities": [{"id": "1", "name": "Entity2"}]}
        
        checksum1 = compute_checksum(data1)
        checksum2 = compute_checksum(data2)
        
        assert checksum1 != checksum2
    
    def test_compute_checksum_order_independence(self):
        """Test that key order doesn't affect checksum."""
        data1 = {"b": 2, "a": 1}
        data2 = {"a": 1, "b": 2}
        
        checksum1 = compute_checksum(data1)
        checksum2 = compute_checksum(data2)
        
        assert checksum1 == checksum2
    
    def test_verify_checksum_valid(self):
        """Test verifying a valid checksum."""
        data = {"entities": [{"id": "1"}], "metadata": {}}
        checksum = compute_checksum(data)
        
        snapshot = data.copy()
        snapshot["checksum"] = checksum
        
        assert verify_checksum(snapshot) is True
    
    def test_verify_checksum_invalid(self):
        """Test verifying an invalid checksum."""
        snapshot = {
            "entities": [{"id": "1"}],
            "metadata": {},
            "checksum": "invalid_checksum"
        }
        
        assert verify_checksum(snapshot) is False
    
    def test_verify_checksum_missing(self):
        """Test verifying snapshot without checksum."""
        snapshot = {
            "entities": [{"id": "1"}],
            "metadata": {}
        }
        
        assert verify_checksum(snapshot) is False
    
    def test_verify_checksum_with_modified_data(self):
        """Test that verification fails when data is modified."""
        data = {"entities": [{"id": "1"}], "metadata": {}}
        checksum = compute_checksum(data)
        
        # Modify data after computing checksum
        snapshot = data.copy()
        snapshot["entities"].append({"id": "2"})
        snapshot["checksum"] = checksum
        
        assert verify_checksum(snapshot) is False
