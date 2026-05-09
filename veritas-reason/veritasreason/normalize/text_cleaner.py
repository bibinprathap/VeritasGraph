"""
Text Cleaning Module

This module provides comprehensive text cleaning and preprocessing capabilities
for the VeritasReason framework, enabling removal of HTML, normalization of
whitespace and Unicode, and text sanitization.

Key Features:
    - HTML tag removal (with BeautifulSoup support)
    - Whitespace normalization
    - Unicode normalization (NFC, NFD, NFKC, NFKD)
    - Special character removal
    - Text sanitization (security-focused)
    - Batch processing

Main Classes:
    - TextCleaner: Text cleaning coordinator

Example Usage:
    >>> from veritasreason.normalize import TextCleaner
    >>> cleaner = TextCleaner()
    >>> cleaned = cleaner.clean(text, remove_html=True, normalize_whitespace=True)
    >>> sanitized = cleaner.sanitize(text)

Author: VeritasReason Contributors
License: MIT
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Union

try:
    from bs4 import BeautifulSoup

    BEAUTIFULSOUP_AVAILABLE = True
except (ImportError, OSError):
    BEAUTIFULSOUP_AVAILABLE = False
    BeautifulSoup = None

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class TextCleaner:
    """
    Text cleaning coordinator.

    This class provides comprehensive text cleaning capabilities, including
    HTML removal, whitespace normalization, Unicode normalization, and
    text sanitization.

    Features:
        - HTML tag removal (with BeautifulSoup support)
        - Whitespace normalization
        - Unicode normalization
        - Special character removal
        - Text sanitization
        - Batch processing

    Example Usage:
        >>> cleaner = TextCleaner()
        >>> cleaned = cleaner.clean(text, remove_html=True)
        >>> sanitized = cleaner.sanitize(text)
        >>> batch_cleaned = cleaner.clean_batch(texts)
    """

    def __init__(self, **config):
        """
        Initialize text cleaner.

        Sets up the cleaner with configuration options.

        Args:
            **config: Configuration options (currently unused)
        """
        self.logger = get_logger("text_cleaner")
        self.config = config

        if not BEAUTIFULSOUP_AVAILABLE:
            self.logger.warning(
                "BeautifulSoup not available, HTML removal will use regex fallback"
            )

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("Text cleaner initialized")

    def clean(
        self,
        text: str,
        remove_html: bool = True,
        normalize_whitespace: bool = True,
        normalize_unicode: bool = True,
        remove_special_chars: bool = False,
        unicode_form: str = "NFC",
        allow_spaces: bool = True,
        **options,
    ) -> str:
        """
        Clean text with various options.

        This method performs comprehensive text cleaning by applying multiple
        cleaning operations in sequence: HTML removal, Unicode normalization,
        whitespace normalization, and special character removal.

        Args:
            text: Input text to clean
            remove_html: Whether to remove HTML tags (default: True)
            normalize_whitespace: Whether to normalize whitespace (default: True)
            normalize_unicode: Whether to normalize Unicode (default: True)
            remove_special_chars: Whether to remove special characters (default: False)
            unicode_form: Unicode normalization form (default: "NFC"):
                - "NFC": Canonical composition
                - "NFD": Canonical decomposition
                - "NFKC": Compatibility composition
                - "NFKD": Compatibility decomposition
            allow_spaces: Whether to allow spaces when removing special chars (default: True)
            **options: Additional cleaning options (unused)

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        cleaned = text

        # Remove HTML tags
        if remove_html:
            cleaned = self.remove_html(cleaned)

        # Normalize unicode
        if normalize_unicode:
            cleaned = self.normalize_unicode(cleaned, form=unicode_form)

        # Normalize whitespace
        if normalize_whitespace:
            cleaned = self.normalize_whitespace(cleaned)

        # Remove special characters
        if remove_special_chars:
            cleaned = self.remove_special_chars(cleaned, allow_spaces=allow_spaces)

        return cleaned.strip()

    def remove_html(self, text: str, preserve_structure: bool = False) -> str:
        """
        Remove HTML tags from text.

        This method removes HTML tags from text, optionally preserving structure
        using BeautifulSoup for better parsing.

        Args:
            text: Input text containing HTML tags
            preserve_structure: Whether to preserve structure using BeautifulSoup
                              (default: False, uses regex if False or BeautifulSoup
                              unavailable)

        Returns:
            str: Text without HTML tags and with HTML entities decoded
        """
        if not text:
            return ""

        if preserve_structure and BEAUTIFULSOUP_AVAILABLE and BeautifulSoup:
            try:
                soup = BeautifulSoup(text, "html.parser")
                return soup.get_text(separator="\n", strip=True)
            except Exception as e:
                self.logger.warning(
                    f"BeautifulSoup parsing failed, using regex fallback: {e}"
                )
                # Fallback to regex
                pass

        # Remove HTML tags using regex
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        # Remove remaining HTML entities
        text = re.sub(r"&#?\w+;", "", text)

        return text

    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text.

        This method normalizes whitespace by replacing tabs and newlines with
        spaces and collapsing multiple spaces into single spaces.

        Args:
            text: Input text with potentially irregular whitespace

        Returns:
            str: Text with normalized whitespace (tabs/newlines -> spaces,
                 multiple spaces -> single space)
        """
        if not text:
            return ""

        # Replace tabs and newlines with spaces
        text = re.sub(r"[\t\n\r]+", " ", text)

        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        return text.strip()

    def normalize_unicode(self, text: str, form: str = "NFC") -> str:
        """
        Normalize Unicode characters.

        This method normalizes Unicode characters using the specified
        normalization form.

        Args:
            text: Input text to normalize
            form: Unicode normalization form (default: "NFC"):
                - "NFC": Canonical composition
                - "NFD": Canonical decomposition
                - "NFKC": Compatibility composition
                - "NFKD": Compatibility decomposition

        Returns:
            str: Unicode-normalized text (returns original text if normalization fails)
        """
        if not text:
            return ""

        try:
            return unicodedata.normalize(form, text)
        except Exception as e:
            self.logger.warning(f"Failed to normalize unicode: {e}")
            return text

    def remove_special_chars(
        self, text: str, allow_spaces: bool = True, allow_newlines: bool = False
    ) -> str:
        """
        Remove special characters from text.

        This method removes special characters from text, keeping only
        alphanumeric characters and optionally spaces and newlines.

        Args:
            text: Input text to process
            allow_spaces: Whether to allow spaces (default: True)
            allow_newlines: Whether to allow newlines (default: False)

        Returns:
            str: Text with special characters removed, keeping only:
                - Alphanumeric characters
                - Spaces (if allow_spaces=True)
                - Newlines (if allow_newlines=True)
        """
        if not text:
            return ""

        if allow_spaces and allow_newlines:
            # Keep alphanumeric, spaces, and newlines
            pattern = r"[^a-zA-Z0-9\s]"
        elif allow_spaces:
            # Keep alphanumeric and spaces
            pattern = r"[^a-zA-Z0-9 ]"
        else:
            # Keep only alphanumeric
            pattern = r"[^a-zA-Z0-9]"

        return re.sub(pattern, "", text)

    def sanitize(self, text: str, remove_data_urls: bool = False, **options) -> str:
        """
        Sanitize text for security.

        This method sanitizes text by removing potentially dangerous content
        like script tags, iframe tags, and javascript: URLs.

        Args:
            text: Input text to sanitize
            remove_data_urls: Whether to remove data: URLs (default: False)
            **options: Additional sanitization options (unused)

        Returns:
            str: Sanitized text with dangerous content removed
        """
        if not text:
            return ""

        # Remove potential script tags
        text = re.sub(
            r"<script[^>]*>.*?</script(?:\s[^>]*)?>", "", text, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(
            r"<iframe[^>]*>.*?</iframe(?:\s[^>]*)?>", "", text, flags=re.IGNORECASE | re.DOTALL
        )

        # Remove javascript: URLs
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

        # Remove data: URLs if requested
        if remove_data_urls:
            text = re.sub(r"data:[^;]*;base64,", "", text, flags=re.IGNORECASE)

        return text

    def trim(self, text: str, remove_empty_lines: bool = False, **options) -> str:
        """
        Trim text.

        This method trims leading and trailing whitespace from text, optionally
        removing empty lines.

        Args:
            text: Input text to trim
            remove_empty_lines: Whether to remove empty lines (default: False)
            **options: Additional trimming options (unused)

        Returns:
            str: Trimmed text with leading/trailing whitespace removed
        """
        if not text:
            return ""

        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove empty lines if requested
        if remove_empty_lines:
            lines = [line for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

        return text

    def clean_batch(self, texts: List[str], **options) -> List[str]:
        """
        Clean multiple texts in batch.

        This method processes multiple texts in batch, applying the same
        cleaning operations to each text.

        Args:
            texts: List of texts to clean
            **options: Cleaning options (passed to clean method)

        Returns:
            list: List of cleaned texts (one per input text)
        """
        return [self.clean(text, **options) for text in texts]
