# Semantic Extract

> **Advanced information extraction system for Entities, Relations, Events, and Triplets.**

---

## 🎯 Overview

The **Semantic Extract Module** extracts structured information from unstructured text. It identifies entities, relationships, events, and semantic structures that form the foundation of knowledge graphs.

### What is Semantic Extraction?

**Semantic extraction** is the process of identifying meaningful information from text:
- **Named Entities**: People, organizations, locations, dates, etc.
- **Relationships**: Connections between entities (e.g., "founded_by", "located_in")
- **Events**: Actions with temporal information and participants
- **Triplets**: Subject-Predicate-Object structures for knowledge graphs
- **Semantic Networks**: Structured networks of nodes and edges

### Why Use the Semantic Extract Module?

- **Multiple Methods**: Support for ML models, LLMs, and rule-based extraction
- **High Accuracy**: LLM-based extraction for complex schemas
- **Flexible Configuration**: Customize extraction for your domain
- **Confidence Scores**: Get confidence scores for all extractions
- **Batch Processing**: Efficient parallel batch processing for large datasets
- **Coreference Resolution**: Resolve pronouns to their entity references

### How It Works

1. **Text Input**: Receive parsed text from the parse module
2. **Entity Extraction**: Identify named entities using NER
3. **Coreference Resolution**: Resolve pronouns to entities (optional)
4. **Relationship Extraction**: Identify relationships between entities
5. **Event Detection**: Detect events with temporal information
6. **Triplet Generation**: Generate RDF triplets for knowledge graphs
7. **Output**: Return structured entities, relationships, and triplets

<div class="grid cards" markdown>

-   :material-account-search:{ .lg .middle } **NER**

    ---

    Extract Named Entities (Person, Org, Loc) with confidence scores

-   :material-relation-one-to-one:{ .lg .middle } **Relation Extraction**

    ---

    Identify relationships between entities (e.g., `founded_by`, `located_in`)

-   :material-calendar-clock:{ .lg .middle } **Event Detection**

    ---

    Detect events with temporal information and participants

-   :material-format-quote-close:{ .lg .middle } **Coreference**

    ---

    Resolve pronouns ("he", "it") to their entity references

-   :material-share-variant:{ .lg .middle } **Triplet Extraction**

    ---

    Extract Subject-Predicate-Object triplets for Knowledge Graphs

-   :material-robot:{ .lg .middle } **LLM Extraction**

    ---

    Use LLMs to improve extraction quality and handle complex schemas

-   :material-graph:{ .lg .middle } **Semantic Networks**

    ---

    Build structured networks with nodes and edges from text

</div>

!!! tip "When to Use"
    - **KG Construction**: Converting unstructured text into structured graph data
    - **Text Analysis**: Identifying key actors and events in documents
    - **Search Indexing**: Extracting metadata for faceted search
    - **Data Enrichment**: Adding semantic tags to content

---

## ⚙️ Algorithms Used

### Named Entity Recognition (NER)

**Purpose**: Identify and classify named entities in text.

**How it works**:

- **Transformer Models**: BERT/RoBERTa for token classification
- **Regex Patterns**: Pattern matching for specific formats (Emails, IDs)
- **LLM Prompting**: Zero-shot extraction for custom entity types

### Relation Extraction

**Purpose**: Identify relationships between entities.

**How it works**:

- **Dependency Parsing**: Analyzing grammatical structure to find subject-verb-object paths
- **Joint Extraction**: Extracting entities and relations simultaneously
- **Semantic Role Labeling**: Identifying "Who did What to Whom"

### Coreference Resolution

**Purpose**: Resolve pronouns and references to their entity references.

**How it works**:

- **Mention Detection**: Finding all potential references (nouns, pronouns)
- **Clustering**: Grouping mentions that refer to the same real-world entity
- **Pronoun Resolution**: Mapping pronouns to the most likely antecedent

### Triplet Extraction

**Purpose**: Extract Subject-Predicate-Object triplets for Knowledge Graphs.

**How it works**:

- **OpenIE**: Open Information Extraction for arbitrary relation strings
- **Schema-Based**: Mapping extracted relations to a predefined ontology
- **Reification**: Handling complex relations (time, location) by creating event nodes.

---

## Main Classes

### NamedEntityRecognizer

Coordinator for entity extraction.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `methods` | list | `["spacy"]` | Extraction methods to use |
| `confidence_threshold` | float | `0.5` | Minimum confidence score |
| `merge_overlapping` | bool | `True` | Merge overlapping entities |
| `include_standard_types` | bool | `True` | Include Person, Org, Location |

**Methods:**

| Method | Description |
|--------|-------------|
| `extract_entities(text)` | Get list of entities |
| `add_custom_pattern(pattern)` | Add regex rule |

**Example:**

```python
from veritasreason.semantic_extract import NamedEntityRecognizer

# Basic usage
ner = NamedEntityRecognizer()
entities = ner.extract_entities("Elon Musk leads SpaceX.")
# [Entity(text="Elon Musk", label="PERSON"), Entity(text="SpaceX", label="ORG")]

# With configuration
ner = NamedEntityRecognizer(
    methods=["spacy", "rule-based"],
    confidence_threshold=0.7,
    merge_overlapping=True
)
entities = ner.extract_entities("Apple Inc. was founded in 1976.")
```

### NERExtractor

Core entity extraction implementation used by notebooks and lower-level integrations.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str or list | `"ml"` | Method(s): "ml", "llm", "pattern", "regex", "huggingface" |
| `entity_types` | list | `None` | Filter for specific entity types |
| `**config` | dict | `{}` | Method-specific config (e.g., `model`, `aggregation_strategy`, `device`) |

**Methods:**

| Method | Description |
|--------|-------------|
| `extract(text, pipeline_id=None, **kwargs)` | Alias for `extract_entities`. Supports `max_workers`. |
| `extract_entities(text, pipeline_id=None, **kwargs)` | Get list of entities. Supports `max_workers`. |

**Example:**

```python
from veritasreason.semantic_extract import NERExtractor

# 1. ML (spaCy) - Default
extractor = NERExtractor(method="ml", model="en_core_web_trf")
entities = extractor.extract("Elon Musk leads SpaceX.")

# 2. LLM (OpenAI/Gemini/Groq/etc)
extractor = NERExtractor(
    method="llm", 
    provider="groq", 
    model="llama-3.3-70b-versatile",
    max_tokens=2048, # Increased output limit
    temperature=0.0
)

# 3. Regex with custom patterns
patterns = {"CODE": r"[A-Z]{3}-\d{3}"}
extractor = NERExtractor(method="regex", patterns=patterns)

# 4. Ensemble (Multiple methods)
extractor = NERExtractor(method=["ml", "llm"], ensemble_voting=True)
```

### RelationExtractor

Extracts relationships between entities.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str | `"dependency"` | Method: "dependency", "pattern", "cooccurrence", "huggingface", "llm" |
| `relation_types` | list | `None` | Specific relation types to extract |
| `bidirectional` | bool | `False` | Extract bidirectional relations |
| `confidence_threshold` | float | `0.6` | Minimum confidence score |
| `max_distance` | int | `50` | Max token distance between entities |
| `**config` | dict | `{}` | Method-specific config (e.g., `model`, `device` for HuggingFace) |

**Methods:**

| Method | Description |
|--------|-------------|
| `extract(text, entities, pipeline_id=None, **kwargs)` | Alias for `extract_relations`. Supports `max_workers`. |
| `extract_relations(text, entities, pipeline_id=None, **kwargs)` | Find links. Supports `max_workers`. |

**Example:**

```python
from veritasreason.semantic_extract import RelationExtractor, NamedEntityRecognizer

# First extract entities
ner = NamedEntityRecognizer()
text = "Elon Musk founded SpaceX in 2002."
entities = ner.extract_entities(text)

# Basic relation extraction
rel_extractor = RelationExtractor()
relations = rel_extractor.extract(text, entities=entities)
# [Relation(subject="Elon Musk", predicate="founded", object="SpaceX")]

# With configuration
rel_extractor = RelationExtractor(
    relation_types=["founded", "leads", "works_at"],
    confidence_threshold=0.7,
    bidirectional=False
)
relations = rel_extractor.extract(text, entities=entities)
```

### CoreferenceResolver

Resolves pronoun references and entity coreferences.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str or list | `None` | Underlying NER method(s) |
| `**config` | dict | `{}` | Configuration for NER method |

**Methods:**

| Method | Description |
|--------|-------------|
| `resolve(text)` | Alias for `resolve_coreferences`. Get coreference chains. |
| `resolve_coreferences(text)` | Get coreference chains |
| `resolve_pronouns(text)` | Resolve pronouns to entities |

**Example:**

```python
from veritasreason.semantic_extract import CoreferenceResolver

resolver = CoreferenceResolver()
text = "Steve Jobs founded Apple. He was the CEO."

# Resolve references
chains = resolver.resolve(text)
# [CoreferenceChain(mentions=["Steve Jobs", "He"], representative="Steve Jobs")]
```

### EventDetector

Identifies events with temporal information and participants.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_types` | list | `None` | Specific event types to detect |
| `extract_participants` | bool | `True` | Extract event participants |
| `extract_location` | bool | `True` | Extract event locations |
| `extract_time` | bool | `True` | Extract temporal information |
| `max_workers` | int | `1` | Threads for parallel batch processing |

**Methods:**

| Method | Description |
|--------|-------------|
| `detect_events(text)` | Find events |

**Example:**

```python
from veritasreason.semantic_extract import EventDetector

detector = EventDetector(
    event_types=["launch", "acquisition", "announcement"],
    extract_participants=True,
    extract_time=True
)
events = detector.detect_events("SpaceX launched Starship on March 14, 2024.")
```

### TripletExtractor

Extracts RDF triplets (Subject-Predicate-Object).

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | str | `"pattern"` | Extraction method ("pattern", "rules", "huggingface", "llm") |
| `triplet_types` | list | `None` | Specific triplet types/predicates to extract |
| `include_temporal` | bool | `False` | Include time information |
| `include_provenance` | bool | `False` | Track source sentences |
| `**kwargs` | dict | `{}` | Configuration options (e.g., `model`, `device`) |

**Methods:**

| Method | Description |
|--------|-------------|
| `extract(text, entities=None, relations=None, pipeline_id=None, **kwargs)` | Alias for `extract_triplets`. Supports `max_workers`. |
| `extract_triplets(text, entities=None, relations=None, pipeline_id=None, **kwargs)` | Get (S, P, O) tuples. Supports `max_workers`. |

**Example:**

```python
from veritasreason.semantic_extract import TripletExtractor

extractor = TripletExtractor(
    include_temporal=True,
    include_provenance=True
)
triplets = extractor.extract_triplets("Steve Jobs founded Apple in 1976.")
# [Triplet(subject="Steve Jobs", predicate="founded", object="Apple", temporal="1976")]
```

### SemanticNetworkExtractor

Extracts structured semantic networks with nodes and edges.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ner_method` | str | `None` | Method for node extraction |
| `relation_method` | str | `None` | Method for edge extraction |
| `max_workers` | int | `1` | Threads for parallel batch processing |
| `**config` | dict | `{}` | Configuration for underlying extractors |

**Methods:**

| Method | Description |
|--------|-------------|
| `extract_network(text)` | Build network from text |
| `extract(text)` | Alias for `extract_network` |
| `export_to_yaml(network, path)` | Save network to YAML |

**Example:**

```python
from veritasreason.semantic_extract import SemanticNetworkExtractor

extractor = SemanticNetworkExtractor()
network = extractor.extract("Apple Inc. is located in Cupertino.")

# Analyze network
print(f"Nodes: {len(network.nodes)}")
print(f"Edges: {len(network.edges)}")
```

### LLMExtraction

LLM-based extraction and enhancement. (Alias: `LLMEnhancer`)

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | str | `"openai"` | LLM provider ("openai", "gemini", "anthropic", etc.) |
| `**config` | dict | `{}` | Model config (model name, api_key, etc.) |

**Methods:**

| Method | Description |
|--------|-------------|
| `enhance_extractions(extractions, text)` | Enhance generic extractions |
| `enhance_entities(text, entities)` | Improve entity accuracy and details |
| `enhance_relations(text, relations)` | Improve relation detection |

**Example:**

```python
from veritasreason.semantic_extract import LLMExtraction

extractor = LLMExtraction(provider="openai", model="gpt-4")
enhanced_entities = extractor.enhance_entities(text, entities)
```

---

## Batch Processing & Provenance

All extractors support batch processing for high-throughput extraction. You can pass a list of strings or a list of dictionaries (with `content` and `id` keys).

**Features:**
- **Progress Tracking**: Automatically shows a progress bar for large batches.
- **Provenance Metadata**: Each extracted item includes `batch_index` and `document_id` in its `metadata`.

```python
from veritasreason.semantic_extract import NERExtractor

documents = [
    {"id": "doc_1", "content": "Apple Inc. was founded by Steve Jobs."},
    {"id": "doc_2", "content": "Microsoft Corporation was founded by Bill Gates."}
]

extractor = NERExtractor()
batch_results = extractor.extract(documents)

for i, doc_entities in enumerate(batch_results):
    print(f"Document {i} entities:")
    for entity in doc_entities:
        print(f"  - {entity.text} ({entity.label})")
        print(f"    Provenance: Batch Index {entity.metadata['batch_index']}, Doc ID {entity.metadata.get('document_id')}")
```

## Robust Extraction Fallbacks

The framework implements robust fallback chains to prevent empty results when primary methods fail (e.g., due to model unavailability or obscure text).

- **NER**: `ML/LLM` -> `Pattern` -> `Last Resort` (Capitalized Words)
- **Relation**: `Primary` -> `Pattern` -> `Last Resort` (Adjacency)
- **Triplet**: `Primary` -> `Relation-to-Triplet` -> `Pattern`

This ensures that you almost always get *some* structured data, even if it requires falling back to simpler heuristics.

---

## Usage Examples

```python
from veritasreason.semantic_extract import (
    NamedEntityRecognizer, 
    RelationExtractor,
    TripletExtractor,
    EventDetector,
    CoreferenceResolver,
    SemanticNetworkExtractor
)

text = "Apple released the iPhone in 2007. Steve Jobs announced it at Macworld."

# Extract entities with confidence filtering
ner = NamedEntityRecognizer(confidence_threshold=0.7)
entities = ner.extract_entities(text)

# Resolve coreferences (recommended before relation extraction)
coref = CoreferenceResolver()
resolved = coref.resolve(text)

# Extract relations
rel_extractor = RelationExtractor(confidence_threshold=0.6)
relations = rel_extractor.extract_relations(text, entities=entities)

# Extract triplets for KG
triplet_extractor = TripletExtractor(include_temporal=True)
triplets = triplet_extractor.extract_triplets(text)

# Detect events
event_detector = EventDetector(extract_time=True)
events = event_detector.detect_events(text)

# Extract semantic network
network_extractor = SemanticNetworkExtractor()
network = network_extractor.extract(text)

print(f"Entities: {len(entities)}")
print(f"Relations: {len(relations)}")
print(f"Triplets: {len(triplets)}")
print(f"Events: {len(events)}")
print(f"Network Nodes: {len(network.nodes)}")
```

---

## Configuration

### Environment Variables

```bash
export NER_MODEL=dslim/bert-base-NER
export RELATION_MODEL=veritasreason/rel-extract-v1
export EXTRACT_CONFIDENCE_THRESHOLD=0.7
```

### YAML Configuration

```yaml
semantic_extract:
  ner:
    model: dslim/bert-base-NER
    min_confidence: 0.7
    
  relations:
    max_distance: 50 # tokens
    
  coreference:
    enabled: true
```

---

## Integration Examples

### KG Population Pipeline

```python
from veritasreason.semantic_extract import NamedEntityRecognizer, RelationExtractor, TripletExtractor
from veritasreason.kg import GraphBuilder

# 1. Extract
text = "Google was founded by Larry Page and Sergey Brin."
ner = NamedEntityRecognizer()
entities = ner.extract_entities(text)
triplet_extractor = TripletExtractor()
triplets = triplet_extractor.extract_triplets(text)

# 2. Populate KG using GraphBuilder
builder = GraphBuilder()
sources = [{
    "entities": entities,
    "relationships": [{"source": t.subject, "target": t.object, "type": t.predicate} for t in triplets]
}]
kg = builder.build(sources)
```

---

## Best Practices

1.  **Resolve Coreferences**: Always run coreference resolution *before* relation extraction to link "He" to "John Doe".
2.  **Filter Low Confidence**: Set a confidence threshold (e.g., 0.7) to reduce noise.
3.  **Use Custom Patterns**: For domain-specific IDs (e.g., "Invoice #123"), regex is faster and more accurate than ML.
4.  **Batch Processing**: Use batch methods when processing large corpora.

---

## See Also

- [Parse Module](parse.md) - Prepares text for extraction
- [Ontology Module](ontology.md) - Defines the schema for extraction
- [Knowledge Graph Module](kg.md) - Stores the extracted data

## Cookbook

Interactive tutorials to learn semantic extraction:

- **[Entity Extraction](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/05_Entity_Extraction.ipynb)**: Extract named entities from text using NER
  - **Topics**: NER, Spacy, LLM extraction, entity types, confidence scores
  - **Difficulty**: Beginner
  - **Use Cases**: Identifying entities in text, building entity lists

- **[Relation Extraction](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/06_Relation_Extraction.ipynb)**: Discover and classify relationships between entities
  - **Topics**: Relation classification, dependency parsing, relationship types
  - **Difficulty**: Beginner
  - **Use Cases**: Finding relationships, building knowledge graphs

- **[Advanced Extraction](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/01_Advanced_Extraction.ipynb)**: Custom extractors, LLM-based extraction, and complex pattern matching
  - **Topics**: Custom models, regex, LLMs, ensemble methods, domain-specific extraction
  - **Difficulty**: Advanced
  - **Use Cases**: Custom extraction schemas, domain-specific entities
