"""
Provenance-enabled wrappers for embedding generation.

Tracks: model, dimensions, input texts, embedding vectors

Usage:
    from veritasreason.embeddings.embeddings_provenance import EmbeddingGeneratorWithProvenance
    
    embedder = EmbeddingGeneratorWithProvenance(provenance=True)
    embeddings = embedder.embed(["text1", "text2"])

Author: VeritasReason Contributors
License: MIT
"""

from typing import List
import uuid


class EmbeddingGeneratorWithProvenance:
    """Embedding generator with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .embedding_generator import EmbeddingGenerator
        
        self.provenance = provenance
        self._generator = EmbeddingGenerator(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def embed(self, texts: List[str], source: str = None, **kwargs):
        """Generate embeddings with provenance tracking."""
        embeddings = self._generator.embed(texts, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"embed_{uuid.uuid4().hex[:8]}",
                source=source or "embedding_generation",
                entity_type="embeddings",
                metadata={
                    "model": getattr(self._generator, 'model', 'unknown'),
                    "dimensions": len(embeddings[0]) if embeddings else 0,
                    "count": len(embeddings)
                }
            )
        
        return embeddings
    
    def __getattr__(self, name):
        return getattr(self._generator, name)


__all__ = ['EmbeddingGeneratorWithProvenance']
