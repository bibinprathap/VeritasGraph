"""
Provenance-enabled wrappers for document ingestion.

Tracks: file paths, pages, metadata, ingestion timestamps

Usage:
    from veritasreason.ingest.ingest_provenance import PDFIngestorWithProvenance
    
    ingestor = PDFIngestorWithProvenance(provenance=True)
    docs = ingestor.ingest("document.pdf")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Optional, List
import uuid


class IngestProvenanceMixin:
    """Mixin for ingest provenance tracking."""
    
    def __init__(self, provenance: bool = False, **kwargs):
        self.provenance = provenance
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False


class PDFIngestorWithProvenance(IngestProvenanceMixin):
    """PDF ingestor with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .pdf_ingestor import PDFIngestor
        
        IngestProvenanceMixin.__init__(self, provenance=provenance)
        self._ingestor = PDFIngestor(**config)
    
    def ingest(self, file_path: str, **kwargs):
        """Ingest PDF with provenance tracking."""
        docs = self._ingestor.ingest(file_path, **kwargs)
        
        if self.provenance and self._prov_manager:
            for doc in docs:
                doc_id = getattr(doc, 'id', f"doc_{uuid.uuid4().hex[:8]}")
                self._prov_manager.track_entity(
                    entity_id=doc_id,
                    source=file_path,
                    entity_type="document",
                    metadata={
                        "file_type": "pdf",
                        "pages": getattr(doc, 'page_count', None)
                    }
                )
        
        return docs
    
    def __getattr__(self, name):
        return getattr(self._ingestor, name)


__all__ = ['PDFIngestorWithProvenance', 'IngestProvenanceMixin']
