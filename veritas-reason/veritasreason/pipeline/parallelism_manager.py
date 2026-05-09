"""
Parallelism Manager Module

This module provides parallel execution management for pipeline tasks and operations,
supporting thread-based and process-based parallelism with load balancing and
performance optimization.

Key Features:
    - Parallel task execution and coordination
    - Resource allocation and scheduling
    - Load balancing and optimization
    - Performance monitoring and tuning
    - Error handling and recovery
    - Thread and process pool execution
    - Task priority management

Main Classes:
    - ParallelismManager: Parallelism management system
    - ParallelExecutor: Parallel execution coordinator
    - Task: Dataclass for parallel task definition
    - ParallelExecutionResult: Dataclass for parallel execution results

Example Usage:
    >>> from veritasreason.pipeline import ParallelismManager, Task
    >>> manager = ParallelismManager(max_workers=4)
    >>> tasks = [Task("task1", handler, args), Task("task2", handler2, args2)]
    >>> results = manager.execute_parallel(tasks)

Author: VeritasReason Contributors
License: MIT
"""

import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .pipeline_builder import Pipeline, PipelineStep


@dataclass
class Task:
    """Parallel task definition."""

    task_id: str
    handler: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class ParallelExecutionResult:
    """Parallel execution result."""

    task_id: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0


class ParallelismManager:
    """
    Parallelism management system.

    • Parallel task execution and coordination
    • Resource allocation and scheduling
    • Load balancing and optimization
    • Performance monitoring and tuning
    • Error handling and recovery
    • Advanced parallelism strategies
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize parallelism manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options:
                - max_workers: Maximum parallel workers
                - use_processes: Use processes instead of threads
        """
        self.logger = get_logger("parallelism_manager")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.max_workers = self.config.get("max_workers", 4)
        self.use_processes = self.config.get("use_processes", False)

        self.executor: Optional[ThreadPoolExecutor] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        self.lock = threading.Lock()

    def execute_parallel(
        self, tasks: List[Task], pipeline_id: Optional[str] = None, **options
    ) -> List[ParallelExecutionResult]:
        """
        Execute tasks in parallel.

        Args:
            tasks: List of tasks to execute
            pipeline_id: Optional pipeline ID for progress tracking
            **options: Additional options

        Returns:
            List of execution results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="ParallelismManager",
            message=f"Executing {len(tasks)} tasks in parallel",
            pipeline_id=pipeline_id,
        )

        try:
            if not tasks:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="completed", message="No tasks to execute"
                )
                return []

            # Sort by priority
            self.progress_tracker.update_tracking(
                tracking_id, message="Sorting tasks by priority..."
            )
            sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

            # Execute tasks
            self.progress_tracker.update_tracking(
                tracking_id,
                message=f"Executing tasks using {'processes' if self.use_processes else 'threads'}...",
            )
            if self.use_processes:
                results = self._execute_with_processes(sorted_tasks, **options)
            else:
                results = self._execute_with_threads(sorted_tasks, **options)

            success_count = sum(1 for r in results if r.success)
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Executed {len(tasks)} tasks: {success_count} succeeded, {len(tasks) - success_count} failed",
            )
            return results

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _execute_with_threads(
        self, tasks: List[Task], **options
    ) -> List[ParallelExecutionResult]:
        """Execute tasks using thread pool."""
        results = []
        max_workers = options.get("max_workers", self.max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(task.handler, *task.args, **task.kwargs): task
                for task in tasks
            }

            # Collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                start_time = time.time()

                try:
                    result = future.result()
                    execution_time = time.time() - start_time
                    results.append(
                        ParallelExecutionResult(
                            task_id=task.task_id,
                            success=True,
                            result=result,
                            execution_time=execution_time,
                        )
                    )
                except Exception as e:
                    execution_time = time.time() - start_time
                    results.append(
                        ParallelExecutionResult(
                            task_id=task.task_id,
                            success=False,
                            error=e,
                            execution_time=execution_time,
                        )
                    )

        return results

    def _execute_with_processes(
        self, tasks: List[Task], **options
    ) -> List[ParallelExecutionResult]:
        """Execute tasks using process pool."""
        results = []
        max_workers = options.get("max_workers", self.max_workers)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(task.handler, *task.args, **task.kwargs): task
                for task in tasks
            }

            # Collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                start_time = time.time()

                try:
                    result = future.result()
                    execution_time = time.time() - start_time
                    results.append(
                        ParallelExecutionResult(
                            task_id=task.task_id,
                            success=True,
                            result=result,
                            execution_time=execution_time,
                        )
                    )
                except Exception as e:
                    execution_time = time.time() - start_time
                    results.append(
                        ParallelExecutionResult(
                            task_id=task.task_id,
                            success=False,
                            error=e,
                            execution_time=execution_time,
                        )
                    )

        return results

    def execute_pipeline_steps_parallel(
        self, steps: List[PipelineStep], data: Any, **options
    ) -> List[Any]:
        """
        Execute pipeline steps in parallel.

        Args:
            steps: List of steps to execute
            data: Input data
            **options: Additional options

        Returns:
            List of step results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="ParallelismManager",
            message=f"Executing {len(steps)} pipeline steps in parallel",
        )

        try:
            # Create tasks from steps
            self.progress_tracker.update_tracking(
                tracking_id, message="Creating tasks from steps..."
            )
            tasks = [
                Task(
                    task_id=step.name,
                    handler=step.handler or (lambda d, **kwargs: d),
                    args=(data,),
                    kwargs=step.config,
                    priority=0,
                )
                for step in steps
            ]

            # Execute tasks
            self.progress_tracker.update_tracking(
                tracking_id, message="Executing tasks in parallel..."
            )
            results = self.execute_parallel(tasks, **options)

            # Map results back to steps
            self.progress_tracker.update_tracking(
                tracking_id, message="Mapping results to steps..."
            )
            result_map = {r.task_id: r for r in results}
            step_results = []

            for step in steps:
                result = result_map.get(step.name)
                if result and result.success:
                    step_results.append(result.result)
                else:
                    raise ProcessingError(
                        f"Step {step.name} failed: {result.error if result else 'Unknown error'}"
                    )

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Executed {len(steps)} steps in parallel",
            )
            return step_results

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def identify_parallelizable_steps(
        self, pipeline: Pipeline
    ) -> List[List[PipelineStep]]:
        """
        Identify steps that can be executed in parallel.

        Args:
            pipeline: Pipeline object

        Returns:
            List of step groups that can run in parallel
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="ParallelismManager",
            message=f"Identifying parallelizable steps for pipeline: {pipeline.name}",
        )

        try:
            # Group steps by dependency level
            self.progress_tracker.update_tracking(
                tracking_id, message="Analyzing step dependencies..."
            )
            step_map = {step.name: step for step in pipeline.steps}
            dependency_levels = {}

            def get_level(step_name: str) -> int:
                if step_name in dependency_levels:
                    return dependency_levels[step_name]

                step = step_map[step_name]
                if not step.dependencies:
                    level = 0
                else:
                    level = max(get_level(dep) for dep in step.dependencies) + 1

                dependency_levels[step_name] = level
                return level

            # Calculate levels for all steps
            for step in pipeline.steps:
                get_level(step.name)

            # Group by level
            self.progress_tracker.update_tracking(
                tracking_id, message="Grouping steps by dependency level..."
            )
            level_groups = {}
            for step in pipeline.steps:
                level = dependency_levels[step.name]
                if level not in level_groups:
                    level_groups[level] = []
                level_groups[level].append(step)

            # Return groups sorted by level
            result = [level_groups[level] for level in sorted(level_groups.keys())]
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Identified {len(result)} parallelizable step groups",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def optimize_parallel_execution(
        self, pipeline: Pipeline, available_workers: int
    ) -> Dict[str, Any]:
        """
        Optimize parallel execution plan.

        Args:
            pipeline: Pipeline object
            available_workers: Available worker count

        Returns:
            Optimization plan
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="ParallelismManager",
            message=f"Optimizing parallel execution for pipeline: {pipeline.name}",
        )

        try:
            self.progress_tracker.update_tracking(
                tracking_id, message="Identifying parallelizable steps..."
            )
            parallel_groups = self.identify_parallelizable_steps(pipeline)

            # Calculate execution plan
            self.progress_tracker.update_tracking(
                tracking_id, message="Calculating execution plan..."
            )
            execution_plan = []
            for group in parallel_groups:
                execution_plan.append(
                    {
                        "steps": [s.name for s in group],
                        "parallel": len(group) > 1,
                        "worker_count": min(len(group), available_workers),
                    }
                )

            result = {
                "execution_plan": execution_plan,
                "total_groups": len(parallel_groups),
                "max_parallelism": max(len(group) for group in parallel_groups)
                if parallel_groups
                else 1,
                "estimated_workers": sum(
                    plan["worker_count"] for plan in execution_plan
                ),
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Optimization complete: {len(parallel_groups)} groups, max parallelism: {result['max_parallelism']}",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise


class ParallelExecutor:
    """Parallel executor for pipeline tasks."""

    def __init__(self, max_workers: int = 4, **config):
        """Initialize parallel executor."""
        self.parallelism_manager = ParallelismManager(max_workers=max_workers, **config)

    def execute_parallel(self, tasks: List[Task]) -> List[ParallelExecutionResult]:
        """Execute tasks in parallel."""
        return self.parallelism_manager.execute_parallel(tasks)
