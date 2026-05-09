"""
Namespace Manager Module

This module provides namespace isolation and management for vector store operations
in the VeritasReason framework, supporting multi-tenant architectures, access control,
and namespace-based vector organization.

Key Features:
    - Namespace creation and management
    - Vector-to-namespace mapping
    - Access control and permissions
    - Namespace metadata and configuration
    - Multi-tenant support
    - Namespace statistics and monitoring
    - Default namespace handling

Main Classes:
    - NamespaceManager: Main namespace manager coordinator
    - Namespace: Namespace container with vector tracking and access control

Example Usage:
    >>> from veritasreason.vector_store import NamespaceManager
    >>> manager = NamespaceManager()
    >>> namespace = manager.create_namespace("user1", description="User 1 vectors")
    >>> manager.add_vector_to_namespace("vec1", "user1")
    >>> vectors = manager.get_namespace_vectors("user1")
    >>> 
    >>> from veritasreason.vector_store import Namespace
    >>> ns = Namespace("docs", description="Document vectors")
    >>> ns.add_vector("vec1")
    >>> ns.set_access_control("user1", ["read", "write"])
    >>> has_access = ns.has_permission("user1", "read")

Author: VeritasReason Contributors
License: MIT
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class Namespace:
    """Namespace container."""

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **config,
    ):
        """Initialize namespace."""
        self.name = name
        self.description = description
        self.metadata = metadata or {}
        self.config = config
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.vector_ids: Set[str] = set()
        self.access_control: Dict[str, List[str]] = {}  # user/role -> permissions

    def add_vector(self, vector_id: str):
        """Add vector to namespace."""
        self.vector_ids.add(vector_id)
        self.updated_at = datetime.now()

    def remove_vector(self, vector_id: str):
        """Remove vector from namespace."""
        self.vector_ids.discard(vector_id)
        self.updated_at = datetime.now()

    def has_vector(self, vector_id: str) -> bool:
        """Check if namespace contains vector."""
        return vector_id in self.vector_ids

    def get_vector_count(self) -> int:
        """Get number of vectors in namespace."""
        return len(self.vector_ids)

    def update_metadata(self, metadata: Dict[str, Any]):
        """Update namespace metadata."""
        self.metadata.update(metadata)
        self.updated_at = datetime.now()

    def set_access_control(self, entity: str, permissions: List[str]):
        """Set access control for entity."""
        self.access_control[entity] = permissions
        self.updated_at = datetime.now()

    def has_permission(self, entity: str, permission: str) -> bool:
        """Check if entity has permission."""
        if entity in self.access_control:
            return permission in self.access_control[entity]
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert namespace to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "vector_count": len(self.vector_ids),
            "access_control": self.access_control,
        }


class NamespaceManager:
    """
    Namespace manager for vector store operations.

    • Namespace creation and management
    • Isolation and access control
    • Namespace metadata and configuration
    • Performance optimization
    • Error handling and recovery
    • Multi-tenant support
    """

    def __init__(self, **config):
        """Initialize namespace manager."""
        self.logger = get_logger("namespace_manager")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True
        self.namespaces: Dict[str, Namespace] = {}
        self.default_namespace = config.get("default_namespace", "default")
        self.vector_namespace_map: Dict[str, str] = {}  # vector_id -> namespace

    def create_namespace(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **options,
    ) -> Namespace:
        """
        Create a new namespace.

        Args:
            name: Namespace name
            description: Namespace description
            metadata: Namespace metadata
            **options: Additional options

        Returns:
            Namespace instance
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message=f"Creating namespace: {name}",
        )

        try:
            if name in self.namespaces:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="failed",
                    message=f"Namespace '{name}' already exists",
                )
                raise ValidationError(f"Namespace '{name}' already exists")

            if not self._validate_namespace_name(name):
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="failed",
                    message=f"Invalid namespace name: {name}",
                )
                raise ValidationError(f"Invalid namespace name: {name}")

            self.progress_tracker.update_tracking(
                tracking_id, message="Initializing namespace..."
            )
            namespace = Namespace(name, description, metadata, **options)
            self.namespaces[name] = namespace

            self.logger.info(f"Created namespace: {name}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Namespace '{name}' created successfully",
            )
            return namespace
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_namespace(self, name: str) -> Optional[Namespace]:
        """
        Get namespace by name.

        Args:
            name: Namespace name

        Returns:
            Namespace instance or None
        """
        return self.namespaces.get(name)

    def delete_namespace(self, name: str, **options) -> bool:
        """
        Delete namespace.

        Args:
            name: Namespace name
            **options: Delete options

        Returns:
            True if successful
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message=f"Deleting namespace: {name}",
        )

        try:
            if name not in self.namespaces:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="failed",
                    message=f"Namespace '{name}' does not exist",
                )
                raise ProcessingError(f"Namespace '{name}' does not exist")

            if name == self.default_namespace:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="failed",
                    message="Cannot delete default namespace",
                )
                raise ProcessingError("Cannot delete default namespace")

            # Remove namespace vectors from mapping
            self.progress_tracker.update_tracking(
                tracking_id, message="Removing vectors from namespace mapping..."
            )
            namespace = self.namespaces[name]
            for vector_id in list(namespace.vector_ids):
                self.vector_namespace_map.pop(vector_id, None)

            del self.namespaces[name]
            self.logger.info(f"Deleted namespace: {name}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Namespace '{name}' deleted successfully",
            )
            return True
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def list_namespaces(self, **options) -> List[str]:
        """
        List all namespace names.

        Args:
            **options: List options

        Returns:
            List of namespace names
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message="Listing all namespaces",
        )

        try:
            namespaces = list(self.namespaces.keys())
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Found {len(namespaces)} namespaces",
            )
            return namespaces
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def add_vector_to_namespace(
        self, vector_id: str, namespace: str, **options
    ) -> bool:
        """
        Add vector to namespace.

        Args:
            vector_id: Vector ID
            namespace: Namespace name
            **options: Additional options

        Returns:
            True if successful
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message=f"Adding vector {vector_id} to namespace {namespace}",
        )

        try:
            if namespace not in self.namespaces:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="failed",
                    message=f"Namespace '{namespace}' does not exist",
                )
                raise ProcessingError(f"Namespace '{namespace}' does not exist")

            # Remove from old namespace if exists
            old_namespace = self.vector_namespace_map.get(vector_id)
            if old_namespace and old_namespace in self.namespaces:
                self.progress_tracker.update_tracking(
                    tracking_id, message=f"Removing from old namespace: {old_namespace}"
                )
                self.namespaces[old_namespace].remove_vector(vector_id)

            # Add to new namespace
            self.progress_tracker.update_tracking(
                tracking_id, message=f"Adding to namespace: {namespace}"
            )
            self.namespaces[namespace].add_vector(vector_id)
            self.vector_namespace_map[vector_id] = namespace

            self.logger.debug(f"Added vector {vector_id} to namespace {namespace}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Vector {vector_id} added to namespace {namespace}",
            )
            return True
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def remove_vector_from_namespace(
        self, vector_id: str, namespace: Optional[str] = None, **options
    ) -> bool:
        """
        Remove vector from namespace.

        Args:
            vector_id: Vector ID
            namespace: Namespace name (if None, uses vector's current namespace)
            **options: Additional options

        Returns:
            True if successful
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message=f"Removing vector {vector_id} from namespace",
        )

        try:
            if namespace is None:
                namespace = self.vector_namespace_map.get(vector_id)

            if namespace and namespace in self.namespaces:
                self.progress_tracker.update_tracking(
                    tracking_id, message=f"Removing from namespace: {namespace}"
                )
                self.namespaces[namespace].remove_vector(vector_id)
                self.vector_namespace_map.pop(vector_id, None)
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Vector {vector_id} removed from namespace {namespace}",
                )
                return True

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Vector {vector_id} not found in any namespace",
            )
            return False
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_vector_namespace(self, vector_id: str) -> Optional[str]:
        """
        Get namespace for a vector.

        Args:
            vector_id: Vector ID

        Returns:
            Namespace name or None
        """
        return self.vector_namespace_map.get(vector_id)

    def get_namespace_vectors(self, namespace: str) -> List[str]:
        """
        Get all vectors in a namespace.

        Args:
            namespace: Namespace name

        Returns:
            List of vector IDs
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message=f"Getting vectors from namespace: {namespace}",
        )

        try:
            if namespace not in self.namespaces:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Namespace '{namespace}' not found",
                )
                return []

            vectors = list(self.namespaces[namespace].vector_ids)
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Found {len(vectors)} vectors in namespace {namespace}",
            )
            return vectors
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def set_namespace_access_control(
        self, namespace: str, entity: str, permissions: List[str], **options
    ) -> bool:
        """
        Set access control for namespace.

        Args:
            namespace: Namespace name
            entity: Entity (user/role) name
            permissions: List of permissions
            **options: Additional options

        Returns:
            True if successful
        """
        if namespace not in self.namespaces:
            raise ProcessingError(f"Namespace '{namespace}' does not exist")

        self.namespaces[namespace].set_access_control(entity, permissions)
        return True

    def check_namespace_access(
        self, namespace: str, entity: str, permission: str
    ) -> bool:
        """
        Check if entity has access to namespace.

        Args:
            namespace: Namespace name
            entity: Entity name
            permission: Permission to check

        Returns:
            True if entity has permission
        """
        if namespace not in self.namespaces:
            return False

        return self.namespaces[namespace].has_permission(entity, permission)

    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """
        Get namespace statistics.

        Args:
            namespace: Namespace name

        Returns:
            Namespace statistics
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="NamespaceManager",
            message=f"Getting statistics for namespace: {namespace}",
        )

        try:
            if namespace not in self.namespaces:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="failed",
                    message=f"Namespace '{namespace}' does not exist",
                )
                raise ProcessingError(f"Namespace '{namespace}' does not exist")

            self.progress_tracker.update_tracking(
                tracking_id, message="Collecting namespace statistics..."
            )
            ns = self.namespaces[namespace]
            stats = {
                "name": ns.name,
                "description": ns.description,
                "vector_count": ns.get_vector_count(),
                "created_at": ns.created_at.isoformat(),
                "updated_at": ns.updated_at.isoformat(),
                "metadata": ns.metadata,
            }
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Statistics collected for namespace {namespace}",
            )
            return stats
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all namespaces."""
        return {name: self.get_namespace_stats(name) for name in self.namespaces.keys()}

    def _validate_namespace_name(self, name: str) -> bool:
        """Validate namespace name."""
        if not name or not isinstance(name, str):
            return False

        # Basic validation: alphanumeric, underscore, hyphen
        return all(c.isalnum() or c in ["_", "-"] for c in name)

    def ensure_namespace(self, name: str, **options) -> Namespace:
        """
        Ensure namespace exists, create if not.

        Args:
            name: Namespace name
            **options: Creation options

        Returns:
            Namespace instance
        """
        if name not in self.namespaces:
            return self.create_namespace(name, **options)
        return self.namespaces[name]
