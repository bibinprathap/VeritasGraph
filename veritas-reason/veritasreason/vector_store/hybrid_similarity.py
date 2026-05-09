"""
Hybrid Similarity Calculator Module

This module provides hybrid similarity calculation capabilities that combine semantic
and structural embeddings for decision tracking and precedent search.

Key Features:
    - Hybrid similarity calculation combining semantic + structural embeddings
    - Configurable weighting between similarity types
    - Precedent search with context-aware scoring
    - Multi-embedding support for decisions
    - Optimized similarity calculations using scipy

Algorithms Used:
    - Cosine Similarity: Primary similarity metric for vector comparisons
    - Pearson Correlation: Alternative similarity metric for correlation analysis
    - Euclidean Distance: Distance-based similarity calculation
    - Dot Product: Normalized dot product similarity
    - Weighted Averaging: Combines semantic + structural similarities
    - Context Enhancement: Multi-hop context-aware scoring
    - Batch Processing: Efficient similarity calculation for multiple vectors

Main Classes:
    - HybridSimilarityCalculator: Main hybrid similarity calculation engine

Example Usage:
    >>> from veritasreason.vector_store import HybridSimilarityCalculator
    >>> calculator = HybridSimilarityCalculator(semantic_weight=0.7, structural_weight=0.3)
    >>> similarity = calculator.calculate_hybrid_similarity(
    ...     semantic_vec1, structural_vec1, semantic_vec2, structural_vec2
    ... )
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from scipy.spatial.distance import cosine
from scipy.stats import pearsonr

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class HybridSimilarityCalculator:
    """
    Hybrid similarity calculator for combining semantic and structural embeddings.
    
    This class provides sophisticated similarity calculation capabilities that
    combine multiple embedding types with configurable weights, enabling
    enhanced decision tracking and precedent search.
    
    Features:
        - Semantic + structural embedding combination
        - Configurable similarity weights
        - Multiple similarity metrics (cosine, pearson, euclidean)
        - Batch similarity calculation
        - Context-aware scoring for decisions
        - Optimized calculations using scipy
    
    Example Usage:
        >>> calculator = HybridSimilarityCalculator(
        ...     semantic_weight=0.7, structural_weight=0.3
        ... )
        >>> similarity = calculator.calculate_hybrid_similarity(
        ...     semantic_vec1, structural_vec1, semantic_vec2, structural_vec2
        ... )
    """
    
    def __init__(
        self,
        semantic_weight: float = 0.7,
        structural_weight: float = 0.3,
        semantic_metric: str = "cosine",
        structural_metric: str = "cosine",
        normalization_method: str = "min_max"
    ):
        """
        Initialize hybrid similarity calculator.
        
        Args:
            semantic_weight: Weight for semantic similarity (0.0 to 1.0)
            structural_weight: Weight for structural similarity (0.0 to 1.0)
            semantic_metric: Similarity metric for semantic embeddings
            structural_metric: Similarity metric for structural embeddings
            normalization_method: Method for normalizing similarity scores
        """
        # Validate weights
        total_weight = semantic_weight + structural_weight
        if not np.isclose(total_weight, 1.0, atol=0.01):
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        self.semantic_metric = semantic_metric.lower()
        self.structural_metric = structural_metric.lower()
        self.normalization_method = normalization_method
        
        self.logger = get_logger(__name__)
        self.progress_tracker = get_progress_tracker()
        
        # Validate metrics
        valid_metrics = {"cosine", "pearson", "euclidean", "dot_product"}
        if self.semantic_metric not in valid_metrics:
            raise ValueError(f"Invalid semantic metric: {semantic_metric}")
        if self.structural_metric not in valid_metrics:
            raise ValueError(f"Invalid structural metric: {structural_metric}")
    
    def calculate_hybrid_similarity(
        self,
        semantic_vec1: np.ndarray,
        structural_vec1: np.ndarray,
        semantic_vec2: np.ndarray,
        structural_vec2: np.ndarray,
        weights: Optional[Tuple[float, float]] = None
    ) -> float:
        """
        Calculate hybrid similarity between two decision embeddings.
        
        Args:
            semantic_vec1: First semantic embedding
            structural_vec1: First structural embedding
            semantic_vec2: Second semantic embedding
            structural_vec2: Second structural embedding
            weights: Optional override for (semantic_weight, structural_weight)
            
        Returns:
            Hybrid similarity score (0.0 to 1.0)
        """
        if weights:
            sem_weight, struct_weight = weights
        else:
            sem_weight, struct_weight = self.semantic_weight, self.structural_weight
        
        # Calculate individual similarities
        semantic_sim = self._calculate_similarity(
            semantic_vec1, semantic_vec2, self.semantic_metric
        )
        structural_sim = self._calculate_similarity(
            structural_vec1, structural_vec2, self.structural_metric
        )
        
        # Combine with weights
        hybrid_sim = (sem_weight * semantic_sim) + (struct_weight * structural_sim)
        
        return float(hybrid_sim)
    
    def calculate_batch_hybrid_similarity(
        self,
        query_semantic: np.ndarray,
        query_structural: np.ndarray,
        candidate_semantics: List[np.ndarray],
        candidate_structurals: List[np.ndarray],
        weights: Optional[Tuple[float, float]] = None
    ) -> List[float]:
        """
        Calculate hybrid similarities for a batch of candidates.
        
        Args:
            query_semantic: Query semantic embedding
            query_structural: Query structural embedding
            candidate_semantics: List of candidate semantic embeddings
            candidate_structurals: List of candidate structural embeddings
            weights: Optional override for similarity weights
            
        Returns:
            List of hybrid similarity scores
        """
        if len(candidate_semantics) != len(candidate_structurals):
            raise ValueError("Candidate lists must have same length")
        
        similarities = []
        for sem_vec, struct_vec in zip(candidate_semantics, candidate_structurals):
            sim = self.calculate_hybrid_similarity(
                query_semantic, query_structural, sem_vec, struct_vec, weights
            )
            similarities.append(sim)
        
        return similarities
    
    def find_most_similar_decisions(
        self,
        query_semantic: np.ndarray,
        query_structural: np.ndarray,
        candidate_embeddings: List[Tuple[np.ndarray, np.ndarray]],
        candidate_metadata: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        weights: Optional[Tuple[float, float]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find most similar decisions with optional filtering.
        
        Args:
            query_semantic: Query semantic embedding
            query_structural: Query structural embedding
            candidate_embeddings: List of (semantic, structural) tuples
            candidate_metadata: Optional metadata for candidates
            top_k: Number of results to return
            weights: Optional similarity weight override
            filters: Optional metadata filters
            
        Returns:
            List of similar decisions with scores and metadata
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="vector_store",
            submodule="HybridSimilarityCalculator",
            message=f"Finding {top_k} most similar decisions"
        )
        
        try:
            # Apply filters if metadata provided
            if candidate_metadata and filters:
                filtered_indices = self._apply_filters(candidate_metadata, filters)
                filtered_embeddings = [candidate_embeddings[i] for i in filtered_indices]
                filtered_metadata = [candidate_metadata[i] for i in filtered_indices]
            else:
                filtered_embeddings = candidate_embeddings
                filtered_metadata = candidate_metadata or [{}] * len(candidate_embeddings)
                filtered_indices = list(range(len(candidate_embeddings)))
            
            # Calculate similarities
            candidate_semantics = [emb[0] for emb in filtered_embeddings]
            candidate_structurals = [emb[1] for emb in filtered_embeddings]
            
            similarities = self.calculate_batch_hybrid_similarity(
                query_semantic, query_structural,
                candidate_semantics, candidate_structurals, weights
            )
            
            # Sort by similarity
            sorted_results = sorted(
                enumerate(similarities),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]
            
            # Build results
            results = []
            for local_idx, similarity in sorted_results:
                original_idx = filtered_indices[local_idx]
                result = {
                    "similarity": similarity,
                    "semantic_similarity": self._calculate_similarity(
                        query_semantic, candidate_semantics[local_idx], self.semantic_metric
                    ),
                    "structural_similarity": self._calculate_similarity(
                        query_structural, candidate_structurals[local_idx], self.structural_metric
                    ),
                    "metadata": filtered_metadata[local_idx],
                    "index": original_idx
                }
                results.append(result)
            
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Found {len(results)} similar decisions"
            )
            return results
            
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise
    
    def calculate_context_aware_similarity(
        self,
        query_semantic: np.ndarray,
        query_structural: np.ndarray,
        candidate_embeddings: List[Tuple[np.ndarray, np.ndarray]],
        context_graph: Optional[Any] = None,
        context_weight: float = 0.1,
        max_hops: int = 2
    ) -> List[float]:
        """
        Calculate context-aware similarity using graph relationships.
        
        Args:
            query_semantic: Query semantic embedding
            query_structural: Query structural embedding
            candidate_embeddings: List of candidate embeddings
            context_graph: Optional context graph for relationship analysis
            context_weight: Weight for context similarity (0.0 to 1.0)
            max_hops: Maximum hops for context analysis
            
        Returns:
            List of context-aware similarity scores
        """
        base_similarities = self.calculate_batch_hybrid_similarity(
            query_semantic, query_structural,
            [emb[0] for emb in candidate_embeddings],
            [emb[1] for emb in candidate_embeddings]
        )
        
        if not context_graph or context_weight == 0.0:
            return base_similarities
        
        # Calculate context similarities
        context_similarities = self._calculate_context_similarities(
            candidate_embeddings, context_graph, max_hops
        )
        
        # Combine base and context similarities
        enhanced_similarities = []
        for base_sim, ctx_sim in zip(base_similarities, context_similarities):
            enhanced_sim = (1 - context_weight) * base_sim + context_weight * ctx_sim
            enhanced_similarities.append(enhanced_sim)
        
        return enhanced_similarities
    
    def _calculate_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """Calculate similarity between two vectors."""
        # Ensure vectors have same dimension
        if len(vec1) != len(vec2):
            # Pad the smaller vector to match the larger one
            if len(vec1) < len(vec2):
                vec1 = np.pad(vec1, (0, len(vec2) - len(vec1)))
            else:
                vec2 = np.pad(vec2, (0, len(vec1) - len(vec2)))
        
        if metric == "cosine":
            # Use scipy's cosine distance (returns distance, not similarity)
            sim = 1 - cosine(vec1, vec2)
            return 0.0 if np.isnan(sim) else float(sim)
        elif metric == "pearson":
            # Use scipy's pearson correlation
            correlation, _ = pearsonr(vec1, vec2)
            return correlation if not np.isnan(correlation) else 0.0
        elif metric == "euclidean":
            # Convert euclidean distance to similarity
            distance = np.linalg.norm(vec1 - vec2)
            return 1 / (1 + distance)
        elif metric == "dot_product":
            # Normalize vectors and compute dot product
            n1, n2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
            if n1 == 0 or n2 == 0:
                return 0.0
            return float(np.clip(np.dot(vec1 / n1, vec2 / n2), -1.0, 1.0))
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    def _apply_filters(
        self,
        metadata_list: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[int]:
        """Apply metadata filters and return indices of matching items."""
        matching_indices = []
        
        for i, metadata in enumerate(metadata_list):
            match = True
            for key, value in filters.items():
                if key not in metadata:
                    match = False
                    break
                elif isinstance(value, dict):
                    # Handle range filters
                    if "min" in value and metadata[key] < value["min"]:
                        match = False
                        break
                    if "max" in value and metadata[key] > value["max"]:
                        match = False
                        break
                elif isinstance(value, list):
                    # Handle list membership
                    if metadata[key] not in value:
                        match = False
                        break
                else:
                    # Handle exact match
                    if metadata[key] != value:
                        match = False
                        break
            
            if match:
                matching_indices.append(i)
        
        return matching_indices
    
    def _calculate_context_similarities(
        self,
        candidate_embeddings: List[Tuple[np.ndarray, np.ndarray]],
        context_graph: Any,
        max_hops: int
    ) -> List[float]:
        """Calculate context similarities based on graph relationships."""
        # This is a simplified implementation
        # In practice, this would analyze the graph structure
        # to find relationships between decisions
        
        context_similarities = []
        
        for i, (sem_emb, struct_emb) in enumerate(candidate_embeddings):
            # Simple context similarity based on embedding similarity
            # This could be enhanced with actual graph analysis
            if i > 0:
                prev_sem, prev_struct = candidate_embeddings[i-1]
                sem_context_sim = self._calculate_similarity(sem_emb, prev_sem, "cosine")
                struct_context_sim = self._calculate_similarity(struct_emb, prev_struct, "cosine")
                context_sim = (sem_context_sim + struct_context_sim) / 2
            else:
                context_sim = 0.5  # Default context similarity
            
            context_similarities.append(context_sim)
        
        return context_similarities
    
    def update_weights(self, semantic_weight: float, structural_weight: float) -> None:
        """Update similarity weights."""
        total_weight = semantic_weight + structural_weight
        if not np.isclose(total_weight, 1.0, atol=0.01):
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        
        self.logger.info(f"Updated weights: semantic={semantic_weight}, structural={structural_weight}")
    
    def get_similarity_breakdown(
        self,
        semantic_vec1: np.ndarray,
        structural_vec1: np.ndarray,
        semantic_vec2: np.ndarray,
        structural_vec2: np.ndarray
    ) -> Dict[str, float]:
        """Get detailed breakdown of similarity components."""
        semantic_sim = self._calculate_similarity(
            semantic_vec1, semantic_vec2, self.semantic_metric
        )
        structural_sim = self._calculate_similarity(
            structural_vec1, structural_vec2, self.structural_metric
        )
        hybrid_sim = self.calculate_hybrid_similarity(
            semantic_vec1, structural_vec1, semantic_vec2, structural_vec2
        )
        
        return {
            "semantic_similarity": semantic_sim,
            "structural_similarity": structural_sim,
            "hybrid_similarity": hybrid_sim,
            "semantic_weight": self.semantic_weight,
            "structural_weight": self.structural_weight
        }
