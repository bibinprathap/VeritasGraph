"""
VeritasGraph - Enterprise-Grade Graph RAG Framework
====================================================

Vision-Native RAG with Knowledge Graph Integration for Secure, On-Premise AI.

"Don't Chunk. Graph." - Document-Centric RAG:
- Treats whole pages/sections as single nodes (not arbitrary 500-token chunks)
- Preserves document structure and visual context
- Better for RAG with tables, charts, and rich formatting

Hierarchical Tree Support:
- Combines PageIndex's TOC-based "human-like retrieval"
- With the flexibility of graph-based semantic search
- "The Power of PageIndex's Tree + The Flexibility of a Graph"

Features:
- Vision-based document processing (no OCR needed)
- Tables and charts extraction using multimodal LLMs
- Hierarchical tree structure extraction (TOC-style navigation)
- Parent-Child section relationships in the graph
- Knowledge graph construction from visual content
- Hybrid RAG combining text and visual understanding
- Integration with GraphRAG for enterprise deployments
- Full source attribution for verifiable AI

Installation:
    pip install veritasgraph
    pip install veritasgraph[all]  # with all optional dependencies

Quick Start:
    >>> from veritasgraph import VisionRAGPipeline, VisionRAGConfig, IngestMode
    >>> 
    >>> # "Don't Chunk. Graph." - Document-centric mode (default)
    >>> config = VisionRAGConfig(
    ...     vision_model="llama3.2-vision:11b",
    ...     ingest_mode="document-centric"  # whole pages/sections as nodes
    ... )
    >>> pipeline = VisionRAGPipeline(config)
    >>> doc = pipeline.ingest_pdf("document.pdf")
    >>> 
    >>> # Tree-based navigation (human-like retrieval)
    >>> print(pipeline.get_document_tree())
    >>> section = pipeline.navigate_to_section("Introduction")
    >>> 
    >>> # Graph-based semantic search
    >>> result = pipeline.query("What are the key findings?")

CLI Usage:
    $ veritasgraph --version
    $ veritasgraph info
    $ veritasgraph ingest document.pdf --ingest-mode=document-centric
    $ veritasgraph init my_project

For more information:
    - Documentation: https://bibinprathap.github.io/VeritasGraph/
    - Repository: https://github.com/bibinprathap/VeritasGraph
"""

__version__ = "0.3.0"  # "Don't Chunk. Graph." - Document-centric ingestion mode
__author__ = "Bibin Prathap"
__email__ = "bibinprathap@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/bibinprathap/VeritasGraph"


def __getattr__(name):
    """Lazy import of components to avoid import errors when dependencies not installed"""
    
    _vision_exports = {
        "VisionRAGConfig",
        "VisionModelClient", 
        "PDFProcessor",
        "VisualElementExtractor",
        "VisionKnowledgeGraph",
        "VisionRAGEngine",
        "VisionRAGPipeline",
    }
    
    _model_exports = {
        "VisualElement",
        "DocumentPage",
        "VisionDocument",
        "GraphNode",
        "TreeNode",
        "HierarchicalStructure",
        "SectionType",
        "IngestMode",
    }
    
    _tree_exports = {
        "HierarchicalTreeExtractor",
        "TreeQueryEngine",
    }
    
    if name in _vision_exports:
        from veritasgraph import vision
        return getattr(vision, name)
    
    if name in _model_exports:
        from veritasgraph import models
        return getattr(models, name)
    
    if name in _tree_exports:
        from veritasgraph import tree_extractor
        return getattr(tree_extractor, name)
    
    raise AttributeError(f"module 'veritasgraph' has no attribute '{name}'")

__all__ = [
    # Configuration
    "VisionRAGConfig",
    # Core clients
    "VisionModelClient",
    "PDFProcessor", 
    "VisualElementExtractor",
    "VisionKnowledgeGraph",
    "VisionRAGEngine",
    "VisionRAGPipeline",
    # Data models
    "VisualElement",
    "DocumentPage",
    "VisionDocument",
    "GraphNode",
    # Hierarchical Tree Support (PageIndex-style)
    "TreeNode",
    "HierarchicalStructure",
    "SectionType",
    "HierarchicalTreeExtractor",
    "TreeQueryEngine",
    # "Don't Chunk. Graph." - Ingestion Modes
    "IngestMode",
]
