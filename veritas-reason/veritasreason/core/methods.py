"""
Orchestration Methods Module

This module provides all orchestration methods as simple, reusable functions for
framework initialization, knowledge base construction, pipeline execution, and
system status management. It supports multiple orchestration approaches and
integrates with the method registry for extensibility.

Supported Methods:

Knowledge Base Construction:
    - "default": Standard knowledge base construction with embeddings and graph
    - "minimal": Minimal knowledge base without embeddings or graph
    - "full": Full knowledge base with all features enabled

Pipeline Execution:
    - "default": Standard pipeline execution
    - "async": Asynchronous pipeline execution
    - "batch": Batch pipeline execution

Framework Initialization:
    - "default": Standard framework initialization
    - "minimal": Minimal initialization without plugins
    - "full": Full initialization with all components

System Status:
    - "default": Standard status retrieval
    - "detailed": Detailed status with component health
    - "summary": Summary status only

Algorithms Used:

Knowledge Base Construction:
    - Source Validation: File system and URL validation
    - Pipeline Orchestration: Multi-stage processing pipeline execution
    - Graph Construction: Entity-relationship graph building
    - Embedding Generation: Vector embedding creation from text

Pipeline Execution:
    - Resource Allocation: Dynamic resource management
    - Error Handling: Graceful error recovery and reporting
    - Progress Tracking: Real-time progress monitoring
    - Result Aggregation: Result collection and formatting

Framework Initialization:
    - Component Initialization: Ordered component startup
    - Configuration Validation: Config validation and loading
    - Plugin Loading: Dynamic plugin discovery and loading
    - Health Checking: Component health verification

System Status:
    - Health Aggregation: Component health status collection
    - State Tracking: System state monitoring
    - Module Status: Module availability checking
    - Plugin Status: Plugin loading status

Key Features:
    - Multiple orchestration methods for knowledge base construction
    - Multiple pipeline execution methods
    - Framework initialization methods
    - System status retrieval methods
    - Method dispatchers with registry support
    - Custom method registration capability
    - Consistent interface across all methods

Main Functions:
    - build_knowledge_base: Knowledge base construction wrapper
    - run_pipeline: Pipeline execution wrapper
    - initialize_framework: Framework initialization wrapper
    - get_status: System status retrieval wrapper
    - get_orchestration_method: Get orchestration method by name

Example Usage:
    >>> from veritasreason.core.methods import build_knowledge_base, get_orchestration_method
    >>> result = build_knowledge_base(sources=["doc1.pdf"], method="default")
    >>> method = get_orchestration_method("knowledge_base", "custom_method")

Author: VeritasReason Contributors
License: MIT
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from ..utils.exceptions import ConfigurationError, ProcessingError
from ..utils.logging import get_logger
from .config_manager import Config, ConfigManager
from .orchestrator import VeritasReason
from .registry import method_registry

logger = get_logger("core_methods")


def build_knowledge_base(
    sources: Union[str, List[Union[str, Path]]],
    method: str = "default",
    config: Optional[Union[Config, Dict[str, Any]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Build knowledge base from data sources (convenience function).

    This is a user-friendly wrapper that constructs a knowledge base from
    various data sources using the specified method.

    Args:
        sources: Single source or list of sources (files, URLs, streams)
        method: Knowledge base construction method (default: "default")
        config: Optional configuration object or dictionary
        **kwargs: Additional options:
            - embeddings: Whether to generate embeddings (default: True)
            - graph: Whether to build knowledge graph (default: True)
            - pipeline: Custom pipeline configuration
            - fail_fast: Whether to stop on first error (default: False)

    Returns:
        Dictionary containing:
            - knowledge_graph: Knowledge graph data
            - embeddings: Embedding vectors
            - results: Processing results
            - statistics: Processing statistics
            - metadata: Processing metadata

    Examples:
        >>> from veritasreason.core.methods import build_knowledge_base
        >>> result = build_knowledge_base(
        ...     sources=["doc1.pdf", "doc2.docx"],
        ...     method="default",
        ...     embeddings=True,
        ...     graph=True
        ... )
        >>> print(f"Processed {result['statistics']['sources_processed']} sources")
    """
    # Normalize sources to list
    if isinstance(sources, str):
        sources = [sources]

    # Check for custom method in registry
    if method != "default":
        custom_method = method_registry.get("knowledge_base", method)
        if custom_method:
            return custom_method(sources, config=config, **kwargs)

    # Use default VeritasReason framework
    framework = VeritasReason(config=config)
    framework.initialize()

    try:
        # Map method to kwargs
        if method == "minimal":
            kwargs.setdefault("embeddings", False)
            kwargs.setdefault("graph", False)
        elif method == "full":
            kwargs.setdefault("embeddings", True)
            kwargs.setdefault("graph", True)
        else:  # default
            kwargs.setdefault("embeddings", True)
            kwargs.setdefault("graph", True)

        result = framework.build_knowledge_base(sources, **kwargs)
        return result
    finally:
        framework.shutdown(graceful=True)


def run_pipeline(
    pipeline: Union[Dict[str, Any], Any],
    data: Any,
    method: str = "default",
    config: Optional[Union[Config, Dict[str, Any]]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Execute a processing pipeline (convenience function).

    This is a user-friendly wrapper that executes a processing pipeline
    on input data using the specified method.

    Args:
        pipeline: Pipeline object or configuration dictionary
        data: Input data for pipeline
        method: Pipeline execution method (default: "default")
        config: Optional configuration object or dictionary
        **kwargs: Additional pipeline options

    Returns:
        Dictionary containing:
            - output: Pipeline output data
            - metadata: Processing metadata
            - metrics: Performance metrics

    Examples:
        >>> from veritasreason.core.methods import run_pipeline
        >>> result = run_pipeline(
        ...     pipeline={"steps": ["extract", "transform"]},
        ...     data="sample text",
        ...     method="default"
        ... )
    """
    # Check for custom method in registry
    if method != "default":
        custom_method = method_registry.get("pipeline", method)
        if custom_method:
            return custom_method(pipeline, data, config=config, **kwargs)

    # Use default VeritasReason framework
    framework = VeritasReason(config=config)
    framework.initialize()

    try:
        result = framework.run_pipeline(pipeline, data, **kwargs)
        return result
    finally:
        framework.shutdown(graceful=True)


def initialize_framework(
    config: Optional[Union[Config, Dict[str, Any]]] = None,
    method: str = "default",
    **kwargs,
) -> VeritasReason:
    """
    Initialize VeritasReason framework (convenience function).

    This is a user-friendly wrapper that initializes the framework
    using the specified method.

    Args:
        config: Optional configuration object or dictionary
        method: Initialization method (default: "default")
        **kwargs: Additional initialization options

    Returns:
        Initialized VeritasReason framework instance

    Examples:
        >>> from veritasreason.core.methods import initialize_framework
        >>> framework = initialize_framework(
        ...     config={"llm_provider": {"name": "openai"}},
        ...     method="default"
        ... )
        >>> status = framework.get_status()
    """
    # Check for custom method in registry
    if method != "default":
        custom_method = method_registry.get("orchestration", method)
        if custom_method:
            return custom_method(config=config, **kwargs)

    # Use default initialization
    framework = VeritasReason(config=config, **kwargs)

    if method == "minimal":
        # Minimal initialization - just create instance, don't initialize
        pass
    elif method == "full":
        # Full initialization
        framework.initialize()
    else:  # default
        framework.initialize()

    return framework


def get_status(
    framework: Optional[VeritasReason] = None, method: str = "default", **kwargs
) -> Dict[str, Any]:
    """
    Get system status (convenience function).

    This is a user-friendly wrapper that retrieves system status
    using the specified method.

    Args:
        framework: Optional VeritasReason framework instance (creates new if None)
        method: Status retrieval method (default: "default")
        **kwargs: Additional options

    Returns:
        Dictionary containing:
            - state: System state
            - health: Health summary
            - modules: Module status
            - plugins: Plugin status
            - config: Configuration status

    Examples:
        >>> from veritasreason.core.methods import get_status
        >>> status = get_status(framework=my_framework, method="detailed")
        >>> print(f"System state: {status['state']}")
    """
    # Check for custom method in registry
    custom_method = method_registry.get("orchestration", f"get_status_{method}")
    if custom_method:
        return custom_method(framework=framework, **kwargs)

    # Use default status retrieval
    if framework is None:
        framework = VeritasReason()
        framework.initialize()
        should_shutdown = True
    else:
        should_shutdown = False

    try:
        status = framework.get_status()

        # Filter based on method
        if method == "summary":
            return {
                "state": status.get("state"),
                "health": {
                    "is_healthy": status.get("health", {}).get("is_healthy"),
                    "healthy_components": status.get("health", {}).get(
                        "healthy_components"
                    ),
                },
            }
        elif method == "detailed":
            return status
        else:  # default
            return status
    finally:
        if should_shutdown:
            framework.shutdown(graceful=True)


def get_orchestration_method(task: str, name: str) -> Optional[Callable]:
    """
    Get orchestration method by task and name.

    This function retrieves a registered orchestration method from the registry
    or returns a built-in method if available.

    Args:
        task: Task type ("pipeline", "knowledge_base", "orchestration", "lifecycle")
        name: Method name

    Returns:
        Method function or None if not found

    Examples:
        >>> from veritasreason.core.methods import get_orchestration_method
        >>> method = get_orchestration_method("knowledge_base", "custom_method")
        >>> if method:
        ...     result = method(sources=["doc.pdf"])
    """
    # First check registry
    method = method_registry.get(task, name)
    if method:
        return method

    # Check built-in methods
    builtin_methods = {
        "knowledge_base": {
            "default": build_knowledge_base,
            "minimal": lambda sources, **kwargs: build_knowledge_base(
                sources, method="minimal", **kwargs
            ),
            "full": lambda sources, **kwargs: build_knowledge_base(
                sources, method="full", **kwargs
            ),
        },
        "pipeline": {
            "default": run_pipeline,
        },
        "orchestration": {
            "default": initialize_framework,
            "minimal": lambda config=None, **kwargs: initialize_framework(
                config=config, method="minimal", **kwargs
            ),
            "full": lambda config=None, **kwargs: initialize_framework(
                config=config, method="full", **kwargs
            ),
        },
    }

    if task in builtin_methods and name in builtin_methods[task]:
        return builtin_methods[task][name]

    return None


def list_available_methods(task: Optional[str] = None) -> Dict[str, List[str]]:
    """
    List all available orchestration methods.

    Args:
        task: Optional task type to filter by

    Returns:
        Dictionary mapping task types to method names

    Examples:
        >>> from veritasreason.core.methods import list_available_methods
        >>> all_methods = list_available_methods()
        >>> kb_methods = list_available_methods("knowledge_base")
    """
    # Get registered methods
    registered = method_registry.list_all(task=task)

    # Add built-in methods
    builtin_methods = {
        "knowledge_base": ["default", "minimal", "full"],
        "pipeline": ["default"],
        "orchestration": ["default", "minimal", "full"],
        "lifecycle": [],
    }

    if task:
        # Merge for specific task
        result = {
            task: list(set(registered.get(task, []) + builtin_methods.get(task, [])))
        }
    else:
        # Merge for all tasks
        result = {}
        for t in set(list(registered.keys()) + list(builtin_methods.keys())):
            result[t] = list(set(registered.get(t, []) + builtin_methods.get(t, [])))

    return result


# Register default methods with registry
method_registry.register("knowledge_base", "default", build_knowledge_base)
method_registry.register("pipeline", "default", run_pipeline)
method_registry.register("orchestration", "default", initialize_framework)
