"""
Semantic Extraction Module

This module provides comprehensive semantic extraction capabilities for knowledge
engineering, enabling extraction of entities, relations, events, triplets, and
semantic networks from text.

Key Features:
    - Named entity recognition (NER) with multiple implementations
    - Relationship extraction between entities
    - Event detection and temporal processing
    - Coreference resolution for pronouns and entity references
    - RDF triplet extraction and serialization
    - Semantic analysis and role labeling
    - Semantic network construction
    - LLM-based extraction enhancement
    - Extraction validation and quality assessment
    - Batch processing with provenance tracking (batch_index, document_id)
    - Robust fallback mechanisms (ML -> Pattern -> Last Resort)

Main Classes:
    - NamedEntityRecognizer: Main NER coordinator (confidence_threshold, merge_overlapping)
    - NERExtractor: Core NER implementation
    - RelationExtractor: Relationship extraction (confidence_threshold, bidirectional)
    - EventDetector: Event detection and classification (extract_participants, extract_time)
    - CoreferenceResolver: Coreference resolution
    - TripletExtractor: RDF triplet extraction (include_temporal, include_provenance)
    - SemanticAnalyzer: Semantic analysis engine
    - SemanticNetworkExtractor: Semantic network construction
    - LLMExtraction: LLM-based extraction and enhancement
    - ExtractionValidator: Quality validation

Example Usage:
    >>> from veritasreason.semantic_extract import NamedEntityRecognizer
    >>> ner = NamedEntityRecognizer(confidence_threshold=0.7)
    >>> entities = ner.extract_entities("Steve Jobs founded Apple.")
    
    >>> from veritasreason.semantic_extract import RelationExtractor
    >>> rel_extractor = RelationExtractor(confidence_threshold=0.6)
    >>> relations = rel_extractor.extract_relations(text, entities=entities)
    
    >>> from veritasreason.semantic_extract import TripletExtractor
    >>> triplet_extractor = TripletExtractor(include_temporal=True)
    >>> triplets = triplet_extractor.extract_triplets(text)

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Dict, List, Optional, Union

from .config import Config, config
from .coreference_resolver import (
    CoreferenceChain,
    CoreferenceChainBuilder,
    CoreferenceResolver,
    EntityCoreferenceDetector,
    Mention,
    PronounResolver,
)
from .event_detector import (
    Event,
    EventClassifier,
    EventDetector,
    EventRelationshipExtractor,
    TemporalEventProcessor,
)
from .extraction_validator import ExtractionValidator, ValidationResult
from .llm_extraction import LLMEnhancer, LLMExtraction, LLMResponse
from .methods import get_entity_method, get_relation_method, get_triplet_method
from .named_entity_recognizer import (
    CustomEntityDetector,
    EntityClassifier,
    EntityConfidenceScorer,
    NamedEntityRecognizer,
)
from .ner_extractor import Entity, NERExtractor
from .providers import (
    AnthropicProvider,
    BaseProvider,
    GeminiProvider,
    GroqProvider,
    HuggingFaceLLMProvider,
    HuggingFaceModelLoader,
    OllamaProvider,
    OpenAIProvider,
    create_provider,
)
from .registry import (
    MethodRegistry,
    ProviderRegistry,
    method_registry,
    provider_registry,
)
from .relation_extractor import Relation, RelationExtractor
from .semantic_analyzer import (
    RoleLabeler,
    SemanticAnalyzer,
    SemanticCluster,
    SemanticClusterer,
    SemanticRole,
    SimilarityAnalyzer,
)
from .semantic_network_extractor import (
    SemanticEdge,
    SemanticNetwork,
    SemanticNetworkExtractor,
    SemanticNode,
)
from .triplet_extractor import (
    RDFSerializer,
    Triplet,
    TripletExtractor,
    TripletQualityChecker,
    TripletValidator,
)

__all__ = [
    # Named Entity Recognition
    "NamedEntityRecognizer",
    "EntityClassifier",
    "EntityConfidenceScorer",
    "CustomEntityDetector",
    "NERExtractor",
    "Entity",
    # Relation Extraction
    "RelationExtractor",
    "Relation",
    # Event Detection
    "EventDetector",
    "Event",
    "EventClassifier",
    "TemporalEventProcessor",
    "EventRelationshipExtractor",
    # Coreference Resolution
    "CoreferenceResolver",
    "Mention",
    "CoreferenceChain",
    "PronounResolver",
    "EntityCoreferenceDetector",
    "CoreferenceChainBuilder",
    # Triplet Extraction
    "TripletExtractor",
    "Triplet",
    "TripletValidator",
    "RDFSerializer",
    "TripletQualityChecker",
    # Semantic Analysis
    "SemanticAnalyzer",
    "SemanticRole",
    "SemanticCluster",
    "SimilarityAnalyzer",
    "RoleLabeler",
    "SemanticClusterer",
    # Semantic Network
    "SemanticNetworkExtractor",
    "SemanticNode",
    "SemanticEdge",
    "SemanticNetwork",
    # LLM Enhancement
    "LLMExtraction",
    "LLMEnhancer",
    "LLMResponse",
    # Validation
    "ExtractionValidator",
    "ValidationResult",
    # Providers
    "BaseProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "GroqProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "HuggingFaceLLMProvider",
    "HuggingFaceModelLoader",
    "create_provider",
    # Registry
    "ProviderRegistry",
    "MethodRegistry",
    "provider_registry",
    "method_registry",
    # Config
    "Config",
    "config",
    # Methods
    "get_entity_method",
    "get_relation_method",
    "get_triplet_method",
]
