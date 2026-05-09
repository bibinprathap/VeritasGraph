"""
RDF4J Store Module

This module provides Eclipse RDF4J integration for RDF storage and SPARQL
querying, supporting repository management and transaction operations.

Key Features:
    - RDF4J connection and repository management
    - SPARQL query execution
    - Repository configuration and setup
    - Transaction support
    - REST API integration
    - Bulk operations

Main Classes:
    - RDF4JStore: Main RDF4J integration store

Example Usage:
    >>> from veritasreason.triplet_store import RDF4JStore
    >>> store = RDF4JStore(endpoint="http://localhost:8080/rdf4j-server", repository_id="repo1")
    >>> result = store.execute_sparql(sparql_query)
    >>> tx_id = store.begin_transaction()
    >>> result = store.add_triplets(triplets)

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Dict, List, Optional

import requests

from ..semantic_extract.triplet_extractor import Triplet
from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class RDF4JStore:
    """
    Eclipse RDF4J store for triplet store operations.

    This class provides integration with Eclipse RDF4J, supporting
    remote repositories, transactions, and high-performance querying.
    """

    def __init__(
        self, endpoint: Optional[str] = None, repository_id: Optional[str] = None, **config
    ):
        """
        Initialize RDF4J store.

        Args:
            endpoint: RDF4J server URL
            repository_id: Repository identifier
            **config: Additional configuration options
        """
        self.logger = get_logger("rdf4j_store")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.endpoint = endpoint.rstrip("/")
        self.repository_id = config.get("repository_id", "default")
        self.username = config.get("username")
        self.password = config.get("password")
        self.timeout = config.get("timeout", 30)

        self.connected = False
        self._connect()

    def _connect(self) -> None:
        """Connect to RDF4J server."""
        try:
            # Test connection
            test_url = f"{self.endpoint}/repositories/{self.repository_id}"
            response = requests.get(
                test_url,
                timeout=self.timeout,
                auth=(self.username, self.password)
                if self.username and self.password
                else None,
            )

            if response.status_code == 200:
                self.connected = True
                self.logger.info(f"Connected to RDF4J: {self.endpoint}")
            else:
                self.logger.warning(
                    f"RDF4J connection test failed: {response.status_code}"
                )
        except Exception as e:
            self.logger.warning(f"Could not connect to RDF4J: {e}")

    def _get_sparql_endpoint(self) -> str:
        """Get SPARQL query endpoint."""
        return f"{self.endpoint}/repositories/{self.repository_id}"

    def _get_update_endpoint(self) -> str:
        """Get SPARQL Update endpoint."""
        return f"{self.endpoint}/repositories/{self.repository_id}/statements"

    def create_repository(
        self, repository_config: Dict[str, Any], **options
    ) -> Dict[str, Any]:
        """
        Create and configure repository.

        Args:
            repository_config: Repository configuration
            **options: Additional options

        Returns:
            Repository information
        """
        # RDF4J repository creation via REST API
        create_url = f"{self.endpoint}/repositories"

        try:
            response = requests.post(
                create_url,
                json=repository_config,
                timeout=self.timeout,
                auth=(self.username, self.password)
                if self.username and self.password
                else None,
            )

            response.raise_for_status()

            return {
                "success": True,
                "repository_id": repository_config.get("id", "new_repository"),
            }
        except Exception as e:
            self.logger.error(f"Create repository failed: {e}")
            raise ProcessingError(f"Create repository failed: {e}")

    def begin_transaction(self, **options) -> str:
        """
        Start transaction for batch operations.

        Args:
            **options: Transaction options

        Returns:
            Transaction ID
        """
        # RDF4J transaction support
        transaction_url = (
            f"{self.endpoint}/repositories/{self.repository_id}/transactions"
        )

        try:
            response = requests.post(
                transaction_url,
                timeout=self.timeout,
                auth=(self.username, self.password)
                if self.username and self.password
                else None,
            )

            response.raise_for_status()
            transaction_id = response.headers.get("Location", "").split("/")[-1]

            return transaction_id
        except Exception as e:
            self.logger.error(f"Begin transaction failed: {e}")
            raise ProcessingError(f"Begin transaction failed: {e}")

    def execute_sparql(self, query: str, **options) -> Dict[str, Any]:
        """
        Execute SPARQL query.

        Args:
            query: SPARQL query string
            **options: Additional options

        Returns:
            Query results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="triplet_store",
            submodule="RDF4JStore",
            message="Executing SPARQL query on RDF4J",
        )

        try:
            if not self.connected:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message="Not connected to RDF4J"
                )
                raise ProcessingError("Not connected to RDF4J")

            sparql_endpoint = self._get_sparql_endpoint()

            self.progress_tracker.update_tracking(
                tracking_id, message="Sending query to RDF4J endpoint..."
            )
            response = requests.post(
                sparql_endpoint,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=self.timeout,
                auth=(self.username, self.password)
                if self.username and self.password
                else None,
            )

            response.raise_for_status()

            self.progress_tracker.update_tracking(
                tracking_id, message="Parsing query results..."
            )
            result_data = response.json()

            result = {
                "success": True,
                "bindings": result_data.get("results", {}).get("bindings", []),
                "variables": result_data.get("head", {}).get("vars", []),
                "metadata": {"query": query, "endpoint": sparql_endpoint},
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Query executed: {len(result['bindings'])} results",
            )
            return result
        except Exception as e:
            self.logger.error(f"SPARQL query failed: {e}")
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise ProcessingError(f"SPARQL query failed: {e}")

    def add_triplets(self, triplets: List[Triplet], **options) -> Dict[str, Any]:
        """
        Add triplets to repository.

        Args:
            triplets: List of triplets
            **options: Additional options

        Returns:
            Operation status
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="triplet_store",
            submodule="RDF4JStore",
            message=f"Adding {len(triplets)} triplets to RDF4J repository",
        )

        try:
            if not self.connected:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message="Not connected to RDF4J"
                )
                raise ProcessingError("Not connected to RDF4J")

            update_endpoint = self._get_update_endpoint()

            # Convert triplets to RDF format
            self.progress_tracker.update_tracking(
                tracking_id, message="Converting triplets to RDF format..."
            )
            rdf_data = self._triplets_to_ntriples(triplets)

            self.progress_tracker.update_tracking(
                tracking_id, message="Sending triplets to RDF4J repository..."
            )
            response = requests.post(
                update_endpoint,
                data=rdf_data,
                headers={"Content-Type": "application/n-triples"},
                timeout=self.timeout * 2,
                auth=(self.username, self.password)
                if self.username and self.password
                else None,
            )

            response.raise_for_status()

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Added {len(triplets)} triplets to repository",
            )

            return {"success": True, "triplets_added": len(triplets)}
        except Exception as e:
            self.logger.error(f"Add triplets failed: {e}")
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise ProcessingError(f"Add triplets failed: {e}")

    def add_triplet(self, triplet: Triplet, **options) -> Dict[str, Any]:
        """Add single triplet."""
        return self.add_triplets([triplet], **options)

    def get_triplets(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None,
        **options,
    ) -> List[Triplet]:
        """Get triplets matching criteria."""
        # Build SPARQL query
        where_clauses = []
        if subject:
            where_clauses.append(f"?s = <{subject}>")
        if predicate:
            where_clauses.append(f"?p = <{predicate}>")
        if object:
            where_clauses.append(f"?o = <{object}>")

        where_clause = " ".join(where_clauses) if where_clauses else ""
        query = f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o {where_clause} }}"

        result = self.execute_sparql(query, **options)

        # Convert bindings to triplets
        triplets = []
        for binding in result["bindings"]:
            triplets.append(
                Triplet(
                    subject=binding.get("s", {}).get("value", ""),
                    predicate=binding.get("p", {}).get("value", ""),
                    object=binding.get("o", {}).get("value", ""),
                    metadata={"source": "rdf4j"},
                )
            )

        return triplets

    def delete_triplet(self, triplet: Triplet, **options) -> Dict[str, Any]:
        """Delete triplet."""
        if not self.connected:
            raise ProcessingError("Not connected to RDF4J")

        update_endpoint = self._get_update_endpoint()

        # Use SPARQL DELETE
        query = f"DELETE DATA {{ <{triplet.subject}> <{triplet.predicate}> <{triplet.object}> }}"

        try:
            response = requests.post(
                update_endpoint,
                data={"update": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
                auth=(self.username, self.password)
                if self.username and self.password
                else None,
            )

            response.raise_for_status()

            return {"success": True}
        except Exception as e:
            self.logger.error(f"Delete triplet failed: {e}")
            raise ProcessingError(f"Delete triplet failed: {e}")

    def _triplets_to_ntriples(self, triplets: List[Triplet]) -> str:
        """Convert triplets to N-Triples format."""
        lines = []
        for triplet in triplets:
            lines.append(f"<{triplet.subject}> <{triplet.predicate}> <{triplet.object}> .")
        return "\n".join(lines)
