# Graph Store Module Usage Guide

The Graph Store module provides comprehensive property graph database integration for the VeritasReason framework, supporting multiple backends including **Neo4j** and **FalkorDB**.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Backend Configuration](#backend-configuration)
4. [Node Operations](#node-operations)
5. [Relationship Operations](#relationship-operations)
6. [Query Execution](#query-execution)
7. [Graph Analytics](#graph-analytics)
8. [Convenience Functions](#convenience-functions)
9. [Advanced Usage](#advanced-usage)

## Installation

### Core Installation

```bash
pip install veritas-reason
```

### Backend-Specific Dependencies

```bash
# Neo4j
pip install neo4j

# FalkorDB
pip install falkordb
```

### Docker Setup for FalkorDB

```bash
docker run -p 6379:6379 -p 3000:3000 -it --rm -v ./data:/var/lib/falkordb/data falkordb/falkordb
```

## Quick Start

### Using the GraphStore Class

```python
from veritasreason.graph_store import GraphStore

# Initialize with Neo4j backend
store = GraphStore(
    backend="neo4j",
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Connect to database
store.connect()

# Create nodes
alice = store.create_node(
    labels=["Person"],
    properties={"name": "Alice", "age": 30}
)

bob = store.create_node(
    labels=["Person"],
    properties={"name": "Bob", "age": 25}
)

# Create relationship
relationship = store.create_relationship(
    start_node_id=alice["id"],
    end_node_id=bob["id"],
    rel_type="KNOWS",
    properties={"since": 2020}
)

# Query the graph
results = store.execute_query(
    "MATCH (p:Person) WHERE p.age > 20 RETURN p.name, p.age"
)

for record in results["records"]:
    print(f"{record['p.name']} is {record['p.age']} years old")

# Close connection
store.close()
```

### Using Convenience Functions

```python
from veritasreason.graph_store import (
    create_node,
    create_relationship,
    get_nodes,
    execute_query,
    shortest_path
)

# Create nodes
alice = create_node(labels=["Person"], properties={"name": "Alice"})
bob = create_node(labels=["Person"], properties={"name": "Bob"})

# Create relationship
rel = create_relationship(
    start_id=alice["id"],
    end_id=bob["id"],
    rel_type="KNOWS"
)

# Get all Person nodes
people = get_nodes(labels=["Person"], limit=100)

# Execute custom query
results = execute_query("MATCH (n) RETURN n LIMIT 10")
```

## Backend Configuration

### Neo4j Configuration

```python
from veritasreason.graph_store import GraphStore

store = GraphStore(
    backend="neo4j",
    uri="bolt://localhost:7687",
    user="neo4j",
    password="your_password",
    database="neo4j",  # Optional: specify database
    encrypted=False    # Optional: enable encryption
)
```

### FalkorDB Configuration

```python
from veritasreason.graph_store import GraphStore

store = GraphStore(
    backend="falkordb",
    host="localhost",
    port=6379,
    password=None,  # Optional: Redis password
    graph_name="my_graph"
)

# Connect to FalkorDB
store.connect()
```

### Environment Variables

Configure backends using environment variables:

```bash
# General
export GRAPH_STORE_DEFAULT_BACKEND=neo4j
export GRAPH_STORE_BATCH_SIZE=1000
export GRAPH_STORE_TIMEOUT=30

# Neo4j
export GRAPH_STORE_NEO4J_URI=bolt://localhost:7687
export GRAPH_STORE_NEO4J_USER=neo4j
export GRAPH_STORE_NEO4J_PASSWORD=password

# FalkorDB
export GRAPH_STORE_FALKORDB_HOST=localhost
export GRAPH_STORE_FALKORDB_PORT=6379
export GRAPH_STORE_FALKORDB_GRAPH_NAME=default
```

## Node Operations

### Creating Nodes

```python
# Single node
node = store.create_node(
    labels=["Person", "Employee"],
    properties={
        "name": "Alice",
        "age": 30,
        "department": "Engineering"
    }
)

# Multiple nodes in batch
nodes = store.create_nodes([
    {"labels": ["Person"], "properties": {"name": "Bob"}},
    {"labels": ["Person"], "properties": {"name": "Charlie"}},
    {"labels": ["Company"], "properties": {"name": "Acme Corp"}}
])
```

### Retrieving Nodes

```python
# Get node by ID
node = store.get_node(node_id=123)

# Get nodes by labels
people = store.get_nodes(labels=["Person"], limit=50)

# Get nodes by properties
engineers = store.get_nodes(
    labels=["Person"],
    properties={"department": "Engineering"}
)
```

### Updating Nodes

```python
# Merge properties (default)
updated = store.update_node(
    node_id=123,
    properties={"age": 31, "title": "Senior Engineer"},
    merge=True
)

# Replace all properties
updated = store.update_node(
    node_id=123,
    properties={"name": "Alice Smith"},
    merge=False
)
```

### Deleting Nodes

```python
# Delete node and its relationships
store.delete_node(node_id=123, detach=True)

# Delete only node (fails if has relationships)
store.delete_node(node_id=123, detach=False)
```

## Relationship Operations

### Creating Relationships

```python
# Single relationship
rel = store.create_relationship(
    start_node_id=alice["id"],
    end_node_id=bob["id"],
    rel_type="KNOWS",
    properties={"since": 2020, "type": "friend"}
)

# Multiple relationships
from veritasreason.graph_store import create_relationships

rels = create_relationships([
    {"start_id": 1, "end_id": 2, "type": "WORKS_FOR"},
    {"start_id": 1, "end_id": 3, "type": "MANAGES"},
    {"start_id": 2, "end_id": 3, "type": "COLLABORATES_WITH"}
])
```

### Retrieving Relationships

```python
# All relationships for a node
rels = store.get_relationships(node_id=123)

# Outgoing relationships only
outgoing = store.get_relationships(
    node_id=123,
    direction="out"
)

# Filter by type
knows_rels = store.get_relationships(
    node_id=123,
    rel_type="KNOWS"
)
```

### Deleting Relationships

```python
store.delete_relationship(rel_id=456)
```

## Query Execution

### Basic Queries

```python
# Simple query
results = store.execute_query(
    "MATCH (n:Person) RETURN n.name, n.age"
)

# Parameterized query
results = store.execute_query(
    "MATCH (n:Person) WHERE n.age > $min_age RETURN n.name",
    parameters={"min_age": 25}
)

# Process results
for record in results["records"]:
    print(record)
```

### Complex Queries

```python
# Find paths
results = store.execute_query("""
    MATCH path = (a:Person {name: 'Alice'})-[:KNOWS*1..3]-(b:Person)
    RETURN path
""")

# Aggregations
results = store.execute_query("""
    MATCH (p:Person)
    RETURN p.department, count(*) as count, avg(p.age) as avg_age
    ORDER BY count DESC
""")
```

## Graph Analytics

### Shortest Path

```python
path = store.shortest_path(
    start_node_id=alice["id"],
    end_node_id=bob["id"],
    rel_type="KNOWS",
    max_depth=5
)

if path:
    print(f"Path length: {path['length']}")
    print(f"Nodes in path: {len(path['nodes'])}")
```

### Get Neighbors

```python
# Direct neighbors
neighbors = store.get_neighbors(node_id=123, depth=1)

# Extended neighborhood
extended = store.get_neighbors(
    node_id=123,
    rel_type="KNOWS",
    direction="out",
    depth=3
)
```

### Run Analytics Algorithms

```python
from veritasreason.graph_store import run_analytics

# Degree centrality
centrality = run_analytics(
    algorithm="degree_centrality",
    labels=["Person"],
    direction="both"
)

# Connected components (basic approximation)
components = run_analytics(
    algorithm="connected_components"
)
```

## Convenience Functions

The module provides convenience functions for common operations:

```python
from veritasreason.graph_store import (
    # Node operations
    create_node,
    create_nodes,
    get_nodes,
    update_node,
    delete_node,
    
    # Relationship operations
    create_relationship,
    create_relationships,
    get_relationships,
    update_relationship,
    delete_relationship,
    
    # Query operations
    execute_query,
    
    # Analytics operations
    shortest_path,
    get_neighbors,
    run_analytics,
    
    # Method registry
    get_graph_store_method,
    list_available_methods
)
```

## Configuration Management

### Using GraphStoreConfig

The `GraphStoreConfig` class provides centralized configuration management:

```python
from veritasreason.graph_store import GraphStoreConfig, graph_store_config

# Get configuration value
default_backend = graph_store_config.get("default_backend", default="neo4j")

# Set configuration value
graph_store_config.set("default_backend", "falkordb")

# Update multiple values
graph_store_config.update({
    "batch_size": 2000,
    "timeout": 60
})

# Get backend-specific configuration
neo4j_config = graph_store_config.get_neo4j_config()
falkordb_config = graph_store_config.get_falkordb_config()

# Get all configuration
all_config = graph_store_config.get_all()

# Reset to defaults
graph_store_config.reset()
```

### Method Registry

The `MethodRegistry` class allows you to register custom methods for extensibility:

```python
from veritasreason.graph_store import MethodRegistry, method_registry

# Register a custom node creation method
def validated_create_node(labels, properties, **options):
    """Custom node creation with validation."""
    if "name" not in properties:
        raise ValueError("name is required")
    
    from veritasreason.graph_store import _get_store
    store = _get_store()
    return store.create_node(labels, properties, **options)

# Register the custom method
method_registry.register("node", "validated", validated_create_node)

# Use the custom method
from veritasreason.graph_store import create_node
node = create_node(
    labels=["Person"],
    properties={"name": "Alice"},
    method="validated"
)

# List available methods
available = method_registry.list_all("node")
# Returns: {"node": ["validated"]}

# Check if a method exists
exists = method_registry.has("node", "validated")

# Get method metadata
metadata = method_registry.get_metadata("node", "validated")

# Unregister a method
method_registry.unregister("node", "validated")
```

## Advanced Usage

### Context Manager

```python
from veritasreason.graph_store import GraphStore

with GraphStore(backend="neo4j", uri="bolt://localhost:7687") as store:
    store.create_node(labels=["Test"], properties={"name": "test"})
    # Connection automatically closed when exiting
```

### Custom Method Registration

```python
from veritasreason.graph_store import method_registry, GraphStore

def custom_create_node(labels, properties, **options):
    """Custom node creation with validation."""
    # Add custom logic
    if "name" not in properties:
        raise ValueError("name is required")
    
    # Call default implementation
    store = GraphStore()
    store.connect()
    try:
        return store.create_node(labels, properties, **options)
    finally:
        store.close()

# Register custom method
method_registry.register("node", "validated", custom_create_node)

# Use custom method
from veritasreason.graph_store import create_node
node = create_node(labels=["Person"], properties={"name": "Alice"}, method="validated")
```

### Indexing

```python
# Create index for faster queries
store.create_index(
    label="Person",
    property_name="name",
    index_type="btree"
)

# Create fulltext index (Neo4j, FalkorDB)
store.create_index(
    label="Document",
    property_name="content",
    index_type="fulltext"
)
```

### Statistics

```python
stats = store.get_stats()
print(f"Total nodes: {stats.get('node_count')}")
print(f"Total relationships: {stats.get('relationship_count')}")
print(f"Labels: {stats.get('label_counts')}")
```

## Backend Comparison

| Feature | Neo4j | FalkorDB |
|---------|-------|----------|
| Query Language | Cypher | OpenCypher |
| Deployment | Server/Cloud | Server (Redis) |
| Schema | Schema-optional | Schema-optional |
| Transactions | ACID | ACID |
| Performance | Good | Ultra-fast |
| Use Case | General purpose | Real-time, LLM |

## Best Practices

1. **Use Parameterized Queries**: Always use parameters for user input to prevent injection attacks.

2. **Create Indexes**: Create indexes on frequently queried properties for better performance.

3. **Batch Operations**: Use batch operations when creating many nodes/relationships.

4. **Close Connections**: Always close connections when done, or use context managers.

5. **Handle Errors**: Wrap operations in try/except blocks for proper error handling.

```python
from veritasreason.utils.exceptions import ProcessingError

try:
    node = store.create_node(labels=["Person"], properties={"name": "Alice"})
except ProcessingError as e:
    print(f"Failed to create node: {e}")
```

## Examples

### Building a Social Network Graph

```python
from veritasreason.graph_store import GraphStore, create_node, create_relationship

# Initialize store
store = GraphStore(backend="neo4j")
store.connect()

# Create users
users = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35},
]

user_nodes = store.create_nodes([
    {"labels": ["User"], "properties": u} for u in users
])

# Create friendships
store.create_relationship(user_nodes[0]["id"], user_nodes[1]["id"], "FRIENDS")
store.create_relationship(user_nodes[1]["id"], user_nodes[2]["id"], "FRIENDS")

# Find friends of friends
results = store.execute_query("""
    MATCH (a:User {name: 'Alice'})-[:FRIENDS]-()-[:FRIENDS]-(fof:User)
    WHERE fof <> a
    RETURN DISTINCT fof.name
""")
```

### Knowledge Graph for RAG

```python
from veritasreason.graph_store import GraphStore

store = GraphStore(backend="falkordb", graph_name="knowledge_graph")
store.connect()

# Create entities
doc = store.create_node(["Document"], {"title": "AI Research", "content": "..."})
concept1 = store.create_node(["Concept"], {"name": "Machine Learning"})
concept2 = store.create_node(["Concept"], {"name": "Neural Networks"})

# Create relationships
store.create_relationship(doc["id"], concept1["id"], "MENTIONS")
store.create_relationship(concept1["id"], concept2["id"], "RELATED_TO")

# Query for retrieval
results = store.execute_query("""
    MATCH (d:Document)-[:MENTIONS]->(c:Concept)
    WHERE c.name CONTAINS 'Learning'
    RETURN d.title, d.content
""")
```

