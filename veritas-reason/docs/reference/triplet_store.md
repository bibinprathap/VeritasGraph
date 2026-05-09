# Triplet Store

> **Store and query RDF triplets with SPARQL support and semantic reasoning using industry-standard triplet stores.**

---

## 🎯 Overview

The **Triplet Store Module** provides storage and querying for RDF (Resource Description Framework) triplets. It supports industry-standard triplet stores with SPARQL querying and semantic reasoning capabilities.

### What is a Triplet Store?

A **triplet store** (also called an RDF store) is a database designed to store and query RDF triplets. RDF triplets are statements in the form:

- **Subject**: The entity being described
- **Predicate**: The relationship or property
- **Object**: The value or related entity

**Example**: `` `(Apple Inc., foundedBy, Steve Jobs)` ``

### Why Use the Triplet Store Module?

- **W3C Standards**: Full support for RDF and SPARQL standards
- **Semantic Reasoning**: RDFS and OWL reasoning for inference
- **Multiple Backends**: Support for Blazegraph, Apache Jena, RDF4J
- **SPARQL Queries**: Powerful SPARQL 1.1 query language
- **Federation**: Query across multiple stores
- **Bulk Loading**: High-performance data loading

### How It Works

1. **Store Selection**: Choose a backend (Blazegraph, Jena, RDF4J)
2. **Triplet Storage**: Store subject-predicate-object triplets
3. **SPARQL Queries**: Query using SPARQL 1.1
4. **Reasoning**: Apply RDFS/OWL reasoning for inference
5. **Federation**: Query across multiple stores if needed

<div class="grid cards" markdown>

-   :material-graph-outline:{ .lg .middle } **RDF Storage**

    ---

    Store subject-predicate-object triplets in W3C-compliant RDF format

-   :material-code-braces:{ .lg .middle } **SPARQL Queries**

    ---

    Full W3C SPARQL 1.1 query language support for powerful semantic queries

-   :material-brain:{ .lg .middle } **Reasoning**

    ---

    RDFS and OWL reasoning for inference and knowledge discovery

-   :material-database-sync:{ .lg .middle } **Multiple Backends**

    ---

    Blazegraph, Apache Jena, and RDF4J support

-   :material-link-variant:{ .lg .middle } **Federation**

    ---

    Query across multiple triplet stores with SPARQL federation

-   :material-upload-multiple:{ .lg .middle } **Bulk Loading**

    ---

    High-performance bulk data loading with progress tracking

</div>

!!! tip "Choosing the Right Backend"
    - **Blazegraph**: High-performance, excellent for large datasets, GPU acceleration
    - **Apache Jena**: Full-featured, TDB2 storage, SHACL validation
    - **RDF4J**: Java-based, excellent tooling, multiple storage backends

---

## ⚙️ Algorithms Used

### Query Algorithms
- **SPARQL Query Optimization**: Join reordering with selectivity estimation
- **Triplet Pattern Matching**: Index-based lookup with B+ trees
- **Graph Pattern Matching**: Subgraph isomorphism with backtracking
- **Query Planning**: Cost-based optimization with statistics
- **Join Algorithms**: Hash join, merge join, nested loop join
- **Filter Pushdown**: Early filter application for performance

### Indexing
- **SPO Index**: Subject-Predicate-Object index for subject lookups
- **POS Index**: Predicate-Object-Subject index for predicate lookups
- **OSP Index**: Object-Subject-Predicate index for object lookups
- **Six-Index Scheme**: All permutations (SPO, SOP, PSO, POS, OSP, OPS) for optimal query performance
- **B+ Tree Indexing**: Efficient range queries and sorted access
- **Hash Indexing**: O(1) exact match lookups

### Reasoning Algorithms
- **RDFS Reasoning**: Subclass/subproperty inference, domain/range inference
- **OWL Reasoning**: Class hierarchy, property characteristics, cardinality constraints
- **Forward Chaining**: Materialization of inferred triplets
- **Backward Chaining**: On-demand inference during query execution
- **Rule-Based Inference**: Custom SWRL rules

### Bulk Loading
- **Batch Processing**: Chunked triplet insertion with configurable batch size
- **Parallel Loading**: Multi-threaded data loading
- **Index Building**: Deferred index construction for faster loading
- **Transaction Management**: Atomic batch commits with rollback support

---

## Main Classes

### TripletStore

Main interface for triplet store operations.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `__init__(backend, endpoint)` | Initialize triplet store | Factory pattern |
| `add_triplet(triplet)` | Add single triplet | Single insert |
| `add_triplets(triplets, batch_size)` | Add multiple triplets | Bulk load with batching |
| `get_triplets(s, p, o)` | Retrieve triplets | Pattern matching |
| `delete_triplet(triplet)` | Delete triplet | Pattern matching deletion |
| `execute_query(query)` | Execute SPARQL | Query engine delegation |

### BulkLoader

High-volume data loading utility.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `load_triplets(triplets, store)` | Bulk load triplets | Batch processing with retries |

### QueryEngine

SPARQL query execution and optimization engine.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `execute(query)` | Execute SPARQL query | Query execution |
| `optimize(query)` | Optimize SPARQL query | Query rewriting |
| `expand_entity_uri(uri, store, ...)` | Expand aligned entity URIs | Bidirectional SPARQL lookup |
| `build_values_clause(var, uris)` | Generate VALUES clause | String formatting |

---

## Cookbook

Interactive tutorials that use triplet stores:

- **[Reasoning and Inference](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/08_Reasoning_and_Inference.ipynb)**: Use logical reasoning with SPARQL and triplet stores
  - **Topics**: SPARQL reasoning, RDF stores, inference engines
  - **Difficulty**: Advanced
  - **Use Cases**: Semantic reasoning, SPARQL queries, RDF-based knowledge graphs

## 🚀 Usage

### Initialization

```python
from veritasreason.triplet_store import TripletStore

# Initialize Blazegraph store
store = TripletStore(
    backend="blazegraph",
    endpoint="http://localhost:9999/blazegraph"
)
```

### Adding Data

```python
from veritasreason.semantic_extract.triplet_extractor import Triplet

# Single triplet
triplet = Triplet("http://s", "http://p", "http://o")
store.add_triplet(triplet)

# Bulk load
triplets = [Triplet(f"http://s{i}", "http://p", "http://o") for i in range(1000)]
store.add_triplets(triplets)
```

### Querying

```python
query = """
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o
}
LIMIT 10
"""
results = store.execute_query(query)
```

### Named Graph Partitions

Use named graphs to partition RDF data inside one store while keeping backward compatibility.

```python
from veritasreason.semantic_extract.triplet_extractor import Triplet

# Write into a specific graph partition
store.add_triplet(
    Triplet("http://entity/1", "http://relation/type", "http://TypeA"),
    graph="http://example.org/graphs/partition-a",
)

# Query only one graph as default dataset
result_a = store.execute_query(
    "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
    graph="http://example.org/graphs/partition-a",
)

# Query multiple named graphs (use GRAPH pattern in WHERE)
result_multi = store.execute_query(
    """
    SELECT ?g ?s ?p ?o WHERE {
      GRAPH ?g { ?s ?p ?o }
    }
    """,
    graphs=[
        "http://example.org/graphs/partition-a",
        "http://example.org/graphs/partition-b",
    ],
)
```

Notes:
- `graph` injects `FROM <...>` before `WHERE`.
- `graphs` injects `FROM NAMED <...>` before `WHERE`.
- If not provided, existing behavior is unchanged.

### Alignment-Aware Queries

In complex enterprise environments with multiple data sources, you may want queries to seamlessly retrieve instances across aligned classes. For example, retrieving all http://schema.org/Person instances when querying for your internal http://internal.org/ontology/Employee class.

The QueryEngine provides helper methods to expand entity URIs based on stored alignments (e.g., owl:equivalentClass, owl:sameAs, skos:exactMatch) and safely inject them into your queries using SPARQL VALUES clauses.

Expanding URIs in Queries
You can expand a URI and build an alignment-aware query dynamically:

```python
from veritasreason.triplet_store.query_engine import QueryEngine

engine = QueryEngine()

# i) Expand the base URI to include all aligned equivalents
expanded_uris = engine.expand_entity_uri(
    entity_uri="[http://internal.org/ontology/Employee](http://internal.org/ontology/Employee)",
    store_backend=store_backend,
    use_alignments=True
)

# ii) Build a SPARQL VALUES clause
values_clause = engine.build_values_clause("entity_class", expanded_uris)
# Result: VALUES ?entity_class { [http://internal.org/ontology/Employee](http://internal.org/ontology/Employee) [http://schema.org/Person](http://schema.org/Person) }

# iii) Inject the clause into your query template
query = f"""
SELECT ?instance ?name WHERE {{
    {values_clause}
    ?instance a ?entity_class .
    ?instance [http://schema.org/name](http://schema.org/name) ?name .
}}
"""

# Execute the query to retrieve results across all aligned ontologies
results = engine.execute_query(query, store_backend)
```
