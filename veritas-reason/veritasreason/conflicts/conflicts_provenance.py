"""
Provenance-enabled wrapper for conflict detection with unified backend.

This module provides unified provenance backend integration for SourceTracker
while maintaining 100% backward compatibility.

Usage:
    from veritasreason.conflicts.conflicts_provenance import SourceTrackerWithUnifiedBackend
    
    tracker = SourceTrackerWithUnifiedBackend()
    tracker.track_property_source(entity_id, property_name, value, source)

Author: VeritasReason Contributors
License: MIT
"""

from typing import Optional, Dict, Any, List


class SourceTrackerWithUnifiedBackend:
    """SourceTracker using unified provenance backend."""
    
    def __init__(self, **config):
        """Initialize with unified backend or fallback to legacy."""
        from .source_tracker import SourceTracker
        
        try:
            from veritasreason.provenance import ProvenanceManager
            self._unified_manager = ProvenanceManager()
            self._use_unified = True
        except ImportError:
            self._use_unified = False
        
        self._original_tracker = SourceTracker(**config)
    
    def track_property_source(self, entity_id: str, property_name: str, value: Any, source: Any, **metadata):
        """Track property source with unified backend."""
        if self._use_unified:
            from veritasreason.provenance import SourceReference
            
            source_ref = SourceReference(
                document=source.document if hasattr(source, 'document') else str(source),
                page=getattr(source, 'page', None),
                section=getattr(source, 'section', None),
                confidence=getattr(source, 'confidence', 1.0)
            )
            
            self._unified_manager.track_property_source(
                entity_id=entity_id,
                property_name=property_name,
                value=value,
                source=source_ref,
                **metadata
            )
        else:
            self._original_tracker.track_property_source(
                entity_id, property_name, value, source, **metadata
            )
    
    def __getattr__(self, name):
        return getattr(self._original_tracker, name)


__all__ = ['SourceTrackerWithUnifiedBackend']
