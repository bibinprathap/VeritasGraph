"""
Mock Arrow Exporter for Benchmark Testing

This module provides a mock implementation of the ArrowExporter to prevent
import errors during benchmark testing when PyArrow is not available in the CI environment.
"""

# Mock PyArrow import for CI compatibility
try:
    import pyarrow as pa
except ImportError:
    # Create a mock pa module for CI environment
    import types
    pa = types.ModuleType('pa')
    
    def mock_schema(*args, **kwargs):
        return types.SimpleNamespace()
    
    def mock_table(*args, **kwargs):
        return types.SimpleNamespace()
    
    def mock_array(*args, **kwargs):
        return types.SimpleNamespace()
    
    pa.schema = mock_schema
    pa.Table = mock_table
    pa.array = mock_array
    pa.RecordBatch = mock_table

# Mock schema definitions
ENTITY_SCHEMA = pa.schema([]) if hasattr(pa, 'schema') else None
RELATIONSHIP_SCHEMA = pa.schema([]) if hasattr(pa, 'schema') else None
METADATA_SCHEMA = pa.schema([]) if hasattr(pa, 'schema') else None

class ArrowExporter:
    """
    Mock Arrow Exporter class for benchmark testing.
    
    This is a lightweight implementation that provides the same interface
    as the real ArrowExporter but doesn't require PyArrow to be installed.
    """
    
    def __init__(self, config=None):
        self.config = config
        self._tables = {}
    
    def export_entities(self, entities, output_path):
        """Mock export entities method."""
        return f"Mock exported {len(entities)} entities to {output_path}"
    
    def export_relationships(self, relationships, output_path):
        """Mock export relationships method."""
        return f"Mock exported {len(relationships)} relationships to {output_path}"
    
    def export_knowledge_graph(self, entities, relationships, output_path):
        """Mock export knowledge graph method."""
        return f"Mock exported knowledge graph to {output_path}"
    
    def to_arrow_table(self, data):
        """Mock conversion to Arrow table."""
        return f"Mock Arrow table with {len(data)} rows"
    
    def save_to_file(self, table, path):
        """Mock save to file method."""
        return f"Mock saved table to {path}"
    
    def batch_export(self, data_list, output_dir):
        """Mock batch export method."""
        return f"Mock batch exported {len(data_list)} items to {output_dir}"
