import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
from veritasreason.export.methods import export_yaml

class TestExportMethodsWrapper(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.schema = {
            "uri": "http://example.org/schema",
            "classes": [{"id": "Person", "label": "Person"}],
            "properties": [{"id": "knows", "label": "Knows"}]
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_export_yaml_schema(self):
        output_path = Path(self.test_dir) / "schema.yaml"
        
        # This should call export_ontology_schema internally
        export_yaml(self.schema, str(output_path), method="schema")
        
        self.assertTrue(output_path.exists())
        with open(output_path, 'r') as f:
            data = yaml.safe_load(f)
            self.assertEqual(data['ontology']['uri'], "http://example.org/schema")
            self.assertEqual(len(data['classes']), 1)

if __name__ == '__main__':
    unittest.main()
