"""
Ontology Evaluator Module

This module evaluates ontologies against competency questions and refines them
to ensure they meet requirements and can answer intended questions. It provides
coverage scores, completeness metrics, gap identification, and improvement suggestions.

Key Features:
    - Validate ontology against competency questions
    - Identify gaps in ontology coverage
    - Suggest refinements and improvements
    - Evaluate class granularity and generalization
    - Check relation completeness
    - Generate evaluation reports
    - Calculate coverage and completeness scores

Main Classes:
    - OntologyEvaluator: Evaluator for ontology quality assessment
    - EvaluationResult: Dataclass representing evaluation results

Example Usage:
    >>> from veritasreason.ontology import OntologyEvaluator
    >>> evaluator = OntologyEvaluator()
    >>> result = evaluator.evaluate_ontology(ontology, competency_questions=["Who are the employees?"])
    >>> report = evaluator.generate_report(ontology)
    >>> granularity = evaluator.evaluate_class_granularity(ontology)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .competency_questions import CompetencyQuestionsManager


@dataclass
class EvaluationResult:
    """Ontology evaluation result."""

    coverage_score: float
    completeness_score: float
    gaps: List[str]
    suggestions: List[str]
    metrics: Dict[str, Any] = field(default_factory=dict)


class OntologyEvaluator:
    """
    Ontology evaluation engine.

    • Validate ontology against competency questions
    • Identify gaps in ontology coverage
    • Suggest refinements and improvements
    • Evaluate class granularity and generalization
    • Check relation completeness
    • Generate evaluation reports
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize ontology evaluator.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("ontology_evaluator")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.competency_questions_manager = CompetencyQuestionsManager(**self.config)

    def evaluate_ontology(
        self,
        ontology: Dict[str, Any],
        competency_questions: Optional[List[str]] = None,
        **options,
    ) -> EvaluationResult:
        """
        Evaluate ontology against competency questions.

        Args:
            ontology: Ontology dictionary
            competency_questions: List of competency questions (optional)
            **options: Additional options

        Returns:
            Evaluation result
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="OntologyEvaluator",
            message="Evaluating ontology against competency questions",
        )

        try:
            # Validate against competency questions
            if competency_questions:
                self.progress_tracker.update_tracking(
                    tracking_id, message="Adding competency questions..."
                )
                for question in competency_questions:
                    self.competency_questions_manager.add_question(question)

            self.progress_tracker.update_tracking(
                tracking_id, message="Validating against competency questions..."
            )
            validation = self.competency_questions_manager.validate_ontology(ontology)

            # Calculate coverage
            self.progress_tracker.update_tracking(
                tracking_id, message="Calculating coverage score..."
            )
            total_questions = validation.get("total_questions", 0)
            answerable = validation.get("answerable", 0)
            coverage_score = (
                answerable / total_questions if total_questions > 0 else 0.0
            )

            # Calculate completeness
            self.progress_tracker.update_tracking(
                tracking_id, message="Calculating completeness score..."
            )
            completeness_score = self._calculate_completeness(ontology)

            # Identify gaps
            self.progress_tracker.update_tracking(
                tracking_id, message="Identifying gaps..."
            )
            gaps = self._identify_gaps(ontology, validation)

            # Generate suggestions
            self.progress_tracker.update_tracking(
                tracking_id, message="Generating suggestions..."
            )
            suggestions = self._generate_suggestions(ontology, gaps)

            # Calculate metrics
            self.progress_tracker.update_tracking(
                tracking_id, message="Calculating evaluation metrics..."
            )
            metrics = self._calculate_evaluation_metrics(ontology, validation)

            result = EvaluationResult(
                coverage_score=coverage_score,
                completeness_score=completeness_score,
                gaps=gaps,
                suggestions=suggestions,
                metrics=metrics,
            )

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Evaluation complete: coverage={coverage_score:.2f}, completeness={completeness_score:.2f}",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _calculate_completeness(self, ontology: Dict[str, Any]) -> float:
        """Calculate ontology completeness score."""
        classes = ontology.get("classes", [])
        properties = ontology.get("properties", [])

        # Check if classes have required fields
        classes_complete = 0
        for cls in classes:
            has_name = "name" in cls
            has_uri = "uri" in cls
            has_label = "label" in cls
            if has_name and has_uri and has_label:
                classes_complete += 1

        classes_score = classes_complete / len(classes) if classes else 0.0

        # Check if properties have required fields
        props_complete = 0
        for prop in properties:
            has_name = "name" in prop
            has_type = "type" in prop
            has_uri = "uri" in prop
            if has_name and has_type and has_uri:
                props_complete += 1

        props_score = props_complete / len(properties) if properties else 0.0

        # Average completeness
        return (classes_score + props_score) / 2.0

    def _identify_gaps(
        self, ontology: Dict[str, Any], validation: Dict[str, Any]
    ) -> List[str]:
        """Identify gaps in ontology coverage."""
        gaps = []

        # Check unanswerable questions
        unanswerable = validation.get("unanswerable", 0)
        if unanswerable > 0:
            gaps.append(f"{unanswerable} competency questions cannot be answered")

        # Check for missing classes
        classes = ontology.get("classes", [])
        if len(classes) == 0:
            gaps.append("Ontology has no classes")

        # Check for missing properties
        properties = ontology.get("properties", [])
        if len(properties) == 0:
            gaps.append("Ontology has no properties")

        # Check for classes without properties
        classes_with_props = set()
        for prop in properties:
            domains = prop.get("domain", [])
            classes_with_props.update(domains)

        for cls in classes:
            if cls["name"] not in classes_with_props:
                gaps.append(f"Class '{cls['name']}' has no associated properties")

        return gaps

    def _generate_suggestions(
        self, ontology: Dict[str, Any], gaps: List[str]
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        # Suggest based on gaps
        if any("competency questions" in gap for gap in gaps):
            suggestions.append(
                "Add missing classes or properties to answer competency questions"
            )

        if any("no classes" in gap for gap in gaps):
            suggestions.append("Infer classes from entities in your data")

        if any("no properties" in gap for gap in gaps):
            suggestions.append("Infer properties from relationships in your data")

        # Suggest based on class granularity
        classes = ontology.get("classes", [])
        if len(classes) > 50:
            suggestions.append(
                "Consider splitting ontology into modules for better organization"
            )

        # Suggest based on hierarchy
        classes_with_parents = sum(
            1 for c in classes if c.get("subClassOf") or c.get("parent")
        )
        if classes_with_parents < len(classes) * 0.3:
            suggestions.append(
                "Consider adding more hierarchical relationships between classes"
            )

        return suggestions

    def _calculate_evaluation_metrics(
        self, ontology: Dict[str, Any], validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate evaluation metrics."""
        classes = ontology.get("classes", [])
        properties = ontology.get("properties", [])

        return {
            "class_count": len(classes),
            "property_count": len(properties),
            "object_property_count": sum(
                1 for p in properties if p.get("type") == "object"
            ),
            "data_property_count": sum(
                1 for p in properties if p.get("type") == "data"
            ),
            "classes_with_hierarchy": sum(
                1 for c in classes if c.get("subClassOf") or c.get("parent")
            ),
            "competency_question_coverage": validation.get("answerable", 0)
            / validation.get("total_questions", 1)
            if validation.get("total_questions", 0) > 0
            else 0.0,
        }

    def evaluate_class_granularity(self, ontology: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate class granularity and generalization.

        Args:
            ontology: Ontology dictionary

        Returns:
            Granularity evaluation results
        """
        classes = ontology.get("classes", [])

        # Count instances per class (if available)
        instance_counts = {}
        for cls in classes:
            instance_count = cls.get("entity_count", cls.get("inferred_count", 0))
            instance_counts[cls["name"]] = instance_count

        # Suggest generalizations
        suggestions = []
        for cls_name, count in instance_counts.items():
            if count < 2:
                suggestions.append(
                    f"Class '{cls_name}' has very few instances - consider merging"
                )
            elif count > 1000:
                suggestions.append(
                    f"Class '{cls_name}' has many instances - consider splitting"
                )

        return {"instance_distribution": instance_counts, "suggestions": suggestions}

    def evaluate_relation_completeness(
        self, ontology: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check relation completeness.

        Args:
            ontology: Ontology dictionary

        Returns:
            Completeness evaluation results
        """
        classes = ontology.get("classes", [])
        properties = ontology.get("properties", [])

        # Check which classes have relations
        classes_with_relations = set()
        for prop in properties:
            domains = prop.get("domain", [])
            classes_with_relations.update(domains)

        isolated_classes = [
            cls["name"] for cls in classes if cls["name"] not in classes_with_relations
        ]

        return {
            "classes_with_relations": len(classes_with_relations),
            "isolated_classes": isolated_classes,
            "relation_coverage": len(classes_with_relations) / len(classes)
            if classes
            else 0.0,
        }

    def generate_report(self, ontology: Dict[str, Any], **options) -> Dict[str, Any]:
        """
        Generate comprehensive evaluation report.

        Args:
            ontology: Ontology dictionary
            **options: Additional options

        Returns:
            Evaluation report
        """
        evaluation = self.evaluate_ontology(ontology, **options)
        granularity = self.evaluate_class_granularity(ontology)
        completeness = self.evaluate_relation_completeness(ontology)

        return {
            "evaluation": {
                "coverage_score": evaluation.coverage_score,
                "completeness_score": evaluation.completeness_score,
                "gaps": evaluation.gaps,
                "suggestions": evaluation.suggestions,
            },
            "granularity": granularity,
            "relation_completeness": completeness,
            "metrics": evaluation.metrics,
        }
