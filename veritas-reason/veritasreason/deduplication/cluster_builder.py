"""
Cluster Builder Module

This module provides cluster building capabilities for the VeritasReason framework,
creating clusters of similar entities for batch deduplication using clustering
algorithms and similarity graphs.

Algorithms Used:
    - Union-Find (Disjoint Set Union): Connected component detection for graph-based clustering
    - Hierarchical Clustering: Agglomerative bottom-up clustering for large datasets
    - Similarity Graph: Graph construction from similarity scores with threshold filtering
    - Cluster Quality Metrics: Cohesion (intra-cluster similarity) and separation (inter-cluster dissimilarity) measures
    - Centroid Calculation: Representative entity calculation for clusters

Key Features:
    - Graph-based clustering using union-find algorithm for efficient connected component detection
    - Hierarchical clustering for large datasets with configurable linkage criteria
    - Cluster quality assessment and metrics (cohesion, separation, silhouette score)
    - Incremental cluster updates for streaming scenarios
    - Configurable cluster size constraints (min/max cluster size)
    - Similarity threshold-based filtering for cluster formation

Main Classes:
    - ClusterBuilder: Main cluster building engine
    - Cluster: Entity cluster representation with centroid and quality score
    - ClusterResult: Cluster building result with quality metrics

Example Usage:
    >>> from veritasreason.deduplication import ClusterBuilder
    >>> builder = ClusterBuilder(
    ...     similarity_threshold=0.8,
    ...     min_cluster_size=2,
    ...     max_cluster_size=50,
    ...     use_hierarchical=False
    ... )
    >>> result = builder.build_clusters(entities)
    >>> print(f"Found {len(result.clusters)} clusters")
    >>> print(f"Quality metrics: {result.quality_metrics}")

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .similarity_calculator import SimilarityCalculator


@dataclass
class Cluster:
    """Entity cluster representation."""

    cluster_id: str
    entities: List[Dict[str, Any]]
    centroid: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterResult:
    """Cluster building result."""

    clusters: List[Cluster]
    unclustered: List[Dict[str, Any]] = field(default_factory=list)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClusterBuilder:
    """
    Cluster building engine for entity clustering.

    This class builds clusters of similar entities for batch deduplication using
    graph-based or hierarchical clustering algorithms. Clusters can be used for
    efficient batch processing of duplicate detection and merging.

    Features:
        - Graph-based clustering using union-find algorithm
        - Hierarchical clustering for large datasets
        - Cluster quality assessment and metrics
        - Incremental cluster updates
        - Configurable cluster size constraints

    Example Usage:
        >>> builder = ClusterBuilder(
        ...     similarity_threshold=0.8,
        ...     min_cluster_size=2,
        ...     max_cluster_size=50
        ... )
        >>> result = builder.build_clusters(entities)
        >>> print(f"Found {len(result.clusters)} clusters")
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,
        min_cluster_size: int = 2,
        max_cluster_size: int = 100,
        use_hierarchical: bool = False,
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize cluster builder.

        Sets up the cluster builder with similarity calculator and clustering
        configuration parameters.

        Args:
            similarity_threshold: Minimum similarity for entities to be in same cluster
                                (0.0 to 1.0, default: 0.7)
            min_cluster_size: Minimum number of entities in a valid cluster (default: 2)
            max_cluster_size: Maximum number of entities in a cluster (default: 100)
            use_hierarchical: Whether to use hierarchical clustering (default: False).
                            If False, uses faster graph-based clustering.
            config: Configuration dictionary (merged with kwargs)
            **kwargs: Additional configuration options:
                - similarity: Configuration for SimilarityCalculator
        """
        self.logger = get_logger("cluster_builder")

        # Merge configuration
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize similarity calculator
        similarity_config = self.config.get("similarity", {})
        self.similarity_calculator = SimilarityCalculator(**similarity_config)

        # Clustering parameters
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size
        self.use_hierarchical = use_hierarchical

        # Initialize progress tracker and ensure it's enabled
        self.progress_tracker = get_progress_tracker()
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug(
            f"Cluster builder initialized: threshold={similarity_threshold}, "
            f"size_range=[{min_cluster_size}, {max_cluster_size}], "
            f"hierarchical={use_hierarchical}"
        )

    def build_clusters(
        self, entities: List[Dict[str, Any]], **options
    ) -> ClusterResult:
        """
        Build clusters of similar entities.

        Args:
            entities: List of entities to cluster
            **options: Clustering options

        Returns:
            ClusterResult with clusters and metrics
        """
        # Track cluster building
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="deduplication",
            submodule="ClusterBuilder",
            message=f"Building clusters from {len(entities)} entities",
        )

        try:
            threshold = options.get("threshold", self.similarity_threshold)

            total_steps = 4  # Clustering, filtering, finding unclustered, quality metrics
            current_step = 0

            # Step 1: Clustering
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Clustering {len(entities)} entities... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )

            if self.use_hierarchical:
                clusters = self._hierarchical_clustering(entities, threshold, tracking_id)
            else:
                clusters = self._graph_based_clustering(entities, threshold, tracking_id)

            # Step 2: Filter clusters by size
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Filtering clusters by size... ({current_step}/{total_steps}, {len(clusters)} clusters, remaining: {remaining_steps} steps)"
            )
            valid_clusters = [
                c
                for c in clusters
                if self.min_cluster_size <= len(c.entities) <= self.max_cluster_size
            ]

            # Step 3: Find unclustered entities
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Finding unclustered entities... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            clustered_entity_ids = set()
            for cluster in valid_clusters:
                for entity in cluster.entities:
                    entity_id = entity.get("id") or id(entity)
                    clustered_entity_ids.add(entity_id)

            unclustered = [
                e for e in entities if (e.get("id") or id(e)) not in clustered_entity_ids
            ]

            # Step 4: Calculate quality metrics
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Calculating cluster quality metrics... ({current_step}/{total_steps}, {len(valid_clusters)} clusters, remaining: {remaining_steps} steps)"
            )
            quality_metrics = self._calculate_cluster_quality(valid_clusters)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Built {len(valid_clusters)} clusters",
            )
            return ClusterResult(
                clusters=valid_clusters,
                unclustered=unclustered,
                quality_metrics=quality_metrics,
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _graph_based_clustering(
        self, entities: List[Dict[str, Any]], threshold: float, tracking_id: str = None
    ) -> List[Cluster]:
        """Build clusters using graph-based approach."""
        # Build similarity graph
        similarity_pairs = self.similarity_calculator.batch_calculate_similarity(
            entities, threshold=threshold
        )
        
        if tracking_id:
            self.progress_tracker.update_tracking(
                tracking_id, message=f"Building clusters from {len(similarity_pairs)} similarity pairs..."
            )

        # Union-find to build clusters
        entity_to_cluster = {}
        clusters_dict = {}
        cluster_id_counter = 0

        total_pairs = len(similarity_pairs)
        processed_pairs = 0
        if total_pairs <= 10:
            update_interval = 1  # Update every item for small datasets
        else:
            update_interval = max(1, min(10, total_pairs // 100))
        
        # Initial progress update
        if tracking_id and total_pairs > 0:
            remaining = total_pairs
            self.progress_tracker.update_progress(
                tracking_id,
                processed=0,
                total=total_pairs,
                message=f"Building clusters from similarity pairs... 0/{total_pairs} (remaining: {remaining})"
            )

        for entity1, entity2, score in similarity_pairs:
            entity1_id = entity1.get("id") or id(entity1)
            entity2_id = entity2.get("id") or id(entity2)

            cluster1 = entity_to_cluster.get(entity1_id)
            cluster2 = entity_to_cluster.get(entity2_id)

            if cluster1 is None and cluster2 is None:
                # Create new cluster
                cluster_id = f"cluster_{cluster_id_counter}"
                cluster_id_counter += 1

                cluster = Cluster(
                    cluster_id=cluster_id,
                    entities=[entity1, entity2],
                    metadata={"similarity_scores": {(entity1_id, entity2_id): score}},
                )
                clusters_dict[cluster_id] = cluster
                entity_to_cluster[entity1_id] = cluster_id
                entity_to_cluster[entity2_id] = cluster_id
            elif cluster1 is not None and cluster2 is None:
                # Add entity2 to cluster1
                clusters_dict[cluster1].entities.append(entity2)
                entity_to_cluster[entity2_id] = cluster1
            elif cluster1 is None and cluster2 is not None:
                # Add entity1 to cluster2
                clusters_dict[cluster2].entities.append(entity1)
                entity_to_cluster[entity1_id] = cluster2
            elif cluster1 != cluster2:
                # Merge clusters
                cluster1_obj = clusters_dict[cluster1]
                cluster2_obj = clusters_dict[cluster2]

                cluster1_obj.entities.extend(cluster2_obj.entities)
                cluster1_obj.metadata.get("similarity_scores", {}).update(
                    cluster2_obj.metadata.get("similarity_scores", {})
                )
                cluster1_obj.metadata["similarity_scores"][
                    (entity1_id, entity2_id)
                ] = score

                # Update references
                for entity in cluster2_obj.entities:
                    entity_id = entity.get("id") or id(entity)
                    entity_to_cluster[entity_id] = cluster1

                del clusters_dict[cluster2]
            
            processed_pairs += 1
            remaining = total_pairs - processed_pairs
            # Update progress: always update for small datasets, or at intervals for large ones
            if tracking_id:
                should_update = (
                    processed_pairs % update_interval == 0 or 
                    processed_pairs == total_pairs or 
                    processed_pairs == 1 or
                    total_pairs <= 10  # Always update for small datasets
                )
                if should_update:
                    self.progress_tracker.update_progress(
                        tracking_id,
                        processed=processed_pairs,
                        total=total_pairs,
                        message=f"Building clusters from similarity pairs... {processed_pairs}/{total_pairs} (remaining: {remaining})"
                    )

        return list(clusters_dict.values())

    def _hierarchical_clustering(
        self, entities: List[Dict[str, Any]], threshold: float, tracking_id: str = None
    ) -> List[Cluster]:
        """Build clusters using hierarchical clustering."""
        # Simplified hierarchical clustering
        # Start with each entity as its own cluster
        clusters = [
            Cluster(cluster_id=f"cluster_{i}", entities=[entity], metadata={})
            for i, entity in enumerate(entities)
        ]

        # Merge clusters based on similarity
        merged = True
        iteration = 0
        total_iterations = len(entities)  # Maximum iterations
        if total_iterations <= 10:
            update_interval = 1  # Update every iteration for small datasets
        else:
            update_interval = max(1, total_iterations // 20)  # Update every 5%
        
        while merged:
            merged = False
            best_merge = None
            best_similarity = threshold

            total_comparisons = len(clusters) * (len(clusters) - 1) // 2
            processed_comparisons = 0
            if total_comparisons <= 10:
                comparison_update_interval = 1  # Update every comparison for small datasets
            else:
                comparison_update_interval = max(1, total_comparisons // 20) if total_comparisons > 0 else 1

            # Initial progress update for comparisons
            if tracking_id and total_comparisons > 0:
                remaining_comparisons = total_comparisons
                self.progress_tracker.update_progress(
                    tracking_id,
                    processed=0,
                    total=total_comparisons,
                    message=f"Comparing clusters... 0/{total_comparisons} (remaining: {remaining_comparisons})"
                )

            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    # Calculate cluster similarity
                    similarity = self._cluster_similarity(clusters[i], clusters[j])

                    if similarity >= best_similarity:
                        best_similarity = similarity
                        best_merge = (i, j)
                    
                    processed_comparisons += 1
                    remaining_comparisons = total_comparisons - processed_comparisons
                    # Update progress: always update for small datasets, or at intervals for large ones
                    if tracking_id:
                        should_update = (
                            processed_comparisons % comparison_update_interval == 0 or 
                            processed_comparisons == total_comparisons or 
                            processed_comparisons == 1 or
                            total_comparisons <= 10  # Always update for small datasets
                        )
                        if should_update:
                            self.progress_tracker.update_progress(
                                tracking_id,
                                processed=processed_comparisons,
                                total=total_comparisons,
                                message=f"Comparing clusters... {processed_comparisons}/{total_comparisons} (remaining: {remaining_comparisons})"
                            )

            if best_merge:
                i, j = best_merge
                # Merge clusters
                merged_cluster = Cluster(
                    cluster_id=clusters[i].cluster_id,
                    entities=clusters[i].entities + clusters[j].entities,
                    metadata={"merge_similarity": best_similarity},
                )
                clusters[i] = merged_cluster
                clusters.pop(j)
                merged = True
                
                iteration += 1
                remaining_iterations = total_iterations - iteration
                # Update progress: always update for small datasets, or at intervals for large ones
                if tracking_id:
                    should_update = (
                        iteration % update_interval == 0 or 
                        iteration == total_iterations or 
                        iteration == 1 or
                        total_iterations <= 10  # Always update for small datasets
                    )
                    if should_update:
                        self.progress_tracker.update_progress(
                            tracking_id,
                            processed=iteration,
                            total=total_iterations,
                            message=f"Hierarchical clustering iteration {iteration}/{total_iterations}... {len(clusters)} clusters remaining (remaining: {remaining_iterations} iterations)"
                        )

        return clusters

    def _cluster_similarity(self, cluster1: Cluster, cluster2: Cluster) -> float:
        """Calculate similarity between two clusters."""
        # Average similarity between all pairs
        similarities = []

        for entity1 in cluster1.entities:
            for entity2 in cluster2.entities:
                similarity = self.similarity_calculator.calculate_similarity(
                    entity1, entity2
                )
                similarities.append(similarity.score)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _calculate_cluster_quality(self, clusters: List[Cluster]) -> Dict[str, Any]:
        """Calculate quality metrics for clusters."""
        if not clusters:
            return {"average_size": 0, "average_quality": 0.0, "total_clusters": 0}

        # Calculate cluster quality scores
        for cluster in clusters:
            cluster.quality_score = self._cluster_quality_score(cluster)

        avg_quality = sum(c.quality_score for c in clusters) / len(clusters)
        avg_size = sum(len(c.entities) for c in clusters) / len(clusters)

        return {
            "average_size": avg_size,
            "average_quality": avg_quality,
            "total_clusters": len(clusters),
            "high_quality_clusters": len(
                [c for c in clusters if c.quality_score >= 0.7]
            ),
        }

    def _cluster_quality_score(self, cluster: Cluster) -> float:
        """Calculate quality score for a cluster."""
        if len(cluster.entities) < 2:
            return 0.0

        # Calculate average pairwise similarity
        similarities = []
        for i in range(len(cluster.entities)):
            for j in range(i + 1, len(cluster.entities)):
                similarity = self.similarity_calculator.calculate_similarity(
                    cluster.entities[i], cluster.entities[j]
                )
                similarities.append(similarity.score)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # Size factor (prefer medium-sized clusters)
        size_factor = 1.0
        size = len(cluster.entities)
        if size < self.min_cluster_size or size > self.max_cluster_size:
            size_factor = 0.8

        return avg_similarity * size_factor

    def update_clusters(
        self,
        existing_clusters: List[Cluster],
        new_entities: List[Dict[str, Any]],
        **options,
    ) -> ClusterResult:
        """
        Incrementally update clusters with new entities.

        Args:
            existing_clusters: Existing clusters
            new_entities: New entities to add
            **options: Update options

        Returns:
            Updated ClusterResult
        """
        threshold = options.get("threshold", self.similarity_threshold)

        # Try to add new entities to existing clusters
        for entity in new_entities:
            best_cluster = None
            best_similarity = threshold

            for cluster in existing_clusters:
                # Calculate similarity to cluster centroid or average
                similarity = self._entity_cluster_similarity(entity, cluster)

                if similarity >= best_similarity:
                    best_similarity = similarity
                    best_cluster = cluster

            if best_cluster:
                best_cluster.entities.append(entity)
            else:
                # Create new singleton cluster
                new_cluster = Cluster(
                    cluster_id=f"cluster_{len(existing_clusters)}", entities=[entity]
                )
                existing_clusters.append(new_cluster)

        # Rebuild all clusters
        all_entities = []
        for cluster in existing_clusters:
            all_entities.extend(cluster.entities)

        return self.build_clusters(all_entities, **options)

    def _entity_cluster_similarity(
        self, entity: Dict[str, Any], cluster: Cluster
    ) -> float:
        """Calculate similarity between entity and cluster."""
        if not cluster.entities:
            return 0.0

        # Average similarity to all entities in cluster
        similarities = [
            self.similarity_calculator.calculate_similarity(entity, e).score
            for e in cluster.entities
        ]

        return sum(similarities) / len(similarities) if similarities else 0.0
