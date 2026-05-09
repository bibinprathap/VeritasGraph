"""Consolidated end-to-end coverage for context-graph critical features."""

from datetime import datetime
from unittest.mock import Mock

from veritasreason.context.agent_context import AgentContext
from veritasreason.context.causal_analyzer import CausalChainAnalyzer
from veritasreason.context.decision_methods import capture_decision_trace
from veritasreason.context.decision_models import Decision
from veritasreason.context.decision_query import DecisionQuery
from veritasreason.context.graph_schema import get_schema_info
from veritasreason.context.policy_engine import PolicyEngine


def _decision() -> Decision:
    return Decision(
        decision_id="e2e_decision_001",
        category="renewal_pricing",
        scenario="Renewal discount exception",
        reasoning="SEV-1 history + churn risk",
        outcome="approved",
        confidence=0.93,
        timestamp=datetime.now(),
        decision_maker="agent_renewal",
    )


def _realistic_cross_system_context():
    """Representative enterprise sources used by agentic workflows."""
    return {
        "salesforce": {
            "account_id": "001A",
            "arr": 120000,
            "customer_tier": "enterprise",
            "renewal_date": "2026-03-15",
        },
        "zendesk": {
            "open_escalations": 2,
            "sev1_tickets_last_90d": 3,
            "latest_ticket_id": "ZD-9912",
        },
        "pagerduty": {
            "sev1_incidents_last_90d": 3,
            "latest_incident": "PD-4421",
            "service": "api-gateway",
        },
        "slack": {
            "risk_channel": "#renewal-risk",
            "churn_flag": True,
            "latest_thread_ref": "ts-1739202.1234",
        },
        "stripe": {
            "invoice_status": "past_due",
            "last_payment_attempt": "2026-01-28",
            "days_past_due": 14,
        },
        "product_telemetry": {
            "weekly_active_users": 284,
            "api_error_rate": 0.038,
            "feature_adoption_score": 0.72,
        },
        "confluence": {
            "playbook_version": "renewals-v4.2",
            "policy_page_id": "CONF-778",
        },
    }


def test_e2e_decision_trace_capture_with_immutable_lineage():
    graph_store = Mock()

    def _execute_query(query, params=None, *args, **kwargs):
        if "RETURN t.trace_id as trace_id" in query:
            return {
                "records": [
                    {
                        "trace_id": "e2e_decision_001:2",
                        "event_index": 2,
                        "event_hash": "prev_hash",
                    }
                ]
            }
        if "RETURN p.policy_id as policy_id, p.version as version" in query:
            return {"records": [{"policy_id": "renewal_policy", "version": "3.2"}]}
        return {"records": []}

    graph_store.execute_query = Mock(side_effect=_execute_query)

    decision_id = capture_decision_trace(
        decision=_decision(),
        cross_system_context=_realistic_cross_system_context(),
        graph_store=graph_store,
        entities=["customer_123"],
        source_documents=["note_001"],
        policy_ids=[{"policy_id": "renewal_policy", "version": "3.2"}],
        exceptions=[{"policy_id": "renewal_policy", "reason": "service-impact"}],
        approvals=[{"approver": "vp_finance", "approval_method": "slack_dm"}],
        precedents=[{"precedent_id": "decision_old_001"}],
        immutable_audit_log=True,
    )

    assert decision_id == "e2e_decision_001"
    queries = [c[0][0] for c in graph_store.execute_query.call_args_list]
    assert any("CREATE (t:DecisionTraceEvent" in q for q in queries)
    assert any("MERGE (d)-[:HAS_TRACE_EVENT]->(t)" in q for q in queries)
    assert any("MERGE (prev)-[:NEXT_TRACE_EVENT]->(curr)" in q for q in queries)


def test_e2e_schema_info_contains_trace_and_policy_versioning():
    schema = get_schema_info()
    assert "DecisionTraceEvent" in schema["node_labels"]
    assert "HAS_TRACE_EVENT" in schema["relationship_types"]["Decision trace relationships"]
    assert "NEXT_TRACE_EVENT" in schema["relationship_types"]["Decision trace relationships"]
    assert "policy_identity_unique" in schema["constraints"]
    assert "decision_trace_timestamp_index" in schema["indexes"]


def test_e2e_policy_applicability_for_wrapped_and_falkordb_shapes():
    # Wrapped records shape
    wrapped_store = Mock()
    wrapped_store.execute_query = Mock(
        return_value={
            "records": [
                {
                    "p": {
                        "policy_id": "p_wrapped",
                        "name": "Wrapped",
                        "description": "wrapped",
                        "rules": {},
                        "category": "renewal_pricing",
                        "version": "1.0",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "metadata": {},
                    }
                }
            ]
        }
    )
    wrapped_engine = PolicyEngine(graph_store=wrapped_store)
    wrapped = wrapped_engine.get_applicable_policies("renewal_pricing", None)
    assert len(wrapped) == 1
    assert wrapped[0].policy_id == "p_wrapped"

    # FalkorDB row+header shape
    falkor_store = Mock()
    falkor_store.execute_query = Mock(
        return_value={
            "records": [
                [
                    {
                        "policy_id": "p_falkor",
                        "name": "Falkor",
                        "description": "row shape",
                        "rules": {},
                        "category": "renewal_pricing",
                        "version": "1.0",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "metadata": {},
                    }
                ]
            ],
            "header": ["p"],
        }
    )
    falkor_engine = PolicyEngine(graph_store=falkor_store)
    falkor = falkor_engine.get_applicable_policies("renewal_pricing", None)
    assert len(falkor) == 1
    assert falkor[0].policy_id == "p_falkor"


def test_e2e_policy_applicability_context_graph_fallback_respects_entities():
    class _ContextGraphLike:
        def find_nodes(self, node_type=None):
            return [
                {
                    "metadata": {
                        "policy_id": "p_match",
                        "name": "match",
                        "description": "match",
                        "rules": {},
                        "category": "renewal_pricing",
                        "version": "1.0",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "metadata": {"entities": ["customer:123"]},
                    }
                },
                {
                    "metadata": {
                        "policy_id": "p_other",
                        "name": "other",
                        "description": "other",
                        "rules": {},
                        "category": "renewal_pricing",
                        "version": "1.0",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "metadata": {"entities": ["customer:999"]},
                    }
                },
            ]

    engine = PolicyEngine(graph_store=_ContextGraphLike())
    policies = engine.get_applicable_policies("renewal_pricing", ["customer:123"])
    assert len(policies) == 1
    assert policies[0].policy_id == "p_match"


def test_e2e_decision_query_and_causal_analyzer_handle_wrapped_results():
    graph_store = Mock()
    graph_store.execute_query = Mock(
        return_value={
            "records": [
                {
                    "d": {
                        "decision_id": "d1",
                        "category": "renewal_pricing",
                        "scenario": "Renewal case",
                        "reasoning": "Reasoning",
                        "outcome": "approved",
                        "confidence": 0.9,
                        "timestamp": datetime.now().isoformat(),
                        "decision_maker": "agent",
                    },
                    "end": {
                        "decision_id": "d2",
                        "category": "renewal_pricing",
                        "scenario": "Downstream case",
                        "reasoning": "Reasoning",
                        "outcome": "approved",
                        "confidence": 0.8,
                        "timestamp": datetime.now().isoformat(),
                        "decision_maker": "agent",
                    },
                    "distance": 1,
                }
            ]
        }
    )

    query = DecisionQuery(graph_store=graph_store)
    precedents = query.find_precedents_hybrid("Renewal case", "renewal_pricing", 5)
    assert len(precedents) == 1
    assert precedents[0].decision_id == "d1"

    analyzer = CausalChainAnalyzer(graph_store=graph_store)
    chain = analyzer.get_causal_chain("d1", "downstream", 3)
    assert len(chain) == 1
    assert chain[0].decision_id == "d2"


def test_e2e_cross_system_capture_sanitizes_internal_errors():
    vector_store = Mock()
    knowledge_graph = Mock()
    knowledge_graph.execute_query = Mock(
        side_effect=RuntimeError("secret backend details")
    )

    ctx = AgentContext(
        vector_store=vector_store, knowledge_graph=knowledge_graph, decision_tracking=True
    )
    data = ctx.capture_cross_system_inputs(["salesforce"], "customer_123")

    assert data["salesforce"]["status"] == "capture_failed"
    assert data["salesforce"]["error"] == "internal_capture_error"
    assert "secret" not in data["salesforce"]["error"]


def test_e2e_cross_system_capture_with_real_source_mix():
    vector_store = Mock()
    knowledge_graph = Mock()

    # Simulate backend records for all systems with wrapper shape.
    knowledge_graph.execute_query = Mock(
        return_value={
            "records": [
                {
                    "c": {
                        "context_id": "ctx_001",
                        "system_name": "source",
                        "context_data": {"sample": True},
                    }
                }
            ]
        }
    )

    ctx = AgentContext(
        vector_store=vector_store, knowledge_graph=knowledge_graph, decision_tracking=True
    )
    systems = list(_realistic_cross_system_context().keys())
    data = ctx.capture_cross_system_inputs(systems, "customer_123")

    assert set(data.keys()) == set(systems)
    for system in systems:
        assert data[system]["system_name"] == system
        assert data[system]["entity_id"] == "customer_123"
        assert data[system]["status"] == "captured"
        assert "captured_at" in data[system]
        assert "records_found" in data[system]
        assert "records" in data[system]
