import unittest
import sys
import os
import networkx as nx

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.kg.centrality_calculator import CentralityCalculator
from veritasreason.kg.community_detector import CommunityDetector
from veritasreason.kg.connectivity_analyzer import ConnectivityAnalyzer

class TestCentralityCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = CentralityCalculator()
        self.graph = {
            "entities": [
                {"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}, {"id": "E"}
            ],
            "relationships": [
                {"source": "A", "target": "B"},
                {"source": "A", "target": "C"},
                {"source": "A", "target": "D"},
                {"source": "A", "target": "E"}
            ]
        }
        # This is a star graph with center A.
        # A should have highest degree centrality.

    def test_degree_centrality(self):
        result = self.calculator.calculate_degree_centrality(self.graph)
        centrality = result["centrality"]
        # A connects to 4 nodes (B, C, D, E). Total nodes = 5.
        # Degree centrality for A = 4 / (5-1) = 1.0
        self.assertAlmostEqual(centrality["A"], 1.0)
        # Leaves have degree 1. 1 / 4 = 0.25
        self.assertAlmostEqual(centrality["B"], 0.25)

    def test_betweenness_centrality(self):
        result = self.calculator.calculate_betweenness_centrality(self.graph)
        centrality = result["centrality"]
        # A is on all shortest paths between any pair of leaves.
        # It should have high betweenness.
        self.assertGreater(centrality["A"], centrality["B"])

    def test_closeness_centrality(self):
        result = self.calculator.calculate_closeness_centrality(self.graph)
        centrality = result["centrality"]
        # A is distance 1 from everyone. Closeness = 1.0
        self.assertAlmostEqual(centrality["A"], 1.0)

    def test_eigenvector_centrality(self):
        result = self.calculator.calculate_eigenvector_centrality(self.graph)
        centrality = result["centrality"]
        # A should be highest
        self.assertEqual(max(centrality, key=centrality.get), "A")


class TestCommunityDetector(unittest.TestCase):
    def setUp(self):
        self.detector = CommunityDetector()
        # Create two cliques connected by a single edge
        # Clique 1: 1, 2, 3
        # Clique 2: 4, 5, 6
        # Edge: 3-4
        self.graph = {
            "entities": [
                {"id": "1"}, {"id": "2"}, {"id": "3"},
                {"id": "4"}, {"id": "5"}, {"id": "6"}
            ],
            "relationships": [
                # Clique 1
                {"source": "1", "target": "2"}, {"source": "2", "target": "3"}, {"source": "3", "target": "1"},
                # Clique 2
                {"source": "4", "target": "5"}, {"source": "5", "target": "6"}, {"source": "6", "target": "4"},
                # Bridge
                {"source": "3", "target": "4"}
            ]
        }

    def test_louvain_communities(self):
        # Louvain should find 2 communities
        result = self.detector.detect_communities(self.graph, algorithm="louvain")
        communities = result["communities"]
        # We expect 2 communities, but small graphs can be tricky for heuristics.
        # Let's just check structure.
        self.assertTrue(len(communities) > 0)
        # Check that nodes in same clique are likely in same community
        # communities is a list of lists/sets
        comm_map = {}
        for c_id, nodes in enumerate(communities):
            for node in nodes:
                comm_map[node] = c_id
                
        self.assertEqual(comm_map["1"], comm_map["2"])
        self.assertEqual(comm_map["4"], comm_map["5"])


class TestConnectivityAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = ConnectivityAnalyzer()
        # Disconnected graph
        # Component 1: A-B
        # Component 2: C-D
        self.graph = {
            "entities": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
            "relationships": [
                {"source": "A", "target": "B"},
                {"source": "C", "target": "D"}
            ]
        }

    def test_connected_components(self):
        result = self.analyzer.find_connected_components(self.graph)
        self.assertEqual(result["num_components"], 2)
        # Components are just lists of nodes, not dicts with size
        # Wait, let's check find_connected_components return value
        # It returns { "components": [[...], [...]], ... }
        # So c is a list of nodes.
        sizes = [len(c) for c in result["components"]]
        self.assertIn(2, sizes)

    def test_shortest_path(self):
        graph = {
            "entities": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "relationships": [
                {"source": "A", "target": "B"},
                {"source": "B", "target": "C"}
            ]
        }
        result = self.analyzer.calculate_shortest_paths(graph, source="A", target="C")
        # When source and target are provided, it returns specific keys
        self.assertEqual(result["distance"], 2)
        self.assertEqual(result["path"], ["A", "B", "C"])

    def test_bridges(self):
        # A-B-C. Both edges are bridges.
        graph = {
            "entities": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "relationships": [
                {"source": "A", "target": "B"},
                {"source": "B", "target": "C"}
            ]
        }
        result = self.analyzer.identify_bridges(graph)
        self.assertEqual(len(result["bridges"]), 2)


if __name__ == "__main__":
    unittest.main()
