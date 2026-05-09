"""
Provenance-enabled wrapper for vector storage.

Tracks: vectors stored, dimensions

Usage:
    from veritasreason.vector_store.vector_store_provenance import VectorStoreWithProvenance
    
    store = VectorStoreWithProvenance(provenance=True)
    store.add_vectors(vectors, source="embeddings.npy")

Author: VeritasReason Contributors
License: MIT
"""

from typing import List, Any
import uuid


class VectorStoreWithProvenance:
    """Vector store with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .vector_store import VectorStore
        
        self.provenance = provenance
        self._store = VectorStore(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def add_vectors(self, vectors: List[Any], source: str = None, **kwargs):
        """Add vectors with provenance tracking."""
        result = self._store.add_vectors(vectors, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"vectors_{uuid.uuid4().hex[:8]}",
                source=source or "vector_store",
                entity_type="vector_collection",
                metadata={
                    "count": len(vectors),
                    "dimensions": len(vectors[0]) if vectors else 0
                }
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._store, name)


__all__ = ['VectorStoreWithProvenance']
