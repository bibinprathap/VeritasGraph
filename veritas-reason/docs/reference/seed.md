# Seed

> **Seed data management system for initializing Knowledge Graphs from verified sources.**

---

## 🎯 Overview

The **Seed Module** provides a system for initializing Knowledge Graphs with verified, structured data from trusted sources. It enables bootstrapping knowledge graphs with reference data, taxonomies, and verified entities.

### What is Seed Data?

**Seed data** is verified, structured data used to bootstrap or enhance knowledge graphs. Examples include:

- **Taxonomies**: Hierarchical classifications (product categories, organizational structures)
- **Reference Data**: Immutable reference information (countries, codes, standards)
- **Verified Entities**: Pre-validated entities from authoritative sources
- **Foundation Graphs**: Initial graph structures to build upon

### Why Use the Seed Module?

- **Bootstrap KGs**: Start with verified data instead of empty graphs
- **Quality Assurance**: Use trusted, validated data sources
- **Faster Development**: Skip initial data extraction for known entities
- **Data Integration**: Merge seed data with extracted data
- **Versioning**: Manage different versions of seed data

### How It Works

1. **Load Seed Data**: Load from CSV, JSON, databases, or APIs
2. **Validate**: Validate data quality and schema compliance
3. **Transform**: Convert to knowledge graph format
4. **Merge**: Integrate with extracted data using configurable strategies
5. **Version**: Track versions of seed data sources

<div class="grid cards" markdown>

-   :material-database-import:{ .lg .middle } **Multi-Source Loading**

    ---

    Load seed data from CSV, JSON, Databases, and APIs

-   :material-graph-outline:{ .lg .middle } **Foundation Graph**

    ---

    Create reliable foundation graphs to bootstrap your KG

-   :material-merge:{ .lg .middle } **Data Integration**

    ---

    Merge seed data with extracted data using configurable strategies

-   :material-check-all:{ .lg .middle } **Validation**

    ---

    Validate seed data quality and schema compliance

-   :material-git:{ .lg .middle } **Versioning**

    ---

    Manage versions of seed data sources

-   :material-export:{ .lg .middle } **Export**

    ---

    Export seed data to standard formats

</div>

!!! tip "When to Use"
    - **Bootstrapping**: When starting a new KG and you have existing structured data (taxonomies, user lists, product catalogs).
    - **Reference Data**: To load immutable reference data (countries, codes, constants).
    - **Testing**: To load consistent test datasets for development.

---

## ⚙️ Algorithms Used

### Data Loading

**Purpose**: Load seed data from various formats efficiently.

**How it works**:

- **Format Detection**: Auto-detection of CSV delimiters, JSON structure
- **Streaming**: Row-by-row processing for large files
- **Normalization**: Type conversion and encoding handling

### Integration & Merging

**Purpose**: Merge seed data with extracted data using configurable strategies.

**How it works**:

- **Seed-First Strategy**: Seed data overrides extracted data (Trust Seed)
- **Extracted-First Strategy**: Extracted data overrides seed (Trust Extraction)
- **Smart Merge**: Property-level merging with conflict resolution
- **ID Matching**: Entity resolution between seed and extracted entities

### Validation

**Purpose**: Validate seed data quality and schema compliance.

**How it works**:

- **Schema Validation**: Template-based structure checking
- **Constraint Checking**: Required field and type validation
- **Consistency Check**: Reference integrity (relationships point to existing entities)

---

## Main Classes

### SeedDataManager

Coordinator for all seed data operations.

**Methods:**

| Method | Description |
|--------|-------------|
| `register_source(name, format, location)` | Add data source |
| `create_foundation_graph()` | Build KG from sources |
| `validate_quality(seed_data)` | Check data quality |
| `integrate_with_extracted(seed, extracted)` | Merge graphs |
| `export_seed_data(path, format)` | Export data |

**Example:**

```python
from veritasreason.seed import SeedDataManager

manager = SeedDataManager()
manager.register_source("countries", "csv", "data/countries.csv")
foundation_kg = manager.create_foundation_graph()
```

### SeedDataSource

Data class defining a source.

**Attributes:**
- `name`: Source identifier
- `type`: `csv`, `json`, `api`, `sql`
- `path`: File path or connection string
- `config`: Parsing options

---



## Configuration

### Environment Variables

```bash
export SEED_DATA_DIR=./data/seed
export SEED_MERGE_STRATEGY=seed_first
```

### YAML Configuration

```yaml
seed:
  sources:
    - name: "employees"
      type: "csv"
      path: "./data/employees.csv"
      
  merge:
    strategy: "seed_first"
    
  validation:
    strict: true
```

---

## Integration Examples

### Bootstrapping a KG

```python
from veritasreason.seed import SeedDataManager
from veritasreason.ingest import Ingestor

# 1. Load Foundation (Seed)
seed_manager = SeedDataManager()
seed_manager.register_source("taxonomy", "json", "taxonomy.json")
foundation_kg = seed_manager.create_foundation_graph()

# 2. Ingest New Data
ingestor = Ingestor()
new_data = ingestor.ingest("news_articles.pdf")

# 3. Merge
final_kg = seed_manager.integrate_seed_extracted(
    seed_graph=foundation_kg,
    extracted_data=new_data,
    strategy="seed_first"  # Keep taxonomy strict
)
```

---

## Best Practices

1.  **Trust Seed Data**: Usually, seed data is verified. Use `seed_first` merge strategy.
2.  **Version Control**: Keep seed data files in version control (git).
3.  **Validate Schema**: Ensure seed data matches your target ontology.
4.  **Clean IDs**: Use consistent ID schemes in seed data to facilitate merging.

---

## Cookbook

Interactive tutorials that use seed data:

- **[Financial Data Integration MCP](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/use_cases/finance/01_Financial_Data_Integration_MCP.ipynb)**: Merging financial data with seed data integration
  - **Topics**: Finance, data fusion, MCP integration, seed data
  - **Difficulty**: Intermediate
  - **Use Cases**: Integrating structured seed data with extracted data

- **[Energy Market Analysis](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/use_cases/renewable_energy/01_Energy_Market_Analysis.ipynb)**: Analyzing trends with seed data integration
  - **Topics**: Energy, time series, temporal analysis, seed data
  - **Difficulty**: Intermediate
  - **Use Cases**: Bootstrapping knowledge graphs with verified data

## See Also

- [Ingest Module](ingest.md) - Loading unstructured data
- [Knowledge Graph Module](kg.md) - The target graph structure
- [Deduplication Module](deduplication.md) - Handling duplicates during merge
