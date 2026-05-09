"""
Test Bridge Axiom Translation Chains

Tests for domain-agnostic bridge axiom functionality across all high-stakes domains.
"""

import pytest
from veritasreason.provenance import ProvenanceManager
from veritasreason.provenance.bridge_axiom import (
    BridgeAxiom,
    TranslationChain,
    create_translation_chain,
    trace_translation_chain
)


class TestBridgeAxiomBasics:
    """Test basic bridge axiom functionality."""
    
    def test_create_bridge_axiom(self):
        """Test creating a bridge axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-TEST-001",
            name="test_axiom",
            rule="Test rule",
            coefficient=0.5,
            source_doi="10.1234/test",
            source_page="Page 1"
        )
        
        assert ba.axiom_id == "BA-TEST-001"
        assert ba.name == "test_axiom"
        assert ba.coefficient == 0.5
        assert ba.confidence == 1.0
    
    def test_bridge_axiom_with_domains(self):
        """Test bridge axiom with input/output domains."""
        ba = BridgeAxiom(
            axiom_id="BA-TEST-002",
            name="domain_test",
            rule="Test rule",
            coefficient=0.75,
            source_doi="10.1234/test",
            source_page="Page 1",
            input_domain="domain_a",
            output_domain="domain_b"
        )
        
        assert ba.input_domain == "domain_a"
        assert ba.output_domain == "domain_b"
    
    def test_bridge_axiom_apply_without_provenance(self):
        """Test applying bridge axiom without provenance manager."""
        ba = BridgeAxiom(
            axiom_id="BA-TEST-003",
            name="apply_test",
            rule="Test rule",
            coefficient=2.0,
            source_doi="10.1234/test",
            source_page="Page 1"
        )
        
        result = ba.apply(
            input_entity="test_entity",
            input_value=10.0
        )
        
        assert result["output_value"] == 20.0
        assert result["input_value"] == 10.0
        assert result["coefficient"] == 2.0
    
    def test_bridge_axiom_apply_with_provenance(self):
        """Test applying bridge axiom with provenance tracking."""
        prov_mgr = ProvenanceManager()
        
        ba = BridgeAxiom(
            axiom_id="BA-TEST-004",
            name="prov_test",
            rule="Test rule",
            coefficient=1.5,
            source_doi="10.1234/test",
            source_page="Page 1"
        )
        
        result = ba.apply(
            input_entity="test_entity",
            input_value=100.0,
            prov_manager=prov_mgr
        )
        
        assert result["output_value"] == 150.0
        assert "output_entity" in result
        
        # Verify provenance was tracked
        lineage = prov_mgr.get_lineage(result["output_entity"])
        assert lineage is not None


class TestDomainSpecificAxioms:
    """Test bridge axioms for different domains."""
    
    def test_blue_finance_axiom(self):
        """Test blue finance domain axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-FINANCE-001",
            name="biomass_tourism_elasticity",
            rule="1% biomass increase → 0.346% tourism revenue increase",
            coefficient=0.346,
            source_doi="10.1038/s41586-021-03371-z",
            source_page="Table S4",
            input_domain="ecological",
            output_domain="financial",
            confidence=0.92
        )
        
        result = ba.apply(
            input_entity="cabo_pulmo_biomass",
            input_value=463
        )
        
        assert result["output_value"] == pytest.approx(160.098, rel=0.01)
        assert result["input_domain"] == "ecological"
        assert result["output_domain"] == "financial"
    
    def test_healthcare_axiom(self):
        """Test healthcare domain axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-HEALTH-001",
            name="fever_influenza_correlation",
            rule="Fever >38°C increases influenza probability by 0.65",
            coefficient=0.65,
            source_doi="10.1001/jama.2020.12345",
            source_page="Table 2",
            input_domain="clinical_observation",
            output_domain="diagnostic_probability",
            confidence=0.85
        )
        
        result = ba.apply(
            input_entity="patient_123_fever",
            input_value=38.5
        )
        
        assert result["output_value"] == pytest.approx(25.025, rel=0.01)
        assert result["confidence"] == 0.85
    
    def test_legal_axiom(self):
        """Test legal domain axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-LEGAL-001",
            name="dna_match_conviction",
            rule="DNA match increases conviction probability by 0.95",
            coefficient=0.95,
            source_doi="10.1016/j.forsciint.2019.12345",
            source_page="Section 4.2",
            input_domain="forensic_evidence",
            output_domain="legal_conclusion",
            confidence=0.98
        )
        
        result = ba.apply(
            input_entity="case_2026_001_dna",
            input_value=1.0
        )
        
        assert result["output_value"] == 0.95
        assert result["confidence"] == 0.98
    
    def test_pharmaceutical_axiom(self):
        """Test pharmaceutical domain axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-PHARMA-001",
            name="dosage_efficacy_relationship",
            rule="10mg increase → 0.15 efficacy improvement",
            coefficient=0.15,
            source_doi="10.1056/NEJMoa2020123",
            source_page="Figure 3",
            input_domain="drug_dosage",
            output_domain="clinical_efficacy",
            confidence=0.88
        )
        
        result = ba.apply(
            input_entity="trial_phase3_dosage",
            input_value=50
        )
        
        assert result["output_value"] == 7.5
        assert result["input_domain"] == "drug_dosage"
        assert result["output_domain"] == "clinical_efficacy"
    
    def test_finance_risk_axiom(self):
        """Test finance risk domain axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-RISK-001",
            name="volatility_risk_correlation",
            rule="1% volatility increase → 0.8 risk score increase",
            coefficient=0.8,
            source_doi="10.1111/jofi.2020.12345",
            source_page="Table 5",
            input_domain="market_volatility",
            output_domain="portfolio_risk",
            confidence=0.91
        )
        
        result = ba.apply(
            input_entity="portfolio_A_volatility",
            input_value=15.3
        )
        
        assert result["output_value"] == pytest.approx(12.24, rel=0.01)
    
    def test_cybersecurity_axiom(self):
        """Test cybersecurity domain axiom."""
        ba = BridgeAxiom(
            axiom_id="BA-SECURITY-001",
            name="anomaly_threat_correlation",
            rule="Anomaly score >0.7 increases threat level by 0.85",
            coefficient=0.85,
            source_doi="10.1109/TDSC.2020.12345",
            source_page="Algorithm 2",
            input_domain="anomaly_detection",
            output_domain="threat_assessment",
            confidence=0.89
        )
        
        result = ba.apply(
            input_entity="network_anomaly",
            input_value=0.82
        )
        
        assert result["output_value"] == pytest.approx(0.697, rel=0.01)


class TestTranslationChains:
    """Test multi-layer translation chains."""
    
    def test_create_translation_chain(self):
        """Test creating a translation chain."""
        chain = TranslationChain(chain_id="chain_001")
        
        assert chain.chain_id == "chain_001"
        assert len(chain.layers) == 0
        assert chain.confidence == 1.0
    
    def test_add_layers_to_chain(self):
        """Test adding layers to translation chain."""
        chain = TranslationChain(chain_id="chain_002")
        
        chain.add_layer("L1", "input", 100, source="doc_1")
        chain.add_layer("L2", "bridge_axiom", 0.5, source="axiom_1")
        chain.add_layer("L3", "output", 50)
        
        assert len(chain.layers) == 3
        assert chain.get_layer("L1")["value"] == 100
        assert chain.get_layer("L2")["value"] == 0.5
        assert chain.get_layer("L3")["value"] == 50
    
    def test_multi_axiom_chain(self):
        """Test translation chain with multiple axioms."""
        prov_mgr = ProvenanceManager()
        
        input_data = {
            "entity_id": "test_input",
            "value": 100,
            "source": "test_source"
        }
        
        axioms = [
            BridgeAxiom(
                axiom_id="BA-001",
                name="axiom_1",
                rule="Test rule 1",
                coefficient=2.0,
                source_doi="10.1234/test1",
                source_page="Page 1"
            ),
            BridgeAxiom(
                axiom_id="BA-002",
                name="axiom_2",
                rule="Test rule 2",
                coefficient=0.5,
                source_doi="10.1234/test2",
                source_page="Page 2"
            )
        ]
        
        chain = create_translation_chain(input_data, axioms, prov_mgr)
        
        assert chain is not None
        assert len(chain.layers) >= 3  # L1 + 2 axioms + final output
        
        # Verify final value: 100 * 2.0 * 0.5 = 100
        final_layer = chain.layers[-1]
        assert final_layer["value"] == 100.0
    
    def test_confidence_propagation(self):
        """Test confidence propagation through chain."""
        prov_mgr = ProvenanceManager()
        
        input_data = {
            "entity_id": "test_input",
            "value": 50,
            "source": "test_source"
        }
        
        axioms = [
            BridgeAxiom(
                axiom_id="BA-001",
                name="axiom_1",
                rule="Test",
                coefficient=1.0,
                source_doi="10.1234/test",
                source_page="Page 1",
                confidence=0.9
            ),
            BridgeAxiom(
                axiom_id="BA-002",
                name="axiom_2",
                rule="Test",
                coefficient=1.0,
                source_doi="10.1234/test",
                source_page="Page 2",
                confidence=0.8
            )
        ]
        
        chain = create_translation_chain(input_data, axioms, prov_mgr)
        
        # Chain confidence should be minimum of all axiom confidences
        assert chain.confidence == 0.8


class TestProvenanceIntegration:
    """Test integration with provenance manager."""
    
    def test_axiom_tracks_provenance(self):
        """Test that applying axiom tracks provenance."""
        prov_mgr = ProvenanceManager()
        
        ba = BridgeAxiom(
            axiom_id="BA-TEST-005",
            name="prov_integration_test",
            rule="Test rule",
            coefficient=1.5,
            source_doi="10.1234/test",
            source_page="Page 1",
            source_quote="Test quote"
        )
        
        result = ba.apply(
            input_entity="input_entity",
            input_value=100,
            prov_manager=prov_mgr
        )
        
        # Check provenance was tracked
        prov = prov_mgr.get_provenance(result["output_entity"])
        assert prov is not None
        assert prov["source_document"] == "10.1234/test"
        assert prov["metadata"]["axiom_id"] == "BA-TEST-005"
    
    def test_chain_tracks_complete_lineage(self):
        """Test that translation chain tracks complete lineage."""
        prov_mgr = ProvenanceManager()
        
        input_data = {
            "entity_id": "lineage_test",
            "value": 75,
            "source": "test_doc"
        }
        
        axioms = [
            BridgeAxiom(
                axiom_id="BA-L1",
                name="layer_1",
                rule="Test",
                coefficient=2.0,
                source_doi="10.1234/l1",
                source_page="P1"
            ),
            BridgeAxiom(
                axiom_id="BA-L2",
                name="layer_2",
                rule="Test",
                coefficient=0.5,
                source_doi="10.1234/l2",
                source_page="P2"
            )
        ]
        
        chain = create_translation_chain(input_data, axioms, prov_mgr)
        
        # Trace lineage
        final_layer = chain.layers[-1]
        final_entity = final_layer.get("entity_id")
        
        if final_entity:
            lineage = prov_mgr.get_lineage(final_entity)
            assert lineage is not None
            assert len(lineage.get("lineage_chain", [])) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_coefficient(self):
        """Test axiom with zero coefficient."""
        ba = BridgeAxiom(
            axiom_id="BA-ZERO",
            name="zero_test",
            rule="Test",
            coefficient=0.0,
            source_doi="10.1234/test",
            source_page="Page 1"
        )
        
        result = ba.apply(
            input_entity="test",
            input_value=100
        )
        
        assert result["output_value"] == 0.0
    
    def test_negative_coefficient(self):
        """Test axiom with negative coefficient."""
        ba = BridgeAxiom(
            axiom_id="BA-NEG",
            name="negative_test",
            rule="Test",
            coefficient=-0.5,
            source_doi="10.1234/test",
            source_page="Page 1"
        )
        
        result = ba.apply(
            input_entity="test",
            input_value=100
        )
        
        assert result["output_value"] == -50.0
    
    def test_large_coefficient(self):
        """Test axiom with large coefficient."""
        ba = BridgeAxiom(
            axiom_id="BA-LARGE",
            name="large_test",
            rule="Test",
            coefficient=1000.0,
            source_doi="10.1234/test",
            source_page="Page 1"
        )
        
        result = ba.apply(
            input_entity="test",
            input_value=5
        )
        
        assert result["output_value"] == 5000.0
    
    def test_axiom_to_dict(self):
        """Test converting axiom to dictionary."""
        ba = BridgeAxiom(
            axiom_id="BA-DICT",
            name="dict_test",
            rule="Test rule",
            coefficient=1.5,
            source_doi="10.1234/test",
            source_page="Page 1",
            input_domain="domain_a",
            output_domain="domain_b"
        )
        
        data = ba.to_dict()
        
        assert data["axiom_id"] == "BA-DICT"
        assert data["name"] == "dict_test"
        assert data["coefficient"] == 1.5
        assert data["input_domain"] == "domain_a"
        assert data["output_domain"] == "domain_b"
    
    def test_chain_to_dict(self):
        """Test converting chain to dictionary."""
        chain = TranslationChain(chain_id="chain_dict")
        chain.add_layer("L1", "input", 100)
        
        data = chain.to_dict()
        
        assert data["chain_id"] == "chain_dict"
        assert len(data["layers"]) == 1
        assert data["confidence"] == 1.0
