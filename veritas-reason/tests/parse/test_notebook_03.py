import unittest
import os
import tempfile
import json

import pytest

from veritasreason.parse import DocumentParser, CSVParser, JSONParser, XMLParser, HTMLParser, StructuredDataParser

pytestmark = pytest.mark.integration

class TestNotebook03(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        # Cleanup temp files
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)

    def test_step_1_document_parser(self):
        """Step 1: Document Parser"""
        document_parser = DocumentParser()
        sample_txt = os.path.join(self.temp_dir, "sample.txt")
        
        with open(sample_txt, 'w') as f:
            f.write("Apple Inc. is a technology company. Tim Cook is the CEO.")
            
        text = document_parser.extract_text(sample_txt)
        metadata = document_parser.extract_metadata(sample_txt)
        
        self.assertTrue(len(text) > 0)
        # metadata might be empty for txt file, but should be a dict
        self.assertIsInstance(metadata, dict)

    def test_step_2_csv_parser(self):
        """Step 2: CSV Parser"""
        csv_parser = CSVParser()
        csv_file = os.path.join(self.temp_dir, "data.csv")
        
        with open(csv_file, 'w') as f:
            f.write("name,company,role\n")
            f.write("Tim Cook,Apple Inc.,CEO\n")
            f.write("Satya Nadella,Microsoft Corporation,CEO\n")
            
        csv_data = csv_parser.parse(csv_file)
        
        # Notebook usage: csv_data.rows, csv_data.headers
        self.assertTrue(len(csv_data.rows) > 0)
        self.assertTrue(len(csv_data.headers) > 0)

    def test_step_3_json_parser(self):
        """Step 3: JSON Parser"""
        json_parser = JSONParser()
        json_file = os.path.join(self.temp_dir, "data.json")
        
        data = {
            "companies": [
                {"name": "Apple Inc.", "ceo": "Tim Cook"},
                {"name": "Microsoft Corporation", "ceo": "Satya Nadella"}
            ]
        }
        
        with open(json_file, 'w') as f:
            json.dump(data, f)
            
        json_data = json_parser.parse(json_file)
        
        # Notebook usage: json_data.data
        self.assertEqual(len(json_data.data.get('companies', [])), 2)

    def test_step_4_xml_parser(self):
        """Step 4: XML Parser"""
        xml_parser = XMLParser()
        xml_file = os.path.join(self.temp_dir, "data.xml")
        
        xml_content = """<?xml version="1.0"?>
        <companies>
            <company name="Apple Inc." ceo="Tim Cook"/>
            <company name="Microsoft Corporation" ceo="Satya Nadella"/>
        </companies>"""
        
        with open(xml_file, 'w') as f:
            f.write(xml_content)
            
        xml_data = xml_parser.parse(xml_file)
        
        # Notebook usage: xml_data.elements (might differ based on implementation), xml_data.root
        # Notebook says: print(f"Parsed XML with {len(xml_data.elements)} elements")
        # Notebook says: print(f"Root element: {xml_data.root.tag if xml_data.root else 'None'}")
        
        # Check if xml_data has elements attribute
        if hasattr(xml_data, 'elements'):
             self.assertIsNotNone(xml_data.elements)
        
        self.assertIsNotNone(xml_data.root)
        self.assertEqual(xml_data.root.tag, "companies")

    def test_step_5_html_parser(self):
        """Step 5: HTML Parser"""
        html_parser = HTMLParser()
        html_file = os.path.join(self.temp_dir, "page.html")
        
        html_content = """<html>
        <head><title>Sample Page</title></head>
        <body>
            <h1>Technology Companies</h1>
            <p>Apple Inc. is a technology company.</p>
        </body>
        </html>"""
        
        with open(html_file, 'w') as f:
            f.write(html_content)
            
        html_data = html_parser.parse(html_file)
        
        # Notebook usage: html_data.metadata, html_data.text
        # This is expected to fail if html_data is a dict
        self.assertEqual(html_data.metadata.get('title'), "Sample Page")
        self.assertTrue("Apple Inc." in html_data.text)

    def test_step_6_structured_data_parser(self):
        """Step 6: Structured Data Parser"""
        structured_parser = StructuredDataParser()
        json_file = os.path.join(self.temp_dir, "data.json")
        csv_file = os.path.join(self.temp_dir, "data.csv")
        
        # Recreate files if needed (independent tests ideally)
        data = {
            "companies": [
                {"name": "Apple Inc.", "ceo": "Tim Cook"},
                {"name": "Microsoft Corporation", "ceo": "Satya Nadella"}
            ]
        }
        with open(json_file, 'w') as f:
            json.dump(data, f)
            
        with open(csv_file, 'w') as f:
            f.write("name,company,role\n")
            f.write("Tim Cook,Apple Inc.,CEO\n")
            f.write("Satya Nadella,Microsoft Corporation,CEO\n")

        parsed_json = structured_parser.parse_data(json_file, data_format="json")
        parsed_csv = structured_parser.parse_data(csv_file, data_format="csv")
        
        # Notebook usage: parsed_json.get('data', ...), parsed_csv.get('rows', ...)
        # Implies structured_parser returns dicts or objects that behave like dicts (or objects with get method?)
        # Wait, if parsed_json is an object (JSONData), does it have .get?
        # Standard dataclasses don't have .get.
        # But maybe StructuredDataParser returns dicts?
        # Let's check logic.
        
        # Notebook says: parsed_json.get('data', {}).get('companies', [])
        # If parsed_json is JSONData, it has .data attribute. It does NOT have .get method unless added.
        # Maybe StructuredDataParser.parse_data returns a dict?
        
        # Assuming dict access for now as per notebook
        self.assertEqual(len(parsed_json.get('data', {}).get('companies', [])), 2)
        self.assertEqual(len(parsed_csv.get('rows', [])), 2)

if __name__ == '__main__':
    unittest.main()
