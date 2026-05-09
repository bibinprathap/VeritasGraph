# Core

> **Framework infrastructure, lifecycle management, and plugin system.**

---

## 🎯 Overview

The **Core Module** provides framework infrastructure, lifecycle management, configuration, and orchestration capabilities. It's the foundation that enables coordination between all VeritasReason modules.

### What is the Core Module?

The Core module provides:

- **Orchestration**: The `` `VeritasReason` `` class coordinates multiple modules for complex workflows
- **Lifecycle Management**: Handles initialization, startup, shutdown, and state transitions
- **Configuration**: Unified configuration management via YAML and environment variables
- **Plugin System**: Extensible plugin registry for custom modules and capabilities
- **Method Registry**: Registry for custom orchestration methods

### When to Use the Core Module

!!! tip "Primary Approach: Individual Modules"
    For most use cases, **use individual modules directly** (e.g., `veritasreason.ingest`, `veritasreason.kg`). This gives you full control and transparency.

!!! note "When to Use Orchestration"
    Use the `VeritasReason` orchestration class when you need:
    - **Complex Workflows**: Multi-step pipelines that span multiple modules
    - **Lifecycle Management**: Application-level initialization and shutdown
    - **Centralized Configuration**: Global settings that affect multiple modules
    - **Plugin Integration**: Custom plugins that need framework coordination

<div class="grid cards" markdown>

-   :material-cogs:{ .lg .middle } **VeritasReason**

    ---

    Orchestration class for coordinating complex workflows across modules

-   :material-lifecycle:{ .lg .middle } **Lifecycle Management**

    ---

    Manage initialization, startup, shutdown, and state transitions

-   :material-tune:{ .lg .middle } **Configuration**

    ---

    Unified configuration management via YAML and Environment variables

-   :material-puzzle:{ .lg .middle } **Plugin System**

    ---

    Extensible plugin registry for adding custom modules and capabilities

-   :material-console:{ .lg .middle } **Method Registry**

    ---

    Registry for custom orchestration methods and extensibility

</div>

---

## ⚙️ Algorithms Used

### Lifecycle Management

**What is Lifecycle Management?**

Lifecycle management handles the initialization, startup, running, and shutdown phases of the VeritasReason framework. It ensures that all components are properly initialized, resources are managed correctly, and cleanup happens gracefully.

**How it works:**
- **State Machine**: `UNINITIALIZED` -> `INITIALIZING` -> `READY` -> `RUNNING` -> `STOPPING` -> `STOPPED`
- **Priority-based Hooks**: Startup and shutdown hooks executed in priority order (lower = earlier)
- **Graceful Shutdown**: Ensuring all resources (DB connections, thread pools) are closed properly

**Why it matters:**
- Prevents resource leaks (database connections, file handles)
- Ensures proper initialization order (dependencies are ready before use)
- Enables clean application shutdown
- Supports health monitoring and status tracking

### Configuration

**What is Configuration Management?**

Configuration management provides a unified way to configure all VeritasReason modules. It supports multiple configuration sources with a clear priority order, ensuring consistent settings across your application.

**How it works:**
- **Layered Loading**: Defaults -> Config File -> Environment Variables (Priority order)
- **Schema Validation**: Validating config structure against defined schemas
- **Nested Access**: Dot notation for accessing nested configuration values

**Why it matters:**
- Centralized configuration for all modules
- Environment-specific settings (dev, staging, production)
- Secure credential management (via environment variables)
- Validation prevents configuration errors

### Plugin System

**What is the Plugin System?**

The plugin system allows you to extend VeritasReason with custom modules and capabilities. Plugins can add new functionality, modify existing behavior, or integrate with external systems.

**How it works:**
- **Discovery**: Auto-discovery of plugins via directory scanning
- **Registration**: Dynamic registration of classes and functions
- **Dependency Resolution**: Automatic loading of plugin dependencies

**Why it matters:**
- Extend VeritasReason with custom functionality
- Integrate with external systems and APIs
- Modify or enhance existing modules
- Share custom functionality across projects

---

## Main Classes

### VeritasReason

The **VeritasReason** class is an orchestration class that coordinates multiple modules for complex workflows. It's designed for applications that need lifecycle management, centralized configuration, and multi-step pipeline coordination.

!!! important "Not a Convenience Wrapper"
    The `VeritasReason` class is **not** a convenience wrapper. It's an orchestration tool for complex workflows. For most use cases, use individual modules directly for better control and transparency.

**What it does:**
- Coordinates multiple modules (ingest, parse, extract, kg, etc.)
- Manages application lifecycle (initialization, shutdown)
- Provides centralized configuration
- Enables plugin integration
- Handles complex multi-step workflows

**When to use it:**
- Building applications with multiple components
- Need lifecycle management (startup/shutdown hooks)
- Complex workflows spanning multiple modules
- Want centralized configuration
- Integrating custom plugins

**Methods:**

| Method | Description |
|--------|-------------|
| `` `__init__(config=None, **kwargs)` `` | Initialize framework with optional configuration |
| `` `initialize()` `` | Initialize all framework components and modules |
| `` `build_knowledge_base(sources, **kwargs)` `` | Orchestrate building a knowledge base from data sources |
| `` `run_pipeline(pipeline, data)` `` | Execute a processing pipeline |
| `` `get_status()` `` | Get system health and status |
| `` `shutdown(graceful=True)` `` | Shutdown the framework gracefully |

**Example - Orchestration for Complex Workflow:**

```python
from veritasreason.core import VeritasReason

# Initialize framework for orchestration
framework = VeritasReason()
framework.initialize()

# Build knowledge base (orchestrates multiple modules)
result = framework.build_knowledge_base(
    sources=["doc1.pdf", "doc2.docx"],
    embeddings=True,
    graph=True
)

# Check status
status = framework.get_status()
print(f"System state: {status['state']}")

# Shutdown gracefully
framework.shutdown()
```

**Alternative - Using Individual Modules (Recommended):**

```python
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder
from veritasreason.embeddings import TextEmbedder

# Use modules directly for full control
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()
rel_extractor = RelationExtractor()
builder = GraphBuilder()
embedder = TextEmbedder()

# Build your pipeline step by step
docs = ingestor.ingest_file("doc1.pdf")
parsed = parser.parse_document("doc1.pdf")
entities = ner.extract_entities(parsed.get("full_text", ""))
relationships = rel_extractor.extract_relations(parsed.get("full_text", ""), entities=entities)
kg = builder.build_graph(entities=entities, relationships=relationships)
embeddings = embedder.embed_batch([e.text for e in entities])
```

### ConfigManager

Manages global configuration loading, validation, and merging.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `load_from_file(file_path, validate=True)` `` | Load config from YAML or JSON file |
| `` `load_from_dict(config_dict, validate=True)` `` | Load config from dictionary |
| `` `merge_configs(*configs, validate=True)` `` | Merge multiple configurations |
| `get_config()` | Get current configuration |
| `set_config(config, validate=True)` | Set current configuration |
| `reload(file_path=None)` | Reload configuration from file |

**Example:**

```python
from veritasreason.core import ConfigManager

manager = ConfigManager()
config = manager.load_from_file("config.yaml")

# Merge configurations
config1 = manager.load_from_file("base_config.yaml")
config2 = manager.load_from_file("override_config.yaml")
merged = manager.merge_configs(config1, config2)
```

### Config

Configuration data class with validation and nested access.

**Methods:**

| Method | Description |
|--------|-------------|
| `get(key_path, default=None)` | Get nested configuration value by key path |
| `set(key_path, value)` | Set nested configuration value |
| `update(updates, merge=True)` | Update configuration with new values |
| `validate()` | Validate configuration settings |
| `to_dict()` | Convert configuration to dictionary |

**Example:**

```python
from veritasreason.core import Config, ConfigManager

manager = ConfigManager()
config = manager.load_from_dict({"processing": {"batch_size": 32}})

# Access nested values
batch_size = config.get("processing.batch_size", default=16)

# Update values
config.set("processing.batch_size", 64)
config.update({"quality": {"min_confidence": 0.9}})

# Validate
config.validate()
```

### LifecycleManager

System lifecycle management with hooks and health monitoring.

**Methods:**

| Method | Description |
|--------|-------------|
| `startup()` | Execute startup sequence with registered hooks |
| `shutdown(graceful=True)` | Execute shutdown sequence |
| `register_startup_hook(hook_fn, priority=50)` | Register a startup hook |
| `register_shutdown_hook(hook_fn, priority=50)` | Register a shutdown hook |
| `register_component(name, component)` | Register component for health monitoring |
| `health_check()` | Perform comprehensive system health check |
| `get_health_summary()` | Get summary of system health |
| `get_state()` | Get current system state |
| `is_ready()` | Check if system is ready |
| `is_running()` | Check if system is running |

**Example:**

```python
from veritasreason.core import LifecycleManager

manager = LifecycleManager()

# Register hooks
def init_db():
    print("Initializing database...")

manager.register_startup_hook(init_db, priority=10)
manager.startup()

# Register component for health monitoring
class DatabaseComponent:
    def health_check(self):
        return {"healthy": True, "message": "Connected"}

db = DatabaseComponent()
manager.register_component("database", db)

# Check health
health = manager.health_check()
summary = manager.get_health_summary()

manager.shutdown(graceful=True)
```

### PluginRegistry

Plugin registry and management system for dynamic plugin discovery and loading.

**Methods:**

| Method | Description |
|--------|-------------|
| `__init__(plugin_paths=None)` | Initialize with optional plugin paths for auto-discovery |
| `register_plugin(plugin_name, plugin_class, version="1.0.0", **metadata)` | Manually register a plugin |
| `load_plugin(plugin_name, **config)` | Load and initialize a plugin |
| `unload_plugin(plugin_name)` | Unload a plugin |
| `list_plugins()` | List all available plugins |
| `get_plugin_info(plugin_name)` | Get information about a plugin |
| `is_plugin_loaded(plugin_name)` | Check if a plugin is loaded |
| `get_loaded_plugin(plugin_name)` | Get loaded plugin instance |

**Example:**

```python
from veritasreason.core import PluginRegistry

# Auto-discover plugins
registry = PluginRegistry(plugin_paths=["./plugins"])

# Load plugin with configuration
plugin = registry.load_plugin("my_plugin", api_key="xxx")

# List all plugins
plugins = registry.list_plugins()
for plugin_info in plugins:
    print(f"{plugin_info['name']}: {plugin_info['version']}")

# Get plugin info
info = registry.get_plugin_info("my_plugin")
```

### MethodRegistry

Registry for custom orchestration methods.

**Methods:**

| Method | Description |
|--------|-------------|
| `register(task, name, method_func)` | Register a custom orchestration method |
| `get(task, name)` | Get method by task and name |
| `list_all(task=None)` | List all registered methods |
| `unregister(task, name)` | Unregister a method |
| `clear(task=None)` | Clear all registered methods |

**Example:**

```python
from veritasreason.core import method_registry

def custom_kb_builder(sources, **kwargs):
    # Custom logic
    return {"knowledge_graph": {}}

method_registry.register("knowledge_base", "custom", custom_kb_builder)

# Use custom method
method = method_registry.get("knowledge_base", "custom")
result = method(sources=["doc.pdf"])
```

---

## Orchestration Methods

Convenience functions for common orchestration tasks.

### build_knowledge_base()

Build knowledge base from data sources.

```python
from veritasreason.core.methods import build_knowledge_base

result = build_knowledge_base(
    sources=["doc1.pdf", "doc2.docx"],
    method="default",
    embeddings=True,
    graph=True
)
```

### run_pipeline()

Execute a processing pipeline.

```python
from veritasreason.core.methods import run_pipeline

result = run_pipeline(
    pipeline={"steps": ["parse", "extract"]},
    data="sample text",
    method="default"
)
```

### initialize_framework()

Initialize VeritasReason framework.

```python
from veritasreason.core.methods import initialize_framework

framework = initialize_framework(
    config={"llm_provider": {"name": "openai"}},
    method="default"
)
```

### get_status()

Get system status.

```python
from veritasreason.core.methods import get_status

status = get_status(framework=my_framework, method="detailed")
```

### get_orchestration_method()

Get orchestration method by task and name.

```python
from veritasreason.core.methods import get_orchestration_method

method = get_orchestration_method("knowledge_base", "custom")
```

### list_available_methods()

List all available orchestration methods.

```python
from veritasreason.core.methods import list_available_methods

all_methods = list_available_methods()
kb_methods = list_available_methods("knowledge_base")
```

---

## Configuration

### Environment Variables

Configuration can be loaded from environment variables with `VERITASREASON_` prefix:

```bash
export VERITASREASON_PROCESSING_BATCH_SIZE=64
export VERITASREASON_LLM_PROVIDER_MODEL=gpt-4
export VERITASREASON_QUALITY_MIN_CONFIDENCE=0.8
```

### YAML Configuration

```yaml
llm_provider:
  name: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}

embedding_model:
  name: openai
  model: text-embedding-ada-002

processing:
  batch_size: 32
  max_workers: 4

quality:
  min_confidence: 0.7

logging:
  level: INFO

plugins:
  my_plugin:
    enabled: true
    config_key: config_value
```

### JSON Configuration

```json
{
  "llm_provider": {
    "name": "openai",
    "model": "gpt-4"
  },
  "processing": {
    "batch_size": 32
  }
}
```

---

## Integration Examples

### Basic Usage

```python
from veritasreason.core import VeritasReason, ConfigManager

# 1. Load configuration
config_manager = ConfigManager()
config = config_manager.load_from_file("config.yaml")

# 2. Initialize framework
framework = VeritasReason(config=config)
framework.initialize()

try:
    # 3. Build knowledge base
    result = framework.build_knowledge_base(
        sources=["doc1.pdf", "doc2.docx"],
        embeddings=True,
        graph=True
    )
    
    # 4. Check status
    status = framework.get_status()
    print(f"System state: {status['state']}")
    
finally:
    # 5. Shutdown gracefully
    framework.shutdown(graceful=True)
```

### Custom Plugin

```python
from veritasreason.core import PluginRegistry

class MyPlugin:
    def initialize(self):
        print("Plugin initialized")
    
    def execute(self, data):
        return {"processed": True}

registry = PluginRegistry()
registry.register_plugin(
    plugin_name="my_plugin",
    plugin_class=MyPlugin,
    version="1.0.0"
)

plugin = registry.load_plugin("my_plugin")
result = plugin.execute("sample data")
```

### Lifecycle Hooks

```python
from veritasreason.core import LifecycleManager

manager = LifecycleManager()

def init_database():
    print("Initializing database...")

def cleanup_database():
    print("Cleaning up database...")

manager.register_startup_hook(init_database, priority=10)
manager.register_shutdown_hook(cleanup_database, priority=10)

manager.startup()
# ... do work ...
manager.shutdown(graceful=True)
```

### Custom Orchestration Method

```python
from veritasreason.core import method_registry, VeritasReason

def fast_kb_builder(sources, **kwargs):
    framework = VeritasReason()
    framework.initialize()
    try:
        return framework.build_knowledge_base(
            sources=sources,
            embeddings=False,  # Skip for speed
            graph=True,
            **kwargs
        )
    finally:
        framework.shutdown()

method_registry.register("knowledge_base", "fast", fast_kb_builder)

# Use custom method
from veritasreason.core.methods import build_knowledge_base
result = build_knowledge_base(sources=["doc.pdf"], method="fast")
```

---

## Best Practices

1. **Always Initialize**: Always call `initialize()` after creating a `VeritasReason` instance before using it.

2. **Graceful Shutdown**: Always call `shutdown(graceful=True)` in a `finally` block to ensure proper cleanup.

3. **Configuration Management**: Use `ConfigManager` for loading and managing configurations. Prefer YAML files for complex configurations.

4. **Error Handling**: Wrap framework operations in try-except blocks to handle `ConfigurationError` and `ProcessingError` appropriately.

5. **Health Monitoring**: Register components with `LifecycleManager` for health monitoring and use `health_check()` regularly.

6. **Plugin Development**: Follow the plugin interface (must have `initialize()` and `execute()` methods) when creating custom plugins.

7. **Method Registration**: Use `MethodRegistry` for extensibility. Register custom methods for knowledge base building, pipeline execution, etc.

8. **Hook Priorities**: Use appropriate priorities for lifecycle hooks. Lower numbers execute first.

9. **Configuration Validation**: Always validate configurations using `config.validate()` before using them.

10. **Resource Cleanup**: Ensure all resources are properly cleaned up in shutdown hooks.

---

## See Also
- [Pipeline Module](pipeline.md) - Pipeline execution and orchestration
- [Utils Module](utils.md) - Shared utilities used by Core
- [Getting Started Guide](../getting-started.md) - Learn the basics

## Cookbook

Interactive tutorials to learn orchestration and lifecycle management:

- **[Welcome to VeritasReason](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/01_Welcome_to_VeritasReason.ipynb)**: Comprehensive introduction to all VeritasReason modules and architecture
  - **Topics**: Framework overview, all modules, architecture, configuration, lifecycle
  - **Difficulty**: Beginner
  - **Use Cases**: Understanding the framework structure, first-time users

- **[Pipeline Orchestration](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/07_Pipeline_Orchestration.ipynb)**: Build robust, automated data processing pipelines
  - **Topics**: Workflows, automation, error handling, pipeline orchestration
  - **Difficulty**: Advanced
  - **Use Cases**: Complex multi-step workflows, production pipelines
