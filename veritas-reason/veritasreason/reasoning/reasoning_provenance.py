"""
Provenance-enabled wrappers for reasoning operations.

Tracks: premises, conclusions, inference rules, confidence scores

Usage:
    from veritasreason.reasoning.reasoning_provenance import ReasoningEngineWithProvenance
    
    reasoner = ReasoningEngineWithProvenance(provenance=True)
    result = reasoner.infer(premises)

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class ReasoningEngineWithProvenance:
    """Reasoning engine with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .reasoning_engine import ReasoningEngine
        
        self.provenance = provenance
        self._engine = ReasoningEngine(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def infer(self, premises: Any, source: str = None, **kwargs):
        """Perform inference with provenance tracking."""
        result = self._engine.infer(premises, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"inference_{uuid.uuid4().hex[:8]}",
                source=source or "reasoning_engine",
                entity_type="inference",
                metadata={
                    "premises_count": len(premises) if hasattr(premises, '__len__') else 1,
                    "confidence": getattr(result, 'confidence', None)
                }
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._engine, name)


__all__ = ['ReasoningEngineWithProvenance']
