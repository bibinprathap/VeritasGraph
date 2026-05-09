# Ontology Management Module Usage Guide

This comprehensive guide demonstrates how to use the ontology management module for ontology generation, class/property inference, validation, evaluation, OWL generation, requirements specification, reuse management, versioning, namespace management, and associative class creation.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Ontology Generation](#ontology-generation)
3. [Class Inference](#class-inference)
4. [Property Inference](#property-inference)
5. [OWL/RDF Generation](#owlrdf-generation)
6. [Ontology Evaluation](#ontology-evaluation)
7. [Requirements Specification](#requirements-specification)
8. [Ontology Reuse](#ontology-reuse)
9. [Version Management](#version-management)
10. [Namespace Management](#namespace-management)
11. [Associative Classes](#associative-classes)
12. [Using Methods](#using-methods)
13. [Using Registry](#using-registry)
14. [Configuration](#configuration)
15. [Advanced Examples](#advanced-examples)

## Basic Usage

### Using Main Classes

```python
from veritasreason.ontology import OntologyGenerator, ClassInferrer, PropertyGenerator

# Create generators
generator = OntologyGenerator(base_uri="https://example.org/ontology/")
inferrer = ClassInferrer()
prop_gen = PropertyGenerator()

# Generate ontology
ontology = generator.generate_ontology(data)

# Infer classes
classes = inferrer.infer_classes(entities, build_hierarchy=True)

# Infer properties
properties = prop_gen.infer_properties(entities, relationships, classes)
```

### Ingesting Ontologies

```python
from veritasreason.ingest import OntologyIngestor

# Create ingestor
ingestor = OntologyIngestor()

# Ingest ontology
ontology_data = ingestor.ingest_ontology("ontology.ttl")
```

## Ontology Generation

### Basic Ontology Generation

```python
from veritasreason.ontology import OntologyEngine, OntologyGenerator

# Using OntologyEngine
data = {
    "entities": [
        {"type": "Person", "name": "John", "age": 30},
        {"type": "Person", "name": "Jane", "age": 25},
        {"type": "Organization", "name": "Acme Corp"}
    ],
    "relationships": [
        {"type": "worksFor", "source": "John", "target": "Acme Corp"},
        {"type": "worksFor", "source": "Jane", "target": "Acme Corp"}
    ]
}
engine = OntologyEngine(base_uri="https://example.org/ontology/")
ontology = engine.from_data(data, name="PersonOrgOntology")
print(f"URI: {ontology['uri']}")
print(f"Classes: {len(ontology['classes'])}")
print(f"Properties: {len(ontology['properties'])}")

# Using class directly
generator = OntologyGenerator(base_uri="https://example.org/ontology/")
ontology = generator.generate_ontology(data, name="PersonOrgOntology")
```

### 6-Stage Pipeline

The ontology generation uses a 6-stage pipeline:

1. **Semantic Network Parsing**: Extract domain concepts
2. **YAML-to-Definition**: Transform to class definitions
3. **Definition-to-Types**: Map to OWL types
4. **Hierarchy Generation**: Build taxonomic structures
5. **TTL Generation**: Generate OWL/Turtle syntax
6. **Symbolic Validation**: HermiT/Pellet reasoning

```python
from veritasreason.ontology import OntologyGenerator

generator = OntologyGenerator(base_uri="https://example.org/ontology/")

# Generate with full pipeline
ontology = generator.generate_ontology(
    data,
    name="MyOntology",
    build_hierarchy=True
)

# Access pipeline stages
print(f"Stage 1: Parsed {len(ontology.get('metadata', {}).get('concept_count', 0))} concepts")
print(f"Stage 2-3: Generated {len(ontology['classes'])} classes and {len(ontology['properties'])} properties")
print(f"Stage 4: Built hierarchy with {len([c for c in ontology['classes'] if 'parent' in c])} parent-child relationships")
```

### Generation Options

```python
from veritasreason.ontology import OntologyEngine

# Generate with custom options
engine = OntologyEngine(base_uri="https://example.org/ontology/", min_occurrences=3)
ontology = engine.from_data(
    data,
    name="CustomOntology",
    build_hierarchy=True,
)
```

## Ontology Ingestion

### Basic Ingestion

Ingest existing ontologies from files (Turtle, RDF/XML, JSON-LD, etc.) into `OntologyData` objects.

```python
from veritasreason.ontology import ingest_ontology

# Ingest a single file
ontology_data = ingest_ontology("path/to/ontology.ttl")

print(f"Source: {ontology_data.source_path}")
print(f"Format: {ontology_data.format}")
print(f"Data keys: {ontology_data.data.keys()}")
```

### Ingesting Directories

Ingest all ontology files in a directory recursively.

```python
from veritasreason.ontology import ingest_ontology

# Ingest a directory
ontologies = ingest_ontology("path/to/ontologies_dir/")

for ont in ontologies:
    print(f"Ingested: {ont.source_path} ({ont.format})")
```

### Unified Ingestion Interface

You can also use the unified `veritasreason.ingest` interface.

```python
from veritasreason.ingest import ingest

# Ingest as "ontology" source type
result = ingest("path/to/ontology.ttl", source_type="ontology")
ontology_data = result["ontology"]
```

## Class Inference

### Basic Class Inference

```python
from veritasreason.ontology import OntologyEngine, ClassInferrer

entities = [
    {"type": "Person", "name": "John", "age": 30},
    {"type": "Person", "name": "Jane", "age": 25},
    {"type": "Organization", "name": "Acme Corp"},
    {"type": "Organization", "name": "Tech Inc"}
]

engine = OntologyEngine()
classes = engine.infer_classes(entities, build_hierarchy=True)

for cls in classes:
    print(f"Class: {cls['name']}, Instances: {cls.get('entity_count', 0)}")

# Using class directly
inferrer = ClassInferrer(min_occurrences=2, similarity_threshold=0.8)
classes = inferrer.infer_classes(entities, build_hierarchy=True)
```

### Hierarchy Building

```python
from veritasreason.ontology import ClassInferrer

inferrer = ClassInferrer()

# Infer classes with hierarchy
classes = inferrer.infer_classes(entities, build_hierarchy=True)

# Build hierarchy separately
hierarchical = inferrer.build_class_hierarchy(classes)

# Validate classes
validation = inferrer.validate_classes(classes)
if validation.get("valid"):
    print("Classes are valid")
```

### Class Inference Options

```python
from veritasreason.ontology import OntologyEngine

# Custom inference options
engine = OntologyEngine()
classes = engine.infer_classes(
    entities,
    build_hierarchy=True,
)
```

## Property Inference

### Basic Property Inference

```python
from veritasreason.ontology import OntologyEngine, PropertyGenerator

entities = [
    {"type": "Person", "name": "John", "age": 30, "email": "john@example.com"},
    {"type": "Person", "name": "Jane", "age": 25, "email": "jane@example.com"}
]

relationships = [
    {"type": "worksFor", "source": "John", "target": "Acme Corp"},
    {"type": "knows", "source": "John", "target": "Jane"}
]

classes = [
    {"name": "Person", "uri": "https://example.org/ontology/Person"},
    {"name": "Organization", "uri": "https://example.org/ontology/Organization"}
]

engine = OntologyEngine()
properties = engine.infer_properties(entities, relationships, classes)

for prop in properties:
    print(f"Property: {prop['name']}, Type: {prop['type']}")

# Using class directly
prop_gen = PropertyGenerator()
properties = prop_gen.infer_properties(entities, relationships, classes)
```

### Object vs Data Properties

```python
from veritasreason.ontology import PropertyGenerator

prop_gen = PropertyGenerator()

# Infer all properties
properties = prop_gen.infer_properties(entities, relationships, classes)

# Separate object and data properties
object_props = [p for p in properties if p['type'] == 'object']
data_props = [p for p in properties if p['type'] == 'data']

print(f"Object properties: {len(object_props)}")
print(f"Data properties: {len(data_props)}")

# Validate properties
validation = prop_gen.validate_properties(properties)
```

## Ontology Validation

### Basic Validation

```python
from veritasreason.ontology import OntologyEngine, OntologyValidator

# Using OntologyEngine
engine = OntologyEngine()
result = engine.validate(ontology)

if result.valid:
    print("Ontology is valid")
if result.consistent:
    print("Ontology is consistent")
if result.errors:
    print(f"Errors: {len(result.errors)}")
if result.warnings:
    print(f"Warnings: {len(result.warnings)}")

# Using class directly
validator = OntologyValidator(reasoner="hermit")
result = validator.validate_ontology(ontology)
```

### Validation with Reasoners

```python
from veritasreason.ontology import OntologyEngine

engine = OntologyEngine()

# HermiT reasoner
result = engine.validate(ontology, reasoner="hermit")

# Pellet reasoner
result = engine.validate(ontology, reasoner="pellet")

# Auto-select reasoner
result = engine.validate(ontology, reasoner="auto")
```

### Validation Options

```python
from veritasreason.ontology import OntologyEngine

# Custom validation options
engine = OntologyEngine()
result = engine.validate(
    ontology,
    check_consistency=True,
    check_satisfiability=True,
)
```

## OWL/RDF Generation

### Basic OWL Generation

```python
from veritasreason.ontology import OntologyEngine, OWLGenerator

# Using OntologyEngine
engine = OntologyEngine()
turtle = engine.to_owl(ontology, format="turtle")
print(turtle)

# Using class directly
generator = OWLGenerator()
turtle = generator.generate_owl(ontology, format="turtle")
```

### Different Formats

```python
from veritasreason.ontology import OntologyEngine

engine = OntologyEngine()

# Turtle format
turtle = engine.to_owl(ontology, format="turtle")

# RDF/XML format
rdfxml = engine.to_owl(ontology, format="rdfxml")

# JSON-LD format
jsonld = engine.to_owl(ontology, format="json-ld")

# N3 format
n3 = engine.to_owl(ontology, format="n3")
```

### Export to File

```python
from veritasreason.ontology import OWLGenerator

generator = OWLGenerator()

# Export to file
generator.export_owl(ontology, "ontology.ttl", format="turtle")
generator.export_owl(ontology, "ontology.rdf", format="rdfxml")
generator.export_owl(ontology, "ontology.jsonld", format="json-ld")
```

## Ontology Evaluation

### Basic Evaluation

```python
from veritasreason.ontology import OntologyEngine, OntologyEvaluator

competency_questions = [
    "Who are the employees of an organization?",
    "What organizations does a person work for?",
    "What is the age of a person?"
]

engine = OntologyEngine()
result = engine.evaluate(
    ontology,
    competency_questions=competency_questions,
)

print(f"Coverage score: {result.coverage_score:.2f}")
print(f"Completeness score: {result.completeness_score:.2f}")
print(f"Gaps: {len(result.gaps)}")
print(f"Suggestions: {len(result.suggestions)}")

# Using class directly
evaluator = OntologyEvaluator()
result = evaluator.evaluate_ontology(ontology, competency_questions=competency_questions)
```

### Coverage and Completeness

```python
from veritasreason.ontology import OntologyEvaluator

evaluator = OntologyEvaluator()

# Evaluate coverage
coverage = evaluator.calculate_coverage(ontology, competency_questions)

# Evaluate completeness
completeness = evaluator.calculate_completeness(ontology)

# Identify gaps
gaps = evaluator.identify_gaps(ontology, competency_questions)

# Generate report
report = evaluator.generate_report(ontology)
```

## Requirements Specification

### Creating Requirements Spec

```python
from veritasreason.ontology import RequirementsSpecManager

# Using class directly
manager = RequirementsSpecManager()
spec = manager.create_spec(
    "PersonOntology",
    "Model person-related concepts",
    "Person entities"
)
```

### Adding Competency Questions

```python
from veritasreason.ontology import CompetencyQuestionsManager

# Using class directly
manager = CompetencyQuestionsManager()
cq = manager.add_question(
    "Who are the employees of a given organization?",
    category="organizational",
    priority=1
)
```

### Requirements Traceability

```python
from veritasreason.ontology import RequirementsSpecManager

manager = RequirementsSpecManager()

# Trace requirements to ontology
trace = manager.trace_requirements("PersonOntology", ontology)

# Validate against requirements
validation = manager.validate_against_spec("PersonOntology", ontology)
```

## Ontology Reuse

### Researching Ontologies

```python
from veritasreason.ontology import ReuseManager

# Using class directly
manager = ReuseManager()
info = manager.research_ontology("http://xmlns.com/foaf/0.1/")
```

### Importing External Ontologies

```python
from veritasreason.ontology import ReuseManager

# Using class directly
manager = ReuseManager()
updated = manager.import_external_ontology("http://xmlns.com/foaf/0.1/", ontology)
```

### Alignment Evaluation

```python
from veritasreason.ontology import ReuseManager

manager = ReuseManager()

# Evaluate alignment
alignment = manager.evaluate_alignment(
    "http://xmlns.com/foaf/0.1/",
    ontology
)

print(f"Compatibility score: {alignment.get('compatibility_score', 0):.2f}")
print(f"Decision: {alignment.get('decision')}")
```

## Version Management

### Creating Versions

```python
from veritasreason.ontology import VersionManager

print(f"Version: {version.version}")
print(f"IRI: {version.ontology_iri}")

# Using class directly
manager = VersionManager(base_uri="https://example.org/ontology/")
version = manager.create_version("1.0", ontology, changes=["Added Person class"])
```

### Version Comparison

```python
from veritasreason.ontology import VersionManager

manager = VersionManager()

# Compare versions
comparison = manager.compare_versions("1.0", "2.0")

# Get version diff
diff = manager.get_version_diff("1.0", "2.0")

# Migrate ontology
migrated = manager.migrate_ontology("1.0", "2.0", ontology)
```

## Namespace Management

### Managing Namespaces

```python
from veritasreason.ontology import NamespaceManager

# Using class directly
manager = NamespaceManager(base_uri="https://example.org/ontology/")
class_iri = manager.generate_class_iri("Person")
property_iri = manager.generate_property_iri("hasName")
```

### Registering Namespaces

```python
from veritasreason.ontology import NamespaceManager

manager = NamespaceManager()

# Register custom namespace
manager.register_namespace("ex", "https://example.org/")

# Get base URI
base_uri = manager.get_base_uri()

# Get all namespaces
namespaces = manager.get_all_namespaces()
```

## Associative Classes

### Creating Associative Classes

```python
from veritasreason.ontology import AssociativeClassBuilder

# Using class directly
builder = AssociativeClassBuilder()
position = builder.create_associative_class(
    "Position",
    ["Person", "Organization", "Role"],
    properties={"startDate": "xsd:date"},
    temporal=True
)
```

### Position Classes

```python
from veritasreason.ontology import AssociativeClassBuilder

builder = AssociativeClassBuilder()

# Create position class
position = builder.create_position_class(
    person_class="Person",
    organization_class="Organization",
    role_class="Role"
)

# Validate associative class
validation = builder.validate_associative_class(position)
```

## Using Methods

### Getting Available Methods

```python
from veritasreason.ontology.methods import get_ontology_method, list_available_methods

# List all available methods
all_methods = list_available_methods()
print("Available methods:", all_methods)

# List methods for specific task
generate_methods = list_available_methods("generate")
print("Generation methods:", generate_methods)

# Get specific method
generate_method = get_ontology_method("generate", "default")
if generate_method:
    ontology = generate_method(data)
```

### Method Examples

```

## Using Registry

### Registering Custom Methods

```python
from veritasreason.ontology.registry import method_registry

# Custom ontology generation method
def custom_ontology_generation(data, **kwargs):
    """Custom generation logic."""
    # Your custom generation code
    return {"uri": "custom", "name": "CustomOntology", "classes": [], "properties": []}

# Register custom method
method_registry.register("generate", "custom", custom_ontology_generation)

# Use custom method
from veritasreason.ontology.methods import get_ontology_method
custom_method = get_ontology_method("generate", "custom")
ontology = custom_method(data)
```

### Listing Registered Methods

```python
from veritasreason.ontology.registry import method_registry

# List all registered methods
all_methods = method_registry.list_all()
print("Registered methods:", all_methods)

# List methods for specific task
generate_methods = method_registry.list_all("generate")
print("Generation methods:", generate_methods)

validate_methods = method_registry.list_all("validate")
print("Validation methods:", validate_methods)
```

### Unregistering Methods

```python
from veritasreason.ontology.registry import method_registry

# Unregister a method
method_registry.unregister("generate", "custom")

# Clear all methods for a task
method_registry.clear("generate")

# Clear all methods
method_registry.clear()
```

## Configuration

### Using Configuration Manager

```python
from veritasreason.ontology.config import ontology_config

# Get configuration values
base_uri = ontology_config.get("base_uri", default="https://veritasreason.dev/ontology/")
reasoner = ontology_config.get("reasoner", default="auto")
format = ontology_config.get("format", default="turtle")
min_occurrences = ontology_config.get("min_occurrences", default=2)

# Set configuration values
ontology_config.set("base_uri", "https://example.org/ontology/")
ontology_config.set("reasoner", "hermit")

# Method-specific configuration
ontology_config.set_method_config("generate", base_uri="https://example.org/ontology/", min_occurrences=3)
generate_config = ontology_config.get_method_config("generate")

# Get all configuration
all_config = ontology_config.get_all()
print("All config:", all_config)
```

### Environment Variables

```bash
# Set environment variables
export ONTOLOGY_BASE_URI=https://example.org/ontology/
export ONTOLOGY_REASONER=hermit
export ONTOLOGY_FORMAT=turtle
export ONTOLOGY_MIN_OCCURRENCES=3
export ONTOLOGY_SIMILARITY_THRESHOLD=0.85
export ONTOLOGY_CHECK_CONSISTENCY=true
export ONTOLOGY_CHECK_SATISFIABILITY=true
```

### Configuration File

```yaml
# config.yaml
ontology:
  base_uri: https://example.org/ontology/
  reasoner: hermit
  format: turtle
  min_occurrences: 3
  similarity_threshold: 0.85
  check_consistency: true
  check_satisfiability: true

ontology_methods:
  generate:
    base_uri: https://example.org/ontology/
    min_occurrences: 3
  validate:
    reasoner: hermit
    check_consistency: true
  owl:
    format: turtle
```

```python
from veritasreason.ontology.config import OntologyConfig

# Load from config file
config = OntologyConfig(config_file="config.yaml")
base_uri = config.get("base_uri")
```

## Advanced Examples

### Complete Ontology Generation Pipeline

```python
from veritasreason.ontology import OntologyEngine

engine = OntologyEngine(base_uri="https://example.org/ontology/")

# Step 1: Generate ontology
data = {
    "entities": [
        {"type": "Person", "name": "John", "age": 30},
        {"type": "Person", "name": "Jane", "age": 25},
        {"type": "Organization", "name": "Acme Corp"}
    ],
    "relationships": [
        {"type": "worksFor", "source": "John", "target": "Acme Corp"}
    ]
}

ontology = engine.from_data(data, name="PersonOrgOntology")

# Step 2: Validate ontology
result = engine.validate(ontology)
if not result.valid:
    print(f"Validation errors: {result.errors}")

# Step 3: Generate OWL
turtle = engine.to_owl(ontology, format="turtle")

# Step 4: Evaluate ontology
competency_questions = ["Who are the employees of an organization?"]
evaluation = engine.evaluate(ontology, competency_questions=competency_questions)

print(f"Coverage: {evaluation.coverage_score:.2f}")
print(f"Completeness: {evaluation.completeness_score:.2f}")
```

### Custom Ontology Workflow

```python
from veritasreason.ontology import (
    OntologyGenerator,
    ClassInferrer,
    PropertyGenerator,
    OntologyValidator,
    OWLGenerator
)

# Create generators with custom config
generator = OntologyGenerator(
    base_uri="https://example.org/ontology/",
    min_occurrences=3
)

inferrer = ClassInferrer(min_occurrences=3, similarity_threshold=0.85)
prop_gen = PropertyGenerator()
validator = OntologyValidator(reasoner="hermit")
owl_gen = OWLGenerator()

# Generate ontology
ontology = generator.generate_ontology(data, name="CustomOntology")

# Infer classes
classes = inferrer.infer_classes(entities, build_hierarchy=True)

# Infer properties
properties = prop_gen.infer_properties(entities, relationships, classes)

# Validate
result = validator.validate(ontology)

# Generate OWL
turtle = owl_gen.generate_owl(ontology, format="turtle")
```

### Requirements-Driven Development

```python
from veritasreason.ontology import OntologyEngine, RequirementsSpecManager, CompetencyQuestionsManager

# Step 1: Create requirements specification
manager = RequirementsSpecManager()
spec = manager.create_spec(
    "PersonOntology",
    "Model person-related concepts",
    "Person, Organization, Role entities",
)

# Step 2: Add competency questions
cq_manager = CompetencyQuestionsManager()
cq_manager.add_question("Who are the employees?", category="organizational")
cq_manager.add_question("What organizations does a person work for?", category="organizational")

# Step 3: Generate ontology
engine = OntologyEngine()
ontology = engine.from_data(data)

# Step 4: Evaluate against requirements
competency_questions = ["Who are the employees?", "What organizations does a person work for?"]
evaluation = engine.evaluate(ontology, competency_questions=competency_questions)

# Step 5: Refine based on gaps
if evaluation.gaps:
    print(f"Gaps identified: {evaluation.gaps}")
    print(f"Suggestions: {evaluation.suggestions}")
```

### Version Management Workflow

```python
from veritasreason.ontology import OntologyEngine, VersionManager

# Generate initial ontology
engine = OntologyEngine()
ontology_v1 = engine.from_data(data, name="PersonOntology")

# Create version 1.0
manager = VersionManager()
version1 = manager.create_version("1.0", ontology_v1, changes=["Initial version"])

# Modify ontology (add new class)
ontology_v2 = ontology_v1.copy()
ontology_v2["classes"].append({"name": "Role", "uri": "https://example.org/ontology/Role"})

# Create version 2.0
version2 = manager.create_version("2.0", ontology_v2, changes=["Added Role class"])

# Compare versions
manager = VersionManager()
comparison = manager.compare_versions("1.0", "2.0")
print(f"Changes: {comparison.get('changes', [])}")
```

### Integration with Knowledge Graph

```python
from veritasreason.ontology import OntologyEngine
from veritasreason.kg import build

# Build knowledge graph
kg = build(sources=[{"entities": entities, "relationships": relationships}])

# Generate ontology from KG
engine = OntologyEngine()
ontology = engine.from_data({
    "entities": kg.get("entities", []),
    "relationships": kg.get("relationships", [])
})

# Generate OWL
turtle = engine.to_owl(ontology, format="turtle")

# Export for use in KG
with open("ontology.ttl", "w") as f:
    f.write(turtle)
```

## Best Practices

1. **Ontology Generation**: Always validate generated ontologies before use
2. **Class Inference**: Use appropriate minimum occurrence thresholds to avoid noise
3. **Property Inference**: Validate domain/range constraints for properties
4. **Validation**: Use symbolic reasoners (HermiT/Pellet) for consistency checking
5. **OWL Generation**: Prefer Turtle format for readability, RDF/XML for compatibility
6. **Evaluation**: Define competency questions early in the development process
7. **Requirements**: Trace requirements to ontology elements for maintainability
8. **Reuse**: Research existing ontologies before creating new ones
9. **Versioning**: Use version-aware IRIs following best practices
10. **Namespaces**: Use stable, resolvable URIs for namespaces
11. **Associative Classes**: Use for complex relationships with properties
12. **Configuration**: Use configuration files for consistent settings across environments
13. **Error Handling**: Always handle ValidationError and ProcessingError exceptions
14. **Method Registry**: Register custom methods for domain-specific ontology needs

# Ontology Module Usage

This guide shows the streamlined API for ontology generation, validation, evaluation, and OWL export. It reflects the refactor that removes global convenience wrappers and introduces a single `OntologyEngine` plus an LLM-driven generator.

## Quick Start

```python
from veritasreason.ontology import OntologyEngine

engine = OntologyEngine(base_uri="https://example.org/ontology/")

# From structured data
data = {"entities": entities, "relationships": relationships}
ontology = engine.from_data(data)

# Validate
result = engine.validate(ontology)
print(result.valid, result.consistent)

# Export OWL
turtle = engine.to_owl(ontology, format="turtle")
with open("ontology.ttl", "w") as f:
    f.write(turtle)
```

## API Overview

- `OntologyEngine` (unified orchestration)
  - `from_data(data, **options)` → ontology dict
  - `from_text(text, provider=None, model=None, **options)` → ontology dict
  - `infer_classes(entities, **options)` → classes list
  - `infer_properties(entities, relationships, classes, **options)` → properties list
  - `validate(ontology, **options)` → `ValidationResult`
  - `evaluate(ontology, **options)` → evaluation dict
  - `to_owl(ontology, format="turtle", **options)` → serialization
  - `export_owl(ontology, path, format="turtle")` → file output

- `LLMOntologyGenerator` (LLM-based generation)
  - `set_provider(provider, model=None, **kwargs)`
  - `generate_ontology_from_text(text, **options)`

## LLM-Based Generation

```python
from veritasreason.ontology import OntologyEngine

engine = OntologyEngine()

# Choose provider: "openai", "groq", "deepseek", "huggingface_llm"
ontology = engine.from_text(
    text,
    provider="openai",
    model="gpt-4o",
    name="CompanyOntology",
    base_uri="https://example.org/company/",
)

print(len(ontology.get("classes", [])), len(ontology.get("properties", [])))
```

Environment variables used by providers:

```bash
export OPENAI_API_KEY=...
export GROQ_API_KEY=...
export DEEPSEEK_API_KEY=...
```

HuggingFace local models do not require API keys but require `transformers` installed.

## Data-Based Generation

```python
from veritasreason.ontology import OntologyEngine

engine = OntologyEngine(base_uri="https://example.org/ontology/")

sources = {
    "entities": [
        {"type": "Person", "name": "Alice"},
        {"type": "Organization", "name": "Acme"}
    ],
    "relationships": [
        {"type": "worksFor", "source": "Alice", "target": "Acme"}
    ]
}

ontology = engine.from_data(sources)
```

## Class and Property Inference

```python
classes = engine.infer_classes(entities, build_hierarchy=True)
properties = engine.infer_properties(entities, relationships, classes)
```

## Validation

```python
result = engine.validate(
    ontology,
    reasoner="hermit",          # "hermit" | "pellet" | "auto"
    check_consistency=True,
    check_satisfiability=True,
)

if result.errors:
    for e in result.errors:
        print(e)
```

Reference: `OntologyValidator` implementation at `veritasreason/ontology/ontology_validator.py:59`.

## OWL Export

```python
turtle = engine.to_owl(ontology, format="turtle")
engine.export_owl(ontology, "ontology.ttl", format="turtle")

rdfxml = engine.to_owl(ontology, format="rdfxml")
jsonld  = engine.to_owl(ontology, format="json-ld")
```

OWL generation uses `OWLGenerator` at `veritasreason/ontology/owl_generator.py:277` for fallback formatting and rdflib-based generation at `veritasreason/ontology/owl_generator.py:156`.

## Evaluation

```python
report = engine.evaluate(ontology)
print(report.get("evaluation", {}))
```

Evaluation includes gap analysis and completeness; see `veritasreason/ontology/ontology_evaluator.py:203`.

## Migration Notes

- Removed global convenience wrappers (e.g., `generate_ontology`, `validate_ontology`).
- Use `OntologyEngine` or direct classes:
  - Generation: `OntologyGenerator().generate_ontology(...)` at `veritasreason/ontology/ontology_generator.py:231`
  - Classes: `ClassInferrer().infer_classes(...)` at `veritasreason/ontology/class_inferrer.py:1`
  - Properties: `PropertyGenerator().infer_properties(...)` at `veritasreason/ontology/property_generator.py:1`
  - Validation: `OntologyValidator().validate_ontology(...)` at `veritasreason/ontology/ontology_validator.py:59`
  - OWL: `OWLGenerator().generate_owl(...)` at `veritasreason/ontology/owl_generator.py:277`

## End-to-End Example

```python
from veritasreason.ontology import OntologyEngine

text = """
Acme Corp. hired Alice as a Software Engineer in 2024. Alice works for Acme.
"""

engine = OntologyEngine()

ontology = engine.from_text(
    text,
    provider="deepseek",
    model="deepseek-chat",
    name="EmploymentOntology",
    base_uri="https://example.org/employment/",
)

result = engine.validate(ontology, reasoner="auto")
print("valid=", result.valid, "consistent=", result.consistent)

ttl = engine.to_owl(ontology, format="turtle")
with open("employment.ttl", "w") as f:
    f.write(ttl)
```

## Best Practices

- Always validate LLM-generated ontologies using a reasoner.
- Prefer domain prompts and few-shot examples for LLM generation.
- Keep class names PascalCase and properties camelCase; use stable base URIs.
- Export and version your ontology as part of CI.
