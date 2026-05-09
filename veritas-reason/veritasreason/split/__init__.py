"""
Split Module

This module provides comprehensive document chunking and splitting capabilities
for optimal processing and semantic analysis, enabling efficient handling of
large documents through various chunking strategies.

Supported Methods:
    - Standard: recursive, token, sentence, paragraph, character, word, semantic_transformer, llm, huggingface, nltk
    - KG/Ontology: entity_aware, relation_aware, graph_based, ontology_aware, hierarchical, community_detection, centrality_based, subgraph, topic_based

Algorithms Used:
    - Recursive Splitting: Separator hierarchy and greedy splitting
    - Token Counting: BPE tokenization (tiktoken, transformers)
    - Sentence Segmentation: NLTK, spaCy, regex-based
    - Semantic Boundary Detection: Sentence transformer embeddings and similarity
    - LLM-based Splitting: Prompt engineering for optimal split point detection
    - Entity Boundary Detection: NER-based entity extraction and boundary preservation
    - Triplet Preservation: Graph-based triplet integrity checking
    - Graph Centrality Analysis: Degree, betweenness, closeness, eigenvector centrality
    - Community Detection: Louvain algorithm, Leiden algorithm, modularity optimization

Key Features:
    - Multiple standard splitting methods
    - KG/ontology/graph analytics-specific chunking methods
    - Unified TextSplitter interface
    - Entity-aware chunking for GraphRAG
    - Relation-aware chunking for KG workflows
    - Graph structure-based chunking
    - Ontology concept-aware chunking
    - Hierarchical multi-level chunking
    - Semantic-based chunking using NLP
    - Structure-aware chunking (headings, paragraphs, lists)
    - Sliding window chunking with overlap
    - Table-specific chunking
    - Provenance tracking for data lineage

Main Classes:
    - TextSplitter: Unified text splitter with method parameter
    - SemanticChunker: Semantic-based chunking coordinator
    - StructuralChunker: Structure-aware chunking
    - SlidingWindowChunker: Fixed-size sliding window chunking
    - TableChunker: Table-specific chunking
    - EntityAwareChunker: Entity boundary-preserving chunker
    - RelationAwareChunker: Triplet-preserving chunker
    - GraphBasedChunker: Graph structure-based chunker
    - OntologyAwareChunker: Ontology concept-based chunker
    - HierarchicalChunker: Multi-level hierarchical chunker
    - ProvenanceTracker: Chunk provenance tracking
    - Chunk: Chunk representation dataclass

Example Usage:
    >>> from veritasreason.split import TextSplitter
    >>> splitter = TextSplitter(method="recursive", chunk_size=1000, chunk_overlap=200)
    >>> chunks = splitter.split(text)
    >>> 
    >>> # Entity-aware for GraphRAG
    >>> splitter = TextSplitter(method="entity_aware", ner_method="llm", chunk_size=1000)
    >>> chunks = splitter.split(text)
    >>> 
    >>> # Using existing chunkers
    >>> from veritasreason.split import SemanticChunker
    >>> chunker = SemanticChunker(chunk_size=1000, chunk_overlap=200)
    >>> chunks = chunker.chunk(long_text)

Author: VeritasReason Contributors
License: MIT
"""

from .config import SplitConfig, split_config
from .kg_chunkers import (
    EntityAwareChunker,
    GraphBasedChunker,
    HierarchicalChunker,
    OntologyAwareChunker,
    RelationAwareChunker,
)
from .methods import (
    get_split_method,
    list_available_methods,
    split_by_characters,
    split_by_paragraphs,
    split_by_sentences,
    split_by_tokens,
    split_by_words,
    split_entity_aware,
    split_graph_based,
    split_hierarchical,
    split_llm,
    split_ontology_aware,
    split_recursive,
    split_relation_aware,
    split_semantic_transformer,
)
from .provenance_tracker import ProvenanceTracker
from .registry import MethodRegistry, method_registry
from .semantic_chunker import Chunk, SemanticChunker
from .sliding_window_chunker import SlidingWindowChunker
from .splitter import TextSplitter

# Alias for backward compatibility
Splitter = TextSplitter

from .structural_chunker import StructuralChunker
from .table_chunker import TableChunker

__all__ = [
    # Unified splitter
    "TextSplitter",
    "Splitter",
    # Existing chunkers
    "SemanticChunker",
    "Chunk",
    "StructuralChunker",
    "SlidingWindowChunker",
    "TableChunker",
    "ProvenanceTracker",
    # KG/Ontology chunkers
    "EntityAwareChunker",
    "RelationAwareChunker",
    "GraphBasedChunker",
    "OntologyAwareChunker",
    "HierarchicalChunker",
    # Methods
    "get_split_method",
    "list_available_methods",
    "split_recursive",
    "split_by_tokens",
    "split_by_sentences",
    "split_by_paragraphs",
    "split_by_characters",
    "split_by_words",
    "split_semantic_transformer",
    "split_llm",
    "split_entity_aware",
    "split_relation_aware",
    "split_graph_based",
    "split_ontology_aware",
    "split_hierarchical",
    # Config and Registry
    "SplitConfig",
    "split_config",
    "MethodRegistry",
    "method_registry",
]
