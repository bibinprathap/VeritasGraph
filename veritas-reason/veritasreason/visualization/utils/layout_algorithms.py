"""
Layout Algorithms Module

This module provides various layout algorithms for positioning nodes in graph visualizations
in the VeritasReason framework, including force-directed, hierarchical, and circular layouts
with NetworkX integration and fallback implementations.

Key Features:
    - Force-directed spring layout algorithm
    - Hierarchical tree layout algorithm
    - Circular node positioning algorithm
    - NetworkX integration with fallback implementations
    - Configurable layout parameters
    - Optional dependency handling

Main Classes:
    - LayoutAlgorithm: Abstract base class for layout algorithms
    - ForceDirectedLayout: Force-directed spring layout with NetworkX support
    - HierarchicalLayout: Hierarchical tree layout with graphviz support
    - CircularLayout: Circular node positioning algorithm

Example Usage:
    >>> from veritasreason.visualization.utils import ForceDirectedLayout, HierarchicalLayout
    >>> force_layout = ForceDirectedLayout(k=1.0, iterations=50)
    >>> positions = force_layout.compute_layout(nodes, edges)
    >>> 
    >>> hierarchical_layout = HierarchicalLayout(vertical_spacing=2.0)
    >>> positions = hierarchical_layout.compute_layout(nodes, edges, root="root_node")
    >>> 
    >>> from veritasreason.visualization.utils import CircularLayout
    >>> circular_layout = CircularLayout(radius=1.5)
    >>> positions = circular_layout.compute_layout(nodes, edges)

Author: VeritasReason Contributors
License: MIT
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from ...utils.logging import get_logger


class LayoutAlgorithm(ABC):
    """Abstract base class for graph layout algorithms."""

    @abstractmethod
    def compute_layout(
        self, nodes: List[str], edges: List[Tuple[str, str]], **options
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute node positions for graph layout.

        Args:
            nodes: List of node identifiers
            edges: List of (source, target) edge tuples
            **options: Layout-specific options

        Returns:
            Dictionary mapping node IDs to (x, y) coordinates
        """
        pass


class ForceDirectedLayout(LayoutAlgorithm):
    """
    Force-directed layout algorithm (spring layout).

    Uses force-directed positioning to create visually appealing graph layouts.
    """

    def __init__(self, **config):
        """Initialize force-directed layout."""
        self.logger = get_logger("force_directed_layout")
        self.config = config
        self.k = config.get("k", 1.0)  # Optimal distance between nodes
        self.iterations = config.get("iterations", 50)
        self.temperature = config.get("temperature", 1.0)
        self.cooling_factor = config.get("cooling_factor", 0.95)

    def compute_layout(
        self, nodes: List[str], edges: List[Tuple[str, str]], **options
    ) -> Dict[str, Tuple[float, float]]:
        """Compute force-directed layout."""
        if len(nodes) > 0:
            try:
                # Create NetworkX graph
                G = nx.Graph()
                G.add_nodes_from(nodes)
                G.add_edges_from(edges)

                # Use NetworkX layout
                algorithm = options.get("algorithm", "spring")
                
                if algorithm == "kamada_kawai":
                    pos = nx.kamada_kawai_layout(G, **{k: v for k, v in options.items() if k in ["weight", "scale", "center", "dim"]})
                else:
                    # Default to spring layout
                    pos = nx.spring_layout(
                        G, k=self.k, iterations=self.iterations, **{k: v for k, v in options.items() if k in ["weight", "scale", "center", "dim", "seed"]}
                    )

                return {
                    node: (float(pos[node][0]), float(pos[node][1])) for node in nodes
                }
            except Exception as e:
                self.logger.warning(
                    f"NetworkX layout failed: {e}, using basic implementation"
                )

        # Basic force-directed implementation
        return self._basic_force_directed(nodes, edges)

    def _basic_force_directed(
        self, nodes: List[str], edges: List[Tuple[str, str]]
    ) -> Dict[str, Tuple[float, float]]:
        """Basic force-directed layout implementation."""
        n = len(nodes)
        if n == 0:
            return {}

        # Initialize positions randomly
        pos = {node: (np.random.random(), np.random.random()) for node in nodes}

        # Build adjacency
        adjacency = {node: [] for node in nodes}
        for source, target in edges:
            if source in adjacency and target in adjacency:
                adjacency[source].append(target)
                adjacency[target].append(source)

        # Iterative force-directed positioning
        temp = self.temperature
        for _ in range(self.iterations):
            forces = {node: np.array([0.0, 0.0]) for node in nodes}

            # Repulsive forces (all nodes repel each other)
            for i, node1 in enumerate(nodes):
                for node2 in nodes[i + 1 :]:
                    dx = pos[node2][0] - pos[node1][0]
                    dy = pos[node2][1] - pos[node1][1]
                    dist_sq = dx * dx + dy * dy + 0.01  # Avoid division by zero
                    dist = np.sqrt(dist_sq)

                    force = self.k * self.k / dist_sq
                    forces[node1] += np.array([-force * dx / dist, -force * dy / dist])
                    forces[node2] += np.array([force * dx / dist, force * dy / dist])

            # Attractive forces (connected nodes attract)
            for source, target in edges:
                if source in pos and target in pos:
                    dx = pos[target][0] - pos[source][0]
                    dy = pos[target][1] - pos[source][1]
                    dist_sq = dx * dx + dy * dy + 0.01
                    dist = np.sqrt(dist_sq)

                    force = dist * dist / self.k
                    forces[source] += np.array([force * dx / dist, force * dy / dist])
                    forces[target] += np.array([-force * dx / dist, -force * dy / dist])

            # Update positions
            for node in nodes:
                force = forces[node]
                force_mag = np.linalg.norm(force)
                if force_mag > temp:
                    force = force * temp / force_mag

                pos[node] = (pos[node][0] + force[0], pos[node][1] + force[1])

            # Cool down
            temp *= self.cooling_factor

        return pos


class HierarchicalLayout(LayoutAlgorithm):
    """
    Hierarchical/tree layout algorithm.

    Positions nodes in a hierarchical tree structure.
    """

    def __init__(self, **config):
        """Initialize hierarchical layout."""
        self.logger = get_logger("hierarchical_layout")
        self.config = config
        self.vertical_spacing = config.get("vertical_spacing", 2.0)
        self.horizontal_spacing = config.get("horizontal_spacing", 1.0)

    def compute_layout(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]],
        root: Optional[str] = None,
        **options,
    ) -> Dict[str, Tuple[float, float]]:
        """Compute hierarchical layout."""
        if len(nodes) > 0:
            try:
                G = nx.DiGraph()
                G.add_nodes_from(nodes)
                G.add_edges_from(edges)

                # Find root if not provided
                if root is None:
                    roots = [n for n in G.nodes() if G.in_degree(n) == 0]
                    root = roots[0] if roots else nodes[0]

                # Try NetworkX hierarchical layout (requires graphviz)
                try:
                    pos = nx.nx_agraph.graphviz_layout(G, prog="dot", root=root)
                    if pos:
                        return {
                            node: (float(pos[node][0]), float(pos[node][1]))
                            for node in nodes
                        }
                except Exception:
                    pass  # Fall through to simple hierarchical layout
            except Exception as e:
                self.logger.warning(
                    f"NetworkX hierarchical layout failed: {e}, using basic implementation"
                )

        root = root or nodes[0] if nodes else None
        return self._simple_hierarchical(nodes, edges, root)

    def _simple_hierarchical(
        self, nodes: List[str], edges: List[Tuple[str, str]], root: Optional[str]
    ) -> Dict[str, Tuple[float, float]]:
        """Simple hierarchical layout implementation."""
        if not nodes:
            return {}

        if root is None:
            root = nodes[0]

        # Build tree structure
        children = {node: [] for node in nodes}
        parents = {node: None for node in nodes}

        for source, target in edges:
            if source in children and target in children:
                children[source].append(target)
                parents[target] = source

        # Assign levels (BFS)
        levels = {root: 0}
        queue = [root]

        while queue:
            node = queue.pop(0)
            for child in children.get(node, []):
                if child not in levels:
                    levels[child] = levels[node] + 1
                    queue.append(child)

        # Position nodes
        pos = {}
        level_nodes = {}
        for node, level in levels.items():
            if level not in level_nodes:
                level_nodes[level] = []
            level_nodes[level].append(node)

        for level, nodes_at_level in sorted(level_nodes.items()):
            y = -level * self.vertical_spacing
            x_spacing = self.horizontal_spacing
            start_x = -(len(nodes_at_level) - 1) * x_spacing / 2

            for i, node in enumerate(nodes_at_level):
                x = start_x + i * x_spacing
                pos[node] = (x, y)

        # Position unconnected nodes
        for node in nodes:
            if node not in pos:
                pos[node] = (0, 0)

        return pos


class CircularLayout(LayoutAlgorithm):
    """
    Circular layout algorithm.

    Positions nodes in a circle.
    """

    def __init__(self, **config):
        """Initialize circular layout."""
        self.logger = get_logger("circular_layout")
        self.config = config
        self.radius = config.get("radius", 1.0)

    def compute_layout(
        self, nodes: List[str], edges: List[Tuple[str, str]], **options
    ) -> Dict[str, Tuple[float, float]]:
        """Compute circular layout."""
        if not nodes:
            return {}

        n = len(nodes)
        angle_step = 2 * np.pi / n

        pos = {}
        for i, node in enumerate(nodes):
            angle = i * angle_step
            x = self.radius * np.cos(angle)
            y = self.radius * np.sin(angle)
            pos[node] = (float(x), float(y))

        return pos
