"""
Naming Conventions Manager Module

This module enforces and validates naming conventions for ontology elements
following semantic modeling best practices. It provides validation, suggestions,
and normalization for class names, property names, and ontology names.

Key Features:
    - Class naming: singular, PascalCase, nouns/noun phrases
    - Attribute naming: lowercase, nouns or verbs
    - Relation naming: camelCase, verbs/verb phrases
    - Ontology naming: title case with "Ontology" suffix
    - Vocabulary naming: title case with "Vocabulary" suffix
    - Naming validation and suggestions
    - Consistency checking across ontology
    - Automatic name normalization

Main Classes:
    - NamingConventions: Manager for naming convention enforcement

Example Usage:
    >>> from veritasreason.ontology import NamingConventions
    >>> conventions = NamingConventions()
    >>> is_valid, suggestion = conventions.validate_class_name("Person")
    >>> normalized = conventions.normalize_class_name("person class")
    >>> suggested = conventions.suggest_property_name("has name", "object")

Author: VeritasReason Contributors
License: MIT
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class NamingConventions:
    """
    Naming conventions enforcement for ontologies.

    • Class naming: singular, PascalCase, nouns/noun phrases
    • Attribute naming: lowercase, nouns or verbs
    • Relation naming: camelCase, verbs/verb phrases
    • Ontology naming: title case with "Ontology" suffix
    • Vocabulary naming: title case with "Vocabulary" suffix
    • Naming validation and suggestions
    • Consistency checking across ontology
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize naming conventions manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("naming_conventions")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

    def validate_class_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate class name against conventions.

        Args:
            name: Class name to validate

        Returns:
            Tuple of (is_valid, suggestion)
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="NamingConventions",
            message=f"Validating class name: {name}",
        )

        try:
            errors = []

            # Check if PascalCase
            self.progress_tracker.update_tracking(
                tracking_id, message="Checking naming conventions..."
            )
            if not self._is_pascal_case(name):
                errors.append("Class names should be PascalCase")

            # Check if singular
            if not self._is_singular(name):
                errors.append("Class names should be singular")

            # Check if noun/noun phrase
            if not self._is_noun_phrase(name):
                errors.append("Class names should be nouns or noun phrases")

            if errors:
                suggestion = self.suggest_class_name(name)
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Validation complete: Invalid, suggested: {suggestion}",
                )
                return (False, suggestion)

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="Validation complete: Valid"
            )
            return (True, None)

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def validate_property_name(
        self, name: str, property_type: str = "object"
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate property name against conventions.

        Args:
            name: Property name to validate
            property_type: Property type ('object', 'data')

        Returns:
            Tuple of (is_valid, suggestion)
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="NamingConventions",
            message=f"Validating property name: {name} (type: {property_type})",
        )

        try:
            errors = []

            self.progress_tracker.update_tracking(
                tracking_id, message="Checking naming conventions..."
            )
            if property_type == "object":
                # Object properties: camelCase, verbs/verb phrases
                if not self._is_camel_case(name):
                    errors.append("Object property names should be camelCase")
                if not self._is_verb_phrase(name):
                    errors.append(
                        "Object property names should be verbs or verb phrases"
                    )
            else:
                # Data properties: lowercase or camelCase
                if not (self._is_lowercase(name) or self._is_camel_case(name)):
                    errors.append(
                        "Data property names should be lowercase or camelCase"
                    )

            if errors:
                suggestion = self.suggest_property_name(name, property_type)
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Validation complete: Invalid, suggested: {suggestion}",
                )
                return (False, suggestion)

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="Validation complete: Valid"
            )
            return (True, None)

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def validate_ontology_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate ontology name against conventions.

        Args:
            name: Ontology name to validate

        Returns:
            Tuple of (is_valid, suggestion)
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="NamingConventions",
            message=f"Validating ontology name: {name}",
        )

        try:
            errors = []

            self.progress_tracker.update_tracking(
                tracking_id, message="Checking naming conventions..."
            )
            # Check if title case
            if not self._is_title_case(name):
                errors.append("Ontology names should be Title Case")

            # Check if ends with "Ontology"
            if not name.endswith("Ontology"):
                errors.append("Ontology names should end with 'Ontology'")

            if errors:
                suggestion = self.suggest_ontology_name(name)
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Validation complete: Invalid, suggested: {suggestion}",
                )
                return (False, suggestion)

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="Validation complete: Valid"
            )
            return (True, None)

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def suggest_class_name(self, name: str) -> str:
        """
        Suggest a valid class name.

        Args:
            name: Original name

        Returns:
            Suggested class name
        """
        # Convert to PascalCase
        suggested = self._to_pascal_case(name)

        # Ensure singular
        suggested = self._to_singular(suggested)

        return suggested

    def suggest_property_name(self, name: str, property_type: str = "object") -> str:
        """
        Suggest a valid property name.

        Args:
            name: Original name
            property_type: Property type

        Returns:
            Suggested property name
        """
        if property_type == "object":
            # camelCase for object properties
            suggested = self._to_camel_case(name)
        else:
            # camelCase for data properties as well (standard practice)
            suggested = self._to_camel_case(name)

        return suggested

    def suggest_ontology_name(self, name: str) -> str:
        """
        Suggest a valid ontology name.

        Args:
            name: Original name

        Returns:
            Suggested ontology name
        """
        # Remove "Ontology" suffix if present
        if name.endswith("Ontology"):
            name = name[:-8]

        # Convert to Title Case
        suggested = self._to_title_case(name)

        # Add "Ontology" suffix
        if not suggested.endswith("Ontology"):
            suggested += "Ontology"

        return suggested

    def normalize_class_name(self, name: str) -> str:
        """
        Normalize class name to conventions.

        Args:
            name: Class name

        Returns:
            Normalized class name
        """
        return self.suggest_class_name(name)

    def normalize_property_name(self, name: str, property_type: str = "object") -> str:
        """
        Normalize property name to conventions.

        Args:
            name: Property name
            property_type: Property type

        Returns:
            Normalized property name
        """
        return self.suggest_property_name(name, property_type)

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is PascalCase."""
        if not name:
            return False
        return name[0].isupper() and name.replace("_", "").replace("-", "").isalnum()

    def _is_camel_case(self, name: str) -> bool:
        """Check if name is camelCase."""
        if not name:
            return False
        return name[0].islower() and name.replace("_", "").replace("-", "").isalnum()

    def _is_lowercase(self, name: str) -> bool:
        """Check if name is lowercase."""
        return name.islower()

    def _is_title_case(self, name: str) -> bool:
        """Check if name is Title Case."""
        words = name.split()
        return all(word[0].isupper() for word in words if word)

    def _is_singular(self, name: str) -> bool:
        """Check if name is singular (basic check)."""
        # Basic plural detection
        plural_endings = ["s", "es", "ies"]
        return not any(
            name.lower().endswith(ending) for ending in plural_endings
        ) or name.lower() in ["class", "process"]

    def _is_noun_phrase(self, name: str) -> bool:
        """Check if name is a noun phrase (basic heuristic)."""
        # Basic heuristic: PascalCase words are typically nouns
        return bool(name and name[0].isupper() and re.match(r"^[A-Za-z0-9]+$", name))

    def _is_verb_phrase(self, name: str) -> bool:
        """Check if name is a verb phrase (basic heuristic)."""
        # Basic heuristic: camelCase starting with verb-like words
        verb_prefixes = ["has", "is", "can", "does", "performs", "contains", "relates"]
        return any(name.lower().startswith(prefix) for prefix in verb_prefixes)

    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        words = re.findall(r"[a-zA-Z0-9]+", name)
        if not words:
            return "Entity"
        return "".join(word.capitalize() for word in words)

    def _to_camel_case(self, name: str) -> str:
        """Convert to camelCase."""
        # Check if already likely camelCase (starts with lower, has upper, single word)
        if name and name[0].islower() and any(c.isupper() for c in name) and ' ' not in name and '_' not in name:
            return name

        words = re.findall(r"[a-zA-Z0-9]+", name)
        if not words:
            return "hasProperty"
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])

    def _to_title_case(self, name: str) -> str:
        """Convert to Title Case."""
        words = re.findall(r"[a-zA-Z0-9]+", name)
        if not words:
            return "Ontology"
        return " ".join(word.capitalize() for word in words)

    def _to_singular(self, name: str) -> str:
        """Convert to singular form (basic)."""
        # Basic singularization rules
        if name.lower().endswith("ies"):
            return name[:-3] + "y"
        elif name.lower().endswith("es") and not name.lower().endswith("ss"):
            return name[:-2]
        elif name.lower().endswith("s") and len(name) > 1 and not name.lower().endswith("ss") and name.lower() not in ["class", "process", "analysis"]:
            return name[:-1]
        return name
