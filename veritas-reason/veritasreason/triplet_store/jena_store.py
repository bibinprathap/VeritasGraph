"""
Apache Jena Store Module

This module provides Apache Jena integration for RDF storage and SPARQL
querying, supporting both in-memory and remote Fuseki endpoints.

Key Features:
    - Jena connection and configuration
    - SPARQL query execution
    - Model and dataset management
    - Inference and reasoning support
    - RDF serialization
    - rdflib integration with fallback

Main Classes:
    - JenaStore: Main Jena integration store

Example Usage:
    >>> from veritasreason.triplet_store import JenaStore
    >>> store = JenaStore(endpoint="http://localhost:3030/ds", dataset="default")
    >>> result = store.add_triplets(triplets)
    >>> query_result = store.execute_sparql(sparql_query)
    >>> rdf_turtle = store.serialize(format="turtle")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any, Dict, List, Optional

from ..semantic_extract.triplet_extractor import Triplet
from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

# Optional Jena imports
try:
    from rdflib import RDF, Graph, Literal, Namespace, URIRef
    from rdflib.plugins.stores.sparqlstore import SPARQLStore

    HAS_JENA_RDFLIB = True
except (ImportError, OSError):
    HAS_JENA_RDFLIB = False
    Graph = None
    RDF = None


class JenaStore:
    """
    Apache Jena store for triplet store operations.

    This class provides integration with Apache Jena and Fuseki, supporting
    both remote SPARQL endpoints and local in-memory graphs via rdflib.
    """

    def __init__(self, endpoint: Optional[str] = None, **config):
        """
        Initialize Jena store.

        Args:
            endpoint: SPARQL endpoint URL (e.g., http://localhost:3030/ds)
            **config: Additional configuration options
        """
        self.logger = get_logger("jena_store")
        self.config = config
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.endpoint = config.get("endpoint")
        self.dataset = config.get("dataset", "default")
        self.enable_inference = config.get("enable_inference", False)

        self.graph: Optional[Graph] = None
        self._initialize_graph()

    def _initialize_graph(self) -> None:
        """Initialize RDF graph."""
        if HAS_JENA_RDFLIB:
            if self.endpoint:
                # Use SPARQL store for remote endpoint
                try:
                    store = SPARQLStore(query_endpoint=self.endpoint)
                    self.graph = Graph(store=store)
                except Exception as e:
                    self.logger.warning(f"Could not initialize SPARQL store: {e}")
                    self.graph = Graph()
            else:
                # Use in-memory graph
                self.graph = Graph()
        else:
            self.logger.warning(
                "rdflib not available. Jena store will use basic operations."
            )
            self.graph = None

    def create_model(self, **options) -> Dict[str, Any]:
        """
        Create and manage RDF models.

        Args:
            **options: Model options

        Returns:
            Model information
        """
        if self.graph is None:
            self._initialize_graph()

        return {
            "model_id": self.dataset,
            "endpoint": self.endpoint,
            "triplet_count": len(self.graph) if self.graph else 0,
        }

    def add_triplets(self, triplets: List[Triplet], **options) -> Dict[str, Any]:
        """
        Add triplets to model.

        Args:
            triplets: List of triplets
            **options: Additional options

        Returns:
            Operation status
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="triplet_store",
            submodule="JenaStore",
            message=f"Adding {len(triplets)} triplets to Jena model",
        )

        try:
            if self.graph is None:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message="Graph not initialized"
                )
                raise ProcessingError("Graph not initialized")

            added_count = 0
            self.progress_tracker.update_tracking(
                tracking_id, message="Adding triplets to graph..."
            )
            for triplet in triplets:
                try:
                    subject = URIRef(triplet.subject)
                    predicate = URIRef(triplet.predicate)
                    obj = (
                        URIRef(triplet.object)
                        if triplet.object.startswith("http")
                        else Literal(triplet.object)
                    )

                    self.graph.add((subject, predicate, obj))
                    added_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to add triplet: {e}")

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Added {added_count}/{len(triplets)} triplets",
            )
            return {"success": True, "added": added_count, "total": len(triplets)}
        except Exception as e:
            self.logger.error(f"Failed to add triplets: {e}")
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise ProcessingError(f"Failed to add triplets: {e}")

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
        if self.graph is None:
            return []

        try:
            # Build SPARQL query
            query_parts = []
            if subject:
                query_parts.append(f"?s = <{subject}>")
            if predicate:
                query_parts.append(f"?p = <{predicate}>")
            if object:
                query_parts.append(f"?o = <{object}>")

            where_clause = " ".join(query_parts) if query_parts else ""
            query = f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o {where_clause} }}"

            results = self.graph.query(query)

            triplets = []
            for row in results:
                triplets.append(
                    Triplet(
                        subject=str(row.s),
                        predicate=str(row.p),
                        object=str(row.o),
                        metadata={"source": "jena"},
                    )
                )

            return triplets
        except Exception as e:
            self.logger.error(f"Failed to get triplets: {e}")
            return []

    def delete_triplet(self, triplet: Triplet, **options) -> Dict[str, Any]:
        """Delete triplet."""
        if self.graph is None:
            raise ProcessingError("Graph not initialized")

        try:
            subject = URIRef(triplet.subject)
            predicate = URIRef(triplet.predicate)
            obj = (
                URIRef(triplet.object)
                if triplet.object.startswith("http")
                else Literal(triplet.object)
            )

            self.graph.remove((subject, predicate, obj))

            return {"success": True}
        except Exception as e:
            self.logger.error(f"Failed to delete triplet: {e}")
            raise ProcessingError(f"Failed to delete triplet: {e}")

    def run_inference(self, model: Optional[Any] = None, **options) -> Dict[str, Any]:
        """
        Execute inference rules.

        Args:
            model: Optional model (uses default if not provided)
            **options: Inference options

        Returns:
            Inference results
        """
        if not self.enable_inference:
            self.logger.warning("Inference not enabled")
            return {"success": False, "message": "Inference not enabled"}

        # Basic inference would require OWL reasoner
        # This is a placeholder implementation
        self.logger.info("Inference would be executed here with OWL reasoner")

        return {
            "success": True,
            "inferred_triplets": 0,
            "message": "Inference placeholder",
        }

    def execute_sparql(self, query: str, **options) -> Dict[str, Any]:
        """
        Execute SPARQL query.

        Args:
            query: SPARQL query string
            **options: Additional options

        Returns:
            Query results
        """
        if self.graph is None:
            raise ProcessingError("Graph not initialized")

        try:
            results = self.graph.query(query)

            bindings = []
            variables = []

            if results.vars:
                variables = [str(v) for v in results.vars]

                for row in results:
                    binding = {}
                    for var in results.vars:
                        value = getattr(row, str(var))
                        if value:
                            binding[str(var)] = {
                                "value": str(value),
                                "type": "uri"
                                if isinstance(value, URIRef)
                                else "literal",
                            }
                    bindings.append(binding)

            return {
                "success": True,
                "bindings": bindings,
                "variables": variables,
                "metadata": {"query": query},
            }
        except Exception as e:
            self.logger.error(f"SPARQL query failed: {e}")
            raise ProcessingError(f"SPARQL query failed: {e}")

    def serialize(self, format: str = "turtle", **options) -> str:
        """
        Serialize graph to RDF format.

        Args:
            format: RDF format (turtle, rdfxml, n3)
            **options: Serialization options

        Returns:
            Serialized RDF string
        """
        if self.graph is None:
            return ""

        try:
            return self.graph.serialize(format=format)
        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
            return ""
