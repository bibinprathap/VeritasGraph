# Pipeline and Orchestration Module Usage Guide

This comprehensive guide demonstrates how to use the pipeline and orchestration module for building, executing, validating, and managing complex data processing workflows with error handling, parallelism, resource scheduling, and pre-built templates.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Pipeline Building](#pipeline-building)
3. [Pipeline Execution](#pipeline-execution)
4. [Error Handling](#error-handling)
5. [Parallel Execution](#parallel-execution)
6. [Resource Scheduling](#resource-scheduling)
7. [Pipeline Validation](#pipeline-validation)
8. [Pipeline Templates](#pipeline-templates)
9. [Algorithms and Methods](#algorithms-and-methods)
10. [Configuration](#configuration)
11. [Advanced Examples](#advanced-examples)

## Basic Usage

### Using the PipelineBuilder

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

# Create pipeline builder
builder = PipelineBuilder()

# Add steps to pipeline
pipeline = builder.add_step("ingest", "file_ingest", source="./documents") \
                  .add_step("parse", "document_parse", formats=["pdf", "docx"]) \
                  .add_step("normalize", "text_normalize") \
                  .build()

# Execute pipeline
engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)

print(f"Pipeline executed: {result.success}")
print(f"Output: {result.output}")
```

### Using Main Classes

```python
from veritasreason.pipeline import (
    PipelineBuilder,
    ExecutionEngine,
    FailureHandler,
    ParallelismManager,
    ResourceScheduler
)

# Create components
builder = PipelineBuilder()
engine = ExecutionEngine(max_workers=4)
failure_handler = FailureHandler()
parallelism_manager = ParallelismManager(max_workers=4)
resource_scheduler = ResourceScheduler()

# Build and execute
pipeline = builder.add_step("step1", "type1").build()
result = engine.execute_pipeline(pipeline)
```

## Pipeline Building

### Basic Pipeline Construction

```python
from veritasreason.pipeline import PipelineBuilder

# Create builder
builder = PipelineBuilder()

# Add steps sequentially
pipeline = builder.add_step("ingest", "ingest", source="documents/") \
                  .add_step("parse", "parse", formats=["pdf"]) \
                  .add_step("extract", "extract", entities=True) \
                  .build()

print(f"Pipeline: {pipeline.name}")
print(f"Steps: {len(pipeline.steps)}")
```

### Step Dependencies

```python
from veritasreason.pipeline import PipelineBuilder

builder = PipelineBuilder()

# Add steps with dependencies
pipeline = builder.add_step("ingest", "ingest", source="documents/") \
                  .add_step("parse", "parse", dependencies=["ingest"]) \
                  .add_step("normalize", "normalize", dependencies=["parse"]) \
                  .add_step("extract", "extract", dependencies=["normalize"]) \
                  .build()

# Steps will execute in dependency order
```

### Step Configuration

```python
from veritasreason.pipeline import PipelineBuilder

builder = PipelineBuilder()

# Add step with detailed configuration
pipeline = builder.add_step(
    "embed",
    "embed",
    model="text-embedding-3-large",
    batch_size=32,
    max_length=512,
    dependencies=["extract"]
).build()
```

### Connecting Steps Explicitly

```python
from veritasreason.pipeline import PipelineBuilder

builder = PipelineBuilder()

# Add steps
builder.add_step("step1", "type1")
builder.add_step("step2", "type2")
builder.add_step("step3", "type3")

# Connect steps explicitly
builder.connect_steps("step1", "step2")
builder.connect_steps("step2", "step3")

pipeline = builder.build()
```

### Pipeline Serialization

```python
from veritasreason.pipeline import PipelineBuilder, PipelineSerializer

builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1").build()

serializer = PipelineSerializer()
serialized = serializer.serialize_pipeline(pipeline, format="json")
restored = serializer.deserialize_pipeline(serialized)
```

### Pipeline Metadata

```python
from veritasreason.pipeline import PipelineBuilder

builder = PipelineBuilder()

# Build pipeline with metadata
pipeline = builder.add_step("step1", "type1") \
                  .build(name="MyPipeline", 
                        metadata={"version": "1.0", "author": "User"})

print(f"Pipeline metadata: {pipeline.metadata}")
```

## Pipeline Execution

### Basic Execution

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

# Build pipeline
builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1").build()

# Execute pipeline
engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)

if result.success:
    print(f"Execution successful: {result.output}")
else:
    print(f"Execution failed: {result.errors}")
```

### Execution with Input Data

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine()

# Execute with input data
input_data = {"documents": ["doc1.pdf", "doc2.pdf"]}
result = engine.execute_pipeline(pipeline, data=input_data)

print(f"Output: {result.output}")
print(f"Metrics: {result.metrics}")
```

### Status Tracking

```python
from veritasreason.pipeline import ExecutionEngine, PipelineStatus

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)

status = engine.get_pipeline_status(pipeline.name)
print(status.value)
```

### Progress Monitoring

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)

progress = engine.get_progress(pipeline.name)
print(progress["progress_percentage"])  # float 0..100
print(progress["completed_steps"])      # int
print(progress["total_steps"])          # int
print(progress["status"])               # status string
```

### Pause and Resume

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)

engine.pause_pipeline(pipeline.name)
engine.resume_pipeline(pipeline.name)
engine.stop_pipeline(pipeline.name)
```

### Execution Metrics

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)

metrics = result.metrics
print(metrics.get("execution_time", 0))
print(metrics.get("steps_executed", 0))
print(metrics.get("steps_failed", 0))
```

## Error Handling

### Basic Error Handling

```python
from veritasreason.pipeline import FailureHandler, RetryPolicy, RetryStrategy

handler = FailureHandler()
policy = RetryPolicy(max_retries=3, strategy=RetryStrategy.EXPONENTIAL, initial_delay=1.0)

try:
    result = step.handler({})
except Exception as e:
    recovery = handler.handle_step_failure(step, e)
    if recovery["retry"]:
        print(recovery["retry_delay"])  # seconds
```

### Retry Strategies

```python
from veritasreason.pipeline import RetryPolicy, RetryStrategy

# Exponential backoff (default)
exponential_policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL,
    initial_delay=1.0,
    backoff_factor=2.0
)
# Delays: 1s, 2s, 4s, 8s...

# Linear backoff
linear_policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.LINEAR,
    initial_delay=1.0,
    backoff_factor=1.0
)
# Delays: 1s, 2s, 3s, 4s...

# Fixed delay
fixed_policy = RetryPolicy(
    max_retries=3,
    strategy=RetryStrategy.FIXED,
    initial_delay=2.0
)
# Delays: 2s, 2s, 2s, 2s...
```

### Error Classification

```python
from veritasreason.pipeline import FailureHandler, ErrorSeverity

handler = FailureHandler()
classification = handler.classify_error(Exception("Connection timeout"))

print(classification["severity"])   # ErrorSeverity
print(classification["error_type"]) # str
print(classification["message"])    # str
```

### Fallback Handlers

```python
from veritasreason.pipeline import FallbackHandler

fallback = FallbackHandler()
fallback.set_fallback_strategy("retry")
strategy = fallback.handle_service_failure("vector_store")
```

### Error Recovery

```python
from veritasreason.pipeline import ErrorRecovery

recovery = ErrorRecovery()
result = recovery.recover_from_error(Exception("Temporary failure"), {"step": "s1"})
print(result["recovery_action"])  
```

### Custom Retry Policies

```python
from veritasreason.pipeline import FailureHandler, RetryPolicy, RetryStrategy

handler = FailureHandler()
custom_policy = RetryPolicy(max_retries=5, strategy=RetryStrategy.EXPONENTIAL, initial_delay=0.5)
handler.set_retry_policy("network_step", custom_policy)
```

## Parallel Execution

### Basic Parallel Execution

```python
from veritasreason.pipeline import ParallelismManager, Task

# Create parallelism manager
manager = ParallelismManager(max_workers=4)

# Define tasks
def process_document(doc_id):
    return f"Processed {doc_id}"

tasks = [
    Task("task1", process_document, args=("doc1",)),
    Task("task2", process_document, args=("doc2",)),
    Task("task3", process_document, args=("doc3",)),
    Task("task4", process_document, args=("doc4",))
]

# Execute tasks in parallel
results = manager.execute_parallel(tasks)

for result in results:
    if result.success:
        print(f"{result.task_id}: {result.result}")
    else:
        print(f"{result.task_id} failed: {result.error}")
```

### Task Priority

```python
from veritasreason.pipeline import ParallelismManager, Task

manager = ParallelismManager(max_workers=2)

# Tasks with different priorities
tasks = [
    Task("high_priority", handler, args=(), priority=10),
    Task("medium_priority", handler, args=(), priority=5),
    Task("low_priority", handler, args=(), priority=1)
]

# Higher priority tasks execute first
results = manager.execute_parallel(tasks)
```

### Thread vs Process Execution

```python
from veritasreason.pipeline import ParallelismManager

# Thread-based execution (default)
thread_manager = ParallelismManager(max_workers=4, use_processes=False)

# Process-based execution (for CPU-intensive tasks)
process_manager = ParallelismManager(max_workers=4, use_processes=True)

# Execute with threads
thread_results = thread_manager.execute_parallel(tasks)

# Execute with processes
process_results = process_manager.execute_parallel(tasks)
```

### Parallel Pipeline Steps

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine(max_workers=4)

# Build pipeline with parallelizable steps
builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1") \
                  .add_step("step2", "type2", dependencies=["step1"]) \
                  .add_step("step3", "type3", dependencies=["step1"]) \
                  .add_step("step4", "type4", dependencies=["step2", "step3"]) \
                  .build()

# Steps 2 and 3 will execute in parallel
result = engine.execute_pipeline(pipeline)
```

### Load Balancing

```python
from veritasreason.pipeline import ParallelismManager

manager = ParallelismManager(max_workers=4)

# Tasks with varying execution times
tasks = [
    Task("quick_task", quick_handler, args=()),
    Task("slow_task", slow_handler, args=()),
    Task("medium_task", medium_handler, args=())
]

# Manager automatically balances load across workers
results = manager.execute_parallel(tasks)
```

## Resource Scheduling

### Basic Resource Allocation

```python
from veritasreason.pipeline import ResourceScheduler

scheduler = ResourceScheduler()
cpu = scheduler.allocate_cpu(cores=2, pipeline_id="p1")
mem = scheduler.allocate_memory(memory_gb=1.0, pipeline_id="p1")
usage = scheduler.get_resource_usage()
scheduler.release_resources({cpu.allocation_id: cpu, mem.allocation_id: mem})
```

### Resource Types

```python
from veritasreason.pipeline import ResourceScheduler, ResourceType

scheduler = ResourceScheduler()
cpu = scheduler.allocate_cpu(2, "p1")
gpu = scheduler.allocate_gpu(0, "p1")
mem = scheduler.allocate_memory(8.0, "p1")
```

### Resource Monitoring

```python
from veritasreason.pipeline import ResourceScheduler

scheduler = ResourceScheduler()
usage = scheduler.get_resource_usage()
print(usage["cpu"]["capacity"])
print(usage["cpu"]["allocated"])
print(usage["cpu"]["available"])
```

### Resource Deallocation

```python
from veritasreason.pipeline import ResourceScheduler

scheduler = ResourceScheduler()
cpu = scheduler.allocate_cpu(2, "p1")
scheduler.release_resources({cpu.allocation_id: cpu})
```

### Automatic Resource Management

```python
from veritasreason.pipeline import ExecutionEngine

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline, cpu_cores=2, memory_gb=1.0)
```

## Pipeline Validation

### Basic Validation

```python
from veritasreason.pipeline import PipelineBuilder, PipelineValidator

# Build pipeline
builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1").build()

# Validate pipeline
validator = PipelineValidator()
result = validator.validate_pipeline(pipeline)

if result.valid:
    print("Pipeline is valid!")
else:
    print(f"Validation errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

### Dependency Validation

```python
from veritasreason.pipeline import PipelineValidator

validator = PipelineValidator()

# Validate dependencies
result = validator.validate_pipeline(pipeline)

# Check for circular dependencies
if "circular_dependency" in result.errors:
    print("Circular dependency detected!")

# Check for missing dependencies
if "missing_dependency" in result.errors:
    print("Missing dependency detected!")
```

### Structure Validation

```python
from veritasreason.pipeline import PipelineValidator

validator = PipelineValidator()

# Validate pipeline structure
result = validator.validate_pipeline(pipeline)

# Check structure issues
if result.valid:
    print("Pipeline structure is valid")
else:
    for error in result.errors:
        if "structure" in error.lower():
            print(f"Structure error: {error}")
```

### Performance Validation

```python
from veritasreason.pipeline import PipelineValidator

validator = PipelineValidator()
perf = validator.validate_performance(pipeline)
print(perf["warnings"])  
```

## Pipeline Templates

### Using Pre-built Templates

```python
from veritasreason.pipeline import PipelineTemplateManager, ExecutionEngine

# Create template manager
template_manager = PipelineTemplateManager()

# Get available templates
templates = template_manager.list_templates()
print(f"Available templates: {templates}")

# Create pipeline from template
builder = template_manager.create_pipeline_from_template(
    "document_processing",
    ingest={"source": "./documents"},
    parse={"formats": ["pdf", "docx"]}
)

pipeline = builder.build()

# Execute pipeline
engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)
```

### Document Processing Template

```python
from veritasreason.pipeline import PipelineTemplateManager

template_manager = PipelineTemplateManager()

# Create document processing pipeline
builder = template_manager.create_pipeline_from_template("document_processing")
pipeline = builder.build()

# Template includes: ingest → parse → normalize → extract → embed → build_kg
```

### RAG Pipeline Template

```python
from veritasreason.pipeline import PipelineTemplateManager

template_manager = PipelineTemplateManager()

# Create RAG pipeline
builder = template_manager.create_pipeline_from_template(
    "rag_pipeline",
    chunk={"chunk_size": 512},
    embed={"model": "text-embedding-3-large"},
    store_vectors={"store": "weaviate"}
)

pipeline = builder.build()
```

### Knowledge Graph Construction Template

```python
from veritasreason.pipeline import PipelineTemplateManager

template_manager = PipelineTemplateManager()

# Create KG construction pipeline
builder = template_manager.create_pipeline_from_template("kg_construction")
pipeline = builder.build()

# Template includes: ingest → extract_entities → extract_relations → deduplicate → resolve_conflicts → build_graph
```

### Custom Templates

```python
from veritasreason.pipeline import PipelineTemplateManager, PipelineTemplate

template_manager = PipelineTemplateManager()

# Create custom template
custom_template = PipelineTemplate(
    name="custom_pipeline",
    description="Custom processing pipeline",
    steps=[
        {"name": "step1", "type": "type1", "config": {}},
        {"name": "step2", "type": "type2", "config": {}, "dependencies": ["step1"]}
    ],
    config={"parallelism": 2},
    metadata={"category": "custom"}
)

# Register template
template_manager.register_template(custom_template)

# Use custom template
builder = template_manager.create_pipeline_from_template("custom_pipeline")
```

### Template Information

```python
from veritasreason.pipeline import PipelineTemplateManager

template_manager = PipelineTemplateManager()

# Get template information
info = template_manager.get_template_info("document_processing")
print(f"Name: {info['name']}")
print(f"Description: {info['description']}")
print(f"Steps: {info['step_count']}")
print(f"Config: {info['config']}")

# List templates by category
rag_templates = template_manager.list_templates(category="rag")
print(f"RAG templates: {rag_templates}")
```

## Algorithms and Methods

### Pipeline Execution Algorithms

#### Topological Sort (Dependency Resolution)
The pipeline execution engine uses topological sorting to determine the correct execution order of steps based on their dependencies.

**Algorithm**: Kahn's Algorithm or DFS-based Topological Sort
- Build dependency graph from step dependencies
- Calculate in-degree for each step
- Process steps with zero in-degree first
- Update in-degrees as steps complete
- Detect cycles (circular dependencies)

```python
# Example: Steps with dependencies
# step1 → step2 → step4
# step1 → step3 → step4
# Execution order: step1, [step2, step3] (parallel), step4
```

#### Step Scheduling
Priority-based scheduling with dependency awareness:
- Priority queue for ready steps
- Dependency tracking for step readiness
- Parallel execution of independent steps
- Sequential execution for dependent steps

#### Status Management
State machine for pipeline and step status:
- **Pending**: Step is queued but not started
- **Running**: Step is currently executing
- **Completed**: Step finished successfully
- **Failed**: Step encountered an error
- **Skipped**: Step was skipped due to conditions

#### Progress Tracking
Incremental progress calculation:
- Track completed steps vs total steps
- Calculate percentage completion
- Estimate remaining time based on average step duration
- Update progress in real-time

### Failure Handling Algorithms

#### Retry Strategies

**Exponential Backoff**:
- Delay = initial_delay × (backoff_factor ^ attempt_number)
- Example: initial_delay=1s, backoff_factor=2 → delays: 1s, 2s, 4s, 8s, 16s
- Maximum delay capped at max_delay

**Linear Backoff**:
- Delay = initial_delay × (1 + attempt_number × backoff_factor)
- Example: initial_delay=1s, backoff_factor=1 → delays: 1s, 2s, 3s, 4s, 5s

**Fixed Delay**:
- Constant delay between retries
- Example: initial_delay=2s → delays: 2s, 2s, 2s, 2s

#### Error Classification
Severity-based error classification:
- **Low**: Non-critical errors, can be ignored or logged
- **Medium**: Errors that may affect functionality
- **High**: Errors that significantly impact execution
- **Critical**: Errors that require immediate attention

Error classification uses pattern matching and exception type analysis.

#### Recovery Mechanisms
- **Automatic Retry**: Retry failed steps based on retry policy
- **Fallback Handlers**: Execute alternative logic when primary fails
- **Rollback**: Undo completed steps when failure occurs
- **Error Propagation**: Bubble errors up through pipeline hierarchy

### Parallel Execution Algorithms

#### Task Parallelization
- **ThreadPoolExecutor**: For I/O-bound tasks (default)
- **ProcessPoolExecutor**: For CPU-intensive tasks
- Task distribution using priority queue
- Load balancing across available workers

#### Dependency Resolution for Parallel Execution
- Identify independent steps (no dependencies)
- Group steps by dependency level
- Execute steps in same level in parallel
- Wait for dependencies before executing dependent steps

#### Load Balancing
- Priority-based task distribution
- Round-robin scheduling for equal priority tasks
- Dynamic load adjustment based on worker availability
- Task queue management with thread-safe operations

### Resource Scheduling Algorithms

#### Resource Allocation Strategies

**First-Fit Allocation**:
- Allocate to first available resource that meets requirements
- Fast allocation, may not be optimal

**Best-Fit Allocation**:
- Allocate to resource with smallest available capacity that fits
- Better resource utilization, slightly slower

**Priority-Based Allocation**:
- Allocate based on pipeline/step priority
- Higher priority tasks get resources first

#### Capacity Management
- Track total capacity vs allocated capacity
- Calculate available capacity in real-time
- Prevent overallocation (capacity exceeded)
- Resource reservation for critical steps

#### Scheduling Algorithms
- **FIFO (First-In-First-Out)**: Simple queue-based scheduling
- **Priority Scheduling**: Execute based on priority levels
- **Fair-Share Scheduling**: Distribute resources fairly across pipelines
- **Deadline-Based Scheduling**: Prioritize tasks with earlier deadlines

### Pipeline Validation Algorithms

#### Cycle Detection (Circular Dependencies)
**Algorithm**: Depth-First Search (DFS)
- Build adjacency list from dependencies
- Use DFS to detect back edges
- Back edge indicates cycle
- Report all cycles found

#### Topological Validation
- Verify that dependency graph is acyclic
- Check that all dependencies exist
- Validate dependency chains are complete
- Ensure no orphaned steps

#### Structure Validation
- Verify step connectivity
- Check for unreachable steps
- Validate step configuration
- Ensure required fields are present

#### Performance Estimation
- Estimate execution time based on step types
- Calculate resource requirements
- Identify potential bottlenecks
- Suggest optimizations

### Methods

#### PipelineBuilder Methods

- `add_step(step_name, step_type, **config)`: Add step to pipeline
- `connect_steps(from_step, to_step, **options)`: Connect two steps
- `set_parallelism(level)`: Set parallelism level
- `build(name="default_pipeline")`: Build pipeline from steps
- `build_pipeline(pipeline_config, **options)`: Build pipeline from dict
- `register_step_handler(step_type, handler)`: Register handler
- `get_step(step_name)`: Get step by name
- `serialize(format="json")`: Serialize builder state
- `validate_pipeline()`: Validate pipeline structure

#### ExecutionEngine Methods

- `execute_pipeline(pipeline, data=None, **options)`: Execute pipeline
- `get_pipeline_status(pipeline_id)`: Get pipeline execution status
- `get_progress(pipeline_id)`: Get execution progress
- `pause_pipeline(pipeline_id)`: Pause pipeline execution
- `resume_pipeline(pipeline_id)`: Resume pipeline execution
- `stop_pipeline(pipeline_id)`: Stop pipeline execution

#### FailureHandler Methods

- `handle_step_failure(step, error, **options)`: Handle step failure
- `classify_error(error)`: Classify error severity and type
- `set_retry_policy(step_type, policy)`: Set retry policy for step type
- `get_retry_policy(step_type)`: Get retry policy for step type
- `retry_failed_step(step, error, **options)`: Retry failed step
- `get_error_history(step_name=None)`: Get error history
- `clear_error_history()`: Clear error history

#### ParallelismManager Methods

- `execute_parallel(tasks, **options)`: Execute tasks in parallel
- `execute_pipeline_steps_parallel(steps, data, **options)`: Execute pipeline steps in parallel
- `identify_parallelizable_steps(pipeline)`: Identify parallelizable groups
- `optimize_parallel_execution(pipeline, available_workers)`: Optimize plan

#### ResourceScheduler Methods

- `allocate_resources(pipeline, **options)`: Allocate CPU/memory/GPU
- `allocate_cpu(cores, pipeline_id, step_name=None)`: Allocate CPU cores
- `allocate_memory(memory_gb, pipeline_id, step_name=None)`: Allocate memory
- `allocate_gpu(device_id, pipeline_id, step_name=None)`: Allocate GPU device
- `release_resources(allocations)`: Release allocations
- `get_resource_usage()`: Current resource usage
- `optimize_resource_allocation(pipeline, **options)`: Recommendations

#### PipelineValidator Methods

- `validate_pipeline(pipeline_or_builder, **options)`: Validate entire pipeline
- `check_dependencies(pipeline_or_builder)`: Validate dependencies
- `validate_step(step, **constraints)`: Validate a step
- `validate_performance(pipeline, **options)`: Estimate performance

#### PipelineTemplateManager Methods

- `get_template(template_name)`: Get template by name
- `create_pipeline_from_template(template_name, **overrides)`: Create pipeline from template
- `register_template(template)`: Register custom template
- `list_templates(category)`: List available templates
- `get_template_info(template_name)`: Get template information

## Configuration

### Environment Variables

```bash
# Pipeline execution configuration
export PIPELINE_MAX_WORKERS=4
export PIPELINE_RETRY_ON_FAILURE=true
export PIPELINE_DEFAULT_MAX_RETRIES=3
export PIPELINE_DEFAULT_BACKOFF_FACTOR=2.0
export PIPELINE_DEFAULT_INITIAL_DELAY=1.0
export PIPELINE_DEFAULT_MAX_DELAY=60.0

# Resource scheduling configuration
export PIPELINE_MAX_CPU_CORES=8
export PIPELINE_MAX_MEMORY_GB=16
export PIPELINE_ENABLE_GPU=false

# Parallelism configuration
export PIPELINE_USE_PROCESSES=false
export PIPELINE_PARALLELISM_LEVEL=2
```

### Programmatic Configuration

```python
from veritasreason.pipeline import ExecutionEngine, FailureHandler, ParallelismManager

engine = ExecutionEngine(max_workers=4)
failure_handler = FailureHandler(default_max_retries=3, default_backoff_factor=2.0)
parallelism_manager = ParallelismManager(max_workers=4, use_processes=False)
```

### Configuration File (YAML)

```yaml
# config.yaml
pipeline:
  max_workers: 4
  retry_on_failure: true
  default_max_retries: 3
  default_backoff_factor: 2.0
  default_initial_delay: 1.0
  default_max_delay: 60.0

pipeline_resources:
  max_cpu_cores: 8
  max_memory_gb: 16
  enable_gpu: false

pipeline_parallelism:
  use_processes: false
  parallelism_level: 2

pipeline_templates:
  document_processing:
    parallelism: 2
  rag_pipeline:
    parallelism: 4
```



## Advanced Examples

### Complete Document Processing Pipeline

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

# Create components
builder = PipelineBuilder()
engine = ExecutionEngine(max_workers=4)

# Build complete pipeline
pipeline = builder.add_step(
    "ingest",
    "ingest",
    source="./documents",
    recursive=True
).add_step(
    "parse",
    "parse",
    formats=["pdf", "docx", "txt"],
    dependencies=["ingest"]
).add_step(
    "normalize",
    "normalize",
    case="lower",
    unicode_form="NFC",
    dependencies=["parse"]
).add_step(
    "extract",
    "extract",
    entities=True,
    relations=True,
    dependencies=["normalize"]
).add_step(
    "embed",
    "embed",
    model="text-embedding-3-large",
    batch_size=32,
    dependencies=["extract"]
).add_step(
    "build_kg",
    "build_kg",
    merge_entities=True,
    resolve_conflicts=True,
    dependencies=["extract", "embed"]
).build(name="DocumentProcessingPipeline")

# Execute pipeline
result = engine.execute_pipeline(pipeline)

if result.success:
    print(f"Pipeline completed successfully!")
    print(f"Processed documents: {result.metrics.get('documents_processed', 0)}")
    print(f"Entities extracted: {result.metrics.get('entities_extracted', 0)}")
    print(f"Relations extracted: {result.metrics.get('relations_extracted', 0)}")
else:
    print(f"Pipeline failed: {result.errors}")
```

### Pipeline with Error Handling and Retries

```python
from veritasreason.pipeline import (
    PipelineBuilder,
    ExecutionEngine,
    FailureHandler,
    RetryPolicy,
    RetryStrategy
)

# Configure retry policy
retry_policy = RetryPolicy(
    max_retries=5,
    strategy=RetryStrategy.EXPONENTIAL,
    initial_delay=1.0,
    backoff_factor=2.0,
    max_delay=60.0,
    retryable_errors=[ConnectionError, TimeoutError]
)

failure_handler = FailureHandler()
failure_handler.set_retry_policy("network_step", retry_policy)

# Build pipeline
builder = PipelineBuilder()
pipeline = builder.add_step(
    "fetch_data",
    "network_step",
    url="https://api.example.com/data"
).add_step(
    "process_data",
    "process",
    dependencies=["fetch_data"]
).build()

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)
```

### Parallel Execution Pipeline

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

# Build pipeline with parallel steps
builder = PipelineBuilder()
pipeline = builder.add_step("ingest", "ingest", source="./documents") \
                  .add_step("parse1", "parse", file="doc1.pdf", dependencies=["ingest"]) \
                  .add_step("parse2", "parse", file="doc2.pdf", dependencies=["ingest"]) \
                  .add_step("parse3", "parse", file="doc3.pdf", dependencies=["ingest"]) \
                  .add_step("merge", "merge", dependencies=["parse1", "parse2", "parse3"]) \
                  .build()

# Execute with parallelism
engine = ExecutionEngine(max_workers=4)
result = engine.execute_pipeline(pipeline)

# parse1, parse2, parse3 will execute in parallel
```

### Resource-Aware Pipeline Execution

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

builder = PipelineBuilder()
pipeline = builder.add_step("step1", "cpu_intensive") \
                  .add_step("step2", "memory_intensive", dependencies=["step1"]) \
                  .build()

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline, cpu_cores=4, memory_gb=8)
```

### Template-Based Pipeline Creation

```python
from veritasreason.pipeline import PipelineTemplateManager, ExecutionEngine

# Create template manager
template_manager = PipelineTemplateManager()

# Create RAG pipeline from template
builder = template_manager.create_pipeline_from_template(
    "rag_pipeline",
    ingest={"source": "./documents"},
    chunk={"chunk_size": 512, "overlap": 50},
    embed={"model": "text-embedding-3-large", "batch_size": 32},
    # Step-specific overrides
    store_vectors={"store": "weaviate", "index_name": "documents"}
)

pipeline = builder.build()

# Execute pipeline
engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)
```

### Pipeline with Progress Monitoring

```python
from veritasreason.pipeline import PipelineBuilder, ExecutionEngine

# Build pipeline
builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1") \
                  .add_step("step2", "type2") \
                  .add_step("step3", "type3") \
                  .build()

engine = ExecutionEngine()
result = engine.execute_pipeline(pipeline)
status = engine.get_pipeline_status(pipeline.name)
progress = engine.get_progress(pipeline.name)
```

### Pipeline Serialization and Persistence

```python
from veritasreason.pipeline import PipelineBuilder, PipelineSerializer

builder = PipelineBuilder()
pipeline = builder.add_step("step1", "type1").build()

serializer = PipelineSerializer()
serialized = serializer.serialize_pipeline(pipeline, format="json")
restored = serializer.deserialize_pipeline(serialized)
```

### Custom Step Handlers

```python
from veritasreason.pipeline import PipelineBuilder, PipelineStep

# Define custom step handler
def custom_handler(step, data, **kwargs):
    print(f"Executing custom step: {step.name}")
    # Custom processing logic
    result = process_data(data)
    return result

# Build pipeline with custom handler
builder = PipelineBuilder()
step = PipelineStep(
    name="custom_step",
    step_type="custom",
    handler=custom_handler
)

pipeline = builder.add_step("custom_step", "custom", handler=custom_handler).build()
```

## Best Practices

1. **Pipeline Design**: 
   - Keep steps focused and single-purpose
   - Minimize dependencies when possible
   - Design for parallel execution where applicable
   - Use clear, descriptive step names

2. **Error Handling**:
   - Always configure retry policies for network operations
   - Use appropriate retry strategies (exponential for transient errors)
   - Implement fallback handlers for critical steps
   - Log all errors with sufficient context

3. **Resource Management**:
   - Monitor resource usage during execution
   - Deallocate resources promptly after use
   - Use appropriate resource types for tasks
   - Set realistic resource limits

4. **Parallel Execution**:
   - Identify independent steps for parallelization
   - Use threads for I/O-bound tasks
   - Use processes for CPU-intensive tasks
   - Balance parallelism with resource constraints

5. **Validation**:
   - Always validate pipelines before execution
   - Check for circular dependencies
   - Verify step configurations
   - Test with sample data first

6. **Templates**:
   - Use pre-built templates when possible
   - Customize templates for specific needs
   - Document custom templates
   - Share templates across teams

7. **Performance**:
   - Monitor execution metrics
   - Optimize slow steps
   - Use caching where appropriate
   - Profile pipeline execution

8. **Configuration**:
   - Use configuration files for consistency
   - Set appropriate retry policies
   - Configure resource limits
   - Document configuration choices

9. **Testing**:
   - Test pipelines with small datasets first
   - Validate error handling paths
   - Test parallel execution
   - Verify resource cleanup

10. **Monitoring**:
    - Track pipeline execution status
    - Monitor progress in real-time
    - Log important events
    - Alert on failures

