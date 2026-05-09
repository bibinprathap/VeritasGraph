"""
Table Chunker Module

This module provides specialized chunking for tabular data while preserving
table structure and relationships, supporting both row-based and column-based chunking.

Key Features:
    - Row-based table chunking
    - Column-based table chunking
    - Header preservation
    - Table schema extraction
    - Text conversion for table chunks
    - Column type inference

Main Classes:
    - TableChunker: Main table chunking coordinator
    - TableChunk: Table chunk representation dataclass

Example Usage:
    >>> from veritasreason.split import TableChunker
    >>> chunker = TableChunker(max_rows=100, preserve_headers=True)
    >>> table_chunks = chunker.chunk_table(table_data)
    >>> text_chunks = chunker.chunk_to_text_chunks(table_data)
    >>> schema = chunker.extract_table_schema(table_data)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .semantic_chunker import Chunk


@dataclass
class TableChunk:
    """Table chunk representation."""

    rows: List[List[str]]
    headers: List[str]
    start_row: int
    end_row: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TableChunker:
    """Table-aware chunker for tabular data."""

    def __init__(self, **config):
        """
        Initialize table chunker.

        Args:
            **config: Configuration options:
                - max_rows: Maximum rows per chunk (default: 100)
                - preserve_headers: Include headers in each chunk (default: True)
                - chunk_by_columns: Chunk by columns instead of rows (default: False)
        """
        self.logger = get_logger("table_chunker")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.max_rows = config.get("max_rows", 100)
        self.preserve_headers = config.get("preserve_headers", True)
        self.chunk_by_columns = config.get("chunk_by_columns", False)

    def chunk(self, text: str) -> List[Chunk]:
        """
        Chunk text containing a table (alias for compatibility).
        Attempts to parse markdown table from text.

        Args:
            text: Text containing a markdown table

        Returns:
            list: List of text chunks
        """
        # Simple markdown table parser
        lines = text.strip().split("\n")
        headers = []
        rows = []
        
        # Find header line (starts with | and not a separator line)
        header_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("|") and "---" not in line:
                headers = [c.strip() for c in line.strip().strip("|").split("|")]
                header_idx = i
                break
        
        if header_idx != -1:
            # Parse rows
            for line in lines[header_idx + 1:]:
                if line.strip().startswith("|") and "---" not in line:
                    row = [c.strip() for c in line.strip().strip("|").split("|")]
                    if len(row) == len(headers):
                        rows.append(row)
            
            table_data = {"headers": headers, "rows": rows}
            return self.chunk_to_text_chunks(table_data)
        
        # If no table found, return as single chunk
        return [Chunk(
            text=text,
            start_index=0,
            end_index=len(text),
            metadata={"chunk_type": "text", "error": "No table found"}
        )]

    def chunk_table(
        self, table_data: Union[Dict[str, Any], List[List[str]]], **options
    ) -> List[TableChunk]:
        """
        Chunk table data.

        Args:
            table_data: Table data (dict with 'headers' and 'rows' or list of lists)
            **options: Chunking options

        Returns:
            list: List of table chunks
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="split", submodule="TableChunker", message="Chunking table data"
        )

        try:
            # Parse table data
            self.progress_tracker.update_tracking(
                tracking_id, message="Parsing table data..."
            )
            if isinstance(table_data, dict):
                headers = table_data.get("headers", [])
                rows = table_data.get("rows", [])
            elif isinstance(table_data, list) and len(table_data) > 0:
                # First row as headers if not provided
                if options.get("first_row_as_header", True):
                    headers = table_data[0]
                    rows = table_data[1:]
                else:
                    headers = [f"Column_{i+1}" for i in range(len(table_data[0]))]
                    rows = table_data
            else:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message="Invalid table data format"
                )
                raise ValidationError("Invalid table data format")

            if self.chunk_by_columns:
                self.progress_tracker.update_tracking(
                    tracking_id, message="Chunking by columns..."
                )
                chunks = self._chunk_by_columns(headers, rows, **options)
            else:
                self.progress_tracker.update_tracking(
                    tracking_id, message="Chunking by rows..."
                )
                chunks = self._chunk_by_rows(headers, rows, **options)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Created {len(chunks)} table chunks",
            )
            return chunks

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _chunk_by_rows(
        self, headers: List[str], rows: List[List[str]], **options
    ) -> List[TableChunk]:
        """Chunk table by rows."""
        chunks = []
        max_rows = options.get("max_rows", self.max_rows)

        for i in range(0, len(rows), max_rows):
            chunk_rows = rows[i : i + max_rows]
            end_row = min(i + max_rows, len(rows))

            chunks.append(
                TableChunk(
                    rows=chunk_rows,
                    headers=headers if self.preserve_headers else [],
                    start_row=i,
                    end_row=end_row - 1,
                    metadata={
                        "row_count": len(chunk_rows),
                        "column_count": len(headers),
                        "has_headers": self.preserve_headers,
                    },
                )
            )

        return chunks

    def _chunk_by_columns(
        self, headers: List[str], rows: List[List[str]], **options
    ) -> List[TableChunk]:
        """Chunk table by columns."""
        chunks = []
        max_cols = options.get("max_columns", 5)

        for i in range(0, len(headers), max_cols):
            chunk_headers = headers[i : i + max_cols]
            chunk_rows = [
                [row[j] for j in range(i, min(i + max_cols, len(row)))] for row in rows
            ]
            end_col = min(i + max_cols, len(headers))

            chunks.append(
                TableChunk(
                    rows=chunk_rows,
                    headers=chunk_headers,
                    start_row=0,
                    end_row=len(rows) - 1,
                    metadata={
                        "row_count": len(chunk_rows),
                        "column_count": len(chunk_headers),
                        "start_column": i,
                        "end_column": end_col - 1,
                        "chunked_by": "columns",
                    },
                )
            )

        return chunks

    def chunk_to_text_chunks(
        self, table_data: Union[Dict[str, Any], List[List[str]]], **options
    ) -> List[Chunk]:
        """
        Convert table chunks to text chunks.

        Args:
            table_data: Table data
            **options: Chunking options

        Returns:
            list: List of text chunks
        """
        table_chunks = self.chunk_table(table_data, **options)
        text_chunks = []

        for idx, table_chunk in enumerate(table_chunks):
            # Convert table to text representation
            lines = []

            if table_chunk.headers:
                lines.append(" | ".join(table_chunk.headers))
                lines.append(" | ".join(["---"] * len(table_chunk.headers)))

            for row in table_chunk.rows:
                lines.append(" | ".join(str(cell) for cell in row))

            chunk_text = "\n".join(lines)

            text_chunks.append(
                Chunk(
                    text=chunk_text,
                    start_index=0,
                    end_index=len(chunk_text),
                    metadata={
                        "chunk_type": "table",
                        "chunk_index": idx,
                        "row_count": len(table_chunk.rows),
                        "column_count": len(table_chunk.headers),
                        "start_row": table_chunk.start_row,
                        "end_row": table_chunk.end_row,
                        **table_chunk.metadata,
                    },
                )
            )

        return text_chunks

    def extract_table_schema(
        self, table_data: Union[Dict[str, Any], List[List[str]]]
    ) -> Dict[str, Any]:
        """
        Extract table schema and metadata.

        Args:
            table_data: Table data

        Returns:
            dict: Table schema
        """
        if isinstance(table_data, dict):
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
        elif isinstance(table_data, list) and len(table_data) > 0:
            headers = table_data[0] if table_data else []
            rows = table_data[1:] if len(table_data) > 1 else []
        else:
            return {}

        # Infer column types
        column_types = {}
        if rows:
            for col_idx, header in enumerate(headers):
                sample_values = [
                    row[col_idx] if col_idx < len(row) else "" for row in rows[:10]
                ]

                # Try to infer type
                if all(
                    str(v).strip().replace(".", "").replace("-", "").isdigit()
                    for v in sample_values
                    if v
                ):
                    column_types[header] = "numeric"
                elif all(
                    str(v).lower() in ["true", "false", "yes", "no"]
                    for v in sample_values
                    if v
                ):
                    column_types[header] = "boolean"
                else:
                    column_types[header] = "text"

        return {
            "headers": headers,
            "column_count": len(headers),
            "row_count": len(rows),
            "column_types": column_types,
            "schema": {
                "columns": [
                    {"name": header, "type": column_types.get(header, "text")}
                    for header in headers
                ]
            },
        }
