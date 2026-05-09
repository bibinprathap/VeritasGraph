"""
Pooling strategies for VeritasReason framework.

This module provides various pooling methods for
embedding generation and aggregation.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger


class PoolingStrategy:
    """Base class for pooling strategies."""

    def pool(self, embeddings: np.ndarray, **options) -> np.ndarray:
        """
        Pool embeddings.

        Args:
            embeddings: Input embeddings (n_embeddings, dim)
            **options: Pooling options

        Returns:
            np.ndarray: Pooled embedding (dim,)
        """
        # Base implementation - should be overridden
        # Default: return mean pooling
        if embeddings.ndim == 2:
            return embeddings.mean(axis=0)
        return embeddings


class MeanPooling(PoolingStrategy):
    """Mean pooling strategy."""

    def pool(self, embeddings: np.ndarray, **options) -> np.ndarray:
        """
        Apply mean pooling.

        Args:
            embeddings: Input embeddings
            **options: Pooling options

        Returns:
            np.ndarray: Mean-pooled embedding
        """
        if len(embeddings) == 0:
            raise ProcessingError("Cannot pool empty embeddings")

        return np.mean(embeddings, axis=0)


class MaxPooling(PoolingStrategy):
    """Max pooling strategy."""

    def pool(self, embeddings: np.ndarray, **options) -> np.ndarray:
        """
        Apply max pooling.

        Args:
            embeddings: Input embeddings
            **options: Pooling options

        Returns:
            np.ndarray: Max-pooled embedding
        """
        if len(embeddings) == 0:
            raise ProcessingError("Cannot pool empty embeddings")

        return np.max(embeddings, axis=0)


class CLSPooling(PoolingStrategy):
    """CLS token pooling strategy."""

    def pool(self, embeddings: np.ndarray, **options) -> np.ndarray:
        """
        Apply CLS token pooling (returns first embedding).

        Args:
            embeddings: Input embeddings
            **options: Pooling options

        Returns:
            np.ndarray: CLS token embedding
        """
        if len(embeddings) == 0:
            raise ProcessingError("Cannot pool empty embeddings")

        return embeddings[0]


class AttentionPooling(PoolingStrategy):
    """Attention-based pooling strategy."""

    def __init__(self, **config):
        """Initialize attention pooling."""
        self.logger = get_logger("attention_pooling")
        self.config = config

    def pool(self, embeddings: np.ndarray, **options) -> np.ndarray:
        """
        Apply attention-based pooling.

        Args:
            embeddings: Input embeddings
            **options: Pooling options

        Returns:
            np.ndarray: Attention-pooled embedding
        """
        if len(embeddings) == 0:
            raise ProcessingError("Cannot pool empty embeddings")

        # Simple attention: compute similarity weights
        # Use mean embedding as query
        query = np.mean(embeddings, axis=0)

        # Compute attention weights (dot product similarity)
        scores = np.dot(embeddings, query)
        scores = scores - np.max(scores)  # Numerical stability
        weights = np.exp(scores) / np.sum(np.exp(scores))

        # Weighted sum
        pooled = np.sum(embeddings * weights[:, np.newaxis], axis=0)

        return pooled


class HierarchicalPooling(PoolingStrategy):
    """Hierarchical pooling strategy."""

    def __init__(self, **config):
        """Initialize hierarchical pooling."""
        self.logger = get_logger("hierarchical_pooling")
        self.config = config
        self.first_level = MeanPooling()
        self.second_level = MeanPooling()

    def pool(self, embeddings: np.ndarray, **options) -> np.ndarray:
        """
        Apply hierarchical pooling.

        Args:
            embeddings: Input embeddings
            **options: Pooling options:
                - chunk_size: Size of first-level chunks

        Returns:
            np.ndarray: Hierarchically pooled embedding
        """
        if len(embeddings) == 0:
            raise ProcessingError("Cannot pool empty embeddings")

        chunk_size = options.get("chunk_size", 10)

        # First level: pool chunks
        chunked_embeddings = []
        for i in range(0, len(embeddings), chunk_size):
            chunk = embeddings[i : i + chunk_size]
            pooled_chunk = self.first_level.pool(chunk)
            chunked_embeddings.append(pooled_chunk)

        # Second level: pool all chunks
        chunked_array = np.array(chunked_embeddings)
        return self.second_level.pool(chunked_array)


class PoolingStrategyFactory:
    """Factory for creating pooling strategies."""

    @staticmethod
    def create(strategy: str, **config) -> PoolingStrategy:
        """
        Create pooling strategy.

        Args:
            strategy: Strategy name ("mean", "max", "cls", "attention", "hierarchical")
            **config: Strategy configuration

        Returns:
            PoolingStrategy: Pooling strategy instance
        """
        strategies = {
            "mean": MeanPooling,
            "max": MaxPooling,
            "cls": CLSPooling,
            "attention": AttentionPooling,
            "hierarchical": HierarchicalPooling,
        }

        strategy_class = strategies.get(strategy.lower())
        if not strategy_class:
            raise ProcessingError(f"Unsupported pooling strategy: {strategy}")

        return strategy_class(**config)
