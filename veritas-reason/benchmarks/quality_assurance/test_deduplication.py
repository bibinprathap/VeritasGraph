import random
import string
import time
from typing import Any, Dict, List
from unittest.mock import patch

import numpy as np
import pytest

from veritasreason.deduplication.cluster_builder import ClusterBuilder
from veritasreason.deduplication.duplicate_detector import DuplicateDetector
from veritasreason.deduplication.entity_merger import EntityMerger
from veritasreason.deduplication.similarity_calculator import SimilarityCalculator

# Infra


class NullTracker:
    """
    Discards all data to prevent memory leaks
    """

    def start_tracking(self, *args, **kwargs):
        return "dummy_id"

    def update_tracking(self, *args, **kwargs):
        pass

    def stop_tracking(self, *args, **kwargs):
        pass

    def register_pipeline_modules(self, *args, **kwargs):
        pass

    def clear_pipeline_context(self, *args, **kwargs):
        pass

    def update_progress(self, *args, **kwargs):
        pass

    @property
    def enabled(self):
        return False

    @enabled.setter
    def enabled(self, value):
        pass


@pytest.fixture(autouse=True)
def kill_io_overhead():
    """
    Replaces ProgressTracker with NullTracker globally.
    """
    with patch("veritasreason.utils.logging.get_logger"), patch(
        "veritasreason.utils.progress_tracker.get_progress_tracker"
    ) as mock_getter:

        mock_getter.return_value = NullTracker()

        with patch(
            "veritasreason.deduplication.similarity_calculator.get_progress_tracker",
            return_value=NullTracker(),
        ), patch(
            "veritasreason.deduplication.duplicate_detector.get_progress_tracker",
            return_value=NullTracker(),
        ), patch(
            "veritasreason.deduplication.cluster_builder.get_progress_tracker",
            return_value=NullTracker(),
        ):
            yield


# Sim data


def generate_entity_cluster(base_name: str, size: int) -> List[Dict[str, Any]]:
    """
    Generates a cluster of similar entities based on a seed name.
    Example: "Apple" -> ["Apple Inc", "Apple Corp", etc.]
    """

    entities = []
    suffixes = ["Inc", "Corp", "Ltd", "Gmbh", "LLC", "Group", "Systems"]

    for i in range(size):
        if random.random() < 0.8:
            name = f"{base_name} {random.choice(suffixes)}"
        else:
            # Generating a typo for our calc to work on
            chars = list(base_name)
            if len(chars) > 2:
                idx = random.randint(0, len(chars) - 2)
                chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
            name = "".join(chars)

        entities.append(
            {
                "id": f"{base_name.lower()}_{i}",
                "name": name,
                "type": "Organization",
                "properties": {
                    "location": "USA" if i % 2 == 0 else "California",
                    "sector": "Tech",
                    "employee_count": 100 + i,
                },
            }
        )

    return entities


def generate_relationship_dataset(size: int) -> List[Dict[str, Any]]:
    """
    Generates a dataset of graph relationships/triplets.
    Includes exact matches, synonym predicates, and dirty literal strings.
    """
    relationships = []
    predicates = ["works_for", "employed_by", "is_employee_of", "has_employer"]
    
    for i in range(size):
        # Base relationship
        rel = {
            "subject": f"Person_{i % 50}",
            "predicate": random.choice(predicates),
            "object": f"Company_{i % 10}"
        }
        relationships.append(rel)
        
        # Inject semantic duplicates (dirty literals / synonym predicates)
        if random.random() < 0.4:
            dirty_rel = {
                "subject": f"Person_{i % 50}",
                "predicate": random.choice(predicates),
                "object": f"  Company_{i % 10} Inc.  " 
            }
            relationships.append(dirty_rel)
            
    return relationships


def generate_dataset(
    num_clusters: int, items_per_cluster: int, worst_case_blocking: bool = False
):
    """
    Generates a full dataset

    Args:
      worst_case_blocking: If True, all names start with 'A' to defeat
                           first-char blocking strategy in SimilarityCalculator.

    """
    dataset = []
    for i in range(num_clusters):
        if worst_case_blocking:
            # All starts with 'A'
            base_name = f"A_Company_{i}"
        else:
            start_char = random.choice(string.ascii_uppercase)
            base_name = f"{start_char}_company_{i}"

        cluster = generate_entity_cluster(base_name, items_per_cluster)
        dataset.extend(cluster)

    return dataset


# ~~ Benchmarks ~~


@pytest.mark.parametrize("method", ["levenshtein", "jaro_winkler"])
def test_string_metric_speed(benchmark, method):
    """
    Measures the speed of string comparison algos.
    """

    calc = SimilarityCalculator()
    s1 = "International Business Machines Corporation"
    s2 = "International Business Machine Corp."

    benchmark.pedantic(
        lambda: calc.calculate_string_similarity(s1, s2, method=method),
        iterations=1000,
        rounds=100,
    )


def test_full_similarity_calculation(benchmark):
    """
    Measures weighted multi-factor calculation overhead.
    (String + Property + Relationship + Weights).
    """

    calc = SimilarityCalculator(
        string_weight=0.5, property_weight=0.3, relationship_weight=0.2
    )

    e1 = {
        "name": "Acme Corp",
        "properties": {"loc": "NY", "id": "123"},
        "relationships": [{"target": "t1"}, {"target": "t2"}],
    }

    e2 = {
        "name": "Acme Inc",
        "properties": {"loc": "NY", "id": "123"},
        "relationships": [{"target": "t1"}, {"target": "t2"}],
    }

    benchmark.pedantic(
        lambda: calc.calculate_similarity(e1, e2), iterations=1000, rounds=50
    )


@pytest.mark.parametrize("dataset_size", [100, 500])
def test_duplicate_detection_scaling_opt(benchmark, dataset_size):
    """
    Tests duplication on a 'Distributed' dataset (Best Case)
    Now utilizing V2 Candidate Generation to ensure no regressions.
    """
    data = generate_dataset(
        num_clusters=dataset_size // 10, items_per_cluster=10, worst_case_blocking=False
    )
    
    detector = DuplicateDetector(
        similarity_threshold=0.8,
        similarity={
            "candidate_strategy": "blocking_v2", 
            "max_candidates_per_entity": 50,
            "prefilter_enabled": True,
            "score_breakdown_enabled": True,
            "prefilter_thresholds": {
                "min_length_ratio": 0.4,
                "require_shared_token": True
            }
        }
    )

    benchmark.pedantic(lambda: detector.detect_duplicates(data), iterations=1, rounds=5)


@pytest.mark.parametrize("dataset_size", [100, 500])
def test_duplicate_detection_worst_Case(benchmark, dataset_size):
    """
    Tests detection on a 'Clustered' dataset (Worst Case).
    Now utilizing V2 Candidate Generation to cut the pair explosion.
    """
    data = generate_dataset(
        num_clusters=dataset_size // 10, items_per_cluster=10, worst_case_blocking=True
    )
    
    detector = DuplicateDetector(
        similarity_threshold=0.8,
        similarity={
            "candidate_strategy": "blocking_v2", 
            "max_candidates_per_entity": 50,
            "prefilter_enabled": True,
            "score_breakdown_enabled": True,
            "prefilter_thresholds": {
                "min_length_ratio": 0.4,
                "require_shared_token": True
            }
        }
    )

    benchmark.pedantic(lambda: detector.detect_duplicates(data), iterations=1, rounds=5)


def test_incremental_detection_speed(benchmark):
    """
    Measures performance of adding new data to existing index.
    """

    existing = generate_dataset(num_clusters=50, items_per_cluster=5)
    new_data = generate_dataset(num_clusters=5, items_per_cluster=2)

    detector = DuplicateDetector()

    benchmark.pedantic(
        lambda: detector.incremental_detect(new_data, existing), iterations=5, rounds=10
    )


@pytest.mark.parametrize("algo", ["graph", "hierarchical"])
def test_clustering_strategy_performance(benchmark, algo):
    """
    Comapres Union-Fund (Graph) vs Hierarchical Clustering.
    """

    data = generate_dataset(num_clusters=20, items_per_cluster=10)

    use_hierarchical = algo == "hierarchical"
    builder = ClusterBuilder(use_hierarchical=use_hierarchical)

    benchmark.pedantic(lambda: builder.build_clusters(data), iterations=1, rounds=5)


def test_merge_entity_benchmark(benchmark):
    """
    Measures the cost of fusing entities / res conflicts.
    """

    group = generate_entity_cluster("MegaCorp", 50)
    merger = EntityMerger()

    benchmark.pedantic(
        lambda: merger.merge_entity_group(group, strategy="keep_most_complete"),
        iterations=10,
        rounds=10,
    )
    

@pytest.mark.parametrize("mode", ["legacy", "semantic_v2"])
def test_relationship_dedup_speed(benchmark, mode):
    """
    Measures the speed of relationship/triplet deduplication.
    Compares the O(N^2) legacy fallback vs the fast canonical hash path.
    """
    # Yields ~280 relationships (approx 39,000 comparisons in O(N^2))
    relationships = generate_relationship_dataset(200) 
    
    detector = DuplicateDetector()
    options = {
        "threshold": 0.85,
        "relationship_dedup_mode": mode,
        "predicate_synonym_map": {
            "works_for": "employed_by",
            "is_employee_of": "employed_by",
            "has_employer": "employed_by"
        },
        "literal_normalization_enabled": True
    }

    benchmark.pedantic(
        lambda: detector.detect_relationship_duplicates(relationships, **options),
        iterations=5,
        rounds=10,
    )