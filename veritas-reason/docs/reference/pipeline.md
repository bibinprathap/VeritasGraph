# Pipeline

> **Robust orchestration engine for building, executing, and managing complex data processing workflows.**

---

## 🎯 Overview

The **Pipeline Module** provides a robust orchestration engine for building, executing, and managing complex data processing workflows. It enables you to create reusable, scalable pipelines with error handling, parallel execution, and resource management.

### What is Pipeline Orchestration?

**Pipeline orchestration** is the process of coordinating multiple processing steps into a workflow. The Pipeline module enables:
- **DAG Construction**: Build directed acyclic graphs (DAGs) of processing steps
- **Parallel Execution**: Run independent steps simultaneously
- **Error Handling**: Retry, fallback, and recovery strategies
- **Resource Management**: CPU and memory allocation
- **Progress Tracking**: Monitor pipeline execution

### Why Use the Pipeline Module?

- **Complex Workflows**: Coordinate multi-step data processing
- **Reusability**: Create reusable pipeline templates
- **Reliability**: Built-in error handling and retry logic
- **Performance**: Parallel execution for faster processing
- **Monitoring**: Track progress and performance
- **Scalability**: Handle large-scale data processing

### How It Works

1. **Pipeline Definition**: Define steps and their dependencies
2. **Validation**: Validate pipeline structure (no cycles, valid dependencies)
3. **Execution**: Execute steps in dependency order
4. **Parallelization**: Run independent steps in parallel
5. **Error Handling**: Retry failed steps, apply fallbacks
6. **Monitoring**: Track progress and resource usage

<div class="grid cards" markdown>

-   :material-pipe:{ .lg .middle } **Pipeline Builder**

    ---

    Fluent API for constructing complex DAG workflows

-   :material-play-circle:{ .lg .middle } **Execution Engine**

    ---

    Robust execution with status tracking and progress monitoring

-   :material-alert-circle-check:{ .lg .middle } **Error Handling**

    ---

    Configurable retry policies, fallbacks, and error recovery

-   :material-fast-forward:{ .lg .middle } **Parallel Execution**

    ---

    Execute independent steps in parallel for maximum performance

-   :material-cpu-64-bit:{ .lg .middle } **Resource Scheduling**

    ---

    Manage CPU/Memory allocation for resource-intensive tasks

-   :material-file-document-edit:{ .lg .middle } **Templates**

    ---

    Pre-built templates for common workflows (ETL, GraphRAG)

</div>

!!! tip "When to Use"
    - **ETL Workflows**: Ingest -> Parse -> Split -> Embed -> Store
    - **Graph Construction**: Extract Entities -> Extract Relations -> Build Graph
    - **Batch Processing**: Processing large volumes of documents reliably

---

## ⚙️ Algorithms Used

### Execution Management

**Purpose**: Manage pipeline execution order and state tracking.

**How it works**:

- **DAG Topological Sort**: Determines execution order of steps based on dependencies
- **State Management**: Tracks `` `PENDING` ``, `` `RUNNING` ``, `` `COMPLETED` ``, `` `FAILED` `` states
- **Checkpointing**: Saves intermediate results to allow resuming failed pipelines

### Parallelism

**Purpose**: Execute independent steps concurrently for maximum performance.

**How it works**:

- **ThreadPoolExecutor**: For I/O-bound tasks (network requests, DB writes)
- **ProcessPoolExecutor**: For CPU-bound tasks (parsing, embedding generation)
- **Dependency Resolution**: Identifies steps that can run concurrently

### Error Handling

**Purpose**: Robust error recovery with configurable retry policies.

**How it works**:

- **Exponential Backoff**: `` `wait = base * (factor ^ attempt)` ``
- **Jitter**: Randomization to prevent thundering herd problem
- **Circuit Breaker**: Stops execution after threshold failures to prevent cascading issues

### Resource Scheduling

**Purpose**: Manage CPU/Memory allocation for resource-intensive tasks.

**How it works**:

- **Token Bucket**: Rate limiting for API calls
- **Semaphore**: Concurrency limiting for resource constraints
- **Priority Queue**: Scheduling critical tasks first

---

## API Reference

### Types

- `Pipeline` — Pipeline definition dataclass
- `PipelineStep` — Pipeline step definition dataclass, Supports `delta_mode` (bool), `base_version_id` (str), and            `target_version_id` (str) for incremental processing.
- `StepStatus` — Enum: `pending`, `running`, `completed`, `failed`, `skipped`
- `ExecutionResult` — Execution result dataclass
- `PipelineStatus` — Enum: `pending`, `running`, `paused`, `completed`, `failed`, `stopped`
- `ValidationResult` — Validation result dataclass
- `RetryPolicy` — Retry policy dataclass
- `RetryStrategy` — Enum: `linear`, `exponential`, `fixed`
- `ErrorSeverity` — Enum: `low`, `medium`, `high`, `critical`
- `FailureRecovery` — Failure recovery dataclass
- `Task` — Parallel task dataclass
- `ParallelExecutionResult` — Parallel execution result dataclass
- `ResourceType` — Enum: `cpu`, `gpu`, `memory`, `disk`, `network`
- `Resource` — Resource definition dataclass
- `ResourceAllocation` — Resource allocation record dataclass

### PipelineBuilder

Fluent interface for constructing pipelines.

**Methods:**

- `add_step(step_name, step_type, **config)` — Add a step
- `connect_steps(from_step, to_step, **options)` — Add dependency
- `set_parallelism(level)` — Configure parallelism
- `build(name="default_pipeline")` — Build pipeline
- `build_pipeline(pipeline_config, **options)` — Build from dict
- `register_step_handler(step_type, handler)` — Register handler
- `get_step(step_name)` — Get step by name
- `serialize(format="json")` — Serialize builder state
- `validate_pipeline()` — Validate pipeline

**Example:**

```python
from veritasreason.pipeline import PipelineBuilder

builder = (
    PipelineBuilder()
    .add_step("ingest", "ingest", handler=ingest_handler)
    .add_step("parse", "parse", dependencies=["ingest"], handler=parse_handler)
    .add_step("embed", "embed", dependencies=["parse"], model="text-embedding-3-large")
    .set_parallelism(2)
)
pipeline = builder.build(name="MyPipeline")

step = builder.get_step("parse")
serialized = builder.serialize(format="json")
validation = builder.validate_pipeline()
```

### PipelineSerializer

Serialization utilities for pipelines.

**Methods:**

- `serialize_pipeline(pipeline, format="json")`
- `deserialize_pipeline(serialized_pipeline, **options)`
- `version_pipeline(pipeline, version_info)`

**Example:**

```python
from veritasreason.pipeline import PipelineBuilder, PipelineSerializer

builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1").build()

serializer = PipelineSerializer()
serialized = serializer.serialize_pipeline(pipeline, format="json")
restored = serializer.deserialize_pipeline(serialized)
versioned = serializer.version_pipeline(restored, {"version": "1.1"})
```

### ExecutionEngine

Executes pipelines and manages lifecycle.

**Methods:**

- `execute_pipeline(pipeline, data=None, **options)` — Run pipeline
- `pause_pipeline(pipeline_id)` — Pause execution
- `resume_pipeline(pipeline_id)` — Resume execution
- `stop_pipeline(pipeline_id)` — Stop execution
- `get_pipeline_status(pipeline_id)` — Get status
- `get_progress(pipeline_id)` — Get progress

**Example:**

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine(max_workers=4)
result = engine.execute_pipeline(pipeline, data={"path": "document.pdf"})

status = engine.get_pipeline_status(pipeline.name)
progress = engine.get_progress(pipeline.name)

engine.pause_pipeline(pipeline.name)
engine.resume_pipeline(pipeline.name)
engine.stop_pipeline(pipeline.name)
```

### Failure Handling

**Classes:** `FailureHandler`, `RetryHandler`, `FallbackHandler`, `ErrorRecovery`

**FailureHandler Methods:**

- `handle_step_failure(step, error, **options)`
- `classify_error(error)`
- `set_retry_policy(step_type, policy)`
- `get_retry_policy(step_type)`
- `retry_failed_step(step, error, **options)`
- `get_error_history(step_name=None)`
- `clear_error_history()`

**Example:**

```python
from veritasreason.pipeline import FailureHandler, RetryPolicy, RetryStrategy

handler = FailureHandler(default_max_retries=3, default_backoff_factor=2.0)
policy = RetryPolicy(max_retries=5, strategy=RetryStrategy.EXPONENTIAL, initial_delay=1.0)
handler.set_retry_policy("network", policy)

classification = handler.classify_error(RuntimeError("timeout"))
history_before = handler.get_error_history()
handler.clear_error_history()
```

### Parallelism

**Classes:** `ParallelismManager`, `ParallelExecutor`

**ParallelismManager Methods:**

- `execute_parallel(tasks, **options)`
- `execute_pipeline_steps_parallel(steps, data, **options)`
- `identify_parallelizable_steps(pipeline)`
- `optimize_parallel_execution(pipeline, available_workers)`

**Example:**

```python
from veritasreason.pipeline import ParallelismManager, Task, ParallelExecutor

def work(x):
    return x * 2

manager = ParallelismManager(max_workers=4)
tasks = [Task(task_id=f"t{i}", handler=work, args=(i,)) for i in range(4)]
results = manager.execute_parallel(tasks)

executor = ParallelExecutor(max_workers=2)
exec_results = executor.execute_parallel(tasks)
```

### Resources

**Class:** `ResourceScheduler`

**Methods:**

- `allocate_resources(pipeline, **options)`
- `allocate_cpu(cores, pipeline_id, step_name=None)`
- `allocate_memory(memory_gb, pipeline_id, step_name=None)`
- `allocate_gpu(device_id, pipeline_id, step_name=None)`
- `release_resources(allocations)`
- `get_resource_usage()`
- `optimize_resource_allocation(pipeline, **options)`

**Example:**

```python
from veritasreason.pipeline import ResourceScheduler, ResourceType

scheduler = ResourceScheduler()
cpu = scheduler.allocate_cpu(cores=2, pipeline_id="p1")
mem = scheduler.allocate_memory(memory_gb=1.0, pipeline_id="p1")
usage = scheduler.get_resource_usage()
scheduler.release_resources({cpu.allocation_id: cpu, mem.allocation_id: mem})
```

### Validation

**Class:** `PipelineValidator`

**Methods:**

- `validate_pipeline(pipeline_or_builder, **options)`
- `validate_step(step, **constraints)`
- `check_dependencies(pipeline_or_builder)`
- `validate_performance(pipeline, **options)`

**Example:**

```python
from veritasreason.pipeline import PipelineValidator, PipelineBuilder

builder = PipelineBuilder()
builder.add_step("a", "type")
builder.add_step("b", "type", dependencies=["a"])

validator = PipelineValidator()
result = validator.validate_pipeline(builder)
deps = validator.check_dependencies(builder)
perf = validator.validate_performance(builder.build())
```

### Templates

**Classes:** `PipelineTemplateManager`, `PipelineTemplate`

**PipelineTemplateManager Methods:**

- `get_template(template_name)`
- `create_pipeline_from_template(template_name, **overrides)`
- `register_template(template)`
- `list_templates(category=None)`
- `get_template_info(template_name)`

**Example:**

```python
from veritasreason.pipeline import PipelineTemplateManager

tm = PipelineTemplateManager()
names = tm.list_templates()
info = tm.get_template_info(names[0])
builder = tm.create_pipeline_from_template(names[0])
pipeline = builder.build()
```

---

## Configuration

### Environment Variables

```bash
export PIPELINE_MAX_WORKERS=4
export PIPELINE_DEFAULT_TIMEOUT=300
export PIPELINE_CHECKPOINT_DIR=./checkpoints
```

### YAML Configuration

This module does not include built-in YAML loaders. Use your own configuration system to populate arguments for `PipelineBuilder`, `ExecutionEngine`, and related classes.

---

## Integration Examples

### RAG-Style Pipeline

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

builder = (
    PipelineBuilder()
    .add_step("ingest", "ingest")
    .add_step("chunk", "chunk", dependencies=["ingest"])
    .add_step("embed", "embed", dependencies=["chunk"]) 
    .add_step("store_vectors", "store_vectors", dependencies=["embed"]) 
)

pipeline = builder.build(name="RAGPipeline")
engine = ExecutionEngine(max_workers=4)
result = engine.execute_pipeline(pipeline, data={"path": "document.pdf"})
```

---

### Incremental / Delta-Aware Pipeline

Use `delta_mode` to process only the differences between two graph versions, drastically reducing compute costs for large datasets.

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

builder = (
    PipelineBuilder()
    # Adding delta_mode=True tells the execution engine to intercept this step,
    # compute the diff between v1 and v2, and pass ONLY the delta payload to the handler.
    .add_step(
        "validate_diff",
        "validation",
        delta_mode=True,
        base_version_id="v1",
        target_version_id="v2",
        handler=diff_validator
    )
    .add_step(
        "alert_on_removals",
        "alerting",
        dependencies=["validate_diff"],
        handler=alert_handler
    )
)

pipeline = builder.build(name="IncrementalJob")
engine = ExecutionEngine()

# Execution requires version_manager and triplet_store injected via options
# so the engine can resolve URIs and compute the graph differences natively.
result = engine.execute_pipeline(
    pipeline,
    version_manager=my_version_manager,
    triplet_store=my_triplet_store
)
```

---

## Best Practices

1.  **Idempotency**: Ensure steps are idempotent (can be run multiple times without side effects) to support retries.
2.  **Granularity**: Keep steps focused on a single task. Smaller steps are easier to debug and retry.
3.  **Context Passing**: Use the execution context to pass metadata between steps, not just return values.
4.  **Error Handling**: Always define specific exceptions for retries; don't retry on `ValueError` or `TypeError`.

---

## Troubleshooting

**Issue**: Pipeline stuck in `RUNNING` state.
**Solution**: Check for deadlocks in dependency graph or infinite loops in steps. Use `timeout_seconds`.

**Issue**: `PickleError` during parallel execution.
**Solution**: Ensure all data passed between steps is serializable. Avoid passing open file handles or database connections.

---

## Cookbook

Interactive tutorials to learn pipeline orchestration:

- **[Pipeline Orchestration](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/advanced/07_Pipeline_Orchestration.ipynb)**: Build robust, automated data processing pipelines
  - **Topics**: Workflows, automation, error handling, pipeline orchestration, DAG construction
  - **Difficulty**: Advanced
  - **Use Cases**: Complex multi-step workflows, production pipelines, ETL processes

## See Also

- [Ingest Module](ingest.md) - Common first step
- [Split Module](split.md) - Common processing step
- [Vector Store Module](vector_store.md) - Common sink step

