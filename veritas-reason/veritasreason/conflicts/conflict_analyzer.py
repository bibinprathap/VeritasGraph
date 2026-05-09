"""
Conflict Analyzer

This module provides comprehensive conflict analysis capabilities for the
VeritasReason framework, analyzing patterns in conflicts, identifying conflict types,
and providing insights into conflict sources and trends.

Algorithms Used:

Pattern Identification:
    - Frequency-based Pattern Detection: Uses Counter and defaultdict to identify
      frequently occurring conflict patterns
    - Pattern Grouping: Groups conflicts by entity, property, type, and source
    - Pattern Frequency Analysis: Calculates frequency of each pattern type

Type Classification:
    - Conflict Type Categorization: Groups conflicts by ConflictType enumeration
    - Type-based Statistics: Calculates statistics per conflict type
    - Type Distribution Analysis: Analyzes distribution of conflict types

Severity Analysis:
    - Severity-based Grouping: Groups conflicts by severity level (low, medium,
      high, critical)
    - Severity Distribution: Calculates distribution of severities
    - Critical Conflict Identification: Identifies critical conflicts requiring
      immediate attention

Source Analysis:
    - Source-based Aggregation: Aggregates conflicts by source document
    - Source Conflict Frequency: Calculates conflict frequency per source
    - Source Credibility Correlation: Correlates conflicts with source credibility

Trend Analysis:
    - Temporal Trend Identification: Uses time-series analysis to identify trends
    - Conflict Rate Calculation: Calculates conflict rate over time
    - Trend Detection: Detects increasing or decreasing conflict trends

Statistical Analysis:
    - Conflict Statistics: Calculates mean, median, and distribution of conflicts
    - Entity Conflict Counts: Counts conflicts per entity
    - Property Conflict Counts: Counts conflicts per property
    - Overall Statistics: Provides overall conflict statistics

Key Features:
    - Analyzes conflict patterns and trends
    - Classifies conflict types
    - Identifies high-conflict areas
    - Generates conflict statistics
    - Provides conflict insights and recommendations
    - Supports conflict prevention strategies
    - Pattern-based conflict identification
    - Severity-based analysis

Main Classes:
    - ConflictPattern: Conflict pattern data structure
    - ConflictAnalyzer: Conflict analyzer for pattern identification

Example Usage:
    >>> from veritasreason.conflicts import ConflictAnalyzer
    >>> analyzer = ConflictAnalyzer()
    >>> analysis = analyzer.analyze_conflicts(conflicts)
    >>> report = analyzer.generate_insights_report(conflicts)

Author: VeritasReason Contributors
License: MIT
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .conflict_detector import Conflict


@dataclass
class ConflictPattern:
    """Conflict pattern analysis."""

    pattern_type: str
    frequency: int
    affected_entities: List[str] = field(default_factory=list)
    affected_properties: List[str] = field(default_factory=list)
    common_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConflictAnalyzer:
    """
    Conflict analyzer for pattern identification and insights.

    • Analyzes conflict patterns and trends
    • Classifies conflict types
    • Identifies high-conflict areas
    • Generates conflict statistics
    • Provides conflict insights and recommendations
    • Supports conflict prevention strategies
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize conflict analyzer.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("conflict_analyzer")
        self.config = config or {}
        self.config.update(kwargs)
        # Initialize progress tracker and ensure it's enabled
        self.progress_tracker = get_progress_tracker()
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

    def analyze_conflicts(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """
        Analyze conflicts and generate insights.

        Args:
            conflicts: List of conflicts to analyze

        Returns:
            Analysis results dictionary
        """
        # Track conflict analysis
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="conflicts",
            submodule="ConflictAnalyzer",
            message=f"Analyzing {len(conflicts)} conflicts",
        )

        try:
            total_steps = 6  # by_type, by_severity, by_source, by_entity, by_property, patterns, recommendations
            current_step = 0
            
            # Step 1: Analyze by type
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Analyzing by type... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            by_type = self._analyze_by_type(conflicts)
            
            # Step 2: Analyze by severity
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Analyzing by severity... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            by_severity = self._analyze_by_severity(conflicts)
            
            # Step 3: Analyze by source
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Analyzing by source... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            by_source = self._analyze_by_source(conflicts)
            
            # Step 4: Analyze by entity
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Analyzing by entity... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            by_entity = self._analyze_by_entity(conflicts)
            
            # Step 5: Analyze by property
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Analyzing by property... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            by_property = self._analyze_by_property(conflicts)
            
            # Step 6: Identify patterns and generate recommendations
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Identifying patterns and generating recommendations... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            patterns = self._identify_patterns(conflicts)
            recommendations = self._generate_recommendations(conflicts)
            
            analysis = {
                "total_conflicts": len(conflicts),
                "by_type": by_type,
                "by_severity": by_severity,
                "by_source": by_source,
                "by_entity": by_entity,
                "by_property": by_property,
                "patterns": patterns,
                "recommendations": recommendations,
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Analyzed {len(conflicts)} conflicts",
            )
            return analysis

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _analyze_by_type(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Analyze conflicts by type."""
        by_type = defaultdict(int)
        type_details = defaultdict(list)

        for conflict in conflicts:
            conflict_type = conflict.conflict_type.value
            by_type[conflict_type] += 1
            type_details[conflict_type].append(
                {
                    "conflict_id": conflict.conflict_id,
                    "entity_id": conflict.entity_id,
                    "severity": conflict.severity,
                }
            )

        return {"counts": dict(by_type), "details": dict(type_details)}

    def _analyze_by_severity(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Analyze conflicts by severity."""
        by_severity = defaultdict(int)
        severity_details = defaultdict(list)

        for conflict in conflicts:
            severity = conflict.severity
            by_severity[severity] += 1
            severity_details[severity].append(
                {
                    "conflict_id": conflict.conflict_id,
                    "type": conflict.conflict_type.value,
                    "entity_id": conflict.entity_id,
                    "property_name": conflict.property_name,
                }
            )

        return {"counts": dict(by_severity), "details": dict(severity_details)}

    def _analyze_by_entity(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Analyze conflicts by entity."""
        by_entity = defaultdict(int)
        entity_conflicts = defaultdict(list)

        for conflict in conflicts:
            if conflict.entity_id:
                by_entity[conflict.entity_id] += 1
                entity_conflicts[conflict.entity_id].append(
                    {
                        "conflict_id": conflict.conflict_id,
                        "property_name": conflict.property_name,
                        "type": conflict.conflict_type.value,
                        "severity": conflict.severity,
                    }
                )

        # Get top entities with most conflicts
        top_entities = sorted(by_entity.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "counts": dict(by_entity),
            "top_entities": [
                {"entity_id": eid, "conflict_count": count}
                for eid, count in top_entities
            ],
            "details": dict(entity_conflicts),
        }

    def _analyze_by_source(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Analyze conflicts by source."""
        by_source = defaultdict(int)
        source_conflicts = defaultdict(list)

        for conflict in conflicts:
            for source in conflict.sources:
                if isinstance(source, dict):
                    document = source.get("document", "unknown")
                    by_source[document] += 1
                    source_conflicts[document].append(
                        {
                            "conflict_id": conflict.conflict_id,
                            "entity_id": conflict.entity_id,
                            "property_name": conflict.property_name,
                            "type": conflict.conflict_type.value,
                            "severity": conflict.severity,
                        }
                    )

        # Get top sources with most conflicts
        top_sources = sorted(by_source.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "counts": dict(by_source),
            "top_sources": [
                {"source": source, "conflict_count": count}
                for source, count in top_sources
            ],
            "details": dict(source_conflicts),
        }

    def _analyze_by_property(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """Analyze conflicts by property."""
        by_property = defaultdict(int)
        property_conflicts = defaultdict(list)

        for conflict in conflicts:
            if conflict.property_name:
                by_property[conflict.property_name] += 1
                property_conflicts[conflict.property_name].append(
                    {
                        "conflict_id": conflict.conflict_id,
                        "entity_id": conflict.entity_id,
                        "type": conflict.conflict_type.value,
                        "severity": conflict.severity,
                    }
                )

        # Get top properties with most conflicts
        top_properties = sorted(by_property.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        return {
            "counts": dict(by_property),
            "top_properties": [
                {"property_name": prop, "conflict_count": count}
                for prop, count in top_properties
            ],
            "details": dict(property_conflicts),
        }

    def _identify_patterns(self, conflicts: List[Conflict]) -> List[ConflictPattern]:
        """Identify conflict patterns."""
        patterns = []

        # Pattern 1: Same property conflicts across multiple entities
        property_entity_map = defaultdict(set)
        for conflict in conflicts:
            if conflict.property_name and conflict.entity_id:
                property_entity_map[conflict.property_name].add(conflict.entity_id)

        for prop, entities in property_entity_map.items():
            if len(entities) > 3:  # Multiple entities affected
                patterns.append(
                    ConflictPattern(
                        pattern_type="widespread_property_conflict",
                        frequency=len(entities),
                        affected_properties=[prop],
                        affected_entities=list(entities),
                        metadata={
                            "description": (
                                f"Property '{prop}' has conflicts across "
                                f"{len(entities)} entities"
                            )
                        },
                    )
                )

        # Pattern 2: Same source appears in multiple conflicts
        source_conflict_map = defaultdict(int)
        for conflict in conflicts:
            for source in conflict.sources:
                source_conflict_map[source.get("document", "unknown")] += 1

        problematic_sources = [
            (source, count)
            for source, count in source_conflict_map.items()
            if count > 5
        ]

        for source, count in problematic_sources:
            patterns.append(
                ConflictPattern(
                    pattern_type="problematic_source",
                    frequency=count,
                    common_sources=[source],
                    metadata={
                        "description": f"Source '{source}' appears in {count} conflicts"
                    },
                )
            )

        # Pattern 3: High-severity conflicts cluster
        critical_conflicts = [c for c in conflicts if c.severity == "critical"]
        if len(critical_conflicts) > 5:
            patterns.append(
                ConflictPattern(
                    pattern_type="critical_conflict_cluster",
                    frequency=len(critical_conflicts),
                    metadata={
                        "description": (
                            f"{len(critical_conflicts)} critical conflicts detected"
                        )
                    },
                )
            )

        return patterns

    def _generate_recommendations(self, conflicts: List[Conflict]) -> List[str]:
        """Generate recommendations based on conflict analysis."""
        recommendations = []

        if not conflicts:
            return ["No conflicts detected. Continue monitoring."]

        # Analyze patterns
        by_property = self._analyze_by_property(conflicts)
        by_entity = self._analyze_by_entity(conflicts)
        patterns = self._identify_patterns(conflicts)

        # Recommendation 1: High-conflict properties
        top_properties = by_property.get("top_properties", [])
        if top_properties:
            top_prop = top_properties[0]
            recommendations.append(
                f"Property '{top_prop['property_name']}' has "
                f"{top_prop['conflict_count']} conflicts. Consider implementing "
                f"stricter validation or source verification."
            )

        # Recommendation 2: Problematic sources
        problematic_source_patterns = [
            p for p in patterns if p.pattern_type == "problematic_source"
        ]
        if problematic_source_patterns:
            for pattern in problematic_source_patterns:
                recommendations.append(
                    f"Source '{pattern.common_sources[0]}' appears in multiple "
                    f"conflicts. Review source quality and credibility."
                )

        # Recommendation 3: High-conflict entities
        top_entities = by_entity.get("top_entities", [])
        if top_entities:
            top_entity = top_entities[0]
            recommendations.append(
                f"Entity '{top_entity['entity_id']}' has "
                f"{top_entity['conflict_count']} conflicts. Review entity data sources "
                f"and merge strategy."
            )

        # Recommendation 4: Critical conflicts
        critical_count = len([c for c in conflicts if c.severity == "critical"])
        if critical_count > 0:
            recommendations.append(
                f"{critical_count} critical conflicts detected. Immediate review "
                f"required."
            )

        if not recommendations:
            recommendations.append("Monitor conflicts and review patterns regularly.")

        return recommendations

    def generate_insights_report(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """
        Generate comprehensive insights report.

        Args:
            conflicts: List of conflicts

        Returns:
            Insights report dictionary
        """
        analysis = self.analyze_conflicts(conflicts)

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_conflicts": analysis["total_conflicts"],
                "critical_count": analysis["by_severity"]["counts"].get("critical", 0),
                "high_count": analysis["by_severity"]["counts"].get("high", 0),
                "medium_count": analysis["by_severity"]["counts"].get("medium", 0),
                "low_count": analysis["by_severity"]["counts"].get("low", 0),
            },
            "analysis": analysis,
            "insights": {
                "most_conflict_prone_properties": [
                    p["property_name"]
                    for p in analysis["by_property"]["top_properties"][:5]
                ],
                "most_conflict_prone_entities": [
                    e["entity_id"] for e in analysis["by_entity"]["top_entities"][:5]
                ],
                "patterns_detected": len(analysis["patterns"]),
                "recommendations": analysis["recommendations"],
            },
        }

        return report

    def analyze_trends(self, conflicts: List[Conflict]) -> List[Dict[str, Any]]:
        """
        Analyze temporal trends in conflicts.

        Args:
            conflicts: List of conflicts to analyze

        Returns:
            List of trend analysis dictionaries
        """
        if not conflicts:
            return []

        # Group conflicts by time period
        from collections import defaultdict
        from datetime import datetime

        trends = []
        conflict_by_period = defaultdict(list)

        # Extract timestamps from conflicts
        for conflict in conflicts:
            # Try to get timestamp from sources or metadata
            timestamp = None
            for source in conflict.sources:
                if isinstance(source, dict):
                    metadata = source.get("metadata", {})
                    if "timestamp" in metadata:
                        timestamp = metadata["timestamp"]
                        break

            if not timestamp and conflict.metadata:
                timestamp = conflict.metadata.get("timestamp")

            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        try:
                            timestamp = datetime.strptime(timestamp, "%Y-%m-%d")
                        except ValueError:
                            timestamp = None

            if timestamp:
                # Group by month
                period_key = timestamp.strftime("%Y-%m")
                conflict_by_period[period_key].append(conflict)
            else:
                # If no timestamp, use current period
                period_key = datetime.now().strftime("%Y-%m")
                conflict_by_period[period_key].append(conflict)

        # Analyze trends
        sorted_periods = sorted(conflict_by_period.keys())
        if len(sorted_periods) < 2:
            # Not enough data for trend analysis
            return [
                {
                    "period": sorted_periods[0] if sorted_periods else "unknown",
                    "conflict_count": len(conflicts),
                    "trend": "insufficient_data",
                    "trend_direction": "stable",
                }
            ]

        for i, period in enumerate(sorted_periods):
            conflict_count = len(conflict_by_period[period])
            trend = "stable"

            if i > 0:
                prev_count = len(conflict_by_period[sorted_periods[i - 1]])
                if conflict_count > prev_count * 1.1:  # 10% increase
                    trend = "increasing"
                elif conflict_count < prev_count * 0.9:  # 10% decrease
                    trend = "decreasing"
                else:
                    trend = "stable"

            trends.append(
                {
                    "period": period,
                    "conflict_count": conflict_count,
                    "trend": trend,
                    "trend_direction": "up"
                    if trend == "increasing"
                    else "down"
                    if trend == "decreasing"
                    else "stable",
                }
            )

        return trends
