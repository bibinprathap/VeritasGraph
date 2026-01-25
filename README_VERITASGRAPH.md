# VeritasGraph

**Vision-Native RAG system for document analysis using multimodal LLMs**

VeritasGraph is a Python package that provides Vision-Native RAG (Retrieval-Augmented Generation) capabilities for processing PDF documents using multimodal large language models. Unlike traditional OCR-based approaches, VeritasGraph directly analyzes document images, enabling accurate extraction of complex visual elements like tables, charts, and diagrams.

## Features

- 🔮 **Vision-Native Processing**: Analyze PDFs directly with multimodal LLMs (LLaVA, Llama 3.2 Vision) - no OCR required
- 📊 **Accurate Table Extraction**: Extract tables with precise values, preserving formatting and structure
- 📈 **Chart Understanding**: Interpret charts and graphs, extracting data points and insights
- 🔗 **Knowledge Graph**: Build connected knowledge graphs from document content
- 🔍 **Semantic Search**: Query documents using natural language with embedding-based retrieval
- 🤖 **Local-First**: Runs entirely on local models via Ollama - no API costs

## Installation

```bash
pip install veritasgraph
```

### Requirements

- Python 3.10+
- [Ollama](https://ollama.ai/) running locally
- [Poppler](https://poppler.freedesktop.org/) for PDF processing
  - Windows: `choco install poppler`
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`

### Required Ollama Models

```bash
# Vision model (required)
ollama pull llama3.2-vision:11b

# Text model for reasoning
ollama pull qwen3:8b

# Embedding model
ollama pull nomic-embed-text:latest
```

## Quick Start

```python
from veritasgraph import VisionRAGPipeline, VisionRAGConfig

# Configure the pipeline
config = VisionRAGConfig(
    vision_model="llama3.2-vision:11b",
    text_model="qwen3:8b",
    embedding_model="nomic-embed-text:latest",
    ollama_host="http://localhost:11434"
)

# Create pipeline
pipeline = VisionRAGPipeline(config)

# Ingest a PDF document
doc = pipeline.ingest_pdf("path/to/document.pdf")

# Query the document
result = pipeline.query("What are the total revenues for Q4 2024?")
print(result["answer"])

# Visualize the knowledge graph
pipeline.visualize_graph()

# Export extracted data
pipeline.export_to_json("output/extracted_data.json")
```

## Components

### VisionRAGConfig

Configuration class for all pipeline settings:

```python
config = VisionRAGConfig(
    vision_model="llama3.2-vision:11b",      # Multimodal model for image analysis
    text_model="qwen3:8b",            # Text model for reasoning
    embedding_model="nomic-embed-text:latest",  # Embedding model
    ollama_host="http://localhost:11434",
    pdf_dpi=200,                      # PDF conversion quality
    extract_tables=True,              # Extract tables
    extract_charts=True,              # Extract charts
    min_confidence=0.7                # Minimum confidence threshold
)
```

### VisionRAGPipeline

Complete end-to-end pipeline:

```python
pipeline = VisionRAGPipeline(config)

# Ingest documents
doc = pipeline.ingest_pdf("document.pdf")

# Query
result = pipeline.query("Your question here")

# Access components
pipeline.vision_client      # VisionModelClient
pipeline.knowledge_graph    # VisionKnowledgeGraph
pipeline.rag_engine        # VisionRAGEngine
```

### VisionModelClient

Direct interface to vision models:

```python
from veritasgraph import VisionModelClient, VisionRAGConfig
from PIL import Image

client = VisionModelClient(VisionRAGConfig())

# Analyze an image
image = Image.open("page.jpg")
response = client.analyze_image(image, "Describe this table")

# Get JSON response
data = client.analyze_with_json(image, "Extract table as JSON")

# Get embeddings
embedding = client.get_embedding("search query")
```

### VisionKnowledgeGraph

Knowledge graph for document relationships:

```python
# Semantic search
results = pipeline.knowledge_graph.semantic_search("revenue metrics", top_k=5)

# Get context for queries
context = pipeline.knowledge_graph.get_context_for_query("Q4 results")

# Visualize
pipeline.knowledge_graph.visualize()
```

## Example Use Cases

### Financial Document Analysis

```python
# Ingest earnings report
doc = pipeline.ingest_pdf("earnings-q4-2024.pdf")

# Extract specific metrics
result = pipeline.query("What was the net income for Q4 2024?")
result = pipeline.query("Compare revenue growth year-over-year")
result = pipeline.query("What are the key highlights from the CEO's statement?")
```

### Technical Documentation

```python
# Process technical PDF
doc = pipeline.ingest_pdf("api-documentation.pdf")

# Query specific topics
result = pipeline.query("How do I authenticate API requests?")
result = pipeline.query("What are the rate limits?")
```

### Research Papers

```python
# Analyze research paper
doc = pipeline.ingest_pdf("research-paper.pdf")

# Extract findings
result = pipeline.query("What methodology did they use?")
result = pipeline.query("What were the main findings?")
```

## Architecture

```
VisionRAGPipeline
├── VisionModelClient (Ollama interface)
├── PDFProcessor (PDF → Images)
├── VisualElementExtractor (Image analysis)
├── VisionKnowledgeGraph (NetworkX graph)
└── VisionRAGEngine (Query processing)
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.
