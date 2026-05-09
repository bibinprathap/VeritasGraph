"""
Core Orchestration Module

This module provides comprehensive orchestration capabilities for the VeritasReason framework,
enabling framework initialization, knowledge base construction, pipeline execution, configuration
management, lifecycle management, and plugin system integration.

Key Features:
    - Framework initialization and lifecycle management
    - Knowledge base construction from various data sources
    - Pipeline execution and resource management
    - Configuration loading, validation, and management
    - Plugin discovery, loading, and lifecycle management
    - System health monitoring and status tracking
    - Method registry for extensible orchestration methods

Algorithms Used:
    - Configuration Management: YAML/JSON parsing, environment variable resolution, validation
    - Lifecycle Management: Priority-based hook execution, state machine transitions
    - Plugin Management: Dynamic module loading, dependency resolution, version management
    - Resource Management: Dynamic allocation, cleanup, graceful shutdown
    - Health Monitoring: Component health checks, status aggregation, error tracking

Main Components:
    - VeritasReason: Main framework class for orchestration and knowledge base building
    - Config: Configuration data class with validation
    - ConfigManager: Configuration loading, validation, and management
    - LifecycleManager: System lifecycle management with hooks and health monitoring
    - PluginRegistry: Dynamic plugin discovery, loading, and management
    - MethodRegistry: Registry for custom orchestration methods
    - Orchestration Methods: Reusable functions for common orchestration tasks

Example Usage:
    >>> from veritasreason.core import VeritasReason
    >>> # Using main class
    >>> framework = VeritasReason()
    >>> framework.initialize()
    >>> result = framework.build_knowledge_base(sources=["doc1.pdf"])
    >>> 
    >>> # Using methods directly
    >>> from veritasreason.core.methods import build_knowledge_base
    >>> result = build_knowledge_base(sources=["doc.pdf"], method="default")

Author: VeritasReason Contributors
License: MIT
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config_manager import Config, ConfigManager
from .lifecycle import HealthStatus, LifecycleManager, SystemState
from .methods import (
    build_knowledge_base,
    get_orchestration_method,
    get_status,
    initialize_framework,
    list_available_methods,
    run_pipeline,
)
from .orchestrator import VeritasReason
from .plugin_registry import LoadedPlugin, PluginInfo, PluginRegistry
from .registry import MethodRegistry, method_registry

__all__ = [
    # Main orchestrator
    "VeritasReason",
    # Configuration
    "Config",
    "ConfigManager",
    # Lifecycle
    "LifecycleManager",
    "SystemState",
    "HealthStatus",
    # Plugins
    "PluginRegistry",
    "PluginInfo",
    "LoadedPlugin",
    # Registry
    "MethodRegistry",
    "method_registry",
    # Methods
    "build_knowledge_base",
    "run_pipeline",
    "initialize_framework",
    "get_status",
    "get_orchestration_method",
    "list_available_methods",
]

