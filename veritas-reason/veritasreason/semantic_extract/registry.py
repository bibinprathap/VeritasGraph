"""
Plugin Registry Module

This module provides a plugin registry system for registering custom LLM providers
and extraction methods, enabling extensibility and community contributions to the
semantic extraction toolkit.

Supported Registration Types:
    - Provider Registry: Register custom LLM providers
    - Method Registry: Register custom extraction methods for:
        * "entity": Entity extraction methods
        * "relation": Relation extraction methods
        * "triplet": Triplet extraction methods
        * "event": Event extraction methods
        * "coreference": Coreference resolution methods

Algorithms Used:
    - Registry Pattern: Dictionary-based registration and lookup
    - Dynamic Registration: Runtime class and function registration
    - Type Checking: Type validation for registered components
    - Lookup Algorithms: Hash-based O(1) lookup for providers and methods
    - Task-based Organization: Hierarchical organization by task type

Key Features:
    - Provider registry for custom LLM providers
    - Method registry for custom extraction methods
    - Task-based method organization (entity, relation, triplet, event, coreference)
    - Dynamic registration and unregistration
    - Easy discovery of available providers and methods
    - Support for community-contributed extensions

Main Classes:
    - ProviderRegistry: Registry for custom LLM providers
    - MethodRegistry: Registry for custom extraction methods

Global Instances:
    - provider_registry: Global provider registry instance
    - method_registry: Global method registry instance

Example Usage:
    >>> from veritasreason.semantic_extract.registry import provider_registry, method_registry
    >>> provider_registry.register("custom_provider", CustomProviderClass)
    >>> method_registry.register("entity", "custom_method", custom_extract_function)
    >>> available = method_registry.list_all("entity")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Callable, Dict, List, Optional, Type


class ProviderRegistry:
    """Registry for custom LLM providers."""

    _providers: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type):
        """Register a custom provider."""
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str) -> Optional[Type]:
        """Get provider by name."""
        return cls._providers.get(name)

    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered providers."""
        return list(cls._providers.keys())

    @classmethod
    def unregister(cls, name: str):
        """Unregister a provider."""
        if name in cls._providers:
            del cls._providers[name]


class MethodRegistry:
    """Registry for custom extraction methods."""

    _methods: Dict[str, Dict[str, Callable]] = {
        "entity": {},
        "relation": {},
        "triplet": {},
        "event": {},
        "coreference": {},
    }

    @classmethod
    def register(cls, task: str, name: str, method_func: Callable):
        """Register a custom extraction method."""
        if task not in cls._methods:
            cls._methods[task] = {}
        cls._methods[task][name] = method_func

    @classmethod
    def get(cls, task: str, name: str) -> Optional[Callable]:
        """Get method by task and name."""
        return cls._methods.get(task, {}).get(name)

    @classmethod
    def list_all(cls, task: Optional[str] = None) -> Dict[str, List[str]]:
        """List all registered methods."""
        if task:
            return {task: list(cls._methods.get(task, {}).keys())}
        return {t: list(m.keys()) for t, m in cls._methods.items()}

    @classmethod
    def unregister(cls, task: str, name: str):
        """Unregister a method."""
        if task in cls._methods and name in cls._methods[task]:
            del cls._methods[task][name]


# Global registries
provider_registry = ProviderRegistry()
method_registry = MethodRegistry()
