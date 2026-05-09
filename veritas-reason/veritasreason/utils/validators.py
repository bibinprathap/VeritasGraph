"""
Validation Utilities Module

This module provides common validation functions used across the VeritasReason framework
for data validation, type checking, constraint enforcement, and schema validation,
ensuring data quality and consistency throughout the framework.

Key Features:
    - Comprehensive data validation against schemas and constraints
    - Type checking for dictionary fields and values
    - Constraint validation (min/max length, value ranges, patterns)
    - Schema validation with required fields and property validation
    - Entity and relationship structure validation
    - File path and URL/email format validation
    - Configuration dictionary validation

Main Functions:
    - validate_data: Validate data against schema and constraints
    - validate_config: Validate configuration dictionary
    - validate_schema: Validate data against JSON-like schema
    - validate_types: Validate field types in dictionary
    - validate_required_fields: Validate that all required fields are present
    - validate_string_constraints: Validate string against constraints
    - validate_numeric_constraints: Validate numeric value against constraints
    - validate_list_constraints: Validate list against constraints
    - validate_entity: Validate entity structure
    - validate_relationship: Validate relationship structure
    - validate_file_path: Validate file path with existence and extension checks
    - validate_url: Validate URL format
    - validate_email: Validate email address format

Example Usage:
    >>> from veritasreason.utils import validate_data, validate_entity
    >>> is_valid, error = validate_data(
    ...     {"name": "John", "age": 30},
    ...     required_fields=["name", "age"],
    ...     field_types={"name": str, "age": int}
    ... )
    >>> 
    >>> entity = {"id": "e1", "text": "John Doe", "type": "PERSON"}
    >>> is_valid, error = validate_entity(entity)
    >>> if not is_valid:
    ...     raise ValidationError(error)
    >>> 
    >>> from veritasreason.utils import validate_url, validate_file_path
    >>> is_valid, error = validate_url("https://example.com")
    >>> is_valid, error = validate_file_path("data.json", must_exist=True)

Author: VeritasReason Contributors
License: MIT
"""

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .exceptions import ValidationError
from .types import Entity, EntityDict, Relationship, RelationshipDict


def validate_data(
    data: Any, schema: Optional[Dict[str, Any]] = None, **constraints: Any
) -> Tuple[bool, Optional[str]]:
    """
    Validate data against schema and constraints.

    Args:
        data: Data to validate
        schema: Schema dictionary defining expected structure
        **constraints: Additional validation constraints:
            - required_fields: List of required field names
            - field_types: Dictionary mapping field names to types
            - min_length: Minimum length for strings/lists
            - max_length: Maximum length for strings/lists
            - min_value: Minimum value for numbers
            - max_value: Maximum value for numbers
            - pattern: Regex pattern for string validation

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Schema validation
    if schema:
        is_valid, error = validate_schema(data, schema)
        if not is_valid:
            return False, error

    # Type validation
    if "field_types" in constraints:
        is_valid, error = validate_types(data, constraints["field_types"])
        if not is_valid:
            return False, error

    # Required fields validation
    if isinstance(data, dict) and "required_fields" in constraints:
        is_valid, error = validate_required_fields(data, constraints["required_fields"])
        if not is_valid:
            return False, error

    # String constraints
    if isinstance(data, str):
        is_valid, error = validate_string_constraints(data, constraints)
        if not is_valid:
            return False, error

    # Numeric constraints
    if isinstance(data, (int, float)):
        is_valid, error = validate_numeric_constraints(data, constraints)
        if not is_valid:
            return False, error

    # List constraints
    if isinstance(data, list):
        is_valid, error = validate_list_constraints(data, constraints)
        if not is_valid:
            return False, error

    return True, None


def validate_config(
    config: Dict[str, Any], required_keys: Optional[List[str]] = None, **options: Any
) -> Tuple[bool, Optional[str]]:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary
        required_keys: List of required configuration keys
        **options: Additional validation options:
            - allowed_keys: List of allowed keys (raises error if others present)
            - key_types: Dictionary mapping keys to expected types
            - nested_validation: Validate nested dictionaries (default: True)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Configuration must be a dictionary"

    # Check required keys
    if required_keys:
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            return (
                False,
                f"Missing required configuration keys: {', '.join(missing_keys)}",
            )

    # Check allowed keys
    if "allowed_keys" in options:
        allowed = set(options["allowed_keys"])
        provided = set(config.keys())
        invalid_keys = provided - allowed
        if invalid_keys:
            return False, f"Invalid configuration keys: {', '.join(invalid_keys)}"

    # Check key types
    if "key_types" in options:
        for key, expected_type in options["key_types"].items():
            if key in config:
                if not isinstance(config[key], expected_type):
                    return False, (
                        f"Configuration key '{key}' must be of type "
                        f"{expected_type.__name__}, got {type(config[key]).__name__}"
                    )

    # Nested validation
    if options.get("nested_validation", True):
        for key, value in config.items():
            if isinstance(value, dict):
                is_valid, error = validate_config(value, **options)
                if not is_valid:
                    return False, f"Error in nested config '{key}': {error}"

    return True, None


def validate_schema(data: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate data against JSON-like schema.

    Args:
        data: Data to validate
        schema: Schema dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Simple schema validation
    if "type" in schema:
        expected_type = schema["type"]
        if expected_type == "string" and not isinstance(data, str):
            return False, f"Expected string, got {type(data).__name__}"
        elif expected_type == "integer" and not isinstance(data, int):
            return False, f"Expected integer, got {type(data).__name__}"
        elif expected_type == "number" and not isinstance(data, (int, float)):
            return False, f"Expected number, got {type(data).__name__}"
        elif expected_type == "boolean" and not isinstance(data, bool):
            return False, f"Expected boolean, got {type(data).__name__}"
        elif expected_type == "array" and not isinstance(data, list):
            return False, f"Expected array, got {type(data).__name__}"
        elif expected_type == "object" and not isinstance(data, dict):
            return False, f"Expected object, got {type(data).__name__}"

    # Properties validation for objects
    if isinstance(data, dict) and "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            if prop_name in data:
                is_valid, error = validate_schema(data[prop_name], prop_schema)
                if not is_valid:
                    return False, f"Property '{prop_name}': {error}"

    # Required properties
    if isinstance(data, dict) and "required" in schema:
        missing = [req for req in schema["required"] if req not in data]
        if missing:
            return False, f"Missing required properties: {', '.join(missing)}"

    return True, None


def validate_types(
    data: Dict[str, Any], field_types: Dict[str, type]
) -> Tuple[bool, Optional[str]]:
    """
    Validate field types in dictionary.

    Args:
        data: Dictionary to validate
        field_types: Dictionary mapping field names to expected types

    Returns:
        Tuple of (is_valid, error_message)
    """
    for field_name, expected_type in field_types.items():
        if field_name in data:
            value = data[field_name]
            if not isinstance(value, expected_type):
                return False, (
                    f"Field '{field_name}' must be of type "
                    f"{expected_type.__name__}, got {type(value).__name__}"
                )

    return True, None


def validate_required_fields(
    data: Dict[str, Any], required_fields: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required fields are present.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, None


def validate_string_constraints(
    value: str, constraints: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Validate string against constraints.

    Args:
        value: String to validate
        constraints: Dictionary of constraints:
            - min_length: Minimum length
            - max_length: Maximum length
            - pattern: Regex pattern
            - allowed_values: List of allowed values

    Returns:
        Tuple of (is_valid, error_message)
    """
    if "min_length" in constraints:
        if len(value) < constraints["min_length"]:
            return False, (
                f"String length {len(value)} is less than minimum "
                f"{constraints['min_length']}"
            )

    if "max_length" in constraints:
        if len(value) > constraints["max_length"]:
            return False, (
                f"String length {len(value)} exceeds maximum "
                f"{constraints['max_length']}"
            )

    if "pattern" in constraints:
        pattern = constraints["pattern"]
        if not re.match(pattern, value):
            return False, f"String does not match required pattern: {pattern}"

    if "allowed_values" in constraints:
        if value not in constraints["allowed_values"]:
            return False, (
                f"Value '{value}' is not in allowed values: "
                f"{constraints['allowed_values']}"
            )

    return True, None


def validate_numeric_constraints(
    value: Union[int, float], constraints: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Validate numeric value against constraints.

    Args:
        value: Numeric value to validate
        constraints: Dictionary of constraints:
            - min_value: Minimum value
            - max_value: Maximum value
            - allowed_values: List of allowed values

    Returns:
        Tuple of (is_valid, error_message)
    """
    if "min_value" in constraints:
        if value < constraints["min_value"]:
            return False, (
                f"Value {value} is less than minimum {constraints['min_value']}"
            )

    if "max_value" in constraints:
        if value > constraints["max_value"]:
            return False, (f"Value {value} exceeds maximum {constraints['max_value']}")

    if "allowed_values" in constraints:
        if value not in constraints["allowed_values"]:
            return False, (
                f"Value {value} is not in allowed values: "
                f"{constraints['allowed_values']}"
            )

    return True, None


def validate_list_constraints(
    value: List[Any], constraints: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Validate list against constraints.

    Args:
        value: List to validate
        constraints: Dictionary of constraints:
            - min_length: Minimum length
            - max_length: Maximum length
            - item_type: Expected type for list items
            - unique: Whether items must be unique

    Returns:
        Tuple of (is_valid, error_message)
    """
    if "min_length" in constraints:
        if len(value) < constraints["min_length"]:
            return False, (
                f"List length {len(value)} is less than minimum "
                f"{constraints['min_length']}"
            )

    if "max_length" in constraints:
        if len(value) > constraints["max_length"]:
            return False, (
                f"List length {len(value)} exceeds maximum "
                f"{constraints['max_length']}"
            )

    if "item_type" in constraints:
        expected_type = constraints["item_type"]
        for i, item in enumerate(value):
            if not isinstance(item, expected_type):
                return False, (
                    f"List item at index {i} must be of type "
                    f"{expected_type.__name__}, got {type(item).__name__}"
                )

    if constraints.get("unique", False):
        if len(value) != len(set(value)):
            return False, "List items must be unique"

    return True, None


def validate_entity(entity: Union[Entity, EntityDict]) -> Tuple[bool, Optional[str]]:
    """
    Validate entity structure.

    Args:
        entity: Entity object or dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(entity, Entity):
        entity_dict = {
            "id": entity.id,
            "text": entity.text,
            "type": entity.type,
        }
    else:
        entity_dict = entity

    required_fields = ["id", "text", "type"]
    is_valid, error = validate_required_fields(entity_dict, required_fields)
    if not is_valid:
        return False, error

    # Validate confidence if present
    if "confidence" in entity_dict:
        confidence = entity_dict["confidence"]
        if not isinstance(confidence, (int, float)):
            return False, "Confidence must be a number"
        if not (0.0 <= confidence <= 1.0):
            return False, "Confidence must be between 0.0 and 1.0"

    return True, None


def validate_relationship(
    relationship: Union[Relationship, RelationshipDict]
) -> Tuple[bool, Optional[str]]:
    """
    Validate relationship structure.

    Args:
        relationship: Relationship object or dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(relationship, Relationship):
        rel_dict = {
            "id": relationship.id,
            "source_id": relationship.source_id,
            "target_id": relationship.target_id,
            "type": relationship.type,
        }
    else:
        rel_dict = relationship

    required_fields = ["id", "source_id", "target_id", "type"]
    is_valid, error = validate_required_fields(rel_dict, required_fields)
    if not is_valid:
        return False, error

    # Validate confidence if present
    if "confidence" in rel_dict:
        confidence = rel_dict["confidence"]
        if not isinstance(confidence, (int, float)):
            return False, "Confidence must be a number"
        if not (0.0 <= confidence <= 1.0):
            return False, "Confidence must be between 0.0 and 1.0"

    return True, None


def validate_file_path(
    file_path: Union[str, Path],
    must_exist: bool = False,
    allowed_extensions: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate file path.

    Args:
        file_path: Path to validate
        must_exist: Whether file must exist
        allowed_extensions: List of allowed file extensions (e.g., ['.txt', '.json'])

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)

    if must_exist and not path.exists():
        return False, f"File does not exist: {file_path}"

    if allowed_extensions:
        extension = path.suffix.lower()
        if extension not in [ext.lower() for ext in allowed_extensions]:
            return False, (
                f"File extension '{extension}' not in allowed extensions: "
                f"{allowed_extensions}"
            )

    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        return False, f"Invalid URL format: {url}"

    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.

    Args:
        email: Email string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    if not email_pattern.match(email):
        return False, f"Invalid email format: {email}"

    return True, None
