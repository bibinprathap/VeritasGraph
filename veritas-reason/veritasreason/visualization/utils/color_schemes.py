"""
Color Schemes Module

This module provides color schemes and palettes for consistent visualization styling in the
VeritasReason framework, supporting multiple predefined color schemes and dynamic color generation
for entities, communities, and visualization elements.

Key Features:
    - Predefined color schemes (Default, Vibrant, Pastel, Dark, Light, Colorblind)
    - Dynamic color generation for arbitrary counts
    - Entity type color mapping
    - Community color assignment
    - Color scheme enumeration and lookup

Main Classes:
    - ColorScheme: Color scheme enumeration with predefined schemes
    - ColorPalette: Color palette manager with color generation methods

Example Usage:
    >>> from veritasreason.visualization.utils import ColorPalette, ColorScheme, get_color_scheme
    >>> colors = ColorPalette.get_colors(ColorScheme.VIBRANT, count=10)
    >>> entity_colors = ColorPalette.get_entity_type_colors(["PERSON", "ORG"], ColorScheme.DEFAULT)
    >>> community_colors = ColorPalette.get_community_colors(5, ColorScheme.PASTEL)
    >>> color = ColorPalette.get_color_by_index(ColorScheme.DEFAULT, 3)
    >>> scheme = get_color_scheme("vibrant")

Author: VeritasReason Contributors
License: MIT
"""

from enum import Enum
from typing import Dict, List, Optional


class ColorScheme(Enum):
    """Predefined color schemes."""

    DEFAULT = "default"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    DARK = "dark"
    LIGHT = "light"
    COLORBLIND = "colorblind"


class ColorPalette:
    """Color palette manager."""

    # Default color schemes
    SCHEMES = {
        ColorScheme.DEFAULT: [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ],
        ColorScheme.VIBRANT: [
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#FFA07A",
            "#98D8C8",
            "#F7DC6F",
            "#BB8FCE",
            "#85C1E2",
            "#F8B739",
            "#6C5CE7",
        ],
        ColorScheme.PASTEL: [
            "#FFB3BA",
            "#BAFFC9",
            "#BAE1FF",
            "#FFFFBA",
            "#FFDFBA",
            "#E0BBE4",
            "#FEC8C1",
            "#FFCCCB",
            "#DDA0DD",
            "#B0E0E6",
        ],
        ColorScheme.DARK: [
            "#2C3E50",
            "#34495E",
            "#7F8C8D",
            "#95A5A6",
            "#BDC3C7",
            "#ECF0F1",
            "#3498DB",
            "#E74C3C",
            "#F39C12",
            "#9B59B6",
        ],
        ColorScheme.LIGHT: [
            "#FFFFFF",
            "#F8F9FA",
            "#E9ECEF",
            "#DEE2E6",
            "#CED4DA",
            "#ADB5BD",
            "#6C757D",
            "#495057",
            "#343A40",
            "#212529",
        ],
        ColorScheme.COLORBLIND: [
            "#006BA4",
            "#FF800E",
            "#ABABAB",
            "#595959",
            "#5F9ED1",
            "#C85200",
            "#898989",
            "#A2C8EC",
            "#FFBC79",
            "#CFCFCF",
        ],
    }

    @classmethod
    def get_colors(
        cls, scheme: ColorScheme = ColorScheme.DEFAULT, count: int = 10
    ) -> List[str]:
        """
        Get color list for a scheme.

        Args:
            scheme: Color scheme to use
            count: Number of colors needed

        Returns:
            List of color hex codes
        """
        base_colors = cls.SCHEMES.get(scheme, cls.SCHEMES[ColorScheme.DEFAULT])

        if count <= len(base_colors):
            return base_colors[:count]

        # Repeat colors if more needed
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])

        return colors

    @classmethod
    def get_color_by_index(cls, scheme: ColorScheme, index: int) -> str:
        """
        Get a single color by index.

        Args:
            scheme: Color scheme to use
            index: Color index

        Returns:
            Color hex code
        """
        colors = cls.SCHEMES.get(scheme, cls.SCHEMES[ColorScheme.DEFAULT])
        return colors[index % len(colors)]

    @classmethod
    def get_entity_type_colors(
        cls, entity_types: List[str], scheme: ColorScheme = ColorScheme.DEFAULT
    ) -> Dict[str, str]:
        """
        Get color mapping for entity types.

        Args:
            entity_types: List of unique entity types
            scheme: Color scheme to use

        Returns:
            Dictionary mapping entity types to colors
        """
        colors = cls.get_colors(scheme, len(entity_types))
        return {entity_type: colors[i] for i, entity_type in enumerate(entity_types)}

    @classmethod
    def get_community_colors(
        cls, num_communities: int, scheme: ColorScheme = ColorScheme.DEFAULT
    ) -> List[str]:
        """
        Get colors for communities.

        Args:
            num_communities: Number of communities
            scheme: Color scheme to use

        Returns:
            List of colors for each community
        """
        return cls.get_colors(scheme, num_communities)


def get_color_scheme(scheme_name: str) -> ColorScheme:
    """
    Get color scheme by name.

    Args:
        scheme_name: Name of the color scheme

    Returns:
        ColorScheme enum value
    """
    try:
        return ColorScheme[scheme_name.upper()]
    except KeyError:
        return ColorScheme.DEFAULT
