# Deduplication Module Usage Guide

This guide demonstrates how to use the deduplication module for detecting and merging duplicate entities in knowledge graphs.

## Table of Contents

1. [Similarity Calculation](#similarity-calculation)
2. [Duplicate Detection](#duplicate-detection)
3. [Entity Merging](#entity-merging)
4. [Clustering](#clustering)
5. [Using Methods](#using-methods)
6. [Using Registry](#using-registry)
7. [Configuration](#configuration)
8. [Advanced Examples](#advanced-examples)

## Similarity Calculation

### Basic Similarity Calculation

```python
from veritasreason.deduplication import SimilarityCalculator

# Initialize with default weights (optimized for entity resolution)
# String: 0.6 (Jaro-Winkler), Property: 0.2, Relationship: 0.2
calculator = SimilarityCalculator()

# Or customize weights
calculator_custom = SimilarityCalculator(
    string_weight=0.6,
    property_weight=0.2,
    embedding_weight=0.2
)

entity1 = {"name": "Apple Inc.", "type": "Company"}
entity2 = {"name": "Apple", "type": "Company"}

# Calculate multi-factor similarity
result = calculator.calculate_similarity(entity1, entity2)
print(f"Similarity score: {result.score:.2f}")
print(f"Components: {result.components}")
```

### Different Similarity Methods

```python
from veritasreason.deduplication.methods import calculate_similarity

entity1 = {"name": "Apple Inc.", "type": "Company"}
entity2 = {"name": "Apple", "type": "Company"}

# Exact matching
exact_result = calculate_similarity(entity1, entity2, method="exact")
print(f"Exact match: {exact_result.score}")

# Levenshtein distance
lev_result = calculate_similarity(entity1, entity2, method="levenshtein")
print(f"Levenshtein similarity: {lev_result.score:.2f}")

# Jaro-Winkler similarity
jaro_result = calculate_similarity(entity1, entity2, method="jaro_winkler")
print(f"Jaro-Winkler similarity: {jaro_result.score:.2f}")

# Property similarity
prop_result = calculate_similarity(entity1, entity2, method="property")
print(f"Property similarity: {prop_result.score:.2f}")

# Relationship similarity
rel_result = calculate_similarity(entity1, entity2, method="relationship")
print(f"Relationship similarity: {rel_result.score:.2f}")

# Multi-factor (default)
multi_result = calculate_similarity(entity1, entity2, method="multi_factor")
print(f"Multi-factor similarity: {multi_result.score:.2f}")
```

### String Similarity Methods

```python
from veritasreason.deduplication import SimilarityCalculator

calculator = SimilarityCalculator()

# Levenshtein distance
lev_score = calculator.calculate_string_similarity(
    "Apple Inc.",
    "Apple",
    method="levenshtein"
)
print(f"Levenshtein: {lev_score:.2f}")

# Jaro-Winkler
jaro_score = calculator.calculate_string_similarity(
    "Apple Inc.",
    "Apple",
    method="jaro_winkler"
)
print(f"Jaro-Winkler: {jaro_score:.2f}")

# Cosine similarity
cosine_score = calculator.calculate_string_similarity(
    "Apple Inc.",
    "Apple",
    method="cosine"
)
print(f"Cosine: {cosine_score:.2f}")
```

## Duplicate Detection

### Pairwise Detection

```python
from veritasreason.deduplication.methods import detect_duplicates

entities = [
    {"id": "1", "name": "Apple Inc."},
    {"id": "2", "name": "Apple"},
    {"id": "3", "name": "Microsoft"},
]

# Pairwise detection (O(n²) comparison)
candidates = detect_duplicates(
    entities,
    method="pairwise",
    similarity_threshold=0.8,
    confidence_threshold=0.7
)

for candidate in candidates:
    print(f"Duplicate: {candidate.entity1['name']} <-> {candidate.entity2['name']}")
    print(f"  Similarity: {candidate.similarity_score:.2f}")
    print(f"  Confidence: {candidate.confidence:.2f}")
```

### Group Detection

```python
from veritasreason.deduplication.methods import detect_duplicates

# Group detection (Union-Find algorithm)
groups = detect_duplicates(
    entities,
    method="group",
    similarity_threshold=0.8
)

for group in groups:
    print(f"Group with {len(group.entities)} entities:")
    print(f"  Confidence: {group.confidence:.2f}")
    print(f"  Representative: {group.representative['name'] if group.representative else 'None'}")
    for entity in group.entities:
        print(f"    - {entity['name']}")
```

### Incremental Detection

```python
from veritasreason.deduplication.methods import detect_duplicates

existing_entities = [
    {"id": "1", "name": "Apple Inc."},
    {"id": "2", "name": "Microsoft"},
]

new_entities = [
    {"id": "3", "name": "Apple"},
    {"id": "4", "name": "Google"},
]

# Incremental detection (O(n×m) comparison)
candidates = detect_duplicates(
    new_entities,
    method="incremental",
    existing_entities=existing_entities,
    similarity_threshold=0.8
)

for candidate in candidates:
    print(f"New entity '{candidate.entity1['name']}' duplicates existing '{candidate.entity2['name']}'")
```

### Using DuplicateDetector Directly

```python
from veritasreason.deduplication import DuplicateDetector

detector = DuplicateDetector(
    similarity_threshold=0.8,
    confidence_threshold=0.7,
    use_clustering=True
)

# Detect duplicate candidates
candidates = detector.detect_duplicates(entities)
print(f"Found {len(candidates)} duplicate candidates")

# Detect duplicate groups
groups = detector.detect_duplicate_groups(entities)
print(f"Found {len(groups)} duplicate groups")

# Incremental detection
new_candidates = detector.incremental_detect(
    new_entities,
    existing_entities
)
print(f"Found {len(new_candidates)} incremental duplicates")
```

## Entity Merging

### Basic Merging

```python
from veritasreason.deduplication.methods import merge_entities

duplicate_entities = [
    {"id": "1", "name": "Apple Inc.", "type": "Company", "founded": 1976},
    {"id": "2", "name": "Apple", "type": "Company", "founded": 1976},
]

# Merge with different strategies
operations = merge_entities(
    duplicate_entities,
    method="keep_most_complete",
    preserve_provenance=True
)

for op in operations:
    print(f"Merged entity: {op.merged_entity['name']}")
    print(f"  Source entities: {len(op.source_entities)}")
    print(f"  Conflicts: {len(op.merge_result.conflicts)}")
```

### Different Merge Strategies

```python
from veritasreason.deduplication.methods import merge_entities

# Keep first entity
result1 = merge_entities(entities, method="keep_first")

# Keep last entity
result2 = merge_entities(entities, method="keep_last")

# Keep most complete entity
result3 = merge_entities(entities, method="keep_most_complete")

# Keep highest confidence entity
result4 = merge_entities(entities, method="keep_highest_confidence")

# Merge all properties
result5 = merge_entities(entities, method="merge_all")
```

### Using EntityMerger Directly

```python
from veritasreason.deduplication import EntityMerger, MergeStrategy

merger = EntityMerger(preserve_provenance=True)

# Merge with specific strategy
operations = merger.merge_duplicates(
    entities,
    strategy=MergeStrategy.KEEP_MOST_COMPLETE
)

# Get merge history
history = merger.get_merge_history()
print(f"Total merge operations: {len(history)}")

# Access merged entities
for op in operations:
    merged = op.merged_entity
    print(f"Merged: {merged['name']}")
    if merger.preserve_provenance:
        print(f"  Sources: {merged.get('_merged_from', [])}")
```

### Custom Merge Strategy

```python
from veritasreason.deduplication import MergeStrategyManager, MergeStrategy

manager = MergeStrategyManager(default_strategy="keep_most_complete")

# Add property-specific rules
manager.add_property_rule("name", MergeStrategy.KEEP_FIRST)
manager.add_property_rule("description", MergeStrategy.MERGE_ALL)

# Custom conflict resolution
def resolve_conflict(values):
    # Return longest value
    return max(values, key=len)

manager.add_property_rule(
    "description",
    MergeStrategy.CUSTOM,
    conflict_resolution=resolve_conflict
)

# Merge entities
result = manager.merge_entities(entities)
print(f"Merged entity: {result.merged_entity}")
print(f"Conflicts: {result.conflicts}")
```

## Clustering

### Graph-based Clustering

```python
from veritasreason.deduplication.methods import build_clusters

entities = [{"id": str(i), "name": f"Entity {i}"} for i in range(100)]

# Graph-based clustering (Union-Find)
result = build_clusters(
    entities,
    method="graph_based",
    similarity_threshold=0.8,
    min_cluster_size=2,
    max_cluster_size=50
)

print(f"Found {len(result.clusters)} clusters")
print(f"Unclustered entities: {len(result.unclustered)}")
print(f"Quality metrics: {result.quality_metrics}")

for cluster in result.clusters:
    print(f"Cluster {cluster.cluster_id}: {len(cluster.entities)} entities")
    print(f"  Quality score: {cluster.quality_score:.2f}")
```

### Hierarchical Clustering

```python
from veritasreason.deduplication.methods import build_clusters

# Hierarchical clustering for large datasets
result = build_clusters(
    entities,
    method="hierarchical",
    similarity_threshold=0.8
)

print(f"Found {len(result.clusters)} clusters using hierarchical method")
```

### Using ClusterBuilder Directly

```python
from veritasreason.deduplication import ClusterBuilder

builder = ClusterBuilder(
    similarity_threshold=0.8,
    min_cluster_size=2,
    max_cluster_size=50,
    use_hierarchical=False
)

result = builder.build_clusters(entities)

for cluster in result.clusters:
    print(f"Cluster: {len(cluster.entities)} entities")
    if cluster.centroid:
        print(f"  Centroid: {cluster.centroid['name']}")
    print(f"  Quality: {cluster.quality_score:.2f}")
```

## Using Methods

### Getting Available Methods

```python
from veritasreason.deduplication.methods import list_available_methods, get_deduplication_method

# List all available methods
all_methods = list_available_methods()
print("Available methods:")
for task, methods in all_methods.items():
    print(f"  {task}: {methods}")

# List methods for specific task
similarity_methods = list_available_methods("similarity")
print(f"Similarity methods: {similarity_methods}")

# Get specific method
levenshtein_method = get_deduplication_method("similarity", "levenshtein")
if levenshtein_method:
    result = levenshtein_method(entity1, entity2)
    print(f"Levenshtein similarity: {result.score:.2f}")
```

## Using Registry

### Registering Custom Methods

```python
from veritasreason.deduplication.registry import method_registry

# Custom similarity method
def custom_similarity(entity1, entity2, **kwargs):
    # Your custom similarity logic
    name1 = entity1.get("name", "").lower()
    name2 = entity2.get("name", "").lower()
    
    # Simple word overlap similarity
    words1 = set(name1.split())
    words2 = set(name2.split())
    
    if not words1 or not words2:
        return SimilarityResult(score=0.0, method="custom")
    
    overlap = len(words1 & words2) / len(words1 | words2)
    return SimilarityResult(score=overlap, method="custom")

# Register custom method
method_registry.register("similarity", "word_overlap", custom_similarity)

# Use custom method
from veritasreason.deduplication.methods import get_deduplication_method
custom_method = get_deduplication_method("similarity", "word_overlap")
result = custom_method(entity1, entity2)
print(f"Custom similarity: {result.score:.2f}")
```

### Listing Registered Methods

```python
from veritasreason.deduplication.registry import method_registry

# List all registered methods
all_methods = method_registry.list_all()
print("Registered methods:", all_methods)

# List methods for specific task
similarity_methods = method_registry.list_all("similarity")
print("Similarity methods:", similarity_methods)
```

## Configuration

### Using Configuration Manager

```python
from veritasreason.deduplication.config import dedup_config

# Get configuration values
threshold = dedup_config.get("similarity_threshold", default=0.7)
confidence = dedup_config.get("confidence_threshold", default=0.6)

# Set configuration values
dedup_config.set("similarity_threshold", 0.8)
dedup_config.set("confidence_threshold", 0.7)

# Method-specific configuration
dedup_config.set_method_config("levenshtein", case_sensitive=False)
levenshtein_config = dedup_config.get_method_config("levenshtein")

# Get all configuration
all_config = dedup_config.get_all()
print("All config:", all_config)
```

### Environment Variables

```bash
# Set environment variables
export DEDUP_SIMILARITY_THRESHOLD=0.8
export DEDUP_CONFIDENCE_THRESHOLD=0.7
export DEDUP_USE_CLUSTERING=true
export DEDUP_PRESERVE_PROVENANCE=true
```

### Configuration File

```yaml
# config.yaml
deduplication:
  similarity_threshold: 0.8
  confidence_threshold: 0.7
  use_clustering: true
  preserve_provenance: true

deduplication_methods:
  levenshtein:
    case_sensitive: false
  multi_factor:
    string_weight: 0.4
    property_weight: 0.3
    embedding_weight: 0.3
```

```python
from veritasreason.deduplication.config import DeduplicationConfig

# Load from config file
config = DeduplicationConfig(config_file="config.yaml")
threshold = config.get("similarity_threshold")
```

## Advanced Examples

### Complete Deduplication Pipeline

```python
from veritasreason.deduplication import (
    DuplicateDetector,
    EntityMerger,
    MergeStrategy,
    ClusterBuilder
)

# Step 1: Build clusters for batch processing
builder = ClusterBuilder(similarity_threshold=0.8)
cluster_result = builder.build_clusters(entities)

# Step 2: Detect duplicates in each cluster
detector = DuplicateDetector(similarity_threshold=0.8)
all_groups = []

for cluster in cluster_result.clusters:
    groups = detector.detect_duplicate_groups(cluster.entities)
    all_groups.extend(groups)

# Step 3: Merge duplicates
merger = EntityMerger(preserve_provenance=True)
all_entities = [e for cluster in cluster_result.clusters for e in cluster.entities]
merge_operations = merger.merge_duplicates(
    all_entities,
    strategy=MergeStrategy.KEEP_MOST_COMPLETE
)

print(f"Processed {len(cluster_result.clusters)} clusters")
print(f"Found {len(all_groups)} duplicate groups")
print(f"Performed {len(merge_operations)} merge operations")
```

### Custom Similarity with Embeddings

```python
from veritasreason.deduplication import SimilarityCalculator

# Entities with embeddings
entity1 = {
    "name": "Apple Inc.",
    "type": "Company",
    "embedding": [0.1, 0.2, 0.3, ...]  # Vector embedding
}

entity2 = {
    "name": "Apple",
    "type": "Company",
    "embedding": [0.12, 0.21, 0.29, ...]  # Similar embedding
}

calculator = SimilarityCalculator(
    embedding_weight=0.5,
    string_weight=0.3,
    property_weight=0.2
)

result = calculator.calculate_similarity(entity1, entity2)
print(f"Similarity: {result.score:.2f}")
print(f"Embedding component: {result.components.get('embedding', 0):.2f}")
```

### Batch Similarity Calculation

```python
from veritasreason.deduplication import SimilarityCalculator

calculator = SimilarityCalculator()

# Calculate similarity for all pairs
similarity_pairs = calculator.batch_calculate_similarity(
    entities,
    threshold=0.7
)

print(f"Found {len(similarity_pairs)} similar pairs above threshold")

for entity1, entity2, score in similarity_pairs:
    print(f"{entity1['name']} <-> {entity2['name']}: {score:.2f}")
```

### Merge History Tracking

```python
from veritasreason.deduplication import EntityMerger

merger = EntityMerger(preserve_provenance=True)

# Perform multiple merges
operations1 = merger.merge_duplicates(entities1)
operations2 = merger.merge_duplicates(entities2)

# Get complete merge history
history = merger.get_merge_history()
print(f"Total merge operations: {len(history)}")

# Analyze merge patterns
for op in history:
    print(f"Merge: {len(op.source_entities)} -> 1")
    print(f"  Strategy: {op.merge_result.metadata.get('strategy')}")
    print(f"  Conflicts: {len(op.merge_result.conflicts)}")
```

### Property-Specific Merge Rules

```python
from veritasreason.deduplication import MergeStrategyManager

manager = MergeStrategyManager(default_strategy="keep_most_complete")

# Different strategies for different properties
manager.add_property_rule("name", "keep_first")
manager.add_property_rule("description", "merge_all")
manager.add_property_rule("founded", "keep_highest_confidence")

# Custom conflict resolution for dates
def resolve_date_conflict(dates):
    # Return most recent date
    return max(dates)

manager.add_property_rule(
    "last_updated",
    "custom",
    conflict_resolution=resolve_date_conflict
)

# Merge with property-specific rules
result = manager.merge_entities(entities)
print(f"Merged entity: {result.merged_entity}")
```

### Incremental Deduplication Workflow

```python
from veritasreason.deduplication import DuplicateDetector, EntityMerger

# Initial knowledge base
existing_entities = load_initial_entities()

detector = DuplicateDetector(similarity_threshold=0.8)
merger = EntityMerger(preserve_provenance=True)

# Process new entities incrementally
def process_new_entities(new_entities):
    # Detect duplicates with existing entities
    candidates = detector.incremental_detect(new_entities, existing_entities)
    
    if candidates:
        # Merge duplicates
        duplicate_entities = [
            candidate.entity1 for candidate in candidates
        ]
        operations = merger.merge_duplicates(duplicate_entities)
        
        # Update existing entities
        for op in operations:
            # Remove old entities, add merged entity
            existing_entities = [
                e for e in existing_entities
                if e not in op.source_entities
            ]
            existing_entities.append(op.merged_entity)
    
    # Add non-duplicate new entities
    duplicate_ids = {c.entity1.get("id") for c in candidates}
    new_non_duplicates = [
        e for e in new_entities
        if e.get("id") not in duplicate_ids
    ]
    existing_entities.extend(new_non_duplicates)
    
    return existing_entities

# Process streaming data
for batch in stream_new_entities():
    existing_entities = process_new_entities(batch)
```

## Best Practices

1. **Choose appropriate similarity threshold**: Higher threshold (0.8-0.9) for precision, lower (0.6-0.7) for recall
2. **Use clustering for large datasets**: Cluster first, then deduplicate within clusters
3. **Preserve provenance**: Enable provenance tracking for audit trails
4. **Use incremental detection**: For streaming data, use incremental detection instead of full pairwise
5. **Customize merge strategies**: Use property-specific rules for better merge quality
6. **Validate merge results**: Check merge history and conflicts for quality assurance
7. **Tune weights**: Adjust similarity component weights based on your data characteristics

