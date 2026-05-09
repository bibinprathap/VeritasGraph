"""
Structural Chunker Module

This module provides document-aware splitting based on document structure
and formatting, preserving headings, paragraphs, lists, and code blocks.

Key Features:
    - Structure-aware chunking (headings, paragraphs, lists, code blocks)
    - Heading hierarchy preservation
    - Section boundary respect
    - Markdown structure detection
    - Configurable max chunk size
    - Element grouping and metadata

Main Classes:
    - StructuralChunker: Main structural chunking coordinator
    - StructuralElement: Structural element representation dataclass

Example Usage:
    >>> from veritasreason.split import StructuralChunker
    >>> chunker = StructuralChunker(respect_headers=True, max_chunk_size=2000)
    >>> chunks = chunker.chunk(structured_document)
    >>> elements = chunker._extract_structure(document)

Author: VeritasReason Contributors
License: MIT
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .semantic_chunker import Chunk


@dataclass
class StructuralElement:
    """Structural element representation."""

    type: str  # heading, paragraph, list, table, code_block
    text: str
    level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuralChunker:
    """Structural chunker for document-aware splitting."""

    def __init__(self, **config):
        """
        Initialize structural chunker.

        Args:
            **config: Configuration options:
                - respect_headers: Respect heading hierarchy (default: True)
                - respect_sections: Respect section boundaries (default: True)
                - max_chunk_size: Maximum chunk size
        """
        self.logger = get_logger("structural_chunker")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.respect_headers = config.get("respect_headers", True)
        self.respect_sections = config.get("respect_sections", True)
        self.max_chunk_size = config.get("max_chunk_size", 2000)

    def chunk(self, text: str, **options) -> List[Chunk]:
        """
        Split text based on document structure.

        Args:
            text: Input text to chunk
            **options: Chunking options

        Returns:
            list: List of chunks
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="split",
            submodule="StructuralChunker",
            message="Splitting text based on document structure",
        )

        try:
            if not text:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="completed", message="No text provided"
                )
                return []

            # Extract structural elements
            self.progress_tracker.update_tracking(
                tracking_id, message="Extracting structural elements..."
            )
            elements = self._extract_structure(text)

            # Group elements into chunks
            self.progress_tracker.update_tracking(
                tracking_id, message="Grouping elements into chunks..."
            )
            chunks = self._group_elements(elements, text)

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message=f"Created {len(chunks)} chunks"
            )
            return chunks

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _extract_structure(self, text: str) -> List[StructuralElement]:
        """Extract structural elements from text."""
        elements = []
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Detect headings (# for markdown, or all caps lines)
            if line.startswith("#") or self._is_heading(line, lines, i):
                level = (
                    len(re.match(r"^#+", line).group()) if line.startswith("#") else 1
                )
                elements.append(
                    StructuralElement(
                        type="heading",
                        text=line,
                        level=level,
                        metadata={"line_number": i + 1},
                    )
                )

            # Detect lists
            elif re.match(r"^[-*+]\s|^\d+\.\s", line):
                list_items = [line]
                j = i + 1
                while j < len(lines) and (
                    re.match(r"^[-*+]\s|^\d+\.\s", lines[j].strip())
                    or not lines[j].strip()
                ):
                    if lines[j].strip():
                        list_items.append(lines[j].strip())
                    j += 1

                elements.append(
                    StructuralElement(
                        type="list",
                        text="\n".join(list_items),
                        level=0,
                        metadata={"item_count": len(list_items), "line_number": i + 1},
                    )
                )
                i = j - 1

            # Detect code blocks
            elif line.startswith("```") or line.startswith("    "):
                code_lines = [line]
                j = i + 1
                if line.startswith("```"):
                    # Find closing ```
                    while j < len(lines) and not lines[j].strip().startswith("```"):
                        code_lines.append(lines[j])
                        j += 1
                    if j < len(lines):
                        code_lines.append(lines[j])
                        j += 1
                else:
                    # Indented code block
                    while j < len(lines) and (
                        lines[j].startswith("    ") or not lines[j].strip()
                    ):
                        code_lines.append(lines[j])
                        j += 1

                elements.append(
                    StructuralElement(
                        type="code_block",
                        text="\n".join(code_lines),
                        level=0,
                        metadata={"line_number": i + 1},
                    )
                )
                i = j - 1

            # Regular paragraph
            else:
                para_lines = [line]
                j = i + 1
                while (
                    j < len(lines)
                    and lines[j].strip()
                    and not self._is_structure_element(lines[j])
                ):
                    para_lines.append(lines[j].strip())
                    j += 1

                paragraph_text = " ".join(para_lines)
                if paragraph_text:
                    elements.append(
                        StructuralElement(
                            type="paragraph",
                            text=paragraph_text,
                            level=0,
                            metadata={"line_number": i + 1},
                        )
                    )
                i = j - 1

            i += 1

        return elements

    def _is_heading(self, line: str, all_lines: List[str], index: int) -> bool:
        """Check if line is a heading."""
        # All caps line followed by blank line
        if line.isupper() and len(line) > 3 and index + 1 < len(all_lines):
            if not all_lines[index + 1].strip():
                return True

        # Line ending with colon and short
        if line.endswith(":") and len(line) < 100:
            return True

        return False

    def _is_structure_element(self, line: str) -> bool:
        """Check if line is a structural element."""
        return (
            line.startswith("#")
            or re.match(r"^[-*+]\s|^\d+\.\s", line)
            or line.startswith("```")
            or line.startswith("    ")
        )

    def _group_elements(
        self, elements: List[StructuralElement], original_text: str
    ) -> List[Chunk]:
        """Group structural elements into chunks."""
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_start = 0

        for element in elements:
            element_size = len(element.text)

            # Check if adding this element would exceed max size
            if current_size + element_size > self.max_chunk_size and current_chunk:
                # Create chunk from current elements
                chunk_text = "\n\n".join([e.text for e in current_chunk])
                start_pos = original_text.find(chunk_text[:50], chunk_start)
                end_pos = (
                    start_pos + len(chunk_text)
                    if start_pos >= 0
                    else chunk_start + len(chunk_text)
                )

                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_index=start_pos if start_pos >= 0 else chunk_start,
                        end_index=end_pos,
                        metadata={
                            "element_count": len(current_chunk),
                            "element_types": [e.type for e in current_chunk],
                            "structure_preserved": True,
                        },
                    )
                )

                chunk_start = end_pos
                current_chunk = []
                current_size = 0

            # Add element to current chunk
            current_chunk.append(element)
            current_size += element_size

            # If we hit a major heading, consider breaking here
            if (
                self.respect_headers
                and element.type == "heading"
                and element.level <= 2
                and current_chunk
            ):
                # Save current chunk (excluding the heading if it's new)
                if len(current_chunk) > 1:
                    chunk_elements = current_chunk[:-1]
                    chunk_text = "\n\n".join([e.text for e in chunk_elements])
                    start_pos = original_text.find(chunk_text[:50], chunk_start)
                    end_pos = (
                        start_pos + len(chunk_text)
                        if start_pos >= 0
                        else chunk_start + len(chunk_text)
                    )

                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            start_index=start_pos if start_pos >= 0 else chunk_start,
                            end_index=end_pos,
                            metadata={
                                "element_count": len(chunk_elements),
                                "element_types": [e.type for e in chunk_elements],
                                "structure_preserved": True,
                            },
                        )
                    )

                    chunk_start = end_pos
                    current_chunk = [element]
                    current_size = len(element.text)

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join([e.text for e in current_chunk])
            start_pos = original_text.find(chunk_text[:50], chunk_start)
            end_pos = (
                start_pos + len(chunk_text) if start_pos >= 0 else len(original_text)
            )

            chunks.append(
                Chunk(
                    text=chunk_text,
                    start_index=start_pos if start_pos >= 0 else chunk_start,
                    end_index=end_pos,
                    metadata={
                        "element_count": len(current_chunk),
                        "element_types": [e.type for e in current_chunk],
                        "structure_preserved": True,
                    },
                )
            )

        return chunks
