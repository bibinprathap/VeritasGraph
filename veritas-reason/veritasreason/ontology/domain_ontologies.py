"""
Pre-built Domain Ontologies Module

This module provides pre-built domain-specific ontologies for common use cases
and domains. It includes templates for healthcare, finance, legal, research,
and cybersecurity domains, and allows registration of custom domain templates.

Key Features:
    - Healthcare domain ontology templates
    - Finance domain ontology templates
    - Legal domain ontology templates
    - Research domain ontology templates
    - Cybersecurity domain ontology templates
    - Custom domain ontology support
    - Domain template registration

Main Classes:
    - DomainOntologies: Manager for pre-built domain ontologies

Example Usage:
    >>> from veritasreason.ontology import DomainOntologies
    >>> domains = DomainOntologies()
    >>> template = domains.get_domain_template("healthcare")
    >>> ontology = domains.create_domain_ontology("healthcare", uri="https://example.org/healthcare/")
    >>> domains.register_domain_template("custom", {"classes": [...], "properties": [...]})

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .ontology_generator import OntologyGenerator


class DomainOntologies:
    """
    Pre-built domain ontologies manager.

    • Healthcare domain ontology
    • Finance domain ontology
    • Legal domain ontology
    • Research domain ontology
    • Cybersecurity domain ontology
    • Custom domain ontology support
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize domain ontologies manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("domain_ontologies")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.ontology_generator = OntologyGenerator(**self.config)
        self.domain_templates: Dict[str, Dict[str, Any]] = {}

        self._load_domain_templates()

    def _load_domain_templates(self) -> None:
        """Load domain-specific templates."""
        # Healthcare domain
        self.domain_templates["healthcare"] = {
            "classes": [
                {"name": "Patient", "comment": "A person receiving medical care"},
                {"name": "Physician", "comment": "A medical doctor"},
                {"name": "Hospital", "comment": "A medical facility"},
                {"name": "Diagnosis", "comment": "Medical diagnosis"},
                {"name": "Treatment", "comment": "Medical treatment"},
                {"name": "Medication", "comment": "Prescribed medication"},
            ],
            "properties": [
                {
                    "name": "hasDiagnosis",
                    "type": "object",
                    "domain": ["Patient"],
                    "range": ["Diagnosis"],
                },
                {
                    "name": "prescribedBy",
                    "type": "object",
                    "domain": ["Medication"],
                    "range": ["Physician"],
                },
                {
                    "name": "treatedAt",
                    "type": "object",
                    "domain": ["Patient"],
                    "range": ["Hospital"],
                },
            ],
        }

        # Finance domain
        self.domain_templates["finance"] = {
            "classes": [
                {"name": "Account", "comment": "Financial account"},
                {"name": "Transaction", "comment": "Financial transaction"},
                {"name": "Bank", "comment": "Financial institution"},
                {"name": "Customer", "comment": "Bank customer"},
            ],
            "properties": [
                {
                    "name": "hasAccount",
                    "type": "object",
                    "domain": ["Customer"],
                    "range": ["Account"],
                },
                {
                    "name": "belongsTo",
                    "type": "object",
                    "domain": ["Account"],
                    "range": ["Bank"],
                },
            ],
        }

    def get_domain_template(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get domain-specific template.

        Args:
            domain: Domain name

        Returns:
            Domain template or None
        """
        return self.domain_templates.get(domain.lower())

    def create_domain_ontology(self, domain: str, **options) -> Dict[str, Any]:
        """
        Create domain-specific ontology.

        Args:
            domain: Domain name
            **options: Additional options

        Returns:
            Generated ontology
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="DomainOntologies",
            message=f"Creating domain ontology: {domain}",
        )

        try:
            self.progress_tracker.update_tracking(
                tracking_id, message="Getting domain template..."
            )
            template = self.get_domain_template(domain)

            if not template:
                raise ValidationError(f"Domain template not found: {domain}")

            # Generate ontology from template
            self.progress_tracker.update_tracking(
                tracking_id, message="Generating ontology from template..."
            )
            ontology = {
                "name": f"{domain.capitalize()}Ontology",
                "uri": options.get("uri", f"https://veritasreason.dev/ontology/{domain}/"),
                "version": options.get("version", "1.0"),
                "classes": template["classes"],
                "properties": template["properties"],
                "metadata": {
                    "domain": domain,
                    "generated_at": __import__("datetime").datetime.now().isoformat(),
                },
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Created domain ontology: {domain} with {len(template['classes'])} classes, {len(template['properties'])} properties",
            )
            return ontology

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def register_domain_template(self, domain: str, template: Dict[str, Any]) -> None:
        """
        Register a custom domain template.

        Args:
            domain: Domain name
            template: Template dictionary with classes and properties
        """
        self.domain_templates[domain.lower()] = template
        self.logger.info(f"Registered domain template: {domain}")

    def list_domains(self) -> List[str]:
        """List available domain templates."""
        return list(self.domain_templates.keys())
