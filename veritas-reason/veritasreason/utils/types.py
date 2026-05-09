"""
Type Definitions and Protocols Module

This module contains type hints, protocols, and data structures used throughout
the VeritasReason framework, providing type safety, interface definitions, and
structured data representations for entities, relationships, and processing results.

Key Features:
    - Type aliases for common data types (JSONType, EntityDict, RelationshipDict)
    - Enumeration types (EntityType, DataType, ProcessingStatus, QualityLevel, RelationshipType)
    - Data classes for structured data (Entity, Relationship, ProcessingResult, QualityMetrics)
    - Protocol definitions for interfaces (Processor, Validator, Exporter, Importer)
    - Generic types for reusable components (Result, BatchResult)
    - Type guards for runtime type checking
    - Conversion functions between dataclasses and dictionaries

Main Classes:
    - EntityType: Entity type enumeration (PERSON, ORGANIZATION, LOCATION, etc.)
    - DataType: Data type enumeration (TEXT, IMAGE, AUDIO, VIDEO, etc.)
    - ProcessingStatus: Processing status enumeration (PENDING, PROCESSING, COMPLETED, etc.)
    - QualityLevel: Quality level enumeration (HIGH, MEDIUM, LOW, POOR)
    - RelationshipType: Relationship type enumeration (WORKS_FOR, LOCATED_IN, etc.)
    - Entity: Structured entity data class
    - Relationship: Structured relationship data class
    - ProcessingResult: Result of a processing operation
    - QualityMetrics: Data quality metrics data class
    - Result: Generic result container with success/error handling
    - BatchResult: Generic batch result container with success rate tracking

Example Usage:
    >>> from veritasreason.utils import Entity, EntityType, Relationship, RelationshipType
    >>> entity = Entity(
    ...     id="e1",
    ...     text="John Doe",
    ...     type=EntityType.PERSON,
    ...     confidence=0.95
    ... )
    >>> relationship = Relationship(
    ...     id="r1",
    ...     source_id="e1",
    ...     target_id="e2",
    ...     type=RelationshipType.WORKS_FOR
    ... )
    >>> 
    >>> from veritasreason.utils import Result, BatchResult
    >>> result = Result(value=processed_data)
    >>> if result.success:
    ...     use_data(result.value)
    >>> batch = BatchResult([Result(v) for v in values])
    >>> print(f"Success rate: {batch.success_rate:.2%}")

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

# Type Aliases
JSONType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
EntityDict = Dict[str, Any]
RelationshipDict = Dict[str, Any]
ConfigDict = Dict[str, Any]
DataDict = Dict[str, Any]


# Generic Type Variables
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


# Entity Types
class EntityType(str, Enum):
    """Entity type enumeration."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    CONCEPT = "CONCEPT"
    DATE = "DATE"
    TIME = "TIME"
    MONEY = "MONEY"
    PERCENT = "PERCENT"
    QUANTITY = "QUANTITY"
    ORDINAL = "ORDINAL"
    CARDINAL = "CARDINAL"
    UNKNOWN = "UNKNOWN"


# Data Types
class DataType(str, Enum):
    """Data type enumeration."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"


# Processing Status
class ProcessingStatus(str, Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


# Quality Levels
class QualityLevel(str, Enum):
    """Quality level enumeration."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    POOR = "poor"


# Relationship Types
class RelationshipType(str, Enum):
    """Relationship type enumeration."""

    WORKS_FOR = "WORKS_FOR"
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    RELATED_TO = "RELATED_TO"
    CAUSES = "CAUSES"
    AFFECTS = "AFFECTS"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    DURING = "DURING"
    SAME_AS = "SAME_AS"
    DIFFERENT_FROM = "DIFFERENT_FROM"
    SIMILAR_TO = "SIMILAR_TO"
    UNKNOWN = "UNKNOWN"


# Data Classes
@dataclass
class Entity:
    """Structured entity data."""

    id: str
    text: str
    type: Union[str, EntityType]
    confidence: float = 1.0
    start: Optional[int] = None
    end: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    relations: List[RelationshipDict] = field(default_factory=list)

    def __hash__(self):
        """Hash based on entity ID."""
        return hash(self.id)

    def __eq__(self, other):
        """Equality based on entity ID."""
        if not isinstance(other, Entity):
            if isinstance(other, dict):
                return self.id == (other.get("id") or other.get("entity_id"))
            return False
        return self.id == other.id


@dataclass
class Relationship:
    """Structured relationship data."""

    id: str
    source_id: str
    target_id: str
    type: Union[str, RelationshipType]
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of a processing operation."""

    status: ProcessingStatus
    data: Optional[Any] = None
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: Optional[float] = None


@dataclass
class QualityMetrics:
    """Data quality metrics."""

    score: float
    completeness: Optional[float] = None
    accuracy: Optional[float] = None
    consistency: Optional[float] = None
    validity: Optional[float] = None
    timeliness: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Protocol Definitions
class Processor(Protocol):
    """Protocol for data processors."""

    def process(self, data: Any, **options: Any) -> ProcessingResult:
        """Process data and return result."""
        ...


class Validator(Protocol):
    """Protocol for validators."""

    def validate(self, data: Any, **options: Any) -> bool:
        """Validate data and return True if valid."""
        ...


class Exporter(Protocol):
    """Protocol for data exporters."""

    def export(self, data: Any, destination: str, **options: Any) -> bool:
        """Export data to destination and return True if successful."""
        ...


class Importer(Protocol):
    """Protocol for data importers."""

    def import_data(self, source: str, **options: Any) -> Any:
        """Import data from source and return imported data."""
        ...


# Callable Type Aliases
DataTransformer = Callable[[Any], Any]
DataFilter = Callable[[Any], bool]
DataValidator = Callable[[Any], Tuple[bool, Optional[str]]]


# Generic Container Types
class Result(Generic[T]):
    """Generic result container."""

    def __init__(self, value: Optional[T] = None, error: Optional[str] = None):
        self.value = value
        self.error = error
        self.success = error is None

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        if self.success:
            return f"Result(value={self.value})"
        else:
            return f"Result(error={self.error})"


class BatchResult(Generic[T]):
    """Generic batch result container."""

    def __init__(self, results: List[Result[T]]):
        self.results = results
        self.successful = [r for r in results if r.success]
        self.failed = [r for r in results if not r.success]

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count


# Type Guards
def is_entity_dict(obj: Any) -> bool:
    """Type guard to check if object is an entity dictionary."""
    return isinstance(obj, dict) and "id" in obj and "text" in obj and "type" in obj


def is_relationship_dict(obj: Any) -> bool:
    """Type guard to check if object is a relationship dictionary."""
    return (
        isinstance(obj, dict)
        and "id" in obj
        and "source_id" in obj
        and "target_id" in obj
        and "type" in obj
    )


def is_processing_result(obj: Any) -> bool:
    """Type guard to check if object is a processing result."""
    return (
        isinstance(obj, dict)
        and "status" in obj
        and obj["status"] in [s.value for s in ProcessingStatus]
    )


# Conversion Functions
def entity_to_dict(entity: Entity) -> EntityDict:
    """Convert Entity dataclass to dictionary."""
    return {
        "id": entity.id,
        "text": entity.text,
        "type": entity.type.value
        if isinstance(entity.type, EntityType)
        else entity.type,
        "confidence": entity.confidence,
        "start": entity.start,
        "end": entity.end,
        "metadata": entity.metadata,
        "relations": entity.relations,
    }


def dict_to_entity(data: EntityDict) -> Entity:
    """Convert dictionary to Entity dataclass."""
    return Entity(
        id=data["id"],
        text=data["text"],
        type=data["type"],
        confidence=data.get("confidence", 1.0),
        start=data.get("start"),
        end=data.get("end"),
        metadata=data.get("metadata", {}),
        relations=data.get("relations", []),
    )


def relationship_to_dict(relationship: Relationship) -> RelationshipDict:
    """Convert Relationship dataclass to dictionary."""
    return {
        "id": relationship.id,
        "source_id": relationship.source_id,
        "target_id": relationship.target_id,
        "type": (
            relationship.type.value
            if isinstance(relationship.type, RelationshipType)
            else relationship.type
        ),
        "confidence": relationship.confidence,
        "metadata": relationship.metadata,
        "properties": relationship.properties,
    }


def dict_to_relationship(data: RelationshipDict) -> Relationship:
    """Convert dictionary to Relationship dataclass."""
    return Relationship(
        id=data["id"],
        source_id=data["source_id"],
        target_id=data["target_id"],
        type=data["type"],
        confidence=data.get("confidence", 1.0),
        metadata=data.get("metadata", {}),
        properties=data.get("properties", {}),
    )
