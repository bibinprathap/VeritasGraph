"""
Provenance-enabled wrapper for context management.

Usage:
    from veritasreason.context.context_provenance import ContextManagerWithProvenance
    
    ctx = ContextManagerWithProvenance(provenance=True)
    ctx.add_context("context data", source="doc1.pdf")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Optional, Any
import uuid


class ContextManagerWithProvenance:
    """Context manager with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        """Initialize context manager with optional provenance."""
        from .context_manager import ContextManager
        
        self.provenance = provenance
        self._context_manager = ContextManager(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def add_context(self, context: Any, source: Optional[str] = None, **kwargs):
        """Add context with provenance tracking."""
        result = self._context_manager.add_context(context, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"context_{uuid.uuid4().hex[:8]}",
                source=source or "context_manager",
                entity_type="context",
                metadata={"context_preview": str(context)[:100]}
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._context_manager, name)


__all__ = ['ContextManagerWithProvenance']
