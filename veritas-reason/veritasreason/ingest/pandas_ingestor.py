"""
Pandas Ingestion Module

This module provides comprehensive pandas DataFrame ingestion capabilities for the
VeritasReason framework, enabling data extraction from DataFrames, CSV, JSON, and dictionaries.

Key Features:
    - DataFrame ingestion from various sources
    - CSV, JSON, dictionary conversion
    - Data transformation and validation
    - Schema extraction
    - Large dataset handling with chunking

Main Classes:
    - PandasIngestor: Main pandas ingestion class
    - PandasData: Data representation for pandas ingestion

Example Usage:
    >>> from veritasreason.ingest import PandasIngestor
    >>> import pandas as pd
    >>> ingestor = PandasIngestor()
    >>> df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
    >>> data = ingestor.ingest_dataframe(df)
    >>> csv_data = ingestor.from_csv("data.csv")
"""

import json
import csv
import chardet
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

try:
    import pandas as pd
except (ImportError, OSError):
    pd = None


@dataclass
class PandasData:
    """Pandas data representation."""

    dataframe: Any  # pd.DataFrame
    row_count: int
    column_count: int
    columns: List[str]
    dtypes: Dict[str, str]
    schema: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.now)


class PandasIngestor:
    """
    Pandas ingestion handler.

    This class provides comprehensive pandas DataFrame ingestion capabilities,
    supporting ingestion from DataFrames, CSV files, JSON files, and dictionaries.

    Features:
        - DataFrame ingestion
        - CSV file reading
        - JSON file reading
        - Dictionary conversion
        - Schema extraction
        - Data validation
        - Large dataset chunking

    Example Usage:
        >>> ingestor = PandasIngestor()
        >>> data = ingestor.ingest_dataframe(df)
        >>> csv_data = ingestor.from_csv("data.csv")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize pandas ingestor.

        Args:
            config: Optional pandas ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        if pd is None:
            raise ImportError(
                "pandas is required for PandasIngestor. Install it with: pip install pandas"
            )

        self.logger = get_logger("pandas_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("Pandas ingestor initialized")

    def ingest_dataframe(
        self, dataframe: Any, **options
    ) -> PandasData:
        """
        Ingest data from pandas DataFrame.

        This method processes a pandas DataFrame and extracts metadata,
        schema information, and data statistics.

        Args:
            dataframe: pandas DataFrame to ingest
            **options: Additional processing options

        Returns:
            PandasData: Ingested data object containing:
                - dataframe: Original DataFrame
                - row_count: Number of rows
                - column_count: Number of columns
                - columns: List of column names
                - dtypes: Dictionary mapping column names to data types
                - schema: Schema information dictionary
                - metadata: Additional metadata

        Raises:
            ValidationError: If dataframe is not a valid pandas DataFrame
            ProcessingError: If ingestion fails
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise ValidationError(
                f"Expected pandas DataFrame, got {type(dataframe).__name__}"
            )

        tracking_id = self.progress_tracker.start_tracking(
            file="dataframe",
            module="ingest",
            submodule="PandasIngestor",
            message="Ingesting pandas DataFrame",
        )

        try:
            # Extract basic information
            row_count = len(dataframe)
            column_count = len(dataframe.columns)
            columns = list(dataframe.columns)
            dtypes = {col: str(dtype) for col, dtype in dataframe.dtypes.items()}

            # Build schema information
            schema = {
                "columns": columns,
                "dtypes": dtypes,
                "shape": (row_count, column_count),
                "index_type": str(type(dataframe.index).__name__),
                "has_nulls": dataframe.isnull().any().any(),
                "null_counts": dataframe.isnull().sum().to_dict(),
            }

            # Extract metadata
            metadata = {
                "memory_usage": dataframe.memory_usage(deep=True).sum(),
                "index_name": dataframe.index.name,
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested DataFrame: {row_count} rows, {column_count} columns",
            )

            self.logger.info(
                f"DataFrame ingestion completed: {row_count} row(s), {column_count} column(s)"
            )

            return PandasData(
                dataframe=dataframe,
                row_count=row_count,
                column_count=column_count,
                columns=columns,
                dtypes=dtypes,
                schema=schema,
                metadata=metadata,
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest DataFrame: {e}")
            raise ProcessingError(f"Failed to ingest DataFrame: {e}") from e

    def from_csv(
        self,
        file_path: Union[str, Path],
        chunksize: Optional[int] = None,
        **pandas_options,
    ) -> PandasData:
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"CSV file not found: {file_path}")

        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="ingest",
            submodule="PandasIngestor",
            message=f"Ingesting CSV: {file_path.name}",
        )

        try:

            # ---------- Encoding Detection ----------
            with open(file_path, "rb") as f:
                raw = f.read(100_000)
                encoding_info = chardet.detect(raw)
            encoding = encoding_info.get("encoding") or "utf-8"

        
            # ---------- Delimiter & Header Detection ----------
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                sample = f.read(10000)
                sniffer = csv.Sniffer()

                try:
                    dialect = sniffer.sniff(sample, delimiters=[",", ";", "\t", "|"])
                    delimiter = dialect.delimiter
                    quotechar = dialect.quotechar
                except Exception:
                    delimiter = ","
                    quotechar = '"'

                # Header handling: default to True (treat first row as header)
                # unless user explicitly overrides via pandas_options['header'].
                has_header = True
                header_opt = pandas_options.get("header", None)
                if header_opt is None:
                    has_header = True
                elif header_opt == 0 or header_opt == "infer":
                    has_header = True
                else:
                    # Any explicit non-header setting (e.g., None or int>0) implies no header
                    try:
                        has_header = False if header_opt is None or int(header_opt) != 0 else True
                    except Exception:
                        has_header = False


            skipped_rows = 0
            dataframes = []

            # ---------- CSV Reading (Chunked if needed) ----------
            # Preserve explicit header setting (including None) if user provided it.
            has_explicit_header = "header" in pandas_options
            explicit_header = pandas_options.pop("header", None) if has_explicit_header else None
            header_arg = explicit_header if has_explicit_header else (0 if has_header else None)

            reader = pd.read_csv(
                file_path,
                sep=delimiter,
                encoding=encoding,
                encoding_errors="replace",
                quoting=csv.QUOTE_MINIMAL,
                header=header_arg,
                quotechar=quotechar,
                escapechar="\\",
                engine="python",
                on_bad_lines="warn",
                chunksize=chunksize,
                **pandas_options,
            )

            if chunksize:
                for chunk in reader:
                    dataframes.append(chunk)
            else:
                dataframes.append(reader)

            dataframe = pd.concat(dataframes, ignore_index=True)

            self.progress_tracker.update_tracking(
                tracking_id,
                message="CSV parsed successfully, ingesting DataFrame...",
            )

            # ---------- Ingest ----------
            pandas_data = self.ingest_dataframe(dataframe)

            # ---------- Metadata ----------
            pandas_data.metadata.update(
                {
                    "source": "csv",
                    "file": str(file_path),
                    "detected_encoding": encoding,
                    "encoding_confidence": encoding_info.get("confidence"),
                    "detected_delimiter": delimiter,
                    "header_detected": has_header,
                    "chunksize": chunksize,
                    "malformed_rows_skipped": skipped_rows,
                }
            )

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"CSV ingestion completed: {pandas_data.row_count} rows",
            )

            return pandas_data

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest CSV {file_path}: {e}")
            raise ProcessingError(f"Failed to ingest CSV: {e}") from e

    def from_json(
        self,
        file_path: Union[str, Path],
        **pandas_options,
    ) -> PandasData:
        """
        Ingest data from JSON file.

        This method reads a JSON file using pandas and ingests it as a DataFrame.

        Args:
            file_path: Path to JSON file
            **pandas_options: Additional options passed to pd.read_json()

        Returns:
            PandasData: Ingested data object

        Raises:
            ProcessingError: If JSON reading fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValidationError(f"JSON file not found: {file_path}")

        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="ingest",
            submodule="PandasIngestor",
            message=f"Ingesting JSON: {file_path.name}",
        )

        try:
            # Read JSON with pandas
            dataframe = pd.read_json(file_path, **pandas_options)

            self.progress_tracker.update_tracking(
                tracking_id, message="JSON read successfully, processing DataFrame..."
            )

            # Ingest the DataFrame
            return self.ingest_dataframe(dataframe, **pandas_options)

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest JSON {file_path}: {e}")
            raise ProcessingError(f"Failed to ingest JSON: {e}") from e

    def from_dict(
        self,
        data: Union[Dict[str, List], List[Dict[str, Any]]],
        **pandas_options,
    ) -> PandasData:
        """
        Ingest data from dictionary.

        This method converts a dictionary or list of dictionaries to a DataFrame
        and ingests it.

        Args:
            data: Dictionary or list of dictionaries
            **pandas_options: Additional options passed to pd.DataFrame()

        Returns:
            PandasData: Ingested data object

        Raises:
            ValidationError: If data format is invalid
            ProcessingError: If conversion fails
        """
        if not isinstance(data, (dict, list)):
            raise ValidationError(
                f"Expected dict or list, got {type(data).__name__}"
            )

        tracking_id = self.progress_tracker.start_tracking(
            file="dictionary",
            module="ingest",
            submodule="PandasIngestor",
            message="Converting dictionary to DataFrame",
        )

        try:
            # Convert to DataFrame
            dataframe = pd.DataFrame(data, **pandas_options)

            self.progress_tracker.update_tracking(
                tracking_id, message="Dictionary converted, processing DataFrame..."
            )

            # Ingest the DataFrame
            return self.ingest_dataframe(dataframe, **pandas_options)

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest dictionary: {e}")
            raise ProcessingError(f"Failed to ingest dictionary: {e}") from e

