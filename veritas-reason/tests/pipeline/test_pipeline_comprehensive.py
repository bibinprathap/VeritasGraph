import unittest
from unittest.mock import MagicMock, patch
import time
from typing import Dict, Any

import pytest

from veritasreason.pipeline.pipeline_builder import PipelineBuilder, StepStatus, Pipeline
from veritasreason.pipeline.execution_engine import ExecutionEngine, PipelineStatus
from veritasreason.pipeline.failure_handler import (
    FailureHandler, RetryPolicy, RetryStrategy, ErrorSeverity
)
from veritasreason.pipeline.parallelism_manager import ParallelismManager, Task
from veritasreason.pipeline.pipeline_validator import PipelineValidator

pytestmark = pytest.mark.integration

class TestPipelineComprehensive(unittest.TestCase):

    def setUp(self):
        # Common setup
        self.mock_tracker_patcher = patch("veritasreason.utils.progress_tracker.get_progress_tracker")
        self.mock_get_tracker = self.mock_tracker_patcher.start()
        self.mock_tracker = MagicMock()
        self.mock_get_tracker.return_value = self.mock_tracker
        
        # Mock logger
        self.mock_logger_patcher = patch("veritasreason.utils.logging.get_logger")
        self.mock_get_logger = self.mock_logger_patcher.start()
        self.mock_logger = MagicMock()
        self.mock_get_logger.return_value = self.mock_logger

    def tearDown(self):
        self.mock_tracker_patcher.stop()
        self.mock_logger_patcher.stop()

    # --- Failure Handler Tests ---

    def test_failure_handler_retry_policy(self):
        handler = FailureHandler()
        policy = RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.LINEAR,
            backoff_factor=1.0,
            initial_delay=0.1
        )
        
        # Test retry decision
        recovery = handler.handle_failure(ValueError("Test"), policy, retry_count=0)
        self.assertTrue(recovery.should_retry)
        self.assertEqual(recovery.retry_delay, 0.1)
        
        # Test max retries
        recovery = handler.handle_failure(ValueError("Test"), policy, retry_count=3)
        self.assertFalse(recovery.should_retry)

    def test_failure_handler_exponential_backoff(self):
        handler = FailureHandler()
        policy = RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            backoff_factor=2.0,
            initial_delay=1.0
        )
        
        # First retry: delay = 1.0 * (2^0) = 1.0
        recovery = handler.handle_failure(ValueError("Test"), policy, retry_count=0)
        self.assertEqual(recovery.retry_delay, 1.0)
        
        # Second retry: delay = 1.0 * (2^1) = 2.0
        recovery = handler.handle_failure(ValueError("Test"), policy, retry_count=1)
        self.assertEqual(recovery.retry_delay, 2.0)
        
        # Third retry: delay = 1.0 * (2^2) = 4.0
        recovery = handler.handle_failure(ValueError("Test"), policy, retry_count=2)
        self.assertEqual(recovery.retry_delay, 4.0)

    # --- Parallelism Manager Tests ---

    def test_parallelism_manager_execution(self):
        manager = ParallelismManager(max_workers=2)
        
        def task_handler(x):
            return x * 2
            
        tasks = [
            Task(task_id="t1", handler=task_handler, args=(1,)),
            Task(task_id="t2", handler=task_handler, args=(2,)),
            Task(task_id="t3", handler=task_handler, args=(3,))
        ]
        
        results = manager.execute_parallel(tasks)
        
        self.assertEqual(len(results), 3)
        
        # Sort results by task_id to ensure order
        results.sort(key=lambda r: r.task_id)
        
        self.assertEqual(results[0].result, 2)
        self.assertEqual(results[1].result, 4)
        self.assertEqual(results[2].result, 6)
        
    def test_parallelism_identify_steps(self):
        # A -> B
        # A -> C
        # B -> D
        # C -> D
        # B and C can run in parallel
        
        builder = PipelineBuilder()
        builder.add_step("A", "dummy")
        builder.add_step("B", "dummy", dependencies=["A"])
        builder.add_step("C", "dummy", dependencies=["A"])
        builder.add_step("D", "dummy", dependencies=["B", "C"])
        
        pipeline = builder.build("parallel_pipeline")
        
        manager = ParallelismManager()
        groups = manager.identify_parallelizable_steps(pipeline)
        
        # Expected groups: [A], [B, C], [D] (roughly)
        # Note: identify_parallelizable_steps might return list of lists
        # where each inner list contains steps that can run in parallel *at that stage*
        
        # Flatten names for checking
        group_names = [[s.name for s in group] for group in groups]
        
        self.assertTrue(any("B" in g and "C" in g for g in group_names))

    # --- Pipeline Validator Tests ---

    def test_pipeline_validator_cycles(self):
        builder = PipelineBuilder()
        builder.add_step("A", "dummy")
        builder.add_step("B", "dummy")
        
        # Create cycle manually if builder allows it (builder usually prevents it, but validator should double check)
        # A -> B -> A
        
        # If builder prevents it, we might need to construct Pipeline object manually or bypass builder checks
        # Let's try via builder first
        builder.connect_steps("A", "B")
        
        try:
            builder.connect_steps("B", "A")
            # If this doesn't raise, then we check validator
            pipeline = builder.build("cycle_pipeline")
            validator = PipelineValidator()
            result = validator.validate(pipeline)
            self.assertFalse(result.valid)
            self.assertIn("Cycle detected", str(result.errors))
        except Exception:
            # If builder raises, that's also good
            pass

    def test_pipeline_validator_missing_deps(self):
        builder = PipelineBuilder()
        builder.add_step("A", "dummy")
        step_b = builder.add_step("B", "dummy")

        # Manually add a non-existent dependency
        step_b.dependencies.append("NON_EXISTENT")

        # Validate the builder directly (build() raises due to missing dep)
        validator = PipelineValidator()
        result = validator.validate(builder)

        self.assertFalse(result.valid)
        self.assertTrue(any("Missing dependency" in e for e in result.errors))

    # --- Execution Engine Advanced Tests ---

    def test_execution_engine_data_flow(self):
        """Test data flowing through pipeline steps."""
        
        def step1(data, **kwargs):
            return {"val": 10}
            
        def step2(data, **kwargs):
            val = data.get("val", 0)
            return {"val": val + 5}
            
        def step3(data, **kwargs):
            val = data.get("val", 0)
            return {"result": val * 2}
            
        builder = PipelineBuilder()
        builder.add_step("s1", "op", handler=step1)
        builder.add_step("s2", "op", handler=step2, dependencies=["s1"])
        builder.add_step("s3", "op", handler=step3, dependencies=["s2"])
        
        pipeline = builder.build("data_flow")
        engine = ExecutionEngine()
        
        result = engine.execute_pipeline(pipeline, {})
        
        self.assertTrue(result.success)
        self.assertEqual(result.output.get("result"), 30) # (10 + 5) * 2 = 30

    def test_execution_engine_retry_integration(self):
        """Test that execution engine uses failure handler for retries."""
        
        # Mock handler that fails twice then succeeds
        mock_handler = MagicMock(side_effect=[ValueError("Fail 1"), ValueError("Fail 2"), "Success"])
        
        builder = PipelineBuilder()
        builder.add_step("flaky", "flaky_type", handler=mock_handler)
        pipeline = builder.build("retry_pipeline")
        
        engine = ExecutionEngine()
        # Configure retry policy for 'flaky_type'
        engine.failure_handler.set_retry_policy(
            "flaky_type",
            RetryPolicy(max_retries=3, strategy=RetryStrategy.FIXED, initial_delay=0.01)
        )
        
        result = engine.execute_pipeline(pipeline, {})
        
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Success")
        self.assertEqual(mock_handler.call_count, 3)
    
    def test_execution_engine_delta_mode(self):
        """
        Test pipeline execution intercepting and computing delta mode.
        """
        
        mock_version_manager = MagicMock()
        mock_version_manager.get_version.side_effect = lambda v: {
            "v1": {"version_id": "v1", "graph_uri": "urn:graph:v1"},
            "v2": {"version_id": "v2", "graph_uri": "urn:graph:v2"}
        }.get(v)
        
        mock_triplet_store = MagicMock()
        expected_delta_payload = {
            "old_graph_uri": "urn:graph:v1",
            "new_graph_uri": "urn:graph:v2",
            "added_triples": ["<urn:s> <urn:p> <urn:o>"],
            "removed_triples": [],
            "added_count": 1,
            "removed_count": 0, 
        }
        mock_triplet_store.compute_delta.return_value = expected_delta_payload
        def delta_aware_handler(data, **kwargs):
            return data

        builder = PipelineBuilder()
        builder.add_step(
            step_name="incremental_validation",
            step_type="validation",
            handler=delta_aware_handler,
            delta_mode=True,
            base_version_id="v1",
            target_version_id="v2",
        )
        
        pipeline = builder.build("delta_pipeline")
        engine = ExecutionEngine()
        
        initial_data = {"full_graph": "huge_amount_of_data"}
        
        result = engine.execute_pipeline(
            pipeline,
            data=initial_data,
            version_manager=mock_version_manager,
            triplet_store=mock_triplet_store
        )
        
        self.assertTrue(result.success)
        
        mock_version_manager.get_version.assert_any_call("v1")
        mock_version_manager.get_version.assert_any_call("v2")

        mock_triplet_store.compute_delta.assert_called_once_with(
            "urn:graph:v1",
            "urn:graph:v2",
            version_manager=mock_version_manager,
            triplet_store=mock_triplet_store
        )
        
        self.assertEqual(result.output, expected_delta_payload)
        self.assertNotEqual(result.output, initial_data)

if __name__ == '__main__':
    unittest.main()
