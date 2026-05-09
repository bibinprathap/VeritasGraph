# Reasoning

> **Simplified reasoning module supporting rule-based inference, SPARQL, and high-performance pattern matching.**

---

## 🎯 Overview

The **Reasoning Module** provides logical inference capabilities for deriving new knowledge from existing facts. It supports rule-based inference, SPARQL-based reasoning, and high-performance pattern matching.

### What is Reasoning?

**Reasoning** is the process of deriving new facts from existing knowledge using logical rules. For example:
- **Given**: `` `Parent(Alice, Bob)` `` and `` `Parent(Bob, Charlie)` ``
- **Rule**: `` `IF Parent(?x, ?y) AND Parent(?y, ?z) THEN Grandparent(?x, ?z)` ``
- **Inferred**: `` `Grandparent(Alice, Charlie)` ``

### Why Use the Reasoning Module?

- **Knowledge Discovery**: Find implicit relationships not explicitly stored
- **Query Expansion**: Answer queries that require inference
- **Validation**: Check logical consistency of knowledge graphs
- **Explanation**: Understand how facts were derived
- **Rule-Based Logic**: Define domain-specific inference rules

### How It Works

1. **Rule Definition**: Define inference rules (IF-THEN patterns)
2. **Fact Matching**: Match facts against rule conditions
3. **Variable Binding**: Bind variables in rules to actual entities
4. **Inference**: Derive new facts from matched rules
5. **Explanation**: Generate explanations for inferred facts

<div class="grid cards" markdown>

-   :material-brain:{ .lg .middle } **Rule-based Inference**

    ---

    Forward-chaining inference engine with variable substitution

-   :material-database-search:{ .lg .middle } **SPARQL Reasoning**

    ---

    Query expansion and property chain inference for RDF graphs

-   :material-flash:{ .lg .middle } **Rete Algorithm**

    ---

    High-performance pattern matching for large rule sets

-   :material-text-box-search:{ .lg .middle } **Explanation**

    ---

    Generate natural language explanations for inferred facts

</div>

!!! tip "When to Use"
    - **Inference**: Deriving new facts from existing data (e.g., `` `Parent(A,B) & Parent(B,C) -> Grandparent(A,C)` ``)
    - **Query Expansion**: Finding results that aren't explicitly stored but implied
    - **Explanation**: Understanding the reasoning path for any derived fact
    - **Validation**: Checking logical consistency of the knowledge graph

---

## ⚙️ Algorithms Used

### Forward Chaining

**Purpose**: Derive new facts from existing knowledge using logical rules.

**How it works**:

- **Variable Substitution**: Supports patterns like `` `Person(?x)` `` to match facts and bind variables
- **Recursive Inference**: Continues deriving facts until no new information can be found
- **Priority-based Execution**: Rules can be prioritized to control the inference flow

**Complexity**: `` `O(n * m)` `` where n is the number of facts and m is the number of rules

**Example**:

```python
# Forward chaining implementation
reasoner = Reasoner()
rules = ["IF Person(?x) THEN Human(?x)"]
facts = ["Person(John)"]
new_facts = reasoner.infer_facts(facts, rules)
```

### Rete Algorithm

**Purpose**: High-performance pattern matching for large rule sets with frequent fact updates.

**How it works**:

- **Alpha Nodes**: Filter facts by single attributes (e.g., `` `type=Person` ``)
- **Beta Nodes**: Join results from Alpha nodes (e.g., `` `Person.id == Parent.child_id` ``)
- **Memory**: Stores partial matches to avoid re-computation
- **Efficiency**: Optimal for scenarios with many rules and frequent fact updates

**Complexity**: `` `O(n + m)` `` where n is the number of facts and m is the number of rules (amortized)

---

## Main Classes

### Reasoner (Facade)

The high-level interface for the reasoning module.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `infer_facts(facts, rules)` `` | Derive new facts from initial state |
| `` `backward_chain(goal)` `` | Prove a goal using backward chaining |
| `` `add_rule(rule)` `` | Add a new inference rule |
| `` `add_fact(fact)` `` | Add a fact to working memory |
| `` `clear()` `` | Reset the reasoner state |

### ReteEngine

High-performance pattern matching engine.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `build_network(rules)` `` | Compile rules into a Rete network |
| `` `add_fact(fact)` `` | Propagate fact through the network |
| `` `match_patterns()` `` | Get triggered rules |

### ExplanationGenerator

Explains *why* a fact was inferred.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `generate_explanation(result)` `` | Generate reasoning trace for an InferenceResult |

---

## Usage Examples

### Simple Rule-based Inference

```python
from veritasreason.reasoning import Reasoner

reasoner = Reasoner()

# Define rules
rules = [
    "IF Person(?x) THEN Human(?x)",
    "IF Human(?x) AND Parent(?x, ?y) THEN Human(?y)"
]

# Initial facts
facts = ["Person(John)", "Parent(John, Jane)"]

# Run inference
new_facts = reasoner.infer_facts(facts, rules)
# Result: ["Human(John)", "Human(Jane)"]
```

### Goal-driven Reasoning (Backward Chaining)

```python
from veritasreason.reasoning import Reasoner

reasoner = Reasoner()
reasoner.add_rule("IF Parent(?a, ?b) AND Parent(?b, ?c) THEN Grandparent(?a, ?c)")
reasoner.add_fact("Parent(Alice, Bob)")
reasoner.add_fact("Parent(Bob, Charlie)")

# Prove a goal
proof = reasoner.backward_chain("Grandparent(Alice, Charlie)")

if proof:
    print(f"Proven: {proof.conclusion}")
    print(f"Steps: {proof.premises}")
```

### Knowledge Graph Enrichment

```python
from veritasreason.reasoning import Reasoner
from veritasreason.kg import GraphBuilder

# 1. Define Rules
rules = [
    "IF Sibling(?x, ?y) THEN Sibling(?y, ?x)",
    "IF Ancestor(?x, ?y) AND Ancestor(?y, ?z) THEN Ancestor(?x, ?z)"
]

# 2. Build Graph and Run Inference
builder = GraphBuilder()
kg = builder.build(sources=data)

reasoner = Reasoner()
# Infer new facts from entities and relationships
inferred = reasoner.infer_facts(kg["entities"] + kg["relationships"], rules)

# 3. Update Graph with Inferred Facts
for fact_str in inferred:
    # Add new inferred facts back to the graph
    # For a production app, you'd parse these into entities/relationships
    kg["entities"].append({"type": "InferredFact", "name": fact_str})
```

---

## Best Practices

1. **Limit Recursion**: Be careful with recursive rules (e.g., `` `A(x,y) -> A(y,x)` ``) which can cause infinite loops in naive implementations
2. **Use Rete for Scale**: For >100 rules or >10k facts, always use the Rete engine
3. **Materialize vs. Query**: Materialize (pre-compute) for read-heavy workloads; Query-rewrite for write-heavy workloads
4. **Validate Rules**: Ensure rules are logically consistent to avoid exploding the fact space

---

## Cookbook

Interactive tutorials to learn reasoning and inference:

- **[Reasoning and Inference](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/advanced/08_Reasoning_and_Inference.ipynb)**: Use logical reasoning to infer new knowledge from existing facts
  - **Topics**: Logic rules, inference engines, forward chaining, SPARQL reasoning, Rete algorithm
  - **Difficulty**: Advanced
  - **Use Cases**: Deriving new facts, query expansion, logical validation

## See Also

- [Ontology Module](ontology.md) - Source of schema-based rules
- [Triplet Store Module](triplet_store.md) - Backend for SPARQL reasoning
- [Modules Guide](../modules.md#quality-assurance) - Consistency checking overview
