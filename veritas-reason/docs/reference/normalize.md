# Normalize

> **Clean, standardize, and prepare text and data for semantic processing with comprehensive normalization capabilities.**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-text-box-remove:{ .lg .middle } **Text Cleaning**

    ---

    Remove noise, fix encoding issues, and standardize whitespace for clean text

-   :material-format-text:{ .lg .middle } **Entity Normalization**

    ---

    Standardize entity names, abbreviations, and formats across documents

-   :material-calendar-clock:{ .lg .middle } **Date & Time**

    ---

    Parse and standardize date/time formats to ISO 8601

-   :material-numeric:{ .lg .middle } **Number Normalization**

    ---

    Standardize numeric values, units, and measurements

-   :material-translate:{ .lg .middle } **Language Detection**

    ---

    Automatically detect document language with confidence scoring

-   :material-file-code:{ .lg .middle } **Encoding Handling**

    ---

    Fix character encoding issues and ensure UTF-8 compliance

</div>

!!! tip "Why Normalize?"
    Normalization is crucial for:
    
    - **Consistency**: Ensure uniform data representation
    - **Accuracy**: Improve entity extraction and matching
    - **Quality**: Reduce noise and errors in downstream processing
    - **Performance**: Enable better deduplication and search

---

## ⚙️ Algorithms Used

### Text Normalization

**Purpose**: Clean and standardize text for consistent processing.

**How it works**:

- **Unicode Normalization**: NFC, NFD, NFKC, NFKD forms using Unicode standard
- **Whitespace Normalization**: Regex-based cleanup (`` `\s+` `` → single space)
- **Case Folding**: Locale-aware case normalization (Unicode case folding)
- **Diacritic Removal**: Unicode decomposition and combining character removal
- **Punctuation Handling**: Smart punctuation normalization preserving sentence structure

### Entity Normalization

**Purpose**: Standardize entity names and resolve variations to canonical forms.

**How it works**:

- **Fuzzy Matching**: Levenshtein distance with configurable threshold (default: `` `0.85` ``)
- **Phonetic Matching**: Soundex and Metaphone algorithms for name variants
- **Abbreviation Expansion**: Dictionary-based expansion with context awareness
- **Canonical Form Selection**: Frequency-based or confidence-based selection
- **Entity Linking**: Hash-based entity ID generation for cross-document linking

### Date/Time Normalization

**Purpose**: Parse and standardize date/time formats to ISO 8601.

**How it works**:

- **Parsing**: dateutil parser with 100+ format support
- **Timezone Handling**: pytz for timezone conversion and DST handling
- **Standardization**: ISO 8601 format output (`` `YYYY-MM-DDTHH:MM:SSZ` ``)
- **Relative Date Resolution**: Convert "yesterday", "last week" to absolute dates
- **Fuzzy Date Parsing**: Handle incomplete dates (e.g., "March 2024")

### Number Normalization

**Purpose**: Standardize numeric values, units, and measurements.

**How it works**:

- **Numeric Parsing**: Handle various formats (`` `1,000.00` ``, `` `1.000,00` ``, `` `1 000.00` ``)
- **Unit Conversion**: Standardize units (km → meters, lbs → kg)
- **Scientific Notation**: Parse and normalize scientific notation
- **Percentage Handling**: Normalize percentage representations
- **Currency Normalization**: Standardize currency symbols and amounts

### Language Detection

**Purpose**: Automatically detect document language with confidence scoring.

**How it works**:

- **N-gram Analysis**: Character and word n-gram frequency analysis
- **Statistical Models**: Language-specific statistical models
- **Confidence Scoring**: Probability-based confidence scores
- **Multi-language Support**: 100+ languages supported

---

## Main Classes

### TextNormalizer

Main text normalization orchestrator with comprehensive cleaning capabilities.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `normalize_text(text, ...)` `` | Normalize single text using full pipeline |
| `` `clean_text(text, ...)` `` | Clean text (HTML removal, sanitization) |
| `` `standardize_format(text, format_type)` `` | Standardize formatting (standard/compact/preserve) |
| `` `process_batch(texts, ...)` `` | Batch normalize multiple texts |

**Example:**

```python
from veritasreason.normalize import TextNormalizer

normalizer = TextNormalizer()

# Normalize
normalized = normalizer.normalize_text("  Apple Inc.  was founded in 1976.  ", case="preserve")

# Clean only
cleaned = normalizer.clean_text("<p>Hello</p>", remove_html=True)

# Batch
texts = ["Hello   World", "Another   Example"]
normalized_batch = normalizer.process_batch(texts, case="lower")
```

---

### EntityNormalizer

Standardize entity names and resolve variations to canonical forms.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `normalize_entity(name, ...)` `` | Normalize entity name to canonical form |
| `` `resolve_aliases(name, ...)` `` | Resolve aliases via alias map |
| `` `disambiguate_entity(name, ...)` `` | Disambiguate using context and candidates |
| `` `link_entities(names, ...)` `` | Link a list of names to canonical forms |

**Configuration Options:**

```python
EntityNormalizer(
    fuzzy_matching=True,          # Enable fuzzy matching
    similarity_threshold=0.85,    # Similarity threshold (0-1)
    phonetic_matching=False,      # Enable phonetic matching
    case_sensitive=False,         # Case-sensitive matching
    preserve_case=True,           # Preserve original case in output
    expand_abbreviations=True,    # Expand common abbreviations
    canonical_dict=None           # Custom canonical mappings
)
```

**Example:**

```python
from veritasreason.normalize import EntityNormalizer

normalizer = EntityNormalizer(similarity_threshold=0.85)

# Normalize single
canonical = normalizer.normalize_entity("Apple, Inc.")

# Link list
linked = normalizer.link_entities(["Apple Inc.", "Apple", "AAPL"], entity_type="Organization")
```

---

### DateNormalizer

Parse and standardize date/time formats to ISO 8601.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `normalize_date(date_str, ...)` `` | Parse and normalize date |
| `` `normalize_time(time_str, ...)` `` | Normalize time-only strings |
| `` `parse_temporal_expression(expr)` `` | Parse date ranges and temporal phrases |

**Configuration Options:**

```python
DateNormalizer(
    output_format="ISO8601",      # ISO8601, UNIX, custom format
    timezone="UTC",               # Target timezone
    handle_relative=True,         # Parse "yesterday", "last week"
    fuzzy=True,                   # Fuzzy parsing
    default_day=1,                # Default day for incomplete dates
    default_month=1               # Default month for incomplete dates
)
```

**Example:**

```python
from veritasreason.normalize import DateNormalizer

normalizer = DateNormalizer()

dates = ["Jan 1, 2024", "01/01/2024", "yesterday"]
normalized = [normalizer.normalize_date(d) for d in dates]

time = normalizer.normalize_time("10:30 AM")
```

---

### NumberNormalizer

Standardize numeric values, units, and measurements.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `normalize_number(input, ...)` `` | Parse and normalize number |
| `` `normalize_quantity(quantity, ...)` `` | Parse value with unit |
| `` `convert_units(value, from_unit, to_unit)` `` | Convert units |
| `` `process_currency(text, ...)` `` | Parse currency amount and code |

**Example:**

```python
from veritasreason.normalize import NumberNormalizer

normalizer = NumberNormalizer()

numbers = ["1,000.50", "50%", "1.5e3"]
normalized = [normalizer.normalize_number(n) for n in numbers]

quantity = normalizer.normalize_quantity("5 kg")
converted = normalizer.convert_units(5, "km", "m")
currency = normalizer.process_currency("$1,234.56")
```

---

### LanguageDetector

Detect document language with confidence scoring.

**Methods:**

| Method | Description |
|--------|-------------|
| `` `detect(text)` `` | Detect language |
| `` `detect_with_confidence(text)` `` | Detect with confidence score |
| `` `detect_multiple(text, top_n)` `` | List top-N candidate languages |
| `` `detect_batch(texts)` `` | Batch language detection |

**Example:**

```python
from veritasreason.normalize import LanguageDetector

detector = LanguageDetector()

# Detect language
texts = [
    "Hello, how are you?",
    "Bonjour, comment allez-vous?",
    "Hola, ¿cómo estás?",
    "Hallo, wie geht es dir?",
    "こんにちは、お元気ですか？"
]

for text in texts:
    result = detector.detect(text)
    print(f"{text[:30]:30} → {result['language']} ({result['confidence']:.2f})")

# Output:
# Hello, how are you?           → en (0.99)
# Bonjour, comment allez-vous?  → fr (0.98)
# Hola, ¿cómo estás?            → es (0.97)
# Hallo, wie geht es dir?       → de (0.96)
# こんにちは、お元気ですか？         → ja (0.99)
```

---

## Configuration

### Environment Variables

```bash
# Normalization settings
export NORMALIZE_DEFAULT_LOWERCASE=false
export NORMALIZE_DEFAULT_ENCODING=utf-8
export NORMALIZE_DEFAULT_TIMEZONE=UTC

# Entity normalization
export NORMALIZE_ENTITY_SIMILARITY_THRESHOLD=0.85
export NORMALIZE_ENTITY_FUZZY_MATCHING=true

# Language detection
export NORMALIZE_LANGUAGE_DETECTOR=langdetect
export NORMALIZE_LANGUAGE_CONFIDENCE_THRESHOLD=0.8
```

### YAML Configuration

```yaml
# config.yaml - Normalize Module Configuration

normalize:
  text:
    lowercase: false
    remove_punctuation: false
    fix_encoding: true
    normalize_whitespace: true
    remove_urls: false
    expand_contractions: false
    
  entity:
    fuzzy_matching: true
    similarity_threshold: 0.85
    phonetic_matching: false
    expand_abbreviations: true
    
  date:
    output_format: "ISO8601"
    timezone: "UTC"
    handle_relative: true
    fuzzy: true
    
  number:
    decimal_separator: "."
    thousands_separator: ","
    normalize_units: true
    
  language:
    detector: "langdetect"  # langdetect, fasttext
    confidence_threshold: 0.8
    fallback_language: "en"
```

---

## Integration Examples

### Complete Document Normalization Pipeline

```python
from veritasreason.normalize import TextNormalizer, EntityNormalizer, DateNormalizer, LanguageDetector
from veritasreason.parse import DocumentParser

# Parse documents
parser = DocumentParser()
documents = parser.parse(["document1.pdf", "document2.docx"])

# Detect language
detector = LanguageDetector()
for doc in documents:
    lang_result = detector.detect(doc.content)
    doc.metadata["language"] = lang_result["language"]
    doc.metadata["language_confidence"] = lang_result["confidence"]

text_normalizer = TextNormalizer()

for doc in documents:
    doc.content = text_normalizer.normalize_text(doc.content)

# Normalize dates in metadata
date_normalizer = DateNormalizer(output_format="ISO8601")
for doc in documents:
    if "date" in doc.metadata:
        doc.metadata["date"] = date_normalizer.normalize_date(doc.metadata["date"])

# Normalize entities
entity_normalizer = EntityNormalizer(similarity_threshold=0.85)
# ... entity normalization logic
```

### Multi-Language Document Processing

```python
from veritasreason.normalize import LanguageDetector, TextNormalizer

detector = LanguageDetector()
normalizers = {
    "en": TextNormalizer(expand_contractions=True),
    "fr": TextNormalizer(remove_diacritics=False),
    "de": TextNormalizer(lowercase=False)
}

def process_multilingual_document(text):
    # Detect language
    lang_result = detector.detect(text)
    language = lang_result["language"]
    
    # Use language-specific normalizer
    normalizer = normalizers.get(language, TextNormalizer())
    normalized = normalizer.normalize_text(text)
    
    return {
        "text": normalized,
        "language": language,
        "confidence": lang_result["confidence"]
    }

# Process documents
documents = ["Hello world", "Bonjour le monde", "Hallo Welt"]
results = [process_multilingual_document(doc) for doc in documents]
```

---

## Best Practices

### 1. Choose Appropriate Normalization Level

```python
# Minimal normalization for entity extraction
minimal = TextNormalizer(
    fix_encoding=True,
    normalize_whitespace=True
)

# Moderate normalization for search
moderate = TextNormalizer(
    fix_encoding=True,
    normalize_whitespace=True,
    lowercase=True,
    remove_urls=True
)

# Aggressive normalization for topic modeling
aggressive = TextNormalizer(
    lowercase=True,
    remove_punctuation=True,
    remove_numbers=True,
    remove_urls=True,
    expand_contractions=True
)
```

### 2. Preserve Original Data

```python
# Always keep original text
doc.original_content = doc.content
doc.content = normalizer.normalize_text(doc.content)

# Store normalization metadata
doc.metadata["normalized"] = True
doc.metadata["normalization_config"] = normalizer.config
```

### 3. Batch Processing for Performance

```python
# Batch normalize for better performance
texts = [doc.content for doc in documents]
normalized_texts = normalizer.process_batch(texts)

for doc, normalized in zip(documents, normalized_texts):
    doc.content = normalized
```

---

## Troubleshooting

### Common Issues

**Issue**: Encoding errors with special characters

```python
# Solution: Enable encoding fix
normalizer = TextNormalizer(fix_encoding=True)

# Or manually fix encoding
from veritasreason.normalize import handle_encoding
fixed_text, confidence = handle_encoding(problematic_text, operation="convert", source_encoding="latin-1")
```

**Issue**: Over-normalization losing important information

```python
# Solution: Use conservative settings
normalizer = TextNormalizer(
    lowercase=False,           # Keep case
    remove_punctuation=False,  # Keep punctuation
    remove_numbers=False       # Keep numbers
)
```

**Issue**: Slow processing for large documents

```python
# Solution: Use batch processing
normalizer = TextNormalizer()
normalized = normalizer.process_batch(documents)
```

---

## Components

Key supporting classes available in `veritasreason.normalize`:

- `UnicodeNormalizer` — Unicode processing (NFC/NFD/NFKC/NFKD), special chars
- `WhitespaceNormalizer` — Line breaks, indentation, whitespace cleanup
- `SpecialCharacterProcessor` — Punctuation and diacritic handling
- `TextCleaner` — HTML removal and sanitization utilities
- `AliasResolver` — Entity alias mapping
- `EntityDisambiguator` — Context-based entity disambiguation
- `NameVariantHandler` — Title and name variant handling
- `TimeZoneNormalizer` — Timezone conversion utilities
- `RelativeDateProcessor` — Relative date expressions (e.g., "3 days ago")
- `TemporalExpressionParser` — Date range and temporal phrase parsing
- `UnitConverter` — Unit normalization and conversion
- `CurrencyNormalizer` — Currency symbol/code parsing
- `ScientificNotationHandler` — Scientific notation parsing
- `DataCleaner` — General data cleaning utilities
- `DuplicateDetector` — Duplicate record detection
- `DataValidator` — Schema-based dataset validation
- `MissingValueHandler` — Missing value strategies
- `EncodingHandler` — Encoding detection and conversion
- `MethodRegistry` — Register and retrieve custom normalization methods
- `NormalizeConfig` — Module configuration manager

## Performance Tips

### Memory Optimization

```python
# Process documents in chunks
def normalize_large_corpus(documents, chunk_size=1000):
    normalizer = TextNormalizer()
    
    for i in range(0, len(documents), chunk_size):
        chunk = documents[i:i + chunk_size]
    normalized_chunk = normalizer.process_batch(chunk)
        yield from normalized_chunk
```

### Speed Optimization

```python
# Disable unnecessary features
fast_normalizer = TextNormalizer(
    fix_encoding=False,        # Skip if encoding is known good
    normalize_unicode=False,   # Skip if not needed
    remove_diacritics=False    # Skip if not needed
)

# Use parallel processing
# Batch processing
normalized_docs = normalizer.process_batch(documents)
```

---

## See Also

- [Parse Module](parse.md) - Document parsing and extraction
- [Semantic Extract Module](semantic_extract.md) - Entity and relation extraction
- [Split Module](split.md) - Text chunking and splitting
- [Ingest Module](ingest.md) - Data ingestion

## Cookbook

Interactive tutorials to learn data normalization:

- **[Data Normalization](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/04_Data_Normalization.ipynb)**: Pipelines for cleaning, normalizing, and preparing text
  - **Topics**: Text cleaning, Unicode, formatting, language detection, entity normalization
  - **Difficulty**: Beginner
  - **Use Cases**: Data preprocessing, text cleaning, standardization
