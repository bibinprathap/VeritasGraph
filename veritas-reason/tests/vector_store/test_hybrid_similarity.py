"""
Tests for Hybrid Similarity Calculator

This module contains comprehensive tests for the hybrid similarity calculator
functionality, including similarity calculation, batch processing, and filtering.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from veritasreason.vector_store.hybrid_similarity import HybridSimilarityCalculator


class TestHybridSimilarityCalculator:
    """Test cases for HybridSimilarityCalculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = HybridSimilarityCalculator(
            semantic_weight=0.7,
            structural_weight=0.3
        )
        
        # Sample embeddings
        self.semantic_vec1 = np.array([0.1, 0.2, 0.3, 0.4])
        self.semantic_vec2 = np.array([0.2, 0.3, 0.4, 0.5])
        self.structural_vec1 = np.array([0.5, 0.6, 0.7, 0.8])
        self.structural_vec2 = np.array([0.6, 0.7, 0.8, 0.9])
    
    def test_initialization(self):
        """Test calculator initialization."""
        assert self.calculator.semantic_weight == 0.7
        assert self.calculator.structural_weight == 0.3
        assert self.calculator.semantic_metric == "cosine"
        assert self.calculator.structural_metric == "cosine"
    
    def test_initialization_invalid_weights(self):
        """Test initialization with invalid weights."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            HybridSimilarityCalculator(semantic_weight=0.8, structural_weight=0.3)
    
    def test_initialization_invalid_metric(self):
        """Test initialization with invalid metric."""
        with pytest.raises(ValueError, match="Invalid semantic metric"):
            HybridSimilarityCalculator(semantic_metric="invalid")
    
    def test_calculate_hybrid_similarity(self):
        """Test hybrid similarity calculation."""
        similarity = self.calculator.calculate_hybrid_similarity(
            self.semantic_vec1, self.structural_vec1,
            self.semantic_vec2, self.structural_vec2
        )
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
    
    def test_calculate_hybrid_similarity_with_weights(self):
        """Test hybrid similarity with custom weights."""
        similarity = self.calculator.calculate_hybrid_similarity(
            self.semantic_vec1, self.structural_vec1,
            self.semantic_vec2, self.structural_vec2,
            weights=(0.5, 0.5)
        )
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
    
    def test_calculate_batch_hybrid_similarity(self):
        """Test batch hybrid similarity calculation."""
        candidate_semantics = [self.semantic_vec2, self.semantic_vec1]
        candidate_structurals = [self.structural_vec2, self.structural_vec1]
        
        similarities = self.calculator.calculate_batch_hybrid_similarity(
            self.semantic_vec1, self.structural_vec1,
            candidate_semantics, candidate_structurals
        )
        
        assert len(similarities) == 2
        assert all(isinstance(s, float) for s in similarities)
        assert all(0.0 <= s <= 1.0 for s in similarities)
    
    def test_calculate_batch_hybrid_similarity_mismatched_lengths(self):
        """Test batch calculation with mismatched list lengths."""
        with pytest.raises(ValueError, match="Candidate lists must have same length"):
            self.calculator.calculate_batch_hybrid_similarity(
                self.semantic_vec1, self.structural_vec1,
                [self.semantic_vec2], []
            )
    
    def test_find_most_similar_decisions(self):
        """Test finding most similar decisions."""
        candidate_embeddings = [
            (self.semantic_vec2, self.structural_vec2),
            (self.semantic_vec1, self.structural_vec1)
        ]
        candidate_metadata = [
            {"category": "credit_approval", "outcome": "approved"},
            {"category": "credit_approval", "outcome": "rejected"}
        ]
        
        results = self.calculator.find_most_similar_decisions(
            self.semantic_vec1, self.structural_vec1,
            candidate_embeddings, candidate_metadata, top_k=2
        )
        
        assert len(results) == 2
        assert all("similarity" in result for result in results)
        assert all("semantic_similarity" in result for result in results)
        assert all("structural_similarity" in result for result in results)
        assert all("metadata" in result for result in results)
    
    def test_find_most_similar_decisions_with_filters(self):
        """Test finding similar decisions with filters."""
        candidate_embeddings = [
            (self.semantic_vec2, self.structural_vec2),
            (self.semantic_vec1, self.structural_vec1)
        ]
        candidate_metadata = [
            {"category": "credit_approval", "outcome": "approved"},
            {"category": "fraud_detection", "outcome": "blocked"}
        ]
        
        results = self.calculator.find_most_similar_decisions(
            self.semantic_vec1, self.structural_vec1,
            candidate_embeddings, candidate_metadata,
            filters={"category": "credit_approval"}
        )
        
        assert len(results) == 1
        assert results[0]["metadata"]["category"] == "credit_approval"
    
    def test_calculate_context_aware_similarity(self):
        """Test context-aware similarity calculation."""
        candidate_embeddings = [
            (self.semantic_vec2, self.structural_vec2),
            (self.semantic_vec1, self.structural_vec1)
        ]
        
        similarities = self.calculator.calculate_context_aware_similarity(
            self.semantic_vec1, self.structural_vec1,
            candidate_embeddings, context_weight=0.1
        )
        
        assert len(similarities) == 2
        assert all(isinstance(s, float) for s in similarities)
        assert all(0.0 <= s <= 1.0 for s in similarities)
    
    def test_calculate_context_aware_similarity_no_context(self):
        """Test context-aware similarity without context graph."""
        candidate_embeddings = [
            (self.semantic_vec2, self.structural_vec2),
            (self.semantic_vec1, self.structural_vec1)
        ]
        
        similarities = self.calculator.calculate_context_aware_similarity(
            self.semantic_vec1, self.structural_vec1,
            candidate_embeddings, context_weight=0.0
        )
        
        assert len(similarities) == 2
        assert all(isinstance(s, float) for s in similarities)
    
    def test_update_weights(self):
        """Test updating similarity weights."""
        self.calculator.update_weights(0.6, 0.4)
        
        assert self.calculator.semantic_weight == 0.6
        assert self.calculator.structural_weight == 0.4
    
    def test_update_weights_invalid(self):
        """Test updating with invalid weights."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            self.calculator.update_weights(0.8, 0.3)
    
    def test_get_similarity_breakdown(self):
        """Test getting detailed similarity breakdown."""
        breakdown = self.calculator.get_similarity_breakdown(
            self.semantic_vec1, self.structural_vec1,
            self.semantic_vec2, self.structural_vec2
        )
        
        assert "semantic_similarity" in breakdown
        assert "structural_similarity" in breakdown
        assert "hybrid_similarity" in breakdown
        assert "semantic_weight" in breakdown
        assert "structural_weight" in breakdown
        
        assert isinstance(breakdown["semantic_similarity"], float)
        assert isinstance(breakdown["structural_similarity"], float)
        assert isinstance(breakdown["hybrid_similarity"], float)
    
    def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation."""
        # Identical vectors should have similarity 1.0
        similarity = self.calculator._calculate_similarity(
            self.semantic_vec1, self.semantic_vec1, "cosine"
        )
        assert abs(similarity - 1.0) < 1e-10
        
        # Orthogonal vectors should have similarity 0.0
        vec_a = np.array([1.0, 0.0])
        vec_b = np.array([0.0, 1.0])
        similarity = self.calculator._calculate_similarity(vec_a, vec_b, "cosine")
        assert abs(similarity - 0.0) < 1e-10
    
    def test_pearson_similarity_calculation(self):
        """Test Pearson correlation similarity calculation."""
        # Identical vectors should have correlation 1.0
        similarity = self.calculator._calculate_similarity(
            self.semantic_vec1, self.semantic_vec1, "pearson"
        )
        assert abs(similarity - 1.0) < 1e-10
    
    def test_euclidean_similarity_calculation(self):
        """Test Euclidean distance similarity calculation."""
        # Identical vectors should have similarity 1.0
        similarity = self.calculator._calculate_similarity(
            self.semantic_vec1, self.semantic_vec1, "euclidean"
        )
        assert abs(similarity - 1.0) < 1e-10
    
    def test_dot_product_similarity_calculation(self):
        """Test dot product similarity calculation."""
        # Identical normalized vectors should have similarity 1.0
        vec_a = np.array([1.0, 0.0])
        vec_b = np.array([1.0, 0.0])
        similarity = self.calculator._calculate_similarity(vec_a, vec_b, "dot_product")
        assert abs(similarity - 1.0) < 1e-10
    
    def test_apply_filters_exact_match(self):
        """Test applying exact match filters."""
        metadata_list = [
            {"category": "credit_approval", "outcome": "approved"},
            {"category": "credit_approval", "outcome": "rejected"},
            {"category": "fraud_detection", "outcome": "blocked"}
        ]
        
        indices = self.calculator._apply_filters(
            metadata_list, {"category": "credit_approval"}
        )
        
        assert indices == [0, 1]
    
    def test_apply_filters_range_filter(self):
        """Test applying range filters."""
        metadata_list = [
            {"confidence": 0.8},
            {"confidence": 0.6},
            {"confidence": 0.4}
        ]
        
        indices = self.calculator._apply_filters(
            metadata_list, {"confidence": {"min": 0.5}}
        )
        
        assert indices == [0, 1]
    
    def test_apply_filters_list_filter(self):
        """Test applying list membership filters."""
        metadata_list = [
            {"outcome": "approved"},
            {"outcome": "rejected"},
            {"outcome": "escalated"}
        ]
        
        indices = self.calculator._apply_filters(
            metadata_list, {"outcome": ["approved", "rejected"]}
        )
        
        assert indices == [0, 1]
    
    def test_apply_filters_no_matches(self):
        """Test filters with no matches."""
        metadata_list = [
            {"category": "credit_approval"},
            {"category": "fraud_detection"}
        ]
        
        indices = self.calculator._apply_filters(
            metadata_list, {"category": "risk_assessment"}
        )
        
        assert indices == []


class TestHybridSimilarityCalculatorEdgeCases:
    """Test edge cases for HybridSimilarityCalculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = HybridSimilarityCalculator()
    
    def test_zero_vectors(self):
        """Test similarity calculation with zero vectors."""
        vec1 = np.array([0.0, 0.0, 0.0])
        vec2 = np.array([1.0, 1.0, 1.0])
        
        similarity = self.calculator._calculate_similarity(vec1, vec2, "cosine")
        assert similarity == 0.0
    
    def test_single_dimension_vectors(self):
        """Test similarity calculation with single dimension vectors."""
        vec1 = np.array([0.5])
        vec2 = np.array([0.8])
        
        similarity = self.calculator._calculate_similarity(vec1, vec2, "cosine")
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
    
    def test_empty_candidate_list(self):
        """Test batch calculation with empty candidate list."""
        similarities = self.calculator.calculate_batch_hybrid_similarity(
            np.array([0.1, 0.2]), np.array([0.3, 0.4]), [], []
        )
        
        assert similarities == []
    
    def test_mixed_dimension_embeddings(self):
        """Test handling of mixed dimension embeddings."""
        vec1 = np.array([0.1, 0.2])
        vec2 = np.array([0.3, 0.4, 0.5])
        
        # Should handle different dimensions gracefully
        similarity = self.calculator._calculate_similarity(vec1, vec2, "cosine")
        assert isinstance(similarity, float)


if __name__ == "__main__":
    pytest.main([__file__])
