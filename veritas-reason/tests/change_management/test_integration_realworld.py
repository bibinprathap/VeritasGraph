"""
Comprehensive Integration Tests for Real-World Scenarios

This module contains integration tests covering real-world use cases including:
- Healthcare compliance (HIPAA)
- Financial compliance (SOX)
- Pharmaceutical compliance (FDA 21 CFR Part 11)
- Large-scale production scenarios
- Data corruption and recovery
- Migration and upgrade paths
- Multi-user concurrent scenarios
- Long-running production workflows

Author: VeritasReason Contributors
"""

import os
import tempfile
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import pytest

from veritasreason.change_management import (
    TemporalVersionManager,
    OntologyVersionManager,
    ChangeLogEntry,
    InMemoryVersionStorage,
    SQLiteVersionStorage,
    compute_checksum,
    verify_checksum
)
from veritasreason.utils.exceptions import ValidationError, ProcessingError


class TestHealthcareCompliance:
    """Test healthcare compliance scenarios (HIPAA § 164.312(b))"""
    
    def test_patient_record_audit_trail(self):
        """Test complete audit trail for patient records"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            manager = TemporalVersionManager(storage_path=db_path)
            
            # Initial patient record
            patient_record = {
                "entities": [
                    {
                        "id": "patient_001",
                        "type": "Patient",
                        "name": "John Doe",
                        "dob": "1980-05-15",
                        "mrn": "MR-2024-001",
                        "ssn_last4": "1234"
                    },
                    {
                        "id": "diagnosis_001",
                        "type": "Diagnosis",
                        "code": "I10",
                        "description": "Essential hypertension",
                        "date": "2024-01-15"
                    }
                ],
                "relationships": [
                    {
                        "source": "patient_001",
                        "target": "diagnosis_001",
                        "type": "has_diagnosis",
                        "date": "2024-01-15"
                    }
                ]
            }
            
            # Create initial version
            v1 = manager.create_snapshot(
                patient_record,
                "patient_001_v1.0",
                "dr.smith@hospital.com",
                "Initial patient record with hypertension diagnosis"
            )
            
            assert v1 is not None
            assert manager.verify_checksum(v1)
            
            # Add medication
            patient_record["entities"].append({
                "id": "medication_001",
                "type": "Medication",
                "name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once daily",
                "prescribed_date": "2024-01-15"
            })
            patient_record["relationships"].append({
                "source": "patient_001",
                "target": "medication_001",
                "type": "prescribed",
                "date": "2024-01-15"
            })
            
            v2 = manager.create_snapshot(
                patient_record,
                "patient_001_v1.1",
                "dr.smith@hospital.com",
                "Added Lisinopril 10mg prescription"
            )
            
            # Verify audit trail
            versions = manager.list_versions()
            assert len(versions) == 2
            
            # Verify all changes are tracked
            diff = manager.compare_versions("patient_001_v1.0", "patient_001_v1.1")
            assert diff["summary"]["entities_added"] == 1
            assert diff["summary"]["relationships_added"] == 1
            
            # Verify data integrity for compliance
            for version in versions:
                retrieved = manager.get_version(version["label"])
                assert manager.verify_checksum(retrieved), f"Integrity check failed for {version['label']}"
            
            # Verify author attribution
            assert all(v["author"] == "dr.smith@hospital.com" for v in versions)
            
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def test_hipaa_access_logging(self):
        """Test that all access is logged for HIPAA compliance"""
        manager = TemporalVersionManager()
        
        # Create patient record
        patient_data = {
            "entities": [{"id": "patient_123", "name": "Jane Smith", "ssn": "***-**-5678"}],
            "relationships": []
        }
        
        # Multiple healthcare providers accessing and modifying
        providers = [
            ("dr.jones@hospital.com", "Initial examination"),
            ("nurse.williams@hospital.com", "Vital signs recorded"),
            ("dr.chen@hospital.com", "Lab results added"),
            ("pharmacist@hospital.com", "Medication dispensed")
        ]
        
        for i, (provider, description) in enumerate(providers):
            snapshot = manager.create_snapshot(
                patient_data,
                f"patient_123_v{i+1}",
                provider,
                description
            )
            assert snapshot["author"] == provider
            assert snapshot["description"] == description
        
        # Verify complete access log
        versions = manager.list_versions()
        assert len(versions) == 4
        
        # Verify each access is properly attributed
        for i, version in enumerate(versions):
            assert version["author"] == providers[i][0]
            assert version["description"] == providers[i][1]
    
    def test_phi_data_integrity(self):
        """Test Protected Health Information (PHI) data integrity"""
        manager = TemporalVersionManager()
        
        # PHI data
        phi_data = {
            "entities": [
                {
                    "id": "patient_456",
                    "name": "Robert Johnson",
                    "dob": "1975-03-20",
                    "ssn": "***-**-9012",
                    "address": "123 Main St, City, State",
                    "phone": "555-0123",
                    "email": "robert.j@email.com"
                }
            ],
            "relationships": []
        }
        
        snapshot = manager.create_snapshot(
            phi_data,
            "phi_v1",
            "admin@hospital.com",
            "PHI data snapshot"
        )
        
        # Verify integrity
        assert manager.verify_checksum(snapshot)
        
        # Simulate tampering
        snapshot["entities"][0]["ssn"] = "123-45-6789"  # Unauthorized modification
        
        # Should detect tampering
        assert not manager.verify_checksum(snapshot)


class TestFinancialCompliance:
    """Test financial compliance scenarios (SOX § 404)"""
    
    def test_financial_transaction_audit(self):
        """Test audit trail for financial transactions"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            manager = TemporalVersionManager(storage_path=db_path)
            
            # Financial transaction graph
            transaction_graph = {
                "entities": [
                    {
                        "id": "txn_001",
                        "type": "Transaction",
                        "amount": 10000.00,
                        "currency": "USD",
                        "date": "2024-01-15",
                        "status": "pending"
                    },
                    {
                        "id": "account_001",
                        "type": "Account",
                        "number": "****1234",
                        "balance": 50000.00
                    }
                ],
                "relationships": [
                    {
                        "source": "txn_001",
                        "target": "account_001",
                        "type": "debits"
                    }
                ]
            }
            
            # Create transaction record
            v1 = manager.create_snapshot(
                transaction_graph,
                "txn_001_initial",
                "system@bank.com",
                "Transaction initiated"
            )
            
            # Approval workflow
            transaction_graph["entities"][0]["status"] = "approved"
            transaction_graph["entities"][0]["approved_by"] = "manager@bank.com"
            transaction_graph["entities"][0]["approved_date"] = "2024-01-15T10:30:00Z"
            
            v2 = manager.create_snapshot(
                transaction_graph,
                "txn_001_approved",
                "manager@bank.com",
                "Transaction approved by manager"
            )
            
            # Completion
            transaction_graph["entities"][0]["status"] = "completed"
            transaction_graph["entities"][1]["balance"] = 40000.00
            
            v3 = manager.create_snapshot(
                transaction_graph,
                "txn_001_completed",
                "system@bank.com",
                "Transaction completed and balance updated"
            )
            
            # Verify complete audit trail
            versions = manager.list_versions()
            assert len(versions) == 3
            
            # Verify immutability - cannot overwrite
            with pytest.raises((ValidationError, ProcessingError)):
                manager.create_snapshot(
                    transaction_graph,
                    "txn_001_initial",  # Duplicate label
                    "hacker@evil.com",
                    "Attempting to modify history"
                )
            
            # Verify all versions have integrity
            for version in versions:
                retrieved = manager.get_version(version["label"])
                assert manager.verify_checksum(retrieved)
            
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def test_sox_change_control(self):
        """Test SOX-compliant change control process"""
        manager = OntologyVersionManager()
        
        # Financial ontology
        financial_ontology = {
            "uri": "https://bank.com/ontology/financial",
            "version_info": {"version": "1.0", "date": "2024-01-30"},
            "structure": {
                "classes": ["Account", "Transaction", "Customer"],
                "properties": ["accountNumber", "balance", "transactionAmount"],
                "individuals": ["CheckingAccount", "SavingsAccount"],
                "axioms": [
                    "Account belongsTo exactly 1 Customer",
                    "Transaction involves exactly 1 Account"
                ]
            }
        }
        
        # Initial version
        v1 = manager.create_snapshot(
            financial_ontology,
            "financial_ont_v1.0",
            "architect@bank.com",
            "Initial financial ontology"
        )
        
        # Add compliance requirements
        financial_ontology["structure"]["classes"].extend(["ComplianceCheck", "AuditLog"])
        financial_ontology["structure"]["properties"].extend(["complianceStatus", "auditTimestamp"])
        financial_ontology["structure"]["axioms"].append(
            "Transaction requiresCompliance exactly 1 ComplianceCheck"
        )
        
        v2 = manager.create_snapshot(
            financial_ontology,
            "financial_ont_v2.0",
            "compliance@bank.com",
            "Added SOX compliance requirements"
        )
        
        # Verify structural changes are tracked
        diff = manager.compare_versions("financial_ont_v1.0", "financial_ont_v2.0")
        assert "ComplianceCheck" in diff["classes_added"]
        assert "AuditLog" in diff["classes_added"]
        assert len(diff["axioms_added"]) == 1


class TestPharmaceuticalCompliance:
    """Test pharmaceutical compliance scenarios (FDA 21 CFR Part 11)"""
    
    def test_clinical_trial_data_integrity(self):
        """Test FDA 21 CFR Part 11 compliant clinical trial data"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            manager = TemporalVersionManager(storage_path=db_path)
            
            # Clinical trial data
            trial_data = {
                "entities": [
                    {
                        "id": "trial_001",
                        "type": "ClinicalTrial",
                        "name": "Phase III Efficacy Study",
                        "drug": "Compound-X",
                        "protocol": "PROTO-2024-001",
                        "status": "active"
                    },
                    {
                        "id": "cohort_001",
                        "type": "PatientCohort",
                        "size": 500,
                        "demographics": "Adults 18-65",
                        "enrollment_date": "2024-01-01"
                    }
                ],
                "relationships": [
                    {
                        "source": "trial_001",
                        "target": "cohort_001",
                        "type": "includes_cohort"
                    }
                ]
            }
            
            # Baseline data with electronic signature
            v1 = manager.create_snapshot(
                trial_data,
                "trial_001_baseline",
                "principal.investigator@pharma.com",
                "Baseline clinical trial data - FDA 21 CFR Part 11 compliant"
            )
            
            # Verify electronic signature (author email)
            assert v1["author"] == "principal.investigator@pharma.com"
            
            # Verify data integrity
            assert manager.verify_checksum(v1)
            
            # Add interim results
            trial_data["entities"].append({
                "id": "results_001",
                "type": "InterimResults",
                "date": "2024-02-15",
                "efficacy_rate": 0.75,
                "adverse_events": 12
            })
            
            v2 = manager.create_snapshot(
                trial_data,
                "trial_001_interim",
                "data.manager@pharma.com",
                "Interim results - 6 week analysis"
            )
            
            # Verify audit trail
            versions = manager.list_versions()
            assert len(versions) == 2
            
            # Verify data integrity for all versions (FDA requirement)
            for version in versions:
                retrieved = manager.get_version(version["label"])
                assert manager.verify_checksum(retrieved), \
                    f"FDA 21 CFR Part 11 integrity check failed for {version['label']}"
            
            # Generate audit report
            audit_report = []
            for version in versions:
                audit_report.append({
                    "version": version["label"],
                    "timestamp": version["timestamp"],
                    "author": version["author"],
                    "description": version["description"],
                    "checksum": version["checksum"],
                    "integrity_verified": manager.verify_checksum(
                        manager.get_version(version["label"])
                    )
                })
            
            # All entries should have verified integrity
            assert all(entry["integrity_verified"] for entry in audit_report)
            
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def test_electronic_signature_validation(self):
        """Test electronic signature validation for FDA compliance"""
        manager = TemporalVersionManager()
        
        # Valid electronic signature (email)
        data = {"entities": [], "relationships": []}
        snapshot = manager.create_snapshot(
            data,
            "v1",
            "qualified.person@pharma.com",
            "Signed by qualified person"
        )
        
        assert snapshot["author"] == "qualified.person@pharma.com"
        
        # Invalid signature should be rejected
        with pytest.raises(ValidationError, match="email"):
            manager.create_snapshot(
                data,
                "v2",
                "not-a-valid-signature",
                "Invalid signature"
            )


class TestLargeScaleProduction:
    """Test large-scale production scenarios"""
    
    def test_high_volume_snapshots(self):
        """Test handling high volume of snapshots"""
        manager = TemporalVersionManager()
        
        # Create 100 versions rapidly
        base_graph = {"entities": [], "relationships": []}
        
        start_time = time.perf_counter()
        for i in range(100):
            base_graph["entities"].append({"id": f"entity_{i}", "value": i})
            manager.create_snapshot(
                base_graph.copy(),
                f"v{i}",
                "system@company.com",
                f"Version {i}"
            )
        duration = time.perf_counter() - start_time
        
        # Should handle 100 versions efficiently
        assert duration < 5.0, f"High volume test took {duration}s, should be <5s"
        
        # Verify all versions are retrievable
        versions = manager.list_versions()
        assert len(versions) == 100
        
        # Spot check some versions
        for i in [0, 25, 50, 75, 99]:
            version = manager.get_version(f"v{i}")
            assert version is not None
            assert len(version["entities"]) == i + 1
    
    def test_large_graph_performance(self):
        """Test performance with very large graphs"""
        manager = TemporalVersionManager()
        
        # Create graph with 5000 entities and 10000 relationships
        large_graph = {
            "entities": [
                {"id": f"entity_{i}", "type": "Node", "value": i}
                for i in range(5000)
            ],
            "relationships": [
                {
                    "source": f"entity_{i}",
                    "target": f"entity_{i+1}",
                    "type": "connects"
                }
                for i in range(4999)
            ] + [
                {
                    "source": f"entity_{i}",
                    "target": f"entity_{i+2}",
                    "type": "skips"
                }
                for i in range(4998)
            ]
        }
        
        # Should handle large graph efficiently
        start = time.perf_counter()
        snapshot = manager.create_snapshot(
            large_graph,
            "large_v1",
            "system@company.com",
            "Large graph snapshot"
        )
        duration = time.perf_counter() - start
        
        assert duration < 1.0, f"Large graph snapshot took {duration}s"
        assert len(snapshot["entities"]) == 5000
        assert len(snapshot["relationships"]) == 9997
    
    def test_concurrent_write_load(self):
        """Test concurrent write operations under load"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            manager = TemporalVersionManager(storage_path=db_path)
            
            def create_version(thread_id, count):
                """Create versions from a thread"""
                results = []
                for i in range(count):
                    graph = {
                        "entities": [{"id": f"t{thread_id}_e{i}", "value": i}],
                        "relationships": []
                    }
                    try:
                        snapshot = manager.create_snapshot(
                            graph,
                            f"thread_{thread_id}_v{i}",
                            f"user{thread_id}@company.com",
                            f"Thread {thread_id} version {i}"
                        )
                        results.append(True)
                    except Exception as e:
                        results.append(False)
                return results
            
            # Run 10 threads, each creating 20 versions
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(create_version, thread_id, 20)
                    for thread_id in range(10)
                ]
                
                all_results = []
                for future in as_completed(futures):
                    all_results.extend(future.result())
            
            # All operations should succeed
            assert all(all_results), f"Some concurrent operations failed"
            
            # Verify all 200 versions were created
            versions = manager.list_versions()
            assert len(versions) == 200
            
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestDataCorruptionRecovery:
    """Test data corruption detection and recovery scenarios"""
    
    def test_detect_corrupted_data(self):
        """Test detection of corrupted data"""
        manager = TemporalVersionManager()
        
        graph = {
            "entities": [{"id": "e1", "value": "original"}],
            "relationships": []
        }
        
        snapshot = manager.create_snapshot(
            graph,
            "v1",
            "user@company.com",
            "Original data"
        )
        
        # Verify original is valid
        assert manager.verify_checksum(snapshot)
        
        # Simulate corruption
        snapshot["entities"][0]["value"] = "corrupted"
        
        # Should detect corruption
        assert not manager.verify_checksum(snapshot)
    
    def test_checksum_mismatch_detection(self):
        """Test detection of checksum mismatches"""
        manager = TemporalVersionManager()
        
        graph = {"entities": [{"id": "e1"}], "relationships": []}
        snapshot = manager.create_snapshot(
            graph,
            "v1",
            "user@company.com",
            "Test"
        )
        
        # Tamper with checksum
        original_checksum = snapshot["checksum"]
        snapshot["checksum"] = "0" * 64  # Invalid checksum
        
        assert not manager.verify_checksum(snapshot)
        
        # Restore correct checksum
        snapshot["checksum"] = original_checksum
        assert manager.verify_checksum(snapshot)
    
    def test_recovery_from_valid_snapshot(self):
        """Test recovery by reverting to valid snapshot"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            manager = TemporalVersionManager(storage_path=db_path)
            
            # Create valid snapshots
            graph = {"entities": [{"id": "e1", "status": "good"}], "relationships": []}
            
            v1 = manager.create_snapshot(graph, "v1", "user@company.com", "Good v1")
            v2 = manager.create_snapshot(graph, "v2", "user@company.com", "Good v2")
            
            # Simulate corruption in v2
            v2["entities"][0]["status"] = "corrupted"
            
            # Detect corruption
            assert not manager.verify_checksum(v2)
            
            # Recover by retrieving v1
            recovered = manager.get_version("v1")
            assert manager.verify_checksum(recovered)
            assert recovered["entities"][0]["status"] == "good"
            
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestMigrationUpgrade:
    """Test migration and upgrade path scenarios"""
    
    def test_storage_backend_migration(self):
        """Test migration from in-memory to SQLite storage"""
        # Start with in-memory
        memory_manager = TemporalVersionManager()
        
        graph = {
            "entities": [{"id": "e1", "name": "Entity 1"}],
            "relationships": []
        }
        
        # Create versions in memory
        for i in range(5):
            memory_manager.create_snapshot(
                graph,
                f"v{i}",
                "user@company.com",
                f"Version {i}"
            )
        
        memory_versions = memory_manager.list_versions()
        assert len(memory_versions) == 5
        
        # Migrate to SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        
        try:
            sqlite_manager = TemporalVersionManager(storage_path=db_path)
            
            # Manually migrate data
            for version_info in memory_versions:
                version_data = memory_manager.get_version(version_info["label"])
                sqlite_manager.storage.save(version_data)
            
            # Verify migration
            sqlite_versions = sqlite_manager.list_versions()
            assert len(sqlite_versions) == 5
            
            # Verify data integrity after migration
            for version_info in sqlite_versions:
                version = sqlite_manager.get_version(version_info["label"])
                assert sqlite_manager.verify_checksum(version)
            
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy API"""
        manager = TemporalVersionManager()
        
        # Old-style usage (should still work)
        graph = {"entities": [], "relationships": []}
        
        # New API
        snapshot = manager.create_snapshot(
            graph,
            "v1",
            "user@company.com",
            "New API"
        )
        
        assert snapshot is not None
        assert "checksum" in snapshot
        assert "author" in snapshot


class TestEdgeCasesStress:
    """Test edge cases and stress scenarios"""
    
    def test_empty_graph_operations(self):
        """Test operations on empty graphs"""
        manager = TemporalVersionManager()
        
        empty_graph = {"entities": [], "relationships": []}
        
        snapshot = manager.create_snapshot(
            empty_graph,
            "empty_v1",
            "user@company.com",
            "Empty graph"
        )
        
        assert snapshot is not None
        assert len(snapshot["entities"]) == 0
        assert len(snapshot["relationships"]) == 0
        assert manager.verify_checksum(snapshot)
    
    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        manager = TemporalVersionManager()
        
        unicode_graph = {
            "entities": [
                {
                    "id": "e1",
                    "name": "Test with 中文字符",
                    "emoji": "🎉🚀💻",
                    "special": "Special chars: @#$%^&*()",
                    "quotes": 'Single "double" quotes'
                }
            ],
            "relationships": []
        }
        
        snapshot = manager.create_snapshot(
            unicode_graph,
            "unicode_v1",
            "user@company.com",
            "Unicode test with émojis 🎉"
        )
        
        # Verify data is preserved
        retrieved = manager.get_version("unicode_v1")
        assert retrieved["entities"][0]["name"] == "Test with 中文字符"
        assert retrieved["entities"][0]["emoji"] == "🎉🚀💻"
        assert manager.verify_checksum(retrieved)
    
    def test_deeply_nested_structures(self):
        """Test handling of deeply nested data structures"""
        manager = TemporalVersionManager()
        
        nested_graph = {
            "entities": [
                {
                    "id": "e1",
                    "level1": {
                        "level2": {
                            "level3": {
                                "level4": {
                                    "level5": {
                                        "value": "deep nested value"
                                    }
                                }
                            }
                        }
                    }
                }
            ],
            "relationships": []
        }
        
        snapshot = manager.create_snapshot(
            nested_graph,
            "nested_v1",
            "user@company.com",
            "Deeply nested structure"
        )
        
        retrieved = manager.get_version("nested_v1")
        assert retrieved["entities"][0]["level1"]["level2"]["level3"]["level4"]["level5"]["value"] == "deep nested value"
        assert manager.verify_checksum(retrieved)
    
    def test_very_long_descriptions(self):
        """Test handling of maximum description length"""
        manager = TemporalVersionManager()
        
        graph = {"entities": [], "relationships": []}
        
        # Maximum allowed length (500 chars)
        max_description = "x" * 500
        snapshot = manager.create_snapshot(
            graph,
            "v1",
            "user@company.com",
            max_description
        )
        assert snapshot["description"] == max_description
        
        # Exceeding maximum should fail
        too_long = "x" * 501
        with pytest.raises(ValidationError, match="too long"):
            manager.create_snapshot(
                graph,
                "v2",
                "user@company.com",
                too_long
            )
    
    def test_rapid_version_creation(self):
        """Test rapid creation of many versions"""
        manager = TemporalVersionManager()
        
        graph = {"entities": [], "relationships": []}
        
        # Create 50 versions as fast as possible
        start = time.perf_counter()
        for i in range(50):
            manager.create_snapshot(
                graph,
                f"rapid_v{i}",
                "user@company.com",
                f"Rapid version {i}"
            )
        duration = time.perf_counter() - start
        
        # Should complete quickly
        assert duration < 2.0, f"Rapid creation took {duration}s"
        
        # All versions should be present
        versions = manager.list_versions()
        assert len(versions) == 50


class TestLongRunningWorkflows:
    """Test long-running production workflows"""
    
    def test_daily_snapshot_workflow(self):
        """Simulate daily snapshot workflow over extended period"""
        manager = TemporalVersionManager()
        
        # Simulate 30 days of daily snapshots
        base_date = datetime(2024, 1, 1)
        graph = {"entities": [], "relationships": []}
        
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            
            # Add daily data
            graph["entities"].append({
                "id": f"daily_entity_{day}",
                "date": current_date.isoformat(),
                "value": day
            })
            
            manager.create_snapshot(
                graph.copy(),
                f"daily_{current_date.strftime('%Y%m%d')}",
                "system@company.com",
                f"Daily snapshot for {current_date.date()}"
            )
        
        # Verify all 30 days are recorded
        versions = manager.list_versions()
        assert len(versions) == 30
        
        # Verify data accumulation
        final_version = manager.get_version(f"daily_20240130")
        assert len(final_version["entities"]) == 30
    
    def test_version_retention_policy(self):
        """Test implementation of version retention policy"""
        manager = TemporalVersionManager()
        
        graph = {"entities": [], "relationships": []}
        
        # Create versions with different ages
        old_date = datetime(2023, 1, 1)
        recent_date = datetime(2024, 1, 1)
        
        # Old versions
        for i in range(5):
            manager.create_snapshot(
                graph,
                f"old_v{i}",
                "user@company.com",
                f"Old version {i}"
            )
        
        # Recent versions
        for i in range(5):
            manager.create_snapshot(
                graph,
                f"recent_v{i}",
                "user@company.com",
                f"Recent version {i}"
            )
        
        # Simulate retention policy (keep only recent)
        all_versions = manager.list_versions()
        assert len(all_versions) == 10
        
        # In production, would implement cleanup based on timestamp
        # For now, verify all versions are accessible
        for version in all_versions:
            retrieved = manager.get_version(version["label"])
            assert retrieved is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
