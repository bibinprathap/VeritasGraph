"""
Encoding Handling Module

This module provides comprehensive encoding detection, conversion, and handling
capabilities for the VeritasReason framework, enabling robust text processing across
various character encodings.

Key Features:
    - Encoding detection (chardet integration)
    - UTF-8 conversion with fallback support
    - BOM (Byte Order Mark) removal
    - File encoding detection and conversion
    - Encoding validation
    - Error handling strategies

Main Classes:
    - EncodingHandler: Encoding detection and conversion coordinator

Example Usage:
    >>> from veritasreason.normalize import EncodingHandler
    >>> handler = EncodingHandler()
    >>> encoding, confidence = handler.detect(data)
    >>> utf8_text = handler.convert_to_utf8(data)
    >>> content = handler.convert_file_to_utf8("input.txt", "output.txt")

Author: VeritasReason Contributors
License: MIT
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import chardet

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class EncodingHandler:
    """
    Encoding detection and conversion coordinator.

    This class provides comprehensive encoding handling capabilities, including
    detection, conversion, BOM removal, and validation.

    Features:
        - Encoding detection using chardet
        - UTF-8 conversion with fallback encodings
        - BOM removal (UTF-8, UTF-16)
        - File encoding detection and conversion
        - Encoding validation
        - Graceful error handling

    Example Usage:
        >>> handler = EncodingHandler()
        >>> encoding, confidence = handler.detect(data)
        >>> utf8_text = handler.convert_to_utf8(data, source_encoding="latin-1")
        >>> content = handler.convert_file_to_utf8("input.txt")
    """

    def __init__(self, **config):
        """
        Initialize encoding handler.

        Sets up the handler with default encoding and fallback encodings.

        Args:
            **config: Configuration options:
                - default_encoding: Default encoding (default: "utf-8")
                - fallback_encodings: List of fallback encodings to try
                                    (default: ["latin-1", "cp1252", "iso-8859-1"])
        """
        self.logger = get_logger("encoding_handler")
        self.config = config
        self.default_encoding = config.get("default_encoding", "utf-8")
        self.fallback_encodings = config.get(
            "fallback_encodings", ["latin-1", "cp1252", "iso-8859-1"]
        )

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug(
            f"Encoding handler initialized (default={self.default_encoding})"
        )

    def detect(self, data: Union[str, bytes], **options) -> Tuple[str, float]:
        """
        Detect encoding of data.

        This method detects the character encoding of input data using chardet.
        If data is a string, it's first encoded to UTF-8 bytes for detection.

        Args:
            data: Input data - can be string or bytes
            **options: Detection options (unused)

        Returns:
            tuple: (encoding_name, confidence_score) where:
                - encoding_name: Detected encoding name (e.g., "utf-8", "latin-1")
                - confidence_score: Confidence score between 0.0 and 1.0
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        if not data:
            return (self.default_encoding, 0.0)

        try:
            result = chardet.detect(data)
            if result:
                encoding = result.get("encoding", self.default_encoding)
                confidence = result.get("confidence", 0.0)
                return (encoding, confidence)
            else:
                return (self.default_encoding, 0.0)
        except Exception as e:
            self.logger.warning(f"Failed to detect encoding: {e}")
            return (self.default_encoding, 0.0)

    def detect_file(
        self, file_path: Union[str, Path], sample_size: int = 10000, **options
    ) -> Tuple[str, float]:
        """
        Detect encoding of file.

        This method detects the character encoding of a file by reading a sample
        of bytes and using chardet for detection.

        Args:
            file_path: Path to file (string or Path object)
            sample_size: Number of bytes to read for detection (default: 10000)
            **options: Additional detection options (unused)

        Returns:
            tuple: (encoding_name, confidence_score) where:
                - encoding_name: Detected encoding name
                - confidence_score: Confidence score between 0.0 and 1.0

        Raises:
            ValidationError: If file does not exist
            ProcessingError: If file reading or detection fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")

        try:
            with open(file_path, "rb") as f:
                sample = f.read(sample_size)

            return self.detect(sample, **options)
        except Exception as e:
            self.logger.error(f"Failed to detect file encoding: {e}")
            raise ProcessingError(f"Failed to detect file encoding: {e}") from e

    def convert_to_utf8(
        self, data: Union[str, bytes], source_encoding: Optional[str] = None, **options
    ) -> str:
        """
        Convert data to UTF-8.

        This method converts input data (string or bytes) to UTF-8 encoding.
        If source_encoding is not provided, it's auto-detected. Falls back to
        multiple encodings if initial conversion fails.

        Args:
            data: Input data - can be string or bytes
            source_encoding: Source encoding name (optional, auto-detected if None)
            **options: Additional conversion options (unused)

        Returns:
            str: UTF-8 encoded string

        Note:
            Uses 'replace' error handling strategy to handle invalid characters
            gracefully, replacing them with replacement characters.
        """
        if isinstance(data, str):
            # Already a string, just ensure it's valid UTF-8
            return data.encode("utf-8", errors="replace").decode("utf-8")

        if source_encoding is None:
            source_encoding, _ = self.detect(data, **options)

        # Try to decode with detected encoding
        try:
            return data.decode(source_encoding, errors="replace")
        except (UnicodeDecodeError, LookupError):
            # Try fallback encodings
            for encoding in self.fallback_encodings:
                try:
                    return data.decode(encoding, errors="replace")
                except (UnicodeDecodeError, LookupError):
                    continue

            # Final fallback: decode with errors replaced
            self.logger.warning(
                f"Failed to decode with detected encoding, using errors='replace'"
            )
            return data.decode(self.default_encoding, errors="replace")

    def convert_file_to_utf8(
        self,
        file_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        **options,
    ) -> str:
        """
        Convert file to UTF-8.

        This method reads a file, detects its encoding, converts it to UTF-8,
        and optionally writes it to an output file.

        Args:
            file_path: Path to input file (string or Path object)
            output_path: Path to output file (optional, if provided, writes
                        converted content to this file)
            **options: Additional conversion options (unused)

        Returns:
            str: Converted content as UTF-8 string

        Raises:
            ValidationError: If input file does not exist
            ProcessingError: If file reading or conversion fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"File not found: {file_path}")

        # Detect encoding
        source_encoding, _ = self.detect_file(file_path, **options)

        # Read file with detected encoding
        try:
            with open(file_path, "r", encoding=source_encoding, errors="replace") as f:
                content = f.read()
        except Exception as e:
            # Try fallback encodings
            content = None
            for encoding in self.fallback_encodings:
                try:
                    with open(file_path, "r", encoding=encoding, errors="replace") as f:
                        content = f.read()
                    break
                except Exception:
                    continue

            if content is None:
                self.logger.error(f"Failed to read file with any encoding: {e}")
                raise ProcessingError(f"Failed to read file: {e}") from e

        # Ensure content is UTF-8
        utf8_content = content.encode("utf-8", errors="replace").decode("utf-8")

        # Write to output file if specified
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(utf8_content)

        return utf8_content

    def remove_bom(self, data: Union[str, bytes]) -> Union[str, bytes]:
        """
        Remove BOM (Byte Order Mark) from data.

        This method removes BOM markers from the beginning of data, supporting
        UTF-8, UTF-16 LE, and UTF-16 BE BOMs.

        Args:
            data: Input data - can be string or bytes

        Returns:
            Union[str, bytes]: Data without BOM (same type as input)
        """
        if isinstance(data, bytes):
            # Remove UTF-8 BOM
            if data.startswith(b"\xef\xbb\xbf"):
                return data[3:]
            # Remove UTF-16 BOMs
            elif data.startswith(b"\xff\xfe"):
                return data[2:]
            elif data.startswith(b"\xfe\xff"):
                return data[2:]
            else:
                return data
        else:
            # String data - remove if present
            if data.startswith("\ufeff"):
                return data[1:]
            else:
                return data

    def handle_encoding_error(
        self, data: bytes, error_strategy: str = "replace", **options
    ) -> str:
        """
        Handle encoding errors gracefully.

        This method attempts to decode bytes data using detected encoding and
        fallback encodings, applying the specified error handling strategy.

        Args:
            data: Input bytes data
            error_strategy: Error handling strategy (default: "replace"):
                - "replace": Replace invalid characters with replacement char
                - "ignore": Ignore invalid characters
                - "strict": Raise exception on errors
            **options: Additional error handling options (unused)

        Returns:
            str: Decoded string with errors handled according to strategy
        """

        # Try detected encoding first
        encoding, _ = self.detect(data, **options)

        try:
            return data.decode(encoding, errors=error_strategy)
        except Exception:
            # Try fallback encodings
            for fallback_encoding in self.fallback_encodings:
                try:
                    return data.decode(fallback_encoding, errors=error_strategy)
                except Exception:
                    continue

            # Final fallback
            return data.decode(self.default_encoding, errors=error_strategy)

    def validate_encoding(
        self, data: Union[str, bytes], encoding: str, **options
    ) -> bool:
        """
        Validate that data can be decoded/encoded with given encoding.

        This method validates that the data can be successfully decoded (for bytes)
        or encoded (for strings) using the specified encoding without errors.

        Args:
            data: Input data - can be string or bytes
            encoding: Encoding name to validate (e.g., "utf-8", "latin-1")
            **options: Additional validation options (unused)

        Returns:
            bool: True if encoding is valid for data, False otherwise
        """
        if isinstance(data, str):
            try:
                data.encode(encoding)
                return True
            except Exception:
                return False
        else:
            try:
                data.decode(encoding, errors="strict")
                return True
            except Exception:
                return False
