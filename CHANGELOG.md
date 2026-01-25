# Changelog

All notable changes to VeritasGraph will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-23

### Added

- **Hierarchical Tree Support** - "The Power of PageIndex's Tree + The Flexibility of a Graph"
  - Combines TOC-based "human-like retrieval" with graph-based semantic search
  - `TreeNode` - Represents sections/subsections in the document hierarchy
  - `HierarchicalStructure` - Complete tree structure with parent-child relationships
  - `SectionType` - Enum for section types (chapter, section, subsection, etc.)
  - `HierarchicalTreeExtractor` - Extracts TOC structure from documents using vision models
  - `TreeQueryEngine` - Query engine for tree-based navigation
  
- **New Pipeline Features**:
  - `pipeline.get_document_tree()` - Get ASCII tree view of document structure
  - `pipeline.navigate_to_section(title)` - Navigate to sections by title
  - Automatic TOC detection and extraction during PDF ingestion
  - Section-aware context retrieval (breadcrumb paths in search results)
  
- **Enhanced Knowledge Graph**:
  - Parent-child edges for hierarchical tree relationships
  - Sibling relationships between sections
  - Section nodes linked to pages and elements
  - `get_tree_context()` - Get full tree context for any section
  - `get_section_contents()` - Get all content within a section
  - Tree visualization with hierarchical layout

- **Updated Entity Extraction Prompt**:
  - Now extracts document sections and subsections
  - Creates "contains" relationships between sections and entities

### Changed

- Version bump to 0.2.0
- `VisionRAGPipeline` now extracts hierarchical structure by default
- Export includes tree context in JSON output
- Graph visualization shows tree edges distinctly (purple)

## [0.1.0] - 2026-01-22

### Added

- Initial PyPI release of `veritasgraph` package
- **Vision-Native RAG**: Process PDFs using multimodal LLMs (no OCR needed)
  - `VisionRAGConfig` - Configuration for vision models and processing
  - `VisionRAGPipeline` - End-to-end pipeline for document ingestion and querying
  - `VisionModelClient` - Client for Ollama vision models (LLaVA, Llama 3.2 Vision)
  - `PDFProcessor` - Convert PDFs to images for vision analysis
  - `VisualElementExtractor` - Extract tables, charts, and diagrams from documents
  - `VisionKnowledgeGraph` - Build knowledge graphs from visual content
  - `VisionRAGEngine` - Query engine with visual context
- **Data Models**: Core data structures
  - `VisualElement` - Represents extracted visual elements
  - `DocumentPage` - Single page with visual analysis
  - `VisionDocument` - Complete document with all pages
  - `GraphNode` - Knowledge graph nodes from visual content
- **CLI**: Command-line interface (`veritasgraph` / `vg`)
  - `veritasgraph info` - Show system information and dependencies
  - `veritasgraph init` - Initialize a new project
  - `veritasgraph ingest` - Ingest PDF documents
  - `veritasgraph query` - Query the knowledge graph
  - `veritasgraph serve` - Start the API server (placeholder)
- **Optional Dependencies**:
  - `[graphrag]` - Microsoft GraphRAG integration
  - `[web]` - Gradio UI and visualization
  - `[ingest]` - YouTube and web article ingestion
  - `[dev]` - Development tools (pytest, black, ruff, mypy)
  - `[all]` - All optional dependencies

### Infrastructure

- `pyproject.toml` with hatchling build system
- Type hints support (PEP 561 py.typed marker)
- GitHub Actions for CI and PyPI publishing
- Comprehensive test suite

## Installation

```bash
# Basic installation
pip install veritasgraph

# With all optional features
pip install veritasgraph[all]
```

[Unreleased]: https://github.com/bibinprathap/VeritasGraph/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bibinprathap/VeritasGraph/releases/tag/v0.1.0
