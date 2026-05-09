---
name: ingest
description: Ingest data from files, databases, APIs, or streams into VeritasReason knowledge graphs with schema mapping and entity linking.
---

# /veritasreason:ingest

Ingest new data into the knowledge graph. Usage: `/veritasreason:ingest <source> [args]`

`$ARGUMENTS` = source type + optional file path, connection string, or dataset identifier.

---

## `file <path> [--format json|csv|yaml|xml]`

Ingest structured data from a local file.

```python
from veritasreason.ingest import ingest_file

data = ingest_file(file_path=path, method='file', file_format=file_format)
```

Output: imported node/edge count and ingestion summary.

---

## `db <connection> [--query <sql>]`

Ingest data from a database source.

```python
from veritasreason.ingest import ingest_database

result = ingest_database(connection_string=conn, query=query)
```

Return: rows ingested, mapped entities, and warnings.
