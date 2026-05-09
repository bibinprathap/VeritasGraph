# Docling Integration

VeritasReason features a native integration with **Docling**, the powerful document parsing library that excels at extracting structured data from complex documents like PDFs, DOCX, and PPTX.

## Overview

Docling is integrated into VeritasReason's `parse` module via the `DoclingParser`. This allows you to seamlessly convert unstructured documents into semantic structures that can be indexed, searched, and analyzed within the VeritasReason framework.

- 📖 **VeritasReason Docling Integration Docs**: [Reference Guide](../reference/parse.md)
- 💻 **VeritasReason Docling Integration GitHub**: [Source Code](https://github.com/bibinprathap/VeritasGraph/blob/main/veritasreason/parse/docling_parser.py)
- 🧑🏽‍🍳 **VeritasReason Docling Integration Example**: [Docling Clear Code Example](../CodeExamples.md#docling-clear-code-example)
- 📦 **VeritasReason Docling Integration PyPI**: [Installation Guide](../installation.md)

---

## Integration Documentation

The `DoclingParser` provides a high-level interface for document processing. It supports:

*   **Multi-format support**: PDF, DOCX, PPTX, HTML, and more.
*   **Table Extraction**: High-fidelity table extraction with header detection.
*   **OCR Support**: Built-in Optical Character Recognition for scanned documents.
*   **Markdown Export**: Clean markdown output optimized for LLM consumption.

### Basic Usage

```python
from veritasreason.parse import DoclingParser

# Initialize with OCR enabled
parser = DoclingParser(enable_ocr=True)

# Parse a complex document
result = parser.parse("financial_report.pdf")

# Access the structured data
print(f"Content: {result['full_text'][:200]}...")
print(f"Found {len(result['tables'])} tables")
```

For more details, see the [Parse Reference](../reference/parse.md).

---

## Integration Example

We provide a detailed cookbook and clear code examples to help you get started quickly.

### Docling Clear Code Example

```python
from veritasreason.parse import DoclingParser
import json

# 1. Initialize the Docling Parser with advanced config
parser = DoclingParser(
    enable_ocr=True, 
    export_format="markdown"
)

# 2. Parse a complex document (PDF, DOCX, etc.)
result = parser.parse("complex_invoice.pdf")

# 3. Access the clean Markdown text
print(f"--- Document Content ---\n{result['full_text']}")

# 4. Iterate through extracted tables
for i, table in enumerate(result['tables']):
    print(f"\nTable {i+1} headers: {table.get('headers', [])}")
    # Access table rows as a list of lists
    for row in table.get('rows', [])[:3]:  # Print first 3 rows
        print(f"  Row: {row}")

# 5. Get document metadata
metadata = result['metadata']
print(f"\n--- Metadata ---\nTitle: {metadata.get('title')}")
print(f"Total Pages: {result.get('total_pages')}")
```

See more in our [Code Examples](../CodeExamples.md).

---

## GitHub Source

The integration is open-source and available on GitHub. You can explore the implementation, contribute improvements, or report issues.

- [docling_parser.py](https://github.com/bibinprathap/VeritasGraph/blob/main/veritasreason/parse/docling_parser.py) - The core implementation of the Docling integration.

---

## PyPI & Installation

Docling is an optional but highly recommended dependency for VeritasReason. You can install it along with VeritasReason or as a separate requirement.

### Install via VeritasReason
```bash
pip install veritas-reason
```

### Install Docling manually
If you are working in a custom environment:
```bash
pip install docling
```

For full installation details, see the [Installation Guide](../installation.md).
