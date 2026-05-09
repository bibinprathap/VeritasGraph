"""
Lifecycle Management Module

This module provides comprehensive lifecycle management for the VeritasReason framework,
including startup/shutdown sequences, health monitoring, and resource management.

Key Features:
    - Startup and shutdown hook system with priority ordering
    - Component health monitoring and status tracking
    - Graceful degradation and error handling
    - Resource cleanup and state management
    - System state tracking (uninitialized, ready, running, stopped, etc.)

Example Usage:
    >>> from veritasreason.core import LifecycleManager
    >>> manager = LifecycleManager()
    >>> manager.register_startup_hook(my_hook, priority=10)
    >>> manager.startup()
    >>> health = manager.get_health_summary()

Author: VeritasReason Contributors
License: MIT
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..utils.exceptions import VeritasReasonError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class SystemState(str, Enum):
    """System state enumeration."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class HealthStatus:
    """Health status information."""

    component: str
    healthy: bool
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class LifecycleManager:
    """
    System lifecycle manager.

    This class coordinates the startup, shutdown, and health monitoring of all
    framework components. It provides a hook-based system for executing code
    at specific lifecycle stages with priority ordering.

    Features:
        - Priority-based startup/shutdown hooks
        - Component registration and health monitoring
        - State management and tracking
        - Graceful error handling during lifecycle transitions

    Example Usage:
        >>> manager = LifecycleManager()
        >>> manager.register_component("database", db_connection)
        >>> manager.register_startup_hook(init_db, priority=10)
        >>> manager.startup()
        >>> # System is now ready
        >>> manager.shutdown(graceful=True)
    """

    def __init__(self):
        """
        Initialize lifecycle manager.

        Creates a new lifecycle manager in UNINITIALIZED state with empty
        registries for components, hooks, and health status.
        """
        self.logger = get_logger("lifecycle")

        # System state tracking
        self.state: SystemState = SystemState.UNINITIALIZED

        # Component registry for health monitoring
        self._component_registry: Dict[str, Any] = {}

        # Health status tracking
        self.health_status: Dict[str, HealthStatus] = {}
        self._last_health_check: Optional[float] = None

        # Hook registries: list of (hook_function, priority) tuples
        # Lower priority = earlier execution
        self.startup_hooks: List[Tuple[Callable[[], None], int]] = []
        self.shutdown_hooks: List[Tuple[Callable[[], None], int]] = []

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()

        self.logger.debug("Lifecycle manager initialized")

    def startup(self) -> None:
        """
        Execute startup sequence.

        This method runs all registered startup hooks in priority order,
        verifies component initialization, and performs initial health checks.
        The system transitions from UNINITIALIZED -> INITIALIZING -> READY.

        Raises:
            VeritasReasonError: If startup fails (hook failure, component verification failure)

        Example:
            >>> manager = LifecycleManager()
            >>> manager.register_startup_hook(init_config, priority=10)
            >>> manager.register_startup_hook(init_database, priority=20)
            >>> manager.startup()  # Hooks execute in order: init_config, then init_database
        """
        # Track system startup
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="core",
            submodule="LifecycleManager",
            message="Starting system lifecycle",
        )

        try:
            # Check if already started
            if self._is_already_started():
                self.progress_tracker.stop_tracking(
                    tracking_id, status="completed", message="System already started"
                )
                return

            # Execute startup sequence
            self._execute_startup_sequence()

            # Verify and check health
            self._verify_and_check_health()

            # Transition to ready state
            self.state = SystemState.READY
            self.logger.info("System startup completed successfully")

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message="System startup completed successfully",
            )

        except Exception as e:
            # Transition to error state on failure
            self.state = SystemState.ERROR
            self.logger.error(f"System startup failed: {e}")
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _is_already_started(self) -> bool:
        """Check if system is already in a started state."""
        if self.state in (SystemState.READY, SystemState.RUNNING):
            self.logger.warning(
                f"System already in {self.state.value} state, skipping startup"
            )
            return True
        return False

    def _execute_startup_sequence(self) -> None:
        """Execute startup hooks in priority order."""
        self.state = SystemState.INITIALIZING
        self.logger.info("Starting system lifecycle")

        # Execute hooks
        self._execute_hooks(self.startup_hooks, "startup")

    def _verify_and_check_health(self) -> None:
        """Verify components and check their health."""
        # Verify all registered components are properly initialized
        self._verify_components()

        # Run initial health checks
        health_results = self.health_check()
        unhealthy_components = [
            name for name, status in health_results.items() if not status.healthy
        ]

        if unhealthy_components:
            self.logger.warning(
                f"Some components are unhealthy after startup: {unhealthy_components}"
            )
        else:
            self.logger.debug("All components are healthy")

    def shutdown(self, graceful: bool = True) -> None:
        """
        Execute shutdown sequence.

        This method runs all registered shutdown hooks in priority order and
        cleans up resources. In graceful mode, hook failures are logged but
        don't stop the shutdown process.

        Args:
            graceful: Whether to shutdown gracefully (default: True)
                - True: Continue shutdown even if hooks fail (log warnings)
                - False: Stop shutdown on first hook failure (raise error)

        Raises:
            VeritasReasonError: If shutdown fails and graceful=False

        Example:
            >>> manager.shutdown(graceful=True)  # Continue even if cleanup fails
            >>> manager.shutdown(graceful=False)  # Stop on first error
        """
        # Track system shutdown
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="core",
            submodule="LifecycleManager",
            message=f"Shutting down system (graceful={graceful})",
        )

        try:
            # Check if already stopped
            if self._is_already_stopped():
                self.progress_tracker.stop_tracking(
                    tracking_id, status="completed", message="System already stopped"
                )
                return

            # Execute shutdown sequence
            self._execute_shutdown_sequence(graceful)

            # Cleanup resources
            self._cleanup_resources()

            # Transition to stopped state
            self.state = SystemState.STOPPED
            self.logger.info("System shutdown completed successfully")

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message="System shutdown completed successfully",
            )

        except Exception as e:
            # Transition to error state on failure
            self.state = SystemState.ERROR
            self.logger.error(f"System shutdown failed: {e}")
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            if not graceful:
                raise

    def _is_already_stopped(self) -> bool:
        """Check if system is already stopped."""
        if self.state == SystemState.STOPPED:
            self.logger.warning("System already in STOPPED state")
            return True
        return False

    def _execute_shutdown_sequence(self, graceful: bool) -> None:
        """Execute shutdown hooks in priority order."""
        self.state = SystemState.STOPPING
        self.logger.info(f"Shutting down system (graceful={graceful})")

        # Execute hooks with graceful error handling
        self._execute_hooks(self.shutdown_hooks, "shutdown", graceful=graceful)

    def _execute_hooks(
        self, hooks: List[Tuple[Callable[[], None], int]], hook_type: str, graceful: bool = False
    ) -> None:
        """
        Execute hooks in priority order.

        Args:
            hooks: List of (hook_function, priority) tuples
            hook_type: Type of hooks ("startup" or "shutdown")
            graceful: Whether to continue on errors (only for shutdown)

        Raises:
            VeritasReasonError: If hook fails and not graceful
        """
        # Sort hooks by priority (lower priority = earlier execution)
        sorted_hooks = sorted(hooks, key=lambda x: x[1])

        if sorted_hooks:
            self.logger.debug(f"Executing {len(sorted_hooks)} {hook_type} hook(s)")

        # Execute all hooks in priority order
        for hook_fn, priority in sorted_hooks:
            try:
                self.logger.debug(f"Executing {hook_type} hook with priority {priority}")
                hook_fn()
            except Exception as e:
                error_msg = f"{hook_type.capitalize()} hook (priority {priority}) failed: {e}"

                if graceful:
                    # In graceful mode, log warning but continue
                    self.logger.warning(error_msg)
                else:
                    # In non-graceful mode, stop on first error
                    self.logger.error(error_msg)
                    raise VeritasReasonError(error_msg) from e

    def health_check(self) -> Dict[str, HealthStatus]:
        """
        Perform comprehensive system health check.

        This method checks the health of all registered components by calling
        their health_check() method if available, or using default health logic.
        Results are cached in health_status and returned.

        Returns:
            Dictionary mapping component names to HealthStatus objects,
            containing health status, messages, and details for each component

        Example:
            >>> health = manager.health_check()
            >>> for name, status in health.items():
            ...     print(f"{name}: {'✓' if status.healthy else '✗'}")
        """
        # Record health check timestamp
        self._last_health_check = time.time()

        # Check health of each registered component
        health_results = {
            name: self._check_component_health(name, component)
            for name, component in self._component_registry.items()
        }

        # Update cached health status
        self.health_status.update(health_results)

        # Log summary
        self._log_health_summary(health_results)

        return health_results

    def _check_component_health(self, component_name: str, component: Any) -> HealthStatus:
        """
        Check health of a single component.

        Args:
            component_name: Name of the component
            component: Component instance

        Returns:
            HealthStatus object for the component
        """
        # Prevent infinite recursion if checking self
        if component is self:
            return HealthStatus(
                component=component_name,
                healthy=True,
                message="LifecycleManager is active",
                details={"state": self.state.value},
            )

        try:
            if hasattr(component, "health_check"):
                # Component has its own health check method
                component_health = component.health_check()
                healthy, message, details = self._parse_health_result(component_health)
            else:
                # No health_check method: assume healthy if component exists
                healthy = component is not None
                message = "Component exists" if healthy else "Component is None"
                details = {}

            return HealthStatus(
                component=component_name,
                healthy=healthy,
                message=message,
                details=details,
            )

        except Exception as e:
            # Health check failed: mark as unhealthy
            error_msg = f"Health check failed: {e}"
            self.logger.warning(f"Component {component_name} health check error: {e}")

            return HealthStatus(
                component=component_name,
                healthy=False,
                message=error_msg,
                details={"error": str(e), "error_type": type(e).__name__},
            )

    def _parse_health_result(self, health_result: Any) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Parse component health check result into standardized format.

        Args:
            health_result: Health check result (dict, bool, or other)

        Returns:
            Tuple of (healthy, message, details)
        """
        if isinstance(health_result, dict):
            # Dictionary format: {"healthy": bool, "message": str, "details": dict}
            return (
                health_result.get("healthy", True),
                health_result.get("message", ""),
                health_result.get("details", {}),
            )
        elif isinstance(health_result, bool):
            # Simple boolean
            return health_result, "", {}
        else:
            # Other types: convert to boolean
            return bool(health_result), "", {}

    def _log_health_summary(self, health_results: Dict[str, HealthStatus]) -> None:
        """Log summary of health check results."""
        unhealthy_components = [
            name for name, status in health_results.items() if not status.healthy
        ]

        if unhealthy_components:
            self.logger.warning(
                f"Health check found {len(unhealthy_components)} unhealthy component(s): "
                f"{unhealthy_components}"
            )
        else:
            self.logger.debug(
                f"Health check passed for all {len(health_results)} component(s)"
            )

    def register_component(self, name: str, component: Any) -> None:
        """
        Register a component for health monitoring.

        Args:
            name: Component name
            component: Component instance
        """
        self._component_registry[name] = component
        self.logger.debug(f"Registered component: {name}")

    def unregister_component(self, name: str) -> None:
        """
        Unregister a component.

        Args:
            name: Component name
        """
        if name in self._component_registry:
            del self._component_registry[name]
            if name in self.health_status:
                del self.health_status[name]
            self.logger.debug(f"Unregistered component: {name}")

    def register_startup_hook(
        self, hook_fn: Callable[[], None], priority: int = 50
    ) -> None:
        """
        Register a startup hook.

        Hooks are executed in order of priority (lower = earlier).
        Priority values are typically between 0-100.

        Args:
            hook_fn: Function to call during startup (no arguments)
            priority: Hook priority (lower = earlier execution, default: 50)
        """
        if not callable(hook_fn):
            raise ValueError("hook_fn must be callable")

        self.startup_hooks.append((hook_fn, priority))
        self.logger.debug(f"Registered startup hook with priority {priority}")

    def register_shutdown_hook(
        self, hook_fn: Callable[[], None], priority: int = 50
    ) -> None:
        """
        Register a shutdown hook.

        Hooks are executed in order of priority (lower = earlier).
        Priority values are typically between 0-100.

        Args:
            hook_fn: Function to call during shutdown (no arguments)
            priority: Hook priority (lower = earlier execution, default: 50)
        """
        if not callable(hook_fn):
            raise ValueError("hook_fn must be callable")

        self.shutdown_hooks.append((hook_fn, priority))
        self.logger.debug(f"Registered shutdown hook with priority {priority}")

    def get_state(self) -> SystemState:
        """
        Get current system state.

        Returns:
            Current system state
        """
        return self.state

    def is_ready(self) -> bool:
        """
        Check if system is ready.

        Returns:
            True if system is ready, False otherwise
        """
        return self.state == SystemState.READY or self.state == SystemState.RUNNING

    def is_running(self) -> bool:
        """
        Check if system is running.

        Returns:
            True if system is running, False otherwise
        """
        return self.state == SystemState.RUNNING

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get summary of system health.

        Returns:
            Dictionary with health summary information
        """
        health_results = self.health_check()

        total = len(health_results)
        healthy = sum(1 for status in health_results.values() if status.healthy)
        unhealthy = total - healthy

        return {
            "state": self.state.value,
            "total_components": total,
            "healthy_components": healthy,
            "unhealthy_components": unhealthy,
            "is_healthy": unhealthy == 0,
            "last_check": self._last_health_check,
            "components": {
                name: {
                    "healthy": status.healthy,
                    "message": status.message,
                    "timestamp": status.timestamp,
                }
                for name, status in health_results.items()
            },
        }

    def _verify_components(self) -> None:
        """
        Verify that all registered components are initialized.

        Raises:
            VeritasReasonError: If components are not properly initialized
        """
        uninitialized = []

        for name, component in self._component_registry.items():
            if component is None:
                uninitialized.append(name)

        if uninitialized:
            raise VeritasReasonError(
                f"Components not initialized: {', '.join(uninitialized)}"
            )

    def _cleanup_resources(self) -> None:
        """
        Cleanup all system resources.

        This method attempts to cleanup all registered components by calling
        their cleanup() or close() methods if available. Errors during cleanup
        are logged but don't stop the cleanup process.
        """
        cleanup_count = 0

        # Cleanup each registered component
        for component_name, component in self._component_registry.items():
            try:
                # Try cleanup() method first, then close()
                if hasattr(component, "cleanup"):
                    component.cleanup()
                    cleanup_count += 1
                    self.logger.debug(f"Cleaned up component: {component_name}")
                elif hasattr(component, "close"):
                    component.close()
                    cleanup_count += 1
                    self.logger.debug(f"Closed component: {component_name}")
            except Exception as e:
                # Log but continue cleanup for other components
                self.logger.warning(
                    f"Failed to cleanup component {component_name}: {e}"
                )

        if cleanup_count > 0:
            self.logger.debug(f"Cleaned up {cleanup_count} component(s)")

        # Clear all registries
        self._component_registry.clear()
        self.health_status.clear()

        self.logger.debug("Resource cleanup completed")
