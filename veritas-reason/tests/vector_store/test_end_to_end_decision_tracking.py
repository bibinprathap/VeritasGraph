"""
End-to-End Decision Tracking Tests

This module contains comprehensive end-to-end tests for the enhanced vector store
decision tracking functionality, testing real-world scenarios and use cases.

Test Scenarios:
    - Credit approval decisions with hybrid search
    - Fraud detection decisions with multi-hop reasoning
    - Risk assessment decisions with context expansion
    - Batch processing of multiple decisions
    - Explainable AI with path tracing
    - Performance under load
    - Error handling and fallbacks
"""

import pytest
import numpy as np
import time
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from veritasreason.vector_store import VectorStore, DecisionEmbeddingPipeline, HybridSimilarityCalculator
from veritasreason.context import DecisionContext, ContextRetriever
from veritasreason.vector_store.decision_vector_methods import (
    quick_decision, find_precedents, explain, similar_to, batch_decisions,
    filter_decisions, get_decision_context, search_by_entities
)


class TestEndToEndDecisionTracking:
    """End-to-end tests for decision tracking functionality."""
    
    def setup_method(self):
        """Set up test environment with real data."""
        self.vector_store = VectorStore(backend="inmemory", dimension=384)
        
        # Real-world decision scenarios
        self.credit_decisions = [
            {
                "scenario": "Credit limit increase request for premium customer",
                "reasoning": "Customer has excellent payment history and high credit score",
                "outcome": "approved",
                "confidence": 0.92,
                "entities": ["customer_12345", "premium_segment", "credit_card"],
                "category": "credit_approval",
                "amount": 50000,
                "risk_level": "low"
            },
            {
                "scenario": "Credit limit increase for high-risk customer",
                "reasoning": "Customer has recent late payments and high credit utilization",
                "outcome": "rejected",
                "confidence": 0.85,
                "entities": ["customer_67890", "high_risk_segment", "credit_card"],
                "category": "credit_approval",
                "amount": 25000,
                "risk_level": "high"
            },
            {
                "scenario": "Credit limit increase for medium-risk customer",
                "reasoning": "Customer has mixed payment history, requires manual review",
                "outcome": "escalated",
                "confidence": 0.75,
                "entities": ["customer_11111", "medium_risk_segment", "credit_card"],
                "category": "credit_approval",
                "amount": 15000,
                "risk_level": "medium"
            }
        ]
        
        self.fraud_decisions = [
            {
                "scenario": "Suspicious transaction pattern detected",
                "reasoning": "Multiple transactions from different locations in short time",
                "outcome": "blocked",
                "confidence": 0.95,
                "entities": ["transaction_999", "customer_12345", "location_ny", "location_ca"],
                "category": "fraud_detection",
                "transaction_amount": 12500,
                "fraud_indicators": ["velocity_exceeded", "location_anomaly"]
            },
            {
                "scenario": "Unusual login pattern detected",
                "reasoning": "Login from new device and location",
                "outcome": "flagged_for_review",
                "confidence": 0.78,
                "entities": ["customer_67890", "device_new", "location_overseas"],
                "category": "fraud_detection",
                "transaction_amount": 0,
                "fraud_indicators": ["new_device", "overseas_access"]
            }
        ]
        
        self.risk_decisions = [
            {
                "scenario": "Loan application risk assessment",
                "reasoning": "Applicant has stable income but high debt-to-income ratio",
                "outcome": "approved_with_conditions",
                "confidence": 0.82,
                "entities": ["applicant_555", "loan_mortgage", "income_verified"],
                "category": "risk_assessment",
                "loan_amount": 250000,
                "risk_score": 650
            },
            {
                "scenario": "Investment risk evaluation",
                "reasoning": "High-risk investment requested by conservative investor",
                "outcome": "rejected",
                "confidence": 0.88,
                "entities": ["investor_777", "investment_crypto", "profile_conservative"],
                "category": "risk_assessment",
                "investment_amount": 10000,
                "risk_score": 880
            }
        ]
    
    def test_credit_approval_workflow_end_to_end(self):
        """Test complete credit approval workflow."""
        print("\n=== Testing Credit Approval Workflow ===")
        
        # Step 1: Initialize DecisionContext
        context = DecisionContext(vector_store=self.vector_store, graph_store=None)
        print("PASS: DecisionContext initialized")
        
        # Step 2: Record credit decisions
        decision_ids = []
        for decision in self.credit_decisions:
            decision_id = context.record_decision(**decision)
            decision_ids.append(decision_id)
            print(f"PASS: Recorded decision: {decision['outcome']} ({decision_id})")
        
        # Step 3: Find similar decisions for new scenario
        precedents = context.find_similar_decisions(
            scenario="Credit limit increase for customer with good payment history",
            limit=5,
            use_hybrid_search=True,
            semantic_weight=0.7,
            structural_weight=0.3
        )
        print(f"PASS: Found {len(precedents)} similar decisions")
        
        # Step 4: Verify precedent quality
        assert len(precedents) > 0, "Should find similar decisions"
        assert all(p.score > 0.0 for p in precedents), "All precedents should have scores"
        print(f"PASS: Precedent scores: {[round(p.score, 2) for p in precedents]}")
        
        # Step 5: Get decision context
        context_info = context.get_decision_context(
            decision_ids[0],
            depth=2,
            include_entities=True,
            include_policies=True
        )
        print(f"PASS: Decision context retrieved with {len(context_info)} components")
        
        # Step 6: Explain decision
        explanation = context.explain_decision(decision_ids[0])
        assert "scenario" in explanation, "Explanation should include scenario"
        assert "reasoning" in explanation, "Explanation should include reasoning"
        print(f"PASS: Decision explanation generated: {explanation['scenario'][:50]}...")
        
        print("PASS: Credit approval workflow completed successfully")
    
    def test_fraud_detection_workflow_end_to_end(self):
        """Test complete fraud detection workflow."""
        print("\n=== Testing Fraud Detection Workflow ===")
        
        # Step 1: Record fraud decisions using convenience functions
        fraud_ids = []
        for decision in self.fraud_decisions:
            decision_id = quick_decision(
                scenario=decision["scenario"],
                reasoning=decision["reasoning"],
                outcome=decision["outcome"],
                confidence=decision["confidence"],
                entities=decision["entities"],
                category=decision["category"]
            )
            fraud_ids.append(decision_id)
            print(f"✅ Quick decision recorded: {decision['outcome']} ({decision_id})")
        
        # Step 2: Find fraud precedents
        fraud_precedents = find_precedents(
            "Suspicious transaction activity",
            limit=3,
            filters={"category": "fraud_detection"}
        )
        print(f"✅ Found {len(fraud_precedents)} fraud precedents")
        
        # Step 3: Search by entities
        entity_decisions = search_by_entities(["customer_12345"], limit=5)
        print(f"✅ Found {len(entity_decisions)} decisions for customer_12345")
        
        # Step 4: Batch process new fraud scenarios
        new_fraud_scenarios = [
            {"scenario": "Multiple failed login attempts", "outcome": "blocked"},
            {"scenario": "Unusual spending pattern", "outcome": "flagged"},
            {"scenario": "Account takeover attempt", "outcome": "blocked"}
        ]
        batch_results = batch_decisions(new_fraud_scenarios)
        print(f"✅ Batch processed {len(batch_results)} fraud decisions")
        
        # Step 5: Filter decisions by criteria
        filtered = filter_decisions(
            category="fraud_detection",
            confidence_min=0.8,
            outcome="blocked"
        )
        print(f"✅ Filtered {len(filtered)} high-confidence blocked decisions")
        
        print("✅ Fraud detection workflow completed successfully")
    
    def test_hybrid_search_performance(self):
        """Test hybrid search performance with different weights."""
        print("\n=== Testing Hybrid Search Performance ===")
        
        # Record all test decisions
        all_decisions = self.credit_decisions + self.fraud_decisions + self.risk_decisions
        context = DecisionContext(vector_store=self.vector_store, graph_store=None)
        
        for decision in all_decisions:
            context.record_decision(**decision)
        
        print(f"✅ Recorded {len(all_decisions)} decisions")
        
        # Test different weight configurations
        weight_configs = [
            (0.9, 0.1),  # Heavy semantic
            (0.5, 0.5),  # Balanced
            (0.1, 0.9),  # Heavy structural
        ]
        
        for sem_weight, struct_weight in weight_configs:
            start_time = time.time()
            
            precedents = context.find_similar_decisions(
                scenario="Credit limit increase request",
                limit=5,
                semantic_weight=sem_weight,
                structural_weight=struct_weight
            )
            
            search_time = time.time() - start_time
            print(f"✅ Semantic:{sem_weight} Structural:{struct_weight} - "
                  f"{len(precedents)} results in {search_time:.3f}s")
            
            # Verify results are reasonable
            assert len(precedents) > 0, "Should find results for all weight configs"
            assert all(0 <= p.score <= 1 for p in precedents), "Scores should be valid"
    
    def test_explainable_ai_features(self):
        """Test explainable AI features with path tracing."""
        print("\n=== Testing Explainable AI Features ===")
        
        # Record decisions
        context = DecisionContext(vector_store=self.vector_store, graph_store=None)
        decision_id = context.record_decision(**self.credit_decisions[0])
        
        # Test comprehensive explanation
        explanation = context.explain_decision(
            decision_id,
            include_paths=True,
            include_confidence=True,
            include_weights=True
        )
        
        print(f"✅ Generated explanation with {len(explanation)} components")
        
        # Verify explanation components
        required_components = ["decision_id", "scenario", "reasoning", "outcome"]
        for component in required_components:
            assert component in explanation, f"Missing component: {component}"
        
        # Verify confidence and weights
        if "confidence" in explanation:
            assert 0 <= explanation["confidence"] <= 1, "Confidence should be valid"
        
        if "semantic_weight" in explanation:
            assert 0 <= explanation["semantic_weight"] <= 1, "Semantic weight should be valid"
        
        print("✅ Explainable AI features working correctly")
    
    def test_batch_processing_performance(self):
        """Test batch processing performance with large datasets."""
        print("\n=== Testing Batch Processing Performance ===")
        
        # Generate large batch of decisions
        large_batch = []
        for i in range(100):
            large_batch.append({
                "scenario": f"Decision {i}: Credit limit assessment",
                "reasoning": f"Automated assessment for customer {i}",
                "outcome": "approved" if i % 3 != 0 else "rejected",
                "confidence": 0.7 + (i % 10) * 0.03,
                "entities": [f"customer_{i}", "credit_card"],
                "category": "credit_approval"
            })
        
        # Test batch processing
        start_time = time.time()
        batch_results = self.vector_store.process_decision_batch(large_batch, batch_size=20)
        processing_time = time.time() - start_time
        
        print(f"✅ Processed {len(batch_results)} decisions in {processing_time:.3f}s")
        print(f"✅ Average time per decision: {processing_time/len(batch_results)*1000:.2f}ms")
        
        # Verify all decisions processed
        assert len(batch_results) == len(large_batch), "All decisions should be processed"
        assert all("vector_id" in result for result in batch_results), "All should have vector IDs"
        
        # Performance should be reasonable
        avg_time_per_decision = processing_time / len(batch_results)
        assert avg_time_per_decision < 0.5, "Should process decisions quickly (<500ms each)"
    
    def test_context_retriever_integration(self):
        """Test ContextRetriever integration with decision tracking."""
        print("\n=== Testing ContextRetriever Integration ===")
        
        # Record decisions
        context = DecisionContext(vector_store=self.vector_store, graph_store=None)
        for decision in self.credit_decisions:
            context.record_decision(**decision)
        
        # Initialize ContextRetriever
        retriever = ContextRetriever(vector_store=self.vector_store, knowledge_graph=None)
        print("✅ ContextRetriever initialized")
        
        # Test decision precedent retrieval
        precedents = retriever.retrieve_decision_precedents(
            query="Credit limit increase for premium customer",
            limit=5,
            use_hybrid_search=True,
            include_context=True
        )
        print(f"✅ Retrieved {len(precedents)} precedents")
        
        # Test query decisions
        queried = retriever.query_decisions(
            query="high-risk credit decisions",
            max_hops=2,
            include_context=True,
            use_hybrid_search=False
        )
        print(f"✅ Queried {len(queried)} decisions")
        
        # Verify results
        assert len(precedents) > 0, "Should find precedents"
        assert len(queried) > 0, "Should find queried decisions"
        assert all(hasattr(p, 'content') for p in precedents), "Precedents should have content"
        assert all(hasattr(q, 'content') for q in queried), "Queried decisions should have content"
    
    def test_error_handling_and_fallbacks(self):
        """Test error handling and graceful fallbacks."""
        print("\n=== Testing Error Handling and Fallbacks ===")
        
        # Test with invalid decision data
        try:
            context = DecisionContext(vector_store=self.vector_store, graph_store=None)
            
            # Missing required field
            with pytest.raises(ValueError):
                context.record_decision(reasoning="test")  # Missing scenario
            
            print("✅ Properly handles missing required fields")
            
            # Test with None graph store
            decision_id = context.record_decision(
                scenario="Test decision",
                reasoning="Test reasoning",
                outcome="approved"
            )
            print("✅ Handles None graph store gracefully")
            
            # Test explanation for non-existent decision
            with pytest.raises(ValueError):
                context.explain_decision("non_existent_id")
            
            print("✅ Properly handles non-existent decisions")
            
        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")
    
    def test_backward_compatibility_stress_test(self):
        """Test backward compatibility under stress."""
        print("\n=== Testing Backward Compatibility Stress Test ===")
        
        # Mix old and new functionality
        old_style_vectors = [[0.1, 0.2, 0.3, 0.4] for _ in range(50)]
        old_style_metadata = [{"type": "document", "source": "test"} for _ in range(50)]
        
        # Store old-style vectors
        old_ids = self.vector_store.store_vectors(old_style_vectors, old_style_metadata)
        print(f"✅ Stored {len(old_ids)} old-style vectors")
        
        # Record new-style decisions
        context = DecisionContext(vector_store=self.vector_store, graph_store=None)
        for decision in self.credit_decisions[:2]:
            context.record_decision(**decision)
        
        # Search should work for both
        old_results = self.vector_store.search_vectors([0.1, 0.2, 0.3, 0.4], limit=10)
        new_results = context.find_similar_decisions("Credit limit increase", limit=5)
        
        print(f"✅ Old-style search: {len(old_results)} results")
        print(f"✅ New-style search: {len(new_results)} results")
        
        # Verify both work
        assert len(old_results) > 0, "Old-style search should work"
        assert len(new_results) > 0, "New-style search should work"
        
        # Verify no interference
        total_vectors = len(self.vector_store.vectors)
        expected_total = len(old_ids) + len(self.credit_decisions[:2])
        assert total_vectors == expected_total, "Total vectors should match sum"
        
        print("✅ Backward compatibility maintained under stress")


class TestRealWorldScenarios:
    """Test real-world decision tracking scenarios."""
    
    def setup_method(self):
        """Set up real-world test environment."""
        self.vector_store = VectorStore(backend="inmemory", dimension=384)
        self.context = DecisionContext(vector_store=self.vector_store, graph_store=None)
    
    def test_banking_credit_decisions(self):
        """Test realistic banking credit decisions."""
        print("\n=== Testing Banking Credit Decisions ===")
        
        # Realistic credit decisions
        banking_decisions = [
            {
                "scenario": "Mortgage application approval for first-time homebuyer",
                "reasoning": "Strong credit score (750), stable employment, 20% down payment, low DTI ratio",
                "outcome": "approved",
                "confidence": 0.94,
                "entities": ["applicant_1001", "mortgage_30yr", "property_123", "bank_chase"],
                "category": "mortgage_approval",
                "loan_amount": 350000,
                "credit_score": 750,
                "dti_ratio": 0.28
            },
            {
                "scenario": "Business line of credit denial for startup",
                "reasoning": "Limited operating history (6 months), insufficient collateral, high industry risk",
                "outcome": "rejected",
                "confidence": 0.87,
                "entities": ["business_startup", "credit_line_50k", "industry_tech"],
                "category": "business_credit",
                "loan_amount": 50000,
                "operating_months": 6,
                "collateral_value": 5000
            },
            {
                "scenario": "Credit card limit increase for loyal customer",
                "reasoning": "12-year relationship, perfect payment history, increased income, low utilization",
                "outcome": "approved",
                "confidence": 0.91,
                "entities": ["customer_loyal", "credit_card_platinum", "income_verified"],
                "category": "credit_card",
                "current_limit": 10000,
                "requested_limit": 25000,
                "payment_history": "perfect"
            }
        ]
        
        # Record decisions
        decision_ids = []
        for decision in banking_decisions:
            decision_id = self.context.record_decision(**decision)
            decision_ids.append(decision_id)
            print(f"✅ Recorded: {decision['category']} - {decision['outcome']}")
        
        # Test scenario-based search
        mortgage_precedents = self.context.find_similar_decisions(
            scenario="Mortgage application with good credit score",
            limit=3,
            filters={"category": "mortgage_approval"}
        )
        print(f"✅ Found {len(mortgage_precedents)} mortgage precedents")
        
        # Test entity-based search
        customer_decisions = search_by_entities(["customer_loyal"], limit=5)
        print(f"✅ Found {len(customer_decisions)} decisions for loyal customer")
        
        # Test filtering by financial criteria
        high_value_decisions = filter_decisions(
            category="credit_approval",
            loan_amount_min=100000
        )
        print(f"✅ Found {len(high_value_decisions)} high-value decisions")
        
        # Verify business logic
        assert len(mortgage_precedents) > 0, "Should find mortgage precedents"
        assert any(d['outcome'] == 'approved' for d in banking_decisions), "Should have approvals"
        assert any(d['outcome'] == 'rejected' for d in banking_decisions), "Should have rejections"
    
    def test_insurance_claims_processing(self):
        """Test insurance claims decision processing."""
        print("\n=== Testing Insurance Claims Processing ===")
        
        insurance_decisions = [
            {
                "scenario": "Auto insurance claim approval for minor accident",
                "reasoning": "Clear liability, reasonable repair costs, no prior claims, policy active",
                "outcome": "approved",
                "confidence": 0.96,
                "entities": ["claim_auto_001", "driver_safe", "policy_active", "repair_shop"],
                "category": "auto_insurance",
                "claim_amount": 2500,
                "prior_claims": 0,
                "liability_clear": True
            },
            {
                "scenario": "Home insurance claim investigation for water damage",
                "reasoning": "Suspicious timing (recent policy purchase), extensive damage, requires expert assessment",
                "outcome": "under_investigation",
                "confidence": 0.72,
                "entities": ["claim_home_002", "policy_new", "damage_water", "adjuster_assigned"],
                "category": "home_insurance",
                "claim_amount": 15000,
                "policy_age_days": 45,
                "requires_investigation": True
            },
            {
                "scenario": "Health insurance claim denial for experimental treatment",
                "reasoning": "Treatment not FDA approved, outside coverage scope, no medical necessity",
                "outcome": "rejected",
                "confidence": 0.89,
                "entities": ["claim_health_003", "treatment_experimental", "policy_hmo"],
                "category": "health_insurance",
                "claim_amount": 50000,
                "fda_approved": False,
                "coverage_exclusion": True
            }
        ]
        
        # Record insurance decisions
        for decision in insurance_decisions:
            decision_id = self.context.record_decision(**decision)
            print(f"✅ Recorded: {decision['category']} - {decision['outcome']}")
        
        # Test claims analysis
        auto_claims = filter_decisions(category="auto_insurance", outcome="approved")
        print(f"✅ Found {len(auto_claims)} approved auto claims")
        
        # Test investigation cases
        investigations = filter_decisions(outcome="under_investigation")
        print(f"✅ Found {len(investigations)} cases under investigation")
        
        # Test high-value claims
        high_value_claims = filter_decisions(claim_amount_min=10000)
        print(f"✅ Found {len(high_value_claims)} high-value claims")
        
        # Verify insurance logic
        assert len(auto_claims) > 0, "Should have approved auto claims"
        assert len(investigations) > 0, "Should have investigations"
        assert len(high_value_claims) >= 2, "Should have high-value claims"
    
    def test_healthcare_triage_decisions(self):
        """Test healthcare triage and medical decisions."""
        print("\n=== Testing Healthcare Triage Decisions ===")
        
        healthcare_decisions = [
            {
                "scenario": "Emergency room admission for chest pain",
                "reasoning": "Chest pain with EKG changes, immediate cardiac workup needed, high risk factors",
                "outcome": "admitted_emergency",
                "confidence": 0.98,
                "entities": ["patient_456", "symptom_chest_pain", "ekg_abnormal", "cardiology"],
                "category": "emergency_triage",
                "urgency_level": "critical",
                "vital_signs": "abnormal",
                "cardiac_markers": "elevated"
            },
            {
                "scenario": "Outpatient referral for specialist consultation",
                "reasoning": "Chronic condition management, primary care exhausted options, specialist expertise needed",
                "outcome": "referral_approved",
                "confidence": 0.85,
                "entities": ["patient_789", "condition_chronic", "specialist_endocrinology"],
                "category": "outpatient_care",
                "urgency_level": "routine",
                "wait_time_days": 14,
                "insurance_coverage": True
            },
            {
                "scenario": "Surgical consultation denied for elective procedure",
                "reasoning": "Medical necessity not established, conservative treatment preferred, risks outweigh benefits",
                "outcome": "denied",
                "confidence": 0.91,
                "entities": ["patient_321", "procedure_elective", "surgeon_consult"],
                "category": "surgical_screening",
                "urgency_level": "elective",
                "medical_necessity": False,
                "alternative_available": True
            }
        ]
        
        # Record healthcare decisions
        for decision in healthcare_decisions:
            decision_id = self.context.record_decision(**decision)
            print(f"✅ Recorded: {decision['category']} - {decision['outcome']}")
        
        # Test emergency triage
        emergency_cases = filter_decisions(
            category="emergency_triage",
            urgency_level="critical"
        )
        print(f"✅ Found {len(emergency_cases)} critical emergency cases")
        
        # Test referral patterns
        referrals = filter_decisions(outcome="referral_approved")
        print(f"✅ Found {len(referrals)} approved referrals")
        
        # Test denial reasons
        denials = filter_decisions(outcome="denied")
        print(f"✅ Found {len(denials)} denied procedures")
        
        # Verify healthcare logic
        assert len(emergency_cases) > 0, "Should have emergency cases"
        assert len(referrals) > 0, "Should have referrals"
        assert len(denials) > 0, "Should have denials"


if __name__ == "__main__":
    # Run end-to-end tests
    pytest.main([__file__, "-v", "-s"])
