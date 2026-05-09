"""
Regression test for ResourceScheduler deadlock fix.
Ensures RLock prevents deadlock in nested lock acquisition.
"""

import pytest
import threading
import time
from veritasreason.pipeline.resource_scheduler import ResourceScheduler
from veritasreason.pipeline.pipeline_builder import Pipeline
from veritasreason.utils.exceptions import ValidationError


class TestResourceSchedulerDeadlock:
    """Test ResourceScheduler deadlock prevention and allocation validation."""
    
    def test_rlock_prevents_deadlock(self):
        """Test that RLock prevents deadlock in allocate_resources."""
        scheduler = ResourceScheduler()
        pipeline = Pipeline("test_pipeline")
        
        # Verify RLock is used
        assert type(scheduler.lock).__name__ == "RLock"
        
        # This should complete without deadlock
        start_time = time.time()
        allocations = scheduler.allocate_resources(
            pipeline,
            cpu_cores=1,
            memory_gb=1.0
        )
        elapsed = time.time() - start_time
        
        # Should complete quickly (not hang)
        assert elapsed < 1.0
        assert len(allocations) == 2
        assert "cpu" in allocations
        assert "memory" in allocations
        
        # Clean up
        scheduler.release_resources(allocations)
    
    def test_allocation_validation_insufficient_resources(self):
        """Test validation when insufficient resources are available."""
        scheduler = ResourceScheduler()
        pipeline = Pipeline("test_pipeline")
        
        # Request more CPU than available - should get partial allocation
        allocations = scheduler.allocate_resources(
            pipeline,
            cpu_cores=1000,  # More than available
            memory_gb=1.0
        )
        
        # Should get memory allocation but not CPU
        assert "cpu" not in allocations
        assert "memory" in allocations
    
    def test_allocation_validation_no_resources(self):
        """Test validation when absolutely no resources can be allocated."""
        scheduler = ResourceScheduler()
        pipeline = Pipeline("test_pipeline")
        
        # Set all resources to zero capacity
        for resource in scheduler.resources.values():
            resource.capacity = 0.0
        
        # Should raise ValidationError when no resources allocated
        with pytest.raises(ValidationError, match="No resources were allocated"):
            scheduler.allocate_resources(
                pipeline,
                cpu_cores=1,
                memory_gb=1.0
            )
    
    def test_allocation_validation_partial_failure(self):
        """Test validation when only some resources can be allocated."""
        scheduler = ResourceScheduler()
        pipeline = Pipeline("test_pipeline")
        
        # Mock insufficient CPU but sufficient memory
        cpu_resource = scheduler.resources.get("cpu")
        if cpu_resource:
            cpu_resource.capacity = 0.1  # Very limited CPU
        
        # Should get partial allocation (memory only)
        allocations = scheduler.allocate_resources(
            pipeline,
            cpu_cores=1,  # More than available
            memory_gb=1.0
        )
        
        # Should get memory allocation but not CPU
        assert "cpu" not in allocations
        assert "memory" in allocations
    
    def test_reentrant_lock_behavior(self):
        """Test that the same thread can acquire lock multiple times."""
        scheduler = ResourceScheduler()
        
        # This should work with RLock
        def nested_lock_test():
            with scheduler.lock:
                with scheduler.lock:  # Nested acquisition
                    return True
        
        assert nested_lock_test() is True
    
    def test_gpu_allocation_with_rlock(self):
        """Test GPU allocation doesn't deadlock with RLock."""
        scheduler = ResourceScheduler()
        pipeline = Pipeline("test_pipeline")
        
        # Test GPU allocation (which also acquires lock)
        allocations = scheduler.allocate_resources(
            pipeline,
            cpu_cores=1,
            memory_gb=1.0,
            gpu_device=0
        )
        
        assert len(allocations) == 3
        assert "gpu" in allocations
        
        # Clean up
        scheduler.release_resources(allocations)
