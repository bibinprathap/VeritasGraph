"""
Advanced Deduplication Module

This module provides comprehensive semantic entity deduplication and merging
capabilities for the VeritasReason framework, helping keep knowledge graphs clean
and maintain a single source of truth. It supports multiple similarity calculation
methods, duplicate detection algorithms, entity merging strategies, and clustering
approaches for efficient batch processing.

Key Features:
    - Multiple similarity calculation methods (exact, Levenshtein, Jaro-Winkler, cosine, embedding)
    - Duplicate detection using similarity metrics and confidence scoring
    - Entity merging with configurable strategies (keep_first, keep_most_complete, etc.)
    - Cluster-based batch deduplication for large datasets
    - Provenance preservation during merges
    - Method registry for extensible deduplication methods
    - Reusable method functions for common deduplication tasks

Algorithms Used:

Similarity Calculation:
    - Levenshtein Distance: Dynamic programming algorithm for edit distance calculation
    - Jaro Similarity: Character-based similarity with match window algorithm
    - Jaro-Winkler Similarity: Jaro with prefix bonus (up to 4 characters)
    - Cosine Similarity: Vector dot product divided by magnitudes for embeddings
    - Jaccard Similarity: Intersection over union for relationship sets
    - Property Matching: Weighted comparison of property values
    - Multi-factor Aggregation: Weighted sum of similarity components

Duplicate Detection:
    - Pairwise Comparison: O(n²) all-pairs similarity calculation
    - Batch Processing: Vectorized similarity calculations for efficiency
    - Union-Find Algorithm: Disjoint set union for duplicate group formation
    - Confidence Scoring: Multi-factor confidence calculation (similarity + name match + property matches)
    - Incremental Processing: O(n×m) efficient new vs existing entity comparison

Clustering:
    - Union-Find (Disjoint Set Union): Connected component detection for graph-based clustering
    - Hierarchical Clustering: Agglomerative bottom-up clustering for large datasets
    - Similarity Graph: Graph construction from similarity scores
    - Cluster Quality Metrics: Cohesion and separation measures

Entity Merging:
    - Strategy Pattern: Multiple merge strategies (keep_first, keep_last, keep_most_complete, etc.)
    - Conflict Resolution: Voting, credibility-weighted, temporal, confidence-based resolution
    - Property Merging: Rule-based property combination with custom rules
    - Relationship Preservation: Union of relationship sets during merges
    - Provenance Tracking: Metadata preservation during merges

Main Components:
    - DuplicateDetector: Detects duplicate entities and relationships using similarity metrics
    - EntityMerger: Merges duplicate entities using configurable strategies
    - SimilarityCalculator: Calculates multi-factor similarity between entities
    - MergeStrategyManager: Manages merge strategies and conflict resolution
    - ClusterBuilder: Builds clusters for batch deduplication
    - MethodRegistry: Registry for custom deduplication methods
    - Deduplication Methods: Reusable functions for common deduplication tasks

Example Usage:
    >>> from veritasreason.deduplication import DuplicateDetector, EntityMerger
    >>> # Using main classes
    >>> detector = DuplicateDetector(similarity_threshold=0.8)
    >>> duplicates = detector.detect_duplicates(entities)
    >>> merger = EntityMerger()
    >>> merged = merger.merge_duplicates(entities)
    >>> 
    >>> # Using methods directly
    >>> from veritasreason.deduplication.methods import detect_duplicates, calculate_similarity
    >>> duplicates = detect_duplicates(entities, method="pairwise", similarity_threshold=0.8)
    >>> similarity = calculate_similarity(entity1, entity2, method="levenshtein")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Dict, List, Optional, Union

from .cluster_builder import Cluster, ClusterBuilder, ClusterResult
from .config import DeduplicationConfig, dedup_config
from .duplicate_detector import DuplicateCandidate, DuplicateDetector, DuplicateGroup
from .entity_merger import EntityMerger, MergeOperation
from .merge_strategy import (
    MergeResult,
    MergeStrategy,
    MergeStrategyManager,
    PropertyMergeRule,
)
from .methods import (
    build_clusters,
    calculate_similarity,
    detect_duplicates,
    get_deduplication_method,
    list_available_methods,
    merge_entities,
)
from .registry import MethodRegistry, method_registry
from .similarity_calculator import SimilarityCalculator, SimilarityResult

__all__ = [
    # Main classes
    "EntityMerger",
    "MergeOperation",
    "SimilarityCalculator",
    "SimilarityResult",
    "DuplicateDetector",
    "DuplicateCandidate",
    "DuplicateGroup",
    "MergeStrategyManager",
    "MergeStrategy",
    "MergeResult",
    "PropertyMergeRule",
    "ClusterBuilder",
    "Cluster",
    "ClusterResult",
    # Registry
    "MethodRegistry",
    "method_registry",
    # Methods
    "detect_duplicates",
    "merge_entities",
    "calculate_similarity",
    "build_clusters",
    "get_deduplication_method",
    "list_available_methods",
    # Config
    "DeduplicationConfig",
    "dedup_config",
]
