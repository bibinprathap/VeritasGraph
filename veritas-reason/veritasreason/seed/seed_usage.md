# Seed Data System Module Usage Guide

This comprehensive guide demonstrates how to use the seed data system module for loading seed data from multiple sources, creating foundation knowledge graphs, validating data quality, integrating with extracted data, and exporting seed data.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Seed Data Loading](#seed-data-loading)
3. [Foundation Graph Creation](#foundation-graph-creation)
4. [Data Integration](#data-integration)
5. [Quality Validation](#quality-validation)
6. [Version Management](#version-management)
7. [Export Operations](#export-operations)
8. [Algorithms and Methods](#algorithms-and-methods)
9. [Configuration](#configuration)
10. [Advanced Examples](#advanced-examples)

## Basic Usage

The Seed module adheres to a class-based design for explicit control and scalability.

```python
from veritasreason.seed import SeedDataManager, SeedDataSource

# Create seed data manager instance
manager = SeedDataManager()

# Register and load seed data
manager.register_source("entities", "json", "data/entities.json", entity_type="Person")
records = manager.load_source("entities")

# Create foundation graph
foundation = manager.create_foundation_graph()
```

## Seed Data Loading

### Loading from CSV

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Load from CSV file
records = manager.load_from_csv(
    "data/entities.csv",
    entity_type="Person"
)

# Load from CSV with custom delimiter
records_pipe = manager.load_from_csv(
    "data/entities_pipe.csv",
    delimiter="|"
)

# Load from CSV with auto-detection (supported for common delimiters like ;, \t, etc.)
records_auto = manager.load_from_csv(
    "data/entities_semicolon.csv"
)

print(f"Loaded {len(records)} records from CSV")

# CSV should have columns like: id, name, type, etc.
for record in records[:5]:
    print(f"Entity: {record.get('id')} - {record.get('name')}")
```

### Loading from JSON

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Load from JSON file
records = manager.load_from_json(
    "data/entities.json",
    entity_type="Person"
)

print(f"Loaded {len(records)} records from JSON")

# JSON can be:
# - List: [{"id": "1", "name": "John"}, ...]
# - Dict with 'entities': {"entities": [...]}
# - Dict with 'data': {"data": [...]}
# - Dict with 'records': {"records": [...]}
#
# Note: Ensure JSON seed files follow these supported top-level structures.
# Unsupported structures will trigger a warning and may be loaded as a single record.
```

### Loading from Database

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Load from database using SQL query
records = manager.load_from_database(
    connection_string="postgresql://user:pass@localhost/db",
    query="SELECT id, name, type FROM entities WHERE verified = true",
    entity_type="Person"
)

# Or load entire table
records = manager.load_from_database(
    connection_string="postgresql://user:pass@localhost/db",
    table_name="entities",
    entity_type="Person"
)

print(f"Loaded {len(records)} records from database")
```

### Loading from API

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Load from API
records = manager.load_from_api(
    api_url="https://api.example.com",
    endpoint="entities",
    api_key="your-api-key",
    entity_type="Person"
)

print(f"Loaded {len(records)} records from API")

# API response can be:
# - List: [{"id": "1", "name": "John"}, ...]
# - Dict with 'entities', 'data', 'results', or 'items' keys
```

### Registering Sources

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register CSV source
manager.register_source(
    name="people",
    format="csv",
    location="data/people.csv",
    entity_type="Person",
    verified=True
)

# Register JSON source
manager.register_source(
    name="companies",
    format="json",
    location="data/companies.json",
    entity_type="Organization",
    verified=True
)

# Register database source
manager.register_source(
    name="locations",
    format="database",
    location="postgresql://user:pass@localhost/db",
    entity_type="Location",
    verified=True
)

# Register API source
manager.register_source(
    name="external_entities",
    format="api",
    location="https://api.example.com",
    entity_type="Entity",
    verified=False
)
```

### Loading Registered Sources

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register sources
manager.register_source("people", "json", "data/people.json", entity_type="Person")
manager.register_source("companies", "csv", "data/companies.csv", entity_type="Organization")

# Load from registered source
people_records = manager.load_source("people")
companies_records = manager.load_source("companies")

print(f"Loaded {len(people_records)} people")
print(f"Loaded {len(companies_records)} companies")
```

## Foundation Graph Creation

### Basic Foundation Graph

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register multiple sources
manager.register_source("people", "json", "data/people.json", entity_type="Person")
manager.register_source("companies", "json", "data/companies.json", entity_type="Organization")
manager.register_source("relationships", "json", "data/relationships.json", relationship_type="worksFor")

# Create foundation graph from all sources
foundation = manager.create_foundation_graph()

print(f"Entities: {len(foundation['entities'])}")
print(f"Relationships: {len(foundation['relationships'])}")
print(f"Sources: {foundation['metadata']['source_count']}")
print(f"Verified: {foundation['metadata']['verified']}")
```

### Foundation Graph with Schema Validation

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register sources
manager.register_source("entities", "json", "data/entities.json")

# Create foundation with schema template validation
schema_template = {
    "required_entity_fields": ["id", "name", "type"],
    "required_relationship_fields": ["source_id", "target_id", "type"]
}

foundation = manager.create_foundation_graph(schema_template=schema_template)
```

### Entity and Relationship Extraction

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Load records
records = manager.load_from_json("data/mixed_data.json")

# Records are automatically converted to entities/relationships
# Entities: records with 'id' or 'entity_type'
# Relationships: records with 'source_id' and 'target_id' or 'relationship_type'

foundation = manager.create_foundation_graph()

# Access entities
for entity in foundation["entities"]:
    print(f"Entity: {entity['id']} ({entity['type']})")

# Access relationships
for rel in foundation["relationships"]:
    print(f"Relationship: {rel['source_id']} -> {rel['target_id']} ({rel['type']})")
```

## Data Integration

### Seed-First Merge Strategy

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Create seed data
seed_data = {
    "entities": [
        {"id": "1", "name": "John", "type": "Person", "verified": True},
        {"id": "2", "name": "Acme Corp", "type": "Organization", "verified": True}
    ],
    "relationships": [
        {"source_id": "1", "target_id": "2", "type": "worksFor", "verified": True}
    ]
}

# Extracted data (may have duplicates or conflicts)
extracted_data = {
    "entities": [
        {"id": "1", "name": "John Doe", "type": "Person", "age": 30},
        {"id": "3", "name": "Jane", "type": "Person"}
    ],
    "relationships": [
        {"source_id": "1", "target_id": "2", "type": "worksFor", "start_date": "2020-01-01"}
    ]
}

# Integrate with seed-first strategy (seed takes precedence)
integrated = manager.integrate_with_extracted(
    seed_data,
    extracted_data,
    merge_strategy="seed_first"
)

# Result: seed entities kept, extracted entities added if not in seed
print(f"Integrated entities: {len(integrated['entities'])}")
```

### Extracted-First Merge Strategy

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Integrate with extracted-first strategy (extracted takes precedence)
integrated = manager.integrate_with_extracted(
    seed_data,
    extracted_data,
    merge_strategy="extracted_first"
)

# Result: extracted entities kept, seed entities added if not in extracted
print(f"Integrated entities: {len(integrated['entities'])}")
```

### Merge Strategy

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Integrate with merge strategy (merge properties, seed takes precedence for conflicts)
integrated = manager.integrate_with_extracted(
    seed_data,
    extracted_data,
    merge_strategy="merge"
)

# Result: properties merged, seed values take precedence for conflicts
# Entity 1: {"id": "1", "name": "John", "type": "Person", "verified": True, "age": 30}
# (name from seed, age from extracted)
```

### Relationship Merging

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Relationships are merged based on (source_id, target_id, type) triple
integrated = manager.integrate_with_extracted(
    seed_data,
    extracted_data,
    merge_strategy="merge"
)

# Duplicate relationships (same source, target, type) are handled
# Seed relationships take precedence in seed_first strategy
```

## Quality Validation

### Basic Quality Validation

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Create foundation graph
foundation = manager.create_foundation_graph()

# Validate quality
validation = manager.validate_quality(foundation)

if validation["valid"]:
    print("Seed data is valid!")
else:
    print(f"Found {len(validation['errors'])} errors:")
    for error in validation["errors"]:
        print(f"  - {error}")

if validation["warnings"]:
    print(f"Found {len(validation['warnings'])} warnings:")
    for warning in validation["warnings"]:
        print(f"  - {warning}")
```

### Validation Metrics

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

foundation = manager.create_foundation_graph()
validation = manager.validate_quality(foundation)

# Access metrics
metrics = validation["metrics"]
print(f"Entity count: {metrics['entity_count']}")
print(f"Relationship count: {metrics['relationship_count']}")
print(f"Unique entity IDs: {metrics['unique_entity_ids']}")
print(f"Duplicate entities: {metrics['duplicate_entities']}")
```

### Custom Validation Options

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

foundation = manager.create_foundation_graph()

# Custom validation options
validation = manager.validate_quality(
    foundation,
    check_required_fields=True,
    check_types=True,
    check_consistency=True
)

print(f"Validation result: {validation['valid']}")
```

### Required Field Validation

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

foundation = manager.create_foundation_graph()

# Validation checks for:
# - Entity 'id' field (required)
# - Entity 'type' field (warning if missing)
# - Relationship 'source_id' and 'target_id' fields (required)
# - Relationship 'type' field (warning if missing)

validation = manager.validate_quality(foundation)

# Check specific validations
if not validation["valid"]:
    for error in validation["errors"]:
        if "missing" in error.lower():
            print(f"Missing field error: {error}")
```

## Version Management

### Source Versioning

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register source with version
manager.register_source(
    name="entities",
    format="json",
    location="data/entities.json",
    version="1.0"
)

# Versions are tracked automatically
print(f"Source versions: {manager.versions.get('entities', [])}")
```

### Version History

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register multiple versions
manager.register_source("entities", "json", "data/entities_v1.json", version="1.0")
manager.register_source("entities", "json", "data/entities_v2.json", version="2.0")

# Access version history
versions = manager.versions.get("entities", [])
print(f"Version history: {versions}")
```

## Export Operations

### Export to JSON

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Create foundation graph
foundation = manager.create_foundation_graph()

# Export to JSON
manager.export_seed_data("output/seed_data.json", format="json")

# JSON structure:
# {
#   "entities": [...],
#   "relationships": [...],
#   "metadata": {
#     "exported_at": "2024-01-01T00:00:00",
#     ...
#   }
# }
```

### Export to CSV

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

foundation = manager.create_foundation_graph()

# Export to CSV (creates separate files for entities and relationships)
manager.export_seed_data("output/seed_data", format="csv")

# Creates:
# - output/seed_data_entities.csv
# - output/seed_data_relationships.csv
```

### Export with Custom Data

```python
from veritasreason.seed import SeedDataManager, SeedData

manager = SeedDataManager()

# Create custom seed data
custom_data = SeedData(
    entities=[
        {"id": "1", "name": "John", "type": "Person"},
        {"id": "2", "name": "Jane", "type": "Person"}
    ],
    relationships=[
        {"source_id": "1", "target_id": "2", "type": "knows"}
    ],
    metadata={"source": "manual", "created_at": "2024-01-01"}
)

# Set seed data
manager.seed_data = custom_data

# Export
manager.export_seed_data("output/custom_seed.json", format="json")
```

## Algorithms and Methods

### Seed Data Loading Algorithms

#### CSV Loading
**Algorithm**: Row-by-row CSV processing with metadata injection

1. **File Reading**: Open CSV file with UTF-8 encoding
2. **Delimiter Detection**: 
   - Use provided delimiter if specified
   - If not, attempt to auto-detect delimiter using `csv.Sniffer`
   - Fallback to comma (`,`) if detection fails
3. **Header Detection**: Use csv.DictReader() for automatic header detection
4. **Row Processing**: Iterate through rows, convert to dictionaries
5. **Data Cleaning**: Remove empty values, clean whitespace
6. **Metadata Injection**: Add entity_type, relationship_type, source metadata
7. **Type Conversion**: Convert string values to appropriate types

**Time Complexity**: O(n) where n = number of rows
**Space Complexity**: O(n) for records storage

```python
# CSV loading example
records = manager.load_from_csv("data.csv", entity_type="Person")
# Each row becomes a dictionary with metadata
```

#### JSON Loading
**Algorithm**: Structure-aware JSON parsing with format detection

1. **File Reading**: Read JSON file using json.load()
2. **Structure Detection**: Detect structure type (list, dict with keys, single object)
3. **Data Extraction**: Extract records based on structure:
   - List: Use directly
   - Dict: Try 'entities', 'data', 'records' keys
   - Single object: Wrap in list
4. **Metadata Injection**: Add entity_type, relationship_type, source
5. **Error Handling**: Handle parsing errors gracefully

**Time Complexity**: O(n) where n = number of records
**Space Complexity**: O(n) for records storage

```python
# JSON loading example
records = manager.load_from_json("data.json", entity_type="Person")
# Handles various JSON structures automatically
```

#### Database Loading
**Algorithm**: SQL query execution with result processing

1. **Connection**: Connect to database using DBIngestor
2. **Query Execution**: Execute SQL query or export table
3. **Result Processing**: Convert result set to list of dictionaries
4. **Row Conversion**: Map database rows to dictionary format
5. **Metadata Injection**: Add entity_type, relationship_type, source

**Time Complexity**: O(n) where n = number of rows
**Space Complexity**: O(n) for records storage

```python
# Database loading example
records = manager.load_from_database(
    "postgresql://...",
    query="SELECT * FROM entities"
)
```

#### API Loading
**Algorithm**: HTTP request with JSON response parsing

1. **URL Construction**: Build full URL from base and endpoint
2. **Authentication**: Add API key as Bearer token if provided
3. **HTTP Request**: Make GET request with headers
4. **Response Parsing**: Parse JSON response
5. **Structure Detection**: Detect response structure (list, dict with keys)
6. **Data Extraction**: Extract records based on structure
7. **Metadata Injection**: Add entity_type, relationship_type, source

**Time Complexity**: O(1) for request + O(n) for parsing
**Space Complexity**: O(n) for records storage

```python
# API loading example
records = manager.load_from_api(
    "https://api.example.com",
    endpoint="entities",
    api_key="key"
)
```

### Foundation Graph Creation Algorithms

#### Multi-Source Aggregation
**Algorithm**: Aggregate data from multiple sources

1. **Source Iteration**: Iterate through all registered sources
2. **Source Loading**: Load data from each source using appropriate loader
3. **Error Handling**: Continue if source fails, log warning
4. **Data Aggregation**: Collect entities and relationships from all sources
5. **Metadata Collection**: Aggregate metadata from all sources

**Time Complexity**: O(s × n) where s = sources, n = records per source
**Space Complexity**: O(n) for aggregated data

```python
# Multi-source aggregation
foundation = manager.create_foundation_graph()
# Aggregates from all registered sources
```

#### Entity Extraction
**Algorithm**: Convert records to entity format

1. **Record Filtering**: Filter records with 'id' or 'entity_type'
2. **Field Mapping**: Map record fields to entity fields:
   - id: from 'id'
   - text: from 'text', 'name', or 'label'
   - type: from 'entity_type' or 'type'
   - confidence: from 'confidence' (default 1.0)
3. **Metadata Preservation**: Preserve other fields as metadata
4. **Entity Creation**: Create standardized entity dictionary

**Time Complexity**: O(n) where n = records
**Space Complexity**: O(n) for entities

```python
# Entity extraction
entity = manager._record_to_entity(record)
# Converts: {"id": "1", "name": "John"} -> {"id": "1", "text": "John", "type": "UNKNOWN", ...}
```

#### Relationship Extraction
**Algorithm**: Convert records to relationship format

1. **Record Filtering**: Filter records with 'source_id'/'target_id' or 'relationship_type'
2. **Field Mapping**: Map record fields to relationship fields:
   - id: from 'id' or generate from source_id_target_id
   - source_id: from 'source_id'
   - target_id: from 'target_id'
   - type: from 'relationship_type' or 'type'
   - confidence: from 'confidence' (default 1.0)
3. **Metadata Preservation**: Preserve other fields as metadata
4. **Relationship Creation**: Create standardized relationship dictionary

**Time Complexity**: O(n) where n = records
**Space Complexity**: O(n) for relationships

### Data Integration Algorithms

#### Merge Strategies

**Seed-First Strategy**:
1. Start with seed entities/relationships
2. Add extracted entities/relationships that don't exist in seed
3. Seed data takes precedence for conflicts

**Extracted-First Strategy**:
1. Start with extracted entities/relationships
2. Add seed entities/relationships that don't exist in extracted
3. Extracted data takes precedence for conflicts

**Merge Strategy**:
1. Combine all entity/relationship IDs
2. For each ID, merge properties (extracted first, then seed)
3. Seed properties take precedence for conflicts

**Time Complexity**: O(n + m) where n = seed items, m = extracted items
**Space Complexity**: O(n + m) for merged data

```python
# Merge strategy example
integrated = manager.integrate_with_extracted(
    seed_data,
    extracted_data,
    merge_strategy="merge"
)
```

#### Entity Merging
**Algorithm**: ID-based entity matching and property merging

1. **ID Indexing**: Create ID-to-entity mapping for both datasets
2. **ID Matching**: Match entities by ID
3. **Property Merging**: Merge properties based on strategy
4. **Conflict Resolution**: Resolve conflicts using strategy priority
5. **Result Construction**: Build merged entity list

**Time Complexity**: O(n + m) where n = seed entities, m = extracted entities
**Space Complexity**: O(n + m) for merged entities

#### Relationship Merging
**Algorithm**: Triplet-based relationship matching

1. **Triplet Indexing**: Create (source_id, target_id, type) to relationship mapping
2. **Triplet Matching**: Match relationships by triple
3. **Property Merging**: Merge relationship properties
4. **Duplicate Handling**: Handle duplicate relationships
5. **Result Construction**: Build merged relationship list

**Time Complexity**: O(r1 + r2) where r1 = seed relationships, r2 = extracted relationships
**Space Complexity**: O(r1 + r2) for merged relationships

### Quality Validation Algorithms

#### Required Field Checking
**Algorithm**: Validate required fields in entities and relationships

1. **Entity Validation**: Check each entity for 'id' field (required)
2. **Type Checking**: Check for 'type' field (warning if missing)
3. **Relationship Validation**: Check each relationship for 'source_id' and 'target_id' (required)
4. **Type Checking**: Check for 'type' field (warning if missing)
5. **Error Collection**: Collect all errors and warnings

**Time Complexity**: O(n + r) where n = entities, r = relationships
**Space Complexity**: O(e) where e = errors/warnings

```python
# Required field checking
validation = manager.validate_quality(foundation)
# Checks all required fields
```

#### Duplicate Detection
**Algorithm**: Set-based duplicate detection

1. **Entity ID Collection**: Collect all entity IDs
2. **Set Creation**: Create set of unique IDs
3. **Duplicate Counting**: Count duplicates (total - unique)
4. **Relationship Triplet Collection**: Collect (source_id, target_id, type) triplets
5. **Duplicate Detection**: Detect duplicate relationships

**Time Complexity**: O(n + r) where n = entities, r = relationships
**Space Complexity**: O(n + r) for ID/triplet sets

```python
# Duplicate detection
validation = manager.validate_quality(foundation)
duplicates = validation["metrics"]["duplicate_entities"]
```

#### Consistency Validation
**Algorithm**: Cross-reference consistency checking

1. **Entity ID Set**: Create set of all entity IDs
2. **Relationship Validation**: Check that relationship source_id and target_id exist in entity set
3. **Type Consistency**: Check type consistency across entities
4. **Metadata Consistency**: Validate metadata consistency

**Time Complexity**: O(r × log(n)) where r = relationships, n = entities
**Space Complexity**: O(n) for entity ID set

### Export Algorithms

#### JSON Export
**Algorithm**: JSON serialization with structure preservation

1. **Data Structure**: Build export structure with entities, relationships, metadata
2. **Metadata Addition**: Add export timestamp
3. **JSON Serialization**: Serialize to JSON using json.dump()
4. **File Writing**: Write to file with UTF-8 encoding

**Time Complexity**: O(n + r) where n = entities, r = relationships
**Space Complexity**: O(n + r) for serialized data

```python
# JSON export
manager.export_seed_data("output.json", format="json")
```

#### CSV Export
**Algorithm**: Multi-file CSV export with header generation

1. **Field Extraction**: Extract field names from first entity/relationship
2. **Header Generation**: Generate CSV header from field names
3. **Entity Export**: Write entities to entities CSV file
4. **Relationship Export**: Write relationships to relationships CSV file
5. **Encoding**: Use UTF-8 encoding

**Time Complexity**: O(n + r) where n = entities, r = relationships
**Space Complexity**: O(1) for streaming write

```python
# CSV export
manager.export_seed_data("output", format="csv")
# Creates: output_entities.csv and output_relationships.csv
```

### Methods

#### SeedDataManager Methods

- `register_source(name, format, location, **options)`: Register seed data source
- `load_from_csv(file_path, **options)`: Load data from CSV file
- `load_from_json(file_path, **options)`: Load data from JSON file
- `load_from_database(connection_string, **options)`: Load data from database
- `load_from_api(api_url, **options)`: Load data from API
- `load_source(source_name)`: Load data from registered source
- `create_foundation_graph(schema_template)`: Create foundation graph from all sources
- `integrate_with_extracted(seed_data, extracted_data, merge_strategy)`: Integrate seed with extracted data
- `validate_quality(seed_data, **options)`: Validate seed data quality
- `export_seed_data(file_path, format)`: Export seed data to file
- `_record_to_entity(record)`: Convert record to entity format
- `_record_to_relationship(record)`: Convert record to relationship format
- `_validate_against_template(foundation, schema_template)`: Validate against schema template

## Configuration

### Environment Variables

```bash
# Seed data configuration
export SEED_AUTO_VALIDATE=true
export SEED_DEFAULT_ENTITY_TYPE=Entity
export SEED_DEFAULT_RELATIONSHIP_TYPE=RELATED_TO
export SEED_VERIFY_SOURCES=true
export SEED_DEFAULT_VERSION=1.0

# Database configuration
export SEED_DB_CONNECTION_STRING=postgresql://user:pass@localhost/db
export SEED_DB_TIMEOUT=30

# API configuration
export SEED_API_TIMEOUT=30
export SEED_API_RETRY_COUNT=3
```

### Programmatic Configuration

```python
from veritasreason.seed import SeedDataManager

# Configure manager
manager = SeedDataManager(
    config={
        "auto_validate": True,
        "default_entity_type": "Entity",
        "default_relationship_type": "RELATED_TO",
        "verify_sources": True
    }
)
```

### Configuration File (YAML)

```yaml
# config.yaml
seed:
  auto_validate: true
  default_entity_type: Entity
  default_relationship_type: RELATED_TO
  verify_sources: true
  default_version: "1.0"

seed_database:
  connection_string: postgresql://user:pass@localhost/db
  timeout: 30

seed_api:
  timeout: 30
  retry_count: 3
```

## Advanced Examples

### Complete Seed Data Pipeline

```python
from veritasreason.seed import SeedDataManager
from veritasreason.kg import build

# Create seed data manager
manager = SeedDataManager()

# Register multiple sources
manager.register_source("people", "json", "data/people.json", entity_type="Person")
manager.register_source("companies", "csv", "data/companies.csv", entity_type="Organization")
manager.register_source("locations", "json", "data/locations.json", entity_type="Location")
manager.register_source("relationships", "json", "data/relationships.json", relationship_type="locatedIn")

# Create foundation graph
foundation = manager.create_foundation_graph()

# Validate quality
validation = manager.validate_quality(foundation)

if validation["valid"]:
    print(f"Foundation graph created successfully!")
    print(f"Entities: {len(foundation['entities'])}")
    print(f"Relationships: {len(foundation['relationships'])}")
    
    # Build knowledge graph from foundation
    kg = build(sources=[foundation])
    
    # Export seed data
    manager.export_seed_data("output/foundation.json", format="json")
else:
    print(f"Validation failed: {validation['errors']}")
```

### Multi-Source Integration

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register sources from different formats
manager.register_source("csv_entities", "csv", "data/entities.csv", entity_type="Person")
manager.register_source("json_entities", "json", "data/entities.json", entity_type="Person")
manager.register_source("db_entities", "database", "postgresql://...", entity_type="Person", table_name="entities")
manager.register_source("api_entities", "api", "https://api.example.com", entity_type="Person", endpoint="entities")

# Load from all sources
all_records = []
for source_name in manager.sources:
    try:
        records = manager.load_source(source_name)
        all_records.extend(records)
    except Exception as e:
        print(f"Failed to load {source_name}: {e}")

print(f"Loaded {len(all_records)} total records from {len(manager.sources)} sources")
```

### Seed and Extracted Data Integration

```python
from veritasreason.seed import SeedDataManager
from veritasreason.extract import extract_entities, extract_relationships

manager = SeedDataManager()

# Load seed data
manager.register_source("seed_entities", "json", "data/seed_entities.json")
seed_foundation = manager.create_foundation_graph()

# Extract data from documents
extracted_entities = extract_entities(documents)
extracted_relationships = extract_relationships(documents)
extracted_data = {
    "entities": extracted_entities,
    "relationships": extracted_relationships
}

# Integrate seed with extracted data
integrated = manager.integrate_with_extracted(
    seed_foundation,
    extracted_data,
    merge_strategy="merge"
)

print(f"Integrated: {len(integrated['entities'])} entities")
print(f"Seed entities: {integrated['metadata']['seed_count']}")
print(f"Extracted entities: {integrated['metadata']['extracted_count']}")
```

### Quality Validation Workflow

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register and load sources
manager.register_source("entities", "json", "data/entities.json")
foundation = manager.create_foundation_graph()

# Validate quality
validation = manager.validate_quality(foundation)

# Check validation results
if not validation["valid"]:
    print("Validation Errors:")
    for error in validation["errors"]:
        print(f"  - {error}")
    
    # Fix errors
    # ... error fixing logic ...

# Check warnings
if validation["warnings"]:
    print("Validation Warnings:")
    for warning in validation["warnings"]:
        print(f"  - {warning}")

# Check metrics
metrics = validation["metrics"]
if metrics["duplicate_entities"] > 0:
    print(f"Found {metrics['duplicate_entities']} duplicate entities")
    # Handle duplicates
```

### Version-Aware Seed Data Management

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register source with version
manager.register_source(
    name="entities",
    format="json",
    location="data/entities_v1.json",
    version="1.0"
)

# Load version 1.0
v1_data = manager.load_source("entities")

# Update to version 2.0
manager.register_source(
    name="entities",
    format="json",
    location="data/entities_v2.json",
    version="2.0"
)

# Load version 2.0
v2_data = manager.load_source("entities")

# Compare versions
print(f"Version history: {manager.versions.get('entities', [])}")
```

### Custom Record Conversion

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Load records
records = manager.load_from_json("data/custom_format.json")

# Custom conversion
custom_entities = []
for record in records:
    # Custom entity conversion logic
    entity = manager._record_to_entity(record)
    if entity:
        # Add custom processing
        entity["custom_field"] = "custom_value"
        custom_entities.append(entity)

# Use custom entities
foundation = {
    "entities": custom_entities,
    "relationships": [],
    "metadata": {}
}
```

### Batch Source Loading

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()

# Register multiple sources
sources = [
    ("people", "json", "data/people.json", "Person"),
    ("companies", "csv", "data/companies.csv", "Organization"),
    ("locations", "json", "data/locations.json", "Location")
]

for name, format, location, entity_type in sources:
    manager.register_source(name, format, location, entity_type=entity_type)

# Load all sources
all_entities = []
all_relationships = []

for source_name in manager.sources:
    try:
        records = manager.load_source(source_name)
        for record in records:
            entity = manager._record_to_entity(record)
            if entity:
                all_entities.append(entity)
            rel = manager._record_to_relationship(record)
            if rel:
                all_relationships.append(rel)
    except Exception as e:
        print(f"Failed to load {source_name}: {e}")

print(f"Loaded {len(all_entities)} entities and {len(all_relationships)} relationships")
```

## Best Practices

1. **Source Registration**:
   - Register all sources before creating foundation graph
   - Use descriptive source names
   - Set appropriate entity/relationship types
   - Mark verified sources appropriately

2. **Data Loading**:
   - Validate source files exist before loading
   - Handle loading errors gracefully
   - Use appropriate format for data type
   - Add metadata (entity_type, relationship_type, source) for tracking

3. **Foundation Graph Creation**:
   - Validate quality after creation
   - Check for duplicates and inconsistencies
   - Use schema templates when available
   - Preserve source metadata

4. **Data Integration**:
   - Choose appropriate merge strategy:
     - Use "seed_first" when seed data is authoritative
     - Use "extracted_first" when extracted data is more current
     - Use "merge" when combining complementary data
   - Validate integrated data
   - Check for conflicts and resolve appropriately

5. **Quality Validation**:
   - Always validate seed data before use
   - Check for required fields
   - Detect and handle duplicates
   - Verify consistency

6. **Version Management**:
   - Track versions for all sources
   - Document version changes
   - Use version strings consistently

7. **Export Operations**:
   - Export in appropriate format (JSON for structure, CSV for tabular)
   - Include metadata in exports
   - Use descriptive file names
   - Preserve data structure

8. **Error Handling**:
   - Handle source loading failures gracefully
   - Log errors and warnings
   - Continue processing other sources if one fails
   - Provide meaningful error messages

9. **Performance**:
   - Load sources in parallel when possible
   - Use appropriate data formats (CSV for large datasets)
   - Cache loaded data when appropriate
   - Optimize database queries

10. **Testing**:
    - Test with sample data first
    - Validate against known good data
    - Test merge strategies
    - Verify export formats

