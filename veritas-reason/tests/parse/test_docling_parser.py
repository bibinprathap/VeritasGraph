import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from veritasreason.parse.docling_parser import DoclingParser, DoclingMetadata

class TestDoclingParser(unittest.TestCase):
    def setUp(self):
        # Patch DOCLING_AVAILABLE to True for testing logic
        self.available_patcher = patch('veritasreason.parse.docling_parser.DOCLING_AVAILABLE', True)
        self.available_patcher.start()
        
        # Mock the DocumentConverter
        self.mock_converter_cls = patch('veritasreason.parse.docling_parser.DocumentConverter').start()
        self.mock_converter = self.mock_converter_cls.return_value
        
        self.parser = DoclingParser()

    def tearDown(self):
        patch.stopall()

    def test_parse_returns_dict(self):
        # Mock the result of converter.convert
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Test Content"
        mock_result.document.tables = []
        mock_result.document.pages = []
        
        # Mock metadata
        mock_result.input.file.name = "test.pdf"
        mock_result.document.name = "test.pdf"
        
        self.mock_converter.convert.return_value = mock_result
        
        # Create a dummy file for Path.exists()
        with patch.object(Path, 'exists', return_value=True):
            result = self.parser.parse("test.pdf")
            
            # Verify result is a dict and has expected keys
            self.assertIsInstance(result, dict)
            self.assertIn("full_text", result)
            self.assertIn("tables", result)
            self.assertIn("metadata", result)
            self.assertIn("total_pages", result)
            
            # Verify we are using dict access for tables (as per our doc fix)
            self.assertIsInstance(result["tables"], list)
            self.assertEqual(result["full_text"], "# Test Content")

    def test_extract_text_uses_dict_access(self):
        # Mock parse to return a dict
        mock_parse_result = {
            "full_text": "Extracted Text",
            "tables": [],
            "metadata": {},
            "total_pages": 1
        }
        
        with patch.object(DoclingParser, 'parse', return_value=mock_parse_result):
            text = self.parser.extract_text("test.pdf")
            self.assertEqual(text, "Extracted Text")

    def test_extract_tables_uses_dict_access(self):
        # Mock parse to return a dict
        mock_tables = [{"headers": ["Col1"], "rows": [["Val1"]]}]
        mock_parse_result = {
            "full_text": "Text",
            "tables": mock_tables,
            "metadata": {},
            "total_pages": 1
        }
        
        with patch.object(DoclingParser, 'parse', return_value=mock_parse_result):
            tables = self.parser.extract_tables("test.pdf")
            self.assertEqual(tables, mock_tables)
            self.assertEqual(tables[0]["headers"], ["Col1"])

if __name__ == '__main__':
    unittest.main()
