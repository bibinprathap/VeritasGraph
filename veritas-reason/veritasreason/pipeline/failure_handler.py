"""
Failure Handler Module

This module provides error handling and retry mechanisms for pipeline execution
and recovery, including configurable retry policies, fallback strategies, and
error severity classification.

Key Features:
    - Error handling and retry mechanisms
    - Configurable retry policies (linear, exponential, fixed)
    - Fallback handler support
    - Error severity classification (low, medium, high, critical)
    - Recovery action management
    - Retry delay calculation
    - Error recovery strategies

Main Classes:
    - FailureHandler: Main failure handler
    - RetryHandler: Retry mechanism handler
    - FallbackHandler: Fallback strategy handler
    - ErrorRecovery: Error recovery coordinator
    - RetryPolicy: Dataclass for retry policy configuration
    - RetryStrategy: Enum for retry strategies
    - ErrorSeverity: Enum for error severity levels
    - FailureRecovery: Dataclass for failure recovery results

Example Usage:
    >>> from veritasreason.pipeline import FailureHandler, RetryPolicy
    >>> handler = FailureHandler()
    >>> policy = RetryPolicy(max_retries=3, strategy=RetryStrategy.EXPONENTIAL)
    >>> recovery = handler.handle_failure(exception, policy)

Author: VeritasReason Contributors
License: MIT
"""

import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .pipeline_builder import PipelineStep


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryStrategy(Enum):
    """Retry strategies."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_retries: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_errors: List[type] = field(default_factory=list)


@dataclass
class FailureRecovery:
    """Failure recovery result."""

    should_retry: bool
    retry_delay: float = 0.0
    recovery_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FailureHandler:
    """
    Failure handling and recovery system.

    • Error detection and classification
    • Retry mechanisms and strategies
    • Failure recovery and rollback
    • Error reporting and logging
    • Performance optimization
    • Custom error handling strategies
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize failure handler.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options:
                - default_max_retries: Default maximum retries
                - default_backoff_factor: Default backoff factor
        """
        self.logger = get_logger("failure_handler")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.default_max_retries = self.config.get("default_max_retries", 3)
        self.default_backoff_factor = self.config.get("default_backoff_factor", 2.0)

        self.retry_policies: Dict[str, RetryPolicy] = {}
        self.error_history: List[Dict[str, Any]] = []

    def handle_step_failure(
        self, step: PipelineStep, error: Exception, **options
    ) -> Dict[str, Any]:
        """
        Handle step failure.

        Args:
            step: Failed step
            error: Exception that occurred
            **options: Additional options

        Returns:
            Recovery result with retry information
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="FailureHandler",
            message=f"Handling step failure: {step.name}",
        )

        try:
            # Classify error
            self.progress_tracker.update_tracking(
                tracking_id, message="Classifying error..."
            )
            error_classification = self.classify_error(error)

            # Get retry policy
            self.progress_tracker.update_tracking(
                tracking_id, message="Getting retry policy..."
            )
            retry_policy = self.get_retry_policy(step.step_type)

            # Check if error is retryable
            self.progress_tracker.update_tracking(
                tracking_id, message="Checking if error is retryable..."
            )
            should_retry = self._should_retry(error, retry_policy)

            # Calculate retry delay
            retry_delay = 0.0
            if should_retry:
                retry_delay = self._calculate_retry_delay(step.name, retry_policy)

            # Log error
            self.logger.error(f"Step '{step.name}' failed: {error}", exc_info=True)

            # Record error history
            self.progress_tracker.update_tracking(
                tracking_id, message="Recording error history..."
            )
            self.error_history.append(
                {
                    "step_name": step.name,
                    "step_type": step.step_type,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "severity": error_classification["severity"].value,
                    "timestamp": time.time(),
                    "retryable": should_retry,
                }
            )

            result = {
                "retry": should_retry,
                "retry_delay": retry_delay,
                "error_classification": error_classification,
                "recovery_action": self._determine_recovery_action(
                    error, error_classification
                ),
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Failure handled: {'Retry' if should_retry else 'No retry'}",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def classify_error(self, error: Exception) -> Dict[str, Any]:
        """
        Classify error severity and type.

        Args:
            error: Exception to classify

        Returns:
            Error classification
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="FailureHandler",
            message=f"Classifying error: {type(error).__name__}",
        )

        try:
            error_type = type(error)
            error_message = str(error)

            # Determine severity
            self.progress_tracker.update_tracking(
                tracking_id, message="Determining error severity..."
            )
            severity = ErrorSeverity.MEDIUM
            if isinstance(error, ValidationError):
                severity = ErrorSeverity.LOW
            elif isinstance(error, ProcessingError):
                severity = ErrorSeverity.HIGH
            elif (
                "timeout" in error_message.lower()
                or "connection" in error_message.lower()
            ):
                severity = ErrorSeverity.MEDIUM
            elif (
                "memory" in error_message.lower() or "resource" in error_message.lower()
            ):
                severity = ErrorSeverity.HIGH
            else:
                severity = ErrorSeverity.MEDIUM

            result = {
                "error_type": error_type.__name__,
                "severity": severity,
                "message": error_message,
                "traceback": traceback.format_exc(),
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Error classified: {severity.value}",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def set_retry_policy(self, step_type: str, policy: RetryPolicy) -> None:
        """
        Set retry policy for step type.

        Args:
            step_type: Step type
            policy: Retry policy
        """
        self.retry_policies[step_type] = policy
        self.logger.debug(f"Set retry policy for {step_type}: {policy}")

    def get_retry_policy(self, step_type: str) -> RetryPolicy:
        """
        Get retry policy for step type.

        Args:
            step_type: Step type

        Returns:
            Retry policy
        """
        return self.retry_policies.get(
            step_type,
            RetryPolicy(
                max_retries=self.default_max_retries,
                backoff_factor=self.default_backoff_factor,
            ),
        )

    def _should_retry(self, error: Exception, policy: RetryPolicy) -> bool:
        """Check if error should be retried."""
        # Check if error type is in retryable list
        if policy.retryable_errors:
            if not any(
                isinstance(error, err_type) for err_type in policy.retryable_errors
            ):
                return False

        # Check max retries (would need step retry count)
        # For now, assume we can retry
        return True

    def _calculate_retry_delay(
        self, step_name: str, policy: RetryPolicy, attempt: int = 1
    ) -> float:
        """Calculate retry delay based on strategy."""
        if policy.strategy == RetryStrategy.LINEAR:
            delay = policy.initial_delay * attempt
        elif policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = policy.initial_delay * (policy.backoff_factor ** (attempt - 1))
        else:  # FIXED
            delay = policy.initial_delay

        return min(delay, policy.max_delay)

    def _determine_recovery_action(
        self, error: Exception, classification: Dict[str, Any]
    ) -> Optional[str]:
        """Determine recovery action based on error."""
        severity = classification["severity"]

        if severity == ErrorSeverity.LOW:
            return "retry"
        elif severity == ErrorSeverity.MEDIUM:
            return "retry_with_backoff"
        elif severity == ErrorSeverity.HIGH:
            return "skip_step"
        else:  # CRITICAL
            return "abort_pipeline"

    def retry_failed_step(self, step: PipelineStep, error: Exception, **options) -> Any:
        """
        Retry failed step.

        Args:
            step: Failed step
            error: Original error
            **options: Additional options

        Returns:
            Step execution result
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="FailureHandler",
            message=f"Retrying failed step: {step.name}",
        )

        try:
            recovery = self.handle_step_failure(step, error, **options)

            if not recovery["retry"]:
                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message="Step not retryable, raising error",
                )
                raise error

            # Wait for retry delay
            if recovery["retry_delay"] > 0:
                self.progress_tracker.update_tracking(
                    tracking_id,
                    message=f"Waiting {recovery['retry_delay']}s before retry...",
                )
                time.sleep(recovery["retry_delay"])

            # Retry step execution
            # This would typically be called by the execution engine
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Retry scheduled for step: {step.name}",
            )
            return recovery

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_error_history(
        self, step_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get error history.

        Args:
            step_name: Optional step name filter

        Returns:
            Error history
        """
        if step_name:
            return [e for e in self.error_history if e["step_name"] == step_name]
        return list(self.error_history)

    def clear_error_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()

    def handle_failure(
        self, error: Exception, policy: "RetryPolicy", retry_count: int = 0
    ) -> "RecoveryAction":
        """
        Handle failure using the given policy and retry count.

        Args:
            error: Exception that occurred
            policy: Retry policy to apply
            retry_count: Current retry count (0-based)

        Returns:
            RecoveryAction with should_retry and retry_delay attributes
        """
        should_retry = retry_count < policy.max_retries and self._should_retry(error, policy)

        if should_retry:
            attempt = retry_count + 1
            if policy.strategy == RetryStrategy.LINEAR:
                delay = policy.initial_delay * attempt
            elif policy.strategy == RetryStrategy.EXPONENTIAL:
                delay = policy.initial_delay * (policy.backoff_factor ** retry_count)
            else:  # FIXED
                delay = policy.initial_delay
            retry_delay = min(delay, policy.max_delay)
        else:
            retry_delay = 0.0

        return RecoveryAction(should_retry=should_retry, retry_delay=retry_delay)


class RecoveryAction:
    """Recovery action result from handle_failure."""

    def __init__(self, should_retry: bool, retry_delay: float = 0.0):
        self.should_retry = should_retry
        self.retry_delay = retry_delay


class RetryHandler:
    """Retry handler for failed steps."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0, **config):
        """Initialize retry handler."""
        self.failure_handler = FailureHandler(
            default_max_retries=max_retries,
            default_backoff_factor=backoff_factor,
            **config,
        )

    def retry_failed_step(self, step: PipelineStep, error: Exception) -> Dict[str, Any]:
        """Retry failed step."""
        return self.failure_handler.retry_failed_step(step, error)

    def set_retry_policy(self, step_type: str, policy: RetryPolicy) -> None:
        """Set retry policy."""
        self.failure_handler.set_retry_policy(step_type, policy)


class FallbackHandler:
    """Fallback handler for service failures."""

    def __init__(self, **config):
        """Initialize fallback handler."""
        self.logger = get_logger("fallback_handler")
        self.config = config
        self.fallback_strategies: Dict[str, str] = {}

    def set_fallback_strategy(self, strategy: str) -> None:
        """Set fallback strategy."""
        self.fallback_strategies["default"] = strategy

    def handle_service_failure(self, service_name: str) -> Dict[str, Any]:
        """Handle service failure."""
        strategy = self.fallback_strategies.get(
            service_name, self.fallback_strategies.get("default", "abort")
        )
        return {"strategy": strategy, "service": service_name}

    def switch_to_backup(self, primary_failed: bool) -> bool:
        """Switch to backup service."""
        return primary_failed


class ErrorRecovery:
    """Error recovery system."""

    def __init__(self, **config):
        """Initialize error recovery."""
        self.logger = get_logger("error_recovery")
        self.config = config
        self.failure_handler = FailureHandler(**config)

    def analyze_error(self, error: Exception) -> Dict[str, Any]:
        """Analyze error and determine recovery strategy."""
        return self.failure_handler.classify_error(error)

    def recover_from_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recover from error."""
        classification = self.analyze_error(error)
        return {
            "recovery_action": self.failure_handler._determine_recovery_action(
                error, classification
            ),
            "classification": classification,
        }
