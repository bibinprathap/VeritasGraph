"""
Ontology Methods Module

This module provides all ontology operations as simple, reusable functions for
ontology generation, class/property inference, validation, evaluation, OWL generation,
requirements specification, reuse management, versioning, namespace management, and
associative class creation. It supports multiple approaches and integrates with the
method registry for extensibility.

Supported Methods:

Ontology Generation:
    - "default": Default ontology generation using 6-stage pipeline
    - "from_data": Generate from entity/relationship data
    - "from_text": Generate from text (future support)

Class/Property Inference:
    - "default": Default inference using ClassInferrer/PropertyGenerator
    - "pattern": Pattern-based inference
    - "hierarchical": Hierarchy-focused inference

Evaluation:
    - "default": Default evaluation using OntologyEvaluator
    - "coverage": Coverage-focused evaluation
    - "completeness": Completeness-focused evaluation

OWL Generation:
    - "default": Default OWL generation using OWLGenerator
    - "turtle": Turtle format generation
    - "rdfxml": RDF/XML format generation
    - "jsonld": JSON-LD format generation

Algorithms Used:

Ontology Generation (6-Stage Pipeline):
    - Stage 1 - Semantic Network Parsing: Extract domain concepts from entities/relationships, entity type analysis (Counter), relationship pattern extraction
    - Stage 2 - YAML-to-Definition: Transform concepts into class definitions, YAML parsing, definition structure creation
    - Stage 3 - Definition-to-Types: Map definitions to OWL types, type inference, OWL class/property mapping (@type assignment)
    - Stage 4 - Hierarchy Generation: Build taxonomic structures, parent-child relationship inference, hierarchy validation, circular dependency detection (DFS)
    - Stage 5 - TTL Generation: Generate OWL/Turtle syntax using rdflib, namespace prefix handling, RDF serialization (rdflib.serialize)

Class Inference:
    - Pattern-Based Inference: Entity type frequency analysis (Counter), minimum occurrence threshold filtering, similarity-based class merging (threshold matching)
    - Hierarchy Building: Parent-child relationship inference, transitive closure calculation, hierarchy depth analysis, circular dependency detection (DFS)
    - Class Validation: Naming convention enforcement (PascalCase), IRI generation (namespace_manager.generate_class_iri), namespace validation

Property Inference:
    - Object Property Inference: Relationship type analysis, domain/range inference from entity types, property cardinality detection
    - Data Property Inference: Entity attribute analysis, XSD type detection (string, integer, float, boolean, date), property domain inference
    - Property Validation: Domain/range validation, property hierarchy management, naming convention enforcement (camelCase)

Ontology Validation:
    - Symbolic Reasoning: HermiT reasoner integration (owlready2.sync_reasoner), Pellet reasoner integration, consistency checking, satisfiability checking
    - Constraint Validation: Domain/range constraint checking, cardinality constraint validation, logical constraint validation
    - Hallucination Detection: LLM-generated ontology validation, fact verification, relationship validation

OWL/RDF Generation:
    - RDF Graph Construction: rdflib.Graph creation, namespace binding, triplet generation (subject-predicate-object)
    - Serialization: Turtle format (rdflib.serialize format="turtle"), RDF/XML format, JSON-LD format, N3 format
    - Namespace Management: Prefix declaration, IRI resolution, namespace prefix mapping

Ontology Evaluation:
    - Competency Question Validation: Question parsing, ontology query generation, answer coverage analysis
    - Coverage Metrics: Class coverage calculation, property coverage calculation, relationship coverage calculation
    - Completeness Metrics: Required class detection, missing property identification, gap analysis
    - Granularity Evaluation: Class granularity assessment, generalization/specialization analysis

Requirements Specification:
    - Competency Question Management: Question storage, categorization, validation
    - Scope Definition: Domain boundary definition, entity type scoping, relationship scoping
    - Traceability: Requirements-to-ontology mapping, coverage tracking

Ontology Reuse:
    - Ontology Research: Known ontology catalog lookup (FOAF, Dublin Core, Schema.org), URI resolution, metadata extraction
    - Alignment Evaluation: Concept alignment scoring, compatibility assessment, interoperability analysis
    - Import Management: External ontology import, namespace merging, conflict resolution

Version Management:
    - Version-Aware IRI Generation: Version in ontology IRI (not element IRIs), version-less element IRIs, logical version-less IRIs
    - Version Comparison: Diff generation, change detection, migration path identification
    - Multi-Version Coexistence: Version isolation, import closure resolution

Namespace Management:
    - IRI Generation: Base URI + local name construction (urljoin), namespace prefix mapping, IRI validation
    - Prefix Handling: Prefix declaration, namespace binding, prefix resolution

Associative Class Creation:
    - Complex Relationship Modeling: N-ary relationship handling, relationship properties, intermediate class creation
    - Pattern Detection: Relationship pattern analysis, associative class inference

Key Features:
    - Multiple ontology operation methods
    - Ontology operations with method dispatch
    - Method dispatchers with registry support
    - Custom method registration capability
    - Consistent interface across all methods

Main Functions:
    - generate_ontology: Ontology generation wrapper (6-stage pipeline)
    - infer_classes: Class inference wrapper
    - infer_properties: Property inference wrapper
    - validate_ontology: Ontology validation wrapper
    - generate_owl: OWL/RDF generation wrapper
    - evaluate_ontology: Ontology evaluation wrapper
    - create_requirements_spec: Requirements specification wrapper
    - add_competency_question: Competency question management wrapper
    - research_ontology: Ontology research wrapper
    - import_external_ontology: External ontology import wrapper
    - create_version: Version creation wrapper
    - manage_namespace: Namespace management wrapper
    - create_associative_class: Associative class creation wrapper
    - get_ontology_method: Get ontology method by name
    - list_available_methods: List registered methods
    - ingest_ontology: Ingest ontology from file or directory (via veritasreason.ingest)

Example Usage:
    >>> from veritasreason.ontology.methods import generate_ontology, infer_classes, ingest_ontology
    >>> ontology = generate_ontology({"entities": [...], "relationships": [...]}, method="default")
    >>> classes = infer_classes(entities, method="default")
    >>> data = ingest_ontology("ontology.ttl")
"""

from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path

from veritasreason.ingest import ingest_ontology as _ingest_ontology, OntologyData
from .registry import method_registry


pass


pass


pass


pass


pass


pass


pass


pass


pass


pass


pass


pass


pass


def get_ontology_method(task: str, name: str) -> Optional[Callable]:
    """Get ontology method by task and name."""
    return method_registry.get(task, name)


def list_available_methods(task: Optional[str] = None) -> Dict[str, List[str]]:
    """List all registered ontology methods."""
    return method_registry.list_all(task)


def ingest_ontology(
    source: Union[str, Path, List[Union[str, Path]]], 
    method: str = "file", 
    **kwargs
) -> Union[OntologyData, List[OntologyData]]:
    """
    Ingest ontology from source.
    
    This is a convenience wrapper around veritasreason.ingest.ingest_ontology.
    
    Args:
        source: Ontology file path, directory path, or list of paths
        method: Ingestion method (default: "file")
        **kwargs: Additional options
        
    Returns:
        OntologyData or List[OntologyData]
    """
    return _ingest_ontology(source, method=method, **kwargs)

