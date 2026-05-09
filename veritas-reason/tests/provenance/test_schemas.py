"""
Test W3C PROV-O Compliant Schemas

Tests for provenance schemas including ProvenanceEntry, SourceReference,
and PropertySource dataclasses.
"""

import pytest
from datetime import datetime
from veritasreason.provenance.schemas import ProvenanceEntry, SourceReference, PropertySource


class TestProvenanceEntry:
    """Test ProvenanceEntry dataclass."""
    
    def test_create_basic_entry(self):
        """Test creating a basic provenance entry."""
        entry = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        
        assert entry.entity_id == "entity_1"
        assert entry.entity_type == "entity"
        assert entry.activity_id == "extraction"
        assert entry.agent_id == "veritasreason"
        assert entry.confidence == 1.0
    
    def test_entry_with_source_tracking(self):
        """Test entry with audit-grade source tracking."""
        entry = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction",
            source_document="DOI:10.1371/journal.pone.0023601",
            source_location="Figure 2",
            source_quote="Total fish biomass increased by 463%",
            confidence=0.92
        )
        
        assert entry.source_document == "DOI:10.1371/journal.pone.0023601"
        assert entry.source_location == "Figure 2"
        assert entry.source_quote == "Total fish biomass increased by 463%"
        assert entry.confidence == 0.92
    
    def test_entry_with_lineage(self):
        """Test entry with parent-child relationships."""
        entry = ProvenanceEntry(
            entity_id="entity_2",
            entity_type="entity",
            activity_id="transformation",
            parent_entity_id="entity_1",
            used_entities=["entity_1", "axiom_1"]
        )
        
        assert entry.parent_entity_id == "entity_1"
        assert len(entry.used_entities) == 2
        assert "entity_1" in entry.used_entities
    
    def test_entry_to_dict(self):
        """Test converting entry to dictionary."""
        entry = ProvenanceEntry(
            entity_id="entity_1",
            entity_type="entity",
            activity_id="extraction"
        )
        
        data = entry.to_dict()
        
        assert isinstance(data, dict)
        assert data["entity_id"] == "entity_1"
        assert data["entity_type"] == "entity"
        assert "timestamp" in data
    
    def test_entry_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "entity_id": "entity_1",
            "entity_type": "entity",
            "activity_id": "extraction",
            "agent_id": "veritasreason",
            "source_document": "doc_1",
            "confidence": 0.9
        }
        
        entry = ProvenanceEntry.from_dict(data)
        
        assert entry.entity_id == "entity_1"
        assert entry.confidence == 0.9


class TestSourceReference:
    """Test SourceReference dataclass."""
    
    def test_create_basic_source(self):
        """Test creating a basic source reference."""
        source = SourceReference(
            document="DOI:10.1038/s41586-021-03371-z"
        )
        
        assert source.document == "DOI:10.1038/s41586-021-03371-z"
        assert source.confidence == 1.0
    
    def test_source_with_location(self):
        """Test source with page and section."""
        source = SourceReference(
            document="DOI:10.1038/s41586-021-03371-z",
            page=4,
            section="Table S4",
            confidence=0.92
        )
        
        assert source.page == 4
        assert source.section == "Table S4"
        assert source.confidence == 0.92
    
    def test_source_to_dict(self):
        """Test converting source to dictionary."""
        source = SourceReference(
            document="doc_1",
            page=1
        )
        
        data = source.to_dict()
        
        assert isinstance(data, dict)
        assert data["document"] == "doc_1"
        assert data["page"] == 1


class TestPropertySource:
    """Test PropertySource dataclass."""
    
    def test_create_property_source(self):
        """Test creating a property source."""
        source_ref = SourceReference(document="doc_1")
        
        prop_source = PropertySource(
            property_name="biomass_increase",
            value="463%",
            sources=[source_ref],
            entity_id="cabo_pulmo_mpa"
        )
        
        assert prop_source.property_name == "biomass_increase"
        assert prop_source.value == "463%"
        assert len(prop_source.sources) == 1
        assert prop_source.entity_id == "cabo_pulmo_mpa"
    
    def test_property_source_to_dict(self):
        """Test converting property source to dictionary."""
        source_ref = SourceReference(document="doc_1")
        prop_source = PropertySource(
            property_name="name",
            value="test",
            sources=[source_ref]
        )
        
        data = prop_source.to_dict()
        
        assert isinstance(data, dict)
        assert data["property_name"] == "name"
        assert len(data["sources"]) == 1
