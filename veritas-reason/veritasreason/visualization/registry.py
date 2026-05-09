"""
Method Registry Module for Visualization

This module provides a method registry system for registering custom visualization methods,
enabling extensibility and community contributions to the visualization toolkit.

Supported Registration Types:
    - Method Registry: Register custom visualization methods for:
        * "kg": Knowledge graph visualization methods
        * "ontology": Ontology visualization methods
        * "embedding": Embedding visualization methods
        * "semantic_network": Semantic network visualization methods
        * "quality": Quality visualization methods
        * "analytics": Analytics visualization methods
        * "temporal": Temporal visualization methods

Algorithms Used:
    - Registry Pattern: Dictionary-based registration and lookup
    - Dynamic Registration: Runtime function registration
    - Type Checking: Type validation for registered components
    - Lookup Algorithms: Hash-based O(1) lookup for methods
    - Task-based Organization: Hierarchical organization by task type

Key Features:
    - Method registry for custom visualization methods
    - Task-based method organization (kg, ontology, embedding, semantic_network, quality, analytics, temporal)
    - Dynamic registration and unregistration
    - Easy discovery of available methods
    - Support for community-contributed extensions

Main Classes:
    - MethodRegistry: Registry for custom visualization methods

Global Instances:
    - method_registry: Global method registry instance

Example Usage:
    >>> from veritasreason.visualization.registry import method_registry
    >>> method_registry.register("kg", "custom_method", custom_kg_visualization_function)
    >>> available = method_registry.list_all("kg")
"""

from typing import Any, Callable, Dict, List, Optional


class MethodRegistry:
    """Registry for custom visualization methods."""

    def __init__(self):
        """Initialize method registry."""
        self._registry: Dict[str, Dict[str, Callable]] = {
            "kg": {},
            "ontology": {},
            "embedding": {},
            "semantic_network": {},
            "quality": {},
            "analytics": {},
            "temporal": {},
        }

    def register(
        self, task: str, method_name: str, method_func: Callable, **metadata
    ) -> None:
        """
        Register a method for a specific task.

        Args:
            task: Task type (kg, ontology, embedding, semantic_network, quality, analytics, temporal)
            method_name: Name of the method
            method_func: Method function to register
            **metadata: Additional metadata for the method
        """
        if task not in self._registry:
            raise ValueError(f"Unknown task type: {task}")

        if not callable(method_func):
            raise ValueError("method_func must be callable")

        self._registry[task][method_name] = method_func

    def unregister(self, task: str, method_name: str) -> None:
        """
        Unregister a method.

        Args:
            task: Task type
            method_name: Name of the method to unregister
        """
        if task not in self._registry:
            raise ValueError(f"Unknown task type: {task}")

        if method_name in self._registry[task]:
            del self._registry[task][method_name]

    def get(self, task: str, method_name: str) -> Optional[Callable]:
        """
        Get a method by task and name.

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
            if task not in self._registry:
                return {}
            return {task: list(self._registry[task].keys())}

        return {
            task_name: list(methods.keys())
            for task_name, methods in self._registry.items()
        }

    def has_method(self, task: str, method_name: str) -> bool:
        """
        Check if a method is registered.

        Args:
            task: Task type
            method_name: Name of the method

        Returns:
            True if method is registered, False otherwise
        """
        if task not in self._registry:
            return False

        return method_name in self._registry[task]

    def clear(self, task: Optional[str] = None) -> None:
        """
        Clear all registered methods for a task or all tasks.

        Args:
            task: Optional task type to clear. If None, clears all tasks.
        """
        if task:
            if task in self._registry:
                self._registry[task].clear()
        else:
            for task_name in self._registry:
                self._registry[task_name].clear()


# Global registry instance
method_registry = MethodRegistry()
