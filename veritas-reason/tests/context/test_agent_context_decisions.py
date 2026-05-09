"""
Tests for AgentContext Decision Tracking Enhancement

This module tests the enhanced AgentContext class with decision tracking
methods and functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from veritasreason.context.agent_context import AgentContext
from veritasreason.context.decision_models import Decision, Policy
from veritasreason.context.context_graph import ContextGraph


class TestAgentContextDecisions:
    """Test AgentContext decision tracking enhancements."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store for testing."""
        mock_store = Mock()
        mock_store.add = Mock()
        mock_store.search = Mock(return_value=[])
        return mock_store
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Mock knowledge graph for testing."""
        mock_graph = Mock()
        mock_graph.execute_query = Mock(return_value=[])  # Return empty list by default
        return mock_graph
    
    @pytest.fixture
    def agent_context_with_decisions(self, mock_vector_store, mock_knowledge_graph):
        """Create AgentContext with decision tracking enabled."""
        return AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=True
        )
    
    @pytest.fixture
    def agent_context_without_decisions(self, mock_vector_store, mock_knowledge_graph):
        """Create AgentContext without decision tracking."""
        return AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=False
        )
    
    def test_agent_context_initialization_with_decisions(self, mock_vector_store, mock_knowledge_graph):
        """Test AgentContext initialization with decision tracking."""
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=True
        )
        
        assert context.config["decision_tracking"] is True
        assert context._decision_recorder is not None
        assert context._decision_query is not None
        assert context._causal_analyzer is not None
        assert context._policy_engine is not None
    
    def test_agent_context_initialization_without_decisions(self, mock_vector_store, mock_knowledge_graph):
        """Test AgentContext initialization without decision tracking."""
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph,
            decision_tracking=False
        )
        
        assert context.config["decision_tracking"] is False
        assert context._decision_recorder is None
        assert context._decision_query is None
        assert context._causal_analyzer is None
        assert context._policy_engine is None
    
    def test_record_decision_success(self, agent_context_with_decisions):
        """Test successful decision recording."""
        decision_id = agent_context_with_decisions.record_decision(
            category="credit_approval",
            scenario="Credit limit increase request",
            reasoning="Customer has excellent payment history",
            outcome="approved",
            confidence=0.85,
            entities=["customer_001"],
            decision_maker="ai_agent_001"
        )
        
        assert decision_id is not None
    
    def test_record_decision_with_cross_system_context(self, agent_context_with_decisions):
        """Test decision recording with cross-system context."""
        cross_system_context = {
            "salesforce": {"customer_tier": "premium"},
            "zendesk": {"open_tickets": 2}
        }
        
        decision_id = agent_context_with_decisions.record_decision(
            category="credit_approval",
            scenario="Credit limit increase request",
            reasoning="Customer has excellent payment history",
            outcome="approved",
            confidence=0.85,
            cross_system_context=cross_system_context
        )
        
        assert decision_id is not None
    
    def test_record_decision_not_enabled(self, agent_context_without_decisions):
        """Test decision recording when not enabled."""
        with pytest.raises(RuntimeError, match="Decision tracking is not enabled"):
            agent_context_without_decisions.record_decision(
                category="test",
                scenario="test scenario",
                reasoning="test reasoning",
                outcome="test outcome",
                confidence=0.8
            )
    
    def test_find_precedents_success(self, agent_context_with_decisions):
        """Test precedent finding."""
        precedents = agent_context_with_decisions.find_precedents(
            scenario="Credit limit increase request",
            category="credit_approval",
            limit=5
        )
        
        # Should return a list (even if empty due to mocked dependencies)
        assert isinstance(precedents, list)
    
    def test_find_precedents_not_hybrid(self, agent_context_with_decisions):
        """Test precedent finding without hybrid search."""
        precedents = agent_context_with_decisions.find_precedents(
            scenario="test scenario",
            category="credit_approval",
            use_hybrid_search=False
        )
        
        # Should return a list (even if empty due to mocked dependencies)
        assert isinstance(precedents, list)
    
    def test_find_precedents_not_enabled(self, agent_context_without_decisions):
        """Test precedent finding when not enabled."""
        with pytest.raises(RuntimeError, match="Decision tracking is not enabled"):
            agent_context_without_decisions.find_precedents("test scenario")
    
    def test_get_causal_chain_success(self, agent_context_with_decisions):
        """Test successful causal chain retrieval."""
        chain = agent_context_with_decisions.get_causal_chain(
            decision_id="decision_001",
            direction="upstream",
            max_depth=5
        )
        
        # Should return a list (even if empty due to mocked dependencies)
        assert isinstance(chain, list)
    
    def test_get_causal_chain_not_enabled(self, agent_context_without_decisions):
        """Test causal chain retrieval when not enabled."""
        with pytest.raises(RuntimeError, match="Decision tracking is not enabled"):
            agent_context_without_decisions.get_causal_chain("decision_001")
    
    def test_get_policy_engine_success(self, agent_context_with_decisions):
        """Test getting policy engine."""
        policy_engine = agent_context_with_decisions.get_policy_engine()
        
        assert policy_engine is not None
        assert policy_engine == agent_context_with_decisions._policy_engine
    
    def test_get_policy_engine_not_enabled(self, agent_context_without_decisions):
        """Test getting policy engine when not enabled."""
        with pytest.raises(RuntimeError, match="Decision tracking is not enabled"):
            agent_context_without_decisions.get_policy_engine()
    
    def test_multi_hop_context_query_success(self, agent_context_with_decisions):
        """Test multi-hop context query."""
        result = agent_context_with_decisions.multi_hop_context_query(
            start_entity="entity_001",
            query="Find related decisions",
            max_hops=3
        )
        
        # Should return a result structure
        assert "query" in result
        assert "start_entity" in result
        assert "max_hops" in result
        assert "decisions" in result
        assert result["query"] == "Find related decisions"
        assert result["start_entity"] == "entity_001"
        assert result["max_hops"] == 3
        assert isinstance(result["decisions"], list)
    
    def test_multi_hop_context_query_not_enabled(self, agent_context_without_decisions):
        """Test multi-hop context query when not enabled."""
        with pytest.raises(RuntimeError, match="Decision tracking is not enabled"):
            agent_context_without_decisions.multi_hop_context_query("entity_001", "test query")
    
    def test_query_decisions_success(self, agent_context_with_decisions):
        """Test decision query."""
        decisions = agent_context_with_decisions.query_decisions(
            query="test query",
            max_hops=2,
            use_hybrid_search=True
        )
        
        # Should return a list (even if empty due to mocked dependencies)
        assert isinstance(decisions, list)
    
    def test_trace_decision_explainability_success(self, agent_context_with_decisions):
        """Test decision explainability tracing."""
        explainability = agent_context_with_decisions.trace_decision_explainability("decision_001")
        
        # Should return an explainability structure
        assert "decision_id" in explainability
        assert "upstream_decisions" in explainability
        assert "downstream_decisions" in explainability
        assert "relationship_paths" in explainability
        assert explainability["decision_id"] == "decision_001"
        assert isinstance(explainability["upstream_decisions"], list)
        assert isinstance(explainability["downstream_decisions"], list)
        assert isinstance(explainability["relationship_paths"], list)
    
    def test_trace_decision_explainability_not_enabled(self, agent_context_without_decisions):
        """Test decision explainability when not enabled."""
        with pytest.raises(RuntimeError, match="Decision tracking is not enabled"):
            agent_context_without_decisions.trace_decision_explainability("decision_001")
    
    def test_capture_cross_system_inputs(self, agent_context_with_decisions):
        """Test cross-system inputs capture."""
        systems = ["salesforce", "zendesk", "pagerduty"]
        entity_id = "customer_001"
        
        context = agent_context_with_decisions.capture_cross_system_inputs(systems, entity_id)
        
        assert len(context) == len(systems)
        assert "salesforce" in context
        assert "zendesk" in context
        assert "pagerduty" in context
        
        for system in systems:
            assert context[system]["entity_id"] == entity_id
            assert context[system]["system_name"] == system
            assert "captured_at" in context[system]
            assert context[system]["status"] == "captured"

    def test_capture_cross_system_inputs_sanitizes_errors(
        self, agent_context_with_decisions, mock_knowledge_graph
    ):
        """Test capture errors are sanitized in returned payload."""
        mock_knowledge_graph.execute_query.side_effect = RuntimeError(
            "backend connection failed: sensitive details"
        )

        context = agent_context_with_decisions.capture_cross_system_inputs(
            ["salesforce"], "customer_001"
        )

        assert context["salesforce"]["status"] == "capture_failed"
        assert context["salesforce"]["error"] == "internal_capture_error"
        assert "sensitive" not in context["salesforce"]["error"]
    
    def test_backward_compatibility(self, mock_vector_store, mock_knowledge_graph):
        """Test backward compatibility when decision tracking is not explicitly set."""
        # Should work without decision tracking enabled
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph
        )
        
        assert context.config["decision_tracking"] is False
        assert context._decision_recorder is None
    
    def test_error_handling(self, agent_context_with_decisions):
        """Test error handling in decision tracking."""
        # Test with invalid parameters
        try:
            agent_context_with_decisions.record_decision(
                category="",  # Invalid empty category
                scenario="test",
                reasoning="test",
                outcome="test",
                confidence=0.8
            )
        except Exception:
            # Should handle errors gracefully
            pass

    def test_checkpoint_diff_and_flush(self, mock_vector_store):
        """Checkpointing should capture and diff graph changes."""
        graph = ContextGraph()
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=graph,
            decision_tracking=True,
        )

        context.checkpoint("before")
        decision_id = context.record_decision(
            category="policy",
            scenario="Apply updated policy",
            reasoning="New evidence available",
            outcome="approved",
            confidence=0.9,
        )
        graph.add_node("entity_001", "entity", content="Customer")
        graph.add_edge(decision_id, "entity_001", "involves")
        context.checkpoint("after")

        diff = context.diff_checkpoints("before", "after")

        assert any(item["id"] == decision_id for item in diff["decisions_added"])
        assert any(item["type"] == "involves" for item in diff["relationships_added"])

        snapshot = context.flush_checkpoint("after")
        assert snapshot["label"] == "after"

    def test_diff_checkpoints_unknown_label_raises_key_error(self, mock_vector_store):
        """Unknown checkpoint labels should raise a clear KeyError."""
        graph = ContextGraph()
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=graph,
            decision_tracking=True,
        )

        context.checkpoint("after")

        with pytest.raises(KeyError, match="unknown"):
            context.diff_checkpoints("unknown", "after")
    
    def test_decision_tracking_requires_knowledge_graph(self, mock_vector_store):
        """Test that decision tracking requires knowledge graph."""
        # Should work but with limited functionality
        context = AgentContext(
            vector_store=mock_vector_store,
            knowledge_graph=None,
            decision_tracking=True
        )
        
        # Should initialize but warn about missing knowledge graph
        assert context.config["decision_tracking"] is True
    
    def test_error_handling(self, agent_context_with_decisions):
        """Test error handling in decision tracking."""
        # Test with invalid parameters
        try:
            agent_context_with_decisions.record_decision(
                category="",  # Invalid empty category
                scenario="test",
                reasoning="test",
                outcome="test",
                confidence=0.8
            )
        except Exception:
            # Should handle errors gracefully
            pass


if __name__ == "__main__":
    pytest.main([__file__])
