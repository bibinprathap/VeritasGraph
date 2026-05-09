"""
Document Parsing Module

This module handles parsing of various document formats including PDF, DOCX,
HTML, and plain text files, extracting text content, metadata, and document structure.

Key Features:
    - PDF text and metadata extraction
    - DOCX content parsing
    - HTML content cleaning
    - Plain text processing
    - Document structure analysis
    - Batch document processing
    - Password-protected document handling
    - Embedded image and table extraction

Main Classes:
    - DocumentParser: Main document parsing class

Example Usage:
    >>> from veritasreason.parse import DocumentParser
    >>> parser = DocumentParser()
    >>> text = parser.parse_document("document.pdf")
    >>> metadata = parser.extract_metadata("document.docx")
    >>> documents = parser.parse_batch(["doc1.pdf", "doc2.docx"])

Author: VeritasReason Contributors
License: MIT
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .docx_parser import DOCXParser
from .html_parser import HTMLParser
from .pdf_parser import PDFParser

# DoclingParser is available as a standalone parser
# Import it directly: from veritasreason.parse import DoclingParser


class DocumentParser:
    """
    Document format parsing handler.

    • Parses various document formats (PDF, DOCX, HTML, TXT)
    • Extracts text content and metadata
    • Handles document structure and formatting
    • Processes embedded images and tables
    • Supports batch document processing
    • Handles password-protected documents

    Attributes:
        • pdf_parser: PDF parsing engine
        • docx_parser: DOCX parsing engine
        • html_parser: HTML parsing engine
        • text_parser: Plain text processor
        • supported_formats: List of supported formats

    Methods:
        • parse_document(): Parse any document format
        • extract_text(): Extract text content
        • extract_metadata(): Extract document metadata
        • parse_batch(): Process multiple documents
    """

    def __init__(self, config=None, **kwargs):
        """
        Initialize document parser.

        • Setup format-specific parsers
        • Configure parsing options
        • Initialize metadata extractors
        • Setup error handling
        • Configure batch processing
        """
        self.logger = get_logger("document_parser")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize format-specific parsers
        self.pdf_parser = PDFParser(**self.config.get("pdf", {}))
        self.docx_parser = DOCXParser(**self.config.get("docx", {}))
        self.html_parser = HTMLParser(**self.config.get("html", {}))

        # Supported formats
        self.supported_formats = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".doc": "docx",
            ".html": "html",
            ".htm": "html",
            ".txt": "text",
            ".text": "text",
        }

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

    def parse(
        self,
        source: Union[str, Path, List[Union[str, Path]], List[Any]],
        **options,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Alias for parse_document or parse_batch.
        Handles FileObject lists as well.

        Args:
            source: Path(s) or FileObject(s)
            **options: Parsing options

        Returns:
            Parsed document(s)
        """
        if isinstance(source, list):
            # Extract paths if FileObjects
            paths = []
            for item in source:
                if hasattr(item, "path"):
                    paths.append(item.path)
                elif isinstance(item, (str, Path)):
                    paths.append(item)
                else:
                    raise ValueError(f"Unsupported item type in list: {type(item)}")

            # Use parse_batch
            batch_result = self.parse_batch(paths, **options)
            # Return list of results (successful ones)
            return [item["result"] for item in batch_result["successful"]]
        else:
            return self.parse_document(source, **options)

    def parse_document(
        self, file_path: Union[str, Path], file_type: Optional[str] = None, **options
    ) -> Dict[str, Any]:
        """
        Parse document of any supported format.

        • Detect document format if not specified
        • Route to appropriate format parser
        • Extract text content and structure
        • Extract metadata and properties
        • Handle parsing errors gracefully
        • Return parsed document object

        Args:
            file_path: Path to document file
            file_type: Document type (auto-detected if None)
            **options: Parsing options

        Returns:
            dict: Parsed document data
        """
        file_path = Path(file_path)

        # Track document parsing
        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="parse",
            submodule="DocumentParser",
            message=f"Document: {file_path.name}",
        )

        try:
            if not file_path.exists():
                raise ValidationError(f"Document file not found: {file_path}")

            # Detect file type if not specified
            if file_type is None:
                file_type = self._detect_file_type(file_path)

            self.progress_tracker.update_tracking(
                tracking_id, message=f"Parsing {file_type} document"
            )

            # Route to appropriate parser
            try:
                if file_type == "pdf":
                    result = self.pdf_parser.parse(file_path, **options)
                elif file_type == "docx":
                    result = self.docx_parser.parse(file_path, **options)
                elif file_type == "html":
                    result = self.html_parser.parse(file_path, **options)
                elif file_type == "text":
                    result = self._parse_text(file_path, **options)
                else:
                    raise ValidationError(f"Unsupported document format: {file_type}")

                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Parsed {file_path.name} ({file_type})",
                )
                return result

            except Exception as e:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message=str(e)
                )
                self.logger.error(f"Failed to parse document {file_path}: {e}")
                raise ProcessingError(f"Failed to parse document: {e}")

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def extract_text(self, file_path: Union[str, Path], **options) -> str:
        """
        Extract text content from document.

        • Parse document content
        • Extract all text elements
        • Preserve text structure and formatting
        • Handle special characters and encoding
        • Clean and normalize text
        • Return extracted text content

        Args:
            file_path: Path to document file
            **options: Parsing options

        Returns:
            str: Extracted text content
        """
        file_path = Path(file_path)
        file_type = self._detect_file_type(file_path)

        if file_type == "pdf":
            return self.pdf_parser.extract_text(file_path, **options)
        elif file_type == "docx":
            return self.docx_parser.extract_text(file_path)
        elif file_type == "html":
            return self.html_parser.extract_text(
                file_path, clean=options.get("clean", True)
            )
        elif file_type == "text":
            return self._parse_text(file_path, **options).get("text", "")
        else:
            raise ValidationError(f"Unsupported document format: {file_type}")

    def extract_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract document metadata and properties.

        • Parse document properties
        • Extract creation and modification dates
        • Get author and title information
        • Extract document statistics
        • Return metadata dictionary

        Args:
            file_path: Path to document file

        Returns:
            dict: Document metadata
        """
        file_path = Path(file_path)
        file_type = self._detect_file_type(file_path)

        result = self.parse_document(
            file_path, file_type=file_type, extract_tables=False, extract_images=False
        )
        return result.get("metadata", {})

    def parse_batch(
        self, file_paths: List[Union[str, Path]], **options
    ) -> Dict[str, Any]:
        """
        Parse multiple documents in batch.

        • Process multiple files concurrently
        • Track parsing progress
        • Handle individual file errors
        • Collect parsing results
        • Return batch processing results

        Args:
            file_paths: List of document file paths
            **options: Parsing options:
                - max_workers: Maximum parallel workers
                - continue_on_error: Continue on errors (default: True)

        Returns:
            dict: Batch processing results
        """
        # Track batch parsing
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="parse",
            submodule="DocumentParser",
            message=f"Parsing {len(file_paths)} documents in batch",
        )

        try:
            results = {"successful": [], "failed": [], "total": len(file_paths)}

            continue_on_error = options.get("continue_on_error", True)
            total_files = len(file_paths)
            update_interval = max(1, total_files // 20)  # Update every 5%

            for idx, file_path in enumerate(file_paths, 1):
                try:
                    result = self.parse_document(file_path, **options)
                    results["successful"].append(
                        {"file_path": str(file_path), "result": result}
                    )
                except Exception as e:
                    error_info = {
                        "file_path": str(file_path),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                    results["failed"].append(error_info)

                    if not continue_on_error:
                        self.progress_tracker.stop_tracking(
                            tracking_id, status="failed", message=str(e)
                        )
                        raise ProcessingError(
                            f"Batch processing failed at {file_path}: {e}"
                        )
                
                # Update progress periodically
                if idx % update_interval == 0 or idx == total_files:
                    self.progress_tracker.update_progress(
                        tracking_id,
                        processed=idx,
                        total=total_files,
                        message=f"Parsing documents... {idx}/{total_files}"
                    )

            results["success_count"] = len(results["successful"])
            results["failure_count"] = len(results["failed"])

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Parsed {results['success_count']}/{total_files} documents successfully",
            )
            return results

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect document file type from extension."""
        suffix = file_path.suffix.lower()
        return self.supported_formats.get(suffix, "unknown")

    def _parse_text(self, file_path: Path, **options) -> Dict[str, Any]:
        """Parse plain text file."""
        encoding = options.get("encoding", "utf-8")

        try:
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                text = f.read()

            return {
                "text": text,
                "metadata": {
                    "file_path": str(file_path),
                    "encoding": encoding,
                    "size": len(text),
                },
                "full_text": text,
            }
        except Exception as e:
            self.logger.error(f"Failed to parse text file {file_path}: {e}")
            raise ProcessingError(f"Failed to parse text file: {e}")
