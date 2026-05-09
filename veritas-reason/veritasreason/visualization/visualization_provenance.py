"""
Provenance-enabled wrapper for visualization.

Usage:
    from veritasreason.visualization.visualization_provenance import VisualizerWithProvenance
    
    viz = VisualizerWithProvenance(provenance=True)
    viz.visualize(data, output="graph.png")

Author: VeritasReason Contributors
License: MIT
"""

from typing import Any
import uuid


class VisualizerWithProvenance:
    """Visualizer with provenance tracking."""
    
    def __init__(self, provenance: bool = False, **config):
        from .visualizer import Visualizer
        
        self.provenance = provenance
        self._visualizer = Visualizer(**config)
        self._prov_manager = None
        
        if provenance:
            try:
                from veritasreason.provenance import ProvenanceManager
                self._prov_manager = ProvenanceManager()
            except ImportError:
                self.provenance = False
    
    def visualize(self, data: Any, output: str = None, **kwargs):
        """Visualize data with provenance tracking."""
        result = self._visualizer.visualize(data, output=output, **kwargs)
        
        if self.provenance and self._prov_manager:
            self._prov_manager.track_entity(
                entity_id=f"viz_{uuid.uuid4().hex[:8]}",
                source="visualization",
                entity_type="visualization",
                metadata={"output": output, "type": kwargs.get('type', 'unknown')}
            )
        
        return result
    
    def __getattr__(self, name):
        return getattr(self._visualizer, name)


__all__ = ['VisualizerWithProvenance']
