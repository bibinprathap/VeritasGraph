# Export

> **Export knowledge graphs and data to multiple formats with W3C-compliant serialization.**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-file-export:{ .lg .middle } **Multi-Format Export**

    ---

    Support for 10+ export formats including RDF, JSON, CSV, GraphML

-   :material-database-export:{ .lg .middle } **Graph Databases**

    ---

    Direct export to Neo4j, ArangoDB, Memgraph with Cypher generation

-   :material-code-json:{ .lg .middle } **RDF Serialization**

    ---

    W3C-compliant formats: Turtle, RDF/XML, JSON-LD, N-Triples

-   :material-cog:{ .lg .middle } **Custom Serializers**

    ---

    Extensible serialization framework for custom formats

-   :material-flash:{ .lg .middle } **Batch Export**

    ---

    Efficient large-scale data export with streaming support

-   :material-file-multiple:{ .lg .middle } **Multiple Outputs**

    ---

    Export to Cytoscape.js, D3.js, Gephi, Graphviz formats

</div>

!!! tip "Choosing Export Format"
    - **Development**: Use Turtle for human-readable RDF
    - **APIs**: Use JSON-LD for web services
    - **Visualization**: Use GraphML or Cytoscape.js
    - **Databases**: Use Neo4j Cypher or CSV for bulk import

---

## ⚙️ Algorithms Used

### Serialization Algorithms

**RDF/XML Serialization**:
- **Standard**: W3C RDF/XML specification
- **Format**: XML-based RDF representation
- **Use case**: Interoperability with XML-based systems

**Turtle Serialization**:
- **Standard**: W3C Turtle specification
- **Format**: Compact RDF format with prefix compression
- **Use case**: Human-readable RDF representation

**JSON-LD Serialization**:
- **Standard**: W3C JSON-LD specification
- **Format**: JSON-based linked data with context
- **Use case**: Web APIs and JavaScript applications

**GraphML Generation**:
- **Format**: XML-based graph format
- **Use case**: Graph visualization tools (Gephi, Cytoscape)

**Cypher Query Generation**:
- **Format**: Neo4j query language
- **Use case**: Direct import into Neo4j graph database

### Export Optimization

**Streaming Export**:
- **Purpose**: Memory-efficient export for large graphs
- **How it works**: Processes data in chunks without loading entire graph into memory
- **Use case**: Exporting graphs with millions of nodes/edges

**Batch Processing**:
- **Purpose**: Efficient large-scale data export
- **How it works**: Chunked export with configurable batch sizes
- **Use case**: Exporting multiple graphs or large datasets

**Compression**:
- **Purpose**: Reduce file size for large exports
- **How it works**: GZIP compression for large exports
- **Use case**: Network transfer and storage optimization

**Incremental Export**:
- **Purpose**: Export only changed data
- **How it works**: Tracks changes and exports only modified entities/relationships
- **Use case**: Regular updates and synchronization

---

## Main Classes

### RDFExporter

Export knowledge graphs to RDF formats (Turtle, RDF/XML, JSON-LD, N-Triples).

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, filename, format)` `` | Export to RDF format | RDF serialization with format-specific encoding |
| `` `export_knowledge_graph(kg, filename, format)` `` | Export knowledge graph | Knowledge graph to RDF conversion |
| `` `serialize(graph, format)` `` | Serialize to string | In-memory RDF generation |
| `` `validate_rdf(rdf_data)` `` | Validate RDF syntax | RDF schema validation |

### RDFSerializer

RDF serialization engine for format conversion.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `serialize_to_turtle(rdf_data)` `` | Serialize to Turtle | Compact RDF format with prefix compression |
| `` `serialize_to_rdfxml(rdf_data)` `` | Serialize to RDF/XML | XML-based RDF format |
| `` `serialize_to_jsonld(rdf_data)` `` | Serialize to JSON-LD | JSON-based linked data format |

### RDFValidator

RDF validation engine for syntax and consistency checking.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `validate_rdf_syntax(rdf_data, format)` `` | Validate RDF syntax | Format-specific syntax validation |
| `` `check_rdf_consistency(rdf_data)` `` | Check consistency | Entity reference and structure validation |

### NamespaceManager

RDF namespace management and conflict resolution.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `extract_namespaces(rdf_data)` `` | Extract namespaces | Namespace discovery from RDF data |
| `` `generate_namespace_declarations(namespaces, format)` `` | Generate declarations | Format-specific namespace declaration |
| `` `resolve_conflicts(namespaces)` `` | Resolve conflicts | Prefix conflict resolution |

**Supported RDF Formats:**

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| **Turtle** | .ttl | Compact, human-readable | Development, debugging |
| **N-Triples** | .nt | Line-based, simple | Streaming, processing |
| **RDF/XML** | .rdf | XML-based, verbose | Legacy systems |
| **JSON-LD** | .jsonld | JSON with linked data | Web APIs, JavaScript |
| **N-Quads** | .nq | N-Triples with graphs | Named graphs |

**Example:**

```python
from veritasreason.export import RDFExporter

exporter = RDFExporter(
    base_uri="http://example.org/",
    namespaces={
        "ex": "http://example.org/",
        "foaf": "http://xmlns.com/foaf/0.1/"
    }
)

# Export to Turtle
exporter.export(
    graph=kg,
    filename="output.ttl",
    format="turtle"
)

# Export to JSON-LD
exporter.export(
    graph=kg,
    filename="output.jsonld",
    format="json-ld"
)
```

---

### JSONExporter

Export knowledge graphs to JSON formats including JSON-LD, Cytoscape.js, and D3.js.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, filename, format)` `` | Export to JSON | JSON serialization with schema |
| `` `export_nodes(graph)` `` | Export nodes only | Node extraction and serialization |
| `` `export_edges(graph)` `` | Export edges only | Edge extraction and serialization |
| `` `export_cytoscape(graph)` `` | Export Cytoscape.js format | Cytoscape JSON generation |
| `export_d3(graph)` | Export D3.js format | D3 force-directed graph format |

**JSON Formats:**

- **Standard JSON**: Simple node/edge lists
- **JSON-LD**: Linked data with @context
- **Cytoscape.js**: For Cytoscape visualization
- **D3.js**: For D3 force-directed graphs
- **Neo4j JSON**: Neo4j-compatible format

**Example:**

```python
from veritasreason.export import JSONExporter

exporter = JSONExporter()

# Standard JSON export
exporter.export(kg, "output.json", format="standard")

# JSON-LD export
exporter.export(kg, "output.jsonld", format="json-ld")

# Cytoscape format
exporter.export_cytoscape(kg, "cytoscape.json")
```

---

### GraphExporter

Export to graph visualization formats (GraphML, GEXF, DOT, Pajek).

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, filename, format)` `` | Export to graph format | Format-specific serialization |
| `` `to_graphml(graph, filename)` `` | Export to GraphML | XML-based graph format |
| `` `to_gexf(graph, filename)` `` | Export to GEXF | Gephi exchange format |
| `` `to_dot(graph, filename)` `` | Export to DOT | Graphviz format |
| `` `to_pajek(graph, filename)` `` | Export to Pajek | Pajek network format |

**Graph Formats:**

| Format | Tool | Use Case |
|--------|------|----------|
| **GraphML** | yEd, Gephi | General graph visualization |
| **GEXF** | Gephi | Network analysis |
| **DOT** | Graphviz | Diagram generation |
| **Pajek** | Pajek | Large network analysis |
| **GML** | Various | Graph Modeling Language |

**Example:**

```python
from veritasreason.export import GraphExporter

exporter = GraphExporter()

# Export to GraphML
exporter.to_graphml(kg, "graph.graphml")

# Export to DOT for Graphviz
exporter.to_dot(kg, "graph.dot")
```

---

### LPGExporter

Export to LPG (Labeled Property Graph) format for Neo4j, Memgraph, and similar databases.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(knowledge_graph, file_path)` `` | Export to LPG format | Cypher query generation |
| `` `export_knowledge_graph(kg, file_path)` `` | Export knowledge graph | Knowledge graph to Cypher conversion |
| `` `generate_cypher(kg)` `` | Generate Cypher queries | CREATE/MERGE statement generation |

**Cypher Generation:**
```cypher
// Node creation
CREATE (n:Person {name: "Steve Jobs", born: 1955})

// Relationship creation
MATCH (a:Person {name: "Steve Jobs"}), (b:Organization {name: "Apple Inc."})
CREATE (a)-[:FOUNDED]->(b)
```

**Example:**

```python
from veritasreason.export import LPGExporter

exporter = LPGExporter(batch_size=1000, include_indexes=True)

# Export to Cypher file
exporter.export_knowledge_graph(kg, "graph.cypher")

# Generate Cypher queries
cypher_queries = exporter.generate_cypher(kg)
print(cypher_queries)
```

---

### CSVExporter

Export to CSV format for spreadsheets and database imports.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export_nodes(graph, filename)` `` | Export nodes to CSV | Node flattening and CSV writing |
| `` `export_edges(graph, filename)` `` | Export edges to CSV | Edge list CSV generation |
| `` `export_combined(graph, prefix)` `` | Export nodes + edges | Separate CSV files |
| `` `flatten_properties(properties)` `` | Flatten nested properties | Recursive property flattening |

**CSV Formats:**
- **Nodes CSV**: id, label, properties (flattened)
- **Edges CSV**: source, target, type, properties
- **Neo4j Import Format**: Neo4j-compatible CSV

**Example:**

```python
from veritasreason.export import CSVExporter

exporter = CSVExporter()

# Export nodes and edges separately
exporter.export_nodes(kg, "nodes.csv")
exporter.export_edges(kg, "edges.csv")

# Or combined export
exporter.export_combined(kg, prefix="graph")
# Creates: graph_nodes.csv, graph_edges.csv
```

---

### VectorExporter

Export vector embeddings to various formats.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(vectors, filename, format)` `` | Export vectors | Format-specific vector serialization |
| `` `export_numpy(vectors, filename)` `` | Export to NumPy | .npy format |
| `` `export_hdf5(vectors, filename)` `` | Export to HDF5 | Hierarchical data format |
| `` `export_parquet(vectors, filename)` `` | Export to Parquet | Columnar storage format |

**Example:**

```python
from veritasreason.export import VectorExporter

exporter = VectorExporter(format="json", include_metadata=True)
exporter.export(vectors, "vectors.json")
```

---

### OWLExporter

Export ontologies to OWL format (OWL/XML, Turtle).

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(ontology, filename, format)` `` | Export ontology | OWL serialization |
| `` `export_classes(classes, filename)` `` | Export classes | Class definition export |
| `` `export_properties(properties, filename)` `` | Export properties | Property definition export |

**Example:**

```python
from veritasreason.export import OWLExporter

exporter = OWLExporter(ontology_uri="http://example.org/ontology#")
exporter.export(ontology, "ontology.owl", format="owl-xml")
```

---

### SemanticNetworkYAMLExporter

Export semantic networks to YAML format.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(semantic_network, filename)` `` | Export semantic network | YAML serialization |
| `` `export_semantic_network(semantic_network)` `` | Export to string | In-memory YAML generation |

**Example:**

```python
from veritasreason.export import SemanticNetworkYAMLExporter

exporter = SemanticNetworkYAMLExporter()
exporter.export(semantic_network, "network.yaml")
```

---

### YAMLSchemaExporter

Export ontology schemas to YAML format.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export_ontology_schema(ontology, filename)` `` | Export ontology schema | YAML schema serialization |

**Example:**

```python
from veritasreason.export import YAMLSchemaExporter

exporter = YAMLSchemaExporter()
exporter.export_ontology_schema(schema, "schema.yaml")
```

---

### ReportGenerator

Generate reports in multiple formats (HTML, Markdown, JSON, Text).

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `generate_report(data, filename, format)` `` | Generate report | Template-based report generation |
| `` `generate_quality_report(metrics, filename, format)` `` | Generate quality report | Quality metrics aggregation |

**Example:**

```python
from veritasreason.export import ReportGenerator

generator = ReportGenerator(format="html", include_charts=True)
generator.generate_report(data, "report.html")
```

---

### MethodRegistry

Registry for custom export methods.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `register(task, name, method_func)` `` | Register method | Dictionary-based registration |
| `` `get(task, name)` `` | Get method | Hash-based lookup |
| `` `list_all(task)` `` | List methods | Method discovery |
| `` `unregister(task, name)` `` | Unregister method | Method removal |
| `` `clear(task)` `` | Clear methods | Registry cleanup |

**Global Instance:**
- `method_registry`: Global method registry instance

**Example:**

```python
from veritasreason.export import method_registry

method_registry.register("json", "custom_method", custom_json_export)
method = method_registry.get("json", "custom_method")
all_methods = method_registry.list_all()
```

---

### ExportConfig

Configuration manager for export module.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `set(key, value)` `` | Set configuration | Configuration storage |
| `` `get(key, default)` `` | Get configuration | Configuration retrieval |
| `` `set_method_config(task, **config)` `` | Set method config | Method-specific configuration |
| `` `get_method_config(task)` `` | Get method config | Method configuration retrieval |

**Global Instance:**
- `export_config`: Global export configuration instance

**Example:**

```python
from veritasreason.export.config import export_config, ExportConfig

# Using global instance
export_config.set("default_format", "json")
format = export_config.get("default_format", default="json")

# Create custom instance
config = ExportConfig(config_file="config.yaml")
```

---

## Convenience Functions

### Export Functions

| Function | Description | Format |
|----------|-------------|--------|
| `` `export_rdf(data, file_path, format)` `` | Export to RDF | turtle, rdfxml, jsonld, ntriples, n3 |
| `` `export_json(data, file_path, format)` `` | Export to JSON | json, json-ld |
| `` `export_csv(data, file_path)` `` | Export to CSV | csv |
| `` `export_graph(graph_data, file_path, format)` `` | Export to graph format | graphml, gexf, dot |
| `` `export_yaml(data, file_path, method)` `` | Export to YAML | semantic_network, schema |
| `` `export_owl(ontology, file_path, format)` `` | Export to OWL | owl-xml, turtle |
| `` `export_vector(vectors, file_path, format)` `` | Export vectors | json, numpy, binary, faiss |
| `` `export_lpg(kg, file_path, method)` `` | Export to LPG | cypher, lpg |
| `` `generate_report(data, file_path, format)` `` | Generate report | html, markdown, json, text |

### Registry Functions

| Function | Description |
|----------|-------------|
| `` `get_export_method(task, name)` `` | Get registered export method |
| `` `list_available_methods(task)` `` | List all available methods |

**Example:**

```python
from veritasreason.export.methods import (
    export_rdf, export_json, export_csv, export_graph,
    export_yaml, export_owl, export_vector, export_lpg,
    generate_report, get_export_method, list_available_methods
)

# Export functions
export_rdf(kg, "output.ttl", format="turtle")
export_json(kg, "output.json", format="json")
export_lpg(kg, "graph.cypher", method="cypher")

# Registry functions
method = get_export_method("json", "custom_method")
all_methods = list_available_methods()
```

---

## Configuration

```yaml
# config.yaml - Export Configuration

export:
  rdf:
    default_format: turtle
    base_uri: "http://example.org/"
    include_provenance: true
    validate_output: true
    
  json:
    pretty_print: true
    indent: 2
    ensure_ascii: false
    
  graph:
    include_metadata: true
    export_properties: true
    
  neo4j:
    batch_size: 1000
    create_indexes: true
    create_constraints: true
    
  csv:
    delimiter: ","
    quote_char: "\""
    encoding: "utf-8"
    include_header: true
```

---

## Performance Characteristics

### Export Speed

| Format | Small Graph | Large Graph | Compression |
|--------|-------------|-------------|-------------|
| JSON | Fast | Medium | Good with gzip |
| RDF/XML | Medium | Slow | Poor |
| Turtle | Fast | Fast | Good |
| CSV | Very Fast | Very Fast | Excellent |
| Neo4j | Medium | Medium | N/A |

### Memory Usage

- **Streaming Export**: Constant memory usage
- **Batch Export**: Memory proportional to batch size
- **Full Export**: Memory proportional to graph size

---

## See Also

- [Knowledge Graph Module](kg.md) - Build graphs
- [Visualization Module](visualization.md) - Visualize exported graphs
- [Core Module](core.md) - Framework orchestration

## Cookbook

Interactive tutorials to learn export capabilities:

- **[Export](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/15_Export.ipynb)**: Export knowledge graphs to various formats
  - **Topics**: RDF, JSON, CSV, OWL export, format conversion
  - **Difficulty**: Intermediate
  - **Use Cases**: Data export, format conversion, interoperability

- **[Multi-Format Export](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/advanced/05_Multi_Format_Export.ipynb)**: Exporting to RDF, OWL, JSON-LD, and NetworkX formats
  - **Topics**: Serialization, interoperability, multiple formats, batch export
  - **Difficulty**: Intermediate
  - **Use Cases**: Multi-format export, data interoperability

---

## Algorithms Used

### Serialization Algorithms
- **RDF/XML Serialization**: W3C RDF/XML specification
- **Turtle Serialization**: Compact RDF format with prefix compression
- **JSON-LD Serialization**: JSON-based linked data with context
- **GraphML Generation**: XML-based graph format
- **Cypher Query Generation**: Neo4j query language generation

### Export Optimization
- **Streaming Export**: Memory-efficient export for large graphs
- **Batch Processing**: Chunked export with configurable batch sizes
- **Compression**: GZIP compression for large exports
- **Incremental Export**: Export only changed data

---

## Main Classes

### RDFExporter


**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, filename, format)` `` | Export to RDF format | RDF serialization with format-specific encoding |
| `` `serialize(graph, format)` `` | Serialize to string | In-memory RDF generation |
| `` `validate(rdf_data)` `` | Validate RDF syntax | RDF schema validation |
| `` `add_namespace(prefix, uri)` `` | Add namespace | Prefix registration |
| `` `set_base_uri(uri)` `` | Set base URI | Base URI configuration |

**Supported RDF Formats:**

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| **Turtle** | .ttl | Compact, human-readable | Development, debugging |
| **N-Triples** | .nt | Line-based, simple | Streaming, processing |
| **RDF/XML** | .rdf | XML-based, verbose | Legacy systems |
| **JSON-LD** | .jsonld | JSON with linked data | Web APIs, JavaScript |
| **N-Quads** | .nq | N-Triples with graphs | Named graphs |

**Example:**

```python
from veritasreason.export import RDFExporter

exporter = RDFExporter(
    base_uri="http://example.org/",
    namespaces={
        "ex": "http://example.org/",
        "foaf": "http://xmlns.com/foaf/0.1/"
    }
)

# Export to Turtle
exporter.export(
    graph=kg,
    filename="output.ttl",
    format="turtle"
)

# Export to JSON-LD
exporter.export(
    graph=kg,
    filename="output.jsonld",
    format="json-ld"
)
```

---

### JSONExporter


**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, filename, format)` `` | Export to JSON | JSON serialization with schema |
| `` `export_nodes(graph)` `` | Export nodes only | Node extraction and serialization |
| `` `export_edges(graph)` `` | Export edges only | Edge extraction and serialization |
| `` `export_cytoscape(graph)` `` | Export Cytoscape.js format | Cytoscape JSON generation |
| `export_d3(graph)` | Export D3.js format | D3 force-directed graph format |

**JSON Formats:**

- **Standard JSON**: Simple node/edge lists
- **JSON-LD**: Linked data with @context
- **Cytoscape.js**: For Cytoscape visualization
- **D3.js**: For D3 force-directed graphs
- **Neo4j JSON**: Neo4j-compatible format

**Example:**

```python
from veritasreason.export import JSONExporter

exporter = JSONExporter()

# Standard JSON export
exporter.export(kg, "output.json", format="standard")

# JSON-LD export
exporter.export(kg, "output.jsonld", format="json-ld")

# Cytoscape format
exporter.export_cytoscape(kg, "cytoscape.json")
```

---

### GraphExporter


**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, filename, format)` `` | Export to graph format | Format-specific serialization |
| `` `to_graphml(graph, filename)` `` | Export to GraphML | XML-based graph format |
| `` `to_gexf(graph, filename)` `` | Export to GEXF | Gephi exchange format |
| `` `to_dot(graph, filename)` `` | Export to DOT | Graphviz format |
| `` `to_pajek(graph, filename)` `` | Export to Pajek | Pajek network format |

**Graph Formats:**

| Format | Tool | Use Case |
|--------|------|----------|
| **GraphML** | yEd, Gephi | General graph visualization |
| **GEXF** | Gephi | Network analysis |
| **DOT** | Graphviz | Diagram generation |
| **Pajek** | Pajek | Large network analysis |
| **GML** | Various | Graph Modeling Language |

**Example:**

```python
from veritasreason.export import GraphExporter

exporter = GraphExporter()

# Export to GraphML
exporter.to_graphml(kg, "graph.graphml")

# Export to DOT for Graphviz
exporter.to_dot(kg, "graph.dot")
```

---

### Neo4jExporter


**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(graph, uri, username, password)` `` | Export to Neo4j | Cypher query execution |
| `` `generate_cypher(graph)` `` | Generate Cypher queries | CREATE/MERGE statement generation |
| `` `batch_import(graph, batch_size)` `` | Batch import | Chunked Cypher execution |
| `` `create_indexes(properties)` `` | Create indexes | Index creation for performance |
| `` `create_constraints(constraints)` `` | Create constraints | Uniqueness constraint creation |

**Cypher Generation:**
```cypher
// Node creation
CREATE (n:Person {name: "Steve Jobs", born: 1955})

// Relationship creation
MATCH (a:Person {name: "Steve Jobs"}), (b:Organization {name: "Apple Inc."})
CREATE (a)-[:FOUNDED]->(b)
```

**Example:**

```python
from veritasreason.export import Neo4jExporter

exporter = Neo4jExporter()

# Direct export to Neo4j
exporter.export(
    graph=kg,
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# Generate Cypher queries
cypher_queries = exporter.generate_cypher(kg)
print(cypher_queries)
```

---

### CSVExporter


**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export_nodes(graph, filename)` `` | Export nodes to CSV | Node flattening and CSV writing |
| `` `export_edges(graph, filename)` `` | Export edges to CSV | Edge list CSV generation |
| `` `export_combined(graph, prefix)` `` | Export nodes + edges | Separate CSV files |
| `` `flatten_properties(properties)` `` | Flatten nested properties | Recursive property flattening |

**CSV Formats:**
- **Nodes CSV**: id, label, properties (flattened)
- **Edges CSV**: source, target, type, properties
- **Neo4j Import Format**: Neo4j-compatible CSV

**Example:**

```python
from veritasreason.export import CSVExporter

exporter = CSVExporter()

# Export nodes and edges separately
exporter.export_nodes(kg, "nodes.csv")
exporter.export_edges(kg, "edges.csv")

# Or combined export
exporter.export_combined(kg, prefix="graph")
# Creates: graph_nodes.csv, graph_edges.csv
```

---

### VectorExporter


**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `` `export(embeddings, filename, format)` `` | Export vectors | Format-specific vector serialization |
| `` `export_numpy(embeddings, filename)` `` | Export to NumPy | .npy format |
| `` `export_hdf5(embeddings, filename)` `` | Export to HDF5 | Hierarchical data format |
| `` `export_parquet(embeddings, filename)` `` | Export to Parquet | Columnar storage format |

---

## Configuration

```yaml
# config.yaml - Export Configuration

export:
  rdf:
    default_format: turtle
    base_uri: "http://example.org/"
    include_provenance: true
    validate_output: true
    
  json:
    pretty_print: true
    indent: 2
    ensure_ascii: false
    
  graph:
    include_metadata: true
    export_properties: true
    
  neo4j:
    batch_size: 1000
    create_indexes: true
    create_constraints: true
    
  csv:
    delimiter: ","
    quote_char: "\""
    encoding: "utf-8"
    include_header: true
```

---

## Performance Characteristics

### Export Speed

| Format | Small Graph | Large Graph | Compression |
|--------|-------------|-------------|-------------|
| JSON | Fast | Medium | Good with gzip |
| RDF/XML | Medium | Slow | Poor |
| Turtle | Fast | Fast | Good |
| CSV | Very Fast | Very Fast | Excellent |
| Neo4j | Medium | Medium | N/A |

### Memory Usage

- **Streaming Export**: Constant memory usage
- **Batch Export**: Memory proportional to batch size
- **Full Export**: Memory proportional to graph size

---

## See Also

- [Knowledge Graph Module](kg.md) - Build graphs
- [Visualization Module](visualization.md) - Visualize exported graphs
- [Core Module](core.md) - Framework orchestration
