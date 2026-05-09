"""
Provenance-enabled wrapper for ontology operations.

Usage:
    from veritasreason.ontology.ontology_provenance import OntologyManagerWithProvenance
    
    ontology = OntologyManagerWithProvenance(provenance=True)
    ontology.add_concept(concept, source="ontology.owl")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class OntologyManagerWithProvenance:
    """Ontology manager with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .ontology_manager import OntologyManager
        
        self.provenance = provenance
        self._manager = OntologyManager(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def add_concept(self, concept: Any, source: str = None, **kwargs):
        """Add concept with provenance tracking."""
        result = self._manager.add_concept(concept, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"concept_{uuid.uuid4().hex[:8]}",
                source=source or "ontology",
                entity_type="ontology_concept",
                metadata={"concept_name": str(concept)}
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._manager, name)


__all__ = ['OntologyManagerWithProvenance']
