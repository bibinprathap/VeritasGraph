"""
Competency Questions Manager Module

This module manages competency questions that define what an ontology should answer,
serving as functional requirements that guide modeling decisions. Competency questions
help ensure that the ontology can answer the queries it was designed to support.

Key Features:
    - Define and manage competency questions
    - Validate ontology against competency questions
    - Trace questions to ontology elements
    - Refine questions based on ontology evolution
    - Generate question-answer validation reports
    - Support natural language question formulation
    - Categorize questions by domain and priority

Main Classes:
    - CompetencyQuestionsManager: Manager for competency questions
    - CompetencyQuestion: Dataclass representing a competency question

Example Usage:
    >>> from veritasreason.ontology import CompetencyQuestionsManager
    >>> manager = CompetencyQuestionsManager()
    >>> manager.add_question("Who are the employees of a given organization?", category="organizational")
    >>> results = manager.validate_ontology(ontology)
    >>> report = manager.generate_report(ontology)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class CompetencyQuestion:
    """
    Competency question definition.

    Represents a question that the ontology should be able to answer, serving as
    a functional requirement for ontology design.

    Attributes:
        question: Question text in natural language
        category: Question category (e.g., "general", "organizational", "temporal")
        priority: Priority level (1=high, 2=medium, 3=low)
        answerable: Whether the ontology can currently answer this question
        trace_to_elements: List of ontology element names relevant to this question
        metadata: Additional metadata dictionary

    Example:
        ```python
        cq = CompetencyQuestion(
            question="Who are the employees of a given organization?",
            category="organizational",
            priority=1
        )
        ```
    """

    question: str
    category: str = "general"
    priority: int = 1  # 1=high, 2=medium, 3=low
    answerable: bool = False
    trace_to_elements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompetencyQuestionsManager:
    """
    Competency questions manager for ontology requirements.

    This class manages competency questions that serve as functional requirements
    for ontology design. It validates whether an ontology can answer these questions
    and traces questions to relevant ontology elements.

    Features:
        - Define and manage competency questions
        - Validate ontology against competency questions
        - Trace questions to ontology elements
        - Refine questions based on ontology evolution
        - Generate question-answer validation reports
        - Support natural language question formulation
        - Categorize and prioritize questions

    Example:
        ```python
        manager = CompetencyQuestionsManager()
        manager.add_question("Who are the employees?", category="organizational")
        results = manager.validate_ontology(ontology)
        ```
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize competency questions manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options

        Example:
            ```python
            manager = CompetencyQuestionsManager()
            ```
        """
        self.logger = get_logger("competency_questions_manager")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.questions: List[CompetencyQuestion] = []

    def add_question(
        self, question: str, category: str = "general", priority: int = 1, **metadata
    ) -> CompetencyQuestion:
        """
        Add a competency question.

        Adds a new competency question to the manager. Competency questions define
        what the ontology should be able to answer.

        Args:
            question: Question text in natural language
            category: Question category (default: "general")
            priority: Priority level (1=high, 2=medium, 3=low, default: 1)
            **metadata: Additional metadata dictionary

        Returns:
            Created CompetencyQuestion instance

        Example:
            ```python
            cq = manager.add_question(
                "Who are the employees of a given organization?",
                category="organizational",
                priority=1
            )
            ```
        """
        cq = CompetencyQuestion(
            question=question, category=category, priority=priority, metadata=metadata
        )

        self.questions.append(cq)
        self.logger.info(f"Added competency question: {question[:50]}...")

        return cq

    def validate_ontology(self, ontology: Dict[str, Any], **options) -> Dict[str, Any]:
        """
        Validate ontology against competency questions.

        Checks whether the ontology can answer each competency question by analyzing
        the presence of relevant classes and properties. Updates the answerable
        status of each question.

        Args:
            ontology: Ontology dictionary containing classes and properties
            **options: Additional options (currently unused)

        Returns:
            Dictionary with validation results:
                - total_questions: Total number of questions
                - answerable: Number of answerable questions
                - unanswerable: Number of unanswerable questions
                - by_category: Breakdown by category
                - by_priority: Breakdown by priority

        Example:
            ```python
            results = manager.validate_ontology(ontology)
            print(f"Answerable: {results['answerable']}/{results['total_questions']}")
            ```
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="CompetencyQuestionsManager",
            message=f"Validating ontology against {len(self.questions)} competency questions",
        )

        try:
            results = {
                "total_questions": len(self.questions),
                "answerable": 0,
                "unanswerable": 0,
                "by_category": {},
                "by_priority": {},
            }

            self.progress_tracker.update_tracking(
                tracking_id, message="Checking if ontology can answer questions..."
            )
            for question in self.questions:
                # Basic check if ontology can answer the question
                answerable = self._can_ontology_answer(ontology, question)
                question.answerable = answerable

                if answerable:
                    results["answerable"] += 1
                else:
                    results["unanswerable"] += 1

                # Track by category
                category = question.category
                if category not in results["by_category"]:
                    results["by_category"][category] = {
                        "answerable": 0,
                        "unanswerable": 0,
                    }

                if answerable:
                    results["by_category"][category]["answerable"] += 1
                else:
                    results["by_category"][category]["unanswerable"] += 1

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Validation complete: {results['answerable']}/{results['total_questions']} answerable",
            )
            return results

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _can_ontology_answer(
        self, ontology: Dict[str, Any], question: CompetencyQuestion
    ) -> bool:
        """Check if ontology can answer the question (basic heuristic)."""
        # Helper to clean text
        def clean_text(text):
            import string
            return text.translate(str.maketrans("", "", string.punctuation))

        # Extract keywords from question
        question_clean = clean_text(question.question.lower())
        
        # Check if ontology has relevant classes
        classes = ontology.get("classes", [])
        for cls in classes:
            class_name_lower = cls.get("name", "").lower()
            if any(
                word in class_name_lower
                for word in question_clean.split()
                if len(word) > 3
            ):
                return True

        # Check if ontology has relevant properties
        properties = ontology.get("properties", [])
        for prop in properties:
            prop_name_lower = prop.get("name", "").lower()
            if any(
                word in prop_name_lower
                for word in question_clean.split()
                if len(word) > 3
            ):
                return True

        return False

    def trace_to_elements(
        self, question: CompetencyQuestion, ontology: Dict[str, Any]
    ) -> List[str]:
        """
        Trace question to ontology elements.

        Identifies which ontology elements (classes and properties) are relevant
        to answering a specific competency question. Uses keyword matching to find
        relevant elements.

        Args:
            question: CompetencyQuestion instance to trace
            ontology: Ontology dictionary containing classes and properties

        Returns:
            List of relevant ontology element names (classes and properties)

        Example:
            ```python
            elements = manager.trace_to_elements(question, ontology)
            print(f"Relevant elements: {elements}")
            ```
        """
        elements = []
        import string
        question_clean = question.question.lower().translate(str.maketrans("", "", string.punctuation))
        keywords = [w for w in question_clean.split() if len(w) > 3]

        # Find relevant classes
        classes = ontology.get("classes", [])
        for cls in classes:
            class_name_lower = cls.get("name", "").lower()
            if any(keyword in class_name_lower for keyword in keywords):
                elements.append(cls["name"])

        # Find relevant properties
        properties = ontology.get("properties", [])
        for prop in properties:
            prop_name_lower = prop.get("name", "").lower()
            if any(keyword in prop_name_lower for keyword in keywords):
                elements.append(prop["name"])

        question.trace_to_elements = elements
        return elements

    def generate_report(self, ontology: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate competency question validation report.

        Generates a comprehensive report showing which questions are answerable,
        which elements trace to each question, and overall coverage statistics.

        Args:
            ontology: Ontology dictionary to validate

        Returns:
            Dictionary containing:
                - validation: Validation results dictionary
                - questions: List of question details with trace information
                - generated_at: Timestamp of report generation

        Example:
            ```python
            report = manager.generate_report(ontology)
            for q in report["questions"]:
                print(f"{q['question']}: {q['answerable']}")
            ```
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="CompetencyQuestionsManager",
            message="Generating competency question validation report",
        )

        try:
            self.progress_tracker.update_tracking(
                tracking_id, message="Validating ontology..."
            )
            validation = self.validate_ontology(ontology)

            # Trace all questions
            self.progress_tracker.update_tracking(
                tracking_id,
                message=f"Tracing {len(self.questions)} questions to ontology elements...",
            )
            for question in self.questions:
                self.trace_to_elements(question, ontology)

            result = {
                "validation": validation,
                "questions": [
                    {
                        "question": q.question,
                        "category": q.category,
                        "priority": q.priority,
                        "answerable": q.answerable,
                        "trace_to_elements": q.trace_to_elements,
                    }
                    for q in self.questions
                ],
                "generated_at": datetime.now().isoformat(),
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Generated report for {len(self.questions)} questions",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_questions_by_category(self, category: str) -> List[CompetencyQuestion]:
        """Get questions by category."""
        return [q for q in self.questions if q.category == category]

    def get_questions_by_priority(self, priority: int) -> List[CompetencyQuestion]:
        """Get questions by priority."""
        return [q for q in self.questions if q.priority == priority]
