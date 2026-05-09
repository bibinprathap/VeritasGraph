"""
DuckDB Ingestion Module

This module provides comprehensive DuckDB ingestion capabilities for the
VeritasReason framework, enabling data extraction from CSV, Parquet, and Excel files
using DuckDB's SQL interface.

Key Features:
    - CSV file ingestion with SQL queries
    - Parquet file ingestion
    - Excel file ingestion
    - SQL query execution on files
    - Schema extraction
    - Large dataset handling

Main Classes:
    - DuckDBIngestor: Main DuckDB ingestion class
    - DuckDBData: Data representation for DuckDB ingestion

Example Usage:
    >>> from veritasreason.ingest import DuckDBIngestor
    >>> ingestor = DuckDBIngestor()
    >>> data = ingestor.ingest_csv("data.csv")
    >>> parquet_data = ingestor.ingest_parquet("data.parquet")
    >>> excel_data = ingestor.ingest_excel("data.xlsx")
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

try:
    import duckdb
except (ImportError, OSError):
    duckdb = None


@dataclass
class DuckDBData:
    """DuckDB data representation."""

    data: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    query: Optional[str] = None
    source_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.now)


class DuckDBIngestor:
    """
    DuckDB ingestion handler.

    This class provides comprehensive DuckDB ingestion capabilities,
    supporting ingestion from CSV, Parquet, and Excel files using DuckDB's
    SQL interface for efficient querying.

    Features:
        - CSV file ingestion
        - Parquet file ingestion
        - Excel file ingestion
        - SQL query execution on files
        - Schema extraction
        - Large dataset handling

    Example Usage:
        >>> ingestor = DuckDBIngestor()
        >>> data = ingestor.ingest_csv("data.csv")
        >>> result = ingestor.execute_query("SELECT * FROM 'data.csv' LIMIT 100")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize DuckDB ingestor.

        Args:
            config: Optional DuckDB ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        if duckdb is None:
            raise ImportError(
                "duckdb is required for DuckDBIngestor. Install it with: pip install duckdb"
            )

        self.logger = get_logger("duckdb_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize DuckDB connection
        self.conn = duckdb.connect()
        if self.config.get("memory_limit"):
            self.conn.execute(f"SET memory_limit='{self.config['memory_limit']}'")

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("DuckDB ingestor initialized")

    def __del__(self):
        """Close DuckDB connection on cleanup."""
        if hasattr(self, "conn") and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def ingest_csv(
        self,
        file_path: Union[str, Path],
        limit: Optional[int] = None,
        where: Optional[str] = None,
        **options,
    ) -> DuckDBData:
        """
        Ingest data from CSV file.

        This method reads a CSV file using DuckDB and returns the data.

        Args:
            file_path: Path to CSV file
            limit: Maximum number of rows to return (optional)
            where: WHERE clause for filtering (optional)
            **options: Additional query options

        Returns:
            DuckDBData: Ingested data object

        Raises:
            ValidationError: If CSV file not found
            ProcessingError: If CSV reading fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"CSV file not found: {file_path}")

        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="ingest",
            submodule="DuckDBIngestor",
            message=f"Ingesting CSV: {file_path.name}",
        )

        try:
            # Build SQL query
            query = f"SELECT * FROM read_csv_auto('{file_path}')"

            if where:
                query += f" WHERE {where}"

            if limit:
                query += f" LIMIT {limit}"

            # Execute query
            result = self.conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.conn.description]

            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in result]

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested CSV: {len(data)} rows",
            )

            self.logger.info(f"CSV ingestion completed: {len(data)} row(s)")

            return DuckDBData(
                data=data,
                row_count=len(data),
                columns=columns,
                query=query,
                source_file=str(file_path),
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest CSV {file_path}: {e}")
            raise ProcessingError(f"Failed to ingest CSV: {e}") from e

    def ingest_parquet(
        self,
        file_path: Union[str, Path],
        limit: Optional[int] = None,
        where: Optional[str] = None,
        **options,
    ) -> DuckDBData:
        """
        Ingest data from Parquet file.

        This method reads a Parquet file using DuckDB and returns the data.

        Args:
            file_path: Path to Parquet file
            limit: Maximum number of rows to return (optional)
            where: WHERE clause for filtering (optional)
            **options: Additional query options

        Returns:
            DuckDBData: Ingested data object

        Raises:
            ValidationError: If Parquet file not found
            ProcessingError: If Parquet reading fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"Parquet file not found: {file_path}")

        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="ingest",
            submodule="DuckDBIngestor",
            message=f"Ingesting Parquet: {file_path.name}",
        )

        try:
            # Build SQL query
            query = f"SELECT * FROM read_parquet('{file_path}')"

            if where:
                query += f" WHERE {where}"

            if limit:
                query += f" LIMIT {limit}"

            # Execute query
            result = self.conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.conn.description]

            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in result]

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested Parquet: {len(data)} rows",
            )

            self.logger.info(f"Parquet ingestion completed: {len(data)} row(s)")

            return DuckDBData(
                data=data,
                row_count=len(data),
                columns=columns,
                query=query,
                source_file=str(file_path),
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest Parquet {file_path}: {e}")
            raise ProcessingError(f"Failed to ingest Parquet: {e}") from e

    def ingest_excel(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[str] = None,
        limit: Optional[int] = None,
        where: Optional[str] = None,
        **options,
    ) -> DuckDBData:
        """
        Ingest data from Excel file.

        This method reads an Excel file using DuckDB (via Parquet conversion)
        and returns the data.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read (optional, reads first sheet if not specified)
            limit: Maximum number of rows to return (optional)
            where: WHERE clause for filtering (optional)
            **options: Additional query options

        Returns:
            DuckDBData: Ingested data object

        Raises:
            ValidationError: If Excel file not found
            ProcessingError: If Excel reading fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"Excel file not found: {file_path}")

        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="ingest",
            submodule="DuckDBIngestor",
            message=f"Ingesting Excel: {file_path.name}",
        )

        try:
            # DuckDB doesn't directly support Excel, so we need to use pandas
            # to read Excel and then query it
            try:
                import pandas as pd
            except (ImportError, OSError):
                raise ImportError(
                    "pandas and openpyxl are required for Excel ingestion. "
                    "Install with: pip install pandas openpyxl"
                )

            # Read Excel with pandas
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, **options)
            else:
                df = pd.read_excel(file_path, **options)

            # Register DataFrame as a DuckDB table
            table_name = f"excel_data_{id(df)}"
            self.conn.register(table_name, df)

            # Build SQL query
            query = f"SELECT * FROM {table_name}"

            if where:
                query += f" WHERE {where}"

            if limit:
                query += f" LIMIT {limit}"

            # Execute query
            result = self.conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.conn.description]

            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in result]

            # Unregister table
            self.conn.unregister(table_name)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested Excel: {len(data)} rows",
            )

            self.logger.info(f"Excel ingestion completed: {len(data)} row(s)")

            return DuckDBData(
                data=data,
                row_count=len(data),
                columns=columns,
                query=query,
                source_file=str(file_path),
                metadata={"sheet_name": sheet_name},
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest Excel {file_path}: {e}")
            raise ProcessingError(f"Failed to ingest Excel: {e}") from e

    def execute_query(
        self,
        query: str,
        file_path: Optional[Union[str, Path]] = None,
        **options,
    ) -> DuckDBData:
        """
        Execute SQL query on file or in-memory data.

        This method executes a SQL query using DuckDB. If file_path is provided,
        the query can reference the file directly.

        Args:
            query: SQL query to execute
            file_path: Optional file path to reference in query
            **options: Additional query options

        Returns:
            DuckDBData: Query result data object

        Raises:
            ProcessingError: If query execution fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=file_path or "query",
            module="ingest",
            submodule="DuckDBIngestor",
            message="Executing SQL query",
        )

        try:
            # Execute query
            result = self.conn.execute(query).fetchall()
            columns = [desc[0] for desc in self.conn.description]

            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in result]

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Query executed: {len(data)} rows",
            )

            self.logger.info(f"Query executed: {len(data)} row(s) returned")

            return DuckDBData(
                data=data,
                row_count=len(data),
                columns=columns,
                query=query,
                source_file=str(file_path) if file_path else None,
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to execute query: {e}")
            raise ProcessingError(f"Failed to execute query: {e}") from e

