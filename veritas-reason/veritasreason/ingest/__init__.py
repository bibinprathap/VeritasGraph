"""
Data Ingestion Module

This module provides comprehensive data ingestion capabilities from various sources
including files, web content, feeds, streams, repositories, emails, and databases.

Algorithms Used:

File Ingestion:
    - File Type Detection: Multi-method detection (extension-based, MIME type, magic number analysis)
    - Directory Scanning: Recursive directory traversal with filtering
    - Cloud Storage Integration: AWS S3, Google Cloud Storage, Azure Blob Storage API integration
    - File Validation: Size limits, format validation, content verification
    - Batch Processing: Parallel file processing with progress tracking
    - Magic Number Analysis: Binary file signature detection for accurate type identification

Web Ingestion:
    - HTTP Request Handling: GET/POST requests with retry logic and error handling
    - Rate Limiting: Time-based delay enforcement between requests
    - Robots.txt Compliance: RobotFileParser-based robots.txt checking and URL filtering
    - Content Extraction: BeautifulSoup-based HTML parsing and text extraction
    - Sitemap Crawling: XML sitemap parsing and URL discovery
    - Link Discovery: HTML link extraction and domain filtering
    - JavaScript Rendering: Optional Selenium/Playwright integration for dynamic content
    - URL Normalization: URL parsing, joining, and canonicalization

Feed Ingestion:
    - RSS/Atom Parsing: XML parsing with format auto-detection
    - Feed Discovery: HTML link tag parsing for feed discovery
    - Date Parsing: Multiple date format parsing (RFC 822, ISO 8601, etc.)
    - Feed Validation: XML schema validation and format verification
    - Update Monitoring: Polling-based feed update detection with callbacks
    - Content Extraction: Feed item content and metadata extraction

Stream Ingestion:
    - Kafka Processing: Kafka consumer group management and message processing
    - RabbitMQ Processing: AMQP protocol handling and queue management
    - AWS Kinesis Processing: Kinesis stream reading and shard management
    - Apache Pulsar Processing: Pulsar consumer and subscription management
    - Message Transformation: Custom transformation pipeline for stream messages
    - Error Handling: Retry logic, dead letter queue handling, error recovery
    - Stream Monitoring: Health checks, metrics collection, performance monitoring
    - Partition Management: Partition assignment and load balancing

Repository Ingestion:
    - Git Operations: Repository cloning, branch checking, commit traversal
    - Code Extraction: File content extraction with language detection
    - Commit Analysis: Git log parsing, diff analysis, statistics calculation
    - Language Detection: File extension and content-based programming language identification
    - Code Structure Analysis: AST parsing for classes, functions, imports extraction
    - Dependency Analysis: Package manager file parsing (requirements.txt, package.json, etc.)
    - Documentation Extraction: README, docstring, and comment extraction

Email Ingestion:
    - IMAP Protocol: IMAP connection, mailbox selection, message retrieval
    - POP3 Protocol: POP3 connection and message downloading
    - Email Parsing: RFC 822 email message parsing with header and body extraction
    - Attachment Processing: MIME attachment extraction and file saving
    - Content Extraction: Plain text and HTML body extraction with BeautifulSoup
    - Thread Analysis: Message-ID and In-Reply-To header-based conversation threading
    - Link Extraction: URL extraction from email HTML content

Database Ingestion:
    - Database Connection: SQLAlchemy-based connection management with connection pooling
    - SQL Query Execution: Parameterized query execution with result set processing
    - Schema Introspection: Database schema analysis and table/column discovery
    - Data Type Conversion: Database-specific type to Python type conversion
    - Pagination: Large dataset processing with LIMIT/OFFSET or cursor-based pagination
    - Data Export: Result set to dictionary/JSON conversion
    - Multi-database Support: PostgreSQL, MySQL, SQLite, Oracle, SQL Server abstraction

Key Features:
    - Multiple ingestion source types (file, web, feed, stream, repo, email, db)
    - Unified ingestion function with source type dispatch
    - Method registry for extensibility
    - Configuration management with environment variables and config files
    - Batch processing and progress tracking
    - Error handling and retry logic
    - Content extraction and transformation

Main Classes:
    - FileIngestor: Local and cloud file processing
    - WebIngestor: Web scraping and crawling
    - FeedIngestor: RSS/Atom feed processing
    - StreamIngestor: Real-time stream processing
    - RepoIngestor: Git repository processing
    - EmailIngestor: Email protocol handling
    - DBIngestor: Database export handling
    - OntologyIngestor: Ontology file processing
    - MethodRegistry: Registry for custom ingestion methods
    - IngestConfig: Configuration manager for ingest module

Convenience Functions:
    - ingest: Unified ingestion function with source type dispatch
    - ingest_file: File ingestion wrapper
    - ingest_web: Web ingestion wrapper
    - ingest_feed: Feed ingestion wrapper
    - ingest_stream: Stream ingestion wrapper
    - ingest_repository: Repository ingestion wrapper
    - ingest_email: Email ingestion wrapper
    - ingest_database: Database ingestion wrapper
    - ingest_ontology: Ontology ingestion wrapper


Example Usage:
    >>> from veritasreason.ingest import ingest, ingest_file, ingest_web
    >>> # Unified ingestion
    >>> result = ingest("document.pdf", source_type="file")
    >>> # File ingestion
    >>> files = ingest_file("./documents", method="directory")
    >>> # Web ingestion
    >>> content = ingest_web("https://example.com", method="url")
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .config import IngestConfig, ingest_config
from .db_ingestor import DatabaseConnector, DataExporter, DBIngestor, TableData
from .email_ingestor import AttachmentProcessor, EmailData, EmailIngestor
from .email_ingestor import EmailParser as EmailIngestorParser
from .feed_ingestor import FeedData, FeedIngestor, FeedItem, FeedMonitor, FeedParser
from .file_ingestor import (
    CloudStorageIngestor,
    FileIngestor,
    FileObject,
    FileTypeDetector,
)
from .mcp_client import MCPClient, MCPResource, MCPTool
from .mcp_ingestor import MCPData, MCPIngestor
from .methods import (
    get_ingest_method,
    ingest,
    ingest_database,
    ingest_email,
    ingest_feed,
    ingest_file,
    ingest_mcp,
    ingest_ontology,
    ingest_repository,
    ingest_stream,
    ingest_web,
    list_available_methods,
)
from .registry import MethodRegistry, method_registry
from .repo_ingestor import (
    CodeExtractor,
    CodeFile,
    CommitInfo,
    GitAnalyzer,
    RepoIngestor,
)
from .stream_ingestor import (
    KafkaProcessor,
    KinesisProcessor,
    PulsarProcessor,
    RabbitMQProcessor,
    StreamIngestor,
    StreamMessage,
    StreamMonitor,
    StreamProcessor,
)
from .web_ingestor import (
    ContentExtractor,
    RateLimiter,
    RobotsChecker,
    SitemapCrawler,
    WebContent,
    WebIngestor,
)

from .ontology_ingestor import OntologyData, OntologyIngestor
from .snowflake_ingestor import SnowflakeConnector, SnowflakeData, SnowflakeIngestor

__all__ = [
    # File ingestion
    "FileIngestor",
    "FileObject",
    "FileTypeDetector",
    "CloudStorageIngestor",
    # Web ingestion
    "WebIngestor",
    "WebContent",
    "RateLimiter",
    "RobotsChecker",
    "ContentExtractor",
    "SitemapCrawler",
    # Feed ingestion
    "FeedIngestor",
    "FeedItem",
    "FeedData",
    "FeedParser",
    "FeedMonitor",
    # Stream ingestion
    "StreamIngestor",
    "StreamMessage",
    "StreamProcessor",
    "KafkaProcessor",
    "RabbitMQProcessor",
    "KinesisProcessor",
    "PulsarProcessor",
    "StreamMonitor",
    # Repository ingestion
    "RepoIngestor",
    "CodeFile",
    "CommitInfo",
    "CodeExtractor",
    "GitAnalyzer",
    # Email ingestion
    "EmailIngestor",
    "EmailData",
    "AttachmentProcessor",
    "EmailIngestorParser",
    # Database ingestion
    "DBIngestor",
    "TableData",
    "DatabaseConnector",
    "DataExporter",
    # MCP ingestion
    "MCPIngestor",
    "MCPData",
    "MCPClient",
    "MCPResource",
    "MCPTool",
    # Ontology ingestion
    "OntologyIngestor",
    "OntologyData",
    # Snowflake ingestion
    "SnowflakeIngestor",
    "SnowflakeData",
    "SnowflakeConnector",
    # Registry and Methods
    "MethodRegistry",
    "method_registry",
    "ingest",
    "ingest_file",
    "ingest_web",
    "ingest_feed",
    "ingest_stream",
    "ingest_repository",
    "ingest_email",
    "ingest_database",
    "ingest_ontology",
    "ingest_mcp",
    "get_ingest_method",
    "list_available_methods",
    # Configuration
    "IngestConfig",
    "ingest_config",
]

