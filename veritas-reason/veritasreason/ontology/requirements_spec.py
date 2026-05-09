"""
Ontology Requirements Specification Module

This module supports the ontology requirements specification phase, including
competency questions, scope definition, and purpose documentation. It helps
ensure that ontologies are designed to meet specific functional requirements.

Key Features:
    - Competency question management
    - Scope definition and validation
    - Purpose and use case documentation
    - Stakeholder collaboration tracking
    - Domain expert input integration
    - Requirements traceability
    - Specification validation

Main Classes:
    - RequirementsSpecManager: Manager for requirements specifications
    - RequirementsSpec: Dataclass representing a requirements specification

Example Usage:
    >>> from veritasreason.ontology import RequirementsSpecManager
    >>> manager = RequirementsSpecManager()
    >>> spec = manager.create_spec("PersonOntologySpec", "Model person-related concepts", "Person, Organization, Role entities")
    >>> manager.add_competency_question("PersonOntologySpec", "Who are the employees of an organization?", category="organizational")
    >>> trace = manager.trace_requirements("PersonOntologySpec", ontology)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .competency_questions import CompetencyQuestion, CompetencyQuestionsManager


@dataclass
class RequirementsSpec:
    """Requirements specification for ontology."""

    name: str
    purpose: str
    scope: str
    competency_questions: List[CompetencyQuestion] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    domain: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequirementsSpecManager:
    """
    Requirements specification manager for ontologies.

    • Competency question management
    • Scope definition and validation
    • Purpose and use case documentation
    • Stakeholder collaboration tracking
    • Domain expert input integration
    • Requirements traceability
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize requirements spec manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("requirements_spec_manager")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.competency_questions_manager = CompetencyQuestionsManager(**self.config)
        self.specs: Dict[str, RequirementsSpec] = {}

    def create_spec(
        self, name: str, purpose: str, scope: str, **options
    ) -> RequirementsSpec:
        """
        Create requirements specification.

        Args:
            name: Specification name
            purpose: Purpose description
            scope: Scope description
            **options: Additional options:
                - domain: Domain name
                - stakeholders: List of stakeholders
                - use_cases: List of use cases

        Returns:
            Created requirements specification
        """
        spec = RequirementsSpec(
            name=name,
            purpose=purpose,
            scope=scope,
            domain=options.get("domain", ""),
            stakeholders=options.get("stakeholders", []),
            use_cases=options.get("use_cases", []),
            metadata={
                "created_at": datetime.now().isoformat(),
                **options.get("metadata", {}),
            },
        )

        self.specs[name] = spec
        self.logger.info(f"Created requirements specification: {name}")

        return spec

    def add_competency_question(
        self,
        spec_name: str,
        question: str,
        category: str = "general",
        priority: int = 1,
        **metadata,
    ) -> CompetencyQuestion:
        """
        Add competency question to specification.

        Args:
            spec_name: Specification name
            question: Question text
            category: Question category
            priority: Priority
            **metadata: Additional metadata

        Returns:
            Created competency question
        """
        if spec_name not in self.specs:
            raise ValidationError(f"Specification not found: {spec_name}")

        cq = self.competency_questions_manager.add_question(
            question=question, category=category, priority=priority, **metadata
        )

        self.specs[spec_name].competency_questions.append(cq)

        return cq

    def validate_spec(self, spec_name: str) -> Dict[str, Any]:
        """
        Validate requirements specification.

        Args:
            spec_name: Specification name

        Returns:
            Validation results
        """
        if spec_name not in self.specs:
            raise ValidationError(f"Specification not found: {spec_name}")

        spec = self.specs[spec_name]
        errors = []
        warnings = []

        # Check required fields
        if not spec.purpose:
            errors.append("Specification missing purpose")
        if not spec.scope:
            errors.append("Specification missing scope")
        if not spec.competency_questions:
            warnings.append("Specification has no competency questions")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def trace_requirements(
        self, spec_name: str, ontology: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trace requirements to ontology elements.

        Args:
            spec_name: Specification name
            ontology: Ontology dictionary

        Returns:
            Traceability mapping
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="RequirementsSpecManager",
            message=f"Tracing requirements for specification: {spec_name}",
        )

        try:
            if spec_name not in self.specs:
                raise ValidationError(f"Specification not found: {spec_name}")

            spec = self.specs[spec_name]

            # Validate ontology against competency questions
            self.progress_tracker.update_tracking(
                tracking_id,
                message="Validating ontology against competency questions...",
            )
            validation = self.competency_questions_manager.validate_ontology(ontology)

            # Trace each question
            self.progress_tracker.update_tracking(
                tracking_id,
                message=f"Tracing {len(spec.competency_questions)} competency questions...",
            )
            traces = {}
            for question in spec.competency_questions:
                elements = self.competency_questions_manager.trace_to_elements(
                    question, ontology
                )
                traces[question.question] = {
                    "elements": elements,
                    "answerable": question.answerable,
                }

            coverage = (
                validation["answerable"] / validation["total_questions"]
                if validation["total_questions"] > 0
                else 0.0
            )
            result = {
                "specification": spec_name,
                "validation": validation,
                "traces": traces,
                "coverage": coverage,
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Traced requirements: coverage={coverage:.2f}",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_spec(self, spec_name: str) -> Optional[RequirementsSpec]:
        """Get requirements specification by name."""
        return self.specs.get(spec_name)

    def list_specs(self) -> List[str]:
        """List all specification names."""
        return list(self.specs.keys())
