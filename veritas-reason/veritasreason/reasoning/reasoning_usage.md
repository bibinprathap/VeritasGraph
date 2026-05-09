# Reasoning Module Usage Guide

The **VeritasReason Reasoning Module** provides a suite of tools for deriving new knowledge from existing facts and knowledge graphs. It supports multiple strategies including rule-based inference, SPARQL-based reasoning, and specialized abductive/deductive reasoners.

## 🚀 Quick Start

```python
from veritasreason.reasoning import Reasoner, Rule, Fact

# Create reasoner
reasoner = Reasoner()

# Add facts
reasoner.add_fact("Person(John)")
reasoner.add_fact("Person(Jane)")

# Add rule
rule = reasoner.add_rule("IF Person(?x) THEN Human(?x)")

# Perform inference
results = reasoner.infer()

print(f"Inferred {len(results)} new facts")
for res in results:
    print(f"Fact: {res.conclusion}")
```

## Core Components

### 1. Reasoner (Facade)
The `Reasoner` class provides a simplified, unified interface to the reasoning system. It is the recommended entry point for all reasoning tasks.

```python
from veritasreason.reasoning import Reasoner

reasoner = Reasoner()
reasoner.add_fact("WorksFor(John, Acme)")
reasoner.add_rule("IF WorksFor(?x, ?y) THEN Employee(?x, ?y)")

results = reasoner.infer()
```

### 2. SPARQL Reasoner
Used for reasoning over RDF/Triplet stores using SPARQL query expansion.

```python
from veritasreason.reasoning import SPARQLReasoner

# Create reasoner with knowledge graph
reasoner = SPARQLReasoner(triplet_store=kg)

# Execute query
query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
result = reasoner.execute_query(query)
```

### 3. Rete Engine
High-performance pattern matching for complex rule sets.

```python
from veritasreason.reasoning import ReteEngine, Fact

rete = ReteEngine()
# ... build network and add facts ...
matches = rete.match_patterns()
```

## Data Structures

### Rule
Represents an inference rule with conditions and a conclusion.
- `rule_id`: Unique identifier
- `name`: Human-readable name
- `conditions`: List of patterns to match
- `conclusion`: Pattern to derive
- `rule_type`: IMPLICATION, EQUIVALENCE, etc.

### Fact
Represents a single piece of knowledge.
- `fact_id`: Unique identifier
- `predicate`: Relationship or property name
- `arguments`: List of subjects/objects

## Explanation Generation
All reasoning results can be passed to the `ExplanationGenerator` to produce human-readable justifications.

```python
from veritasreason.reasoning import ExplanationGenerator

explainer = ExplanationGenerator()
explanation = explainer.generate_explanation(results[0])
print(explanation.natural_language)
```
