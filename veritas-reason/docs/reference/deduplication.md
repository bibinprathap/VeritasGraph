# Deduplication

> **Advanced entity deduplication and resolution system for maintaining a clean, single-source-of-truth Knowledge Graph.**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-content-duplicate:{ .lg .middle } **Duplicate Detection**

    ---

    Identify duplicates using multi-factor similarity metrics

-   :material-set-merge:{ .lg .middle } **Entity Merging**

    ---

    Merge entities with configurable strategies (Keep First, Most Complete, etc.)

-   :material-group:{ .lg .middle } **Clustering**

    ---

    Cluster similar entities for efficient batch processing

-   :material-calculator:{ .lg .middle } **Similarity Metrics**

    ---

    Levenshtein, Jaro-Winkler, Cosine, and Jaccard similarity support

-   :material-history:{ .lg .middle } **Provenance**

    ---

    Preserve data lineage and history during merges

-   :material-scale:{ .lg .middle } **Scalable**

    ---

    Batch processing and blocking for large datasets

</div>

!!! tip "When to Use"
    - **Data Ingestion**: Clean incoming data before adding to the graph
    - **Graph Maintenance**: Periodically clean up existing knowledge graphs
    - **Entity Resolution**: Resolve entities from different sources (e.g., "Apple" vs "Apple Inc.")

---

## ⚙️ Algorithms Used

### Similarity Calculation

The deduplication system uses multiple similarity metrics:

- **Levenshtein Distance**: Edit distance for string difference
- **Jaro-Winkler**: String similarity with prefix weighting (Default for strings, optimized for entity names)
- **Cosine Similarity**: Vector similarity for embeddings
- **Jaccard Similarity**: Set overlap for properties/relationships
- **Property Matching**: Handles disjoint properties with neutral scoring (`` `0.5` ``) to prevent false negatives
- **Multi-factor Aggregation**: Weighted sum of multiple metrics

### Default Configuration

The deduplication module uses the following default weights to prioritize name matching while considering other factors:

- **String Similarity**: `` `0.6` `` (Primary factor, using Jaro-Winkler)
- **Property Similarity**: `` `0.2` `` (Handles missing values neutrally)
- **Relationship Similarity**: `` `0.2` ``
- **Embedding Similarity**: `` `0.0` `` (Optional, enabled if embeddings are present)

### Duplicate Detection

The system uses efficient detection algorithms:

- **Pairwise Comparison**: `` `O(n²)` `` comparison (for small sets)
- **Blocking/Indexing**: Reduce search space for large sets
- **Union-Find**: Disjoint set data structure for grouping duplicates
- **Confidence Scoring**: `` `0.0 - 1.0` `` probability score for duplicates

### Clustering

The module provides clustering algorithms for grouping similar entities:
- **Hierarchical Clustering**: Agglomerative bottom-up clustering
- **Connected Components**: Graph-based cluster detection
- **Cluster Quality**: Cohesion and separation metrics

### Entity Merging
- **Strategy Pattern**: Pluggable merge logic
- **Property Union**: Combining unique properties
- **Relationship Merging**: Re-linking relationships to the merged entity

---

## Main Classes

### DuplicateDetector

Identifies potential duplicates in a dataset using similarity metrics and confidence scoring.

**Initialization:**

```python
DuplicateDetector(
    similarity_threshold: float = 0.7,
    confidence_threshold: float = 0.6,
    use_clustering: bool = True,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
)
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `detect_duplicates(entities, threshold=None, **options)` | Find duplicate pairs | `List[DuplicateCandidate]` |
| `detect_duplicate_groups(entities, threshold=None, **options)` | Find clusters of duplicates | `List[DuplicateGroup]` |
| `incremental_detect(new_entities, existing_entities, threshold=None, **options)` | Detect duplicates between new and existing entities | `List[DuplicateCandidate]` |
| `detect_relationship_duplicates(relationships, **options)` | Detect duplicate relationships | `List[Tuple[Dict, Dict]]` |

**Example:**

```python
from veritasreason.deduplication import DuplicateDetector

detector = DuplicateDetector(similarity_threshold=0.85, confidence_threshold=0.7)
candidates = detector.detect_duplicates(entities)
groups = detector.detect_duplicate_groups(entities)

for candidate in candidates:
    print(f"Duplicate: {candidate.entity1['name']} <-> {candidate.entity2['name']}")
    print(f"  Similarity: {candidate.similarity_score:.2f}, Confidence: {candidate.confidence:.2f}")
```

### EntityMerger

Merges duplicate entities into a single canonical entity using configurable strategies.

**Initialization:**

```python
EntityMerger(
    preserve_provenance: bool = True,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
)
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `merge_duplicates(entities, strategy=None, **options)` | Execute merge on duplicate entities | `List[MergeOperation]` |
| `merge_entity_group(entities, strategy=None, **options)` | Merge a specific group of entities | `MergeOperation` |
| `incremental_merge(new_entities, existing_entities, **options)` | Incrementally merge new entities with existing ones | `List[MergeOperation]` |
| `get_merge_history()` | Get merge operation history | `List[MergeOperation]` |
| `validate_merge_quality(merge_operation)` | Validate quality of a merge operation | `Dict[str, Any]` |

**Strategies:**
- `"keep_first"`: Keep the first entity encountered
- `"keep_last"`: Keep the last entity encountered
- `"keep_most_complete"`: Keep entity with most properties/relationships
- `"keep_highest_confidence"`: Keep entity with highest confidence score
- `"merge_all"`: Create new entity combining all info

**Example:**

```python
from veritasreason.deduplication import EntityMerger

merger = EntityMerger(preserve_provenance=True)

# Merge with specific strategy
operations = merger.merge_duplicates(
    entities,
    strategy="keep_most_complete"
)

# Get merge history
history = merger.get_merge_history()
```

### SimilarityCalculator

Calculates multi-factor similarity between entities using string, property, relationship, and embedding similarity.

**Initialization:**

```python
SimilarityCalculator(
    embedding_weight: float = 0.4,
    string_weight: float = 0.3,
    property_weight: float = 0.2,
    relationship_weight: float = 0.1,
    similarity_threshold: float = 0.7,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
)
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `calculate_similarity(entity1, entity2, **options)` | Calculate overall similarity | `SimilarityResult` |
| `calculate_string_similarity(str1, str2, method="levenshtein")` | Calculate string similarity | `float` |
| `calculate_property_similarity(entity1, entity2)` | Calculate property similarity | `float` |
| `calculate_relationship_similarity(entity1, entity2)` | Calculate relationship similarity | `float` |
| `calculate_embedding_similarity(embedding1, embedding2)` | Calculate embedding similarity | `float` |
| `batch_calculate_similarity(entities, threshold=None)` | Calculate similarity for all pairs | `List[Tuple[Dict, Dict, float]]` |

**Example:**

```python
from veritasreason.deduplication import SimilarityCalculator

calculator = SimilarityCalculator(
    string_weight=0.4,
    property_weight=0.3,
    embedding_weight=0.3
)

result = calculator.calculate_similarity(entity1, entity2)
print(f"Similarity: {result.score:.2f}")
print(f"Components: {result.components}")
```

### ClusterBuilder

Builds clusters of similar entities for efficient batch deduplication.

**Initialization:**

```python
ClusterBuilder(
    similarity_threshold: float = 0.7,
    min_cluster_size: int = 2,
    max_cluster_size: int = 100,
    use_hierarchical: bool = False,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
)
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `build_clusters(entities, **options)` | Build clusters of similar entities | `ClusterResult` |
| `update_clusters(existing_clusters, new_entities, **options)` | Incrementally update clusters with new entities | `ClusterResult` |

**Example:**

```python
from veritasreason.deduplication import ClusterBuilder

builder = ClusterBuilder(
    similarity_threshold=0.8,
    min_cluster_size=2,
    max_cluster_size=50
)

result = builder.build_clusters(entities)
print(f"Found {len(result.clusters)} clusters")
print(f"Unclustered: {len(result.unclustered)} entities")
print(f"Quality metrics: {result.quality_metrics}")
```

### MergeStrategyManager

Manages merge strategies and property-specific merge rules with conflict resolution.

**Initialization:**

```python
MergeStrategyManager(
    default_strategy: str = "keep_most_complete",
    config: Optional[Dict[str, Any]] = None,
    **kwargs
)
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `merge_entities(entities, strategy=None, **options)` | Merge entities using specified strategy | `MergeResult` |
| `add_property_rule(property_name, strategy, conflict_resolution=None, priority=0)` | Add property-specific merge rule | `None` |
| `validate_merge(merge_result)` | Validate merge result quality | `Dict[str, Any]` |

**Example:**

```python
from veritasreason.deduplication import MergeStrategyManager, MergeStrategy

manager = MergeStrategyManager(default_strategy="keep_most_complete")
manager.add_property_rule("name", MergeStrategy.KEEP_FIRST)
manager.add_property_rule("description", MergeStrategy.MERGE_ALL)

result = manager.merge_entities(entities)
print(f"Merged entity: {result.merged_entity}")
print(f"Conflicts: {len(result.conflicts)}")
```

### MethodRegistry

Registry for custom deduplication methods, enabling extensibility.

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `register(task, name, method_func)` | Register a custom deduplication method | `None` |
| `get(task, name)` | Get method by task and name | `Optional[Callable]` |
| `list_all(task=None)` | List all registered methods | `Dict[str, List[str]]` |
| `unregister(task, name)` | Unregister a method | `None` |
| `clear(task=None)` | Clear all registered methods | `None` |

**Example:**

```python
from veritasreason.deduplication.registry import method_registry

# Register custom similarity method
def custom_similarity(entity1, entity2, **kwargs):
    # Custom logic
    return SimilarityResult(score=0.85, method="custom")

method_registry.register("similarity", "custom_method", custom_similarity)

# Use custom method
method = method_registry.get("similarity", "custom_method")
result = method(entity1, entity2)
```

### DeduplicationConfig

Configuration manager for deduplication operations, supporting environment variables, config files, and programmatic configuration.

**Initialization:**

```python
DeduplicationConfig(config_file: Optional[str] = None)
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `set(key, value)` | Set configuration value programmatically | `None` |
| `get(key, default=None)` | Get configuration value | `Any` |
| `set_method_config(method, **config)` | Set method-specific configuration | `None` |
| `get_method_config(method)` | Get method-specific configuration | `Dict` |
| `get_all()` | Get all configuration | `Dict[str, Any]` |

**Example:**

```python
from veritasreason.deduplication.config import dedup_config

# Get configuration
threshold = dedup_config.get("similarity_threshold", default=0.7)

# Set configuration
dedup_config.set("similarity_threshold", 0.8)

# Method-specific configuration
dedup_config.set_method_config("levenshtein", case_sensitive=False)
levenshtein_config = dedup_config.get_method_config("levenshtein")
```

---

## Data Classes

### DuplicateCandidate

Represents a duplicate candidate pair with confidence scores.

**Fields:**
- `entity1`: First entity dictionary
- `entity2`: Second entity dictionary
- `similarity_score`: Similarity score (0.0 to 1.0)
- `confidence`: Confidence score (0.0 to 1.0)
- `reasons`: List of reasons why they're considered duplicates
- `metadata`: Additional metadata dictionary

### DuplicateGroup

Represents a group of duplicate entities.

**Fields:**
- `entities`: List of duplicate entity dictionaries
- `similarity_scores`: Dict mapping entity pairs to similarity scores
- `representative`: Representative entity (most complete)
- `confidence`: Group confidence score (0.0 to 1.0)
- `metadata`: Additional group metadata

### MergeOperation

Represents an entity merge operation.

**Fields:**
- `source_entities`: List of original entities that were merged
- `merged_entity`: Resulting merged entity dictionary
- `merge_result`: Detailed merge result with conflicts
- `timestamp`: Optional timestamp of merge operation
- `metadata`: Additional operation metadata

### SimilarityResult

Represents a similarity calculation result.

**Fields:**
- `score`: Overall similarity score (0.0 to 1.0)
- `method`: Calculation method used
- `components`: Dict of individual component scores
- `metadata`: Additional metadata dictionary

### Cluster

Represents an entity cluster.

**Fields:**
- `cluster_id`: Unique cluster identifier
- `entities`: List of entities in the cluster
- `centroid`: Optional representative entity (centroid)
- `quality_score`: Cluster quality score (0.0 to 1.0)
- `metadata`: Additional cluster metadata

### ClusterResult

Represents the result of cluster building.

**Fields:**
- `clusters`: List of Cluster objects
- `unclustered`: List of entities not in any cluster
- `quality_metrics`: Cluster quality metrics dictionary
- `metadata`: Additional result metadata

### MergeResult

Represents the result of a merge operation.

**Fields:**
- `merged_entity`: Resulting merged entity dictionary
- `merged_entities`: List of original entities that were merged
- `conflicts`: List of unresolved conflicts
- `metadata`: Additional merge metadata

### PropertyMergeRule

Represents a rule for merging specific properties.

**Fields:**
- `property_name`: Property name
- `strategy`: Merge strategy to use
- `conflict_resolution`: Optional custom conflict resolution function
- `priority`: Rule priority (higher priority rules take precedence)

### MergeStrategy

Enumeration of available merge strategies.

**Values:**
- `KEEP_FIRST`: Keep the first entity encountered
- `KEEP_LAST`: Keep the last entity encountered
- `KEEP_MOST_COMPLETE`: Keep entity with most properties/relationships
- `KEEP_HIGHEST_CONFIDENCE`: Keep entity with highest confidence score
- `MERGE_ALL`: Create new entity combining all info
- `CUSTOM`: Use custom merge logic

---

## Convenience Functions

### detect_duplicates

Convenience function for duplicate detection with multiple methods.

```python
from veritasreason.deduplication.methods import detect_duplicates

# Pairwise detection
candidates = detect_duplicates(
    entities,
    method="pairwise",
    similarity_threshold=0.8,
    confidence_threshold=0.7
)

# Group detection
groups = detect_duplicates(
    entities,
    method="group",
    similarity_threshold=0.8
)

# Incremental detection
new_candidates = detect_duplicates(
    new_entities,
    method="incremental",
    existing_entities=existing_entities,
    similarity_threshold=0.8
)
```

**Methods:**
- `"pairwise"`: O(n²) comparison of all entity pairs
- `"batch"`: Efficient batch similarity calculation
- `"incremental"`: O(n×m) comparison for new vs existing entities
- `"group"`: Union-find algorithm for duplicate group formation

### merge_entities

Convenience function for entity merging with multiple strategies.

```python
from veritasreason.deduplication.methods import merge_entities

operations = merge_entities(
    duplicate_entities,
    method="keep_most_complete",
    preserve_provenance=True
)
```

**Methods:**
- `"keep_first"`: Preserve first entity, merge others
- `"keep_last"`: Preserve last entity, merge others
- `"keep_most_complete"`: Preserve entity with most properties/relationships
- `"keep_highest_confidence"`: Preserve entity with highest confidence
- `"merge_all"`: Combine all properties and relationships

### calculate_similarity

Convenience function for similarity calculation with multiple methods.

```python
from veritasreason.deduplication.methods import calculate_similarity

# Different similarity methods
exact_result = calculate_similarity(entity1, entity2, method="exact")
lev_result = calculate_similarity(entity1, entity2, method="levenshtein")
jaro_result = calculate_similarity(entity1, entity2, method="jaro_winkler")
multi_result = calculate_similarity(entity1, entity2, method="multi_factor")
```

**Methods:**
- `"exact"`: Exact string matching
- `"levenshtein"`: Levenshtein distance-based similarity
- `"jaro_winkler"`: Jaro-Winkler similarity with prefix bonus
- `"cosine"`: Cosine similarity for embeddings
- `"property"`: Property value comparison
- `"relationship"`: Jaccard similarity of relationships
- `"embedding"`: Cosine similarity of vector embeddings
- `"multi_factor"`: Weighted aggregation of all components

### build_clusters

Convenience function for cluster building with multiple methods.

```python
from veritasreason.deduplication.methods import build_clusters

# Graph-based clustering
result = build_clusters(
    entities,
    method="graph_based",
    similarity_threshold=0.8
)

# Hierarchical clustering
result = build_clusters(
    entities,
    method="hierarchical",
    similarity_threshold=0.8
)
```

**Methods:**
- `"graph_based"`: Union-find algorithm for connected components
- `"hierarchical"`: Agglomerative clustering for large datasets

### get_deduplication_method

Get deduplication method by task and name.

```python
from veritasreason.deduplication.methods import get_deduplication_method

method = get_deduplication_method("similarity", "levenshtein")
if method:
    result = method(entity1, entity2)
```

### list_available_methods

List all available deduplication methods.

```python
from veritasreason.deduplication.methods import list_available_methods

# List all methods
all_methods = list_available_methods()

# List methods for specific task
similarity_methods = list_available_methods("similarity")
```

---

## Configuration

The deduplication module supports multiple configuration sources: environment variables, config files (YAML, JSON, TOML), and programmatic configuration.

### Environment Variables

```bash
export DEDUP_SIMILARITY_THRESHOLD=0.8
export DEDUP_CONFIDENCE_THRESHOLD=0.7
export DEDUP_USE_CLUSTERING=true
export DEDUP_PRESERVE_PROVENANCE=true
export DEDUP_DEFAULT_STRATEGY=keep_most_complete
export DEDUP_MIN_CLUSTER_SIZE=2
export DEDUP_MAX_CLUSTER_SIZE=100
```

### YAML Configuration

```yaml
deduplication:
  similarity_threshold: 0.8
  confidence_threshold: 0.7
  use_clustering: true
  preserve_provenance: true
  default_strategy: keep_most_complete
  min_cluster_size: 2
  max_cluster_size: 100

deduplication_methods:
  levenshtein:
    case_sensitive: false
  multi_factor:
    string_weight: 0.4
    property_weight: 0.3
    embedding_weight: 0.3
```

### Programmatic Configuration

```python
from veritasreason.deduplication.config import dedup_config

# Set configuration values
dedup_config.set("similarity_threshold", 0.8)
dedup_config.set("confidence_threshold", 0.7)

# Get configuration values
threshold = dedup_config.get("similarity_threshold", default=0.7)

# Method-specific configuration
dedup_config.set_method_config("levenshtein", case_sensitive=False)
levenshtein_config = dedup_config.get_method_config("levenshtein")

# Load from config file
from veritasreason.deduplication.config import DeduplicationConfig
config = DeduplicationConfig(config_file="config.yaml")
```

### Configuration File Support

The `DeduplicationConfig` class supports loading configuration from:
- **YAML files** (`.yaml`, `.yml`)
- **JSON files** (`.json`)
- **TOML files** (`.toml`)

Configuration is loaded in the following priority order:
1. Programmatic configuration (via `set()`)
2. Environment variables
3. Config file values
4. Default values

---

## Integration Examples

### Ingestion Pipeline

```python
from veritasreason.core import VeritasReason
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor
from veritasreason.deduplication import DuplicateDetector, EntityMerger, MergeStrategy

# 1. Build knowledge base using individual modules
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()

all_entities = []
for file_path in files:
    doc = ingestor.ingest_file(file_path)
    parsed = parser.parse_document(file_path)
    text = parsed.get("full_text", "")
    entities = ner.extract_entities(text)
    all_entities.extend(entities)

raw_entities = all_entities

# 2. Deduplicate
detector = DuplicateDetector(similarity_threshold=0.85)
duplicate_groups = detector.detect_duplicate_groups(raw_entities)

merger = EntityMerger(preserve_provenance=True)
merge_operations = merger.merge_duplicates(
    raw_entities,
    strategy=MergeStrategy.MERGE_ALL
)

# Extract merged entities
merged_entities = [op.merged_entity for op in merge_operations]
```

---

## Best Practices

1.  **Block First**: For >1000 entities, enable blocking to avoid O(n²) performance.
2.  **Tune Thresholds**: Start with 0.85 and adjust based on false positive/negative rates.
3.  **Preserve Provenance**: Keep `preserve_provenance=True` to track where merged data came from.
4.  **Normalize**: Run `normalize` module before deduplication for best results.

---

## Troubleshooting

**Issue**: Merging "Apple" and "Apple Pie" (False Positive).
**Solution**: Increase threshold or use Jaro-Winkler which penalizes prefix mismatches.

```python
detector = DuplicateDetector(
    similarity_method="jaro_winkler",
    similarity_threshold=0.9
)
```

**Issue**: Slow performance on large datasets.
**Solution**: Use `ClusterBuilder` with blocking.

---

## See Also

- [Conflicts Module](conflicts.md) - Handling conflicting values during merge
- [Normalize Module](normalize.md) - Pre-processing for better matching
- [Knowledge Graph Module](kg.md) - Target for deduplicated data

## Cookbook

Interactive tutorials to learn deduplication:

- **[Deduplication](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/18_Deduplication.ipynb)**: Advanced deduplication techniques for entity resolution
  - **Topics**: Entity deduplication, fuzzy matching, similarity thresholds, merge strategies
  - **Difficulty**: Intermediate
  - **Use Cases**: Entity resolution, data cleaning, multi-source integration
