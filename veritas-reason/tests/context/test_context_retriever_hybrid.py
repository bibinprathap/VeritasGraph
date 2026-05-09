"""
Tests for Enhanced Context Retriever Hybrid Search

This module contains comprehensive tests for the enhanced context retriever
with hybrid precedent search capabilities.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from veritasreason.context import ContextRetriever, RetrievedContext


class TestContextRetrieverHybrid:
    """Test cases for enhanced ContextRetriever with hybrid search."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock vector store with decision search capabilities
        self.mock_vector_store = Mock()
        self.mock_vector_store.search_decisions.return_value = [
            {
                "similarity": 0.85,
                "metadata": {
                    "scenario": "Credit limit increase",
                    "reasoning": "Good payment history",
                    "outcome": "approved",
                    "entities": ["customer_123"],
                    "category": "credit_approval"
                },
                "id": "decision_1"
            },
            {
                "similarity": 0.75,
                "metadata": {
                    "scenario": "Credit limit decrease",
                    "reasoning": "High risk profile",
                    "outcome": "rejected",
                    "entities": ["customer_456"],
                    "category": "credit_approval"
                },
                "id": "decision_2"
            }
        ]
        
        # Mock knowledge graph
        self.mock_knowledge_graph = Mock()
        self.mock_knowledge_graph.get_neighbors.return_value = ["related_entity_1", "related_entity_2"]
        self.mock_knowledge_graph.get_nodes_by_label.return_value = ["policy_1", "policy_2"]
        
        # Create context retriever
        self.context_retriever = ContextRetriever(
            vector_store=self.mock_vector_store,
            knowledge_graph=self.mock_knowledge_graph,
            max_expansion_hops=3
        )
    
    def test_initialization_with_decision_components(self):
        """Test initialization with decision-specific components."""
        assert hasattr(self.context_retriever, 'hybrid_calculator')
        assert hasattr(self.context_retriever, 'decision_pipeline')
        assert self.context_retriever.decision_pipeline is not None
    
    def test_initialization_without_vector_store(self):
        """Test initialization without vector store."""
        retriever = ContextRetriever(vector_store=None, knowledge_graph=self.mock_knowledge_graph)
        
        assert retriever.decision_pipeline is None
        assert retriever.hybrid_calculator is not None
    
    def test_retrieve_decision_precedents(self):
        """Test retrieving decision precedents."""
        precedents = self.context_retriever.retrieve_decision_precedents(
            query="Credit limit increase",
            limit=5,
            use_hybrid_search=True,
            semantic_weight=0.7,
            structural_weight=0.3
        )
        
        assert len(precedents) == 2
        assert all(isinstance(p, RetrievedContext) for p in precedents)
        
        # Check first precedent
        precedent = precedents[0]
        assert "Scenario: Credit limit increase" in precedent.content
        assert "Reasoning: Good payment history" in precedent.content
        assert "Outcome: approved" in precedent.content
        assert precedent.score == 0.85
        assert precedent.source == "decision_precedent"
        assert precedent.metadata["scenario"] == "Credit limit increase"
    
    def test_retrieve_decision_precedents_without_vector_store(self):
        """Test retrieving precedents without vector store."""
        retriever = ContextRetriever(vector_store=None, knowledge_graph=self.mock_knowledge_graph)
        
        precedents = retriever.retrieve_decision_precedents("test query")
        
        assert precedents == []
    
    def test_retrieve_decision_precedents_fallback_search(self):
        """Test retrieving precedents with fallback search."""
        # Mock vector store without search_decisions
        self.mock_vector_store.search_decisions.side_effect = AttributeError("No search_decisions")
        self.mock_vector_store.search.return_value = [
            {
                "score": 0.8,
                "metadata": {"scenario": "Test decision"},
                "id": "vec_1"
            }
        ]
        
        precedents = self.context_retriever.retrieve_decision_precedents("test query")
        
        assert len(precedents) == 1
        assert precedents[0].score == 0.8
    
    def test_retrieve_decision_precedents_with_context_expansion(self):
        """Test retrieving precedents with context expansion."""
        precedents = self.context_retriever.retrieve_decision_precedents(
            query="Credit limit increase",
            include_context=True,
            max_hops=2
        )
        
        assert len(precedents) == 2
        
        # Check that context was added
        precedent = precedents[0]
        assert len(precedent.related_entities) > 0
        
        # Verify graph expansion was called
        self.mock_knowledge_graph.get_neighbors.assert_called()
    
    def test_query_decisions(self):
        """Test querying decisions with multi-hop reasoning."""
        results = self.context_retriever.query_decisions(
            query="Credit limit increase",
            max_hops=3,
            include_context=True,
            use_hybrid_search=False,
            limit=10
        )
        
        assert len(results) == 2
        assert all(isinstance(r, RetrievedContext) for r in results)
        
        # Verify search parameters
        self.mock_vector_store.search_decisions.assert_called_with(
            query="Credit limit increase",
            semantic_weight=0.7,
            structural_weight=0.3,
            filters=None,
            limit=10,
            use_hybrid_search=False
        )
    
    def test_get_decision_context(self):
        """Test getting comprehensive decision context."""
        # Mock vector store methods
        self.mock_vector_store.get_metadata.return_value = {
            "scenario": "Credit limit increase",
            "reasoning": "Good payment history",
            "outcome": "approved",
            "entities": ["customer_123"],
            "category": "credit_approval"
        }
        
        context = self.context_retriever.get_decision_context(
            decision_id="decision_1",
            depth=2,
            include_entities=True,
            include_policies=True,
            max_hops=3
        )
        
        assert isinstance(context, RetrievedContext)
        assert "Decision ID: decision_1" in context.content
        assert "Scenario: Credit limit increase" in context.content
        assert "Reasoning: Good payment history" in context.content
        assert "Outcome: approved" in context.content
        assert context.score == 1.0
        assert context.source == "decision_context"
        
        # Verify entities and policies were added
        assert len(context.related_entities) > 0
        assert len(context.related_relationships) > 0
    
    def test_get_decision_context_not_found(self):
        """Test getting context for non-existent decision."""
        self.mock_vector_store.get_metadata.return_value = None
        
        with pytest.raises(ValueError, match="Decision decision_999 not found"):
            self.context_retriever.get_decision_context("decision_999")
    
    def test_get_decision_context_no_vector_store(self):
        """Test getting context without vector store."""
        retriever = ContextRetriever(vector_store=None, knowledge_graph=self.mock_knowledge_graph)
        
        with pytest.raises(ValueError, match="Vector store required for decision context"):
            retriever.get_decision_context("decision_1")
    
    def test_extract_entities_from_decision(self):
        """Test extracting entities from decision metadata."""
        metadata = {
            "entities": ["customer_123", "credit_card"],
            "category": "credit_approval"
        }
        
        entities = self.context_retriever._extract_entities_from_decision(metadata)
        
        assert len(entities) == 3  # 2 entities + 1 category
        assert any(e["name"] == "customer_123" for e in entities)
        assert any(e["name"] == "credit_card" for e in entities)
        assert any(e["name"] == "credit_approval" for e in entities)
        assert all(e["source"] == "decision" for e in entities)
    
    def test_expand_decision_context(self):
        """Test expanding decision context using graph traversal."""
        entities = [
            {"name": "customer_123", "type": "entity", "source": "decision"},
            {"name": "credit_approval", "type": "category", "source": "decision"}
        ]
        
        expanded = self.context_retriever._expand_decision_context(entities, max_hops=2)
        
        assert len(expanded) > 0
        assert all(e["source"] == "graph_expansion" for e in expanded)
        assert all("parent_entity" in e for e in expanded)
        
        # Verify graph traversal was called (at least once per entity)
        assert self.mock_knowledge_graph.get_neighbors.call_count >= 2
    
    def test_expand_decision_context_no_knowledge_graph(self):
        """Test expanding context without knowledge graph."""
        retriever = ContextRetriever(vector_store=self.mock_vector_store, knowledge_graph=None)
        
        entities = [{"name": "test", "type": "entity", "source": "decision"}]
        expanded = retriever._expand_decision_context(entities, max_hops=2)
        
        assert expanded == []
    
    def test_find_relevant_policies(self):
        """Test finding relevant policies for decision."""
        metadata = {"category": "credit_approval"}
        
        policies = self.context_retriever._find_relevant_policies(metadata)
        
        assert len(policies) == 2
        assert all(p["type"] == "policy" for p in policies)
        assert all(p["source"] == "policy_search" for p in policies)
        assert all(p["related_category"] == "credit_approval" for p in policies)
        
        # Verify policy search was called
        self.mock_knowledge_graph.get_nodes_by_label.assert_called_with("Policy")
    
    def test_find_relevant_policies_no_category(self):
        """Test finding policies without category."""
        metadata = {"outcome": "approved"}
        
        policies = self.context_retriever._find_relevant_policies(metadata)
        
        assert policies == []
    
    def test_find_relevant_policies_no_knowledge_graph(self):
        """Test finding policies without knowledge graph."""
        retriever = ContextRetriever(vector_store=self.mock_vector_store, knowledge_graph=None)
        
        policies = retriever._find_relevant_policies({"category": "test"})
        
        assert policies == []
    
    def test_retrieve_decision_precedents_with_filters(self):
        """Test retrieving precedents with filters."""
        filters = {"category": "credit_approval", "outcome": "approved"}
        
        precedents = self.context_retriever.retrieve_decision_precedents(
            query="Credit limit increase",
            filters=filters
        )
        
        assert len(precedents) == 2
        
        # Verify filters were passed through
        self.mock_vector_store.search_decisions.assert_called_with(
            query="Credit limit increase",
            semantic_weight=0.7,
            structural_weight=0.3,
            filters=filters,
            limit=10,
            use_hybrid_search=True
        )
    
    def test_retrieve_decision_precedents_context_expansion_disabled(self):
        """Test retrieving precedents with context expansion disabled."""
        precedents = self.context_retriever.retrieve_decision_precedents(
            query="Credit limit increase",
            include_context=False
        )
        
        assert len(precedents) == 2
        
        # Verify no graph expansion
        for precedent in precedents:
            assert len(precedent.related_entities) == 0
    
    def test_retrieve_decision_precedents_no_hybrid_search(self):
        """Test retrieving precedents without hybrid search."""
        precedents = self.context_retriever.retrieve_decision_precedents(
            query="Credit limit increase",
            use_hybrid_search=False
        )
        
        assert len(precedents) == 2
        
        # Verify no graph expansion for context
        for precedent in precedents:
            assert len(precedent.related_entities) == 0


class TestContextRetrieverHybridEdgeCases:
    """Test edge cases for enhanced ContextRetriever."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_vector_store = Mock()
        self.mock_knowledge_graph = Mock()
        self.context_retriever = ContextRetriever(
            vector_store=self.mock_vector_store,
            knowledge_graph=self.mock_knowledge_graph
        )
    
    def test_retrieve_decision_precedents_empty_results(self):
        """Test retrieving precedents with empty results."""
        self.mock_vector_store.search_decisions.return_value = []
        
        precedents = self.context_retriever.retrieve_decision_precedents("test query")
        
        assert precedents == []
    
    def test_retrieve_decision_precedents_malformed_metadata(self):
        """Test retrieving precedents with malformed metadata."""
        self.mock_vector_store.search_decisions.return_value = [
            {
                "similarity": 0.8,
                "metadata": {"scenario": "Test"},  # Minimal metadata
                "id": "decision_1"
            },
            {
                "similarity": 0.7,
                "metadata": {},  # Empty metadata
                "id": "decision_2"
            }
        ]
        
        precedents = self.context_retriever.retrieve_decision_precedents("test query")
        
        assert len(precedents) == 2
        assert all(isinstance(p, RetrievedContext) for p in precedents)
    
    def test_retrieve_decision_precedents_graph_expansion_error(self):
        """Test graph expansion error handling."""
        self.mock_vector_store.search_decisions.return_value = [
            {
                "similarity": 0.8,
                "metadata": {
                    "scenario": "Test",
                    "entities": ["entity_1"]
                },
                "id": "decision_1"
            }
        ]
        
        # Mock graph expansion to raise error
        self.mock_knowledge_graph.get_neighbors.side_effect = Exception("Graph error")
        
        # Should not raise exception, just log warning
        precedents = self.context_retriever.retrieve_decision_precedents(
            "test query",
            include_context=True
        )
        
        assert len(precedents) == 1
        assert len(precedents[0].related_entities) > 0  # Should still have original entities
    
    def test_extract_entities_from_decision_empty_metadata(self):
        """Test extracting entities from empty metadata."""
        entities = self.context_retriever._extract_entities_from_decision({})
        
        assert entities == []
    
    def test_expand_decision_context_empty_entities(self):
        """Test expanding context with empty entities."""
        expanded = self.context_retriever._expand_decision_context([], max_hops=2)
        
        assert expanded == []
    
    def test_expand_decision_context_entity_without_name(self):
        """Test expanding context with entity without name."""
        entities = [{"type": "entity", "source": "decision"}]  # Missing name
        
        expanded = self.context_retriever._expand_decision_context(entities, max_hops=2)
        
        assert expanded == []
    
    def test_find_relevant_policies_graph_error(self):
        """Test policy search with graph error."""
        self.mock_knowledge_graph.get_nodes_by_label.side_effect = Exception("Graph error")
        
        policies = self.context_retriever._find_relevant_policies({"category": "test"})
        
        assert policies == []


if __name__ == "__main__":
    pytest.main([__file__])
