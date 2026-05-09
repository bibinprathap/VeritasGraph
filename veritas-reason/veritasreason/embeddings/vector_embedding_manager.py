"""
Vector Embedding Manager Module

This module provides utilities for managing embeddings specifically for vector databases,
including formatting, validation, and integration helpers for various vector DB backends.

Key Features:
    - Format embeddings for vector DB storage
    - Validate embedding dimensions for different backends
    - Normalize embeddings for vector DB requirements
    - Create metadata compatible with vector DBs
    - Integration helpers for FAISS, Weaviate, Qdrant, Milvus

Example Usage:
    >>> from veritasreason.embeddings import VectorEmbeddingManager
    >>> manager = VectorEmbeddingManager()
    >>> formatted = manager.prepare_for_vector_db(embeddings, metadata, backend="faiss")
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from .embedding_generator import EmbeddingGenerator


class VectorEmbeddingManager:
    """
    Manager for embeddings in vector database contexts.

    This class provides utilities for preparing, validating, and formatting
    embeddings specifically for vector database storage and retrieval.
    Supports multiple vector DB backends with backend-specific optimizations.

    Supported Backends:
        - FAISS: Local vector storage
        - Weaviate: GraphQL-based vector database
        - Qdrant: Vector similarity search engine
        - Milvus: Open-source vector database

    Example Usage:
        >>> manager = VectorEmbeddingManager()
        >>> # Prepare embeddings for FAISS
        >>> formatted = manager.prepare_for_vector_db(
        ...     embeddings,
        ...     metadata=metadata_list,
        ...     backend="faiss"
        ... )
        >>> # Validate dimensions
        >>> is_valid = manager.validate_dimensions(embeddings, backend="weaviate")
    """

    def __init__(self, embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize vector embedding manager.

        Args:
            embedding_generator: Optional EmbeddingGenerator instance for
                               generating embeddings if needed
        """
        self.logger = get_logger("vector_embedding_manager")
        self.embedding_generator = embedding_generator or EmbeddingGenerator()

        # Backend-specific dimension requirements
        self.backend_requirements = {
            "faiss": {"min_dim": 1, "max_dim": None, "dtype": np.float32},
            "weaviate": {"min_dim": 1, "max_dim": None, "dtype": np.float32},
            "qdrant": {"min_dim": 1, "max_dim": None, "dtype": np.float32},
            "milvus": {"min_dim": 1, "max_dim": 32768, "dtype": np.float32},
        }

    def prepare_for_vector_db(
        self,
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None,
        backend: str = "faiss",
        normalize: bool = True,
        **options,
    ) -> Dict[str, Any]:
        """
        Prepare embeddings and metadata for vector database storage.

        Formats embeddings and metadata according to backend-specific requirements.
        Validates dimensions, normalizes if needed, and creates compatible data structures.

        Args:
            embeddings: Embeddings array (n_samples, embedding_dim) or (embedding_dim,)
            metadata: Optional list of metadata dictionaries (one per embedding)
            backend: Vector DB backend ("faiss", "weaviate", "qdrant", "milvus")
            normalize: Whether to normalize embeddings (default: True)
            **options: Additional backend-specific options

        Returns:
            Dictionary containing:
                - vectors: Formatted embeddings array
                - metadata: Formatted metadata (if provided)
                - ids: Generated IDs (if not provided in metadata)
                - backend_info: Backend-specific information

        Raises:
            ProcessingError: If embeddings are invalid or backend is unsupported

        Example:
            >>> embeddings = np.random.rand(10, 384).astype(np.float32)
            >>> metadata = [{"text": f"doc_{i}"} for i in range(10)]
            >>> result = manager.prepare_for_vector_db(
            ...     embeddings, metadata, backend="weaviate"
            ... )
        """
        if backend.lower() not in self.backend_requirements:
            raise ProcessingError(
                f"Unsupported backend: {backend}. "
                f"Supported: {list(self.backend_requirements.keys())}"
            )

        # Validate embeddings
        if not self.validate_dimensions(embeddings, backend):
            raise ProcessingError(
                f"Embeddings do not meet requirements for backend: {backend}"
            )

        # Normalize embeddings if requested
        if normalize:
            embeddings = self.normalize_for_storage(embeddings)

        # Ensure correct dtype
        req = self.backend_requirements[backend.lower()]
        if embeddings.dtype != req["dtype"]:
            embeddings = embeddings.astype(req["dtype"])

        # Handle single embedding vs batch
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        # Prepare metadata
        formatted_metadata = None
        if metadata:
            formatted_metadata = self.create_metadata(
                metadata, backend=backend, **options
            )

        # Generate IDs if not provided
        ids = options.get("ids")
        if ids is None:
            ids = [f"vec_{i}" for i in range(len(embeddings))]

        result = {
            "vectors": embeddings,
            "metadata": formatted_metadata,
            "ids": ids,
            "backend": backend.lower(),
            "shape": embeddings.shape,
            "dtype": str(embeddings.dtype),
        }

        # Add backend-specific information
        result["backend_info"] = self._get_backend_info(backend, embeddings, **options)

        return result

    def batch_prepare(
        self,
        embeddings_list: List[np.ndarray],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        backend: str = "faiss",
        **options,
    ) -> Dict[str, Any]:
        """
        Prepare multiple embedding batches for vector database storage.

        Args:
            embeddings_list: List of embedding arrays
            metadata_list: Optional list of metadata lists (one per embedding batch)
            backend: Vector DB backend
            **options: Additional options

        Returns:
            Dictionary with prepared data for all batches
        """
        all_embeddings = []
        all_metadata = []
        all_ids = []

        for idx, embeddings in enumerate(embeddings_list):
            metadata = metadata_list[idx] if metadata_list else None
            batch_ids = options.get("ids")
            if batch_ids:
                batch_ids = batch_ids[idx] if isinstance(batch_ids[0], list) else None

            prepared = self.prepare_for_vector_db(
                embeddings, metadata, backend, ids=batch_ids, **options
            )

            all_embeddings.append(prepared["vectors"])
            if prepared["metadata"]:
                all_metadata.extend(prepared["metadata"])
            all_ids.extend(prepared["ids"])

        # Concatenate all embeddings
        combined_embeddings = np.vstack(all_embeddings)

        return {
            "vectors": combined_embeddings,
            "metadata": all_metadata if all_metadata else None,
            "ids": all_ids,
            "backend": backend.lower(),
            "shape": combined_embeddings.shape,
            "num_batches": len(embeddings_list),
        }

    def validate_dimensions(
        self, embeddings: np.ndarray, backend: str
    ) -> bool:
        """
        Validate embedding dimensions for vector database backend.

        Checks if embeddings meet the dimension requirements for the specified backend.

        Args:
            embeddings: Embeddings array to validate
            backend: Vector DB backend name

        Returns:
            bool: True if dimensions are valid, False otherwise

        Example:
            >>> is_valid = manager.validate_dimensions(embeddings, backend="weaviate")
        """
        if backend.lower() not in self.backend_requirements:
            self.logger.warning(f"Unknown backend: {backend}, skipping validation")
            return True

        req = self.backend_requirements[backend.lower()]

        # Handle single embedding
        if embeddings.ndim == 1:
            dim = len(embeddings)
        else:
            dim = embeddings.shape[1]

        # Check dimension constraints
        if req["min_dim"] is not None and dim < req["min_dim"]:
            self.logger.error(
                f"Dimension {dim} below minimum {req['min_dim']} for {backend}"
            )
            return False

        if req["max_dim"] is not None and dim > req["max_dim"]:
            self.logger.error(
                f"Dimension {dim} above maximum {req['max_dim']} for {backend}"
            )
            return False

        return True

    def normalize_for_storage(
        self, embeddings: np.ndarray, method: str = "l2"
    ) -> np.ndarray:
        """
        Normalize embeddings for vector database storage.

        Normalizes embeddings according to the specified method. L2 normalization
        is standard for cosine similarity in most vector databases.

        Args:
            embeddings: Embeddings array to normalize
            method: Normalization method ("l2" for L2 normalization)

        Returns:
            np.ndarray: Normalized embeddings

        Example:
            >>> normalized = manager.normalize_for_storage(embeddings)
        """
        if method == "l2":
            # L2 normalization
            if embeddings.ndim == 1:
                norm = np.linalg.norm(embeddings)
                if norm > 0:
                    return embeddings / norm
                return embeddings
            else:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1  # Avoid division by zero
                return embeddings / norms
        else:
            self.logger.warning(f"Unknown normalization method: {method}")
            return embeddings

    def create_metadata(
        self,
        metadata: List[Dict[str, Any]],
        backend: str = "faiss",
        **options,
    ) -> List[Dict[str, Any]]:
        """
        Create metadata compatible with vector database backend.

        Formats metadata according to backend-specific requirements and constraints.

        Args:
            metadata: List of metadata dictionaries
            backend: Vector DB backend
            **options: Additional formatting options

        Returns:
            List of formatted metadata dictionaries

        Example:
            >>> metadata = [{"text": "doc1", "category": "science"}]
            >>> formatted = manager.create_metadata(metadata, backend="weaviate")
        """
        formatted = []

        for meta in metadata:
            # Create a copy to avoid modifying original
            formatted_meta = meta.copy()

            # Backend-specific formatting
            if backend.lower() == "weaviate":
                # Weaviate uses specific property types
                # Ensure values are compatible
                formatted_meta = {
                    k: v
                    for k, v in formatted_meta.items()
                    if v is not None
                }
            elif backend.lower() == "qdrant":
                # Qdrant supports various payload types
                formatted_meta = {
                    k: v
                    for k, v in formatted_meta.items()
                    if v is not None
                }

            formatted.append(formatted_meta)

        return formatted

    def _get_backend_info(
        self, backend: str, embeddings: np.ndarray, **options
    ) -> Dict[str, Any]:
        """
        Get backend-specific information for embeddings.

        Args:
            backend: Vector DB backend name
            embeddings: Embeddings array
            **options: Additional options

        Returns:
            Dictionary with backend-specific information
        """
        info = {
            "backend": backend.lower(),
            "num_vectors": len(embeddings),
            "dimension": embeddings.shape[1] if embeddings.ndim > 1 else len(embeddings),
            "dtype": str(embeddings.dtype),
        }

        # Add backend-specific details
        if backend.lower() == "faiss":
            info["index_type"] = options.get("index_type", "flat")
        elif backend.lower() == "weaviate":
            info["class_name"] = options.get("class_name", "Document")

        return info

