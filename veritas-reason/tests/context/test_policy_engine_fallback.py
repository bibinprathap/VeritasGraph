from datetime import datetime

from veritasreason.context import ContextGraph, PolicyEngine
from veritasreason.context.decision_models import Policy, Decision


def _make_policy(pid="p1", version="1.0.0", min_conf=0.8):
    return Policy(
        policy_id=pid,
        name="Test Policy",
        description="desc",
        rules={"min_confidence": min_conf, "allowed_outcomes": ["approved", "rejected"]},
        category="test",
        version=version,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )


def _make_decision(decision_id, conf=0.9, outcome="approved"):
    return Decision(
        decision_id=decision_id,
        category="test",
        scenario="s",
        reasoning="r",
        outcome=outcome,
        confidence=conf,
        timestamp=datetime.now(),
        decision_maker="tester",
        metadata={},
    )


def test_policy_engine_add_get_update_with_context_graph():
    graph = ContextGraph()
    engine = PolicyEngine(graph)
    policy = _make_policy()
    engine.add_policy(policy)
    latest = engine.get_policy("p1")
    assert latest is not None
    assert latest.version == "1.0.0"
    new_ver = engine.update_policy(
        "p1",
        {"min_confidence": 0.85, "allowed_outcomes": ["approved", "rejected"]},
        "raise min",
    )
    assert isinstance(new_ver, str)
    latest2 = engine.get_policy("p1")
    assert latest2 is not None
    assert latest2.version != "1.0.0"


def test_policy_engine_compliance_and_application_edges():
    graph = ContextGraph()
    engine = PolicyEngine(graph)
    policy = _make_policy()
    engine.add_policy(policy)
    decision = _make_decision("d1", conf=0.9, outcome="approved")
    graph.add_decision(decision)
    ok = engine.check_compliance(decision, "p1")
    assert ok is True
    engine.record_policy_application("d1", "p1", "1.0.0")
    edges = graph.find_edges(edge_type="APPLIED_POLICY")
    assert any(
        e.get("source") == "d1"
        and isinstance(e.get("target"), str)
        and e.get("target").startswith("p1:")
        for e in edges
    )
