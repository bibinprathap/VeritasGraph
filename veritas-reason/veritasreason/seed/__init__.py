"""
Seed Data System Module

This module provides comprehensive seed data management for initial knowledge
graph construction, enabling the framework to build on existing verified
knowledge from multiple sources.

Algorithms Used:

Seed Data Loading:
    - CSV Loading: csv.DictReader() integration, row-by-row processing, delimiter detection, header extraction, encoding handling (UTF-8), type conversion, metadata injection (entity_type, relationship_type, source)
    - JSON Loading: json.load()/json.loads() integration, structure detection (list, dict with 'entities'/'data'/'records' keys, single object), nested structure handling, metadata injection, error handling
    - Database Loading: DBIngestor integration, SQL query execution, table export, connection pooling, result set processing, row-to-dictionary conversion, metadata injection
    - API Loading: HTTP GET requests (requests library), JSON response parsing, response structure detection (list, dict with 'entities'/'data'/'results'/'items' keys), authentication handling (Bearer token, custom headers), error handling and retries

Foundation Graph Creation:
    - Multi-Source Aggregation: Load data from all registered sources, iterate through sources sequentially, handle source failures gracefully, aggregate entities and relationships
    - Entity Extraction: Record-to-entity conversion (_record_to_entity), field mapping (id, text/name/label, type, confidence), metadata preservation, entity type inference
    - Relationship Extraction: Record-to-relationship conversion (_record_to_relationship), source/target ID extraction, relationship type inference, metadata preservation
    - Schema Validation: Template-based validation (_validate_against_template), structure checking, type validation, constraint checking

Data Integration:
    - Merge Strategies: Seed-first (seed data takes precedence, extracted fills gaps), extracted-first (extracted data takes precedence, seed fills gaps), merge (property merging, seed takes precedence for conflicts)
    - Entity Merging: ID-based entity matching, property merging, conflict resolution (seed-first, extracted-first, merge), duplicate handling
    - Relationship Merging: Triplet-based relationship matching (source_id, target_id, type), duplicate relationship detection, relationship property merging
    - Conflict Resolution: Priority-based conflict resolution, property-level merging, metadata preservation

Quality Validation:
    - Required Field Checking: Entity ID validation, relationship source/target ID validation, type field checking, missing field detection
    - Duplicate Detection: Entity ID duplicate detection (set-based), relationship duplicate detection (triplet-based), duplicate counting and reporting
    - Consistency Validation: Entity-reference consistency (relationships reference existing entities), type consistency checking, metadata consistency
    - Metrics Calculation: Entity count, relationship count, unique entity ID count, duplicate entity count, validation statistics

Version Management:
    - Source Versioning: Version string tracking per source, version history maintenance, version comparison
    - Version Tracking: Version list per source (versions dictionary), version registration, version querying

Export Operations:
    - JSON Export: JSON serialization (json.dump()), structure preservation, metadata inclusion, timestamp addition
    - CSV Export: Multi-file export (entities and relationships separate), csv.DictWriter() integration, header generation, field extraction, encoding handling

Key Features:
    - Multi-source seed data loading (CSV, JSON, Database, API)
    - Foundation graph creation from seed data
    - Seed data quality validation
    - Integration with extracted data using configurable merge strategies
    - Version management for seed sources
    - Export capabilities (JSON, CSV)
    - Schema template validation
    - Method registry for extensibility
    - Configuration management with environment variables and config files

Main Classes:
    - SeedDataManager: Main coordinator for seed data operations
    - SeedDataSource: Seed data source definition dataclass
    - SeedData: Seed data container dataclass


Example Usage:
    >>> from veritasreason.seed import SeedDataManager
    >>> manager = SeedDataManager()
    >>> manager.register_source("entities", "json", "data/entities.json")
    >>> foundation = manager.create_foundation_graph()

Author: VeritasReason Contributors
License: MIT
"""


from typing import Any, Dict, List, Optional, Union
from pathlib import Path


from .seed_manager import SeedData, SeedDataManager, SeedDataSource

__all__ = [
    "SeedDataManager",
    "SeedDataSource",
    "SeedData",
]
