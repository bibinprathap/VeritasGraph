"""
Resource Scheduler Module

This module provides resource allocation and scheduling for pipeline execution and
optimization, managing CPU, GPU, memory, disk, and network resources.

Key Features:
    - Resource allocation and scheduling
    - Multiple resource types (CPU, GPU, memory, disk, network)
    - Resource capacity management
    - Allocation tracking and monitoring
    - Resource optimization
    - Thread-safe resource management

Main Classes:
    - ResourceScheduler: Resource scheduler for pipeline execution
    - Resource: Dataclass for resource definition
    - ResourceAllocation: Dataclass for resource allocation records
    - ResourceType: Enum for resource types

Example Usage:
    >>> from veritasreason.pipeline import ResourceScheduler, ResourceType
    >>> scheduler = ResourceScheduler()
    >>> scheduler.register_resource("cpu1", ResourceType.CPU, capacity=100.0)
    >>> allocation = scheduler.allocate_resource("cpu1", ResourceType.CPU, 50.0, "pipeline1")

Author: VeritasReason Contributors
License: MIT
"""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .pipeline_builder import Pipeline


class ResourceType(Enum):
    """Resource types."""

    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class Resource:
    """Resource definition."""

    resource_id: str
    resource_type: ResourceType
    capacity: float
    allocated: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceAllocation:
    """Resource allocation record."""

    allocation_id: str
    resource_id: str
    resource_type: ResourceType
    amount: float
    pipeline_id: str
    step_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceScheduler:
    """
    Resource scheduling and allocation system.

    • Resource allocation and management
    • Scheduling algorithms and strategies
    • Load balancing and optimization
    • Performance monitoring and tuning
    • Error handling and recovery
    • Advanced scheduling techniques
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize resource scheduler.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options:
                - max_cpu_cores: Maximum CPU cores
                - max_memory_gb: Maximum memory in GB
                - enable_gpu: Enable GPU allocation
        """
        self.logger = get_logger("resource_scheduler")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.resources: Dict[str, Resource] = {}
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.lock = threading.RLock()  # RLock allows re-entrancy for nested lock acquisition in allocate_resources

        self._initialize_resources()

    def _initialize_resources(self) -> None:
        """Initialize available resources."""
        try:
            import psutil

            # CPU resources
            cpu_count = psutil.cpu_count(logical=False) or 1
            self.resources["cpu"] = Resource(
                resource_id="cpu",
                resource_type=ResourceType.CPU,
                capacity=float(cpu_count),
                metadata={"logical_cores": psutil.cpu_count(logical=True) or 1},
            )

            # Memory resources
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            self.resources["memory"] = Resource(
                resource_id="memory",
                resource_type=ResourceType.MEMORY,
                capacity=memory_gb,
                metadata={"available_gb": memory.available / (1024**3)},
            )

            # Disk resources
            try:
                disk = psutil.disk_usage("/")
                disk_gb = disk.free / (1024**3)
                self.resources["disk"] = Resource(
                    resource_id="disk",
                    resource_type=ResourceType.DISK,
                    capacity=disk_gb,
                    metadata={"total_gb": disk.total / (1024**3)},
                )
            except Exception:
                # Default disk capacity if unavailable
                self.resources["disk"] = Resource(
                    resource_id="disk",
                    resource_type=ResourceType.DISK,
                    capacity=100.0,
                    metadata={},
                )
        except (ImportError, OSError):
            # Fallback if psutil not available
            self.logger.warning("psutil not available, using default resource values")
            self.resources["cpu"] = Resource(
                resource_id="cpu",
                resource_type=ResourceType.CPU,
                capacity=4.0,
                metadata={},
            )
            self.resources["memory"] = Resource(
                resource_id="memory",
                resource_type=ResourceType.MEMORY,
                capacity=8.0,
                metadata={},
            )
            self.resources["disk"] = Resource(
                resource_id="disk",
                resource_type=ResourceType.DISK,
                capacity=100.0,
                metadata={},
            )

    def allocate_resources(
        self, pipeline: Pipeline, **options
    ) -> Dict[str, ResourceAllocation]:
        """
        Allocate resources for pipeline.

        Args:
            pipeline: Pipeline object
            **options: Additional options:
                - cpu_cores: Number of CPU cores to allocate
                - memory_gb: Memory in GB to allocate
                - gpu_device: GPU device ID to allocate

        Returns:
            Dictionary of resource allocations
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="ResourceScheduler",
            message=f"Allocating resources for pipeline: {pipeline.name}",
        )

        try:
            allocations = {}

            with self.lock:
                # Allocate CPU
                cpu_cores = options.get("cpu_cores", 1)
                cpu_allocation = self.allocate_cpu(cpu_cores, pipeline.name)
                if cpu_allocation:
                    allocations["cpu"] = cpu_allocation

                # Allocate memory
                memory_gb = options.get("memory_gb", 1.0)
                memory_allocation = self.allocate_memory(memory_gb, pipeline.name)
                if memory_allocation:
                    allocations["memory"] = memory_allocation

                # Allocate GPU if requested
                if options.get("gpu_device") is not None:
                    gpu_allocation = self.allocate_gpu(
                        options["gpu_device"], pipeline.name
                    )
                    if gpu_allocation:
                        allocations["gpu"] = gpu_allocation

            # Validate allocations before returning
            if not allocations:
                # Clean up any allocated resources before raising error
                if allocations:
                    self.release_resources(allocations)
                raise ValidationError("No resources were allocated - insufficient capacity")

            # Update progress tracking outside of lock (after validation)
            self.progress_tracker.update_tracking(
                tracking_id, message="Allocating CPU resources..."
            )
            self.progress_tracker.update_tracking(
                tracking_id, message="Allocating memory resources..."
            )
            if options.get("gpu_device") is not None:
                self.progress_tracker.update_tracking(
                    tracking_id, message="Allocating GPU resources..."
                )
            
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Allocated {len(allocations)} resource(s) for pipeline: {pipeline.name}",
            )
            return allocations

        except Exception as e:
            # Clean up resources on any error
            if 'allocations' in locals() and allocations:
                self.release_resources(allocations)
            
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def allocate_cpu(
        self, cores: int, pipeline_id: str, step_name: Optional[str] = None
    ) -> Optional[ResourceAllocation]:
        """
        Allocate CPU cores.

        Args:
            cores: Number of CPU cores
            pipeline_id: Pipeline identifier
            step_name: Optional step name

        Returns:
            Resource allocation or None
        """
        resource = self.resources.get("cpu")
        if not resource:
            return None

        with self.lock:
            available = resource.capacity - resource.allocated
            if available >= cores:
                allocation_id = (
                    f"cpu_{pipeline_id}_{step_name or 'default'}_{time.time()}"
                )
                allocation = ResourceAllocation(
                    allocation_id=allocation_id,
                    resource_id="cpu",
                    resource_type=ResourceType.CPU,
                    amount=cores,
                    pipeline_id=pipeline_id,
                    step_name=step_name,
                )

                resource.allocated += cores
                self.allocations[allocation_id] = allocation

                self.logger.debug(f"Allocated {cores} CPU cores to {pipeline_id}")
                return allocation
            else:
                self.logger.warning(
                    f"Insufficient CPU resources: requested {cores}, available {available}"
                )
                return None

    def allocate_gpu(
        self, device_id: int, pipeline_id: str, step_name: Optional[str] = None
    ) -> Optional[ResourceAllocation]:
        """
        Allocate GPU device.

        Args:
            device_id: GPU device ID
            pipeline_id: Pipeline identifier
            step_name: Optional step name

        Returns:
            Resource allocation or None
        """
        # Check if GPU resource exists
        gpu_resource_id = f"gpu_{device_id}"
        if gpu_resource_id not in self.resources:
            # Initialize GPU resource
            self.resources[gpu_resource_id] = Resource(
                resource_id=gpu_resource_id,
                resource_type=ResourceType.GPU,
                capacity=1.0,
                metadata={"device_id": device_id},
            )

        resource = self.resources[gpu_resource_id]

        with self.lock:
            if resource.allocated < resource.capacity:
                allocation_id = (
                    f"gpu_{pipeline_id}_{step_name or 'default'}_{time.time()}"
                )
                allocation = ResourceAllocation(
                    allocation_id=allocation_id,
                    resource_id=gpu_resource_id,
                    resource_type=ResourceType.GPU,
                    amount=1.0,
                    pipeline_id=pipeline_id,
                    step_name=step_name,
                    metadata={"device_id": device_id},
                )

                resource.allocated += 1.0
                self.allocations[allocation_id] = allocation

                self.logger.debug(f"Allocated GPU {device_id} to {pipeline_id}")
                return allocation
            else:
                self.logger.warning(f"GPU {device_id} is already allocated")
                return None

    def allocate_memory(
        self, memory_gb: float, pipeline_id: str, step_name: Optional[str] = None
    ) -> Optional[ResourceAllocation]:
        """
        Allocate memory.

        Args:
            memory_gb: Memory in GB
            pipeline_id: Pipeline identifier
            step_name: Optional step name

        Returns:
            Resource allocation or None
        """
        resource = self.resources.get("memory")
        if not resource:
            return None

        with self.lock:
            available = resource.capacity - resource.allocated
            if available >= memory_gb:
                allocation_id = (
                    f"memory_{pipeline_id}_{step_name or 'default'}_{time.time()}"
                )
                allocation = ResourceAllocation(
                    allocation_id=allocation_id,
                    resource_id="memory",
                    resource_type=ResourceType.MEMORY,
                    amount=memory_gb,
                    pipeline_id=pipeline_id,
                    step_name=step_name,
                )

                resource.allocated += memory_gb
                self.allocations[allocation_id] = allocation

                self.logger.debug(f"Allocated {memory_gb} GB memory to {pipeline_id}")
                return allocation
            else:
                self.logger.warning(
                    f"Insufficient memory: requested {memory_gb} GB, available {available} GB"
                )
                return None

    def release_resources(self, allocations: Dict[str, ResourceAllocation]) -> None:
        """
        Release resource allocations.

        Args:
            allocations: Dictionary of resource allocations
        """
        with self.lock:
            for allocation in allocations.values():
                if allocation.allocation_id in self.allocations:
                    # Release resource
                    resource = self.resources.get(allocation.resource_id)
                    if resource:
                        resource.allocated -= allocation.amount
                        resource.allocated = max(0.0, resource.allocated)

                    # Remove allocation
                    del self.allocations[allocation.allocation_id]

                    self.logger.debug(f"Released resource: {allocation.resource_id}")

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        with self.lock:
            usage = {}
            for resource_id, resource in self.resources.items():
                usage[resource_id] = {
                    "capacity": resource.capacity,
                    "allocated": resource.allocated,
                    "available": resource.capacity - resource.allocated,
                    "utilization_percent": (
                        resource.allocated / resource.capacity * 100
                    )
                    if resource.capacity > 0
                    else 0.0,
                }

            return usage

    def optimize_resource_allocation(
        self, pipeline: Pipeline, **options
    ) -> Dict[str, Any]:
        """
        Optimize resource allocation for pipeline.

        Args:
            pipeline: Pipeline object
            **options: Additional options

        Returns:
            Optimization recommendations
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="pipeline",
            submodule="ResourceScheduler",
            message=f"Optimizing resource allocation for pipeline: {pipeline.name}",
        )

        try:
            # Analyze pipeline requirements
            self.progress_tracker.update_tracking(
                tracking_id, message="Analyzing pipeline requirements..."
            )
            step_count = len(pipeline.steps)

            # Calculate resource recommendations
            self.progress_tracker.update_tracking(
                tracking_id, message="Calculating resource recommendations..."
            )
            recommendations = {
                "cpu_cores": min(
                    step_count,
                    self.resources.get(
                        "cpu", Resource("", ResourceType.CPU, 0)
                    ).capacity,
                ),
                "memory_gb": step_count * 0.5,  # 0.5 GB per step
                "parallel_execution": step_count > 1,
            }

            result = {
                "recommendations": recommendations,
                "available_resources": self.get_resource_usage(),
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Optimization complete: {recommendations['cpu_cores']} CPU cores, {recommendations['memory_gb']} GB memory recommended",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise
