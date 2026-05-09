# VeritasReason - Semantic Layer & Knowledge Engineering Framework

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/Hawksight-AI/veritas-reason/blob/main/LICENSE)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/veritas-reason-dev/veritasreason)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://docs.veritasreason.dev)

**VeritasReason** is a comprehensive Python framework for building semantic layers and performing knowledge engineering from unstructured data. It provides production-ready tools for transforming raw data into structured, queryable knowledge graphs with advanced semantic understanding.

## 🚀 Key Features

### Core Capabilities
- **Universal Data Ingestion**: Process documents, web content, structured data, emails, and more
- **Advanced Semantic Processing**: Extract entities, relationships, and events with high accuracy
- **Knowledge Graph Construction**: Build and manage complex knowledge graphs
- **Multi-Modal Support**: Handle text, images, audio, and video content
- **Real-Time Processing**: Stream processing and real-time analytics
- **Production Ready**: Enterprise-grade quality assurance and monitoring

### Semantic Intelligence
- **Named Entity Recognition**: Extract and classify entities from text
- **Relationship Extraction**: Identify relationships between entities
- **Event Detection**: Detect and analyze events in text
- **Coreference Resolution**: Resolve pronoun and entity references
- **Semantic Similarity**: Calculate semantic similarity between texts
- **Ontology Generation**: Automatically generate ontologies from data

### Knowledge Engineering
- **Knowledge Graph Management**: Build, query, and analyze knowledge graphs
- **Graph Analytics**: Centrality measures, community detection, connectivity analysis
- **Entity Resolution**: Deduplicate and resolve entity conflicts
- **Provenance Tracking**: Track data sources and processing history


### Visualization & Analytics
- **Interactive Visualizations**: Plotly-based interactive charts and graphs
- **Knowledge Graph Networks**: Network visualizations with community and centrality coloring
- **Ontology Hierarchies**: Class hierarchy trees and property graphs
- **Embedding Projections**: 2D/3D projections with UMAP, t-SNE, and PCA
- **Analytics Visualizations**: Centrality rankings, community structures, connectivity analysis
- **Temporal Views**: Timeline and evolution visualizations

## 📦 Installation

### Basic Installation
```bash
pip install veritas-reason
```

### With GPU Support
```bash
pip install veritas-reason[gpu]
```

### With Cloud Support
```bash
pip install veritas-reason[cloud]
```

### With Monitoring
```bash
pip install veritas-reason[monitoring]
```

### With Visualization (Optional)
```bash
pip install veritas-reason[viz]
```

Note: Visualization dependencies (plotly, matplotlib, seaborn) are included by default. The `viz` extra includes optional dependencies like `umap-learn` and `graphviz` for advanced features.

### Development Installation
```bash
git clone https://github.com/veritas-reason-dev/veritasreason.git
cd veritasreason
pip install -e ".[dev]"
```

## 🎯 Quick Start

> **User-Friendly API**: VeritasReason supports lazy initialization. No need to call `initialize()` explicitly - the framework auto-initializes on first use. Access submodules via dot notation like `veritasreason.kg`, `veritasreason.embeddings`, etc.

#### API Usage Patterns

**Pattern 1: Using Individual Modules (Recommended)**
```python
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder
from veritasreason.embeddings import TextEmbedder

# Use individual modules for full control
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()
rel_extractor = RelationExtractor()
builder = GraphBuilder(merge_entities=True)
embedder = TextEmbedder()

# Build knowledge base step by step
docs = ingestor.ingest_file("doc1.pdf")
parsed = parser.parse_document("doc1.pdf")
text = parsed.get("full_text", "")
entities = ner.extract_entities(text)
relationships = rel_extractor.extract_relations(text, entities=entities)
kg = builder.build_graph(entities=entities, relationships=relationships)
embeddings = embedder.embed_batch([e.text for e in entities])
```

**Pattern 2: Using VeritasReason Class (Orchestration)**
```python
from veritasreason.core import VeritasReason

# Use VeritasReason class for orchestration of complex workflows
# For orchestration, use VeritasReason class
from veritasreason.core import VeritasReason
framework = VeritasReason()
framework.initialize()
framework.initialize()
result = framework.build_knowledge_base(["doc1.pdf", "doc2.docx"], embeddings=True, graph=True)
framework.shutdown()
```

!!! tip "Which Pattern to Use?"
    - **Use Individual Modules** (Pattern 1) for most use cases - gives you full control and transparency
    - **Use VeritasReason Class** (Pattern 2) for complex workflows that need lifecycle management and orchestration

### 1. Basic Document Processing
```python
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder
from veritasreason.embeddings import TextEmbedder

# Use individual modules
documents = ["document1.pdf", "document2.docx", "document3.txt"]
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()
rel_extractor = RelationExtractor()
builder = GraphBuilder(merge_entities=True)
embedder = TextEmbedder()

# Process each document
all_entities = []
all_relationships = []
for doc_path in documents:
    doc = ingestor.ingest_file(doc_path)
    parsed = parser.parse_document(doc_path)
    text = parsed.get("full_text", "")
    entities = ner.extract_entities(text)
    relationships = rel_extractor.extract_relations(text, entities=entities)
    all_entities.extend(entities)
    all_relationships.extend(relationships)

# Build knowledge graph and generate embeddings
kg = builder.build_graph(entities=all_entities, relationships=all_relationships)
embeddings = embedder.embed_batch([e.text for e in all_entities])

# Access results
knowledge_graph = result["knowledge_graph"]
embeddings = result["embeddings"]
statistics = result["statistics"]

print(f"Processed {statistics['sources_processed']} documents")
print(f"Success rate: {statistics['success_rate']:.2%}")

# Visualize the knowledge graph
from veritasreason.visualization import KGVisualizer

kg_viz = KGVisualizer(layout="force", color_scheme="vibrant")
fig = kg_viz.visualize_network(knowledge_graph, output="interactive")
fig.show()  # Display interactive visualization

# Or save to HTML file
kg_viz.visualize_network(knowledge_graph, output="html", file_path="knowledge_graph.html")
```

### 2. Web Content Processing
```python
from veritasreason.core import VeritasReason
from veritasreason.ingest import WebIngestor

# Ingest web content
web_ingestor = WebIngestor(
    config={
        "delay": 1.0,  # Rate limiting delay
        "respect_robots": True,
        "timeout": 30
    }
)

# Ingest single URL
url = "https://example.com/article"
web_content = web_ingestor.ingest_url(url)

# Or crawl sitemap
sitemap_url = "https://example.com/sitemap.xml"
pages = web_ingestor.crawl_sitemap(sitemap_url)

# Build knowledge base from web content
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder

parser = DocumentParser()
ner = NERExtractor()
rel_extractor = RelationExtractor()
builder = GraphBuilder()

all_entities = []
all_relationships = []
for web_content in pages:
    parsed = parser.parse_document(web_content.url)
    text = parsed.get("full_text", "")
    entities = ner.extract_entities(text)
    relationships = rel_extractor.extract_relations(text, entities=entities)
    all_entities.extend(entities)
    all_relationships.extend(relationships)

kg = builder.build_graph(entities=all_entities, relationships=all_relationships)
```

### 3. Knowledge Graph Analytics
```python
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder, GraphAnalyzer, CentralityCalculator, CommunityDetector

# Build knowledge graph using individual modules
sources = ["document1.pdf", "document2.pdf"]
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()
rel_extractor = RelationExtractor()
builder = GraphBuilder(merge_entities=True, entity_resolution_strategy="fuzzy")

# Process documents
all_entities = []
all_relationships = []
for source in sources:
    doc = ingestor.ingest_file(source)
    parsed = parser.parse_document(source)
    text = parsed.get("full_text", "")
    entities = ner.extract_entities(text)
    relationships = rel_extractor.extract_relations(text, entities=entities)
    all_entities.extend(entities)
    all_relationships.extend(relationships)

kg = builder.build_graph(entities=all_entities, relationships=all_relationships)

# Build graph object from extracted entities and relationships
graph_builder = GraphBuilder(
    merge_entities=True,
    entity_resolution_strategy="fuzzy",
    resolve_conflicts=True
)

# Prepare sources with entities and relationships
graph_sources = []
for source_result in kg_data.get("results", []):
    graph_sources.append({
        "entities": source_result.get("entities", []),
        "relationships": source_result.get("relationships", [])
    })

graph = graph_builder.build(graph_sources)

# Analyze graph properties
analyzer = GraphAnalyzer()

# Calculate centrality using GraphAnalyzer
centrality = analyzer.calculate_centrality(graph, centrality_type="degree")

# Or use CentralityCalculator directly
centrality_calc = CentralityCalculator()
centrality = centrality_calc.calculate_all_centrality(
    graph,
    centrality_types=["degree", "betweenness", "closeness"]
)

# Detect communities
community_detector = CommunityDetector()
communities = community_detector.detect_communities(graph, algorithm="louvain")

# Analyze connectivity
connectivity = analyzer.analyze_connectivity(graph)

# Or use ConnectivityAnalyzer directly
from veritasreason.kg import ConnectivityAnalyzer
connectivity_analyzer = ConnectivityAnalyzer()
connectivity = connectivity_analyzer.analyze_connectivity(graph)

print(f"Found {len(communities)} communities")
print(f"Graph connectivity: {connectivity['is_connected']}")
```

## 🏗️ Architecture

### Core Modules
- **Core**: Framework orchestration and configuration
- **Ingest**: Data ingestion from various sources
- **Parse**: Content parsing and extraction
- **Normalize**: Data normalization and cleaning
- **Semantic Extract**: Entity and relationship extraction
- **Ontology**: Ontology management and generation
- **Knowledge Graph**: Graph construction and management
- **Embeddings**: Vector embedding generation
- **Vector Store**: Vector storage and retrieval
- **Pipeline**: Processing pipeline orchestration
- **Streaming**: Real-time stream processing
- **Security**: Access control and data protection
- **Quality**: Quality assurance and validation
- **Export**: Data export and reporting

### Supported Data Sources
- **Documents**: PDF, DOCX, HTML, TXT, XML, JSON, CSV
- **Web Content**: Websites, RSS feeds, APIs
- **Databases**: SQL, NoSQL, Graph databases
- **Streams**: Kafka, Pulsar, RabbitMQ, Kinesis
- **Cloud Storage**: S3, GCS, Azure Blob
- **Repositories**: Git repositories, code analysis

## 📚 Documentation

### Comprehensive Guides
- [Getting Started](https://docs.veritasreason.dev/getting-started)
- [API Reference](https://docs.veritasreason.dev/api-reference)
- [Cookbook Examples](https://docs.veritasreason.dev/cookbook)
- [Configuration Guide](https://docs.veritasreason.dev/configuration)
- [Deployment Guide](https://docs.veritasreason.dev/deployment)

### Tutorials
- [Document Processing Tutorial](https://docs.veritasreason.dev/tutorials/document-processing)
- [Knowledge Graph Tutorial](https://docs.veritasreason.dev/tutorials/knowledge-graph)
- [Web Scraping Tutorial](https://docs.veritasreason.dev/tutorials/web-scraping)
- [Multi-Modal Processing Tutorial](https://docs.veritasreason.dev/tutorials/multi-modal)

## 🎨 Detailed Code Examples

### 1. Data Ingestion Examples

#### File Ingestion

**Option 1: Using module-level build function (Recommended)**
```python
from veritasreason.ingest import FileIngestor

# Initialize file ingestor
ingestor = FileIngestor()

# Ingest directory recursively
files = ingestor.ingest_directory(
    "documents/",
    recursive=True,
    file_types=[".pdf", ".docx", ".txt"]
)

for file_obj in files:
    print(f"File: {file_obj.path}")
    print(f"Type: {file_obj.file_type}")
    print(f"Size: {file_obj.size} bytes")
```

**Option 2: Using FileIngestor for single files**
```python
from veritasreason.ingest import FileIngestor
from pathlib import Path

# Initialize file ingestor
file_ingestor = FileIngestor()

# Ingest single file
file_obj = file_ingestor.ingest_file("document.pdf")

# Ingest entire directory
files = file_ingestor.ingest_directory(
    "documents/",
    recursive=True,
    extensions=[".pdf", ".docx", ".txt"]
)

# Process file objects
for file_obj in files:
    print(f"File: {file_obj.path}")
    print(f"Type: {file_obj.file_type}")
    print(f"Size: {file_obj.size} bytes")
```

#### Web Content Ingestion
```python
from veritasreason.ingest import WebIngestor, FeedIngestor

# Web ingestion
web_ingestor = WebIngestor(
    config={
        "delay": 1.0,
        "respect_robots": True,
        "user_agent": "MyBot/1.0"
    }
)

# Ingest single URL
content = web_ingestor.ingest_url("https://example.com/article")
print(f"Title: {content.title}")
print(f"Text: {content.text[:200]}...")

# Crawl sitemap
pages = web_ingestor.crawl_sitemap("https://example.com/sitemap.xml")
print(f"Found {len(pages)} pages")

# RSS/Atom feed ingestion
feed_ingestor = FeedIngestor()
feed_data = feed_ingestor.ingest_feed("https://example.com/feed.xml")

for item in feed_data.items:
    print(f"Title: {item.title}")
    print(f"Published: {item.published}")
```

#### Stream Ingestion
```python
from veritasreason.ingest import StreamIngestor, KafkaProcessor, RabbitMQProcessor

# Initialize stream ingestor
stream_ingestor = StreamIngestor()

# Ingest from Kafka
kafka_processor = stream_ingestor.ingest_kafka(
    topic="documents",
    bootstrap_servers=["localhost:9092"],
    consumer_config={"group_id": "veritasreason_processor"}
)

# Or ingest from RabbitMQ
rabbitmq_processor = stream_ingestor.ingest_rabbitmq(
    queue="documents",
    connection_url="amqp://user:pass@localhost:5672/"
)

# Or create processors directly
kafka_processor = KafkaProcessor(
    topic="documents",
    bootstrap_servers=["localhost:9092"],
    consumer_config={"group_id": "veritasreason_processor"}
)

# Process messages with callback
def process_message(message):
    result = kafka_processor.process_message(message)
    print(f"Received: {result['content']}")
    # Process message content...

# Set message handler
kafka_processor.message_handler = process_message

# Start streaming
stream_ingestor.start_streaming([kafka_processor])

# Or start individual processor
kafka_processor.start_consuming()
```

#### Database Ingestion
```python
from veritasreason.ingest import DBIngestor

# Initialize database ingestor
db_ingestor = DBIngestor(
    config={
        "batch_size": 1000
    }
)

# Export from specific table
connection_string = "postgresql://user:pass@localhost/db"
table_data = db_ingestor.export_table(
    connection_string,
    "articles",
    limit=1000
)

# Or ingest entire database
database_data = db_ingestor.ingest_database(
    connection_string,
    include_tables=["articles", "authors"],
    max_rows_per_table=10000
)

# Access table data
for row in table_data.rows:
    print(f"ID: {row['id']}, Title: {row['title']}")

# Or execute custom query
results = db_ingestor.execute_query(
    connection_string,
    "SELECT * FROM articles WHERE published_at > :date",
    date="2023-01-01"
)
```

### 2. Semantic Extraction Examples

#### Entity Extraction

**Option 1: Using module-level build function (Recommended)**
```python
from veritasreason.semantic_extract import NamedEntityRecognizer

text = "Apple Inc. is a technology company founded by Steve Jobs in Cupertino, California."

# Extract entities using NamedEntityRecognizer
ner = NamedEntityRecognizer()
entities = ner.extract_entities(text)

for entity in entities:
    print(f"Entity: {entity.get('text')}")
    print(f"Type: {entity.get('type')}")
    print(f"Confidence: {entity.get('confidence')}")
    print()
```

**Option 2: Using NERExtractor for more control**
```python
from veritasreason.semantic_extract import NERExtractor, NamedEntityRecognizer

# Simple NER extractor
ner_extractor = NERExtractor(
    model="en_core_web_sm",
    min_confidence=0.5
)

text = "Apple Inc. is a technology company founded by Steve Jobs in Cupertino, California."

# Extract entities
entities = ner_extractor.extract_entities(text)

for entity in entities:
    print(f"Entity: {entity.text}")
    print(f"Type: {entity.entity_type}")
    print(f"Confidence: {entity.confidence}")
    print(f"Position: {entity.start_char}-{entity.end_char}")
    print()

# Advanced entity recognizer
entity_recognizer = NamedEntityRecognizer(
    config={
        "ner": {"model": "en_core_web_lg"},
        "classifier": {"enable": True}
    }
)

# Extract and classify entities
entities = entity_recognizer.extract_entities(text)
classified = entity_recognizer.classify_entities(entities)

# Group entities by type
for entity_type, entity_list in classified.items():
    print(f"{entity_type}: {len(entity_list)} entities")
```

#### Relationship Extraction
```python
from veritasreason.semantic_extract import RelationExtractor, NERExtractor

# Initialize extractors
ner_extractor = NERExtractor()
relation_extractor = RelationExtractor()

text = "Tim Cook is the CEO of Apple Inc. Apple was founded by Steve Jobs."

# Extract entities first
entities = ner_extractor.extract_entities(text)

# Extract relationships
relations = relation_extractor.extract_relations(text, entities)

for relation in relations:
    print(f"Subject: {relation.subject}")
    print(f"Predicate: {relation.predicate}")
    print(f"Object: {relation.object}")
    print(f"Confidence: {relation.confidence}")
    print()
```

#### Triplet Extraction
```python
from veritasreason.semantic_extract import TripletExtractor

# Initialize triplet extractor
triplet_extractor = TripletExtractor(
    config={
        "validator": {"strict": True},
        "serializer": {"format": "turtle"}
    }
)

text = "Barack Obama was the President of the United States from 2009 to 2017."

# Extract RDF triples
triplets = triplet_extractor.extract_triples(text)

for triplet in triples:
    print(f"Subject: {triplet.subject}")
    print(f"Predicate: {triplet.predicate}")
    print(f"Object: {triplet.object}")
    print(f"Confidence: {triplet.confidence}")
    print()
```

#### Event Detection
```python
from veritasreason.semantic_extract import EventDetector

# Initialize event detector
event_detector = EventDetector(
    config={
        "classifier": {"enable": True},
        "temporal": {"enable": True}
    }
)

text = "The company announced the merger on January 15, 2023. The deal was finalized in March."

# Detect events
events = event_detector.detect_events(text)

for event in events:
    print(f"Event: {event.text}")
    print(f"Type: {event.event_type}")
    print(f"Time: {event.time}")
    print(f"Participants: {event.participants}")
    print()
```

### 3. Embeddings Generation Examples

#### Text Embeddings

**Option 1: Using module-level build function (Recommended)**
```python
import numpy as np

# Generate embeddings using EmbeddingGenerator
from veritasreason.embeddings import EmbeddingGenerator

texts = [
    "First document text.",
    "Second document text.",
    "Third document text."
]

generator = EmbeddingGenerator()
embeddings = [generator.generate_embeddings(t, data_type="text") for t in texts]
print(f"Generated {len(embeddings)} embeddings")
```

**Option 2: Using TextEmbedder for more control**
```python
import numpy as np
from veritasreason.embeddings import TextEmbedder, EmbeddingGenerator

# Simple text embedder
text_embedder = TextEmbedder(
    model_name="all-MiniLM-L6-v2",
    device="cpu",
    normalize=True
)

# Embed single text
text = "This is a sample text for embedding."
embedding = text_embedder.embed_text(text)
print(f"Embedding shape: {embedding.shape}")
print(f"Embedding norm: {np.linalg.norm(embedding)}")

# Embed batch of texts
texts = [
    "First document text.",
    "Second document text.",
    "Third document text."
]
embeddings = text_embedder.embed_batch(texts)
print(f"Batch embeddings shape: {embeddings.shape}")

# Advanced embedding generator
embedding_generator = EmbeddingGenerator(
    config={
        "text": {"model_name": "sentence-transformers/all-mpnet-base-v2"},
        "image": {"model_name": "clip-vit-base-patch32"},
        "audio": {"model_name": "wav2vec2-base"}
    }
)

# Generate embeddings for different data types
text_embedding = embedding_generator.generate_embeddings(
    "Sample text",
    data_type="text"
)

image_embedding = embedding_generator.generate_embeddings(
    "image.jpg",
    data_type="image"
)
```

#### Multi-Modal Embeddings
```python
from veritasreason.embeddings import MultimodalEmbedder

# Initialize multimodal embedder
multimodal_embedder = MultimodalEmbedder(
    config={
        "text_model": "sentence-transformers/all-mpnet-base-v2",
        "image_model": "openai/clip-vit-base-patch32"
    }
)

# Embed text and image together
text = "A red apple on a white table"
image_path = "apple.jpg"

# Joint embedding
joint_embedding = multimodal_embedder.embed_multimodal(
    text=text,
    image=image_path
)

# Calculate similarity
similarity = multimodal_embedder.calculate_similarity(
    text=text,
    image=image_path
)
print(f"Text-Image similarity: {similarity}")
```

### 4. Knowledge Graph Building Examples

#### Building Knowledge Graph

**Option 1: Using GraphBuilder (Recommended)**
```python
from veritasreason.kg import GraphBuilder

# Build knowledge graph from entity/relationship data
builder = GraphBuilder(
    merge_entities=True,
    entity_resolution_strategy="fuzzy",
    resolve_conflicts=True,
    enable_temporal=True
)

# Prepare sources with entities and relationships
sources = [{
    "entities": [...],  # Your extracted entities
    "relationships": [...]  # Your extracted relationships
}]

graph = builder.build(sources)
print(f"Total entities: {len(graph.get('entities', []))}")
print(f"Total relationships: {len(graph.get('relationships', []))}")
```

**Option 2: Using GraphBuilder with full control**
```python
from veritasreason.kg import GraphBuilder, EntityResolver
from veritasreason.semantic_extract import NERExtractor, RelationExtractor

# Initialize components
graph_builder = GraphBuilder(
    merge_entities=True,
    entity_resolution_strategy="fuzzy",
    resolve_conflicts=True,
    enable_temporal=True,
    temporal_granularity="day"
)

entity_resolver = EntityResolver(
    similarity_threshold=0.8,
    strategy="fuzzy"
)

# Extract entities and relationships from multiple sources
ner_extractor = NERExtractor()
relation_extractor = RelationExtractor()

sources = []
for doc in documents:
    entities = ner_extractor.extract_entities(doc["text"])
    relations = relation_extractor.extract_relations(doc["text"], entities)
    sources.append({
        "entities": entities,
        "relationships": relations,
        "metadata": {"source": doc["path"]}
    })

# Build knowledge graph
graph = graph_builder.build(
    sources,
    entity_resolver=entity_resolver
)

# Access graph data
print(f"Total entities: {len(graph.entities)}")
print(f"Total relationships: {len(graph.relationships)}")
```

#### Temporal Knowledge Graph
```python
from veritasreason.kg import GraphBuilder, TemporalGraphQuery

# Build temporal knowledge graph
temporal_graph_builder = GraphBuilder(
    enable_temporal=True,
    track_history=True,
    version_snapshots=True
)

# Build graph with temporal information
graph = temporal_graph_builder.build(sources)

# Query temporal information
temporal_query = TemporalGraphQuery(graph)

# Query graph at specific time
snapshot = temporal_query.query_at_time(
    "2023-01-15",
    include_entities=True,
    include_relationships=True
)

# Detect temporal patterns
from veritasreason.kg import TemporalPatternDetector
pattern_detector = TemporalPatternDetector()
patterns = pattern_detector.detect_patterns(graph)

for pattern in patterns:
    print(f"Pattern: {pattern.pattern_type}")
    print(f"Entities: {pattern.entities}")
    print(f"Time span: {pattern.start_time} - {pattern.end_time}")
```

### 5. Pipeline Building Examples

#### Custom Pipeline
```python
from veritasreason.pipeline import PipelineBuilder
from veritasreason.pipeline import ExecutionEngine

# Build custom pipeline
pipeline_builder = PipelineBuilder()

pipeline = (
    pipeline_builder
    .add_step("ingest", "ingest", config={"source": "documents/"})
    .add_step("parse", "parse", config={"formats": ["pdf", "docx"]}, dependencies=["ingest"])
    .add_step("normalize", "normalize", config={}, dependencies=["parse"])
    .add_step("extract", "extract", config={"entities": True, "relations": True}, dependencies=["normalize"])
    .add_step("embed", "embed", config={"model": "text-embedding-3-large"}, dependencies=["extract"])
    .add_step("build_kg", "build_kg", config={}, dependencies=["extract", "embed"])
    .set_parallelism(4)
    .build("document_processing_pipeline")
)

# Execute pipeline
execution_engine = ExecutionEngine()
result = execution_engine.execute_pipeline(pipeline, data="documents/")

print(f"Pipeline executed: {result.success}")
print(f"Execution time: {result.execution_time:.2f}s")
print(f"Steps completed: {result.steps_completed if hasattr(result, 'steps_completed') else 'N/A'}")
```

#### Using Pipeline Templates
```python
from veritasreason.pipeline import PipelineTemplateManager, PipelineBuilder, ExecutionEngine

# Initialize template manager
template_manager = PipelineTemplateManager()

# Get pre-built template
pipeline_template = template_manager.get_template("document_processing")

# Build pipeline from template
pipeline_builder = PipelineBuilder()
# Note: You would need to implement from_template method or manually build from template
custom_pipeline = pipeline_builder.build("custom_document_pipeline")

# Execute
execution_engine = ExecutionEngine()
result = execution_engine.execute_pipeline(custom_pipeline)
```

### 6. Quality Assurance Examples

Note: The `veritasreason.kg_qa` module is temporarily unavailable and will be reintroduced in a future release.

### 7. Export Examples

#### Export Knowledge Graph
```python
from veritasreason.export import JSONExporter, RDFExporter, GraphExporter, CSVExporter

# Export to JSON
json_exporter = JSONExporter()
json_exporter.export(graph, "knowledge_graph.json")

# Or export knowledge graph specifically
json_exporter.export_knowledge_graph(graph, "knowledge_graph.json")

# Export entities and relationships separately
json_exporter.export_entities(graph.entities, "entities.json")
json_exporter.export_relationships(graph.relationships, "relationships.json")

# Export to RDF
rdf_exporter = RDFExporter()
rdf_exporter.export(graph, "knowledge_graph.ttl", format="turtle")

# Or export to RDF directly
rdf_content = rdf_exporter.export_to_rdf(graph, format="turtle")

# Export to graph formats (GraphML, GEXF, DOT)
graph_exporter = GraphExporter(format="graphml")
graph_exporter.export_knowledge_graph(graph, "knowledge_graph.graphml")

# Export to CSV
csv_exporter = CSVExporter()
csv_exporter.export_entities(graph.entities, "entities.csv")
csv_exporter.export_relationships(graph.relationships, "relationships.csv")

# Or export entire knowledge graph to CSV
csv_exporter.export_knowledge_graph(graph, "knowledge_graph.csv")
```

### 8. Complete End-to-End Example

```python
from veritasreason.ingest import FileIngestor
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.embeddings import EmbeddingGenerator
from veritasreason.kg import GraphBuilder
from veritasreason.export import JSONExporter

# No explicit initialization needed - framework auto-initializes on first use

# Step 1: Ingest documents
file_ingestor = FileIngestor()
files = file_ingestor.ingest_directory("documents/", recursive=True)

# Step 2: Extract entities and relationships
ner_extractor = NERExtractor(model="en_core_web_lg")
relation_extractor = RelationExtractor()

all_entities = []
all_relationships = []

for file_obj in files:
    # Parse file (assuming parsed text available)
    text = file_obj.content.decode("utf-8") if file_obj.content else ""
    
    # Extract entities
    entities = ner_extractor.extract_entities(text)
    all_entities.extend(entities)
    
    # Extract relationships
    relations = relation_extractor.extract_relations(text, entities)
    all_relationships.extend(relations)

# Step 3: Generate embeddings
embedding_generator = EmbeddingGenerator()
embeddings = embedding_generator.generate_embeddings(
    [e.text for e in all_entities],
    data_type="text"
)

# Step 4: Build knowledge graph
graph_builder = GraphBuilder(
    merge_entities=True,
    resolve_conflicts=True
)

graph = graph_builder.build({
    "entities": all_entities,
    "relationships": all_relationships
})

# Step 5: (Optional) Quality assessment is temporarily unavailable
# The `veritasreason.kg_qa` module will be reintroduced in a future release.

# Step 6: Export results
json_exporter = JSONExporter()
json_exporter.export(graph, "final_knowledge_graph.json")

print("Processing complete!")
print(f"Total entities: {len(graph.entities)}")
print(f"Total relationships: {len(graph.relationships)}")
```

### 9. Visualization Examples

The VeritasReason visualization module provides comprehensive visualization capabilities for all knowledge artifacts. All visualizers support both interactive (Plotly) and static export formats (HTML, PNG, SVG, PDF).

#### Knowledge Graph Visualization
```python
from veritasreason.visualization import KGVisualizer

# Initialize KG visualizer
kg_viz = KGVisualizer(layout="force", color_scheme="vibrant")

# Visualize network graph
graph = {
    "entities": all_entities,
    "relationships": all_relationships
}

# Interactive network visualization
fig = kg_viz.visualize_network(graph, output="interactive")
fig.show()

# Save to HTML
kg_viz.visualize_network(graph, output="html", file_path="kg_network.html")

# Visualize with community coloring
from veritasreason.kg import CommunityDetector
community_detector = CommunityDetector()
communities = community_detector.detect_communities(graph, algorithm="louvain")
kg_viz.visualize_communities(graph, communities, output="html", file_path="kg_communities.html")

# Visualize with centrality
from veritasreason.kg import CentralityCalculator
centrality_calc = CentralityCalculator()
centrality = centrality_calc.calculate_all_centrality(graph, centrality_types=["degree"])
kg_viz.visualize_centrality(graph, centrality, centrality_type="degree", 
                           output="html", file_path="kg_centrality.html")

# Entity type distribution
kg_viz.visualize_entity_types(graph, output="html", file_path="entity_types.html")

# Relationship matrix
kg_viz.visualize_relationship_matrix(graph, output="html", file_path="relationship_matrix.html")
```

#### Ontology Visualization
```python
from veritasreason.visualization import OntologyVisualizer
from veritasreason.ontology import OntologyGenerator

# Initialize ontology visualizer
onto_viz = OntologyVisualizer(color_scheme="default")

# Option 1: Visualize from ontology generator result
ontology_generator = OntologyGenerator()
semantic_model = ontology_generator.generate_ontology(data)

# Visualize semantic model (handles both ontology and semantic network)
onto_viz.visualize_semantic_model(semantic_model, output="html", file_path="semantic_model.html")

# Option 2: Visualize class hierarchy directly
ontology = {
    "classes": classes,
    "properties": properties
}

# Hierarchy tree visualization
onto_viz.visualize_hierarchy(ontology, output="html", file_path="ontology_hierarchy.html")

# Option 3: Visualize from semantic network (auto-extracts classes)
from veritasreason.semantic_extract import SemanticNetworkExtractor
extractor = SemanticNetworkExtractor()
semantic_network = extractor.extract_network(text)

# Can visualize directly - will extract classes automatically
onto_viz.visualize_hierarchy({"semantic_network": semantic_network}, 
                             output="html", file_path="ontology_from_network.html")

# Property graph visualization
onto_viz.visualize_properties(ontology, output="html", file_path="ontology_properties.html")

# Ontology structure network
onto_viz.visualize_structure(ontology, output="html", file_path="ontology_structure.html")

# Class-property matrix
onto_viz.visualize_class_property_matrix(ontology, output="html", file_path="class_property_matrix.html")

# Ontology metrics dashboard
onto_viz.visualize_metrics(ontology, output="html", file_path="ontology_metrics.html")
```

#### Embedding Visualization
```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

# Initialize embedding visualizer
emb_viz = EmbeddingVisualizer(point_size=8)

# 2D projection using UMAP
embeddings = np.array([...])  # Your embeddings array
fig = emb_viz.visualize_2d_projection(
    embeddings,
    labels=["Entity 1", "Entity 2", ...],
    method="umap",
    output="interactive"
)
fig.show()

# 3D projection
emb_viz.visualize_3d_projection(embeddings, method="pca", 
                                output="html", file_path="embeddings_3d.html")

# Similarity heatmap
emb_viz.visualize_similarity_heatmap(embeddings, 
                                     output="html", file_path="similarity_heatmap.html")

# Clustering visualization
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=5)
cluster_labels = kmeans.fit_predict(embeddings)
emb_viz.visualize_clustering(embeddings, cluster_labels, method="umap",
                             output="html", file_path="embedding_clusters.html")

# Multi-modal comparison
text_embeddings = np.array([...])
image_embeddings = np.array([...])
emb_viz.visualize_multimodal_comparison(
    text_embeddings=text_embeddings,
    image_embeddings=image_embeddings,
    output="html",
    file_path="multimodal_comparison.html"
)

# Quality metrics
# emb_viz.visualize_quality_metrics(embeddings, output="html", file_path="embedding_quality.html")
```

#### Semantic Network Visualization
```python
from veritasreason.visualization import SemanticNetworkVisualizer

# Initialize semantic network visualizer
sem_net_viz = SemanticNetworkVisualizer()

# Option 1: Visualize SemanticNetwork dataclass object
from veritasreason.semantic_extract import SemanticNetworkExtractor
extractor = SemanticNetworkExtractor()
semantic_network = extractor.extract_network(text)

# Network graph
sem_net_viz.visualize_network(semantic_network, output="html", file_path="semantic_network.html")

# Option 2: Visualize from dictionary format
semantic_network_dict = {
    "nodes": [{"id": "n1", "label": "Node 1", "type": "Entity"}],
    "edges": [{"source": "n1", "target": "n2", "label": "relatedTo"}]
}
sem_net_viz.visualize_network(semantic_network_dict, output="html", file_path="semantic_network.html")

# Option 3: Visualize from semantic model (ontology generator result)
from veritasreason.ontology import OntologyGenerator
generator = OntologyGenerator()
semantic_model = generator.generate_ontology(data)
sem_net_viz.visualize_network(semantic_model.semantic_network, output="html", file_path="semantic_model_network.html")

# Node type distribution
sem_net_viz.visualize_node_types(semantic_network, output="html", file_path="node_types.html")

# Edge type distribution
sem_net_viz.visualize_edge_types(semantic_network, output="html", file_path="edge_types.html")
```



#### Graph Analytics Visualization
```python
from veritasreason.visualization import AnalyticsVisualizer

# Initialize analytics visualizer
analytics_viz = AnalyticsVisualizer()

# Centrality rankings
from veritasreason.kg import CentralityCalculator
centrality_calc = CentralityCalculator()
centrality = centrality_calc.calculate_all_centrality(graph, centrality_types=["degree", "betweenness"])

analytics_viz.visualize_centrality_rankings(centrality, centrality_type="degree", top_n=20,
                                           output="html", file_path="centrality_rankings.html")

# Community structure
from veritasreason.kg import CommunityDetector
community_detector = CommunityDetector()
communities = community_detector.detect_communities(graph)
analytics_viz.visualize_community_structure(graph, communities, 
                                           output="html", file_path="communities.html")

# Connectivity analysis
from veritasreason.kg import ConnectivityAnalyzer
connectivity_analyzer = ConnectivityAnalyzer()
connectivity = connectivity_analyzer.analyze_connectivity(graph)
analytics_viz.visualize_connectivity(connectivity, output="html", file_path="connectivity.html")

# Degree distribution
analytics_viz.visualize_degree_distribution(graph, output="html", file_path="degree_distribution.html")

# Metrics dashboard
from veritasreason.kg import GraphAnalyzer
analyzer = GraphAnalyzer()
metrics = analyzer.compute_metrics(graph)
analytics_viz.visualize_metrics_dashboard(metrics, output="html", file_path="metrics_dashboard.html")

# Centrality comparison
degree_centrality = centrality_calc.calculate_degree_centrality(graph)
betweenness_centrality = centrality_calc.calculate_betweenness_centrality(graph)
centrality_results = {
    "degree": degree_centrality,
    "betweenness": betweenness_centrality
}
analytics_viz.visualize_centrality_comparison(centrality_results, top_n=10,
                                             output="html", file_path="centrality_comparison.html")
```

#### Temporal Graph Visualization
```python
from veritasreason.visualization import TemporalVisualizer

# Initialize temporal visualizer
temporal_viz = TemporalVisualizer()

# Timeline visualization
temporal_data = {
    "events": [
        {"timestamp": "2023-01-15", "type": "entity_added", "entity": "Entity1"},
        {"timestamp": "2023-02-20", "type": "relationship_added", "entity": "Entity2"},
    ]
}
temporal_viz.visualize_timeline(temporal_data, output="html", file_path="timeline.html")

# Temporal patterns
from veritasreason.kg import TemporalPatternDetector
pattern_detector = TemporalPatternDetector()
patterns = pattern_detector.detect_patterns(temporal_graph)
temporal_viz.visualize_temporal_patterns(patterns, output="html", file_path="temporal_patterns.html")

# Snapshot comparison
from veritasreason.kg import TemporalVersionManager
version_manager = TemporalVersionManager()
snapshots = {
    "2023-01-01": version_manager.get_snapshot("2023-01-01"),
    "2023-06-01": version_manager.get_snapshot("2023-06-01"),
    "2023-12-01": version_manager.get_snapshot("2023-12-01")
}
temporal_viz.visualize_snapshot_comparison(snapshots, output="html", file_path="snapshot_comparison.html")

# Version history
version_history = [
    {"version": "v1.0", "date": "2023-01-01", "changes": "Initial version"},
    {"version": "v1.1", "date": "2023-06-01", "changes": "Added new classes"},
    {"version": "v2.0", "date": "2023-12-01", "changes": "Major refactoring"}
]
temporal_viz.visualize_version_history(version_history, output="html", file_path="version_history.html")

# Metrics evolution
metrics_history = {
    "num_entities": [100, 150, 200, 250],
    "num_relationships": [200, 300, 400, 500],
    "density": [0.1, 0.12, 0.15, 0.18]
}
timestamps = ["2023-01-01", "2023-06-01", "2023-09-01", "2023-12-01"]
temporal_viz.visualize_metrics_evolution(metrics_history, timestamps, 
                                        output="html", file_path="metrics_evolution.html")
```

#### Quick Visualization Example

```python
from veritasreason.ingest import FileIngestor
from veritasreason.parse import DocumentParser
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder
from veritasreason.embeddings import TextEmbedder
from veritasreason.visualization import KGVisualizer, EmbeddingVisualizer
import numpy as np

# Build knowledge graph using individual modules
ingestor = FileIngestor()
parser = DocumentParser()
ner = NERExtractor()
rel_extractor = RelationExtractor()
builder = GraphBuilder()
embedder = TextEmbedder()

doc = ingestor.ingest_file("document.pdf")
parsed = parser.parse_document("document.pdf")
text = parsed.get("full_text", "")
entities = ner.extract_entities(text)
relationships = rel_extractor.extract_relations(text, entities=entities)
kg = builder.build_graph(entities=entities, relationships=relationships)
embeddings = embedder.embed_batch([e.text for e in entities])

# Visualize knowledge graph
kg_viz = KGVisualizer(layout="force", color_scheme="vibrant")
kg_viz.visualize_network(
    result["knowledge_graph"], 
    output="html", 
    file_path="kg_visualization.html"
)

# Visualize embeddings
if "embeddings" in result:
    emb_viz = EmbeddingVisualizer()
    embeddings_array = np.array([e["embedding"] for e in result["embeddings"]])
    emb_viz.visualize_2d_projection(
        embeddings_array,
        method="umap",
        output="html",
        file_path="embeddings_2d.html"
    )
```

## 🔧 Configuration

### Basic Configuration
```python
from veritasreason.semantic_extract import NERExtractor
from veritasreason.kg import GraphBuilder

# Configure modules individually
ner = NERExtractor(
    method="llm",
    provider="openai",
    model="gpt-4",
    confidence_threshold=0.7
)

builder = GraphBuilder(
    merge_entities=True,
    merge_threshold=0.9
)
```

### Advanced Configuration
```python
from veritasreason.core import Config, ConfigManager
from veritasreason.semantic_extract import NERExtractor
from veritasreason.kg import GraphBuilder

# Load configuration from file
config_manager = ConfigManager()
config = config_manager.load_from_file("config.yaml")

# Use configuration with modules
ner = NERExtractor(
    method="llm",
    provider=config.get("llm_provider.name"),
    model=config.get("llm_provider.model"),
    api_key=config.get("llm_provider.api_key")
    },
    "embedding_model": {
        "name": "sentence-transformers",
        "model": "all-MiniLM-L6-v2"
    },
    "vector_store": {
        "backend": "faiss",
        "index_type": "IVF"
    },
    "graph_db": {
        "backend": "neo4j",
        "uri": "bolt://localhost:7687",
        "username": "neo4j",
        "password": "password"
    }
})

# Use advanced configuration with VeritasReason
veritasreason = VeritasReason(config=config)
result = veritasreason.build_knowledge_base(["document.pdf"])
```

## 🚀 Performance

### Benchmarks
- **Processing Speed**: Optimized for high-throughput document processing
- **Memory Usage**: Optimized for large-scale processing
- **Accuracy**: High accuracy entity extraction
- **Scalability**: Horizontal scaling support
- **Latency**: Fast query response times

### Optimization
- **Parallel Processing**: Multi-threaded and multi-process support
- **Caching**: Intelligent caching for improved performance
- **Streaming**: Real-time processing capabilities
- **GPU Support**: CUDA acceleration for deep learning models
- **Cloud Integration**: Native cloud deployment support

## 🔒 Security

### Security Features
- **Access Control**: Role-based access control (RBAC)
- **Data Encryption**: End-to-end encryption support
- **PII Protection**: Automatic PII detection and redaction
- **Audit Logging**: Comprehensive audit trail
- **Compliance**: GDPR, HIPAA, SOC2 compliance support

### Privacy Protection
- **Data Masking**: Automatic sensitive data masking
- **Anonymization**: Data anonymization capabilities
- **Secure Storage**: Encrypted data storage
- **Access Logging**: Detailed access logging and monitoring

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](contributing.md) for details.

### Development Setup
```bash
git clone https://github.com/veritas-reason-dev/veritasreason.git
cd veritasreason
pip install -e ".[dev]"
pre-commit install
```

### Running Tests
```bash
pytest tests/
pytest tests/ -m "not slow"
pytest tests/ -m "integration"
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/Hawksight-AI/veritas-reason/blob/main/LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ by the VeritasReason team
- Powered by state-of-the-art NLP and ML libraries
- Inspired by the open-source community
- Special thanks to all contributors and users

## 📞 Support

- **Documentation**: [https://docs.veritasreason.dev](https://docs.veritasreason.dev)
- **Issues**: [GitHub Issues](https://github.com/veritas-reason-dev/veritas-reason/issues)
- **Discussions**: [GitHub Discussions](https://github.com/veritas-reason-dev/veritas-reason/discussions)
- **Email**: support@veritasreason.dev

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=veritas-reason-dev/veritasreason&type=Date)](https://star-history.com/#veritas-reason-dev/veritasreason&Date)

---

**VeritasReason** - Transform your data into intelligent knowledge. 🚀
