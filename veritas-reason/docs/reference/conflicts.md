# Conflicts

> **Comprehensive conflict detection and resolution system for managing data discrepancies across multiple sources.**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-alert-decagram:{ .lg .middle } **Multi-Source Detection**

    ---

    Detect conflicts across values, types, relationships, and temporal data

-   :material-scale-balance:{ .lg .middle } **Resolution Strategies**

    ---

    Resolve using voting, credibility, recency, or confidence scores

-   :material-chart-line:{ .lg .middle } **Conflict Analysis**

    ---

    Analyze patterns, trends, and severity of data discrepancies

-   :material-source-branch:{ .lg .middle } **Source Tracking**

    ---

    Track data provenance and source credibility

-   :material-clipboard-check:{ .lg .middle } **Investigation Guides**

    ---

    Generate automated guides for manual conflict resolution

-   :material-history:{ .lg .middle } **Traceability**

    ---

    Maintain full traceability of resolution decisions

</div>

!!! tip "When to Use"
    - **Data Integration**: When merging data from multiple sources with overlapping entities
    - **Quality Assurance**: To identify inconsistent data in your knowledge graph
    - **Truth Maintenance**: To establish a "single source of truth" from noisy data

---

## ⚙️ Algorithms Used

### Conflict Detection

The conflict detection system identifies discrepancies using:

- **Value Comparison**: Equality checking with type normalization
- **Type Mismatch**: Entity type hierarchy validation
- **Temporal Analysis**: Timestamp comparison for time-based conflicts
- **Logical Consistency**: Rule-based validation (e.g., "Person cannot be Organization")
- **Severity Calculation**: Multi-factor scoring based on:
    - Property importance weights
    - Value difference magnitude
    - Number of conflicting sources

### Conflict Resolution

The module provides multiple resolution strategies:

- **Voting (Majority Rule)**: `` `max(frequency(values))` `` using Counter
- **Credibility Weighted**: `` `Σ(value_i * source_credibility_i) / Σ(source_credibility)` ``
- **Temporal Selection**: Select value with latest timestamp (`` `max(timestamp)` ``)
- **Confidence Selection**: Select value with highest extraction confidence
- **Hybrid Resolution**: Waterfall approach (e.g., Voting → Credibility → Recency)

### Analysis & Tracking
- **Pattern Identification**: Frequency analysis of conflict types
- **Credibility Scoring**: Historical accuracy tracking per source
- **Traceability**: Graph-based lineage of values and decisions

---

## Main Classes

### ConflictDetector

Detects conflicts across entities and properties.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `detect_conflicts(entities, entity_type)` | Detect all conflicts | Multi-pass detection |
| `detect_value_conflicts(entities, property_name, entity_type)` | Check specific property | Value comparison |
| `detect_type_conflicts(entities)` | Check entity types | Hierarchy validation |
| `detect_temporal_conflicts(entities)` | Check timestamps | Time-series analysis |
| `detect_logical_conflicts(entities)` | Check logical inconsistencies | Rule validation |
| `detect_relationship_conflicts(relationships)` | Check relationship conflicts | Relationship comparison |
| `detect_entity_conflicts(entities, entity_type)` | Detect all conflicts for entity | Multi-property detection |
| `get_conflict_report()` | Generate conflict report | Report generation |

**Example:**

```python
from veritasreason.conflicts import ConflictDetector

detector = ConflictDetector()
conflicts = detector.detect_conflicts([
    {"id": "1", "name": "Apple", "source": "doc1"},
    {"id": "1", "name": "Apple Inc.", "source": "doc2"}
])

for conflict in conflicts:
    print(f"Conflict on {conflict.property_name}: {conflict.conflicting_values}")
```

### ConflictResolver

Resolves detected conflicts using configured strategies.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `resolve_conflicts(conflicts, strategy)` | Resolve list of conflicts | Strategy pattern |
| Strategies: `voting`, `credibility_weighted`, `most_recent`, `first_seen`, `highest_confidence`, `manual_review` | Various resolution strategies | See algorithm descriptions |

**Example:**

```python
from veritasreason.conflicts import ConflictResolver

resolver = ConflictResolver(default_strategy="credibility_weighted")
results = resolver.resolve_conflicts(conflicts)

for result in results:
    if result.resolved:
        print(f"Resolved conflict {result.conflict_id}: {result.resolved_value}")
        print(f"Strategy used: {result.resolution_strategy}")
```

### SourceTracker

Tracks source information and credibility scores.

**Methods:**

| Method | Description |
|--------|-------------|
| `track_property_source(entity_id, property_name, value, source)` | Track source for property value |
| `track_entity_source(entity_id, source)` | Track source for entity |
| `track_relationship_source(relationship_id, source)` | Track source for relationship |
| `get_source_credibility(document)` | Get current credibility score |
| `set_source_credibility(document, score)` | Set source credibility score |
| `get_property_sources(entity_id, property_name)` | Get sources for a property |
| `get_entity_sources(entity_id)` | Get all sources for an entity |
| `generate_traceability_chain(entity_id, property_name)` | Generate traceability chain |
| `generate_source_report(entity_id)` | Generate source analysis report |

**Example:**

```python
from veritasreason.conflicts import SourceTracker, SourceReference

tracker = SourceTracker()
tracker.set_source_credibility("reliable_source", 0.9)
tracker.set_source_credibility("noisy_source", 0.4)

# Track property sources
source = SourceReference(document="doc1", confidence=0.9)
tracker.track_property_source("entity_1", "name", "Apple Inc.", source)
```

### InvestigationGuideGenerator

Generates human-readable guides for manual resolution.

**Methods:**

| Method | Description |
|--------|-------------|
| `generate_guide(conflict, additional_context)` | Create investigation guide for a conflict |
| `generate_guides(conflicts, additional_context)` | Create investigation guides for multiple conflicts |
| `export_investigation_checklist(guide, format)` | Export guide as checklist (text/markdown) |
| `generate_conflict_report(conflicts, format)` | Generate comprehensive conflict report |

**Example:**

```python
from veritasreason.conflicts import InvestigationGuideGenerator

generator = InvestigationGuideGenerator()
guide = generator.generate_guide(conflict)
checklist = generator.export_investigation_checklist(guide, format="markdown")
```

### ConflictAnalyzer

Analyzes conflict patterns, trends, and provides recommendations.

**Methods:**

| Method | Description |
|--------|-------------|
| `analyze_conflicts(conflicts)` | Comprehensive conflict analysis |
| `analyze_trends(conflicts)` | Temporal trend analysis |
| `generate_insights_report(conflicts)` | Generate insights report |

**Example:**

```python
from veritasreason.conflicts import ConflictAnalyzer

analyzer = ConflictAnalyzer()
analysis = analyzer.analyze_conflicts(conflicts)
trends = analyzer.analyze_trends(conflicts)
insights = analyzer.generate_insights_report(conflicts)
```

---

## Configuration

### Environment Variables

```bash
export CONFLICT_DEFAULT_STRATEGY=voting
export CONFLICT_SIMILARITY_THRESHOLD=0.85
export CONFLICT_AUTO_RESOLVE=true
```

### YAML Configuration

```yaml
conflicts:
  default_strategy: voting
  auto_resolve: true
  
  strategies:
    voting:
      min_votes: 2
    credibility:
      default_score: 0.5
      
  weights:
    name: 1.0
    description: 0.5
    date: 0.8
```

---

## Integration Examples

### Pipeline Integration

```python
from veritasreason.conflicts import ConflictDetector, ConflictResolver
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor
from veritasreason.kg import GraphBuilder

# 1. Build knowledge base from multiple sources using individual modules
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()
builder = GraphBuilder()

all_entities = []
for source in ["source1.pdf", "source2.html"]:
    doc = ingestor.ingest_file(source)
    parsed = parser.parse_document(source)
    text = parsed.get("full_text", "")
    entities = ner.extract_entities(text)
    all_entities.extend(entities)

kg = builder.build_graph(entities=all_entities, relationships=[])
entities = all_entities

# 3. Detect conflicts
detector = ConflictDetector()
conflicts = detector.detect_value_conflicts(entities, "revenue")

# 4. Resolve conflicts
resolver = ConflictResolver(default_strategy="credibility_weighted")
resolutions = resolver.resolve_conflicts(
    conflicts,
    strategy="credibility_weighted"
)

# 5. Apply resolutions
for resolution in resolutions:
    if resolution.resolved:
        print(f"Final value for {resolution.conflict_id}: {resolution.resolved_value}")
```

---

## Best Practices

1.  **Define Source Credibility**: Always assign credibility scores to your sources if possible.
2.  **Use Hybrid Strategies**: Voting is good for categorical data, Recency for temporal data.
3.  **Keep Humans in the Loop**: Use `InvestigationGuideGenerator` for high-severity conflicts.
4.  **Normalize First**: Ensure data is normalized (dates, numbers) before conflict detection to avoid false positives.

---

## Troubleshooting

**Issue**: Too many false positives on string fields.
**Solution**: Enable fuzzy matching or increase similarity threshold.

```python
detector = ConflictDetector(
    string_similarity_threshold=0.9,  # Stricter matching
    ignore_case=True
)
```

**Issue**: Resolution favoring wrong source.
**Solution**: Check and adjust source credibility scores.

```python
tracker.set_source_credibility("bad_source", 0.1)
```

---

## See Also

- [Deduplication Module](deduplication.md) - For merging duplicate entities
- [Normalize Module](normalize.md) - For pre-processing data
- [Modules Guide](../modules.md#quality-assurance) - Quality assurance overview

## Cookbook

Interactive tutorials to learn conflict detection and resolution:

- **[Conflict Detection & Resolution](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/17_Conflict_Detection_and_Resolution.ipynb)**: Strategies for handling contradictory information from multiple sources
  - **Topics**: Truth discovery, voting, confidence scoring, conflict resolution strategies
  - **Difficulty**: Advanced
  - **Use Cases**: Multi-source data integration, quality assurance
