#!/usr/bin/env python3
"""
Comprehensive test suite for Context Graphs feature examples from issue #290.
This tests all the example use cases provided in the feature description.
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch

# Add the veritasreason package to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from veritasreason.context import AgentContext
from veritasreason.context.context_graph import ContextGraph
from veritasreason.context.decision_models import Decision, Policy, PolicyException
from veritasreason.vector_store import VectorStore
from veritasreason.embeddings import EmbeddingGenerator


class TestContextGraphsExamples:
    """Test suite for Context Graphs feature examples."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store for testing."""
        store = Mock(spec=VectorStore)
        store.store = Mock(return_value="test_memory_id")
        store.retrieve = Mock(return_value=[])
        store.embed = Mock(return_value=[0.1] * 384)  # Mock embedding
        return store
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Create a mock knowledge graph for testing."""
        kg = Mock(spec=ContextGraph)
        kg.execute_query = Mock(return_value=[])
        kg.build_from_conversations = Mock(return_value={"statistics": {"node_count": 0, "edge_count": 0}})
        return kg
    
    def test_context_graph_direct_functionality(self):
        """Test ContextGraph directly with decision support features."""
        print("Testing ContextGraph Direct Functionality...")
        
        # Create context graph with advanced features
        graph = ContextGraph(
            advanced_analytics=True,
            centrality_analysis=True,
            community_detection=True,
            node_embeddings=True
        )
        
        # Add a decision
        decision = Decision(
            decision_id="test_decision_001",
            category="test",
            scenario="Test scenario for credit approval",
            reasoning="Good credit history and stable income",
            outcome="approved",
            confidence=0.95,
            timestamp=datetime.now(),
            decision_maker="ai_agent"
        )
        
        graph.add_decision(decision)
        assert len(graph.nodes) == 1
        print("+ Added decision to context graph")
        
        # Add another decision and causal relationship
        decision2 = Decision(
            decision_id="test_decision_002",
            category="test",
            scenario="Related credit decision",
            reasoning="Based on previous approval",
            outcome="approved",
            confidence=0.90,
            timestamp=datetime.now(),
            decision_maker="ai_agent"
        )
        
        graph.add_decision(decision2)
        graph.add_causal_relationship("test_decision_001", "test_decision_002", "CAUSED")
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        print("+ Added causal relationship")
        
        # Test causal chain
        chain = graph.get_causal_chain("test_decision_002", direction="upstream")
        assert len(chain) == 1
        assert chain[0].decision_id == "test_decision_001"
        print("+ Found causal chain with decisions")
        
        # Test precedent search
        precedents = graph.find_precedents("test_decision_002")
        assert len(precedents) == 0  # No precedent relationships added
        
        # Add precedent relationship and test again
        graph.add_causal_relationship("test_decision_001", "test_decision_002", "PRECEDENT_FOR")
        precedents = graph.find_precedents("test_decision_002")
        assert len(precedents) == 1
        assert precedents[0].decision_id == "test_decision_001"
        print("+ Found precedents")
        
        # Test serialization
        graph_dict = graph.to_dict()
        assert len(graph_dict['nodes']) == 2
        assert len(graph_dict['edges']) == 2
        assert 'properties' in graph_dict['nodes'][0]
        print("+ Serialized graph correctly")
        
        # Test deserialization
        new_graph = ContextGraph()
        new_graph.from_dict(graph_dict)
        assert len(new_graph.nodes) == 2
        assert len(new_graph.edges) == 2
        print("+ Deserialized graph correctly")
        
        print("✓ ContextGraph direct functionality test passed")
    
    def test_financial_services_example(self, mock_vector_store, mock_knowledge_graph):
        """Test the financial services example from the feature description."""
        print("Testing Financial Services Example...")
        
        # Initialize context with decision tracking
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=True,
            advanced_analytics=True,
            kg_algorithms=True,
            vector_store_features=True
        )
        
        # Credit decision with precedent search
        decision_id = context.record_decision(
            category="credit_approval",
            scenario="High-risk credit limit increase",
            reasoning="Past fraud flag with velocity check failure",
            outcome="rejected",
            confidence=0.788,
            entities=["customer:jessica_norris"]
        )
        assert decision_id is not None
        print("+ Recorded decision")
        
        # Find similar precedents
        precedents = context.find_precedents(
            scenario="High-risk customer credit increase",
            category="credit_approval",
            limit=5
        )
        assert isinstance(precedents, list)
        print("+ Found precedents")
        
        # Analyze causal chain
        causal_chain = context.get_causal_chain(decision_id, max_depth=5)
        assert isinstance(causal_chain, list)
        print("+ Analyzed causal chain")
        
        print("✓ Financial services example test passed")
    
    def test_healthcare_example(self, mock_vector_store, mock_knowledge_graph):
        """Test the healthcare example from the feature description."""
        print("Testing Healthcare Example...")
        
        # Initialize context with decision tracking
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=True,
            advanced_analytics=True,
            kg_algorithms=True,
            vector_store_features=True
        )
        
        # Treatment decision with policy compliance
        decision_id = context.record_decision(
            category="treatment_plan",
            scenario="Diabetic patient with comorbidities",
            reasoning="Standard protocol contraindicated due to renal function",
            outcome="modified_treatment",
            confidence=0.92
        )
        assert decision_id is not None
        print("+ Recorded decision")
        
        # Check policy engine availability
        policy_engine = context.get_policy_engine()
        if policy_engine:
            # Create a test policy
            policy = Policy(
                policy_id="diabetes_protocol_v2",
                name="Diabetes Treatment Protocol v2",
                description="Standard treatment protocol for diabetes patients",
                rules={"contraindications": ["renal_impairment"], "max_dosage": 100},
                category="treatment",
                version="v2",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Test policy operations
            assert policy.policy_id == "diabetes_protocol_v2"
            assert policy.category == "treatment"
            print("+ Policy operations working")
        
        print("✓ Healthcare example test passed")
    
    def test_legal_example(self, mock_vector_store, mock_knowledge_graph):
        """Test the legal example from the feature description."""
        print("Testing Legal Example...")
        
        # Initialize context with decision tracking
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=True,
            advanced_analytics=True,
            kg_algorithms=True,
            vector_store_features=True
        )
        
        # Legal decision with precedent analysis
        decision_id = context.record_decision(
            category="contract_review",
            scenario="Non-standard liability clause",
            reasoning="Precedent cases show similar clauses upheld",
            outcome="approved_with_modifications",
            confidence=0.85
        )
        assert decision_id is not None
        print("+ Recorded decision")
        
        # Find legal precedents
        precedents = context.find_precedents(
            scenario="Liability limitation clauses",
            category="contract_review",
            limit=10
        )
        assert isinstance(precedents, list)
        print("+ Found legal precedents")
        
        print("✓ Legal example test passed")
    
    def test_decision_models_functionality(self):
        """Test decision models functionality."""
        print("Testing Decision Models...")
        
        # Test Decision model
        decision = Decision(
            decision_id="test_decision",
            category="test_category",
            scenario="Test scenario",
            reasoning="Test reasoning",
            outcome="approved",
            confidence=0.95,
            timestamp=datetime.now(),
            decision_maker="test_agent"
        )
        
        assert decision.decision_id == "test_decision"
        assert decision.category == "test_category"
        assert 0 <= decision.confidence <= 1
        
        # Test serialization
        decision_dict = decision.to_dict()
        assert decision_dict["decision_id"] == "test_decision"
        assert "timestamp" in decision_dict
        
        # Test deserialization
        restored_decision = Decision.from_dict(decision_dict)
        assert restored_decision.decision_id == decision.decision_id
        assert restored_decision.category == decision.category
        print("+ Decision model serialization working")
        
        # Test Policy model
        policy = Policy(
            policy_id="test_policy",
            name="Test Policy",
            description="Test policy description",
            rules={"max_amount": 1000},
            category="test",
            version="1.0",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert policy.policy_id == "test_policy"
        assert policy.rules["max_amount"] == 1000
        
        # Test PolicyException model
        exception = PolicyException(
            exception_id="test_exception",
            decision_id="test_decision",
            policy_id="test_policy",
            reason="Test exception",
            approver="test_approver",
            approval_timestamp=datetime.now(),
            justification="Test justification"
        )
        
        assert exception.exception_id == "test_exception"
        assert exception.decision_id == "test_decision"
        print("+ Policy models working")
        
        print("✓ Decision models functionality test passed")
    
    def test_context_graph_edge_cases(self):
        """Test ContextGraph edge cases and error handling."""
        print("Testing ContextGraph Edge Cases...")
        
        graph = ContextGraph()
        
        # Test empty decision ID handling
        decision_empty_id = Decision(
            decision_id="",  # Empty ID - will be auto-generated
            category="test",
            scenario="test scenario",
            reasoning="test reasoning",
            outcome="test outcome",
            confidence=0.8,
            timestamp=datetime.now(),
            decision_maker="test_agent"
        )
        
        graph.add_decision(decision_empty_id)
        assert len(graph.nodes) == 1  # Should have generated UUID for empty string
        assert "" not in graph.nodes  # Empty string should not be preserved
        print("+ Empty decision ID handling working")
        
        # Test None decision ID handling
        decision_none_id = Decision(
            decision_id=None,  # None ID
            category="test",
            scenario="test scenario 2",
            reasoning="test reasoning 2",
            outcome="test outcome 2",
            confidence=0.8,
            timestamp=datetime.now(),
            decision_maker="test_agent"
        )
        
        graph.add_decision(decision_none_id)
        assert len(graph.nodes) == 2  # Should have generated UUID
        print("+ None decision ID handling working")
        
        # Test causal relationship with nonexistent nodes (should not raise error)
        graph.add_causal_relationship("nonexistent1", "nonexistent2", "CAUSED")
        assert len(graph.edges) == 0  # Should not add relationship
        print("+ Nonexistent node handling working")
        
        # Test invalid relationship type
        with pytest.raises(ValueError):
            graph.add_causal_relationship("test", "test2", "INVALID_TYPE")
        print("+ Invalid relationship type validation working")
        
        # Test causal chain with nonexistent decision
        chain = graph.get_causal_chain("nonexistent", direction="upstream")
        assert len(chain) == 0
        print("+ Nonexistent decision handling working")
        
        print("✓ ContextGraph edge cases test passed")
    
    def test_advanced_features_integration(self, mock_vector_store, mock_knowledge_graph):
        """Test advanced features integration."""
        print("Testing Advanced Features Integration...")
        
        # Test with all features enabled
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=True,
            advanced_analytics=True,
            kg_algorithms=True,
            vector_store_features=True,
            graph_expansion=True,
            max_expansion_hops=3,
            hybrid_alpha=0.7
        )
        
        # Verify configuration
        assert context.config["decision_tracking"] is True
        assert context.config["advanced_analytics"] is True
        assert context.config["kg_algorithms"] is True
        assert context.config["vector_store_features"] is True
        assert context.config["graph_expansion"] is True
        assert context.config["max_expansion_hops"] == 3
        assert context.config["hybrid_alpha"] == 0.7
        print("+ Configuration validation working")
        
        # Test decision tracking with advanced features
        decision_id = context.record_decision(
            category="advanced_test",
            scenario="Advanced feature test scenario",
            reasoning="Testing advanced analytics integration",
            outcome="processed",
            confidence=0.88,
            entities=["entity1", "entity2"]
        )
        
        assert decision_id is not None
        print("+ Advanced decision recording working")
        
        # Test context insights
        insights = context.get_context_insights()
        assert isinstance(insights, dict)
        print("+ Context insights working")
        
        print("✓ Advanced features integration test passed")


class TestContextGraphsPerformance:
    """Performance tests for Context Graphs feature."""
    
    def test_large_decision_network(self):
        """Test handling of large decision networks."""
        print("Testing Large Decision Network...")
        
        graph = ContextGraph()
        
        # Create a network of 100 decisions
        decisions = []
        for i in range(100):
            decision = Decision(
                decision_id=f"decision_{i:03d}",
                category="performance_test",
                scenario=f"Performance test scenario {i}",
                reasoning=f"Performance test reasoning {i}",
                outcome="processed",
                confidence=0.8 + (i % 20) * 0.01,  # Varying confidence
                timestamp=datetime.now(),
                decision_maker="performance_agent"
            )
            decisions.append(decision)
            graph.add_decision(decision)
        
        assert len(graph.nodes) == 100
        print("+ Created 100 decisions")
        
        # Add causal relationships to create a network
        for i in range(99):
            # Create a mix of relationship types
            relationship_type = ["CAUSED", "INFLUENCED", "PRECEDENT_FOR"][i % 3]
            graph.add_causal_relationship(f"decision_{i:03d}", f"decision_{i+1:03d}", relationship_type)
        
        assert len(graph.edges) == 99
        print("+ Created 99 causal relationships")
        
        # Test causal chain performance
        chain = graph.get_causal_chain("decision_099", direction="upstream", max_depth=50)
        assert len(chain) > 0
        print("+ Causal chain analysis working")
        
        # Test precedent search performance
        precedents = graph.find_precedents("decision_050", limit=20)
        assert isinstance(precedents, list)
        print("+ Precedent search working")
        
        # Test serialization performance
        graph_dict = graph.to_dict()
        assert len(graph_dict['nodes']) == 100
        assert len(graph_dict['edges']) == 99
        print("+ Large graph serialization working")
        
        print("✓ Large decision network test passed")
    
    def test_concurrent_operations(self):
        """Test concurrent decision operations."""
        print("Testing Concurrent Operations...")
        
        import threading
        import time
        
        graph = ContextGraph()
        results = []
        errors = []
        
        def add_decisions(start_id, count):
            """Add decisions in a separate thread."""
            try:
                for i in range(count):
                    decision = Decision(
                        decision_id=f"concurrent_decision_{start_id + i:03d}",
                        category="concurrent_test",
                        scenario=f"Concurrent test {start_id + i}",
                        reasoning="Concurrent reasoning",
                        outcome="processed",
                        confidence=0.8,
                        timestamp=datetime.now(),
                        decision_maker="concurrent_agent"
                    )
                    graph.add_decision(decision)
                    time.sleep(0.001)  # Small delay to simulate real work
                results.append(f"Thread {start_id} completed")
            except Exception as e:
                errors.append(f"Thread {start_id} error: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_decisions, args=(i * 20, 20))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        assert len(graph.nodes) == 100  # 5 threads * 20 decisions each
        print("+ Concurrent operations completed successfully")
        
        print("✓ Concurrent operations test passed")


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])
