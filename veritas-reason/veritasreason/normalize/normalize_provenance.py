"""
Provenance-enabled wrapper for normalization.

Usage:
    from veritasreason.normalize.normalize_provenance import NormalizerWithProvenance
    
    normalizer = NormalizerWithProvenance(provenance=True)
    normalized_data = normalizer.normalize(data)

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class NormalizerWithProvenance:
    """Normalizer with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .normalizer import Normalizer
        
        self.provenance = provenance
        self._normalizer = Normalizer(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def normalize(self, data: Any, source: str = None, **kwargs):
        """Normalize data with provenance tracking."""
        result = self._normalizer.normalize(data, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"normalize_{uuid.uuid4().hex[:8]}",
                source=source or "normalization",
                entity_type="normalized_data",
                metadata={"method": kwargs.get('method', 'default')}
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._normalizer, name)


__all__ = ['NormalizerWithProvenance']
