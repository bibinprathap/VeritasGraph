"""
HuggingFace Ingestion Module

This module provides comprehensive HuggingFace datasets ingestion capabilities for the
VeritasReason framework, enabling data extraction from HuggingFace Hub datasets.

Key Features:
    - Dataset ingestion
    - Streaming dataset support
    - Split export
    - Large dataset handling

Main Classes:
    - HuggingFaceIngestor: Main HuggingFace ingestion class
    - HFData: Data representation for HuggingFace ingestion

Example Usage:
    >>> from veritasreason.ingest import HuggingFaceIngestor
    >>> ingestor = HuggingFaceIngestor()
    >>> data = ingestor.ingest_dataset("squad", split="train")
    >>> stream_data = ingestor.stream_dataset("squad", split="train")
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

try:
    from datasets import load_dataset, Dataset, IterableDataset
except (ImportError, OSError):
    load_dataset = None
    Dataset = None
    IterableDataset = None


@dataclass
class HFData:
    """HuggingFace data representation."""

    data: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    dataset_name: str
    split: Optional[str] = None
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.now)


class HuggingFaceIngestor:
    """
    HuggingFace ingestion handler.

    This class provides comprehensive HuggingFace datasets ingestion capabilities,
    loading datasets from HuggingFace Hub and converting them to standard formats.

    Features:
        - Dataset ingestion
        - Streaming dataset support
        - Split export
        - Large dataset handling

    Example Usage:
        >>> ingestor = HuggingFaceIngestor()
        >>> data = ingestor.ingest_dataset("squad", split="train")
        >>> stream_data = ingestor.stream_dataset("squad", split="train")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize HuggingFace ingestor.

        Args:
            config: Optional HuggingFace ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        if load_dataset is None:
            raise ImportError(
                "datasets is required for HuggingFaceIngestor. Install it with: pip install datasets"
            )

        self.logger = get_logger("huggingface_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("HuggingFace ingestor initialized")

    def ingest_dataset(
        self,
        dataset_name: str,
        split: Optional[str] = None,
        limit: Optional[int] = None,
        **options,
    ) -> HFData:
        """
        Ingest data from HuggingFace dataset.

        This method loads a dataset from HuggingFace Hub and converts it to
        a standard format.

        Args:
            dataset_name: Name of the dataset (e.g., "squad", "glue")
            split: Dataset split to load (e.g., "train", "test", "validation")
            limit: Maximum number of rows to return (optional)
            **options: Additional options passed to load_dataset()

        Returns:
            HFData: Ingested data object containing:
                - data: List of row dictionaries
                - row_count: Number of rows
                - columns: List of column names
                - dataset_name: Dataset name
                - split: Split name
                - schema: Schema information

        Raises:
            ValidationError: If dataset not found
            ProcessingError: If ingestion fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=dataset_name,
            module="ingest",
            submodule="HuggingFaceIngestor",
            message=f"Loading dataset: {dataset_name}",
        )

        try:
            # Load dataset
            self.progress_tracker.update_tracking(
                tracking_id, message="Loading from HuggingFace Hub..."
            )

            if split:
                dataset = load_dataset(dataset_name, split=split, **options)
            else:
                # Load all splits
                dataset = load_dataset(dataset_name, **options)
                # Use first split if multiple splits
                if isinstance(dataset, dict):
                    split = list(dataset.keys())[0]
                    dataset = dataset[split]

            # Convert to list of dictionaries
            self.progress_tracker.update_tracking(
                tracking_id, message="Converting to list format..."
            )

            if limit:
                data = [dataset[i] for i in range(min(limit, len(dataset)))]
            else:
                data = list(dataset)

            # Extract columns and schema
            columns = list(data[0].keys()) if data else []
            schema = {
                "columns": columns,
                "features": dataset.features.to_dict() if hasattr(dataset, "features") else {},
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested {len(data)} rows",
            )

            self.logger.info(
                f"Dataset ingestion completed: {len(data)} row(s) from {dataset_name}"
            )

            return HFData(
                data=data,
                row_count=len(data),
                columns=columns,
                dataset_name=dataset_name,
                split=split,
                schema=schema,
                metadata={"features": schema.get("features", {})},
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest dataset {dataset_name}: {e}")
            raise ProcessingError(f"Failed to ingest dataset: {e}") from e

    def stream_dataset(
        self,
        dataset_name: str,
        split: Optional[str] = None,
        limit: Optional[int] = None,
        **options,
    ) -> HFData:
        """
        Stream dataset from HuggingFace Hub.

        This method loads a dataset in streaming mode, which is more memory-efficient
        for large datasets.

        Args:
            dataset_name: Name of the dataset
            split: Dataset split to load (optional)
            limit: Maximum number of rows to return (optional)
            **options: Additional options passed to load_dataset()

        Returns:
            HFData: Streamed data object

        Raises:
            ProcessingError: If streaming fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=dataset_name,
            module="ingest",
            submodule="HuggingFaceIngestor",
            message=f"Streaming dataset: {dataset_name}",
        )

        try:
            # Load dataset in streaming mode
            self.progress_tracker.update_tracking(
                tracking_id, message="Loading in streaming mode..."
            )

            streaming_options = options.copy()
            streaming_options["streaming"] = True

            if split:
                dataset = load_dataset(
                    dataset_name, split=split, **streaming_options
                )
            else:
                dataset = load_dataset(dataset_name, **streaming_options)
                if isinstance(dataset, dict):
                    split = list(dataset.keys())[0]
                    dataset = dataset[split]

            # Convert streaming dataset to list
            self.progress_tracker.update_tracking(
                tracking_id, message="Streaming and converting data..."
            )

            data = []
            columns = None

            for i, item in enumerate(dataset):
                if columns is None:
                    columns = list(item.keys())

                data.append(item)

                if limit and len(data) >= limit:
                    break

            # Extract schema
            schema = {
                "columns": columns or [],
                "features": dataset.features.to_dict() if hasattr(dataset, "features") else {},
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Streamed {len(data)} rows",
            )

            self.logger.info(
                f"Dataset streaming completed: {len(data)} row(s) from {dataset_name}"
            )

            return HFData(
                data=data,
                row_count=len(data),
                columns=columns or [],
                dataset_name=dataset_name,
                split=split,
                schema=schema,
                metadata={"streaming": True},
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to stream dataset {dataset_name}: {e}")
            raise ProcessingError(f"Failed to stream dataset: {e}") from e

    def export_split(
        self,
        dataset_name: str,
        split: str,
        **options,
    ) -> HFData:
        """
        Export a specific split from a dataset.

        This method exports a specific split from a HuggingFace dataset.

        Args:
            dataset_name: Name of the dataset
            split: Split name to export
            **options: Additional options

        Returns:
            HFData: Exported split data object

        Raises:
            ProcessingError: If export fails
        """
        return self.ingest_dataset(dataset_name, split=split, **options)

