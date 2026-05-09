"""
Metadata Store Module

This module provides metadata indexing and management for vector store operations
in the VeritasReason framework, supporting fast metadata queries, schema validation,
and efficient filtering for hybrid search operations.

Key Features:
    - Fast metadata indexing and lookup
    - Schema validation and enforcement
    - Field-based querying with AND/OR operators
    - Metadata import/export (JSON, dict)
    - Field value enumeration
    - Statistics and monitoring
    - Multi-format metadata support

Main Classes:
    - MetadataStore: Main metadata store coordinator
    - MetadataIndex: Fast metadata indexing and querying
    - MetadataSchema: Schema validation and management

Example Usage:
    >>> from veritasreason.vector_store import MetadataStore
    >>> store = MetadataStore(schema={"category": {"type": str, "required": True}})
    >>> store.store_metadata("vec1", {"category": "science", "year": 2023})
    >>> metadata = store.get_metadata("vec1")
    >>> vector_ids = store.query_metadata({"category": "science"}, operator="AND")
    >>> 
    >>> from veritasreason.vector_store import MetadataIndex
    >>> index = MetadataIndex()
    >>> index.index_metadata("vec1", {"category": "science"})
    >>> matching_ids = index.query({"category": "science"})

Author: VeritasReason Contributors
License: MIT
"""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class MetadataIndex:
    """Metadata index for fast lookups."""

    def __init__(self):
        """Initialize metadata index."""
        self.field_indexes: Dict[str, Dict[Any, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.vector_metadata: Dict[str, Dict[str, Any]] = {}

    def index_metadata(self, vector_id: str, metadata: Dict[str, Any]):
        """Index metadata for a vector."""
        self.vector_metadata[vector_id] = metadata

        for field, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                self.field_indexes[field][value].add(vector_id)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (str, int, float, bool)):
                        self.field_indexes[field][item].add(vector_id)

    def remove_metadata(self, vector_id: str):
        """Remove metadata from index."""
        if vector_id not in self.vector_metadata:
            return

        metadata = self.vector_metadata[vector_id]

        for field, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                if vector_id in self.field_indexes[field].get(value, set()):
                    self.field_indexes[field][value].remove(vector_id)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (str, int, float, bool)):
                        if vector_id in self.field_indexes[field].get(item, set()):
                            self.field_indexes[field][item].remove(vector_id)

        del self.vector_metadata[vector_id]

    def query(self, conditions: Dict[str, Any], operator: str = "AND") -> Set[str]:
        """
        Query vectors by metadata conditions.

        Args:
            conditions: Field-value conditions
            operator: "AND" or "OR"

        Returns:
            Set of vector IDs matching conditions
        """
        if not conditions:
            return set(self.vector_metadata.keys())

        result_sets = []

        for field, value in conditions.items():
            if field in self.field_indexes:
                if value in self.field_indexes[field]:
                    result_sets.append(self.field_indexes[field][value])
                else:
                    result_sets.append(set())
            else:
                result_sets.append(set())

        if operator == "AND":
            result = set.intersection(*result_sets) if result_sets else set()
        else:  # OR
            result = set.union(*result_sets) if result_sets else set()

        return result


class MetadataSchema:
    """Metadata schema validator."""

    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """Initialize metadata schema."""
        self.schema = schema or {}
        self.logger = get_logger("metadata_schema")

    def validate(self, metadata: Dict[str, Any]) -> bool:
        """
        Validate metadata against schema.

        Args:
            metadata: Metadata to validate

        Returns:
            True if valid
        """
        if not self.schema:
            return True

        for field, field_schema in self.schema.items():
            if field_schema.get("required", False):
                if field not in metadata:
                    raise ValidationError(f"Required field '{field}' is missing")

            if field in metadata:
                value = metadata[field]
                field_type = field_schema.get("type")

                if field_type and not isinstance(value, field_type):
                    raise ValidationError(
                        f"Field '{field}' must be of type {field_type}, got {type(value)}"
                    )

        return True

    def add_field(
        self, field: str, field_type: type, required: bool = False, default: Any = None
    ):
        """Add field to schema."""
        self.schema[field] = {
            "type": field_type,
            "required": required,
            "default": default,
        }


class MetadataStore:
    """
    Metadata store for vector store operations.

    • Metadata indexing and storage
    • Metadata querying and filtering
    • Schema management and validation
    • Performance optimization
    • Error handling and recovery
    • Multi-format metadata support
    """

    def __init__(self, schema: Optional[Dict[str, Any]] = None, **config):
        """Initialize metadata store."""
        self.logger = get_logger("metadata_store")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True
        self.schema = MetadataSchema(schema)
        self.index = MetadataIndex()
        self.metadata: Dict[str, Dict[str, Any]] = {}

    def store_metadata(
        self, vector_id: str, metadata: Dict[str, Any], **options
    ) -> bool:
        """
        Store metadata for a vector.

        Args:
            vector_id: Vector ID
            metadata: Metadata dictionary
            **options: Storage options

        Returns:
            True if successful
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="MetadataStore",
            message=f"Storing metadata for vector {vector_id}",
        )

        try:
            # Validate against schema
            self.progress_tracker.update_tracking(
                tracking_id, message="Validating metadata against schema..."
            )
            self.schema.validate(metadata)

            # Store metadata
            self.progress_tracker.update_tracking(
                tracking_id, message="Indexing metadata..."
            )
            self.metadata[vector_id] = metadata
            self.index.index_metadata(vector_id, metadata)

            self.logger.debug(f"Stored metadata for vector {vector_id}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Metadata stored for vector {vector_id}",
            )
            return True

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise ProcessingError(f"Failed to store metadata: {str(e)}")

    def get_metadata(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a vector.

        Args:
            vector_id: Vector ID

        Returns:
            Metadata dictionary or None
        """
        return self.metadata.get(vector_id)

    def update_metadata(
        self, vector_id: str, metadata_updates: Dict[str, Any], **options
    ) -> bool:
        """
        Update metadata for a vector.

        Args:
            vector_id: Vector ID
            metadata_updates: Metadata updates
            **options: Update options

        Returns:
            True if successful
        """
        if vector_id not in self.metadata:
            raise ProcessingError(f"Vector {vector_id} not found")

        try:
            # Merge updates
            updated_metadata = {**self.metadata[vector_id], **metadata_updates}

            # Validate
            self.schema.validate(updated_metadata)

            # Remove old index entries
            self.index.remove_metadata(vector_id)

            # Update
            self.metadata[vector_id] = updated_metadata
            self.index.index_metadata(vector_id, updated_metadata)

            self.logger.debug(f"Updated metadata for vector {vector_id}")
            return True

        except Exception as e:
            raise ProcessingError(f"Failed to update metadata: {str(e)}")

    def delete_metadata(self, vector_id: str, **options) -> bool:
        """
        Delete metadata for a vector.

        Args:
            vector_id: Vector ID
            **options: Delete options

        Returns:
            True if successful
        """
        if vector_id in self.metadata:
            self.index.remove_metadata(vector_id)
            del self.metadata[vector_id]
            self.logger.debug(f"Deleted metadata for vector {vector_id}")

        return True

    def query_metadata(
        self, conditions: Dict[str, Any], operator: str = "AND", **options
    ) -> List[str]:
        """
        Query vectors by metadata.

        Args:
            conditions: Field-value conditions
            operator: "AND" or "OR"
            **options: Query options

        Returns:
            List of vector IDs matching conditions
        """
        matching_ids = self.index.query(conditions, operator)
        return list(matching_ids)

    def filter_metadata(
        self,
        vector_ids: List[str],
        conditions: Dict[str, Any],
        operator: str = "AND",
        **options,
    ) -> List[str]:
        """
        Filter vector IDs by metadata conditions.

        Args:
            vector_ids: List of vector IDs to filter
            conditions: Field-value conditions
            operator: "AND" or "OR"
            **options: Filter options

        Returns:
            Filtered list of vector IDs
        """
        matching_ids = self.query_metadata(conditions, operator, **options)
        return [vid for vid in vector_ids if vid in matching_ids]

    def get_all_metadata(
        self, vector_ids: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all metadata.

        Args:
            vector_ids: Optional list of vector IDs to retrieve

        Returns:
            Dictionary mapping vector IDs to metadata
        """
        if vector_ids:
            return {vid: self.metadata.get(vid, {}) for vid in vector_ids}
        else:
            return self.metadata.copy()

    def get_field_values(self, field: str) -> List[Any]:
        """
        Get all unique values for a field.

        Args:
            field: Field name

        Returns:
            List of unique values
        """
        if field in self.index.field_indexes:
            return list(self.index.field_indexes[field].keys())
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get metadata store statistics."""
        return {
            "total_vectors": len(self.metadata),
            "indexed_fields": len(self.index.field_indexes),
            "field_counts": {
                field: len(values) for field, values in self.index.field_indexes.items()
            },
        }

    def export_metadata(
        self, format: str = "json", **options
    ) -> Union[str, Dict[str, Any]]:
        """
        Export metadata.

        Args:
            format: Export format ("json", "dict")
            **options: Export options

        Returns:
            Exported metadata
        """
        if format == "json":
            return json.dumps(self.metadata, indent=2, default=str)
        else:
            return self.metadata.copy()

    def import_metadata(
        self, data: Union[str, Dict[str, Any]], format: str = "json", **options
    ) -> bool:
        """
        Import metadata.

        Args:
            data: Metadata data
            format: Data format ("json", "dict")
            **options: Import options

        Returns:
            True if successful
        """
        if format == "json":
            if isinstance(data, str):
                data = json.loads(data)

        if not isinstance(data, dict):
            raise ValidationError("Metadata must be a dictionary")

        for vector_id, metadata in data.items():
            self.store_metadata(vector_id, metadata, **options)

        self.logger.info(f"Imported metadata for {len(data)} vectors")
        return True
