"""
Enhanced Version Managers Module

This module provides enhanced version management capabilities for both knowledge graphs
and ontologies, with comprehensive change tracking, persistent storage, and audit trails.

Key Features:
    - Enhanced TemporalVersionManager for knowledge graphs
    - Enhanced VersionManager for ontologies
    - Detailed diff algorithms for entities and relationships
    - Structural comparison for ontology elements
    - Integration with storage backends and metadata

Main Classes:
    - EnhancedTemporalVersionManager: Advanced KG version management
    - EnhancedVersionManager: Advanced ontology version management

Author: VeritasReason Contributors
License: MIT
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .change_log import ChangeLogEntry
from .version_storage import (
    VersionStorage,
    InMemoryVersionStorage,
    SQLiteVersionStorage,
    compute_checksum,
    verify_checksum,
)
from ..utils.exceptions import ValidationError, ProcessingError
from ..utils.logging import get_logger


class BaseVersionManager(ABC):
    """
    Abstract base class for enhanced version managers.

    Provides common functionality for version management across different data types.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize base version manager.

        Args:
            storage_path: Path to SQLite database for persistent storage.
                         If None, uses in-memory storage.
        """
        self.logger = get_logger(self.__class__.__name__.lower())

        # Initialize storage backend
        if storage_path:
            self.storage = SQLiteVersionStorage(storage_path)
            self.logger.info(f"Initialized with SQLite storage: {storage_path}")
        else:
            self.storage = InMemoryVersionStorage()
            self.logger.info("Initialized with in-memory storage")

    @abstractmethod
    def create_snapshot(
        self, data: Any, version_label: str, author: str, description: str, **options
    ) -> Dict[str, Any]:
        """Create a versioned snapshot of the data."""
        pass

    @abstractmethod
    def compare_versions(
        self, version1: Any, version2: Any, **options
    ) -> Dict[str, Any]:
        """Compare two versions and return detailed differences."""
        pass

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all version snapshots."""
        return self.storage.list_all()

    def get_version(self, label: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific version by label."""
        return self.storage.get(label)

    def verify_checksum(self, snapshot: Dict[str, Any]) -> bool:
        """Verify the integrity of a snapshot using its checksum."""
        return verify_checksum(snapshot)


class TemporalVersionManager(BaseVersionManager):
    """
    Temporal version management engine for knowledge graphs.

    Provides comprehensive version/snapshot management capabilities including
    persistent storage, detailed change tracking, and audit trails.

    Features:
        - Persistent snapshot storage (SQLite or in-memory)
        - Detailed change tracking with entity-level diffs
        - SHA-256 checksums for data integrity
        - Standardized metadata with author attribution
        - Version comparison with backward compatibility
        - Input validation and security features
    """

    def __init__(self, storage_path: Optional[str] = None, **config):
        """
        Initialize enhanced temporal version manager.

        Args:
            storage_path: Path to SQLite database file for persistent storage.
                         If None, uses in-memory storage
            **config: Additional configuration options
        """
        super().__init__(storage_path)
        self.config = config
        self._attached_graphs: List[Any] = []

    def create_snapshot(
        self,
        graph: Dict[str, Any],
        version_label: str,
        author: str,
        description: str,
        **options,
    ) -> Dict[str, Any]:
        """
        Create and store snapshot with checksum and metadata.

        Args:
            graph: Knowledge graph dict with "nodes"/"edges" or
                legacy "entities"/"relationships"
            version_label: Version string (e.g., "v1.0")
            author: Email address of the change author
            description: Change description (max 500 chars)
            **options: Additional options

        Returns:
            dict: Snapshot with metadata and checksum

        Raises:
            ValidationError: If input validation fails
            ProcessingError: If storage operation fails
        """
        change_entry = ChangeLogEntry(
            timestamp=datetime.now().isoformat(), author=author, description=description
        )
        entities, relationships = self._extract_graph_collections(graph)

        snapshot = {
            "label": version_label,
            "timestamp": change_entry.timestamp,
            "author": change_entry.author,
            "description": change_entry.description,
            # Store both key shapes during the migration window so older
            # readers and newer ContextGraph restore paths both work.
            "nodes": entities.copy(),
            "edges": relationships.copy(),
            "entities": entities.copy(),
            "relationships": relationships.copy(),
            "metadata": options.get("metadata", {}),
        }

        snapshot["checksum"] = compute_checksum(snapshot)
        self.storage.save(snapshot)
        self.storage.assign_version_to_unlabeled_mutations(version_label)
        self.logger.info(f"Created snapshot '{version_label}' by {author}")
        return snapshot

    def _extract_graph_collections(
        self, graph: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Normalize graph payloads to entity/relationship collections."""
        if not isinstance(graph, dict):
            raise ValidationError("Graph must be provided as a dictionary")

        has_node_schema = "nodes" in graph or "edges" in graph
        has_legacy_schema = "entities" in graph or "relationships" in graph
        if not (has_node_schema or has_legacy_schema):
            raise ValidationError(
                "Graph dictionary must contain 'nodes'/'edges' or "
                "'entities'/'relationships'"
            )

        entities = graph.get("nodes")
        if entities is None:
            entities = graph.get("entities", [])

        relationships = graph.get("edges")
        if relationships is None:
            relationships = graph.get("relationships", [])

        return list(entities or []), list(relationships or [])

    def compare_versions(
        self,
        v1_label_or_dict,
        v2_label_or_dict,
        comparison_metrics: Optional[List[str]] = None,
        **options,
    ) -> Dict[str, Any]:
        """
        Compare two graph versions with detailed entity-level differences.

        Args:
            v1_label_or_dict: First version (label string or snapshot dict)
            v2_label_or_dict: Second version (label string or snapshot dict)
            comparison_metrics: List of metrics to calculate (optional, unused)
            **options: Additional comparison options (unused)

        Returns:
            dict: Detailed version comparison results
        """
        if isinstance(v1_label_or_dict, str):
            version1 = self.storage.get(v1_label_or_dict)
            if not version1:
                raise ValidationError(f"Version not found: {v1_label_or_dict}")
        else:
            version1 = v1_label_or_dict

        if isinstance(v2_label_or_dict, str):
            version2 = self.storage.get(v2_label_or_dict)
            if not version2:
                raise ValidationError(f"Version not found: {v2_label_or_dict}")
        else:
            version2 = v2_label_or_dict

        detailed_diff = self._compute_detailed_diff(version1, version2)

        summary = {
            "entities_added": len(detailed_diff["entities_added"]),
            "entities_removed": len(detailed_diff["entities_removed"]),
            "entities_modified": len(detailed_diff["entities_modified"]),
            "relationships_added": len(detailed_diff["relationships_added"]),
            "relationships_removed": len(detailed_diff["relationships_removed"]),
            "relationships_modified": len(detailed_diff["relationships_modified"]),
            "nodes_added": len(detailed_diff["nodes_added"]),
            "nodes_removed": len(detailed_diff["nodes_removed"]),
            "nodes_modified": len(detailed_diff["nodes_modified"]),
            "edges_added": len(detailed_diff["edges_added"]),
            "edges_removed": len(detailed_diff["edges_removed"]),
            "edges_modified": len(detailed_diff["edges_modified"]),
        }

        return {
            "version1": version1.get("label", "unknown"),
            "version2": version2.get("label", "unknown"),
            "summary": summary,
            **detailed_diff,
        }

    def _compute_detailed_diff(
        self, version1: Dict[str, Any], version2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute detailed entity and relationship differences between versions.

        Args:
            version1: First version snapshot
            version2: Second version snapshot

        Returns:
            Dict with detailed diff information
        """
        version1_entities, version1_relationships = self._extract_graph_collections(
            version1
        )
        version2_entities, version2_relationships = self._extract_graph_collections(
            version2
        )

        nodes1 = {n.get("id", str(i)): n for i, n in enumerate(version1_entities)}
        nodes2 = {n.get("id", str(i)): n for i, n in enumerate(version2_entities)}

        edges1 = {self._relationship_key(e): e for e in version1_relationships}
        edges2 = {self._relationship_key(e): e for e in version2_relationships}


        node_ids1 = set(nodes1.keys())
        node_ids2 = set(nodes2.keys())

        nodes_added = [nodes2[nid] for nid in node_ids2 - node_ids1]
        nodes_removed = [nodes1[nid] for nid in node_ids1 - node_ids2]
        nodes_modified = []
        for nid in node_ids1 & node_ids2:
            if nodes1[nid] != nodes2[nid]:
                changes = self._compute_entity_changes(nodes1[nid], nodes2[nid])
                nodes_modified.append({
                    "id": nid, "before": nodes1[nid], "after": nodes2[nid], "changes": changes
                })


        edge_keys1 = set(edges1.keys())
        edge_keys2 = set(edges2.keys())

        edges_added = [edges2[k] for k in edge_keys2 - edge_keys1]
        edges_removed = [edges1[k] for k in edge_keys1 - edge_keys2]
        edges_modified = []
        for k in edge_keys1 & edge_keys2:
            if edges1[k] != edges2[k]:
                changes = self._compute_relationship_changes(edges1[k], edges2[k])
                edges_modified.append({
                    "key": k, "before": edges1[k], "after": edges2[k], "changes": changes
                })

        return {
            "entities_added": nodes_added,
            "entities_removed": nodes_removed,
            "entities_modified": nodes_modified,
            "relationships_added": edges_added,
            "relationships_removed": edges_removed,
            "relationships_modified": edges_modified,
            "nodes_added": nodes_added,
            "nodes_removed": nodes_removed,
            "nodes_modified": nodes_modified,
            "edges_added": edges_added,
            "edges_removed": edges_removed,
            "edges_modified": edges_modified,
        }
        
        
    def _relationship_key(self, relationship: Dict[str, Any]) -> str:
        """Generate a unique key for a relationship."""
        source = relationship.get("source", "")
        target = relationship.get("target", "")
        rel_type = relationship.get("type", relationship.get("relationship", ""))
        return f"{source}|{rel_type}|{target}"

    def _compute_entity_changes(
        self, entity1: Dict[str, Any], entity2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute changes between two entity versions."""
        changes = {}
        all_keys = set(entity1.keys()) | set(entity2.keys())

        for key in all_keys:
            val1 = entity1.get(key)
            val2 = entity2.get(key)

            if val1 != val2:
                changes[key] = {"from": val1, "to": val2}

        return changes

    def _compute_relationship_changes(
        self, rel1: Dict[str, Any], rel2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute changes between two relationship versions."""
        changes = {}
        all_keys = set(rel1.keys()) | set(rel2.keys())

        for key in all_keys:
            val1 = rel1.get(key)
            val2 = rel2.get(key)

            if val1 != val2:
                changes[key] = {"from": val1, "to": val2}

        return changes
    
    def prune_versions(self, keep_last_n: int = 5, triplet_store: Any = None) -> Dict [str, Any]:
        """
        Prune old snapshots, keeping only the most recent N versions.
        Optionally deletes the backend graphs from the triplet store to free space.

        Args:
            keep_last_n: Number of recent versions to retain.
            triplet_store: Optional TripletStore instance to execute DROP GRAPH.
            
        Returns:
            Dict containing counts and labels of pruned versions.
        """
        
        all_versions = self.list_versions()
        all_versions.sort(key = lambda x: x.get("timestamp", ""), reverse=True)
        
        versions_to_delete = all_versions[keep_last_n:]
        deleted_labels = []
        
        for v in versions_to_delete:
            label = v.get("label")
            graph_uri = v.get("graph_uri")
            
            # delete metadata from SQLite / In-Memory
            if self.storage.delete(label):
                deleted_labels.append(label)
                
                # Clean up the actual graph if provided
                if triplet_store and graph_uri:
                    try:
                        safe_graph_uri = self._sanitize_graph_uri(graph_uri)
                        triplet_store.execute_query(
                            f"DROP SILENT GRAPH <{safe_graph_uri}>"
                        )
                        self.logger.info(f"Dropped obsolete graph {graph_uri} from store")
                    except Exception as e:
                        self.logger.warning(f"Failed to drop graph {graph_uri} during pruning: {e}")
        
        self.logger.info(f"Pruned {len(deleted_labels)} old versions, kept {keep_last_n}")
        return {
            "pruned_count": len(deleted_labels),
            "pruned_versions": deleted_labels,
            "retained_count": len(all_versions) - len(deleted_labels)
        }

    def _sanitize_graph_uri(self, graph_uri: Any) -> str:
        """Percent-encode unsafe characters before embedding a graph URI in SPARQL."""
        raw_uri = str(graph_uri).strip().strip("<>")
        return quote(raw_uri, safe="/:?&=@[]!$'()*+,%-._~")
    
    # Git-like audit trails

    def attach_to_graph(self, graph: Any) -> None:
        """
        Attach this manager to a ContextGraph to enable mutation tracking.
        Injects the mutation callback into the graph to capture all node/edge changes.
        """
        graph.mutation_callback = self.record_mutation
        if graph not in self._attached_graphs:
            self._attached_graphs.append(graph)
        self.logger.info(f"Attached mutation tracking to graph: {getattr(graph, 'graph_id', 'unknown')}")

    def record_mutation(
        self, 
        operation: str, 
        entity_id: str, 
        payload: Dict[str, Any],
        version_label: Optional[str] = None
    ) -> None:
        """
        Callback triggered by the graph to record granular mutations.
        """
        from .change_log import MutationRecord
        record = MutationRecord(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            entity_id=entity_id,
            payload=payload,
            version_label=version_label
        )
        
        mutation_dict = {
            "timestamp": record.timestamp,
            "operation": record.operation,
            "entity_id": record.entity_id,
            "payload": record.payload,
            "version_label": record.version_label
        }
        self.storage.save_mutation(mutation_dict)
        self.logger.debug(f"Recorded mutation: {operation} on {entity_id}")
    def tag_version(self, version_label: str, tag_name: str) -> None:
        """
        Create a named tag (e.g., 'v1.0-approved') for a specific version.
        """
        if not self.storage.exists(version_label):
            raise ValidationError(f"Cannot tag non-existent version: '{version_label}'")
        
        self.storage.save_tag(tag_name, version_label)
        self.logger.info(f"Tagged version '{version_label}' as '{tag_name}'")

    def list_tags(self) -> Dict[str, str]:
        """
        Return a mapping of all tag names to their version labels.
        """
        return self.storage.list_tags()

    def diff(self, version_a: str, version_b: str) -> Dict[str, Any]:
        """
        Git-like alias for compare_versions. Computes added/removed/modified entities.
        """
        return self.compare_versions(version_a, version_b)

    def get_node_history(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve the complete chronological mutation history for a specific node.
        """
        return self.storage.get_entity_history(node_id)

    def restore_snapshot(self, graph: Any, target_version: str, require_confirmation: bool = True) -> bool:
        """
        Restore the graph to a specific version snapshot.
        
        Args:
            graph: The ContextGraph instance to restore.
            target_version: The version label to restore to.
            require_confirmation: If True, raises ProcessingError to prevent accidental data loss.
        """
        if require_confirmation:
            raise ProcessingError(
                "Rollback protection active. Explicitly set require_confirmation=False "
                "to overwrite the current graph state."
            )

        snapshot = self.storage.get(target_version)
        if not snapshot:
            raise ValidationError(f"Version '{target_version}' not found in storage.")

        self.logger.warning(f"Restoring graph to version '{target_version}' - clearing current state.")
        
        entities, relationships = self._extract_graph_collections(snapshot)
        graph_payload = {"nodes": entities, "edges": relationships}

        previous_state = getattr(graph, "_suspend_mutation_callback", False)
        graph._suspend_mutation_callback = True
        try:
            graph.from_dict(graph_payload)
        finally:
            graph._suspend_mutation_callback = previous_state
        
        self.logger.info(f"Successfully restored graph to version '{target_version}'.")
        return True
        
                        
class OntologyVersionManager(BaseVersionManager):
    """
    Version management for ontologies with structural comparison.

    Provides comprehensive version management for ontologies including
    detailed structural analysis and change tracking.

    Features:
        - Structural comparison of ontology elements
        - Detailed diff for classes, properties, individuals, axioms
        - Persistent storage with metadata
        - Change tracking and audit trails
    """

    def __init__(self, storage_path: Optional[str] = None, **config):
        """
        Initialize enhanced version manager.

        Args:
            storage_path: Path to SQLite database file for persistent storage.
                         If None, uses in-memory storage
            **config: Additional configuration options
        """
        super().__init__(storage_path)
        self.config = config
        self.versions = {}  # In-memory version tracking for compatibility

    def create_snapshot(
        self,
        ontology_data: Dict[str, Any],
        version_label: str,
        author: str,
        description: str,
        **options,
    ) -> Dict[str, Any]:
        """
        Create ontology version snapshot.

        Args:
            ontology_data: Ontology data dictionary
            version_label: Version string (e.g., "v1.0")
            author: Email address of the change author
            description: Change description
            **options: Additional options including metadata

        Returns:
            dict: Ontology version snapshot
        """
        change_entry = ChangeLogEntry(
            timestamp=datetime.now().isoformat(), author=author, description=description
        )

        snapshot = {
            "label": version_label,
            "timestamp": change_entry.timestamp,
            "author": change_entry.author,
            "description": change_entry.description,
            "ontology_iri": ontology_data.get("uri", ""),
            "version_info": ontology_data.get("version_info", {}),
            "structure": ontology_data.get("structure", {}),
            "metadata": options.get("metadata", {}),
        }

        snapshot["checksum"] = compute_checksum(snapshot)
        self.storage.save(snapshot)
        self.versions[version_label] = snapshot
        self.logger.info(f"Created ontology snapshot '{version_label}' by {author}")
        return snapshot

    def compare_versions(
        self, version1: str, version2: str, **options
    ) -> Dict[str, Any]:
        """
        Compare two ontology versions with detailed structural analysis.

        Args:
            version1: First version label
            version2: Second version label
            **options: Additional comparison options

        Returns:
            Detailed comparison results including structural differences
        """
        # Get versions from storage
        v1_snapshot = self.storage.get(version1)
        v2_snapshot = self.storage.get(version2)

        if not v1_snapshot:
            raise ValidationError(f"Version not found: {version1}")
        if not v2_snapshot:
            raise ValidationError(f"Version not found: {version2}")

        # Basic metadata comparison
        metadata_changes = {}
        if v1_snapshot.get("ontology_iri") != v2_snapshot.get("ontology_iri"):
            metadata_changes["ontology_iri"] = {
                "from": v1_snapshot.get("ontology_iri"),
                "to": v2_snapshot.get("ontology_iri"),
            }
        if v1_snapshot.get("version_info") != v2_snapshot.get("version_info"):
            metadata_changes["version_info"] = {
                "from": v1_snapshot.get("version_info"),
                "to": v2_snapshot.get("version_info"),
            }

        # Structural comparison
        structural_diff = self._compare_ontology_structures(v1_snapshot, v2_snapshot)

        return {
            "version1": version1,
            "version2": version2,
            "metadata_changes": metadata_changes,
            **structural_diff,
        }

    def _compare_ontology_structures(
        self, v1_snapshot: Dict[str, Any], v2_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare structural elements between two ontology versions.

        Args:
            v1_snapshot: First ontology version snapshot
            v2_snapshot: Second ontology version snapshot

        Returns:
            Dictionary with structural differences
        """
        # Extract structural information
        v1_structure = v1_snapshot.get("structure", {})
        v2_structure = v2_snapshot.get("structure", {})

        # Compare classes
        v1_classes = set(v1_structure.get("classes", []))
        v2_classes = set(v2_structure.get("classes", []))

        classes_added = list(v2_classes - v1_classes)
        classes_removed = list(v1_classes - v2_classes)

        # Compare properties
        v1_properties = set(v1_structure.get("properties", []))
        v2_properties = set(v2_structure.get("properties", []))

        properties_added = list(v2_properties - v1_properties)
        properties_removed = list(v1_properties - v2_properties)

        # Compare individuals
        v1_individuals = set(v1_structure.get("individuals", []))
        v2_individuals = set(v2_structure.get("individuals", []))

        individuals_added = list(v2_individuals - v1_individuals)
        individuals_removed = list(v1_individuals - v2_individuals)

        # Compare axioms/rules
        v1_axioms = set(v1_structure.get("axioms", []))
        v2_axioms = set(v2_structure.get("axioms", []))

        axioms_added = list(v2_axioms - v1_axioms)
        axioms_removed = list(v1_axioms - v2_axioms)

        return {
            "classes_added": classes_added,
            "classes_removed": classes_removed,
            "properties_added": properties_added,
            "properties_removed": properties_removed,
            "individuals_added": individuals_added,
            "individuals_removed": individuals_removed,
            "axioms_added": axioms_added,
            "axioms_removed": axioms_removed,
            "summary": {
                "classes_added": len(classes_added),
                "classes_removed": len(classes_removed),
                "properties_added": len(properties_added),
                "properties_removed": len(properties_removed),
                "individuals_added": len(individuals_added),
                "individuals_removed": len(individuals_removed),
                "axioms_added": len(axioms_added),
                "axioms_removed": len(axioms_removed),
            },
        }
