"""
Graph Store Module

This module provides comprehensive property graph database integration for
the VeritasReason framework, supporting multiple graph database backends including
Neo4j and FalkorDB for storing and querying knowledge graphs.

Algorithms Used:

Graph Store Management:
    - Store Registration: Store type detection, store factory pattern,
      configuration management, default store selection
    - Backend Pattern: Unified interface for multiple backends (Neo4j,
      FalkorDB), backend instantiation, backend-specific operation delegation
    - Store Selection: Default store resolution, store ID lookup,
      store validation

Node and Relationship Operations:
    - Node Creation: Single node insertion, batch node insertion,
      property validation, label management, backend delegation
    - Node Retrieval: Pattern matching (label/property filtering),
      Cypher query construction, result extraction, node reconstruction
    - Node Update: Property update, label modification, atomic update
      operations, conflict detection
    - Node Deletion: Node matching, cascade deletion (optional),
      deletion operation delegation, result verification
    - Relationship Creation: Single relationship insertion, batch insertion,
      property validation, type management
    - Relationship Retrieval: Pattern matching, path queries, traversal queries
    - Relationship Update: Property update, type modification
    - Relationship Deletion: Relationship matching, deletion operation
      delegation

Graph Query Execution:
    - Cypher Query: Full Cypher query language support for Neo4j and
      FalkorDB (OpenCypher)
    - Pattern Matching: Node and relationship pattern matching, variable
      binding, path matching
    - Graph Traversal: BFS/DFS traversal, shortest path algorithms,
      path finding
    - Aggregation: COUNT, SUM, AVG, MIN, MAX operations, GROUP BY support
    - Query Optimization: Query caching, execution plan analysis,
      index utilization

Graph Analytics:
    - Centrality Algorithms: Degree centrality, betweenness centrality,
      PageRank, closeness centrality
    - Community Detection: Label propagation, Louvain modularity,
      connected components
    - Path Algorithms: Shortest path, all shortest paths, Dijkstra,
      A* pathfinding
    - Similarity: Node similarity, Jaccard similarity, cosine similarity

Store Backends:
    - Neo4j Store: Official Neo4j Python driver, Bolt protocol
      communication, transaction support, multi-database support,
      APOC procedures
    - FalkorDB Store: Redis-based graph database, sparse matrix
      representation, linear algebra queries, OpenCypher support,
      ultra-fast performance

Bulk Operations:
    - Batch Processing: Chunking algorithm (fixed-size batch creation),
      batch size optimization, memory management for large datasets
    - Transaction Management: ACID transaction support, batch commits,
      rollback on failure
    - Progress Tracking: Load progress calculation, elapsed time tracking,
      throughput calculation

Key Features:
    - Multi-backend property graph support (Neo4j, FalkorDB)
    - Full Cypher/OpenCypher query language support
    - Node and relationship CRUD operations
    - Graph traversal and path finding
    - Graph analytics and algorithms
    - Bulk data loading with progress tracking
    - Transaction support with rollback
    - Index and constraint management
    - Method registry for extensibility
    - Configuration management with environment variables and config files

Main Classes:
    - GraphStore: Main graph store interface
    - GraphManager: Graph store management and operations
    - Neo4jStore: Neo4j integration store
    - FalkorDBStore: FalkorDB integration store
    - NodeManager: Node CRUD operations
    - RelationshipManager: Relationship CRUD operations
    - QueryEngine: Cypher query execution and optimization
    - GraphAnalytics: Graph algorithms and analytics

Convenience Functions:
    - create_node: Create node wrapper
    - create_relationship: Create relationship wrapper
    - get_nodes: Get nodes wrapper
    - get_relationships: Get relationships wrapper
    - update_node: Update node wrapper
    - delete_node: Delete node wrapper
    - execute_query: Execute Cypher query wrapper
    - run_analytics: Run graph analytics wrapper
    - get_graph_store_method: Get graph store method by task and name
    - list_available_methods: List registered graph store methods

Example Usage:
    >>> from veritasreason.graph_store import GraphStore, create_node, \
    ...     create_relationship, execute_query
    >>> # Using convenience functions
    >>> node_id = create_node(labels=["Person"],
    ...                       properties={"name": "Alice", "age": 30})
    >>> rel_id = create_relationship(start_id=node1_id, end_id=node2_id,
    ...                              rel_type="KNOWS",
    ...                              properties={"since": 2020})
    >>> results = execute_query("MATCH (p:Person) WHERE p.age > 25 "
    ...                         "RETURN p.name")
    >>> # Using classes directly
    >>> store = GraphStore(backend="neo4j", uri="bolt://localhost:7687")
    >>> node_id = store.create_node(labels=["Person"],
    ...                             properties={"name": "Bob"})
    >>> results = store.execute_query("MATCH (n) RETURN n LIMIT 10")

Author: VeritasReason Contributors
License: MIT
"""

from .age_store import ApacheAgeStore
from .amazon_neptune import (
    AmazonNeptuneStore,
    NeptuneAuthTokenManager,
    NeptuneDriver,
    NeptuneSession,
    NeptuneTransaction,
)
from .config import GraphStoreConfig, graph_store_config
from .falkordb_store import FalkorDBClient, FalkorDBGraph, FalkorDBStore
from .graph_store import (
    GraphAnalytics,
    GraphManager,
    GraphStore,
    NodeManager,
    QueryEngine,
    RelationshipManager,
)
from .methods import (
    create_node,
    create_nodes,
    create_relationship,
    create_relationships,
    delete_node,
    delete_relationship,
    execute_query,
    get_graph_store_method,
    get_neighbors,
    get_nodes,
    get_relationships,
    list_available_methods,
    run_analytics,
    shortest_path,
    update_node,
    update_relationship,
)
from .neo4j_store import Neo4jDriver, Neo4jStore, Neo4jTransaction
from .registry import MethodRegistry, method_registry

__all__ = [
    # Core graph store
    "GraphStore",
    "GraphManager",
    "NodeManager",
    "RelationshipManager",
    "QueryEngine",
    "GraphAnalytics",
    # Neo4j
    "Neo4jStore",
    "Neo4jDriver",
    "Neo4jTransaction",
    # Apache AGE
    "ApacheAgeStore",
    # Amazon Neptune
    "AmazonNeptuneStore",
    "NeptuneAuthTokenManager",
    "NeptuneDriver",
    "NeptuneSession",
    "NeptuneTransaction",
    # FalkorDB
    "FalkorDBStore",
    "FalkorDBClient",
    "FalkorDBGraph",
    # Convenience functions
    "create_node",
    "create_nodes",
    "create_relationship",
    "create_relationships",
    "get_nodes",
    "get_relationships",
    "get_neighbors",
    "update_node",
    "update_relationship",
    "delete_node",
    "delete_relationship",
    "execute_query",
    "shortest_path",
    "run_analytics",
    "get_graph_store_method",
    "list_available_methods",
    # Configuration and registry
    "GraphStoreConfig",
    "graph_store_config",
    "MethodRegistry",
    "method_registry",
]
