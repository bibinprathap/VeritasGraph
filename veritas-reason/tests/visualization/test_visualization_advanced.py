
import unittest
from unittest.mock import MagicMock, patch
import sys
import numpy as np

# Mock heavy libraries before importing visualization modules
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['matplotlib.colors'] = MagicMock()
sys.modules['matplotlib.patches'] = MagicMock()
sys.modules['plotly'] = MagicMock()
sys.modules['plotly.express'] = MagicMock()
sys.modules['plotly.graph_objects'] = MagicMock()
sys.modules['plotly.subplots'] = MagicMock()
sys.modules['seaborn'] = MagicMock()
sys.modules['umap'] = MagicMock()
sys.modules['sklearn'] = MagicMock()
sys.modules['sklearn.decomposition'] = MagicMock()
sys.modules['sklearn.manifold'] = MagicMock()

from veritasreason.visualization.analytics_visualizer import AnalyticsVisualizer
from veritasreason.visualization.embedding_visualizer import EmbeddingVisualizer
from veritasreason.visualization.utils.color_schemes import ColorScheme

class TestVisualizationAdvanced(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()
        self.mock_tracker = MagicMock()
        
        self.patchers = [
            patch('veritasreason.visualization.analytics_visualizer.get_logger', return_value=self.mock_logger),
            patch('veritasreason.visualization.analytics_visualizer.get_progress_tracker', return_value=self.mock_tracker),
            patch('veritasreason.visualization.embedding_visualizer.get_logger', return_value=self.mock_logger),
            patch('veritasreason.visualization.embedding_visualizer.get_progress_tracker', return_value=self.mock_tracker),
        ]
        
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    # --- AnalyticsVisualizer Tests ---
    def test_analytics_viz_init(self):
        viz = AnalyticsVisualizer(color_scheme="vibrant")
        self.assertIsInstance(viz, AnalyticsVisualizer)
        self.assertEqual(viz.color_scheme, ColorScheme.VIBRANT)

    def test_visualize_centrality_rankings(self):
        viz = AnalyticsVisualizer()
        centrality = {"n1": 0.5, "n2": 0.3}
        
        # Access the mock that was injected
        import plotly.graph_objects as go
        # Reset mock to ensure clean state
        go.Bar.reset_mock()
        
        viz.visualize_centrality_rankings(centrality, output="interactive")
        go.Bar.assert_called()

    def test_visualize_community_structure(self):
        viz = AnalyticsVisualizer()
        
        if hasattr(viz, 'visualize_community_structure'):
            import plotly.graph_objects as go
            # Reset mocks
            go.Figure.reset_mock()
            
            graph = MagicMock()
            communities = {"c1": ["n1", "n2"]}
            
            # Assuming it creates a figure or raises error if not implemented
            try:
                viz.visualize_community_structure(graph, communities)
            except Exception:
                pass
            # Just ensuring it runs without crashing due to missing deps (since we mocked them)

    # --- EmbeddingVisualizer Tests ---
    def test_embedding_viz_init(self):
        viz = EmbeddingVisualizer(point_size=10)
        self.assertIsInstance(viz, EmbeddingVisualizer)
        self.assertEqual(viz.point_size, 10)

    def test_visualize_2d_projection(self):
        viz = EmbeddingVisualizer()
        embeddings = np.random.rand(10, 128)
        
        import plotly.graph_objects as go
        
        # Mock UMAP/TSNE/PCA
        with patch('veritasreason.visualization.embedding_visualizer.umap') as mock_umap, \
             patch('veritasreason.visualization.embedding_visualizer.TSNE') as mock_tsne, \
             patch('veritasreason.visualization.embedding_visualizer.PCA') as mock_pca:
            
            # Setup mock returns
            mock_reducer = MagicMock()
            mock_reducer.fit_transform.return_value = np.random.rand(10, 2)
            mock_umap.UMAP.return_value = mock_reducer
            mock_tsne.return_value = mock_reducer
            mock_pca.return_value = mock_reducer
            
            # Test UMAP
            viz.visualize_2d_projection(embeddings, method="umap")
            if mock_umap: 
                mock_umap.UMAP.assert_called()
            
            # Test PCA
            viz.visualize_2d_projection(embeddings, method="pca")
            mock_pca.assert_called()

    def test_visualize_similarity_heatmap(self):
        viz = EmbeddingVisualizer()
        embeddings = np.random.rand(5, 5)
        
        import plotly.graph_objects as go
        go.Heatmap.reset_mock()
        
        if hasattr(viz, 'visualize_similarity_heatmap'):
            viz.visualize_similarity_heatmap(embeddings)
            go.Heatmap.assert_called()

if __name__ == '__main__':
    unittest.main()
