"""
Tests for enhanced TemporalVersionManager with persistent storage.

This module tests the comprehensive version management capabilities for knowledge
graphs, including persistent storage, detailed change tracking, and audit trails.
"""

import os
import tempfile
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from veritasreason.kg.temporal_query import TemporalVersionManager
from veritasreason.kg.temporal_model import TemporalBound
from veritasreason.change_management import ChangeLogEntry, InMemoryVersionStorage, SQLiteVersionStorage
from veritasreason.utils.exceptions import ValidationError, ProcessingError


class TestTemporalVersionManager:
    """Test cases for enhanced TemporalVersionManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_graph = {
            "entities": [
                {"id": "1", "name": "Entity1", "type": "Person"},
                {"id": "2", "name": "Entity2", "type": "Organization"}
            ],
            "relationships": [
                {"source": "1", "target": "2", "type": "works_for"}
            ]
        }
        
        self.modified_graph = {
            "entities": [
                {"id": "1", "name": "Entity1 Modified", "type": "Person"},
                {"id": "2", "name": "Entity2", "type": "Organization"},
                {"id": "3", "name": "Entity3", "type": "Product"}
            ],
            "relationships": [
                {"source": "1", "target": "2", "type": "works_for"},
                {"source": "2", "target": "3", "type": "produces"}
            ]
        }
    
    def test_in_memory_initialization(self):
        """Test initialization with in-memory storage."""
        manager = TemporalVersionManager()
        assert manager.storage is not None
        assert manager.version_strategy == "timestamp"
    
    def test_sqlite_initialization(self):
        """Test initialization with SQLite storage."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            manager = TemporalVersionManager(storage_path=db_path)
            assert manager.storage is not None
            assert os.path.exists(db_path)
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def test_create_snapshot_basic(self):
        """Test creating a basic snapshot."""
        manager = TemporalVersionManager()
        
        snapshot = manager.create_snapshot(
            graph=self.sample_graph,
            version_label="v1.0",
            author="alice@company.com",
            description="Initial version"
        )
        
        assert snapshot["label"] == "v1.0"
        assert snapshot["author"] == "alice@company.com"
        assert snapshot["description"] == "Initial version"
        assert "checksum" in snapshot
        assert len(snapshot["entities"]) == 2
        assert len(snapshot["relationships"]) == 1
    
    def test_create_snapshot_with_invalid_author(self):
        """Test that invalid author email raises ValidationError."""
        manager = TemporalVersionManager()
        
        with pytest.raises(ValidationError, match="Invalid email format"):
            manager.create_snapshot(
                graph=self.sample_graph,
                version_label="v1.0",
                author="invalid-email",
                description="Test version"
            )
    
    def test_create_snapshot_with_long_description(self):
        """Test that description over 500 chars raises ValidationError."""
        manager = TemporalVersionManager()
        long_description = "x" * 501
        
        with pytest.raises(ValidationError, match="Description too long"):
            manager.create_snapshot(
                graph=self.sample_graph,
                version_label="v1.0",
                author="alice@company.com",
                description=long_description
            )
    
    def test_list_versions_empty(self):
        """Test listing versions from empty storage."""
        manager = TemporalVersionManager()
        versions = manager.list_versions()
        assert versions == []
    
    def test_list_versions_with_data(self):
        """Test listing versions with data."""
        manager = TemporalVersionManager()
        
        # Create multiple snapshots
        manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        manager.create_snapshot(
            self.modified_graph, "v2.0", "bob@company.com", "Version 2"
        )
        
        versions = manager.list_versions()
        assert len(versions) == 2
        
        labels = [v["label"] for v in versions]
        assert "v1.0" in labels
        assert "v2.0" in labels
    
    def test_get_version_existing(self):
        """Test retrieving an existing version."""
        manager = TemporalVersionManager()
        
        # Create snapshot
        manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        
        # Retrieve it
        retrieved = manager.get_version("v1.0")
        assert retrieved is not None
        assert retrieved["label"] == "v1.0"
        assert retrieved["author"] == "alice@company.com"
    
    def test_get_version_nonexistent(self):
        """Test retrieving a nonexistent version."""
        manager = TemporalVersionManager()
        retrieved = manager.get_version("nonexistent")
        assert retrieved is None
    
    def test_verify_checksum_valid(self):
        """Test verifying a valid checksum."""
        manager = TemporalVersionManager()
        
        snapshot = manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        
        assert manager.verify_checksum(snapshot) is True
    
    def test_verify_checksum_invalid(self):
        """Test verifying an invalid checksum."""
        manager = TemporalVersionManager()
        
        snapshot = manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        
        # Corrupt the checksum
        snapshot["checksum"] = "invalid_checksum"
        assert manager.verify_checksum(snapshot) is False
    
    def test_compare_versions_with_labels(self):
        """Test comparing versions using labels."""
        manager = TemporalVersionManager()
        
        # Create two versions
        manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        manager.create_snapshot(
            self.modified_graph, "v2.0", "bob@company.com", "Version 2"
        )
        
        # Compare them
        diff = manager.compare_versions("v1.0", "v2.0")
        
        assert diff["version1"] == "v1.0"
        assert diff["version2"] == "v2.0"
        assert "summary" in diff
        assert "entities_added" in diff
        assert "entities_removed" in diff
        assert "entities_modified" in diff
        
        # Check summary counts
        summary = diff["summary"]
        assert summary["entities_added"] == 1  # Entity3 added
        assert summary["entities_removed"] == 0
        assert summary["entities_modified"] == 1  # Entity1 modified
        assert summary["relationships_added"] == 1  # New relationship added
    
    def test_compare_versions_with_dicts(self):
        """Test comparing versions using snapshot dictionaries."""
        manager = TemporalVersionManager()
        
        # Create snapshots but don't store them
        snapshot1 = {
            "label": "v1.0",
            "entities": self.sample_graph["entities"],
            "relationships": self.sample_graph["relationships"]
        }
        
        snapshot2 = {
            "label": "v2.0", 
            "entities": self.modified_graph["entities"],
            "relationships": self.modified_graph["relationships"]
        }
        
        # Compare directly
        diff = manager.compare_versions(snapshot1, snapshot2)
        
        assert diff["version1"] == "v1.0"
        assert diff["version2"] == "v2.0"
        assert len(diff["entities_added"]) == 1
        assert diff["entities_added"][0]["id"] == "3"
    
    def test_compare_versions_nonexistent_label(self):
        """Test comparing with nonexistent version label."""
        manager = TemporalVersionManager()
        
        manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        
        with pytest.raises(ValidationError, match="Version not found: nonexistent"):
            manager.compare_versions("v1.0", "nonexistent")

    def test_apply_revision_preserves_history_and_revises_valid_time(self):
        manager = TemporalVersionManager()
        snapshot = manager.create_snapshot(
            graph={
                "entities": [],
                "relationships": [
                    {
                        "id": "fact-1",
                        "source": "drug_a",
                        "target": "drug_b",
                        "type": "interacts_with",
                        "valid_from": "2021-01-01",
                        "valid_until": TemporalBound.OPEN,
                    }
                ],
            },
            version_label="v1.0",
            author="alice@company.com",
            description="Initial version",
        )

        revised = manager.apply_revision(
            snapshot,
            {
                "fact_ids": ["fact-1"],
                "new_valid_from": "2019-01-01",
                "new_valid_until": None,
                "revision_type": "retroactive",
                "author": "alice@company.com",
                "reason": "Backfilled evidence",
            },
        )

        query_engine = __import__("veritasreason.kg.temporal_query", fromlist=["TemporalGraphQuery"]).TemporalGraphQuery()
        result = query_engine.query_at_time(revised, "", "2020-06-01")

        assert len(result["relationships"]) == 1
        assert result["relationships"][0]["id"].startswith("fact-1__rev__")

        original = manager.get_version("v1.0")
        assert original is not None
        assert manager.get_version(revised["label"]) is not None
        assert len(manager.list_versions()) == 2
        assert manager.verify_checksum(revised) is True

    def test_apply_revision_recomputes_checksums_for_saved_snapshots(self):
        manager = TemporalVersionManager()
        snapshot = manager.create_snapshot(
            graph={
                "entities": [],
                "relationships": [
                    {
                        "id": "fact-1",
                        "source": "drug_a",
                        "target": "drug_b",
                        "type": "interacts_with",
                        "valid_from": "2021-01-01",
                        "valid_until": TemporalBound.OPEN,
                    }
                ],
            },
            version_label="v1.0",
            author="alice@company.com",
            description="Initial version",
        )

        revised = manager.apply_revision(
            snapshot,
            {
                "fact_ids": ["fact-1"],
                "new_valid_from": "2019-01-01",
                "new_valid_until": None,
                "revision_type": "retroactive",
                "author": "alice@company.com",
                "reason": "Backfilled evidence",
            },
        )

        assert manager.verify_checksum(revised) is True
        persisted_original = manager.get_version("v1.0")
        assert persisted_original is not None
        assert manager.verify_checksum(persisted_original) is True

    def test_generate_revision_suffix_is_collision_resistant(self):
        manager = TemporalVersionManager()
        revision_time = datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc)

        suffix_one = manager._generate_revision_suffix(revision_time)
        suffix_two = manager._generate_revision_suffix(revision_time)

        assert suffix_one != suffix_two

    def test_apply_revision_uses_collision_resistant_suffix_for_ids_and_labels(self):
        manager = TemporalVersionManager()
        snapshot = manager.create_snapshot(
            graph={
                "entities": [],
                "relationships": [
                    {
                        "id": "fact-1",
                        "source": "drug_a",
                        "target": "drug_b",
                        "type": "interacts_with",
                        "valid_from": "2021-01-01",
                        "valid_until": TemporalBound.OPEN,
                    }
                ],
            },
            version_label="v1.0",
            author="alice@company.com",
            description="Initial version",
        )

        with patch.object(manager, "_generate_revision_suffix", return_value="fixed_suffix"):
            revised = manager.apply_revision(
                snapshot,
                {
                    "fact_ids": ["fact-1"],
                    "new_valid_from": "2019-01-01",
                    "new_valid_until": None,
                    "revision_type": "retroactive",
                    "author": "alice@company.com",
                    "reason": "Backfilled evidence",
                },
            )

        assert revised["label"].endswith("__revision__fixed_suffix")
        replacement = next(
            rel for rel in revised["relationships"] if rel["id"].startswith("fact-1__rev__")
        )
        assert replacement["id"] == "fact-1__rev__fixed_suffix"
    
    def test_detailed_entity_diff(self):
        """Test detailed entity-level differences."""
        manager = TemporalVersionManager()
        
        # Create versions
        manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        manager.create_snapshot(
            self.modified_graph, "v2.0", "bob@company.com", "Version 2"
        )
        
        diff = manager.compare_versions("v1.0", "v2.0")
        
        # Check entities_added
        assert len(diff["entities_added"]) == 1
        assert diff["entities_added"][0]["id"] == "3"
        assert diff["entities_added"][0]["name"] == "Entity3"
        
        # Check entities_modified
        assert len(diff["entities_modified"]) == 1
        modified_entity = diff["entities_modified"][0]
        assert modified_entity["id"] == "1"
        assert "changes" in modified_entity
        assert "name" in modified_entity["changes"]
        assert modified_entity["changes"]["name"]["from"] == "Entity1"
        assert modified_entity["changes"]["name"]["to"] == "Entity1 Modified"
    
    def test_detailed_relationship_diff(self):
        """Test detailed relationship-level differences."""
        manager = TemporalVersionManager()
        
        manager.create_snapshot(
            self.sample_graph, "v1.0", "alice@company.com", "Version 1"
        )
        manager.create_snapshot(
            self.modified_graph, "v2.0", "bob@company.com", "Version 2"
        )
        
        diff = manager.compare_versions("v1.0", "v2.0")
        
        # Check relationships_added
        assert len(diff["relationships_added"]) == 1
        added_rel = diff["relationships_added"][0]
        assert added_rel["source"] == "2"
        assert added_rel["target"] == "3"
        assert added_rel["type"] == "produces"
    
    def test_backward_compatibility_create_version(self):
        """Test that old create_version method still works."""
        manager = TemporalVersionManager()
        
        # Use old method signature
        version = manager.create_version(
            graph=self.sample_graph,
            version_label="v1.0"
        )
        
        assert version["label"] == "v1.0"
        assert "entities" in version
        assert "relationships" in version
    
    def test_persistence_across_instances(self):
        """Test that data persists across manager instances."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Create snapshot with first instance
            manager1 = TemporalVersionManager(storage_path=db_path)
            manager1.create_snapshot(
                self.sample_graph, "v1.0", "alice@company.com", "Version 1"
            )
            
            # Retrieve with second instance
            manager2 = TemporalVersionManager(storage_path=db_path)
            retrieved = manager2.get_version("v1.0")
            
            assert retrieved is not None
            assert retrieved["label"] == "v1.0"
            assert retrieved["author"] == "alice@company.com"
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def test_relationship_key_generation(self):
        """Test the relationship key generation method."""
        manager = TemporalVersionManager()
        
        relationship = {
            "source": "entity1",
            "target": "entity2", 
            "type": "relates_to"
        }
        
        key = manager._relationship_key(relationship)
        assert key == "entity1|relates_to|entity2"
    
    def test_relationship_key_with_missing_fields(self):
        """Test relationship key generation with missing fields."""
        manager = TemporalVersionManager()
        
        relationship = {"source": "entity1"}  # Missing target and type
        key = manager._relationship_key(relationship)
        assert key == "entity1||"
    
    def test_entity_changes_computation(self):
        """Test entity changes computation."""
        manager = TemporalVersionManager()
        
        entity1 = {"id": "1", "name": "Original", "type": "Person"}
        entity2 = {"id": "1", "name": "Modified", "type": "Person", "age": 30}
        
        changes = manager._compute_entity_changes(entity1, entity2)
        
        assert "name" in changes
        assert changes["name"]["from"] == "Original"
        assert changes["name"]["to"] == "Modified"
        assert "age" in changes
        assert changes["age"]["from"] is None
        assert changes["age"]["to"] == 30
    
    def test_snapshot_with_metadata(self):
        """Test creating snapshot with additional metadata."""
        manager = TemporalVersionManager()
        
        snapshot = manager.create_snapshot(
            graph=self.sample_graph,
            version_label="v1.0",
            author="alice@company.com",
            description="Version with metadata",
            metadata={"environment": "production", "build": "123"}
        )
        
        assert snapshot["metadata"]["environment"] == "production"
        assert snapshot["metadata"]["build"] == "123"
