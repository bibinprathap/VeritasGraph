"""
Simplified provenance workflow tests.

Tests provenance tracking workflows using only available methods.
"""

import pytest
import networkx as nx
import time
from typing import Dict, List, Any
import uuid

from veritasreason.kg import (
    GraphBuilderWithProvenance,
    AlgorithmTrackerWithProvenance,
    NodeEmbedder,
    SimilarityCalculator,
    LinkPredictor,
    CentralityCalculator,
    CommunityDetector
)


class TestProvenanceWorkflowsSimple:
    """Test provenance tracking workflows with available methods."""
    
    @pytest.fixture
    def workflow_graph(self):
        """Create a graph for workflow testing."""
        graph = nx.Graph()
        graph.add_edges_from([
            ('A', 'B', {'weight': 1.0, 'type': 'friendship'}),
            ('B', 'C', {'weight': 0.8, 'type': 'friendship'}),
            ('C', 'D', {'weight': 0.9, 'type': 'friendship'}),
            ('D', 'E', {'weight': 0.7, 'type': 'friendship'}),
            ('E', 'F', {'weight': 0.6, 'type': 'friendship'}),
            ('F', 'A', {'weight': 0.5, 'type': 'friendship'})
        ])
        return graph
    
    @pytest.fixture
    def workflow_embeddings(self):
        """Create embeddings for workflow testing."""
        import numpy as np
        np.random.seed(42)
        
        nodes = ['A', 'B', 'C', 'D', 'E', 'F']
        embeddings = {}
        
        for node in nodes:
            # Generate 4-dimensional embeddings
            embedding = np.random.randn(4)
            embeddings[node] = embedding.tolist()
        
        return embeddings
    
    @pytest.fixture
    def workflow_data(self):
        """Create workflow data for graph building."""
        return {
            'entities': [
                {'id': 'user1', 'type': 'User', 'name': 'Alice', 'department': 'Engineering'},
                {'id': 'user2', 'type': 'User', 'name': 'Bob', 'department': 'Marketing'},
                {'id': 'project1', 'type': 'Project', 'name': 'AI Initiative'},
                {'id': 'skill1', 'type': 'Skill', 'name': 'Python'}
            ],
            'relationships': [
                {'source': 'user1', 'target': 'project1', 'type': 'WORKS_ON', 'role': 'Lead'},
                {'source': 'user2', 'target': 'project1', 'type': 'WORKS_ON', 'role': 'Developer'},
                {'source': 'user1', 'target': 'skill1', 'type': 'HAS_SKILL', 'level': 'Expert'}
            ]
        }
    
    def test_embedding_workflow_simple(self, workflow_graph, workflow_embeddings):
        """Test simple embedding workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        
        workflow_id = f"embedding_workflow_{uuid.uuid4().hex[:8]}"
        
        # Track embedding computation
        embed_id = tracker.track_embedding_computation(
            graph=workflow_graph,
            algorithm='node2vec',
            embeddings=workflow_embeddings,
            parameters={
                'embedding_dimension': 4,
                'walk_length': 10,
                'num_walks': 5,
                'p': 1.0,
                'q': 1.0,
                'learning_rate': 0.025
            },
            source=workflow_id
        )
        
        assert embed_id is not None
        assert embed_id.startswith('embedding_')
        
        print(f"Simple embedding workflow completed: {workflow_id}")
        return workflow_id
    
    def test_similarity_workflow_simple(self, workflow_embeddings):
        """Test simple similarity workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        sim_calc = SimilarityCalculator()
        
        workflow_id = f"similarity_workflow_{uuid.uuid4().hex[:8]}"
        
        # Calculate similarities
        query_embedding = [0.5, 0.5, 0.5, 0.5]
        similarities = sim_calc.batch_similarity(
            embeddings=workflow_embeddings,
            query_embedding=query_embedding,
            method='cosine',
            top_k=3
        )
        
        # Track similarity calculation
        sim_id = tracker.track_similarity_calculation(
            embeddings=workflow_embeddings,
            query_embedding=query_embedding,
            similarities=similarities,
            method='cosine',
            source=workflow_id
        )
        
        assert sim_id is not None
        assert sim_id.startswith('similarity_')
        
        print(f"Simple similarity workflow completed: {workflow_id}")
        return workflow_id
    
    def test_link_prediction_workflow_simple(self, workflow_graph):
        """Test simple link prediction workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        link_predictor = LinkPredictor()
        
        workflow_id = f"link_prediction_workflow_{uuid.uuid4().hex[:8]}"
        
        # Predict links
        predictions = link_predictor.predict_links(
            graph=workflow_graph,
            method='preferential_attachment',
            top_k=5
        )
        
        # Track link prediction
        link_id = tracker.track_link_prediction(
            graph=workflow_graph,
            predictions=predictions,
            method='preferential_attachment',
            parameters={'top_k': 5},
            source=workflow_id
        )
        
        assert link_id is not None
        assert link_id.startswith('link_prediction_')
        
        print(f"Simple link prediction workflow completed: {workflow_id}")
        return workflow_id
    
    def test_centrality_workflow_simple(self, workflow_graph):
        """Test simple centrality workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        centrality_calc = CentralityCalculator()
        
        workflow_id = f"centrality_workflow_{uuid.uuid4().hex[:8]}"
        
        # Convert graph to dict format
        graph_dict = {
            'nodes': list(workflow_graph.nodes()),
            'edges': list(workflow_graph.edges())
        }
        
        # Calculate centrality
        degree_cent = centrality_calc.calculate_degree_centrality(graph_dict)
        
        # Track centrality calculation
        cent_id = tracker.track_centrality_calculation(
            graph=workflow_graph,
            centrality_scores=degree_cent['centrality'],
            method='degree',
            parameters={},
            source=workflow_id
        )
        
        assert cent_id is not None
        assert cent_id.startswith('centrality_')
        
        print(f"Simple centrality workflow completed: {workflow_id}")
        return workflow_id
    
    def test_community_detection_workflow_simple(self, workflow_graph):
        """Test simple community detection workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        community_detector = CommunityDetector()
        
        workflow_id = f"community_detection_workflow_{uuid.uuid4().hex[:8]}"
        
        # Convert graph to dict format
        graph_dict = {
            'nodes': list(workflow_graph.nodes()),
            'edges': list(workflow_graph.edges())
        }
        
        # Detect communities
        communities = community_detector.detect_communities(graph_dict, method='label_propagation')
        
        # Track community detection
        comm_id = tracker.track_community_detection(
            graph=workflow_graph,
            communities=communities['communities'],
            method='label_propagation',
            parameters={},
            source=workflow_id
        )
        
        assert comm_id is not None
        assert comm_id.startswith('community_')
        
        print(f"Simple community detection workflow completed: {workflow_id}")
        return workflow_id
    
    def test_graph_construction_workflow_simple(self, workflow_data):
        """Test simple graph construction workflow with provenance."""
        builder = GraphBuilderWithProvenance(provenance=True)
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        
        workflow_id = f"graph_construction_workflow_{uuid.uuid4().hex[:8]}"
        
        # Build graph
        graph_result = builder.build_single_source(workflow_data)
        
        # Verify graph construction
        assert 'entities' in graph_result
        assert 'relationships' in graph_result
        assert len(graph_result['entities']) == 4
        assert len(graph_result['relationships']) == 3
        
        # Track graph construction using embedding computation method as proxy
        construction_id = tracker.track_embedding_computation(
            graph={'nodes': list(graph_result['entities']), 'edges': list(graph_result['relationships'])},
            algorithm='graph_construction',
            embeddings={'graph_size': len(graph_result['entities'])},
            parameters={
                'entities_count': len(graph_result['entities']),
                'relationships_count': len(graph_result['relationships'])
            },
            source=workflow_id
        )
        
        assert construction_id is not None
        assert construction_id.startswith('embedding_')  # Using embedding method as proxy
        
        print(f"Simple graph construction workflow completed: {workflow_id}")
        return workflow_id
    
    def test_comprehensive_workflow_simple(self, workflow_data, workflow_graph, workflow_embeddings):
        """Test comprehensive workflow with all available methods."""
        # Initialize components
        builder = GraphBuilderWithProvenance(provenance=True)
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        sim_calc = SimilarityCalculator()
        link_predictor = LinkPredictor()
        centrality_calc = CentralityCalculator()
        community_detector = CommunityDetector()
        
        master_workflow_id = f"comprehensive_workflow_{uuid.uuid4().hex[:8]}"
        execution_ids = {}
        
        # Phase 1: Graph Construction
        graph_result = builder.build_single_source(workflow_data)
        
        construction_id = tracker.track_embedding_computation(
            graph={'nodes': list(graph_result['entities']), 'edges': list(graph_result['relationships'])},
            algorithm='graph_construction',
            embeddings={'graph_size': len(graph_result['entities'])},
            parameters={'entities_count': len(graph_result['entities'])},
            source=master_workflow_id
        )
        execution_ids['construction'] = construction_id
        
        # Phase 2: Embedding Computation
        embed_id = tracker.track_embedding_computation(
            graph=workflow_graph,
            algorithm='node2vec',
            embeddings=workflow_embeddings,
            parameters={'dim': 4, 'walk_length': 10},
            source=master_workflow_id
        )
        execution_ids['embedding'] = embed_id
        
        # Phase 3: Similarity Analysis
        query_embedding = [0.5, 0.5, 0.5, 0.5]
        similarities = sim_calc.batch_similarity(
            embeddings=workflow_embeddings,
            query_embedding=query_embedding,
            method='cosine',
            top_k=3
        )
        
        sim_id = tracker.track_similarity_calculation(
            embeddings=workflow_embeddings,
            query_embedding=query_embedding,
            similarities=similarities,
            method='cosine',
            source=master_workflow_id
        )
        execution_ids['similarity'] = sim_id
        
        # Phase 4: Link Prediction
        predictions = link_predictor.predict_links(
            graph=workflow_graph,
            method='preferential_attachment',
            top_k=5
        )
        
        link_id = tracker.track_link_prediction(
            graph=workflow_graph,
            predictions=predictions,
            method='preferential_attachment',
            parameters={'top_k': 5},
            source=master_workflow_id
        )
        execution_ids['link_prediction'] = link_id
        
        # Phase 5: Centrality Analysis
        graph_dict = {
            'nodes': list(workflow_graph.nodes()),
            'edges': list(workflow_graph.edges())
        }
        
        degree_cent = centrality_calc.calculate_degree_centrality(graph_dict)
        cent_id = tracker.track_centrality_calculation(
            graph=workflow_graph,
            centrality_scores=degree_cent['centrality'],
            method='degree',
            parameters={},
            source=master_workflow_id
        )
        execution_ids['centrality'] = cent_id
        
        # Phase 6: Community Detection
        communities = community_detector.detect_communities(graph_dict, method='label_propagation')
        comm_id = tracker.track_community_detection(
            graph=workflow_graph,
            communities=communities['communities'],
            method='label_propagation',
            parameters={},
            source=master_workflow_id
        )
        execution_ids['community_detection'] = comm_id
        
        # Verify all execution IDs
        assert len(execution_ids) == 6
        for phase, exec_id in execution_ids.items():
            assert exec_id is not None
            assert len(exec_id) > 10
        
        # Verify all IDs are unique
        all_ids = list(execution_ids.values())
        assert len(set(all_ids)) == len(all_ids)
        
        # Verify ID prefixes
        assert execution_ids['embedding'].startswith('embedding_')
        assert execution_ids['similarity'].startswith('similarity_')
        assert execution_ids['link_prediction'].startswith('link_prediction_')
        assert execution_ids['centrality'].startswith('centrality_')
        assert execution_ids['community_detection'].startswith('community_')
        
        print(f"Comprehensive workflow completed: {master_workflow_id}")
        print(f"Execution IDs: {list(execution_ids.keys())}")
        
        return master_workflow_id
    
    def test_provenance_data_integrity_simple(self, workflow_graph, workflow_embeddings):
        """Test provenance data integrity with available methods."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        
        workflow_id = f"integrity_test_{uuid.uuid4().hex[:8]}"
        
        # Track multiple operations
        operations = []
        
        # Operation 1: Embedding computation
        embed_id = tracker.track_embedding_computation(
            graph=workflow_graph,
            algorithm='node2vec',
            embeddings=workflow_embeddings,
            parameters={'dim': 4},
            source=workflow_id
        )
        operations.append(('embedding', embed_id))
        
        # Operation 2: Similarity calculation
        sim_id = tracker.track_similarity_calculation(
            embeddings=workflow_embeddings,
            query_embedding=[0.5, 0.5, 0.5, 0.5],
            similarities={'A': 0.9, 'B': 0.8},
            method='cosine',
            source=workflow_id
        )
        operations.append(('similarity', sim_id))
        
        # Operation 3: Link prediction
        link_id = tracker.track_link_prediction(
            graph=workflow_graph,
            predictions=[('A', 'C', 0.7)],
            method='preferential_attachment',
            parameters={},
            source=workflow_id
        )
        operations.append(('link_prediction', link_id))
        
        # Verify data integrity
        for op_type, op_id in operations:
            assert op_id is not None
            assert len(op_id) > 10
            
            # Verify ID format consistency
            if op_type == 'embedding':
                assert op_id.startswith('embedding_')
            elif op_type == 'similarity':
                assert op_id.startswith('similarity_')
            elif op_type == 'link_prediction':
                assert op_id.startswith('link_prediction_')
        
        # Verify workflow consistency
        workflow_ids = [op_id for _, op_id in operations]
        assert len(set(workflow_ids)) == len(workflow_ids)  # All unique
        
        print(f"Provenance data integrity test completed: {workflow_id}")
    
    def test_provenance_error_recovery_simple(self):
        """Test provenance system error recovery."""
        # Test graceful degradation
        tracker_no_prov = AlgorithmTrackerWithProvenance(provenance=False)
        
        result = tracker_no_prov.track_embedding_computation(
            graph={'nodes': [], 'edges': []},
            algorithm='test',
            embeddings={},
            parameters={}
        )
        
        assert result is None  # Should return None when provenance is disabled
        
        # Test error handling during tracking
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        
        # This should not raise exceptions even with invalid data
        try:
            result = tracker.track_embedding_computation(
                graph=None,  # Invalid graph
                algorithm='test',
                embeddings={},
                parameters={}
            )
            # Should either return None or handle gracefully
        except Exception as e:
            # If it raises, it should be a controlled exception
            assert isinstance(e, (ValueError, TypeError))
        
        print("Provenance error recovery test completed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
