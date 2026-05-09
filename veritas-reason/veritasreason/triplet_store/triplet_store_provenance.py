"""
Provenance-enabled wrapper for triplet storage.

Tracks: triplets stored

Usage:
    from veritasreason.triplet_store.triplet_store_provenance import TripletStoreWithProvenance
    
    store = TripletStoreWithProvenance(provenance=True)
    store.add_triplet(subject, predicate, object, source="kg.json")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class TripletStoreWithProvenance:
    """Triplet store with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .triplet_store import TripletStore
        
        self.provenance = provenance
        self._store = TripletStore(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def add_triplet(self, subject: Any, predicate: Any, obj: Any, source: str = None, **kwargs):
        """Add triplet with provenance tracking."""
        result = self._store.add_triplet(subject, predicate, obj, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"triplet_{uuid.uuid4().hex[:8]}",
                source=source or "triplet_store",
                entity_type="triplet",
                metadata={
                    "subject": str(subject),
                    "predicate": str(predicate),
                    "object": str(obj)
                }
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._store, name)


__all__ = ['TripletStoreWithProvenance']
