"""
Graph Embedding Manager Module

This module provides utilities for managing embeddings specifically for graph databases,
including entity embedding, relationship embedding, and integration helpers for various
graph DB backends.

Key Features:
    - Generate embeddings for graph entities (nodes)
    - Generate embeddings for graph relationships (edges)
    - Format embeddings for graph DB storage
    - Integration helpers for Neo4j, NetworkX, FalkorDB

Example Usage:
    >>> from veritasreason.embeddings import GraphEmbeddingManager
    >>> manager = GraphEmbeddingManager()
    >>> node_embeddings = manager.create_node_embeddings(entities, backend="neo4j")
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from .embedding_generator import EmbeddingGenerator


class GraphEmbeddingManager:
    """
    Manager for embeddings in graph database contexts.

    This class provides utilities for generating and managing embeddings
    specifically for graph database storage, including node and edge embeddings.
    Supports multiple graph DB backends with backend-specific optimizations.

    Supported Backends:
        - Neo4j: Graph database with Cypher query language
        - NetworkX: Python graph library
        - FalkorDB: Redis-based graph database

    Example Usage:
        >>> manager = GraphEmbeddingManager()
        >>> # Create node embeddings
        >>> node_embeddings = manager.create_node_embeddings(
        ...     entities,
        ...     backend="neo4j"
        ... )
        >>> # Create edge embeddings
        >>> edge_embeddings = manager.create_edge_embeddings(
        ...     relationships,
        ...     backend="neo4j"
        ... )
    """

    def __init__(self, embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize graph embedding manager.

        Args:
            embedding_generator: Optional EmbeddingGenerator instance for
                               generating embeddings if needed
        """
        self.logger = get_logger("graph_embedding_manager")
        self.embedding_generator = embedding_generator or EmbeddingGenerator()

    def prepare_for_graph_db(
        self,
        entities: List[Dict[str, Any]],
        relationships: Optional[List[Dict[str, Any]]] = None,
        backend: str = "neo4j",
        **options,
    ) -> Dict[str, Any]:
        """
        Prepare embeddings for graph database storage.

        Generates and formats embeddings for both entities (nodes) and relationships (edges)
        according to backend-specific requirements.

        Args:
            entities: List of entity dictionaries with at least "id" and "text" or "content"
            relationships: Optional list of relationship dictionaries with
                         "source", "target", and optionally "text" or "type"
            backend: Graph DB backend ("neo4j", "networkx", "falkordb")
            **options: Additional backend-specific options

        Returns:
            Dictionary containing:
                - node_embeddings: Dictionary mapping node IDs to embeddings
                - edge_embeddings: Dictionary mapping edge IDs to embeddings (if provided)
                - nodes: Formatted node data with embeddings
                - edges: Formatted edge data with embeddings (if provided)
                - backend_info: Backend-specific information

        Raises:
            ProcessingError: If entities are invalid or backend is unsupported

        Example:
            >>> entities = [
            ...     {"id": "e1", "text": "Entity 1", "type": "Person"},
            ...     {"id": "e2", "text": "Entity 2", "type": "Organization"}
            ... ]
            >>> relationships = [
            ...     {"source": "e1", "target": "e2", "type": "WORKS_FOR"}
            ... ]
            >>> result = manager.prepare_for_graph_db(
            ...     entities, relationships, backend="neo4j"
            ... )
        """
        if backend.lower() not in ["neo4j", "networkx", "falkordb"]:
            raise ProcessingError(
                f"Unsupported backend: {backend}. "
                f"Supported: neo4j, networkx, falkordb"
            )

        # Generate node embeddings
        node_embeddings = self.create_node_embeddings(entities, backend=backend, **options)

        # Generate edge embeddings if relationships provided
        edge_embeddings = None
        if relationships:
            edge_embeddings = self.create_edge_embeddings(
                relationships, backend=backend, **options
            )

        # Format nodes with embeddings
        nodes = []
        for entity in entities:
            node_data = entity.copy()
            node_id = entity.get("id") or entity.get("node_id")
            if node_id and node_id in node_embeddings:
                node_data["embedding"] = node_embeddings[node_id]
            nodes.append(node_data)

        # Format edges with embeddings
        edges = []
        if relationships and edge_embeddings:
            for rel in relationships:
                edge_data = rel.copy()
                edge_id = self._get_edge_id(rel)
                if edge_id and edge_id in edge_embeddings:
                    edge_data["embedding"] = edge_embeddings[edge_id]
                edges.append(edge_data)

        result = {
            "node_embeddings": node_embeddings,
            "edge_embeddings": edge_embeddings,
            "nodes": nodes,
            "edges": edges,
            "backend": backend.lower(),
            "num_nodes": len(entities),
            "num_edges": len(relationships) if relationships else 0,
        }

        # Add backend-specific information
        result["backend_info"] = self._get_backend_info(backend, **options)

        return result

    def embed_entities(
        self,
        entities: List[Dict[str, Any]],
        text_field: str = "text",
        **options,
    ) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for graph entities.

        Creates embeddings for entities by extracting text content and generating
        embeddings using the embedding generator.

        Args:
            entities: List of entity dictionaries
            text_field: Field name containing text to embed (default: "text")
            **options: Additional embedding options

        Returns:
            Dictionary mapping entity IDs to embedding vectors

        Example:
            >>> entities = [
            ...     {"id": "e1", "text": "John Doe"},
            ...     {"id": "e2", "text": "Acme Corp"}
            ... ]
            >>> embeddings = manager.embed_entities(entities)
        """
        entity_embeddings = {}

        # Extract texts for batch processing
        texts = []
        entity_ids = []
        for entity in entities:
            entity_id = entity.get("id") or entity.get("node_id")
            if not entity_id:
                self.logger.warning(f"Entity missing ID, skipping: {entity}")
                continue

            # Get text content
            text = entity.get(text_field) or entity.get("content") or entity.get("name")
            if not text:
                self.logger.warning(f"Entity {entity_id} missing text content, skipping")
                continue

            texts.append(str(text))
            entity_ids.append(entity_id)

        if not texts:
            self.logger.warning("No valid entities found for embedding")
            return entity_embeddings

        # Generate embeddings in batch
        try:
            embeddings = self.embedding_generator.generate_embeddings(
                texts, data_type="text", **options
            )

            # Map embeddings to entity IDs
            for idx, entity_id in enumerate(entity_ids):
                if embeddings.ndim == 1:
                    entity_embeddings[entity_id] = embeddings
                else:
                    entity_embeddings[entity_id] = embeddings[idx]

        except Exception as e:
            self.logger.error(f"Failed to generate entity embeddings: {e}")
            raise ProcessingError(f"Failed to generate entity embeddings: {e}")

        return entity_embeddings

    def embed_relationships(
        self,
        relationships: List[Dict[str, Any]],
        text_field: Optional[str] = None,
        **options,
    ) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for graph relationships.

        Creates embeddings for relationships by extracting relationship text or
        combining source and target entity information.

        Args:
            relationships: List of relationship dictionaries
            text_field: Optional field name containing relationship text
                       If None, combines source and target information
            **options: Additional embedding options

        Returns:
            Dictionary mapping relationship IDs to embedding vectors

        Example:
            >>> relationships = [
            ...     {"source": "e1", "target": "e2", "type": "WORKS_FOR", "text": "works at"}
            ... ]
            >>> embeddings = manager.embed_relationships(relationships)
        """
        relationship_embeddings = {}

        # Extract texts for batch processing
        texts = []
        rel_ids = []
        for rel in relationships:
            rel_id = self._get_edge_id(rel)
            if not rel_id:
                self.logger.warning(f"Relationship missing ID, skipping: {rel}")
                continue

            # Get relationship text
            if text_field and text_field in rel:
                text = str(rel[text_field])
            else:
                # Combine relationship type and source/target info
                rel_type = rel.get("type", "")
                source = rel.get("source", "")
                target = rel.get("target", "")
                text = f"{rel_type} {source} {target}".strip()

            if not text:
                self.logger.warning(f"Relationship {rel_id} missing text content, skipping")
                continue

            texts.append(text)
            rel_ids.append(rel_id)

        if not texts:
            self.logger.warning("No valid relationships found for embedding")
            return relationship_embeddings

        # Generate embeddings in batch
        try:
            embeddings = self.embedding_generator.generate_embeddings(
                texts, data_type="text", **options
            )

            # Map embeddings to relationship IDs
            for idx, rel_id in enumerate(rel_ids):
                if embeddings.ndim == 1:
                    relationship_embeddings[rel_id] = embeddings
                else:
                    relationship_embeddings[rel_id] = embeddings[idx]

        except Exception as e:
            self.logger.error(f"Failed to generate relationship embeddings: {e}")
            raise ProcessingError(f"Failed to generate relationship embeddings: {e}")

        return relationship_embeddings

    def create_node_embeddings(
        self,
        entities: List[Dict[str, Any]],
        backend: str = "neo4j",
        **options,
    ) -> Dict[str, np.ndarray]:
        """
        Create embeddings for graph nodes (entities).

        Args:
            entities: List of entity dictionaries
            backend: Graph DB backend
            **options: Additional options

        Returns:
            Dictionary mapping node IDs to embedding vectors

        Example:
            >>> entities = [{"id": "n1", "text": "Node 1"}]
            >>> embeddings = manager.create_node_embeddings(entities, backend="neo4j")
        """
        return self.embed_entities(entities, **options)

    def create_edge_embeddings(
        self,
        relationships: List[Dict[str, Any]],
        backend: str = "neo4j",
        **options,
    ) -> Dict[str, np.ndarray]:
        """
        Create embeddings for graph edges (relationships).

        Args:
            relationships: List of relationship dictionaries
            backend: Graph DB backend
            **options: Additional options

        Returns:
            Dictionary mapping edge IDs to embedding vectors

        Example:
            >>> relationships = [{"source": "n1", "target": "n2", "type": "RELATES_TO"}]
            >>> embeddings = manager.create_edge_embeddings(relationships, backend="neo4j")
        """
        return self.embed_relationships(relationships, **options)

    def _get_edge_id(self, relationship: Dict[str, Any]) -> Optional[str]:
        """
        Get unique ID for a relationship.

        Args:
            relationship: Relationship dictionary

        Returns:
            Relationship ID or None if not available
        """
        # Try explicit ID fields
        edge_id = relationship.get("id") or relationship.get("edge_id") or relationship.get("rel_id")
        if edge_id:
            return str(edge_id)

        # Generate ID from source, target, and type
        source = relationship.get("source")
        target = relationship.get("target")
        rel_type = relationship.get("type", "")

        if source and target:
            return f"{source}_{rel_type}_{target}"

        return None

    def _get_backend_info(self, backend: str, **options) -> Dict[str, Any]:
        """
        Get backend-specific information.

        Args:
            backend: Graph DB backend name
            **options: Additional options

        Returns:
            Dictionary with backend-specific information
        """
        info = {"backend": backend.lower()}

        # Add backend-specific details
        if backend.lower() == "neo4j":
            info["database"] = options.get("database", "neo4j")
            info["label"] = options.get("label", "Node")
        elif backend.lower() == "networkx":
            info["graph_type"] = options.get("graph_type", "DiGraph")
        elif backend.lower() == "falkordb":
            info["graph_name"] = options.get("graph_name", "default")

        return info

