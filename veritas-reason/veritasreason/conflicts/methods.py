"""
Conflict Methods Module

This module provides all conflict methods as simple, reusable functions for
conflict detection, resolution, analysis, source tracking, and investigation
guide generation. It supports multiple conflict handling approaches and integrates
with the method registry for extensibility.

Supported Methods:

Conflict Detection:
    - "value": Property value conflict detection
    - "type": Entity type conflict detection
    - "relationship": Relationship conflict detection
    - "temporal": Temporal conflict detection
    - "logical": Logical conflict detection
    - "entity": Entity-wide conflict detection

Conflict Resolution:
    - "voting": Majority value selection from multiple sources
    - "credibility_weighted": Weighted average based on source credibility
    - "most_recent": Temporal-based selection (newest value)
    - "first_seen": Temporal-based selection (oldest value)
    - "highest_confidence": Confidence-based selection
    - "manual_review": Flag for human review
    - "expert_review": Flag for domain expert review

Conflict Analysis:
    - "pattern": Pattern identification and frequency analysis
    - "type": Conflict type classification
    - "severity": Severity-based analysis
    - "source": Source-based conflict analysis
    - "trend": Temporal trend identification

Source Tracking:
    - "property": Track sources for property values
    - "entity": Track sources for entities
    - "relationship": Track sources for relationships
    - "credibility": Source credibility scoring

Investigation Guide:
    - "guide": Generate investigation guides for conflicts
    - "checklist": Generate investigation checklists
    - "context": Extract conflict context

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
    - Multiple conflict detection methods
    - Multiple conflict resolution strategies
    - Comprehensive conflict analysis methods
    - Source tracking and provenance management
    - Investigation guide generation
    - Method dispatchers with registry support
    - Custom method registration capability
    - Consistent interface across all methods

Main Functions:
    - detect_conflicts: Conflict detection wrapper
    - resolve_conflicts: Conflict resolution wrapper
    - analyze_conflicts: Conflict analysis wrapper
    - track_sources: Source tracking wrapper
    - generate_investigation_guide: Investigation guide generation wrapper
    - get_conflict_method: Get conflict method by name

Example Usage:
    >>> from veritasreason.conflicts.methods import detect_conflicts, resolve_conflicts
    >>> conflicts = detect_conflicts(entities, method="value", property_name="name")
    >>> results = resolve_conflicts(conflicts, method="voting")
    >>> from veritasreason.conflicts.methods import get_conflict_method
    >>> method = get_conflict_method("resolution", "custom_method")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Callable, Dict, List, Optional, Union

from ..utils.logging import get_logger
from .conflict_analyzer import ConflictAnalyzer
from .conflict_detector import Conflict, ConflictDetector
from .conflict_resolver import ConflictResolver, ResolutionResult, ResolutionStrategy
from .investigation_guide import InvestigationGuide, InvestigationGuideGenerator
from .registry import method_registry
from .source_tracker import SourceReference, SourceTracker

logger = get_logger("conflicts_methods")


def detect_conflicts(
    entities: List[Dict[str, Any]],
    method: str = "value",
    property_name: Optional[str] = None,
    entity_type: Optional[str] = None,
    **kwargs,
) -> List[Conflict]:
    """
    Detect conflicts in entities (convenience function).

    This is a user-friendly wrapper that detects conflicts using the specified method.

    Args:
        entities: List of entity dictionaries to check for conflicts
        method: Detection method (default: "value")
            - "value": Property value conflict detection
            - "type": Entity type conflict detection
            - "relationship": Relationship conflict detection
            - "temporal": Temporal conflict detection
            - "logical": Logical conflict detection
            - "entity": Entity-wide conflict detection
        property_name: Property name to check (required for "value" method)
        entity_type: Optional entity type filter
        **kwargs: Additional options passed to ConflictDetector

    Returns:
        List of Conflict objects

    Examples:
        >>> from veritasreason.conflicts.methods import detect_conflicts
        >>> entities = [
        ...     {"id": "1", "name": "Apple Inc.", "source": "doc1"},
        ...     {"id": "1", "name": "Apple", "source": "doc2"}
        ... ]
        >>> conflicts = detect_conflicts(entities, method="value", property_name="name")
        >>> print(f"Found {len(conflicts)} conflicts")
    """
    # Check for custom method in registry
    custom_method = method_registry.get("detection", method)
    if custom_method:
        return custom_method(
            entities, property_name=property_name, entity_type=entity_type, **kwargs
        )

    # Use default ConflictDetector
    detector = ConflictDetector(**kwargs)

    # Map method to detector method
    if method == "value":
        if not property_name:
            raise ValueError("property_name is required for value conflict detection")
        return detector.detect_value_conflicts(entities, property_name, entity_type)
    elif method == "type":
        return detector.detect_type_conflicts(entities)
    elif method == "relationship":
        relationships = kwargs.get("relationships", [])
        return detector.detect_relationship_conflicts(relationships)
    elif method == "temporal":
        return detector.detect_temporal_conflicts(entities)
    elif method == "logical":
        return detector.detect_logical_conflicts(entities)
    elif method == "entity":
        return detector.detect_entity_conflicts(entities, entity_type)
    else:
        # Default to value conflicts
        if property_name:
            return detector.detect_value_conflicts(entities, property_name, entity_type)
        else:
            return detector.detect_entity_conflicts(entities, entity_type)


def resolve_conflicts(
    conflicts: Union[Conflict, List[Conflict]], method: str = "voting", **kwargs
) -> Union[ResolutionResult, List[ResolutionResult]]:
    """
    Resolve conflicts (convenience function).

    This is a user-friendly wrapper that resolves conflicts using the specified method.

    Args:
        conflicts: Single conflict or list of conflicts to resolve
        method: Resolution strategy (default: "voting")
            - "voting": Majority value selection
            - "credibility_weighted": Weighted average based on source credibility
            - "most_recent": Temporal-based selection (newest value)
            - "first_seen": Temporal-based selection (oldest value)
            - "highest_confidence": Confidence-based selection
            - "manual_review": Flag for human review
            - "expert_review": Flag for domain expert review
        **kwargs: Additional options passed to ConflictResolver

    Returns:
        ResolutionResult or List[ResolutionResult]

    Examples:
        >>> from veritasreason.conflicts.methods import resolve_conflicts
        >>> conflicts = detect_conflicts(entities, method="value", property_name="name")
        >>> results = resolve_conflicts(conflicts, method="voting")
        >>> for result in results:
        ...     print(f"Resolved: {result.resolved}, Value: {result.resolved_value}")
    """
    # Check for custom method in registry
    custom_method = method_registry.get("resolution", method)
    if custom_method:
        return custom_method(conflicts, **kwargs)

    # Use default ConflictResolver
    resolver = ConflictResolver(**kwargs)

    # Map method to resolution strategy
    strategy_map = {
        "voting": ResolutionStrategy.VOTING,
        "credibility_weighted": ResolutionStrategy.CREDIBILITY_WEIGHTED,
        "most_recent": ResolutionStrategy.MOST_RECENT,
        "first_seen": ResolutionStrategy.FIRST_SEEN,
        "highest_confidence": ResolutionStrategy.HIGHEST_CONFIDENCE,
        "manual_review": ResolutionStrategy.MANUAL_REVIEW,
        "expert_review": ResolutionStrategy.EXPERT_REVIEW,
    }

    strategy = strategy_map.get(method, ResolutionStrategy.VOTING)

    # Handle single conflict or list
    if isinstance(conflicts, Conflict):
        return resolver.resolve_conflict(conflicts, strategy=strategy)
    else:
        return resolver.resolve_conflicts(conflicts, strategy=strategy)


def analyze_conflicts(
    conflicts: List[Conflict], method: str = "pattern", **kwargs
) -> Dict[str, Any]:
    """
    Analyze conflicts (convenience function).

    This is a user-friendly wrapper that analyzes conflicts using the specified method.

    Args:
        conflicts: List of conflicts to analyze
        method: Analysis method (default: "pattern")
            - "pattern": Pattern identification and frequency analysis
            - "type": Conflict type classification
            - "severity": Severity-based analysis
            - "source": Source-based conflict analysis
            - "trend": Temporal trend identification
        **kwargs: Additional options passed to ConflictAnalyzer

    Returns:
        Dictionary containing analysis results

    Examples:
        >>> from veritasreason.conflicts.methods import analyze_conflicts
        >>> conflicts = detect_conflicts(entities, method="value", property_name="name")
        >>> analysis = analyze_conflicts(conflicts, method="pattern")
        >>> print(f"Patterns: {analysis.get('patterns')}")
    """
    # Check for custom method in registry
    custom_method = method_registry.get("analysis", method)
    if custom_method:
        return custom_method(conflicts, **kwargs)

    # Use default ConflictAnalyzer
    analyzer = ConflictAnalyzer(**kwargs)

    # Map method to analyzer method
    if method == "pattern":
        return analyzer.analyze_conflicts(conflicts)
    elif method == "type":
        analysis = analyzer.analyze_conflicts(conflicts)
        return {"by_type": analysis.get("by_type", {})}
    elif method == "severity":
        analysis = analyzer.analyze_conflicts(conflicts)
        return {"by_severity": analysis.get("by_severity", {})}
    elif method == "source":
        analysis = analyzer.analyze_conflicts(conflicts)
        return {"by_source": analysis.get("by_source", {})}
    elif method == "trend":
        return {"trends": analyzer.analyze_trends(conflicts)}
    else:
        # Default to full analysis
        return analyzer.analyze_conflicts(conflicts)


def track_sources(
    entity_id: str,
    property_name: Optional[str] = None,
    value: Optional[Any] = None,
    source: Optional[SourceReference] = None,
    method: str = "property",
    tracker: Optional[SourceTracker] = None,
    **kwargs,
) -> bool:
    """
    Track source information (convenience function).

    This is a user-friendly wrapper that tracks source information using the
    specified method.

    Args:
        entity_id: Entity identifier
        property_name: Property name (for property tracking)
        value: Property value (for property tracking)
        source: Source reference
        method: Tracking method (default: "property")
            - "property": Track sources for property values
            - "entity": Track sources for entities
            - "relationship": Track sources for relationships
        tracker: Optional SourceTracker instance to use (otherwise creates new one)
        **kwargs: Additional options passed to SourceTracker

    Returns:
        True if tracking successful

    Examples:
        >>> from veritasreason.conflicts.methods import track_sources
        >>> from veritasreason.conflicts import SourceReference
        >>> source = SourceReference(document="doc1", page=1, confidence=0.9)
        >>> track_sources(
        ...     "entity_1", property_name="name", value="Apple", source=source
        ... )
    """
    # Check for custom method in registry
    custom_method = method_registry.get("tracking", method)
    if custom_method:
        return custom_method(
            entity_id,
            property_name=property_name,
            value=value,
            source=source,
            tracker=tracker,
            **kwargs,
        )

    # Use provided tracker or create new one
    # Also check kwargs for 'source_tracker' for compatibility
    actual_tracker = tracker or kwargs.get("source_tracker") or SourceTracker(**kwargs)

    # Map method to tracker method
    if method == "property":
        if not property_name or not value or not source:
            raise ValueError(
                "property_name, value, and source are required for property tracking"
            )
        return actual_tracker.track_property_source(
            entity_id, property_name, value, source, **kwargs
        )
    elif method == "entity":
        if not source:
            raise ValueError("source is required for entity tracking")
        return actual_tracker.track_entity_source(entity_id, source, **kwargs)
    elif method == "relationship":
        relationship_id = kwargs.get("relationship_id")
        if not relationship_id or not source:
            raise ValueError(
                "relationship_id and source are required for relationship tracking"
            )
        return actual_tracker.track_relationship_source(
            relationship_id, source, **kwargs
        )
    else:
        # Default to property tracking
        if property_name and value and source:
            return actual_tracker.track_property_source(
                entity_id, property_name, value, source, **kwargs
            )
        else:
            raise ValueError("Invalid parameters for tracking")


def generate_investigation_guide(
    conflict: Union[Conflict, List[Conflict]], method: str = "guide", **kwargs
) -> Union[InvestigationGuide, List[InvestigationGuide]]:
    """
    Generate investigation guide (convenience function).

    This is a user-friendly wrapper that generates investigation guides using the
    specified method.

    Args:
        conflict: Single conflict or list of conflicts
        method: Guide generation method (default: "guide")
            - "guide": Generate investigation guides for conflicts
            - "checklist": Generate investigation checklists
            - "context": Extract conflict context
        **kwargs: Additional options passed to InvestigationGuideGenerator

    Returns:
        InvestigationGuide or List[InvestigationGuide]

    Examples:
        >>> from veritasreason.conflicts.methods import generate_investigation_guide
        >>> conflicts = detect_conflicts(entities, method="value", property_name="name")
        >>> guide = generate_investigation_guide(conflicts[0], method="guide")
        >>> print(f"Investigation steps: {len(guide.investigation_steps)}")
    """
    # Check for custom method in registry
    custom_method = method_registry.get("investigation", method)
    if custom_method:
        return custom_method(conflict, **kwargs)

    # Use default InvestigationGuideGenerator
    generator = InvestigationGuideGenerator(**kwargs)

    # Map method to generator method
    if method == "guide":
        if isinstance(conflict, Conflict):
            return generator.generate_guide(conflict, **kwargs)
        else:
            return generator.generate_guides(conflict, **kwargs)
    elif method == "checklist":
        if isinstance(conflict, Conflict):
            guide = generator.generate_guide(conflict, **kwargs)
            return generator.export_investigation_checklist(
                guide, format="text", **kwargs
            )
        else:
            checklists = []
            for c in conflict:
                guide = generator.generate_guide(c, **kwargs)
                checklist = generator.export_investigation_checklist(
                    guide, format="text", **kwargs
                )
                checklists.append(checklist)
            return checklists
    elif method == "context":
        if isinstance(conflict, Conflict):
            guide = generator.generate_guide(conflict, **kwargs)
            return guide.context
        else:
            contexts = []
            for c in conflict:
                guide = generator.generate_guide(c, **kwargs)
                contexts.append(guide.context)
            return contexts
    else:
        # Default to guide generation
        if isinstance(conflict, Conflict):
            return generator.generate_guide(conflict, **kwargs)
        else:
            return generator.generate_guides(conflict, **kwargs)


def get_conflict_method(task: str, name: str) -> Optional[Callable]:
    """
    Get conflict method by task and name.

    This function retrieves a registered conflict method from the registry
    or returns a built-in method if available.

    Args:
        task: Task type ("detection", "resolution", "analysis", "tracking",
            "investigation")
        name: Method name

    Returns:
        Method function or None if not found

    Examples:
        >>> from veritasreason.conflicts.methods import get_conflict_method
        >>> method = get_conflict_method("resolution", "custom_method")
        >>> if method:
        ...     result = method(conflicts)
    """
    # First check registry
    method = method_registry.get(task, name)
    if method:
        return method

    # Check built-in methods
    builtin_methods = {
        "detection": {
            "value": lambda entities, **kw: detect_conflicts(
                entities, method="value", **kw
            ),
            "type": lambda entities, **kw: detect_conflicts(
                entities, method="type", **kw
            ),
            "relationship": lambda entities, **kw: detect_conflicts(
                entities, method="relationship", **kw
            ),
            "temporal": lambda entities, **kw: detect_conflicts(
                entities, method="temporal", **kw
            ),
            "logical": lambda entities, **kw: detect_conflicts(
                entities, method="logical", **kw
            ),
            "entity": lambda entities, **kw: detect_conflicts(
                entities, method="entity", **kw
            ),
        },
        "resolution": {
            "voting": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="voting", **kw
            ),
            "credibility_weighted": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="credibility_weighted", **kw
            ),
            "most_recent": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="most_recent", **kw
            ),
            "first_seen": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="first_seen", **kw
            ),
            "highest_confidence": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="highest_confidence", **kw
            ),
            "manual_review": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="manual_review", **kw
            ),
            "expert_review": lambda conflicts, **kw: resolve_conflicts(
                conflicts, method="expert_review", **kw
            ),
        },
        "analysis": {
            "pattern": lambda conflicts, **kw: analyze_conflicts(
                conflicts, method="pattern", **kw
            ),
            "type": lambda conflicts, **kw: analyze_conflicts(
                conflicts, method="type", **kw
            ),
            "severity": lambda conflicts, **kw: analyze_conflicts(
                conflicts, method="severity", **kw
            ),
            "source": lambda conflicts, **kw: analyze_conflicts(
                conflicts, method="source", **kw
            ),
            "trend": lambda conflicts, **kw: analyze_conflicts(
                conflicts, method="trend", **kw
            ),
            "statistics": lambda conflicts, **kw: analyze_conflicts(
                conflicts, method="statistics", **kw
            ),
        },
        "tracking": {
            "property": lambda entity_id, **kw: track_sources(
                entity_id, method="property", **kw
            ),
            "entity": lambda entity_id, **kw: track_sources(
                entity_id, method="entity", **kw
            ),
            "relationship": lambda entity_id, **kw: track_sources(
                entity_id, method="relationship", **kw
            ),
        },
        "investigation": {
            "guide": lambda conflict, **kw: generate_investigation_guide(
                conflict, method="guide", **kw
            ),
            "checklist": lambda conflict, **kw: generate_investigation_guide(
                conflict, method="checklist", **kw
            ),
            "context": lambda conflict, **kw: generate_investigation_guide(
                conflict, method="context", **kw
            ),
        },
    }

    if task in builtin_methods and name in builtin_methods[task]:
        return builtin_methods[task][name]

    return None


def list_available_methods(task: Optional[str] = None) -> Dict[str, List[str]]:
    """
    List all available conflict methods.

    Args:
        task: Optional task type to filter by

    Returns:
        Dictionary mapping task types to method names

    Examples:
        >>> from veritasreason.conflicts.methods import list_available_methods
        >>> all_methods = list_available_methods()
        >>> resolution_methods = list_available_methods("resolution")
    """
    # Get registered methods
    registered = method_registry.list_all(task=task)

    # Add built-in methods
    builtin_methods = {
        "detection": ["value", "type", "relationship", "temporal", "logical", "entity"],
        "resolution": [
            "voting",
            "credibility_weighted",
            "most_recent",
            "first_seen",
            "highest_confidence",
            "manual_review",
            "expert_review",
        ],
        "analysis": ["pattern", "type", "severity", "source", "trend"],
        "tracking": ["property", "entity", "relationship"],
        "investigation": ["guide", "checklist", "context"],
    }

    if task:
        # Merge for specific task
        result = {
            task: list(set(registered.get(task, []) + builtin_methods.get(task, [])))
        }
    else:
        # Merge for all tasks
        result = {}
        for t in set(list(registered.keys()) + list(builtin_methods.keys())):
            result[t] = list(set(registered.get(t, []) + builtin_methods.get(t, [])))

    return result
