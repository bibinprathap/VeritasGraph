# Graph Store

> **Unified interface for Property Graph Databases (Neo4j, FalkorDB).**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-database-search:{ .lg .middle } **Multi-Backend**

    ---

    Support for Neo4j (Enterprise) and FalkorDB (Redis-based)

-   :material-code-braces:{ .lg .middle } **Cypher Support**

    ---

    Execute standard Cypher queries across all supported backends

-   :material-graph:{ .lg .middle } **Graph Algorithms**

    ---

    Built-in support for PageRank, Community Detection, and Path Finding

-   :material-flash:{ .lg .middle } **Bulk Loading**

    ---

    Optimized batch processing for high-speed data ingestion

-   :material-lock:{ .lg .middle } **Transactions**

    ---

    ACID transaction support with rollback capabilities

-   :material-chart-bell-curve:{ .lg .middle } **Analytics**

    ---

    Centrality, Similarity, and Connectivity analysis

</div>

!!! tip "When to Use"
    - **Persistent Storage**: Storing the Knowledge Graph for long-term access
    - **Complex Queries**: Running multi-hop pattern matching queries
    - **Graph Analytics**: Performing global analysis on the graph structure
    - **Production**: Scaling to billions of nodes/edges (Neo4j/FalkorDB)

---

## ⚙️ Algorithms Used

### Query Execution

The module provides efficient query execution:

- **Cypher Translation**: Adapting queries for specific backend nuances (though most support OpenCypher)
- **Query Optimization**: Index utilization and execution plan analysis

### Graph Analytics

Built-in graph analytics algorithms include:

- **PageRank**: Measuring node importance based on incoming links
- **Louvain Modularity**: Detecting communities by optimizing modularity
- **Shortest Path**: Dijkstra/A* for finding optimal routes
- **Jaccard Similarity**: Measuring node similarity based on shared neighbors

### Bulk Operations

Efficient bulk loading capabilities:

- **Chunking**: Splitting large datasets into optimal batch sizes (e.g., `` `5000` `` records) to prevent memory overflow
- **Parallel Loading**: Concurrent batch insertion (backend dependent)

---

## Main Classes

### Core Classes

#### GraphStore

The main facade for graph operations.

**Methods:**

| Method | Description |
|--------|-------------|
| `connect(**options)` | Connect to the graph database |
| `close()` | Close connection to the graph database |
| `create_node(labels, properties, **options)` | Create a single node |
| `create_nodes(nodes, **options)` | Create multiple nodes in batch |
| `get_node(node_id, **options)` | Get a node by ID |
| `get_nodes(labels, properties, limit, **options)` | Get nodes matching criteria |
| `update_node(node_id, properties, merge, **options)` | Update node properties |
| `delete_node(node_id, detach, **options)` | Delete a node |
| `create_relationship(start_node_id, end_node_id, rel_type, properties, **options)` | Create a relationship |
| `get_relationships(node_id, rel_type, direction, limit, **options)` | Get relationships |
| `delete_relationship(rel_id, **options)` | Delete a relationship |
| `execute_query(query, parameters, **options)` | Execute a Cypher/OpenCypher query |
| `shortest_path(start_node_id, end_node_id, rel_type, max_depth, **options)` | Find shortest path between nodes |
| `get_neighbors(node_id, rel_type, direction, depth, **options)` | Get neighboring nodes |
| `get_stats()` | Get graph statistics |
| `create_index(label, property_name, index_type, **options)` | Create an index |

**Properties:**
- `nodes` - Access to NodeManager
- `relationships` - Access to RelationshipManager
- `query_engine` - Access to QueryEngine
- `analytics` - Access to GraphAnalytics

**Example:**

```python
from veritasreason.graph_store import GraphStore

store = GraphStore(backend="neo4j")
store.connect()
store.execute_query(
    "MATCH (n:Person {name: $name}) RETURN n",
    parameters={"name": "Alice"}
)
store.close()
```

#### GraphManager

Manager for graph store operations. Provides access to node, relationship, query, and analytics managers.

**Methods:**
- `get_stats()` - Get graph statistics
- `create_index(label, property_name, index_type, **options)` - Create an index

#### NodeManager

Manager for node CRUD operations.

**Methods:**
- `create(labels, properties, **options)` - Create a node
- `create_batch(nodes, **options)` - Create multiple nodes
- `get(node_id, labels, properties, limit, **options)` - Get node(s)
- `update(node_id, properties, merge, **options)` - Update a node
- `delete(node_id, detach, **options)` - Delete a node

#### RelationshipManager

Manager for relationship CRUD operations.

**Methods:**
- `create(start_node_id, end_node_id, rel_type, properties, **options)` - Create a relationship
- `get(node_id, rel_type, direction, limit, **options)` - Get relationships
- `delete(rel_id, **options)` - Delete a relationship

#### QueryEngine

Engine for query execution and optimization.

**Methods:**
- `execute(query, parameters, use_cache, **options)` - Execute a Cypher/OpenCypher query
- `clear_cache()` - Clear query cache
- `enable_cache()` - Enable query caching
- `disable_cache()` - Disable query caching

#### GraphAnalytics

Graph analytics and algorithms.

**Methods:**
- `shortest_path(start_node_id, end_node_id, rel_type, max_depth, **options)` - Find shortest path
- `get_neighbors(node_id, rel_type, direction, depth, **options)` - Get neighboring nodes
- `degree_centrality(labels, rel_type, direction, **options)` - Calculate degree centrality
- `connected_components(labels, **options)` - Find connected components

### Store Backends

#### Neo4jStore

Enterprise-grade Neo4j backend store.

**Features:**
- Bolt protocol support
- Cluster awareness
- APOC procedure integration
- Multi-database support
- Transaction support

**Related Classes:**
- `Neo4jDriver` - Neo4j driver wrapper
- `Neo4jSession` - Session management wrapper
- `Neo4jTransaction` - Transaction wrapper


#### FalkorDBStore

High-performance Redis-based FalkorDB backend store.

**Features:**
- Sparse matrix representation
- Ultra-low latency
- Redis protocol
- Multi-graph support
- Linear algebra based querying

**Related Classes:**
- `FalkorDBClient` - Client wrapper
- `FalkorDBGraph` - Graph wrapper with operations
- `FalkorDBQuery` - Query execution wrapper

**Special Methods:**
- `select_graph(graph_name)` - Select or create a graph
- `list_graphs()` - List all available graphs
- `delete_graph(graph_name)` - Delete a graph

### Configuration and Registry Classes

#### GraphStoreConfig

Configuration manager for graph store module. Supports environment variables, config files (YAML, JSON, TOML), and programmatic configuration.

**Methods:**
- `get(key, default)` - Get configuration value
- `set(key, value)` - Set configuration value
- `update(config)` - Update configuration with dictionary
- `get_method_config(method_name)` - Get method-specific configuration
- `set_method_config(method_name, config)` - Set method-specific configuration
- `get_all()` - Get all configuration
- `get_neo4j_config()` - Get Neo4j-specific configuration
- `get_falkordb_config()` - Get FalkorDB-specific configuration
- `reset()` - Reset configuration to defaults

**Global Instance:**
- `graph_store_config` - Global configuration instance

#### MethodRegistry

Registry for custom graph store methods, enabling extensibility.

**Methods:**
- `register(task, method_name, method_func, **metadata)` - Register a method
- `unregister(task, method_name)` - Unregister a method
- `get(task, method_name)` - Get a registered method
- `list_all(task)` - List all registered methods
- `has(task, method_name)` - Check if a method is registered
- `get_metadata(task, method_name)` - Get metadata for a registered method

**Supported Task Types:**
- `node` - Node CRUD methods
- `relationship` - Relationship CRUD methods
- `query` - Query execution methods
- `traversal` - Graph traversal methods
- `analytics` - Graph analytics methods
- `bulk` - Bulk operation methods

**Global Instance:**
- `method_registry` - Global method registry instance

---

## Convenience Functions

The module provides convenience functions for common graph operations. These functions use a global GraphStore instance and support method registration for extensibility.

### Node Operations

| Function | Description |
|----------|-------------|
| `create_node(labels, properties, method, **options)` | Create a single node |
| `create_nodes(nodes, method, **options)` | Create multiple nodes in batch |
| `get_nodes(labels, properties, limit, method, **options)` | Get nodes matching criteria |
| `update_node(node_id, properties, merge, method, **options)` | Update node properties |
| `delete_node(node_id, detach, method, **options)` | Delete a node |

### Relationship Operations

| Function | Description |
|----------|-------------|
| `create_relationship(start_id, end_id, rel_type, properties, method, **options)` | Create a relationship |
| `create_relationships(relationships, method, **options)` | Create multiple relationships in batch |
| `get_relationships(node_id, rel_type, direction, limit, method, **options)` | Get relationships matching criteria |
| `update_relationship(rel_id, properties, method, **options)` | Update relationship properties |
| `delete_relationship(rel_id, method, **options)` | Delete a relationship |

### Query Operations

| Function | Description |
|----------|-------------|
| `execute_query(query, parameters, method, **options)` | Execute a Cypher/OpenCypher query |

### Analytics Operations

| Function | Description |
|----------|-------------|
| `shortest_path(start_node_id, end_node_id, rel_type, max_depth, method, **options)` | Find shortest path between nodes |
| `get_neighbors(node_id, rel_type, direction, depth, method, **options)` | Get neighboring nodes |
| `run_analytics(algorithm, method, **options)` | Run graph analytics algorithm |

### Utility Functions

| Function | Description |
|----------|-------------|
| `get_graph_store_method(task, method_name)` | Get graph store method by task and name |
| `list_available_methods(task)` | List all available graph store methods |

**Example:**

```python
from veritasreason.graph_store import (
    create_node,
    create_nodes,
    create_relationship,
    execute_query,
    shortest_path,
    get_neighbors,
    run_analytics
)

# Quick node creation
alice = create_node(["Person"], {"name": "Alice", "age": 30})
bob = create_node(["Person"], {"name": "Bob", "age": 25})

# Batch node creation
people = create_nodes([
    {"labels": ["Person"], "properties": {"name": "Charlie"}},
    {"labels": ["Person"], "properties": {"name": "Diana"}}
])

# Create relationship
rel = create_relationship(
    start_id=alice["id"],
    end_id=bob["id"],
    rel_type="KNOWS",
    properties={"since": 2020}
)

# Quick query
results = execute_query("MATCH (n:Person) RETURN count(n) as count")

# Find shortest path
path = shortest_path(
    start_node_id=alice["id"],
    end_node_id=bob["id"],
    max_depth=5
)

# Get neighbors
neighbors = get_neighbors(node_id=alice["id"], depth=2)

# Run analytics
centrality = run_analytics(
    algorithm="degree_centrality",
    labels=["Person"]
)
```

---

## Configuration

### Environment Variables

```bash
export GRAPH_STORE_BACKEND=neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
```

### YAML Configuration

```yaml
graph_store:
  backend: neo4j
  
  neo4j:
    uri: bolt://localhost:7687
    pool_size: 50
    
```

---

## Integration Examples

### Hybrid Search (Vector + Graph)

```python
from veritasreason.graph_store import GraphStore
from veritasreason.vector_store import VectorStore

# 1. Find relevant nodes via Vector Search
vector_store = VectorStore()
results = vector_store.search(query_vec, k=5)
node_ids = [r.metadata['node_id'] for r in results]

# 2. Expand context via Graph Traversal
graph_store = GraphStore()
query = """
MATCH (n)-[r]-(m)
WHERE elementId(n) IN $ids
RETURN n, r, m
"""
subgraph = graph_store.execute_query(query, parameters={"ids": node_ids})
```

---

## Best Practices

1.  **Use Parameters**: Always use parameters in Cypher queries (`$name`) instead of string concatenation to prevent injection and improve caching.
2.  **Batch Writes**: Use `create_nodes` (plural) for bulk insertion instead of loop-inserting.
3.  **Create Indexes**: Ensure you have indexes on frequently queried properties (`id`, `name`).
4.  **Close Connections**: Use context managers (`with GraphStore() as store:`) or call `close()` to release resources.

---

## See Also

- [Knowledge Graph Module](kg.md) - Logical layer above Graph Store
- [Triplet Store Module](triplet_store.md) - RDF-based alternative
- [Visualization Module](visualization.md) - Visualizing query results

## Cookbook

Interactive tutorials to learn graph storage:

- **[Graph Store](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/09_Graph_Store.ipynb)**: Persist knowledge graphs in Neo4j or FalkorDB
  - **Topics**: Neo4j, FalkorDB, Cypher, persistence, graph databases
  - **Difficulty**: Intermediate
  - **Use Cases**: Persistent storage, production deployments, graph database integration
