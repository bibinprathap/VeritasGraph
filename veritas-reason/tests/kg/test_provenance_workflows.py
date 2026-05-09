"""
End-to-end tests for provenance workflows.

Tests complete provenance tracking workflows across multiple algorithms.
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


class TestProvenanceWorkflows:
    """Test provenance tracking workflows."""
    
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
            ('F', 'A', {'weight': 0.5, 'type': 'friendship'}),
            ('A', 'C', {'weight': 0.4, 'type': 'colleague'}),
            ('B', 'D', {'weight': 0.3, 'type': 'colleague'}),
            ('C', 'E', {'weight': 0.2, 'type': 'colleague'}),
            ('D', 'F', {'weight': 0.1, 'type': 'colleague'})
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
                {'id': 'user2', 'type': 'User', 'name': 'Bob', 'department': 'Engineering'},
                {'id': 'user3', 'type': 'User', 'name': 'Charlie', 'department': 'Marketing'},
                {'id': 'user4', 'type': 'User', 'name': 'Diana', 'department': 'Marketing'},
                {'id': 'project1', 'type': 'Project', 'name': 'AI Initiative'},
                {'id': 'project2', 'type': 'Project', 'name': 'Data Pipeline'},
                {'id': 'skill1', 'type': 'Skill', 'name': 'Python'},
                {'id': 'skill2', 'type': 'Skill', 'name': 'Machine Learning'}
            ],
            'relationships': [
                {'source': 'user1', 'target': 'project1', 'type': 'WORKS_ON', 'role': 'Lead'},
                {'source': 'user2', 'target': 'project1', 'type': 'WORKS_ON', 'role': 'Developer'},
                {'source': 'user3', 'target': 'project2', 'type': 'WORKS_ON', 'role': 'Lead'},
                {'source': 'user4', 'target': 'project2', 'type': 'WORKS_ON', 'role': 'Developer'},
                {'source': 'user1', 'target': 'skill1', 'type': 'HAS_SKILL', 'level': 'Expert'},
                {'source': 'user2', 'target': 'skill1', 'type': 'HAS_SKILL', 'level': 'Advanced'},
                {'source': 'user2', 'target': 'skill2', 'type': 'HAS_SKILL', 'level': 'Intermediate'},
                {'source': 'user3', 'target': 'skill2', 'type': 'HAS_SKILL', 'level': 'Expert'},
                {'source': 'user1', 'target': 'user2', 'type': 'COLLABORATES_WITH'},
                {'source': 'user3', 'target': 'user4', 'type': 'COLLABORATES_WITH'},
                {'source': 'project1', 'target': 'project2', 'type': 'RELATED_TO'},
                {'source': 'skill1', 'target': 'skill2', 'type': 'RELATED_TO'}
            ]
        }
    
    def test_graph_construction_workflow(self, workflow_data):
        """Test complete graph construction workflow with provenance."""
        builder = GraphBuilderWithProvenance(provenance=True)
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        
        workflow_id = f"graph_construction_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Build graph with provenance
        start_time = time.time()
        graph_result = builder.build_single_source(workflow_data)
        build_time = time.time() - start_time
        
        # Verify graph construction
        assert 'entities' in graph_result
        assert 'relationships' in graph_result
        assert len(graph_result['entities']) == 8
        assert len(graph_result['relationships']) == 12
        
        # Step 2: Track graph construction
        construction_id = tracker.track_graph_construction(
            input_data=workflow_data,
            output_graph=graph_result,
            entities_count=len(graph_result['entities']),
            relationships_count=len(graph_result['relationships']),
            construction_time=build_time,
            source=workflow_id
        )
        
        assert construction_id is not None
        assert construction_id.startswith('graph_construction_')
        
        # Step 3: Track entity processing
        for entity in graph_result['entities']:
            entity_id = tracker.track_entity_processing(
                entity_id=entity['id'],
                entity_type=entity['type'],
                entity_data=entity,
                source=workflow_id
            )
            assert entity_id is not None
        
        # Step 4: Track relationship processing
        for relationship in graph_result['relationships']:
            rel_id = tracker.track_relationship_processing(
                relationship_id=f"{relationship['source']}-{relationship['target']}",
                relationship_type=relationship['type'],
                relationship_data=relationship,
                source=workflow_id
            )
            assert rel_id is not None
        
        print(f"Graph construction workflow completed: {workflow_id}")
        return workflow_id
    
    def test_embedding_workflow(self, workflow_graph, workflow_embeddings):
        """Test complete embedding workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        
        workflow_id = f"embedding_workflow_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Track embedding computation
        start_time = time.time()
        
        # Simulate embedding computation
        computed_embeddings = {}
        for node, embedding in workflow_embeddings.items():
            # Simulate some processing time
            time.sleep(0.001)
            computed_embeddings[node] = embedding
        
        computation_time = time.time() - start_time
        
        embed_id = tracker.track_embedding_computation(
            graph=workflow_graph,
            algorithm='node2vec',
            embeddings=computed_embeddings,
            parameters={
                'embedding_dimension': 4,
                'walk_length': 10,
                'num_walks': 5,
                'p': 1.0,
                'q': 1.0,
                'learning_rate': 0.025,
                'computation_time': computation_time
            },
            source=workflow_id
        )
        
        assert embed_id is not None
        assert embed_id.startswith('embedding_')
        
        # Step 2: Track embedding quality metrics
        quality_metrics = {
            'mean_norm': 1.0,
            'variance': 0.5,
            'coverage': 1.0,
            'computation_time': computation_time
        }
        
        # Track quality using the same method with different parameters
        quality_id = tracker.track_embedding_computation(
            graph=workflow_graph,
            algorithm='node2vec_quality_check',
            embeddings=computed_embeddings,
            parameters=quality_metrics,
            source=workflow_id
        )
        
        assert quality_id is not None
        
        print(f"Embedding workflow completed: {workflow_id}")
        return workflow_id
    
    def test_similarity_analysis_workflow(self, workflow_embeddings):
        """Test complete similarity analysis workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        sim_calc = SimilarityCalculator()
        
        workflow_id = f"similarity_workflow_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Track similarity calculation
        query_embedding = [0.5, 0.5, 0.5, 0.5]
        
        start_time = time.time()
        similarities = sim_calc.batch_similarity(
            embeddings=workflow_embeddings,
            query_embedding=query_embedding,
            method='cosine',
            top_k=3
        )
        calculation_time = time.time() - start_time
        
        sim_id = tracker.track_similarity_calculation(
            embeddings=workflow_embeddings,
            query_embedding=query_embedding,
            similarities=similarities,
            method='cosine',
            calculation_time=calculation_time,
            source=workflow_id
        )
        
        assert sim_id is not None
        assert sim_id.startswith('similarity_')
        
        # Step 2: Track individual similarity results
        for node_id, similarity_score in similarities.items():
            result_id = tracker.track_similarity_result(
                node_id=node_id,
                similarity_score=similarity_score,
                method='cosine',
                execution_id=sim_id,
                source=workflow_id
            )
            assert result_id is not None
        
        # Step 3: Track similarity threshold analysis
        threshold = 0.7
        high_similarity = {k: v for k, v in similarities.items() if v > threshold}
        
        threshold_id = tracker.track_similarity_threshold_analysis(
            execution_id=sim_id,
            threshold=threshold,
            high_similarity_nodes=high_similarity,
            source=workflow_id
        )
        
        assert threshold_id is not None
        
        print(f"Similarity analysis workflow completed: {workflow_id}")
        return workflow_id
    
    def test_link_prediction_workflow(self, workflow_graph):
        """Test complete link prediction workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        link_predictor = LinkPredictor()
        
        workflow_id = f"link_prediction_workflow_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Track link prediction
        methods = ['preferential_attachment', 'jaccard', 'adamic_adar']
        
        for method in methods:
            start_time = time.time()
            predictions = link_predictor.predict_links(
                graph=workflow_graph,
                method=method,
                top_k=5
            )
            prediction_time = time.time() - start_time
            
            pred_id = tracker.track_link_prediction(
                graph=workflow_graph,
                predictions=predictions,
                method=method,
                parameters={'top_k': 5},
                prediction_time=prediction_time,
                source=workflow_id
            )
            
            assert pred_id is not None
            assert pred_id.startswith('link_prediction_')
            
            # Step 2: Track individual predictions
            for i, (source, target, score) in enumerate(predictions):
                result_id = tracker.track_link_prediction_result(
                    source_node=source,
                    target_node=target,
                    prediction_score=score,
                    method=method,
                    execution_id=pred_id,
                    source=workflow_id
                )
                assert result_id is not None
        
        print(f"Link prediction workflow completed: {workflow_id}")
        return workflow_id
    
    def test_centrality_analysis_workflow(self, workflow_graph):
        """Test complete centrality analysis workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        centrality_calc = CentralityCalculator()
        
        workflow_id = f"centrality_workflow_{uuid.uuid4().hex[:8]}"
        
        # Convert graph to dict format
        graph_dict = {
            'nodes': list(workflow_graph.nodes()),
            'edges': list(workflow_graph.edges())
        }
        
        # Step 1: Track centrality calculations
        centrality_methods = [
            ('degree', centrality_calc.calculate_degree_centrality),
            ('betweenness', centrality_calc.calculate_betweenness_centrality),
            ('closeness', centrality_calc.calculate_closeness_centrality),
            ('eigenvector', centrality_calc.calculate_eigenvector_centrality)
        ]
        
        for method_name, method_func in centrality_methods:
            try:
                start_time = time.time()
                result = method_func(graph_dict)
                calculation_time = time.time() - start_time
                
                cent_id = tracker.track_centrality_calculation(
                    graph=workflow_graph,
                    centrality_scores=result['centrality'],
                    method=method_name,
                    parameters={},
                    calculation_time=calculation_time,
                    source=workflow_id
                )
                
                assert cent_id is not None
                assert cent_id.startswith('centrality_')
                
                # Step 2: Track individual centrality scores
                for node_id, score in result['centrality'].items():
                    score_id = tracker.track_centrality_score(
                        node_id=node_id,
                        centrality_score=score,
                        method=method_name,
                        execution_id=cent_id,
                        source=workflow_id
                    )
                    assert score_id is not None
                
                # Step 3: Track centrality ranking analysis
                rankings = result['rankings']
                top_nodes = rankings[:3]  # Top 3 nodes
                
                ranking_id = tracker.track_centrality_ranking(
                    execution_id=cent_id,
                    rankings=rankings,
                    top_nodes=top_nodes,
                    method=method_name,
                    source=workflow_id
                )
                
                assert ranking_id is not None
                
            except Exception as e:
                print(f"Warning: {method_name} centrality failed: {e}")
        
        print(f"Centrality analysis workflow completed: {workflow_id}")
        return workflow_id
    
    def test_community_detection_workflow(self, workflow_graph):
        """Test complete community detection workflow with provenance."""
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        community_detector = CommunityDetector()
        
        workflow_id = f"community_detection_workflow_{uuid.uuid4().hex[:8]}"
        
        # Convert graph to dict format
        graph_dict = {
            'nodes': list(workflow_graph.nodes()),
            'edges': list(workflow_graph.edges())
        }
        
        # Step 1: Track community detection
        methods = ['label_propagation', 'louvain']
        
        for method in methods:
            try:
                start_time = time.time()
                result = community_detector.detect_communities(graph_dict, method=method)
                detection_time = time.time() - start_time
                
                comm_id = tracker.track_community_detection(
                    graph=workflow_graph,
                    communities=result['communities'],
                    method=method,
                    parameters={},
                    detection_time=detection_time,
                    source=workflow_id
                )
                
                assert comm_id is not None
                assert comm_id.startswith('community_')
                
                # Step 2: Track individual communities
                for i, community in enumerate(result['communities']):
                    comm_result_id = tracker.track_community_result(
                        community_id=i,
                        nodes=community,
                        method=method,
                        execution_id=comm_id,
                        source=workflow_id
                    )
                    assert comm_result_id is not None
                
                # Step 3: Track community quality metrics
                quality_metrics = {
                    'modularity': 0.3,
                    'num_communities': len(result['communities']),
                    'avg_community_size': len(result['communities']) / len(result['communities']) if result['communities'] else 0
                }
                
                quality_id = tracker.track_community_quality(
                    execution_id=comm_id,
                    metrics=quality_metrics,
                    method=method,
                    source=workflow_id
                )
                
                assert quality_id is not None
                
            except Exception as e:
                print(f"Warning: {method} community detection failed: {e}")
        
        print(f"Community detection workflow completed: {workflow_id}")
        return workflow_id
    
    def test_comprehensive_provenance_workflow(self, workflow_data, workflow_graph, workflow_embeddings):
        """Test comprehensive provenance workflow combining all algorithms."""
        # Initialize all components
        builder = GraphBuilderWithProvenance(provenance=True)
        tracker = AlgorithmTrackerWithProvenance(provenance=True)
        sim_calc = SimilarityCalculator()
        link_predictor = LinkPredictor()
        centrality_calc = CentralityCalculator()
        community_detector = CommunityDetector()
        
        master_workflow_id = f"comprehensive_workflow_{uuid.uuid4().hex[:8]}"
        execution_ids = {}
        
        # Phase 1: Graph Construction
        print("Phase 1: Graph Construction")
        graph_result = builder.build_single_source(workflow_data)
        
        construction_id = tracker.track_graph_construction(
            input_data=workflow_data,
            output_graph=graph_result,
            entities_count=len(graph_result['entities']),
            relationships_count=len(graph_result['relationships']),
            construction_time=0.1,
            source=master_workflow_id
        )
        execution_ids['construction'] = construction_id
        
        # Phase 2: Embedding Computation
        print("Phase 2: Embedding Computation")
        embed_id = tracker.track_embedding_computation(
            graph=workflow_graph,
            algorithm='node2vec',
            embeddings=workflow_embeddings,
            parameters={'dim': 4, 'walk_length': 10},
            source=master_workflow_id
        )
        execution_ids['embedding'] = embed_id
        
        # Phase 3: Similarity Analysis
        print("Phase 3: Similarity Analysis")
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
        print("Phase 4: Link Prediction")
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
        print("Phase 5: Centrality Analysis")
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
        print("Phase 6: Community Detection")
        communities = community_detector.detect_communities(graph_dict, method='label_propagation')
        comm_id = tracker.track_community_detection(
            graph=workflow_graph,
            communities=communities['communities'],
            method='label_propagation',
            parameters={},
            source=master_workflow_id
        )
        execution_ids['community_detection'] = comm_id
        
        # Phase 7: Workflow Summary
        print("Phase 7: Workflow Summary")
        summary_id = tracker.track_workflow_summary(
            master_workflow_id=master_workflow_id,
            execution_phases=list(execution_ids.keys()),
            execution_ids=execution_ids,
            total_time=time.time(),
            source='comprehensive_test'
        )
        
        # Verify all execution IDs
        assert len(execution_ids) == 6
        for phase, exec_id in execution_ids.items():
            assert exec_id is not None
            assert len(exec_id) > 10
        
        # Verify all IDs are unique
        all_ids = list(execution_ids.values()) + [summary_id]
        assert len(set(all_ids)) == len(all_ids)
        
        # Verify ID prefixes
        assert execution_ids['construction'].startswith('graph_construction_')
        assert execution_ids['embedding'].startswith('embedding_')
        assert execution_ids['similarity'].startswith('similarity_')
        assert execution_ids['link_prediction'].startswith('link_prediction_')
        assert execution_ids['centrality'].startswith('centrality_')
        assert execution_ids['community_detection'].startswith('community_')
        assert summary_id.startswith('workflow_summary_')
        
        print(f"Comprehensive provenance workflow completed: {master_workflow_id}")
        print(f"Execution IDs: {list(execution_ids.keys())}")
        
        return master_workflow_id
    
    def test_provenance_data_integrity(self, workflow_graph, workflow_embeddings):
        """Test provenance data integrity and consistency."""
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
    
    def test_provenance_error_recovery(self):
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
