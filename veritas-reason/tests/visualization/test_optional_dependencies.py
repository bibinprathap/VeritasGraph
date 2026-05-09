import unittest
from unittest.mock import MagicMock, patch
import sys
import numpy as np

# Helper to mock modules
def mock_module(name):
    m = MagicMock()
    sys.modules[name] = m
    return m

class TestOptionalDependencies(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Mock heavy/problematic dependencies globally to prevent environment crashes
        # We use a dict to save original modules if they exist, but for this test file
        # we generally want to run in a controlled "clean" environment.
        cls.modules_to_patch = [
            'sklearn', 'sklearn.decomposition', 'sklearn.manifold', 
            'scipy', 'scipy.optimize', 
            'matplotlib', 'matplotlib.pyplot', 'matplotlib.patches',
            'plotly', 'plotly.express', 'plotly.graph_objects', 'plotly.subplots',
            'networkx', 'seaborn'
        ]
        
        cls.original_modules = {}
        for mod in cls.modules_to_patch:
            if mod in sys.modules:
                cls.original_modules[mod] = sys.modules[mod]
            sys.modules[mod] = MagicMock()

    @classmethod
    def tearDownClass(cls):
        # Restore original modules
        for mod in cls.modules_to_patch:
            if mod in cls.original_modules:
                sys.modules[mod] = cls.original_modules[mod]
            else:
                del sys.modules[mod]

    def setUp(self):
        # Clear cached visualization modules to ensure fresh imports
        self.viz_modules = [
            'veritasreason.visualization.embedding_visualizer',
            'veritasreason.visualization.ontology_visualizer',
            'veritasreason.visualization.kg_visualizer',
            'veritasreason.visualization.utils.export_formats'
        ]
        for mod in self.viz_modules:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_embedding_visualizer_without_umap(self):
        """Test EmbeddingVisualizer behavior when umap is missing."""
        # Ensure umap is missing
        with patch.dict(sys.modules, {'umap': None}):
            from veritasreason.visualization.embedding_visualizer import EmbeddingVisualizer
            
            # Setup PCA mock to verify fallback
            mock_pca_class = sys.modules['sklearn.decomposition'].PCA
            mock_pca_instance = mock_pca_class.return_value
            # Configure fit_transform to return correct shape (n_samples, 2)
            mock_pca_instance.fit_transform.return_value = np.zeros((4, 2))
            
            viz = EmbeddingVisualizer()
            # Use numpy array!
            embeddings = np.array([[0, 1, 2], [1, 0, 3], [0, 0, 0], [1, 1, 1]])
            
            # Should fallback to PCA when method="umap" is used but umap is None
            # The code logs a warning and uses PCA
            viz.visualize_2d_projection(embeddings, method="umap")
            
            # Verify PCA was called
            mock_pca_class.assert_called()

    def test_ontology_visualizer_without_graphviz(self):
        """Test OntologyVisualizer behavior when graphviz is missing."""
        # Ensure graphviz is missing
        with patch.dict(sys.modules, {'graphviz': None}):
            from veritasreason.visualization.ontology_visualizer import OntologyVisualizer, ProcessingError
            
            viz = OntologyVisualizer()
            ontology = {
                "classes": [
                    {"name": "A", "label": "A"},
                    {"name": "B", "label": "B", "parent": "A"}
                ]
            }
            
            with self.assertRaises(ProcessingError) as cm:
                viz.visualize_hierarchy(ontology, output="dot", file_path="test.dot")
            
            self.assertIn("Graphviz is required for DOT export", str(cm.exception))

    def test_analytics_visualizer_without_plotly(self):
        """Test AnalyticsVisualizer behavior when plotly is missing."""
        with patch.dict(sys.modules, {'plotly': None, 'plotly.express': None, 'plotly.graph_objects': None}):
            from veritasreason.visualization.analytics_visualizer import AnalyticsVisualizer, ProcessingError
            
            # Need to ensure numpy is available for init (it's imported at top level)
            # But we are testing plotly missing.
            
            viz = AnalyticsVisualizer()
            
            with self.assertRaises(ProcessingError) as cm:
                viz.visualize_centrality_rankings({"node1": 1.0})
            
            self.assertIn("Plotly is required", str(cm.exception))

    def test_analytics_visualizer_without_plotly(self):
        """Test AnalyticsVisualizer behavior when plotly is missing."""
        with patch.dict(sys.modules, {'plotly': None, 'plotly.express': None, 'plotly.graph_objects': None}):
            from veritasreason.visualization.analytics_visualizer import AnalyticsVisualizer, ProcessingError
            
            viz = AnalyticsVisualizer()
            
            with self.assertRaises(ProcessingError) as cm:
                viz.visualize_centrality_rankings({})
            
            self.assertIn("Plotly is required", str(cm.exception))

    def test_semantic_network_visualizer_without_plotly(self):
        """Test SemanticNetworkVisualizer behavior when plotly is missing."""
        with patch.dict(sys.modules, {'plotly': None, 'plotly.express': None, 'plotly.graph_objects': None}):
            from veritasreason.visualization.semantic_network_visualizer import SemanticNetworkVisualizer, ProcessingError
            
            viz = SemanticNetworkVisualizer()
            
            with self.assertRaises(ProcessingError) as cm:
                viz.visualize_network({})
            
            self.assertIn("Plotly is required", str(cm.exception))

    def test_temporal_visualizer_without_plotly(self):
        """Test TemporalVisualizer behavior when plotly is missing."""
        with patch.dict(sys.modules, {'plotly': None, 'plotly.express': None, 'plotly.graph_objects': None}):
            from veritasreason.visualization.temporal_visualizer import TemporalVisualizer, ProcessingError
            
            viz = TemporalVisualizer()
            
            with self.assertRaises(ProcessingError) as cm:
                viz.visualize_timeline({"events": []})
            
            self.assertIn("Plotly is required", str(cm.exception))


if __name__ == '__main__':
    unittest.main()
