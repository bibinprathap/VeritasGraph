"""
Conflict Detection and Resolution Module

This module provides comprehensive conflict detection and resolution capabilities
for the VeritasReason framework, identifying conflicts from multiple sources and
providing investigation guides for discrepancies. It enables source tracking,
conflict analysis, and automated resolution strategies.

Algorithms Used:

Conflict Detection:
    - Value Comparison: Property value comparison across sources with equality checking
    - Type Mismatch Detection: Entity type comparison and mismatch identification
    - Relationship Consistency: Relationship property comparison and inconsistency
      detection
    - Temporal Analysis: Time-based conflict detection using timestamp comparison
    - Logical Consistency: Logical rule validation and inconsistency detection
    - Severity Calculation: Multi-factor severity scoring (property importance,
      value difference, source count)
    - Confidence Scoring: Confidence calculation based on source credibility and
      value diversity

Conflict Resolution:
    - Voting Algorithm: Majority value selection using Counter-based frequency counting
    - Credibility Weighted: Weighted average calculation using source credibility scores
    - Temporal Selection: Timestamp-based selection (newest/oldest value)
    - Confidence Selection: Maximum confidence value selection
    - Manual Flagging: Conflict flagging for human review workflow

Conflict Analysis:
    - Pattern Identification: Frequency-based pattern detection using Counter and
      defaultdict
    - Type Classification: Conflict type categorization and grouping
    - Severity Analysis: Severity-based grouping and analysis
    - Source Analysis: Source-based conflict aggregation and analysis
    - Trend Analysis: Temporal trend identification using time-series analysis

Source Tracking:
    - Property Source Tracking: Dictionary-based property-to-source mapping
    - Entity Source Tracking: Entity-to-source relationship tracking
    - Relationship Source Tracking: Relationship-to-source mapping
    - Credibility Scoring: Source credibility calculation based on historical accuracy
    - Traceability Chain: Graph-based traceability chain generation

Investigation Guide:
    - Guide Generation: Template-based investigation guide generation
    - Checklist Generation: Step-by-step checklist creation
    - Context Extraction: Conflict context and metadata extraction
    - Step Generation: Investigation step generation based on conflict type

Key Features:
    - Multi-source conflict detection (value, type, relationship, temporal, logical)
    - Source tracking and provenance management
    - Conflict analysis and pattern identification
    - Multiple resolution strategies (voting, credibility-weighted, recency, confidence)
    - Investigation guide generation
    - Source credibility scoring
    - Conflict reporting
    - Method registry for custom conflict methods
    - Configuration management with environment variables and config files

Main Classes:
    - ConflictDetector: Detects conflicts from multiple sources
    - ConflictResolver: Resolves conflicts using various strategies
    - ConflictAnalyzer: Analyzes conflict patterns and trends
    - SourceTracker: Tracks source information and provenance
    - InvestigationGuideGenerator: Generates investigation guides
    - MethodRegistry: Registry for custom conflict methods
    - ConflictsConfig: Configuration manager for conflicts module

Example Usage:
    >>> from veritasreason.conflicts import ConflictDetector, ConflictResolver
    >>> # Using classes directly
    >>> detector = ConflictDetector()
    >>> conflicts = detector.detect_value_conflicts(entities, "name")
    >>> resolver = ConflictResolver()
    >>> results = resolver.resolve_conflicts(conflicts, strategy="voting")

Author: VeritasReason Contributors
License: MIT
"""

from .config import ConflictsConfig, conflicts_config
from .conflict_analyzer import ConflictAnalyzer, ConflictPattern
from .conflict_detector import Conflict, ConflictDetector, ConflictType
from .conflict_resolver import ConflictResolver, ResolutionResult, ResolutionStrategy
from .investigation_guide import (
    InvestigationGuide,
    InvestigationGuideGenerator,
    InvestigationStep,
)
from .methods import (
    analyze_conflicts,
    detect_conflicts,
    generate_investigation_guide,
    get_conflict_method,
    list_available_methods,
    resolve_conflicts,
    track_sources,
)
from .registry import MethodRegistry, method_registry
from .source_tracker import PropertySource, SourceReference, SourceTracker

voting = ResolutionStrategy.VOTING
credibility_weighted = ResolutionStrategy.CREDIBILITY_WEIGHTED
most_recent = ResolutionStrategy.MOST_RECENT
first_seen = ResolutionStrategy.FIRST_SEEN
highest_confidence = ResolutionStrategy.HIGHEST_CONFIDENCE
manual_review = ResolutionStrategy.MANUAL_REVIEW
expert_review = ResolutionStrategy.EXPERT_REVIEW


__all__ = [
    # Core Classes
    "ConflictDetector",
    "Conflict",
    "ConflictType",
    "SourceTracker",
    "SourceReference",
    "PropertySource",
    "ConflictResolver",
    "ResolutionResult",
    "ResolutionStrategy",
    "voting",
    "credibility_weighted",
    "most_recent",
    "first_seen",
    "highest_confidence",
    "manual_review",
    "expert_review",
    "InvestigationGuideGenerator",
    "InvestigationGuide",
    "InvestigationStep",
    "ConflictAnalyzer",
    "ConflictPattern",
    # Registry and Methods
    "MethodRegistry",
    "method_registry",
    "detect_conflicts",
    "resolve_conflicts",
    "analyze_conflicts",
    "track_sources",
    "generate_investigation_guide",
    "get_conflict_method",
    "list_available_methods",
    # Configuration
    "ConflictsConfig",
    "conflicts_config",
]
