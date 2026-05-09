"""
Provenance-enabled wrappers for export operations.

Tracks: export format, destination, timestamp, data exported

Usage:
    from veritasreason.export.export_provenance import JSONExporterWithProvenance
    
    exporter = JSONExporterWithProvenance(provenance=True)
    exporter.export(data, "output.json")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class ExporterWithProvenance:
    """Base exporter with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .exporter import Exporter
        
        self.provenance = provenance
        self._exporter = Exporter(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def export(self, data: Any, destination: str, **kwargs):
        """Export data with provenance tracking."""
        result = self._exporter.export(data, destination, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"export_{uuid.uuid4().hex[:8]}",
                source="export_operation",
                entity_type="export",
                metadata={
                    "destination": destination,
                    "format": kwargs.get('format', 'unknown')
                }
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._exporter, name)


__all__ = ['ExporterWithProvenance']
