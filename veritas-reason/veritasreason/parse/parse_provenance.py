"""
Provenance-enabled wrappers for parsing operations.

Tracks: file parsed, format, structure, parsing method

Usage:
    from veritasreason.parse.parse_provenance import JSONParserWithProvenance
    
    parser = JSONParserWithProvenance(provenance=True)
    data = parser.parse("data.json")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class ParserWithProvenance:
    """Base parser with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .parser import Parser
        
        self.provenance = provenance
        self._parser = Parser(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def parse(self, file_path: str, **kwargs):
        """Parse file with provenance tracking."""
        data = self._parser.parse(file_path, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"parse_{uuid.uuid4().hex[:8]}",
                source=file_path,
                entity_type="parsed_data",
                metadata={
                    "file_path": file_path,
                    "format": kwargs.get('format', 'unknown')
                }
            )
        
        return data
    
    def __getattr__(self, name):
        return getattr(self._parser, name)


__all__ = ['ParserWithProvenance']
