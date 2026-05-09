"""
Method Registry Module for Ontology

This module provides a method registry system for registering custom ontology methods,
enabling extensibility and community contributions to the ontology toolkit.

Supported Registration Types:
    - Method Registry: Register custom ontology methods for:
        * "generate": Ontology generation methods
        * "infer": Class/property inference methods
        * "validate": Validation methods
        * "evaluate": Evaluation methods
        * "owl": OWL/RDF generation methods
        * "requirements": Requirements specification methods
        * "reuse": Ontology reuse methods
        * "version": Version management methods
        * "namespace": Namespace management methods
        * "associative": Associative class creation methods

Algorithms Used:
    - Registry Pattern: Dictionary-based registration and lookup
    - Dynamic Registration: Runtime function registration
    - Type Checking: Type validation for registered components
    - Lookup Algorithms: Hash-based O(1) lookup for methods
    - Task-based Organization: Hierarchical organization by task type

Key Features:
    - Method registry for custom ontology methods
    - Task-based method organization (generate, infer, validate, evaluate, owl, requirements, reuse, version, namespace, associative)
    - Dynamic registration and unregistration
    - Easy discovery of available methods
    - Support for community-contributed extensions

Main Classes:
    - MethodRegistry: Registry for custom ontology methods

Global Instances:
    - method_registry: Global method registry instance

Example Usage:
    >>> from veritasreason.ontology.registry import method_registry
    >>> method_registry.register("generate", "custom_method", custom_ontology_generation_function)
    >>> available = method_registry.list_all("generate")
"""

from typing import Any, Callable, Dict, List, Optional


class MethodRegistry:
    """Registry for custom ontology methods."""

    _methods: Dict[str, Dict[str, Callable]] = {
        "generate": {},
        "infer": {},
        "validate": {},
        "evaluate": {},
        "owl": {},
        "requirements": {},
        "reuse": {},
        "version": {},
        "namespace": {},
        "associative": {},
    }

    @classmethod
    def register(cls, task: str, name: str, method_func: Callable):
        """
        Register a custom ontology method.

        Args:
            task: Task type ("generate", "infer", "validate", "evaluate", "owl", "requirements", "reuse", "version", "namespace", "associative")
            name: Method name
            method_func: Method function
        """
        if task not in cls._methods:
            cls._methods[task] = {}
        cls._methods[task][name] = method_func

    @classmethod
    def get(cls, task: str, name: str) -> Optional[Callable]:
        """
        Get method by task and name.

        Args:
            task: Task type ("generate", "infer", "validate", "evaluate", "owl", "requirements", "reuse", "version", "namespace", "associative")
            name: Method name

        Returns:
            Method function or None
        """
        return cls._methods.get(task, {}).get(name)

    @classmethod
    def list_all(cls, task: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List all registered methods.

        Args:
            task: Optional task type to filter by

        Returns:
            Dictionary mapping task types to method names
        """
        if task:
            return {task: list(cls._methods.get(task, {}).keys())}
        return {t: list(m.keys()) for t, m in cls._methods.items()}

    @classmethod
    def unregister(cls, task: str, name: str):
        """
        Unregister a method.

        Args:
            task: Task type ("generate", "infer", "validate", "evaluate", "owl", "requirements", "reuse", "version", "namespace", "associative")
            name: Method name
        """
        if task in cls._methods and name in cls._methods[task]:
            del cls._methods[task][name]

    @classmethod
    def clear(cls, task: Optional[str] = None):
        """
        Clear all registered methods for a task or all tasks.

        Args:
            task: Optional task type to clear (clears all if None)
        """
        if task:
            if task in cls._methods:
                cls._methods[task].clear()
        else:
            for task_dict in cls._methods.values():
                task_dict.clear()


# Global registry
method_registry = MethodRegistry()
