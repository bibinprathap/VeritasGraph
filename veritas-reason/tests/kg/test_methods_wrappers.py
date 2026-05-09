import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from veritasreason.kg import methods

class TestMethodsWrappers(unittest.TestCase):
    
    @patch("veritasreason.kg.methods.GraphBuilder")
    def test_build_kg(self, mock_builder_cls):
        mock_builder = mock_builder_cls.return_value
        mock_builder.build.return_value = {"entities": [], "relationships": []}
        
        sources = []
        result = methods.build_kg(sources)
        
        mock_builder_cls.assert_called_once()
        mock_builder.build.assert_called_once_with(sources)
        self.assertIn("entities", result)

    @patch("veritasreason.kg.methods.GraphAnalyzer")
    def test_analyze_graph(self, mock_analyzer_cls):
        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze_graph.return_value = {"metrics": {}}
        
        graph = {"entities": [], "relationships": []}
        result = methods.analyze_graph(graph)
        
        mock_analyzer_cls.assert_called_once()
        mock_analyzer.analyze_graph.assert_called_once_with(graph)

    @patch("veritasreason.kg.methods.EntityResolver")
    def test_resolve_entities(self, mock_resolver_cls):
        mock_resolver = mock_resolver_cls.return_value
        mock_resolver.resolve_entities.return_value = []
        
        entities = []
        result = methods.resolve_entities(entities)
        
        mock_resolver_cls.assert_called_once()
        mock_resolver.resolve_entities.assert_called_once_with(entities)

if __name__ == "__main__":
    unittest.main()
