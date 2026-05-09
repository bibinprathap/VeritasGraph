"""
Pipeline and Orchestration Module

This module provides comprehensive pipeline construction and orchestration capabilities,
enabling the creation, execution, validation, and management of complex data processing
workflows with error handling, parallelism, and resource scheduling.

Key Features:
    - Pipeline construction DSL for building workflows
    - Pipeline execution engine with status tracking
    - Error handling and retry mechanisms
    - Parallel execution management
    - Resource allocation and scheduling
    - Pipeline validation and testing
    - Pre-built pipeline templates
    - Progress tracking and monitoring
    - Failure recovery strategies

Main Classes:
    - PipelineBuilder: Pipeline construction DSL
    - ExecutionEngine: Pipeline execution engine
    - FailureHandler: Error handling and retry mechanisms
    - ParallelismManager: Parallel execution management
    - ResourceScheduler: Resource allocation and scheduling
    - PipelineValidator: Pipeline validation and testing
    - PipelineTemplateManager: Pre-built pipeline templates
    - Pipeline: Pipeline definition dataclass
    - PipelineStep: Pipeline step definition dataclass

Example Usage:
    >>> from veritasreason.pipeline import PipelineBuilder, ExecutionEngine
    >>> builder = PipelineBuilder()
    >>> pipeline = builder.add_step("ingest", "file_ingest").add_step("parse", "document_parse").build()
    >>> engine = ExecutionEngine()
    >>> result = engine.execute(pipeline)

Author: VeritasReason Contributors
License: MIT
"""

from .execution_engine import (
    ExecutionEngine,
    ExecutionResult,
    PipelineStatus,
    ProgressTracker,
)
from .failure_handler import (
    ErrorRecovery,
    ErrorSeverity,
    FailureHandler,
    FailureRecovery,
    FallbackHandler,
    RetryHandler,
    RetryPolicy,
    RetryStrategy,
)
from .parallelism_manager import (
    ParallelExecutionResult,
    ParallelExecutor,
    ParallelismManager,
    Task,
)
from .pipeline_builder import (
    Pipeline,
    PipelineBuilder,
    PipelineSerializer,
    PipelineStep,
    StepStatus,
)
from .pipeline_templates import PipelineTemplate, PipelineTemplateManager
from .pipeline_validator import PipelineValidator, ValidationResult
from .resource_scheduler import (
    Resource,
    ResourceAllocation,
    ResourceScheduler,
    ResourceType,
)

__all__ = [
    # Pipeline construction
    "PipelineBuilder",
    "Pipeline",
    "PipelineStep",
    "StepStatus",
    "PipelineSerializer",
    # Execution
    "ExecutionEngine",
    "ExecutionResult",
    "PipelineStatus",
    "ProgressTracker",
    # Failure handling
    "FailureHandler",
    "RetryHandler",
    "FallbackHandler",
    "ErrorRecovery",
    "RetryPolicy",
    "RetryStrategy",
    "ErrorSeverity",
    "FailureRecovery",
    # Parallelism
    "ParallelismManager",
    "ParallelExecutor",
    "Task",
    "ParallelExecutionResult",
    # Resource management
    "ResourceScheduler",
    "Resource",
    "ResourceAllocation",
    "ResourceType",
    # Validation
    "PipelineValidator",
    "ValidationResult",
    # Templates
    "PipelineTemplateManager",
    "PipelineTemplate",
]
