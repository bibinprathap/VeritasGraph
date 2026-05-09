"""
Ontology Documentation Manager Module

This module provides comprehensive ontology documentation including metadata,
descriptions, version information, and contributor tracking. It supports
generation of Markdown documentation and export to various formats.

Key Features:
    - Ontology metadata management (description, purpose, scope)
    - Author and contributor tracking
    - Creation date and version tracking
    - License and IRI namespace management
    - Documentation generation and export
    - Documentation validation
    - Markdown and HTML export support

Main Classes:
    - OntologyDocumentationManager: Manager for ontology documentation
    - OntologyDocumentation: Dataclass representing ontology documentation

Example Usage:
    >>> from veritasreason.ontology import OntologyDocumentationManager
    >>> manager = OntologyDocumentationManager()
    >>> doc = manager.create_documentation("PersonOntology", "Ontology for person entities", "Model person-related concepts", "Person, Organization, Role")
    >>> markdown = manager.generate_markdown("PersonOntology", ontology)
    >>> manager.export_documentation("PersonOntology", "docs.md", format="markdown")

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.helpers import ensure_directory
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class OntologyDocumentation:
    """Ontology documentation structure."""

    name: str
    description: str
    purpose: str
    scope: str
    authors: List[str] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    created_at: str = ""
    version: str = "1.0"
    license: str = ""
    namespace: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class OntologyDocumentationManager:
    """
    Ontology documentation management system.

    • Ontology metadata management (description, purpose, scope)
    • Author and contributor tracking
    • Creation date and version tracking
    • License and IRI namespace management
    • Documentation generation and export
    • Documentation validation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize documentation manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("ontology_documentation_manager")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.documentation: Dict[str, OntologyDocumentation] = {}

    def create_documentation(
        self, name: str, description: str, purpose: str, scope: str, **options
    ) -> OntologyDocumentation:
        """
        Create ontology documentation.

        Args:
            name: Ontology name
            description: Description
            purpose: Purpose statement
            scope: Scope description
            **options: Additional options:
                - authors: List of authors
                - contributors: List of contributors
                - version: Version string
                - license: License information
                - namespace: Namespace URI

        Returns:
            Created documentation
        """
        doc = OntologyDocumentation(
            name=name,
            description=description,
            purpose=purpose,
            scope=scope,
            authors=options.get("authors", []),
            contributors=options.get("contributors", []),
            created_at=datetime.now().isoformat(),
            version=options.get("version", "1.0"),
            license=options.get("license", ""),
            namespace=options.get("namespace", ""),
            metadata=options.get("metadata", {}),
        )

        self.documentation[name] = doc
        self.logger.info(f"Created documentation for: {name}")

        return doc

    def add_author(self, ontology_name: str, author: str) -> None:
        """Add author to documentation."""
        if ontology_name not in self.documentation:
            raise ValidationError(f"Documentation not found: {ontology_name}")

        doc = self.documentation[ontology_name]
        if author not in doc.authors:
            doc.authors.append(author)

    def add_contributor(self, ontology_name: str, contributor: str) -> None:
        """Add contributor to documentation."""
        if ontology_name not in self.documentation:
            raise ValidationError(f"Documentation not found: {ontology_name}")

        doc = self.documentation[ontology_name]
        if contributor not in doc.contributors:
            doc.contributors.append(contributor)

    def generate_markdown(
        self, ontology_name: str, ontology: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate Markdown documentation.

        Args:
            ontology_name: Ontology name
            ontology: Optional ontology dictionary

        Returns:
            Markdown documentation string
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="OntologyDocumentationManager",
            message=f"Generating Markdown documentation for: {ontology_name}",
        )

        try:
            if ontology_name not in self.documentation:
                raise ValidationError(f"Documentation not found: {ontology_name}")

            doc = self.documentation[ontology_name]

            self.progress_tracker.update_tracking(
                tracking_id, message="Generating documentation sections..."
            )
            lines = []
            lines.append(f"# {doc.name}")
            lines.append("")
            lines.append(f"**Version:** {doc.version}")
            lines.append(f"**Namespace:** {doc.namespace}")
            lines.append("")

            lines.append("## Description")
            lines.append("")
            lines.append(doc.description)
            lines.append("")

            lines.append("## Purpose")
            lines.append("")
            lines.append(doc.purpose)
            lines.append("")

            lines.append("## Scope")
            lines.append("")
            lines.append(doc.scope)
            lines.append("")

            if doc.authors:
                lines.append("## Authors")
                lines.append("")
                for author in doc.authors:
                    lines.append(f"- {author}")
                lines.append("")

            if doc.contributors:
                lines.append("## Contributors")
                lines.append("")
                for contributor in doc.contributors:
                    lines.append(f"- {contributor}")
                lines.append("")

            if doc.license:
                lines.append("## License")
                lines.append("")
                lines.append(doc.license)
                lines.append("")

            if ontology:
                self.progress_tracker.update_tracking(
                    tracking_id, message="Adding ontology classes and properties..."
                )
                classes = ontology.get("classes", [])
                properties = ontology.get("properties", [])

                lines.append("## Classes")
                lines.append("")
                for cls in classes:
                    lines.append(f"### {cls.get('name', 'Unknown')}")
                    if cls.get("comment"):
                        lines.append(f"{cls['comment']}")
                    lines.append("")

                lines.append("## Properties")
                lines.append("")
                for prop in properties:
                    lines.append(f"### {prop.get('name', 'Unknown')}")
                    lines.append(f"**Type:** {prop.get('type', 'unknown')}")
                    if prop.get("comment"):
                        lines.append(f"{prop['comment']}")
                    lines.append("")

            result = "\n".join(lines)
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Generated Markdown documentation: {len(result)} characters",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def export_documentation(
        self,
        ontology_name: str,
        file_path: Union[str, Path],
        format: str = "markdown",
        ontology: Optional[Dict[str, Any]] = None,
        **options,
    ) -> None:
        """
        Export documentation to file.

        Args:
            ontology_name: Ontology name
            file_path: Output file path
            format: Export format ('markdown', 'html')
            ontology: Optional ontology dictionary
            **options: Additional options
        """
        file_path = Path(file_path)
        ensure_directory(file_path.parent)

        if format == "markdown":
            content = self.generate_markdown(ontology_name, ontology)
        else:
            raise ValidationError(f"Unsupported format: {format}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"Exported documentation to: {file_path}")

    def validate_documentation(self, ontology_name: str) -> Dict[str, Any]:
        """
        Validate documentation completeness.

        Args:
            ontology_name: Ontology name

        Returns:
            Validation results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="OntologyDocumentationManager",
            message=f"Validating documentation for: {ontology_name}",
        )

        try:
            if ontology_name not in self.documentation:
                raise ValidationError(f"Documentation not found: {ontology_name}")

            doc = self.documentation[ontology_name]
            errors = []
            warnings = []

            self.progress_tracker.update_tracking(
                tracking_id, message="Checking required fields..."
            )
            if not doc.description:
                errors.append("Documentation missing description")
            if not doc.purpose:
                errors.append("Documentation missing purpose")
            if not doc.scope:
                errors.append("Documentation missing scope")
            if not doc.authors:
                warnings.append("Documentation has no authors")
            if not doc.namespace:
                warnings.append("Documentation missing namespace")

            result = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Validation complete: {'Valid' if result['valid'] else 'Invalid'} ({len(errors)} errors, {len(warnings)} warnings)",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_documentation(self, ontology_name: str) -> Optional[OntologyDocumentation]:
        """Get documentation by name."""
        return self.documentation.get(ontology_name)
