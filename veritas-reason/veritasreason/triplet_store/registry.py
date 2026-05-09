"""
Method Registry Module for Triplet Store

This module provides a method registry system for registering custom triplet store methods,
enabling extensibility and community contributions to the triplet store toolkit.

Supported Registration Types:
    - Method Registry: Register custom triplet store methods for:
        * "register": Store registration methods
        * "add": Triplet addition methods
        * "get": Triplet retrieval methods
        * "delete": Triplet deletion methods
        * "update": Triplet update methods
        * "query": SPARQL query execution methods
        * "optimize": Query optimization methods
        * "bulk_load": Bulk loading methods
        * "validate": Validation methods

Algorithms Used:
    - Registry Pattern: Dictionary-based registration and lookup
    - Dynamic Registration: Runtime function registration
    - Type Checking: Type validation for registered components
    - Lookup Algorithms: Hash-based O(1) lookup for methods
    - Task-based Organization: Hierarchical organization by task type

Key Features:
    - Method registry for custom triplet store methods
    - Task-based method organization (register, add, get, delete, update, query, optimize, bulk_load, validate)
    - Dynamic registration and unregistration
    - Easy discovery of available methods
    - Support for community-contributed extensions

Main Classes:
    - MethodRegistry: Registry for custom triplet store methods

Global Instances:
    - method_registry: Global method registry instance

Example Usage:
    >>> from veritasreason.triplet_store.registry import method_registry
    >>> method_registry.register("add", "custom_method", custom_add_function)
    >>> available = method_registry.list_all("add")
"""

from typing import Any, Callable, Dict, List, Optional


class MethodRegistry:
    """Registry for custom triplet store methods."""

    def __init__(self):
        """Initialize method registry."""
        self._registry: Dict[str, Dict[str, Callable]] = {
            "register": {},
            "add": {},
            "get": {},
            "delete": {},
            "update": {},
            "query": {},
            "optimize": {},
            "bulk_load": {},
            "validate": {},
        }

    def register(
        self, task: str, method_name: str, method_func: Callable, **metadata
    ) -> None:
        """
        Register a method for a specific task.

        Args:
            task: Task type (register, add, get, delete, update, query, optimize, bulk_load, validate)
            method_name: Name of the method
            method_func: Method function to register
            **metadata: Additional metadata for the method
        """
        if task not in self._registry:
            raise ValueError(f"Unknown task type: {task}")

        if not callable(method_func):
            raise ValueError("method_func must be callable")

        # Store method with metadata
        method_func._registry_metadata = metadata
        self._registry[task][method_name] = method_func

    def unregister(self, task: str, method_name: str) -> None:
        """
        Unregister a method.

        Args:
            task: Task type
            method_name: Name of the method to unregister
        """
        if task in self._registry and method_name in self._registry[task]:
            del self._registry[task][method_name]

    def get(self, task: str, method_name: str) -> Optional[Callable]:
        """
        Get a registered method.

        Args:
            task: Task type
            method_name: Name of the method

        Returns:
            Method function or None if not found
        """
        if task not in self._registry:
            return None
        return self._registry[task].get(method_name)

    def list_all(self, task: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List all registered methods.

        Args:
            task: Optional task type to filter by

        Returns:
            Dictionary mapping task types to lists of method names
        """
        if task:
            if task in self._registry:
                return {task: list(self._registry[task].keys())}
            return {}

        return {task: list(methods.keys()) for task, methods in self._registry.items()}

    def has(self, task: str, method_name: str) -> bool:
        """
        Check if a method is registered.

        Args:
            task: Task type
            method_name: Name of the method

        Returns:
            True if method is registered, False otherwise
        """
        return task in self._registry and method_name in self._registry[task]

    def get_metadata(self, task: str, method_name: str) -> Dict[str, Any]:
        """
        Get metadata for a registered method.

        Args:
            task: Task type
            method_name: Name of the method

        Returns:
            Method metadata dictionary
        """
        method = self.get(task, method_name)
        if method and hasattr(method, "_registry_metadata"):
            return method._registry_metadata.copy()
        return {}


# Global method registry instance
method_registry = MethodRegistry()
