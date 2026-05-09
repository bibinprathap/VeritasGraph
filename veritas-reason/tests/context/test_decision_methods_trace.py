"""Tests for decision trace capture convenience API."""

from datetime import datetime
import logging
from unittest.mock import Mock

from veritasreason.context.decision_methods import (
    _append_immutable_trace_events,
    capture_decision_trace,
)
from veritasreason.context.decision_models import Decision


def _sample_decision() -> Decision:
    return Decision(
        decision_id="decision_trace_test_001",
        category="credit_approval",
        scenario="Credit line increase for long-term customer",
        reasoning="Strong payment history and low utilization",
        outcome="approved",
        confidence=0.92,
        timestamp=datetime.now(),
        decision_maker="ai_agent",
    )


def test_capture_decision_trace_without_graph_store_is_backward_compatible(caplog):
    decision = _sample_decision()
    with caplog.at_level(logging.WARNING):
        decision_id = capture_decision_trace(
            decision,
            cross_system_context={"crm": {"arr": 120000}},
            policy_ids=[{"policy_id": "renewal_discount_policy", "version": "3.2"}],
        )
    assert decision_id == decision.decision_id
    assert "capture_decision_trace skipped persistence (no graph_store)" in caplog.text
    assert f"decision_id={decision.decision_id}" in caplog.text
    assert f"decision_maker={decision.decision_maker}" in caplog.text
    assert f"outcome={decision.outcome}" in caplog.text


def test_capture_decision_trace_with_graph_store_records_trace_events():
    decision = _sample_decision()
    graph_store = Mock()

    def _execute_query(query, params=None, *args, **kwargs):
        if "RETURN t.trace_id as trace_id" in query:
            # Simulate existing chain head so NEXT_TRACE_EVENT is exercised.
            return {
                "records": [
                    {
                        "trace_id": "decision_trace_test_001:3",
                        "event_index": 3,
                        "event_hash": "prev_hash_123",
                    }
                ]
            }
        if "RETURN p.policy_id as policy_id, p.version as version" in query:
            return {
                "records": [
                    {"policy_id": "renewal_discount_policy_v3_2", "version": "3.2"}
                ]
            }
        return {"records": []}

    graph_store.execute_query = Mock(side_effect=_execute_query)

    decision_id = capture_decision_trace(
        decision=decision,
        cross_system_context={"crm": {"arr": 120000}},
        graph_store=graph_store,
        entities=["customer_123"],
        source_documents=["renewal_note_001"],
        policy_ids=["renewal_discount_policy_v3_2"],
        approvals=[
            {
                "approver": "vp_finance",
                "approval_method": "slack_dm",
                "approval_context": "Approved due to SEV-1 impact history",
            }
        ],
        precedents=[
            {
                "precedent_id": "decision_legacy_001",
                "relationship_type": "similar_scenario",
            }
        ],
        immutable_audit_log=True,
    )

    assert decision_id == decision.decision_id
    calls = graph_store.execute_query.call_args_list
    queries = [c[0][0] for c in calls]
    params_list = [c[0][1] if len(c[0]) > 1 else {} for c in calls]

    assert any("CREATE (t:DecisionTraceEvent" in q for q in queries)
    assert any("MERGE (d)-[:HAS_TRACE_EVENT]->(t)" in q for q in queries)
    assert any("MERGE (prev)-[:NEXT_TRACE_EVENT]->(curr)" in q for q in queries)

    event_types = [
        p.get("event_type")
        for p in params_list
        if isinstance(p, dict) and "event_type" in p
    ]
    assert "DECISION_RECORDED" in event_types
    assert "CROSS_SYSTEM_CONTEXT_CAPTURED" in event_types
    assert "POLICIES_APPLIED" in event_types
    assert "APPROVAL_CHAIN_RECORDED" in event_types
    assert "PRECEDENTS_LINKED" in event_types


def test_capture_decision_trace_accepts_legacy_payload_shapes():
    decision = _sample_decision()
    graph_store = Mock()
    graph_store.execute_query = Mock(return_value=[{"t": {"trace_id": "decision_trace_test_001:4", "event_index": 4, "event_hash": "abc"}}])

    decision_id = capture_decision_trace(
        decision=decision,
        cross_system_context={"crm": {"arr": 120000}},
        graph_store=graph_store,
        entities="customer_legacy_001",
        source_documents="doc_legacy_001",
        policy_ids="policy_legacy_v1",
        exceptions={"policy_id": "policy_legacy_v1", "reason": "legacy exception"},
        approvals={"approver": "vp_ops", "approval_method": "email"},
        precedents=["decision_legacy_001"],
        immutable_audit_log=True,
    )

    assert decision_id == decision.decision_id
    assert graph_store.execute_query.call_count > 0


def test_capture_decision_trace_accepts_versioned_policy_refs():
    decision = _sample_decision()
    graph_store = Mock()
    graph_store.execute_query = Mock(
        return_value={"records": [{"policy_id": "renewal_discount_policy", "version": "3.2"}]}
    )

    decision_id = capture_decision_trace(
        decision=decision,
        cross_system_context={"crm": {"arr": 120000}},
        graph_store=graph_store,
        policy_ids=[{"policy_id": "renewal_discount_policy", "version": "3.2"}],
        immutable_audit_log=False,
    )

    assert decision_id == decision.decision_id
    policy_calls = [
        c for c in graph_store.execute_query.call_args_list
        if "policy_version" in c[0][1]
    ]
    assert policy_calls
    assert policy_calls[0][0][1]["policy_version"] == "3.2"


def test_append_immutable_trace_events_logs_lookup_failure_and_continues(caplog):
    graph_store = Mock()
    calls = {"n": 0}

    def _execute_query(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("lookup failed")
        return {"records": []}

    graph_store.execute_query = Mock(side_effect=_execute_query)

    with caplog.at_level(logging.WARNING):
        _append_immutable_trace_events(
            graph_store=graph_store,
            decision_id="decision_trace_test_001",
            events=[{"event_type": "DECISION_RECORDED", "payload": {"ok": True}}],
            logger=logging.getLogger("test_logger"),
        )

    assert "Failed to lookup previous immutable trace event" in caplog.text
    assert "decision_id=decision_trace_test_001" in caplog.text
    assert graph_store.execute_query.call_count >= 2
