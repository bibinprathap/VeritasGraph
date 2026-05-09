"""
W3C PROV-O Compliant Provenance Schemas

This module provides dataclasses for provenance tracking that comply with
W3C PROV-O (Provenance Ontology) standards while consolidating functionality
from existing VeritasReason provenance trackers.

Consolidates:
    - kg.ProvenanceTracker: Entity/relationship tracking with temporal info
    - split.ProvenanceInfo: Chunk tracking with parent-child relationships
    - conflicts.SourceReference: Source tracking with credibility scores

W3C PROV-O Mapping:
    - ProvenanceEntry.entity_id → prov:Entity
    - ProvenanceEntry.activity_id → prov:Activity
    - ProvenanceEntry.agent_id → prov:Agent
    - ProvenanceEntry.parent_entity_id → prov:wasDerivedFrom
    - ProvenanceEntry.used_entities → prov:used
    - ProvenanceEntry.timestamp → prov:generatedAtTime

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ProvenanceEntry:
    """
    W3C PROV-O compliant provenance entry.
    
    This unified schema consolidates provenance tracking from:
    - kg.ProvenanceTracker (entity/relationship tracking)
    - split.ProvenanceInfo (chunk tracking)
    - conflicts.SourceReference (source tracking)
    
    Attributes:
        entity_id: Unique identifier for the entity (prov:Entity)
        entity_type: Type of entity (entity, chunk, relationship, property, etc.)
        activity_id: Activity that generated this entity (prov:Activity)
        agent_id: Agent responsible for the activity (prov:Agent)
        source_document: Source document identifier (DOI, file path, URL)
        source_location: Location within source (page, figure, char range)
        source_quote: Direct quote from source (for audit trail)
        timestamp: When this provenance entry was created (prov:generatedAtTime)
        first_seen: When entity was first tracked (from kg.ProvenanceTracker)
        last_updated: When entity was last updated (from kg.ProvenanceTracker)
        confidence: Confidence score for this provenance entry (0.0-1.0)
        checksum: SHA-256 checksum for integrity verification
        parent_entity_id: Parent entity ID (prov:wasDerivedFrom)
        used_entities: List of entities used to create this entity (prov:used)
        start_index: Start character index (from split.ProvenanceInfo)
        end_index: End character index (from split.ProvenanceInfo)
        credibility: Source credibility score (from conflicts.SourceTracker)
        metadata: Additional metadata dictionary
        version: Provenance schema version
    
    Example:
        >>> entry = ProvenanceEntry(
        ...     entity_id="entity_123",
        ...     entity_type="named_entity",
        ...     activity_id="ner_extraction",
        ...     source_document="DOI:10.1371/journal.pone.0023601",
        ...     source_location="Figure 2",
        ...     source_quote="Total fish biomass increased by 463%",
        ...     confidence=0.92
        ... )
    """
    
    # W3C PROV-O core entities
    entity_id: str
    entity_type: str
    activity_id: str
    agent_id: str = "veritasreason"
    
    # Audit-grade source tracking
    source_document: str = ""
    source_location: Optional[str] = None
    source_quote: Optional[str] = None
    
    # Temporal tracking (from kg.ProvenanceTracker)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    first_seen: Optional[str] = None
    last_updated: Optional[str] = None
    
    # Quality metrics
    confidence: float = 1.0
    checksum: Optional[str] = None
    
    # Chain of custody (W3C PROV-O)
    parent_entity_id: Optional[str] = None
    used_entities: List[str] = field(default_factory=list)
    
    # Chunk-specific fields (from split.ProvenanceInfo)
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    
    # Source credibility (from conflicts.SourceTracker)
    credibility: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert provenance entry to dictionary.
        
        Returns:
            Dictionary representation of provenance entry
        """
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "activity_id": self.activity_id,
            "agent_id": self.agent_id,
            "source_document": self.source_document,
            "source_location": self.source_location,
            "source_quote": self.source_quote,
            "timestamp": self.timestamp,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "confidence": self.confidence,
            "checksum": self.checksum,
            "parent_entity_id": self.parent_entity_id,
            "used_entities": self.used_entities,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "credibility": self.credibility,
            "metadata": self.metadata,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceEntry":
        """
        Create provenance entry from dictionary.
        
        Args:
            data: Dictionary containing provenance data
            
        Returns:
            ProvenanceEntry instance
        """
        return cls(**data)


@dataclass
class SourceReference:
    """
    Source reference for provenance tracking.
    
    Compatible with conflicts.SourceReference for backward compatibility.
    
    Attributes:
        document: Document identifier (DOI, file path, URL)
        page: Page number within document
        section: Section identifier within document
        line: Line number within document
        timestamp: When this source was accessed/created
        confidence: Confidence score for this source (0.0-1.0)
        metadata: Additional metadata dictionary
    
    Example:
        >>> source = SourceReference(
        ...     document="DOI:10.1038/s41586-021-03371-z",
        ...     page=4,
        ...     section="Table S4",
        ...     confidence=0.92
        ... )
    """
    
    document: str
    page: Optional[int] = None
    section: Optional[str] = None
    line: Optional[int] = None
    timestamp: Optional[datetime] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert source reference to dictionary.
        
        Returns:
            Dictionary representation of source reference
        """
        return {
            "document": self.document,
            "page": self.page,
            "section": self.section,
            "line": self.line,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceReference":
        """
        Create source reference from dictionary.
        
        Args:
            data: Dictionary containing source reference data
            
        Returns:
            SourceReference instance
        """
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class PropertySource:
    """
    Property source information for conflict tracking.
    
    Compatible with conflicts.PropertySource for backward compatibility.
    
    Attributes:
        property_name: Name of the property
        value: Value of the property
        sources: List of source references
        entity_id: Entity this property belongs to
        metadata: Additional metadata dictionary
    
    Example:
        >>> prop_source = PropertySource(
        ...     property_name="biomass_increase",
        ...     value="463%",
        ...     sources=[source_ref],
        ...     entity_id="cabo_pulmo_mpa"
        ... )
    """
    
    property_name: str
    value: Any
    sources: List[SourceReference] = field(default_factory=list)
    entity_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert property source to dictionary.
        
        Returns:
            Dictionary representation of property source
        """
        return {
            "property_name": self.property_name,
            "value": self.value,
            "sources": [s.to_dict() for s in self.sources],
            "entity_id": self.entity_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PropertySource":
        """
        Create property source from dictionary.
        
        Args:
            data: Dictionary containing property source data
            
        Returns:
            PropertySource instance
        """
        if "sources" in data:
            data["sources"] = [
                SourceReference.from_dict(s) if isinstance(s, dict) else s
                for s in data["sources"]
            ]
        return cls(**data)
