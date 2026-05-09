"""
Provenance-enabled wrapper for deduplication.

Tracks: duplicates found, merge operations, deduplication strategy

Usage:
    from veritasreason.deduplication.deduplication_provenance import DeduplicatorWithProvenance
    
    dedup = DeduplicatorWithProvenance(provenance=True)
    unique_items = dedup.deduplicate(items)

Author: VeritasReason Contributors
License: MIT
"""

from typing import List, Any
import uuid


class DeduplicatorWithProvenance:
    """Deduplicator with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .deduplicator import Deduplicator
        
        self.provenance = provenance
        self._deduplicator = Deduplicator(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def deduplicate(self, items: List[Any], source: str = None, **kwargs):
        """Deduplicate items with provenance tracking."""
        unique_items = self._deduplicator.deduplicate(items, **kwargs)
        
        if self.provenance and self._prov_manager:
            duplicates_found = len(items) - len(unique_items)
            self._prov_manager.track_entity(
                entity_id=f"dedup_{uuid.uuid4().hex[:8]}",
                source=source or "deduplication",
                entity_type="deduplication_operation",
                metadata={
                    "input_count": len(items),
                    "output_count": len(unique_items),
                    "duplicates_removed": duplicates_found
                }
            )
        
        return unique_items
    
    def __getattr__(self, name):
        return getattr(self._deduplicator, name)


__all__ = ['DeduplicatorWithProvenance']
