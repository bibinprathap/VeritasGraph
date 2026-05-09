"""
Enhanced Change Management Module for VeritasReason

This module provides comprehensive change management capabilities including:
- Persistent version storage (SQLite and in-memory)
- Detailed change tracking and diff algorithms
- Standardized metadata and audit trails
- Data integrity verification with checksums
- Enhanced version managers for KG and ontologies
- Enterprise compliance support (HIPAA, SOX, FDA)

Public API:
    ChangeLogEntry: Standardized metadata for version changes
    VersionStorage: Abstract storage interface
    InMemoryVersionStorage: Fast in-memory storage backend
    SQLiteVersionStorage: Persistent SQLite storage backend
    compute_checksum: SHA-256 checksum computation
    verify_checksum: Data integrity verification
    EnhancedTemporalVersionManager: Advanced KG version management
    EnhancedVersionManager: Advanced ontology version management
"""

from .change_log import ChangeLogEntry
from .version_storage import (
    VersionStorage,
    InMemoryVersionStorage,
    SQLiteVersionStorage,
    compute_checksum,
    verify_checksum
)
from .managers import (
    BaseVersionManager,
    TemporalVersionManager,
    OntologyVersionManager
)
from .ontology_version_manager import VersionManager, OntologyVersion

__all__ = [
    # Change metadata
    "ChangeLogEntry",
    
    # Storage backends
    "VersionStorage",
    "InMemoryVersionStorage", 
    "SQLiteVersionStorage",
    
    # Integrity utilities
    "compute_checksum",
    "verify_checksum",
    
    # Version managers
    "BaseVersionManager",
    "TemporalVersionManager",
    "OntologyVersionManager",
    
    # Ontology version management
    "VersionManager",
    "OntologyVersion"
]

__version__ = "1.0.0"
__author__ = "VeritasReason Team"
__description__ = "Enhanced Change Management for VeritasReason"
