
import unittest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch

# Import veritasreason modules
# We use try-except to handle potential missing optional dependencies in the test environment
try:
    from veritasreason.ingest import FileIngestor, WebIngestor, DBIngestor, FeedIngestor
    from veritasreason.parse import DocumentParser, PDFParser, StructuredDataParser, JSONParser
    from veritasreason.semantic_extract import NERExtractor, RelationExtractor, TripletExtractor, SemanticAnalyzer
    from veritasreason.kg import GraphBuilder, GraphAnalyzer, CentralityCalculator, CommunityDetector
    from veritasreason.kg import ConnectivityAnalyzer, TemporalGraphQuery, TemporalPatternDetector
    from veritasreason.ontology import OntologyGenerator, ClassInferrer, PropertyGenerator, OntologyValidator
    from veritasreason.reasoning import Reasoner, ExplanationGenerator
    from veritasreason.export import JSONExporter, RDFExporter, OWLExporter, ReportGenerator
    # Visualization might require matplotlib/networkx which might be missing or headless
    from veritasreason.visualization import KGVisualizer, OntologyVisualizer, AnalyticsVisualizer
except ImportError as e:
    print(f"Skipping imports due to missing dependencies: {e}")

class TestDiseaseNetworkAnalysis(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.disease_file = os.path.join(self.temp_dir, "disease_data.json")
        
        # Sample disease data from the notebook
        self.disease_data = {
            "diseases": [
                {
                    "disease_name": "Type 2 Diabetes",
                    "icd10_code": "E11",
                    "related_diseases": ["Hypertension", "Cardiovascular Disease", "Obesity"],
                    "symptoms": ["Increased thirst", "Frequent urination", "Fatigue"],
                    "treatments": ["Metformin", "Insulin", "Lifestyle changes"],
                    "prevalence": "High"
                },
                {
                    "disease_name": "Hypertension",
                    "icd10_code": "I10",
                    "related_diseases": ["Type 2 Diabetes", "Cardiovascular Disease", "Kidney Disease"],
                    "symptoms": ["High blood pressure", "Headaches", "Dizziness"],
                    "treatments": ["ACE inhibitors", "Beta blockers", "Lifestyle changes"],
                    "prevalence": "Very High"
                }
            ]
        }
        
        with open(self.disease_file, 'w') as f:
            json.dump(self.disease_data, f, indent=2)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_pipeline_execution(self):
        """
        Replicates the logic of cookbook/use_cases/healthcare/02_Disease_Network_Analysis.ipynb
        """
        # --- Step 1: Ingest ---
        file_ingestor = FileIngestor()
        json_parser = JSONParser()
        
        # We mock WebIngestor/DBIngestor to avoid external calls
        web_ingestor = MagicMock()
        web_ingestor.ingest_url.return_value = {"content": "Mock API Content"}
        
        # Ingest file
        file_objects = file_ingestor.ingest_file(self.disease_file, read_content=True)
        self.assertIsNotNone(file_objects)
        
        # Parse
        parsed_data = json_parser.parse(self.disease_file)
        self.assertIsNotNone(parsed_data)
        
        # --- Step 2: Extract ---
        # The notebook manually extracts entities/relationships from the parsed JSON
        # It instantiates extractors but doesn't use them for the main logic shown
        # We instantiate them to ensure they can be instantiated
        try:
            ner_extractor = NERExtractor(method="pattern") # Use pattern to avoid spacy model load if missing
            relation_extractor = RelationExtractor()
        except Exception as e:
            print(f"Warning: Could not instantiate extractors: {e}")
            
        disease_entities = []
        disease_relationships = []
        
        # Extraction logic copied from notebook
        if parsed_data and parsed_data.data:
            diseases = parsed_data.data.get("diseases", []) if isinstance(parsed_data.data, dict) else []
            
            for disease in diseases:
                if isinstance(disease, dict):
                    disease_name = disease.get("disease_name", "")
                    
                    disease_entities.append({
                        "id": disease_name,
                        "type": "Disease",
                        "name": disease_name,
                        "properties": {
                            "icd10_code": disease.get("icd10_code", ""),
                            "prevalence": disease.get("prevalence", "")
                        }
                    })
                    
                    # Related diseases
                    for related in disease.get("related_diseases", []):
                        disease_entities.append({
                            "id": related,
                            "type": "Disease",
                            "name": related,
                            "properties": {}
                        })
                        disease_relationships.append({
                            "source": disease_name,
                            "target": related,
                            "type": "related_to",
                            "properties": {}
                        })
                    
                    # Symptoms
                    for symptom in disease.get("symptoms", []):
                        disease_entities.append({
                            "id": symptom,
                            "type": "Symptom",
                            "name": symptom,
                            "properties": {}
                        })
                        disease_relationships.append({
                            "source": disease_name,
                            "target": symptom,
                            "type": "has_symptom",
                            "properties": {}
                        })
                        
                    # Treatments
                    for treatment in disease.get("treatments", []):
                        disease_entities.append({
                            "id": treatment,
                            "type": "Treatment",
                            "name": treatment,
                            "properties": {}
                        })
                        disease_relationships.append({
                            "source": disease_name,
                            "target": treatment,
                            "type": "treated_with",
                            "properties": {}
                        })
        
        self.assertTrue(len(disease_entities) > 0)
        self.assertTrue(len(disease_relationships) > 0)
        
        # --- Step 3: Build KG ---
        builder = GraphBuilder(merge_entities=True, entity_resolution_strategy="exact")
        ontology_generator = OntologyGenerator()
        class_inferrer = ClassInferrer()
        property_generator = PropertyGenerator()
        ontology_validator = OntologyValidator()
        
        # Combine entities and relationships into a source structure for the builder
        sources = [{"entities": disease_entities, "relationships": disease_relationships}]
        disease_kg = builder.build(sources)
        self.assertIn("entities", disease_kg)
        self.assertIn("relationships", disease_kg)
        
        disease_ontology = ontology_generator.generate_ontology({
            "entities": disease_entities,
            "relationships": disease_relationships
        })
        self.assertIn("classes", disease_ontology)
        
        # --- Step 4: Analyze ---
        graph_analyzer = GraphAnalyzer()
        centrality_calculator = CentralityCalculator()
        community_detector = CommunityDetector()
        connectivity_analyzer = ConnectivityAnalyzer()
        
        metrics = graph_analyzer.compute_metrics(disease_kg)
        self.assertIsNotNone(metrics)
        
        centrality_result = centrality_calculator.calculate_degree_centrality(disease_kg)
        self.assertIn("centrality", centrality_result)
        
        communities = community_detector.detect_communities(disease_kg)
        # communities might be a list or dict depending on implementation/algorithm
        self.assertTrue(len(communities) > 0) # Should have found some communities or at least one
        
        connectivity = connectivity_analyzer.analyze_connectivity(disease_kg)
        self.assertIn("components", connectivity)
        
        # --- Step 5: Predict Outcomes (Reasoning) ---
        # Inference logic updated to use Reasoner facade
        reasoner = Reasoner()
        reasoner.add_rule("IF related_to(?a, ?b) AND related_to(?b, ?c) THEN comorbid(?a, ?c)")
        
        # Add some facts for testing
        reasoner.add_fact("related_to(Diabetes, Hypertension)")
        reasoner.add_fact("related_to(Hypertension, Obesity)")
        
        outcome_predictions = reasoner.infer_facts([])
        self.assertIn("comorbid(Diabetes, Obesity)", outcome_predictions)
        
        # --- Step 6: Export/Report ---
        # Mocking exporters to avoid file writing issues or just testing they run
        json_exporter = JSONExporter()
        report_generator = ReportGenerator()
        
        out_file = os.path.join(self.temp_dir, "disease_kg.json")
        json_exporter.export_knowledge_graph(disease_kg, out_file)
        self.assertTrue(os.path.exists(out_file))
        
        report_data = {
            "summary": "Test Summary",
            "diseases_analyzed": 10,
            "relationships": 20,
            "predictions": len(outcome_predictions),
            "quality_score": 0.95
        }
        
        report = report_generator.generate_report(report_data, format="markdown")
        self.assertIsInstance(report, str)
        self.assertIn("Test Summary", report)

if __name__ == "__main__":
    unittest.main()
