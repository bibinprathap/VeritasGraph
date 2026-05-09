"""
Visualization Utilities Module

This module provides utility functions and classes for visualization operations in the
VeritasReason framework, including layout algorithms, color schemes, and export format handlers.

Key Features:
    - Graph layout algorithms (force-directed, hierarchical, circular)
    - Color scheme management and palettes
    - Export format handlers (Plotly, Matplotlib, HTML)
    - Entity type and community color mapping

Main Classes:
    - LayoutAlgorithm: Abstract base class for layout algorithms
    - ForceDirectedLayout: Force-directed spring layout algorithm
    - HierarchicalLayout: Hierarchical tree layout algorithm
    - CircularLayout: Circular node positioning algorithm
    - ColorScheme: Color scheme enumeration
    - ColorPalette: Color palette manager with predefined schemes

Example Usage:
    >>> from veritasreason.visualization.utils import ForceDirectedLayout, ColorPalette, ColorScheme
    >>> layout = ForceDirectedLayout(k=1.0, iterations=50)
    >>> positions = layout.compute_layout(nodes, edges)
    >>> colors = ColorPalette.get_colors(ColorScheme.VIBRANT, count=10)
    >>> entity_colors = ColorPalette.get_entity_type_colors(entity_types, ColorScheme.DEFAULT)
    >>> 
    >>> from veritasreason.visualization.utils import export_plotly_figure
    >>> export_plotly_figure(fig, "output.html", format="html")

Author: VeritasReason Contributors
License: MIT
"""

from .color_schemes import ColorPalette, ColorScheme, get_color_scheme
from .export_formats import export_matplotlib_figure, export_plotly_figure, save_html
from .layout_algorithms import (
    CircularLayout,
    ForceDirectedLayout,
    HierarchicalLayout,
    LayoutAlgorithm,
)

__all__ = [
    "LayoutAlgorithm",
    "ForceDirectedLayout",
    "HierarchicalLayout",
    "CircularLayout",
    "ColorScheme",
    "get_color_scheme",
    "ColorPalette",
    "export_plotly_figure",
    "export_matplotlib_figure",
    "save_html",
]
