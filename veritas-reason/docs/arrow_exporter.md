# Apache Arrow Exporter

## Overview

The Apache Arrow exporter provides high-performance columnar data export for VeritasReason's knowledge graphs, entities, and relationships. It uses explicit schemas (no inference) and writes Arrow IPC files (.arrow) that are compatible with Pandas and DuckDB.

## Features

- **Explicit Schemas**: Pre-defined schemas for entities and relationships (no inference)
- **Columnar Format**: Efficient storage and fast analytics
- **Metadata Support**: Converts metadata dictionaries to Arrow struct fields
- **Field Normalization**: Handles various entity and relationship field name variations
- **Progress Tracking**: Integrated progress monitoring
- **Error Handling**: Structured error handling with detailed logging
- **Pandas/DuckDB Compatible**: Direct conversion to DataFrames and SQL queries

## Installation

The Arrow exporter requires PyArrow:

```bash
pip install pyarrow
```

## Usage

### Basic Usage

```python
from veritasreason.export import ArrowExporter

# Initialize exporter
exporter = ArrowExporter()

# Export entities
entities = [
    {"id": "e1", "text": "Alice", "type": "Person", "confidence": 0.95},
    {"id": "e2", "text": "Acme Corp", "type": "Organization", "confidence": 0.88}
]
exporter.export_entities(entities, "entities.arrow")

# Export relationships
relationships = [
    {"id": "r1", "source_id": "e1", "target_id": "e2", "type": "WORKS_FOR"}
]
exporter.export_relationships(relationships, "relationships.arrow")

# Export knowledge graph
knowledge_graph = {
    "entities": entities,
    "relationships": relationships
}
exporter.export_knowledge_graph(knowledge_graph, "kg_base")
# Creates: kg_base_entities.arrow, kg_base_relationships.arrow
```

### Using Convenience Function

```python
from veritasreason.export import export_arrow

# Simple export
export_arrow(entities, "entities.arrow")

# Export multiple types
data = {
    "entities": entities,
    "relationships": relationships
}
export_arrow(data, "output_base")
```

### With Compression

```python
# Use LZ4 compression
exporter = ArrowExporter(compression="lz4")
exporter.export_entities(entities, "entities_compressed.arrow")
```

## Schemas

### Entity Schema

```python
ENTITY_SCHEMA = pa.schema([
    pa.field("id", pa.string(), nullable=False),
    pa.field("text", pa.string(), nullable=True),
    pa.field("type", pa.string(), nullable=True),
    pa.field("confidence", pa.float64(), nullable=True),
    pa.field("start", pa.int64(), nullable=True),
    pa.field("end", pa.int64(), nullable=True),
    pa.field("metadata", pa.struct([
        pa.field("keys", pa.list_(pa.string())),
        pa.field("values", pa.list_(pa.string()))
    ]), nullable=True),
])
```

### Relationship Schema

```python
RELATIONSHIP_SCHEMA = pa.schema([
    pa.field("id", pa.string(), nullable=False),
    pa.field("source_id", pa.string(), nullable=False),
    pa.field("target_id", pa.string(), nullable=False),
    pa.field("type", pa.string(), nullable=True),
    pa.field("confidence", pa.float64(), nullable=True),
    pa.field("metadata", pa.struct([
        pa.field("keys", pa.list_(pa.string())),
        pa.field("values", pa.list_(pa.string()))
    ]), nullable=True),
])
```

## Field Normalization

The exporter automatically normalizes field names:

**Entities:**
- `text`, `label`, `name` → `text`
- `type`, `entity_type` → `type`
- `id`, `entity_id` → `id`
- `start`, `start_offset` → `start`
- `end`, `end_offset` → `end`

**Relationships:**
- `source`, `source_id` → `source_id`
- `target`, `target_id` → `target_id`
- `type`, `relationship_type` → `type`

## Reading Arrow Files

### With PyArrow

```python
import pyarrow as pa
import pyarrow.ipc as ipc

with pa.OSFile("entities.arrow", 'rb') as source:
    with ipc.open_file(source) as reader:
        table = reader.read_all()
        print(table.schema)
        print(table.to_pandas())
```

### With Pandas

```python
import pandas as pd
import pyarrow.ipc as ipc

with ipc.open_file("entities.arrow") as reader:
    df = reader.read_all().to_pandas()
    print(df)
```

### With DuckDB

```python
import duckdb

# Query Arrow file directly
result = duckdb.query("SELECT * FROM 'entities.arrow' WHERE type = 'Person'")
print(result.df())
```

## Methods

### `export(data, file_path, schema=None, **options)`

Generic export method that handles both single and multiple files.

**Parameters:**
- `data`: List of dicts or dict with list values
- `file_path`: Output file path (base path for dict exports)
- `schema`: Optional Arrow schema (auto-detected if not provided)
- `**options`: Additional options

### `export_entities(entities, file_path, **options)`

Export entities to Arrow IPC file with normalization.

**Parameters:**
- `entities`: List of entity dictionaries
- `file_path`: Output Arrow file path
- `**options`: Additional options

### `export_relationships(relationships, file_path, **options)`

Export relationships to Arrow IPC file with normalization.

**Parameters:**
- `relationships`: List of relationship dictionaries
- `file_path`: Output Arrow file path
- `**options`: Additional options

### `export_knowledge_graph(knowledge_graph, base_path, **options)`

Export knowledge graph to multiple Arrow files.

**Parameters:**
- `knowledge_graph`: Knowledge graph dictionary with 'entities' and 'relationships'
- `base_path`: Base path for output files (without extension)
- `**options`: Additional options

## Examples

See `examples/arrow_export_example.py` for comprehensive usage examples.

## Testing

Run the test suite:

```bash
# All Arrow exporter tests
pytest tests/test_arrow_exporter.py -v

# Integration tests
pytest tests/test_export_module.py::TestExportModule::test_arrow_exporter -v
```

## Performance Benefits

- **Columnar Storage**: Faster analytics on specific columns
- **Compression**: Smaller file sizes (especially with LZ4/ZSTD)
- **Zero-Copy**: Memory-efficient data transfer
- **Cross-Language**: Works with Python, R, Julia, JavaScript, and more
- **SQL Queries**: Direct querying with DuckDB without loading into memory

## Comparison with Other Formats

| Feature | Arrow | CSV | JSON |
|---------|-------|-----|------|
| Type Safety | ✓ | ✗ | ✗ |
| Compression | ✓ | ✗ | ✗ |
| Schema Validation | ✓ | ✗ | ✗ |
| Pandas Compatible | ✓ | ✓ | ✓ |
| DuckDB Native | ✓ | ✓ | ✗ |
| Binary Format | ✓ | ✗ | ✗ |
| Human Readable | ✗ | ✓ | ✓ |

## Architecture

The Arrow exporter follows VeritasReason's export architecture:

1. **Normalization**: Field names are normalized to consistent format
2. **Schema Application**: Explicit schemas ensure type safety
3. **Metadata Conversion**: Dicts converted to Arrow struct fields
4. **Progress Tracking**: Integrated with VeritasReason's progress tracker
5. **Error Handling**: Structured exceptions with detailed messages

## Contributing

When contributing to the Arrow exporter:

1. Maintain explicit schemas (no inference)
2. Follow existing code style and patterns
3. Add comprehensive tests for new features
4. Update this documentation
5. Ensure Pandas/DuckDB compatibility

## License

MIT License - See LICENSE file for details.

## Author

VeritasReason Contributors
