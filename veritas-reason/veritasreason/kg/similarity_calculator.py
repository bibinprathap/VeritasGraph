"""
Similarity Calculator Module

This module provides comprehensive similarity calculation algorithms for node embeddings and
graph analysis, enabling structural similarity assessment and comparison.

Supported Algorithms:
    - Cosine similarity: Measures angular similarity between embedding vectors
    - Euclidean distance: Calculates straight-line distance between vectors
    - Manhattan distance: Computes L1 distance (sum of absolute differences)
    - Pearson correlation: Measures linear correlation between embedding vectors
    - Batch similarity: Efficient similarity computation for multiple embeddings
    - Pairwise similarity: All-vs-all similarity matrix computation

Key Features:
    - Individual similarity calculations (cosine, euclidean, manhattan, correlation)
    - Batch similarity computation for performance optimization
    - Pairwise similarity matrix generation
    - Sparse matrix operations for large-scale datasets
    - Configurable similarity methods and normalization options

Main Classes:
    - SimilarityCalculator: Comprehensive similarity calculation engine

Methods:
    - cosine_similarity(): Calculate cosine similarity between two vectors
    - euclidean_distance(): Calculate Euclidean distance between vectors
    - manhattan_distance(): Calculate Manhattan distance between vectors
    - correlation_similarity(): Calculate Pearson correlation similarity
    - batch_similarity(): Compute similarities for multiple embeddings
    - pairwise_similarity(): Generate all-vs-all similarity matrix
    - find_most_similar(): Find top-k most similar embeddings

Example Usage:
    >>> from veritasreason.kg import SimilarityCalculator
    >>> calc = SimilarityCalculator()
    >>> similarity = calc.cosine_similarity(embedding1, embedding2)
    >>> similarities = calc.batch_similarity(embeddings, query_embedding)
    >>> most_similar = calc.find_most_similar(embeddings, query_embedding, top_k=5)

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import sparse
from scipy.spatial.distance import cdist

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class SimilarityCalculator:
    """
    Similarity calculation engine for node embeddings and graph analysis.
    
    This class provides various similarity metrics for comparing node embeddings
    and assessing structural similarity in knowledge graphs. It supports both
    individual and batch similarity calculations with optimized performance.
    
    Supported Similarity Metrics:
        - cosine: Cosine similarity (default, good for embeddings)
        - euclidean: Euclidean distance
        - manhattan: Manhattan distance
        - correlation: Pearson correlation
    
    Features:
        - Multiple similarity metrics
        - Efficient batch calculations
        - Sparse matrix operations for large datasets
        - Configurable distance metrics
        - Vectorized operations for performance
    
    Example Usage:
        >>> calc = SimilarityCalculator(method="cosine")
        >>> # Individual similarity
        >>> similarity = calc.cosine_similarity(embedding1, embedding2)
        >>> # Batch similarity
        >>> similarities = calc.batch_similarity(embeddings, query_embedding)
        >>> # Distance calculation
        >>> distance = calc.euclidean_distance(embedding1, embedding2)
    """
    
    def __init__(self, method: str = "cosine", normalize: bool = True):
        """
        Initialize the similarity calculator.
        
        Args:
            method: Default similarity method ("cosine", "euclidean", "manhattan", "correlation")
            normalize: Whether to normalize vectors before similarity calculation
        """
        self.method = method
        self.normalize = normalize
        
        self.logger = get_logger(__name__)
        self.progress_tracker = get_progress_tracker()
        
        if method not in ["cosine", "euclidean", "manhattan", "correlation"]:
            raise ValueError(f"Unsupported similarity method: {method}")
    
    def cosine_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vector1: First vector
            vector2: Second vector
            
        Returns:
            Cosine similarity score (-1 to 1)
            
        Raises:
            ValueError: If vectors have different dimensions or contain invalid values
        """
        if len(vector1) != len(vector2):
            raise ValueError("Embedding vectors must have the same dimension")
        
        # Check for invalid values
        vec1 = np.array(vector1, dtype=float)
        vec2 = np.array(vector2, dtype=float)
        
        if np.any(np.isinf(vec1)) or np.any(np.isnan(vec1)) or np.any(np.isinf(vec2)) or np.any(np.isnan(vec2)):
            raise ValueError("Vectors contain infinity or NaN values")
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def euclidean_distance(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate Euclidean distance between two embedding vectors.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Euclidean distance (non-negative)
            
        Raises:
            ValueError: If vectors have different dimensions
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embedding vectors must have the same dimension")
        
        vec1 = np.array(embedding1, dtype=np.float64)
        vec2 = np.array(embedding2, dtype=np.float64)
        
        return np.linalg.norm(vec1 - vec2)
    
    def manhattan_distance(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate Manhattan distance between two embedding vectors.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Manhattan distance (non-negative)
            
        Raises:
            ValueError: If vectors have different dimensions
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embedding vectors must have the same dimension")
        
        vec1 = np.array(embedding1, dtype=np.float64)
        vec2 = np.array(embedding2, dtype=np.float64)
        
        return np.sum(np.abs(vec1 - vec2))
    
    def correlation_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate Pearson correlation similarity between two embedding vectors.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Pearson correlation coefficient between -1 and 1
            
        Raises:
            ValueError: If vectors have different dimensions or insufficient length
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embedding vectors must have the same dimension")
        
        if len(embedding1) < 2:
            raise ValueError("Vectors must have at least 2 elements for correlation")
        
        vec1 = np.array(embedding1, dtype=np.float64)
        vec2 = np.array(embedding2, dtype=np.float64)
        
        # Calculate Pearson correlation
        correlation = np.corrcoef(vec1, vec2)[0, 1]
        
        # Handle NaN case (constant vectors)
        if np.isnan(correlation):
            return 0.0
        
        return correlation
    
    def batch_similarity(
        self,
        embeddings: Dict[str, List[float]],
        query_embedding: List[float],
        method: str = None,
        top_k: int = None,
        chunk_size: int = 1000
    ) -> Dict[str, float]:
        """
        Calculate similarity between query embedding and all embeddings.
        
        Args:
            embeddings: Dictionary of node embeddings
            query_embedding: Query embedding vector
            method: Similarity method (uses default if None)
            top_k: Number of top results to return
            chunk_size: Process embeddings in chunks for memory efficiency
            
        Returns:
            Dictionary of node IDs to similarity scores
        """
        if method is None:
            method = self.method
        
        if top_k is not None and top_k <= 0:
            return {}
        
        if not embeddings:
            return {}
        
        method = method or self.method
        query_vec = np.array(query_embedding, dtype=np.float64)
        
        # Validate dimensions
        sample_embedding = next(iter(embeddings.values()))
        if len(query_embedding) != len(sample_embedding):
            raise ValueError(f"Query embedding dimension {len(query_embedding)} "
                           f"does not match sample embedding dimension {len(sample_embedding)}")
        
        # For large datasets, process in chunks to manage memory
        if len(embeddings) > chunk_size:
            similarities = {}
            node_ids = list(embeddings.keys())
            
            for i in range(0, len(node_ids), chunk_size):
                chunk_node_ids = node_ids[i:i + chunk_size]
                chunk_embeddings = {node_id: embeddings[node_id] for node_id in chunk_node_ids}
                
                # Convert chunk to numpy matrix for efficient computation
                embedding_matrix = np.array([chunk_embeddings[node_id] for node_id in chunk_node_ids], dtype=np.float64)
                
                # Compute similarities for chunk
                if method == "cosine":
                    chunk_similarities = self._batch_cosine_similarity(embedding_matrix, query_vec)
                elif method == "euclidean":
                    distances = self._batch_euclidean_distance(embedding_matrix, query_vec)
                    chunk_similarities = 1.0 / (1.0 + distances)
                elif method == "manhattan":
                    distances = self._batch_manhattan_distance(embedding_matrix, query_vec)
                    chunk_similarities = 1.0 / (1.0 + distances)
                elif method == "correlation":
                    chunk_similarities = self._batch_correlation_similarity(embedding_matrix, query_vec)
                else:
                    raise ValueError(f"Unsupported similarity method: {method}")
                
                # Add chunk results
                similarities.update(dict(zip(chunk_node_ids, chunk_similarities)))
        else:
            # For smaller datasets, use existing efficient method
            node_ids = list(embeddings.keys())
            embedding_matrix = np.array([embeddings[node_id] for node_id in node_ids], dtype=np.float64)
            
            if method == "cosine":
                similarities = self._batch_cosine_similarity(embedding_matrix, query_vec)
            elif method == "euclidean":
                distances = self._batch_euclidean_distance(embedding_matrix, query_vec)
                similarities = 1.0 / (1.0 + distances)
            elif method == "manhattan":
                distances = self._batch_manhattan_distance(embedding_matrix, query_vec)
                similarities = 1.0 / (1.0 + distances)
            elif method == "correlation":
                similarities = self._batch_correlation_similarity(embedding_matrix, query_vec)
            else:
                raise ValueError(f"Unsupported similarity method: {method}")
            
            similarities = dict(zip(node_ids, similarities))
        
        # Return top-k if specified
        if top_k is not None:
            sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_similarities[:top_k])
        
        return similarities
    
    def pairwise_similarity(
        self,
        embeddings: Dict[str, List[float]],
        method: Optional[str] = None
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate pairwise similarities between all embeddings.
        
        Args:
            embeddings: Dictionary of node embeddings
            method: Similarity method to use (overrides default)
            
        Returns:
            Dictionary of node pairs to similarity scores
            
        Raises:
            ValueError: If embeddings have inconsistent dimensions
        """
        if len(embeddings) < 2:
            return {}
        
        method = method or self.method
        node_ids = list(embeddings.keys())
        embedding_matrix = np.array([embeddings[node_id] for node_id in node_ids])
        
        # Calculate pairwise similarity matrix
        if method == "cosine":
            similarity_matrix = self._pairwise_cosine_similarity(embedding_matrix)
        elif method == "euclidean":
            distance_matrix = self._pairwise_euclidean_distance(embedding_matrix)
            similarity_matrix = 1.0 / (1.0 + distance_matrix)
        elif method == "manhattan":
            distance_matrix = self._pairwise_manhattan_distance(embedding_matrix)
            similarity_matrix = 1.0 / (1.0 + distance_matrix)
        elif method == "correlation":
            similarity_matrix = self._pairwise_correlation_similarity(embedding_matrix)
        else:
            raise ValueError(f"Unsupported similarity method: {method}")
        
        # Convert to dictionary
        result = {}
        for i, node_id1 in enumerate(node_ids):
            for j, node_id2 in enumerate(node_ids):
                if i < j:  # Only store upper triangle to avoid duplicates
                    result[(node_id1, node_id2)] = similarity_matrix[i, j]
        
        return result
    
    def find_most_similar(
        self,
        embeddings: Dict[str, List[float]],
        query_embedding: List[float],
        top_k: int = 10,
        method: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Find most similar nodes to a query embedding.
        
        Args:
            embeddings: Dictionary of node embeddings
            query_embedding: Query embedding vector
            top_k: Number of most similar nodes to return
            method: Similarity method to use (overrides default)
            
        Returns:
            List of (node_id, similarity) tuples sorted by similarity
        """
        if top_k <= 0:
            return []
        
        similarities = self.batch_similarity(embeddings, query_embedding, method)
        
        # Sort by similarity and return top-k
        sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        return sorted_similarities[:top_k]
    
    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """Normalize a vector to unit length."""
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    def _batch_cosine_similarity(self, embedding_matrix: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
        """Calculate cosine similarities for batch of embeddings."""
        # Normalize vectors
        normalized_embeddings = embedding_matrix / np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        normalized_query = query_vec / np.linalg.norm(query_vec)
        
        # Handle zero vectors
        normalized_embeddings = np.nan_to_num(normalized_embeddings)
        normalized_query = np.nan_to_num(normalized_query)
        
        # Calculate cosine similarities
        similarities = np.dot(normalized_embeddings, normalized_query)
        return similarities
    
    def _batch_euclidean_distance(self, embedding_matrix: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
        """Calculate Euclidean distances for batch of embeddings."""
        return np.linalg.norm(embedding_matrix - query_vec, axis=1)
    
    def _batch_manhattan_distance(self, embedding_matrix: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
        """Calculate Manhattan distances for batch of embeddings."""
        return np.sum(np.abs(embedding_matrix - query_vec), axis=1)
    
    def _batch_correlation_similarity(self, embedding_matrix: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
        """Calculate correlation similarities for batch of embeddings."""
        similarities = []
        for embedding in embedding_matrix:
            corr = np.corrcoef(embedding, query_vec)[0, 1]
            similarities.append(0.0 if np.isnan(corr) else corr)
        return np.array(similarities)
    
    def _pairwise_cosine_similarity(self, embedding_matrix: np.ndarray) -> np.ndarray:
        """Calculate pairwise cosine similarity matrix."""
        # Normalize vectors
        normalized = embedding_matrix / np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        normalized = np.nan_to_num(normalized)
        
        # Calculate similarity matrix
        similarity_matrix = np.dot(normalized, normalized.T)
        return similarity_matrix
    
    def _pairwise_euclidean_distance(self, embedding_matrix: np.ndarray) -> np.ndarray:
        """Calculate pairwise Euclidean distance matrix."""
        return cdist(embedding_matrix, embedding_matrix, metric='euclidean')
    
    def _pairwise_manhattan_distance(self, embedding_matrix: np.ndarray) -> np.ndarray:
        """Calculate pairwise Manhattan distance matrix."""
        return cdist(embedding_matrix, embedding_matrix, metric='cityblock')
    
    def _pairwise_correlation_similarity(self, embedding_matrix: np.ndarray) -> np.ndarray:
        """Calculate pairwise correlation similarity matrix."""
        return np.corrcoef(embedding_matrix)
