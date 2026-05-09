# Parse

> **Universal data parser supporting documents, web content, structured data, emails, code, and media.**

---

## 🎯 Overview

The **Parse Module** extracts structured content from raw files and data sources. It converts various file formats (PDF, DOCX, HTML, JSON, etc.) into usable text and structured data for semantic processing.

### What is Document Parsing?

**Document parsing** is the process of extracting text, structure, and metadata from files. The parse module handles:
- **Documents**: PDF, DOCX, PPTX, Excel, TXT, RTF
- **Web Content**: HTML, XML, JavaScript-rendered pages
- **Structured Data**: JSON, CSV, XML, YAML
- **Email**: MIME messages with attachments
- **Code**: Source code parsing into ASTs
- **Media**: OCR for images, metadata for audio/video

### Why Use the Parse Module?

- **Universal Format Support**: Handle dozens of file formats
- **Structure Preservation**: Maintain document structure (tables, headings, etc.)
- **OCR Support**: Extract text from scanned documents and images
- **Metadata Extraction**: Extract document metadata (author, date, etc.)
- **Code Analysis**: Parse source code for structure and dependencies
- **Error Handling**: Robust handling of corrupted or malformed files

### How It Works

1. **Format Detection**: Automatically detect file format
2. **Parser Selection**: Choose appropriate parser for the format
3. **Content Extraction**: Extract text, structure, and metadata
4. **Normalization**: Normalize extracted content
5. **Output**: Return structured data ready for semantic processing

<div class="grid cards" markdown>

-   :material-file-document:{ .lg .middle } **Document Parsing**

    ---

    Extract text, tables, and metadata from PDF, DOCX, PPTX, Excel, and TXT

-   :material-web:{ .lg .middle } **Web Content**

    ---

    Parse HTML, XML, and JavaScript-rendered pages with Selenium/Playwright

-   :material-code-json:{ .lg .middle } **Structured Data**

    ---

    Handle JSON, CSV, XML, and YAML with nested structure preservation

-   :material-email:{ .lg .middle } **Email Parsing**

    ---

    Extract headers, bodies, attachments, and thread structure from MIME messages

-   :material-code-braces:{ .lg .middle } **Code Analysis**

    ---

    Parse source code (Python, JS, etc.) into ASTs, extracting functions and dependencies

-   :material-image:{ .lg .middle } **Media Processing**

    ---

    OCR for images and metadata extraction for audio/video files

</div>

!!! tip "When to Use"
    - **After Ingestion**: The first step after loading raw files to convert them into usable text/data
    - **Data Extraction**: Pulling specific fields from structured files (JSON/CSV)
    - **Content Analysis**: Analyzing codebases or email archives
    - **OCR**: Extracting text from scanned documents or images

---

## ⚙️ Algorithms Used

### Document Parsing
- **PDF**: `pdfplumber` for precise layout preservation, table extraction, and image handling. Fallback to `PyPDF2`.
- **Docling**: `docling` integration for advanced document structure understanding and high-accuracy table extraction across PDF, DOCX, PPTX, XLSX, and HTML.
- **Office (DOCX/PPTX/XLSX)**: XML-based parsing of OpenXML formats to extract text, styles, and properties.
- **OCR**: Tesseract-based optical character recognition for image-based PDFs and image files.

### Web Parsing
- **DOM Traversal**: BeautifulSoup for static HTML parsing and element extraction.
- **Headless Browser**: Selenium/Playwright for rendering dynamic JavaScript content before extraction.
- **Content Cleaning**: Heuristic removal of boilerplates (navbars, footers, ads).

### Code Parsing
- **AST Traversal**: Abstract Syntax Tree parsing to identify classes, functions, and imports.
- **Dependency Graphing**: Static analysis of import statements to build dependency networks.
- **Comment Extraction**: Regex and parser-based extraction of docstrings and inline comments.

---

## Main Classes

### DocumentParser

Unified interface for document formats.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse_document(path)` `` | Auto-detect format and parse |
| `` `extract_text(path)` `` | Extract text from PDF/DOCX/HTML/TXT |
| `` `extract_metadata(path)` `` | Extract document metadata |
| `` `parse_batch(paths)` `` | Parse multiple documents |

**Example:**

```python
from veritasreason.parse import DocumentParser

parser = DocumentParser()
doc = parser.parse_document("report.pdf")
print(doc.get("metadata", {}).get("title"))
print(doc.get("full_text", "")[:100])
```

### DoclingParser

Specialized parser using Docling for enhanced layout understanding and table extraction. It is independent of `DocumentParser` and optimized for complex document structures.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse(path)` `` | Full parse including text, tables, and metadata |
| `` `parse_batch(paths)` `` | Parse multiple documents in parallel |
| `` `extract_text(path)` `` | Extract clean text in Markdown/HTML/JSON format |
| `` `extract_tables(path)` `` | High-accuracy table extraction |
| `` `extract_metadata(path)` `` | Extract document properties |

**Configuration:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `export_format` | `str` | `"markdown"` | Output format: `"markdown"`, `"html"`, `"json"` |
| `enable_ocr` | `bool` | `False` | Enable OCR for scanned documents |

**Example:**

```python
from veritasreason.parse import DoclingParser

parser = DoclingParser()
result = parser.parse("complex_table.pdf")

# Access high-accuracy tables
for table in result["tables"]:
    print(table["headers"])
    
# Get markdown representation
print(result["full_text"])
```

### WebParser

Parses web content.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse_web_content(content, content_type)` `` | Parse HTML/XML |
| `` `extract_text(content)` `` | Clean text from HTML |
| `` `extract_links(content)` `` | Extract hyperlinks |
| `` `render_javascript(url)` `` | Render JS for dynamic pages |

### StructuredDataParser

Parses data files.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse_data(path, data_format)` `` | Parse JSON/CSV/XML/YAML |

**Example:**

```python
from veritasreason.parse import StructuredDataParser

parser = StructuredDataParser()
data = parser.parse_data("data.json", data_format="json")
print(type(data.get("data"))).__name__
```

### CodeParser

Parses source code.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse_code(path)` `` | Parse code file; returns structure, comments, dependencies |

**Example:**

```python
from veritasreason.parse import CodeParser

parser = CodeParser()
data = parser.parse_code("script.py", language="python")
print(data.get("structure", {}).get("functions", []))
print(data.get("dependencies", {}))
```

### EmailParser

Parses email messages.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse_email(path)` `` | Parse full email (headers/body/attachments) |
| `` `parse_headers(path)` `` | Extract headers only |
| `` `extract_body(path)` `` | Extract text/HTML body |
| `` `analyze_thread(path)` `` | Thread reconstruction |

**Example:**

```python
from veritasreason.parse import EmailParser

parser = EmailParser()
email = parser.parse_email("email.eml", extract_attachments=True)
print(email.headers.subject)
print(email.body.text[:120])
```

### MediaParser

Parses media files.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `parse_media(path, media_type)` `` | Parse image/audio/video |

**Example:**

```python
from veritasreason.parse import MediaParser

parser = MediaParser()
image = parser.parse_media("image.jpg", media_type="image")
print(image.get("metadata", {}))
```

### Format-Specific Parsers

- `PDFParser`, `DOCXParser`, `PPTXParser`, `ExcelParser`
- `HTMLParser`, `XMLParser`
- `JSONParser`, `CSVParser`
- `ImageParser`

**Examples:**

```python
from veritasreason.parse import DocumentParser, WebParser, StructuredDataParser

# Document
doc = DocumentParser().parse_document("document.pdf")
print(doc.get("full_text", "")[:120])

# Web
web = WebParser().parse_web_content("https://example.com", content_type="html")
print(web.get("text", "")[:120])

# Structured Data (JSON)
data = StructuredDataParser().parse_data("data.json", data_format="json")
print(list(data.get("data", {}).keys()))
```

---

## Usage Examples

### WebParser

```python
from veritasreason.parse import WebParser

parser = WebParser()
html = parser.parse_web_content("https://example.com", content_type="html")
links = parser.extract_links("https://example.com")
```

### StructuredDataParser

```python
from veritasreason.parse import StructuredDataParser

parser = StructuredDataParser()
json = parser.parse_data("data.json", data_format="json")
csv = parser.parse_data("data.csv", data_format="csv")
xml = parser.parse_data("data.xml", data_format="xml")
```

---

## Configuration

### Environment Variables

```bash
export PARSE_OCR_ENABLED=true
export PARSE_OCR_LANG=eng
export PARSE_USER_AGENT="VeritasReasonBot/1.0"
```

### YAML Configuration

```yaml
parse:
  ocr:
    enabled: true
    language: eng
    
  web:
    user_agent: "MyBot/1.0"
    timeout: 30
    
  pdf:
    extract_tables: true
    extract_images: false
```

---

## Integration

Use parser classes directly in pipelines and services. Avoid convenience functions for stronger type clarity and consistency.

---

## Best Practices

1.  Disable OCR if not needed; enable only for scanned documents.
2.  Use specific parser classes like `JSONParser` or `PDFParser` when format is known.
3.  Handle encodings explicitly for CSV/TXT where auto-detect may fail.
4.  Clean web content using `WebParser` utilities rather than raw HTML parsing.

---

## Troubleshooting

**Issue**: `TesseractNotFoundError`
**Solution**: Install Tesseract OCR on your system (`apt-get install tesseract-ocr` or brew).

**Issue**: PDF tables are messy.
**Solution**: Try `pdfplumber` settings in config or use specialized table extraction tools if layout is complex.

---

## See Also

- [Ingest Module](ingest.md) - Handles file downloading/loading
- [Split Module](split.md) - Chunks the parsed text
- [Semantic Extract Module](semantic_extract.md) - Extracts entities from text

## Cookbook

Interactive tutorials to learn document parsing:

- **[Document Parsing](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/03_Document_Parsing.ipynb)**: Extract clean text from complex formats
  - **Topics**: OCR, PDF parsing, text extraction, format detection
  - **Difficulty**: Beginner
  - **Use Cases**: Processing documents, extracting text from various formats
