"""
Elasticsearch Ingestion Module

This module provides comprehensive Elasticsearch ingestion capabilities for the
VeritasReason framework, enabling data extraction from Elasticsearch indices.

Key Features:
    - Index ingestion
    - Search query execution
    - Index export
    - Schema extraction
    - Large dataset handling with scroll API

Main Classes:
    - ElasticIngestor: Main Elasticsearch ingestion class
    - ElasticData: Data representation for Elasticsearch ingestion

Example Usage:
    >>> from veritasreason.ingest import ElasticIngestor
    >>> ingestor = ElasticIngestor()
    >>> data = ingestor.ingest_index("http://localhost:9200", "my_index")
    >>> results = ingestor.search_documents("http://localhost:9200", "my_index", {"query": {"match_all": {}}})
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import scan
except (ImportError, OSError):
    Elasticsearch = None
    scan = None


@dataclass
class ElasticData:
    """Elasticsearch data representation."""

    documents: List[Dict[str, Any]]
    document_count: int
    index_name: str
    schema: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.now)


class ElasticIngestor:
    """
    Elasticsearch ingestion handler.

    This class provides comprehensive Elasticsearch ingestion capabilities,
    connecting to Elasticsearch, querying indices, and exporting data.

    Features:
        - Index ingestion
        - Search query execution
        - Index export
        - Schema extraction
        - Large dataset handling with scroll API

    Example Usage:
        >>> ingestor = ElasticIngestor()
        >>> data = ingestor.ingest_index("http://localhost:9200", "my_index")
        >>> results = ingestor.search_documents("http://localhost:9200", "my_index", {"query": {"match_all": {}}})
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize Elasticsearch ingestor.

        Args:
            config: Optional Elasticsearch ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        if Elasticsearch is None:
            raise ImportError(
                "elasticsearch is required for ElasticIngestor. Install it with: pip install elasticsearch"
            )

        self.logger = get_logger("elastic_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("Elasticsearch ingestor initialized")

    def _get_client(self, connection_string: str) -> Elasticsearch:
        """
        Get Elasticsearch client.

        Args:
            connection_string: Elasticsearch connection string or host

        Returns:
            Elasticsearch: Elasticsearch client object
        """
        # Parse connection string
        if connection_string.startswith("http://") or connection_string.startswith(
            "https://"
        ):
            hosts = [connection_string]
        else:
            # Assume it's a host:port format
            hosts = [connection_string]

        # Create client
        client_config = self.config.get("client_config", {})
        client = Elasticsearch(hosts=hosts, **client_config)

        # Test connection
        if not client.ping():
            raise ProcessingError("Failed to connect to Elasticsearch")

        return client

    def ingest_index(
        self,
        connection_string: str,
        index_name: str,
        limit: Optional[int] = None,
        **options,
    ) -> ElasticData:
        """
        Ingest data from Elasticsearch index.

        This method connects to Elasticsearch, retrieves documents from an index,
        and extracts schema information.

        Args:
            connection_string: Elasticsearch connection string (e.g., "http://localhost:9200")
            index_name: Name of the index
            limit: Maximum number of documents to retrieve (optional)
            **options: Additional processing options

        Returns:
            ElasticData: Ingested data object containing:
                - documents: List of document dictionaries
                - document_count: Number of documents
                - index_name: Index name
                - schema: Schema information dictionary

        Raises:
            ProcessingError: If ingestion fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=index_name,
            module="ingest",
            submodule="ElasticIngestor",
            message=f"Ingesting index: {index_name}",
        )

        try:
            # Get client
            client = self._get_client(connection_string)

            # Check if index exists
            if not client.indices.exists(index=index_name):
                raise ValidationError(f"Index not found: {index_name}")

            # Get total document count
            count_response = client.count(index=index_name)
            total_count = count_response["count"]

            # Retrieve documents using scroll API for large datasets
            self.progress_tracker.update_tracking(
                tracking_id, message=f"Retrieving documents (total: {total_count})..."
            )

            query = options.get("query", {"match_all": {}})
            scroll_size = options.get("scroll_size", 1000)

            documents = []
            if limit:
                # Use regular search with size limit
                response = client.search(
                    index=index_name, body={"query": query}, size=limit
                )
                documents = [hit["_source"] for hit in response["hits"]["hits"]]
            else:
                # Use scroll API for all documents
                for doc in scan(
                    client, query={"query": query}, index=index_name, size=scroll_size
                ):
                    documents.append(doc["_source"])
                    if limit and len(documents) >= limit:
                        break

            # Extract schema information
            schema = self._extract_schema(documents)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested {len(documents)} documents",
            )

            self.logger.info(
                f"Index ingestion completed: {len(documents)} document(s)"
            )

            return ElasticData(
                documents=documents,
                document_count=len(documents),
                index_name=index_name,
                schema=schema,
                metadata={"total_count": total_count, "query": query},
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest index: {e}")
            raise ProcessingError(f"Failed to ingest index: {e}") from e

    def search_documents(
        self,
        connection_string: str,
        index_name: str,
        search_query: Dict[str, Any],
        limit: Optional[int] = None,
        **options,
    ) -> ElasticData:
        """
        Search documents in Elasticsearch index.

        This method executes a search query on an Elasticsearch index and returns
        matching documents.

        Args:
            connection_string: Elasticsearch connection string
            index_name: Name of the index
            search_query: Elasticsearch search query dictionary
            limit: Maximum number of documents to return (optional)
            **options: Additional search options

        Returns:
            ElasticData: Search result data object

        Raises:
            ProcessingError: If search fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=index_name,
            module="ingest",
            submodule="ElasticIngestor",
            message=f"Searching index: {index_name}",
        )

        try:
            # Get client
            client = self._get_client(connection_string)

            # Execute search
            size = limit or options.get("size", 100)
            response = client.search(
                index=index_name, body=search_query, size=size, **options
            )

            # Extract documents
            documents = [hit["_source"] for hit in response["hits"]["hits"]]

            # Extract schema information
            schema = self._extract_schema(documents)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Search returned {len(documents)} documents",
            )

            self.logger.info(f"Search completed: {len(documents)} document(s)")

            return ElasticData(
                documents=documents,
                document_count=len(documents),
                index_name=index_name,
                schema=schema,
                metadata={
                    "total_hits": response["hits"]["total"]["value"],
                    "query": search_query,
                },
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to search documents: {e}")
            raise ProcessingError(f"Failed to search documents: {e}") from e

    def export_index(
        self,
        connection_string: str,
        index_name: str,
        **options,
    ) -> ElasticData:
        """
        Export entire index.

        This method exports all documents from an Elasticsearch index.

        Args:
            connection_string: Elasticsearch connection string
            index_name: Name of the index
            **options: Additional export options

        Returns:
            ElasticData: Exported data object

        Raises:
            ProcessingError: If export fails
        """
        return self.ingest_index(connection_string, index_name, limit=None, **options)

    def _extract_schema(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract schema information from documents.

        Args:
            documents: List of Elasticsearch documents

        Returns:
            Dictionary containing schema information
        """
        if not documents:
            return {"fields": [], "field_types": {}}

        # Collect all field names and types
        field_types = {}
        for doc in documents:
            for key, value in doc.items():
                if key not in field_types:
                    field_types[key] = set()
                field_types[key].add(type(value).__name__)

        # Convert sets to lists
        schema = {
            "fields": list(field_types.keys()),
            "field_types": {
                k: list(v) if len(v) > 1 else list(v)[0]
                for k, v in field_types.items()
            },
        }

        return schema

