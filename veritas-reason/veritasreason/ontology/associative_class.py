"""
Associative Class Builder Module

This module provides support for creating associative classes (like Position) that connect
multiple classes together when simple relations are insufficient. This is useful for
modeling complex relationships like Person-Role-Organization, where the relationship
itself has properties and temporal characteristics.

Key Features:
    - Create associative classes connecting multiple entities
    - Model complex multi-entity relationships
    - Support temporal associations (time-based connections)
    - Enable position/role modeling
    - Handle association cardinality
    - Support association property management
    - Validate associative class definitions

Main Classes:
    - AssociativeClassBuilder: Builder for creating associative classes
    - AssociativeClass: Dataclass representing an associative class

Example Usage:
    >>> from veritasreason.ontology import AssociativeClassBuilder
    >>> builder = AssociativeClassBuilder()
    >>> position = builder.create_position_class("Person", "Organization", "Role")
    >>> membership = builder.create_temporal_association("Membership", ["Person", "Organization"])
    >>> result = builder.validate_associative_class(position)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class AssociativeClass:
    """
    Associative class definition.

    Associative classes are used to model relationships that have their own properties
    and characteristics, beyond simple binary relationships.

    Attributes:
        name: Name of the associative class
        connects: List of class names this associative class connects
        properties: Dictionary of properties for the association
        temporal: Whether this is a temporal association (time-based)
        metadata: Additional metadata for the associative class

    Example:
        ```python
        assoc = AssociativeClass(
            name="Position",
            connects=["Person", "Organization", "Role"],
            properties={"startDate": "xsd:date", "endDate": "xsd:date"},
            temporal=True
        )
        ```
    """

    name: str
    connects: List[str]  # List of class names this connects
    properties: Dict[str, Any] = field(default_factory=dict)
    temporal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssociativeClassBuilder:
    """
    Associative class builder for complex relationships.

    This class provides functionality to create and manage associative classes that
    connect multiple entities when simple binary relationships are insufficient.

    Features:
        - Create associative classes connecting multiple entities
        - Model complex multi-entity relationships
        - Support temporal associations (time-based connections)
        - Enable position/role modeling
        - Handle association cardinality
        - Support association property management
        - Validate associative class definitions

    Example:
        ```python
        builder = AssociativeClassBuilder()

        # Create position class
        position = builder.create_position_class(
            person_class="Person",
            organization_class="Organization"
        )

        # Validate
        result = builder.validate_associative_class(position)
        ```
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize associative class builder.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options

        Example:
            ```python
            builder = AssociativeClassBuilder()
            ```
        """
        self.logger = get_logger("associative_class_builder")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.associative_classes: Dict[str, AssociativeClass] = {}

    def create_associative_class(
        self, name: str, connects: List[str], **options
    ) -> AssociativeClass:
        """
        Create an associative class.

        Creates a new associative class that connects multiple classes together.
        This is useful for modeling relationships that have their own properties
        and characteristics.

        Args:
            name: Class name (must be non-empty)
            connects: List of class names this connects (must have at least 2 classes)
            **options: Additional options:
                - temporal: Whether this is a temporal association (default: False)
                - properties: Dictionary of properties for the association (default: {})
                - metadata: Additional metadata dictionary (default: {})

        Returns:
            Created associative class instance

        Raises:
            ValidationError: If name is empty or connects has fewer than 2 classes

        Example:
            ```python
            assoc = builder.create_associative_class(
                name="Membership",
                connects=["Person", "Organization"],
                temporal=True,
                properties={"startDate": "xsd:date", "endDate": "xsd:date"}
            )
            ```
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="AssociativeClassBuilder",
            message=f"Creating associative class: {name}",
        )

        try:
            if not name:
                raise ValidationError("Associative class name is required")

            if not connects or len(connects) < 2:
                raise ValidationError(
                    "Associative class must connect at least 2 classes"
                )

            self.progress_tracker.update_tracking(
                tracking_id, message="Creating associative class definition..."
            )
            assoc_class = AssociativeClass(
                name=name,
                connects=connects,
                properties=options.get("properties", {}),
                temporal=options.get("temporal", False),
                metadata=options.get("metadata", {}),
            )

            self.associative_classes[name] = assoc_class

            self.logger.info(f"Created associative class: {name} connecting {connects}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Created associative class: {name} connecting {len(connects)} classes",
            )
            return assoc_class

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def create_position_class(
        self,
        person_class: str,
        organization_class: str,
        role_class: Optional[str] = None,
        name: str = "Position",
        **options,
    ) -> AssociativeClass:
        """
        Create a position/role associative class.

        Creates a specialized associative class for modeling positions or roles
        that connect a person to an organization (and optionally a role). This
        is a common pattern in organizational modeling.

        Args:
            person_class: Person class name
            organization_class: Organization class name
            role_class: Optional role class name
            **options: Additional options:
                - name: Name for the position class (default: "Position")
                - temporal: Whether this is temporal (default: True)
                - properties: Additional properties dictionary
                - metadata: Additional metadata dictionary

        Returns:
            Created associative class instance

        Example:
            ```python
            position = builder.create_position_class(
                person_class="Person",
                organization_class="Organization",
                role_class="Role"
            )
            ```
        """
        connects = [person_class, organization_class]
        if role_class:
            connects.append(role_class)

        temporal = options.pop("temporal", True)
        user_props = options.pop("properties", {})

        merged_props = {
            "startDate": "xsd:date",
            "endDate": "xsd:date",
            **user_props,
        }

        return self.create_associative_class(
            name=name,
            connects=connects,
            temporal=temporal,
            properties= merged_props,
            **options,
        )

    def create_temporal_association(
        self, name: str, connects: List[str], **options
    ) -> AssociativeClass:
        """
        Create a temporal associative class.

        Creates an associative class with temporal characteristics, automatically
        adding startDate and endDate properties for time-based relationships.

        Args:
            name: Class name
            connects: List of class names this connects
            **options: Additional options:
                - properties: Additional properties dictionary (startDate and endDate are added automatically)
                - metadata: Additional metadata dictionary

        Returns:
            Created associative class instance with temporal properties

        Example:
            ```python
            membership = builder.create_temporal_association(
                name="Membership",
                connects=["Person", "Organization"]
            )
            ```
        """

        user_props = options.pop("properties", {})
        merged_props = {
            "startDate": "xsd:dateTime",
            "endDate": "xsd:dateTime",
            **user_props,
        }
        return self.create_associative_class(
            name=name,
            connects=connects,
            temporal=True,
            properties=merged_props,
            **options,
        )

    def get_associative_class(self, name: str) -> Optional[AssociativeClass]:
        """
        Get associative class by name.

        Retrieves an associative class that was previously created.

        Args:
            name: Class name to retrieve

        Returns:
            Associative class instance if found, None otherwise

        Example:
            ```python
            assoc = builder.get_associative_class("Position")
            if assoc:
                print(f"Found: {assoc.name}")
            ```
        """
        return self.associative_classes.get(name)

    def list_associative_classes(self) -> List[AssociativeClass]:
        """
        List all associative classes.

        Returns a list of all associative classes that have been created.

        Returns:
            List of associative class instances

        Example:
            ```python
            all_classes = builder.list_associative_classes()
            for assoc in all_classes:
                print(assoc.name)
            ```
        """
        return list(self.associative_classes.values())

    def validate_associative_class(
        self, assoc_class: AssociativeClass
    ) -> Dict[str, Any]:
        """
        Validate associative class.

        Validates an associative class definition, checking for required fields,
        proper structure, and potential issues.

        Args:
            assoc_class: Associative class instance to validate

        Returns:
            Dictionary with validation results:
                - valid: Boolean indicating if validation passed
                - errors: List of error messages
                - warnings: List of warning messages

        Example:
            ```python
            result = builder.validate_associative_class(assoc_class)
            if result["valid"]:
                print("Valid associative class")
            else:
                print(f"Errors: {result['errors']}")
            ```
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="AssociativeClassBuilder",
            message=f"Validating associative class: {assoc_class.name}",
        )

        try:
            errors = []
            warnings = []

            # Check name
            self.progress_tracker.update_tracking(
                tracking_id, message="Validating class structure..."
            )
            if not assoc_class.name:
                errors.append("Associative class must have a name")

            # Check connects
            if len(assoc_class.connects) < 2:
                errors.append("Associative class must connect at least 2 classes")

            # Check for duplicate connections
            if len(assoc_class.connects) != len(set(assoc_class.connects)):
                warnings.append("Associative class has duplicate connections")

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
