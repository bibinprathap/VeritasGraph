"""
Investigation Guide Generator

This module provides comprehensive investigation guide generation capabilities
for the VeritasReason framework, generating investigation guides for detected
conflicts to help domain experts investigate and resolve discrepancies.

Algorithms Used:

Guide Generation:
    - Template-based Generation: Uses conflict type and severity to select appropriate
      templates
    - Context Extraction: Extracts conflict context from Conflict object and
      SourceTracker
    - Step Generation: Generates investigation steps based on conflict characteristics
    - Severity-based Recommendations: Provides recommendations based on conflict
      severity

Checklist Generation:
    - Step-by-step Checklist Creation: Converts investigation steps into checklist
      format
    - Action Item Extraction: Extracts actionable items from investigation steps
    - Priority Ordering: Orders checklist items by priority and severity

Context Extraction:
    - Conflict Context: Extracts conflict metadata, sources, and conflicting values
    - Source Context: Extracts source information from SourceTracker
    - Historical Context: Includes historical conflict information if available
    - Related Conflicts: Identifies related conflicts for context

Step Generation:
    - Type-based Steps: Generates steps specific to conflict type (value, type,
      relationship, etc.)
    - Severity-based Steps: Adjusts steps based on conflict severity
    - Source Investigation Steps: Includes steps for investigating conflicting sources
    - Resolution Steps: Suggests resolution steps based on conflict characteristics

Export Formats:
    - Text Export: Plain text format for investigation guides
    - Markdown Export: Markdown format for documentation and reporting
    - Structured Export: Structured format for programmatic processing

Key Features:
    - Generates conflict investigation checklists
    - Identifies conflicting source documents
    - Provides conflict context and history
    - Suggests investigation steps
    - Generates conflict summary reports
    - Supports compliance audit workflows
    - Export formats (text, markdown)
    - Severity-based recommendations

Main Classes:
    - InvestigationStep: Investigation step data structure
    - InvestigationGuide: Investigation guide data structure
    - InvestigationGuideGenerator: Investigation guide generator for conflicts

Example Usage:
    >>> from veritasreason.conflicts import InvestigationGuideGenerator
    >>> generator = InvestigationGuideGenerator()
    >>> guide = generator.generate_guide(conflict)
    >>> checklist = generator.export_investigation_checklist(guide, format="markdown")

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .conflict_detector import Conflict, ConflictType
from .source_tracker import SourceTracker


@dataclass
class InvestigationStep:
    """Investigation step definition."""

    step_number: int
    description: str
    action: str
    expected_outcome: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvestigationGuide:
    """Investigation guide for a conflict."""

    conflict_id: str
    conflict_summary: str
    severity: str
    conflicting_sources: List[Dict[str, Any]] = field(default_factory=list)
    investigation_steps: List[InvestigationStep] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def title(self) -> str:
        """Get guide title."""
        return f"Investigation: {self.conflict_id}"


class InvestigationGuideGenerator:
    """
    Investigation guide generator for conflicts.

    • Generates conflict investigation checklists
    • Identifies conflicting source documents
    • Provides conflict context and history
    • Suggests investigation steps
    • Generates conflict summary reports
    • Supports compliance audit workflows
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize investigation guide generator.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options:
                - source_tracker: Source tracker instance
                - include_traceability: Include traceability information
        """
        self.logger = get_logger("investigation_guide")
        self.config = config or {}
        self.config.update(kwargs)

        self.source_tracker = self.config.get("source_tracker") or SourceTracker()
        self.include_traceability = self.config.get("include_traceability", True)
        self.progress_tracker = get_progress_tracker()

    def generate_guide(
        self, conflict: Conflict, additional_context: Optional[Dict[str, Any]] = None
    ) -> InvestigationGuide:
        """
        Generate investigation guide for a conflict.

        Args:
            conflict: Conflict to investigate
            additional_context: Additional context information

        Returns:
            Investigation guide
        """
        # Track investigation guide generation
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="conflicts",
            submodule="InvestigationGuideGenerator",
            message=f"Generating guide for conflict: {conflict.conflict_id}",
        )

        try:
            guide = InvestigationGuide(
                conflict_id=conflict.conflict_id,
                conflict_summary=self._generate_summary(conflict),
                severity=conflict.severity,
                conflicting_sources=conflict.sources,
                investigation_steps=self._generate_investigation_steps(conflict),
                recommended_actions=self._generate_recommended_actions(conflict),
                context=additional_context or {},
            )

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="Investigation guide generated"
            )
            return guide

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def generate_guides(
        self,
        conflicts: List[Conflict],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> List[InvestigationGuide]:
        """
        Generate investigation guides for multiple conflicts.

        Args:
            conflicts: List of conflicts
            additional_context: Additional context information

        Returns:
            List of investigation guides
        """
        guides = []

        for conflict in conflicts:
            guide = self.generate_guide(conflict, additional_context)
            guides.append(guide)

        return guides

    def _generate_summary(self, conflict: Conflict) -> str:
        """Generate conflict summary."""
        parts = []

        parts.append(f"Conflict Type: {conflict.conflict_type.value}")

        if conflict.entity_id:
            parts.append(f"Entity: {conflict.entity_id}")

        if conflict.property_name:
            parts.append(f"Property: {conflict.property_name}")

        if conflict.conflicting_values:
            unique_values = list(set(str(v) for v in conflict.conflicting_values))
            parts.append(f"Conflicting Values: {', '.join(unique_values)}")

        parts.append(f"Severity: {conflict.severity}")

        if conflict.sources:
            source_docs = list(
                set(s.get("document", "unknown") for s in conflict.sources)
            )
            parts.append(f"Sources: {', '.join(source_docs)}")

        return " | ".join(parts)

    def _generate_investigation_steps(
        self, conflict: Conflict
    ) -> List[InvestigationStep]:
        """Generate investigation steps."""
        steps = []

        # Step 1: Review conflict details
        steps.append(
            InvestigationStep(
                step_number=1,
                description="Review conflict details and context",
                action=(
                    "Examine the conflict summary and identify the conflicting values"
                ),
                expected_outcome=(
                    "Understanding of the nature and scope of the conflict"
                ),
            )
        )

        # Step 2: Identify source documents
        if conflict.sources:
            source_list = ", ".join(
                set(s.get("document", "unknown") for s in conflict.sources)
            )
            steps.append(
                InvestigationStep(
                    step_number=2,
                    description="Identify all source documents",
                    action=(
                        "Locate and review the following source documents: "
                        f"{source_list}"
                    ),
                    expected_outcome="All source documents identified and accessible",
                )
            )

        # Step 3: Compare source documents
        if conflict.sources and len(conflict.sources) > 1:
            steps.append(
                InvestigationStep(
                    step_number=3,
                    description="Compare conflicting information across sources",
                    action=(
                        "Review each source document and note the specific value and "
                        "context for each"
                    ),
                    expected_outcome="List of values and their sources with context",
                )
            )

        # Step 4: Check source credibility
        if conflict.sources:
            steps.append(
                InvestigationStep(
                    step_number=4,
                    description="Assess source credibility and reliability",
                    action="Review source credibility scores and document metadata",
                    expected_outcome="Source credibility assessment completed",
                )
            )

        # Step 5: Determine resolution
        steps.append(
            InvestigationStep(
                step_number=5,
                description="Determine resolution approach",
                action=(
                    "Choose resolution strategy based on source credibility, "
                    "recency, and business rules"
                ),
                expected_outcome="Resolution approach selected",
            )
        )

        # Step 6: Document resolution
        steps.append(
            InvestigationStep(
                step_number=6,
                description="Document resolution decision",
                action="Record the resolved value, resolution method, and rationale",
                expected_outcome="Resolution documented with traceability",
            )
        )

        return steps

    def _generate_recommended_actions(self, conflict: Conflict) -> List[str]:
        """Generate recommended actions."""
        actions = []

        # Severity-based actions
        if conflict.severity == "critical":
            actions.append("URGENT: Critical conflict requires immediate attention")
            actions.append("Escalate to domain expert or data owner")

        elif conflict.severity == "high":
            actions.append("High priority: Review within 24 hours")
            actions.append("Consult with subject matter expert")

        # Type-based actions
        if conflict.conflict_type == ConflictType.VALUE_CONFLICT:
            actions.append("Compare source documents side-by-side")
            actions.append("Check for data entry errors or typos")
            actions.append("Verify if values represent different time periods")

        elif conflict.conflict_type == ConflictType.TYPE_CONFLICT:
            actions.append("Review entity type definitions")
            actions.append("Check for classification errors")

        elif conflict.conflict_type == ConflictType.TEMPORAL_CONFLICT:
            actions.append("Check temporal context of each value")
            actions.append("Determine if conflict represents historical change")

        # Source-based actions
        if conflict.sources:
            source_docs = set(s.get("document", "unknown") for s in conflict.sources)
            if len(source_docs) > 1:
                actions.append(
                    f"Review {len(source_docs)} conflicting source documents"
                )
                actions.append("Identify most authoritative source")

        # Default actions
        if not actions:
            actions.append(
                "Review conflict details and determine appropriate resolution"
            )
            actions.append("Document resolution decision for future reference")

        return actions

    def generate_conflict_report(
        self, conflicts: List[Conflict], format: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive conflict report.

        Args:
            conflicts: List of conflicts
            format: Report format ('detailed', 'summary')

        Returns:
            Conflict report dictionary
        """
        guides = self.generate_guides(conflicts)

        report = {
            "generated_at": datetime.now().isoformat(),
            "total_conflicts": len(conflicts),
            "conflicts": [],
        }

        for guide in guides:
            conflict_data = {
                "conflict_id": guide.conflict_id,
                "summary": guide.conflict_summary,
                "severity": guide.severity,
                "conflicting_sources": guide.conflicting_sources,
                "recommended_actions": guide.recommended_actions,
            }

            if format == "detailed":
                conflict_data["investigation_steps"] = [
                    {
                        "step_number": step.step_number,
                        "description": step.description,
                        "action": step.action,
                        "expected_outcome": step.expected_outcome,
                    }
                    for step in guide.investigation_steps
                ]

            report["conflicts"].append(conflict_data)

        # Add summary statistics
        severity_counts = {}
        for conflict in conflicts:
            severity = conflict.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        report["summary"] = {
            "by_severity": severity_counts,
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0),
            "medium_count": severity_counts.get("medium", 0),
            "low_count": severity_counts.get("low", 0),
        }

        return report

    def export_investigation_checklist(
        self, guide: InvestigationGuide, format: str = "text"
    ) -> str:
        """
        Export investigation guide as checklist.

        Args:
            guide: Investigation guide
            format: Export format ('text', 'markdown')

        Returns:
            Checklist string
        """
        if format == "markdown":
            lines = [
                f"# Investigation Guide: {guide.conflict_id}",
                "",
                f"**Conflict Summary:** {guide.conflict_summary}",
                f"**Severity:** {guide.severity}",
                "",
                "## Investigation Steps",
                "",
            ]

            for step in guide.investigation_steps:
                lines.append(f"### Step {step.step_number}: {step.description}")
                lines.append(f"- **Action:** {step.action}")
                if step.expected_outcome:
                    lines.append(f"- **Expected Outcome:** {step.expected_outcome}")
                lines.append("")

            lines.extend(["## Recommended Actions", ""])

            for action in guide.recommended_actions:
                lines.append(f"- {action}")

            return "\n".join(lines)

        else:  # text format
            lines = [
                f"INVESTIGATION GUIDE: {guide.conflict_id}",
                "=" * 60,
                f"Conflict Summary: {guide.conflict_summary}",
                f"Severity: {guide.severity}",
                "",
                "INVESTIGATION STEPS:",
                "",
            ]

            for step in guide.investigation_steps:
                lines.append(f"Step {step.step_number}: {step.description}")
                lines.append(f"  Action: {step.action}")
                if step.expected_outcome:
                    lines.append(f"  Expected Outcome: {step.expected_outcome}")
                lines.append("")

            lines.extend(["RECOMMENDED ACTIONS:", ""])

            for action in guide.recommended_actions:
                lines.append(f"  - {action}")

            return "\n".join(lines)
