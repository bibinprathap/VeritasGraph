"""
Provenance-enabled wrapper for graph storage.

Tracks: nodes added, edges created

Usage:
    from veritasreason.graph_store.graph_store_provenance import GraphStoreWithProvenance
    
    store = GraphStoreWithProvenance(provenance=True)
    store.add_node(node, source="doc1.pdf")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class GraphStoreWithProvenance:
    """Graph store with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .graph_store import GraphStore
        
        self.provenance = provenance
        self._store = GraphStore(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def add_node(self, node: Any, source: str = None, **kwargs):
        """Add node with provenance tracking."""
        result = self._store.add_node(node, **kwargs)
        
        if self.provenance and self._prov_manager:
            node_id = getattr(node, 'id', f"node_{uuid.uuid4().hex[:8]}")
            self._prov_manager.track_entity(
                entity_id=node_id,
                source=source or "graph_store",
                entity_type="graph_node",
                metadata={"properties": getattr(node, 'properties', {})}
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._store, name)


__all__ = ['GraphStoreWithProvenance']
