"""
MongoDB Ingestion Module

This module provides comprehensive MongoDB ingestion capabilities for the
VeritasReason framework, enabling data extraction from MongoDB collections and databases.

Key Features:
    - Collection ingestion
    - Query-based document retrieval
    - Database export
    - Schema extraction
    - Large dataset handling with pagination

Main Classes:
    - MongoIngestor: Main MongoDB ingestion class
    - MongoConnector: MongoDB connection handler
    - MongoData: Data representation for MongoDB ingestion

Example Usage:
    >>> from veritasreason.ingest import MongoIngestor
    >>> ingestor = MongoIngestor()
    >>> data = ingestor.ingest_collection("mongodb://localhost:27017", "mydb", "mycollection")
    >>> docs = ingestor.query_documents("mongodb://...", "mydb", "mycollection", {"status": "active"})
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
except (ImportError, OSError):
    MongoClient = None
    ConnectionFailure = None
    OperationFailure = None


@dataclass
class MongoData:
    """MongoDB data representation."""

    documents: List[Dict[str, Any]]
    document_count: int
    collection_name: str
    database_name: str
    schema: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=datetime.now)


class MongoConnector:
    """
    MongoDB connection management.

    This class manages connections to MongoDB, handles connection pooling,
    and provides a unified interface for database operations.

    Example Usage:
        >>> connector = MongoConnector()
        >>> client = connector.connect("mongodb://localhost:27017")
        >>> connector.disconnect()
    """

    def __init__(self, **config):
        """
        Initialize MongoDB connector.

        Args:
            **config: Connection configuration options
        """
        if MongoClient is None:
            raise ImportError(
                "pymongo is required for MongoConnector. Install it with: pip install pymongo"
            )

        self.logger = get_logger("mongo_connector")
        self.config = config
        self.client: Optional[MongoClient] = None

        self.logger.debug("MongoDB connector initialized")

    def connect(self, connection_string: str) -> MongoClient:
        """
        Establish MongoDB connection.

        Args:
            connection_string: MongoDB connection string
                              Example: "mongodb://localhost:27017"

        Returns:
            MongoClient: MongoDB client object

        Raises:
            ProcessingError: If connection fails
        """
        try:
            self.client = MongoClient(connection_string, **self.config)
            # Test connection
            self.client.admin.command("ping")
            self.logger.info("Connected to MongoDB")
            return self.client
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            raise ProcessingError(f"Failed to connect to MongoDB: {e}") from e

    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.logger.info("Disconnected from MongoDB")

    def test_connection(self, connection_string: str) -> bool:
        """
        Test MongoDB connection without creating a persistent connection.

        Args:
            connection_string: MongoDB connection string to test

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            client.close()
            return True
        except Exception as e:
            self.logger.debug(f"Connection test failed: {e}")
            return False


class MongoIngestor:
    """
    MongoDB ingestion handler.

    This class provides comprehensive MongoDB ingestion capabilities,
    connecting to MongoDB, querying collections, and exporting data.

    Features:
        - Collection ingestion
        - Query-based document retrieval
        - Database export
        - Schema extraction
        - Large dataset handling with pagination

    Example Usage:
        >>> ingestor = MongoIngestor()
        >>> data = ingestor.ingest_collection("mongodb://...", "mydb", "mycollection")
        >>> docs = ingestor.query_documents("mongodb://...", "mydb", "mycollection", {"status": "active"})
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize MongoDB ingestor.

        Args:
            config: Optional MongoDB ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        self.logger = get_logger("mongo_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize connector
        self.connector = MongoConnector(**self.config)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()

        self.logger.debug("MongoDB ingestor initialized")

    def ingest_collection(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
        limit: Optional[int] = None,
        **options,
    ) -> MongoData:
        """
        Ingest data from MongoDB collection.

        This method connects to MongoDB, retrieves documents from a collection,
        and extracts schema information.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database
            collection_name: Name of the collection
            limit: Maximum number of documents to retrieve (optional)
            **options: Additional processing options

        Returns:
            MongoData: Ingested data object containing:
                - documents: List of document dictionaries
                - document_count: Number of documents
                - collection_name: Collection name
                - database_name: Database name
                - schema: Schema information dictionary

        Raises:
            ProcessingError: If ingestion fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=f"{database_name}.{collection_name}",
            module="ingest",
            submodule="MongoIngestor",
            message=f"Collection: {database_name}.{collection_name}",
        )

        try:
            # Connect to MongoDB
            client = self.connector.connect(connection_string)
            db = client[database_name]
            collection = db[collection_name]

            # Get document count
            total_count = collection.count_documents({})

            # Retrieve documents
            self.progress_tracker.update_tracking(
                tracking_id, message=f"Retrieving documents (total: {total_count})..."
            )

            query = options.get("query", {})
            cursor = collection.find(query)

            if limit:
                cursor = cursor.limit(limit)

            documents = list(cursor)

            # Extract schema information
            schema = self._extract_schema(documents)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Ingested {len(documents)} documents",
            )

            self.logger.info(
                f"Collection ingestion completed: {len(documents)} document(s)"
            )

            return MongoData(
                documents=documents,
                document_count=len(documents),
                collection_name=collection_name,
                database_name=database_name,
                schema=schema,
                metadata={"total_count": total_count, "query": query},
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to ingest collection: {e}")
            raise ProcessingError(f"Failed to ingest collection: {e}") from e
        finally:
            self.connector.disconnect()

    def query_documents(
        self,
        connection_string: str,
        database_name: str,
        collection_name: str,
        query: Dict[str, Any],
        limit: Optional[int] = None,
        **options,
    ) -> MongoData:
        """
        Query documents from MongoDB collection.

        This method executes a query on a MongoDB collection and returns
        matching documents.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database
            collection_name: Name of the collection
            query: MongoDB query dictionary
            limit: Maximum number of documents to return (optional)
            **options: Additional query options

        Returns:
            MongoData: Query result data object

        Raises:
            ProcessingError: If query fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=f"{database_name}.{collection_name}",
            module="ingest",
            submodule="MongoIngestor",
            message=f"Querying collection: {database_name}.{collection_name}",
        )

        try:
            # Connect to MongoDB
            client = self.connector.connect(connection_string)
            db = client[database_name]
            collection = db[collection_name]

            # Execute query
            cursor = collection.find(query)

            if limit:
                cursor = cursor.limit(limit)

            if "sort" in options:
                cursor = cursor.sort(options["sort"])

            documents = list(cursor)

            # Extract schema information
            schema = self._extract_schema(documents)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Query returned {len(documents)} documents",
            )

            self.logger.info(f"Query completed: {len(documents)} document(s)")

            return MongoData(
                documents=documents,
                document_count=len(documents),
                collection_name=collection_name,
                database_name=database_name,
                schema=schema,
                metadata={"query": query},
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to query documents: {e}")
            raise ProcessingError(f"Failed to query documents: {e}") from e
        finally:
            self.connector.disconnect()

    def export_database(
        self,
        connection_string: str,
        database_name: str,
        include_collections: Optional[List[str]] = None,
        exclude_collections: Optional[List[str]] = None,
        **options,
    ) -> Dict[str, MongoData]:
        """
        Export entire database.

        This method exports all collections from a MongoDB database.

        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database
            include_collections: List of collection names to include (optional)
            exclude_collections: List of collection names to exclude (optional)
            **options: Additional export options

        Returns:
            Dictionary mapping collection names to MongoData objects

        Raises:
            ProcessingError: If export fails
        """
        tracking_id = self.progress_tracker.start_tracking(
            file=database_name,
            module="ingest",
            submodule="MongoIngestor",
            message=f"Exporting database: {database_name}",
        )

        try:
            # Connect to MongoDB
            client = self.connector.connect(connection_string)
            db = client[database_name]

            # Get all collection names
            all_collections = db.list_collection_names()

            # Apply filters
            if include_collections:
                collections = [c for c in all_collections if c in include_collections]
            else:
                exclude_collections = exclude_collections or []
                collections = [c for c in all_collections if c not in exclude_collections]

            self.progress_tracker.update_tracking(
                tracking_id, message=f"Exporting {len(collections)} collections..."
            )

            # Export each collection
            result = {}
            for collection_name in collections:
                try:
                    data = self.ingest_collection(
                        connection_string, database_name, collection_name, **options
                    )
                    result[collection_name] = data
                except Exception as e:
                    self.logger.error(
                        f"Failed to export collection {collection_name}: {e}"
                    )
                    if self.config.get("fail_fast", False):
                        raise

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Exported {len(result)} collections",
            )

            self.logger.info(f"Database export completed: {len(result)} collection(s)")

            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            self.logger.error(f"Failed to export database: {e}")
            raise ProcessingError(f"Failed to export database: {e}") from e
        finally:
            self.connector.disconnect()

    def _extract_schema(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract schema information from documents.

        Args:
            documents: List of MongoDB documents

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

