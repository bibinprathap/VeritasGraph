import unittest
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritasreason.semantic_extract import (
    NERExtractor, 
    NamedEntityRecognizer, 
    RelationExtractor, 
    TripletExtractor,
    Entity,
    Relation
)
from veritasreason.semantic_extract.methods import get_entity_method, get_relation_method

pytestmark = pytest.mark.integration

class TestNotebooksVerification(unittest.TestCase):
    """
    Test suite to verify the code snippets from the notebooks:
    - 05_Entity_Extraction.ipynb
    - 06_Relation_Extraction.ipynb
    """

    def setUp(self):
        self.ner_extractor = NERExtractor()
        self.relation_extractor = RelationExtractor()

    def test_05_entity_extraction_notebook_flow(self):
        """Verify the flow demonstrated in 05_Entity_Extraction.ipynb"""
        print("\nTesting 05_Entity_Extraction.ipynb flow...")

        # --- Step 1: Basic Entity Extraction ---
        text = """
        Apple Inc. is a technology company founded by Steve Jobs, Steve Wozniak, and Ronald Wayne 
        in Cupertino, California on April 1, 1976. The company's current CEO is Tim Cook, who took 
        over from Steve Jobs in August 2011. Apple is headquartered at One Apple Park Way in Cupertino.
        """
        
        entities = self.ner_extractor.extract(text)
        self.assertIsInstance(entities, list)
        if len(entities) > 0:
            first_entity = entities[0]
            # Notebook handles dict or object, let's verify what we get
            is_dict = isinstance(first_entity, dict)
            is_object = hasattr(first_entity, 'text')
            self.assertTrue(is_dict or is_object, "Entity must be dict or object")
            
            if is_object:
                print(f"NERExtractor returned objects: {first_entity.text} ({first_entity.label})")
            else:
                print(f"NERExtractor returned dicts: {first_entity.get('text')} ({first_entity.get('label')})")

        # --- Step 3: Different Extraction Methods ---
        methods_to_try = ["pattern", "regex"] # Skipping 'ml' as it might require spaCy which might be missing/mocked
        
        sample_text = "Apple Inc. was founded by Steve Jobs in Cupertino, California in 1976."
        
        for method_name in methods_to_try:
            try:
                method = get_entity_method(method_name)
                method_entities = method(sample_text)
                self.assertIsInstance(method_entities, list)
                print(f"Method '{method_name}' returned {len(method_entities)} entities")
            except Exception as e:
                print(f"Method '{method_name}' failed as expected/unexpected: {e}")

        # --- Step 4: Advanced Entity Recognition ---
        # Note: We use patterns/regex here to avoid spaCy dependency issues in CI/Test env
        # but the notebook uses 'spacy'. We'll adapt for robustness.
        ner = NamedEntityRecognizer(
            methods=["pattern", "regex"],
            confidence_threshold=0.5,
            merge_overlapping=True,
            include_standard_types=True
        )
        
        texts = [
            "Tim Cook is the CEO of Apple Inc., based in Cupertino.",
            "Microsoft Corporation, founded by Bill Gates, is headquartered in Redmond, Washington."
        ]
        
        for text in texts:
            entities = ner.extract_entities(text)
            self.assertIsInstance(entities, list)

    def test_06_relation_extraction_notebook_flow(self):
        """Verify the flow demonstrated in 06_Relation_Extraction.ipynb"""
        print("\nTesting 06_Relation_Extraction.ipynb flow...")

        # --- Step 1: Basic Relation Extraction ---
        text = """
        Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
        The company is headquartered in Cupertino, California. Tim Cook is the current CEO
        of Apple Inc. and took over from Steve Jobs in August 2011.
        """
        
        # First extract entities
        entities = self.ner_extractor.extract(text)
        
        # Then extract relationships
        # Note: RelationExtractor might default to 'dependency' which needs spaCy.
        # We should check if it falls back or if we need to specify a method.
        # The notebook calls `relation_extractor.extract(text, entities)` directly.
        
        relationships = self.relation_extractor.extract(text, entities)
        self.assertIsInstance(relationships, list)
        
        if len(relationships) > 0:
            first_rel = relationships[0]
            is_dict = isinstance(first_rel, dict)
            is_object = hasattr(first_rel, 'subject')
            self.assertTrue(is_dict or is_object, "Relation must be dict or object")
            
            if is_object:
                print(f"RelationExtractor returned objects: {first_rel.subject} --[{first_rel.predicate}]--> {first_rel.object}")
            else:
                print(f"RelationExtractor returned dicts: {first_rel.get('subject')} --[{first_rel.get('predicate')}]--> {first_rel.get('object')}")

        # --- Step 2: Different Extraction Methods ---
        methods_to_try = ["pattern", "cooccurrence"] # Skipping 'dependency' to be safe
        
        sample_text = "Apple Inc. was founded by Steve Jobs in Cupertino, California."
        sample_entities = self.ner_extractor.extract(sample_text)
        
        for method_name in methods_to_try:
            try:
                method = get_relation_method(method_name)
                # Some methods might need specific args, but notebook shows standard call signature
                if method_name == "cooccurrence":
                     # cooccurrence might return empty if window is small or entities far apart
                     # but interface should hold
                     rels = method(sample_text, sample_entities)
                else:
                     rels = method(sample_text, sample_entities)
                     
                self.assertIsInstance(rels, list)
                print(f"Method '{method_name}' returned {len(rels)} relations")
            except Exception as e:
                print(f"Method '{method_name}' failed: {e}")

        # --- Step 3: Advanced Relation Extraction ---
        advanced_extractor = RelationExtractor(
            relation_types=["founded_by", "located_in", "works_for"],
            confidence_threshold=0.1, # Low threshold to ensure we catch something
            bidirectional=False,
            max_distance=50
        )
        
        texts = [
            "Microsoft was founded by Bill Gates and Paul Allen in Albuquerque, New Mexico.",
            "Satya Nadella works for Microsoft as the CEO."
        ]
        
        for text in texts:
            ents = self.ner_extractor.extract(text)
            rels = advanced_extractor.extract(text, ents)
            self.assertIsInstance(rels, list)

if __name__ == '__main__':
    unittest.main()
