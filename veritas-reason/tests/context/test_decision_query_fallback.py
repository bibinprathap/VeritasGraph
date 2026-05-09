"""
Tests for ContextGraph-native fallback paths in DecisionQuery and DecisionRecorder.

Covers the full integration flow and individual method contracts.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from veritasreason.context.context_graph import ContextGraph
from veritasreason.context.decision_models import Decision, PolicyException
from veritasreason.context.decision_query import DecisionQuery
from veritasreason.context.decision_recorder import DecisionRecorder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_components():
    cg = ContextGraph()
    recorder = DecisionRecorder(graph_store=cg)
    dq = DecisionQuery(graph_store=cg)
    return cg, recorder, dq


@pytest.fixture()
def graph():
    return ContextGraph()


@pytest.fixture()
def recorder(graph):
    return DecisionRecorder(graph_store=graph)


@pytest.fixture()
def query(graph):
    return DecisionQuery(graph_store=graph, advanced_analytics=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_decision(category="approval", scenario="Test scenario", outcome="approved"):
    return Decision(
        decision_id=str(uuid.uuid4()),
        category=category,
        scenario=scenario,
        reasoning="Some reasoning",
        outcome=outcome,
        confidence=0.9,
        timestamp=datetime.now(),
        decision_maker="test_agent",
    )


def _store(recorder, decision, entities=None):
    return recorder.record_decision(decision, entities or [], [])


# ---------------------------------------------------------------------------
# Integration test (original from PR)
# ---------------------------------------------------------------------------

def test_decision_query_contextgraph_fallback(memory_components):
    """Test all DecisionQuery paths with native ContextGraph fallback execution."""
    cg, recorder, dq = memory_components

    entity_1 = "entity_user_1"
    entity_2 = "entity_company_1"
    now = datetime.now()

    dec1_id = recorder.record_decision(
        Decision(
            decision_id="dec_1",
            category="loan_approval",
            scenario="User requested loan",
            reasoning="Good credit",
            outcome="approved",
            confidence=0.9,
            timestamp=now - timedelta(days=2),
            decision_maker="system",
            metadata={"amount": 5000}
        ),
        entities=[entity_1],
        source_documents=[]
    )

    dec2_id = recorder.record_decision(
        Decision(
            decision_id="dec_2",
            category="risk_assessment",
            scenario="Company requested credit line",
            reasoning="High debt ratio",
            outcome="rejected",
            confidence=0.95,
            timestamp=now - timedelta(days=1),
            decision_maker="analyst",
            metadata={"amount": 50000}
        ),
        entities=[entity_2],
        source_documents=[]
    )

    # Test find_by_category
    loans = dq.find_by_category("loan_approval")
    assert len(loans) == 1
    assert loans[0].decision_id == "dec_1"

    # Test find_by_entity
    user_decisions = dq.find_by_entity(entity_1)
    assert len(user_decisions) == 1
    assert user_decisions[0].decision_id == "dec_1"

    # Test find_by_time_range
    recent_decisions = dq.find_by_time_range(now - timedelta(days=3), now)
    assert len(recent_decisions) == 2

    # Add a precedent link for tracing & multihop
    recorder.link_precedents(dec1_id, [dec2_id], ["SIMILAR_SCENARIO"])

    # Test multi_hop_reasoning (Undirected Traversal)
    multi_hop = dq.multi_hop_reasoning(entity_1, "", max_hops=1)
    assert any(d.decision_id == "dec_1" for d in multi_hop), "Undirected traversal failed to find Dec 1 from Entity 1"

    # Verify metadata preservation
    dec1 = [d for d in multi_hop if d.decision_id == "dec_1"][0]
    assert dec1.metadata.get("amount") == 5000, f"Custom metadata 'amount' lost: {dec1.metadata}"

    # Test trace_decision_path
    paths = dq.trace_decision_path(dec1_id, ["SIMILAR_SCENARIO"])
    assert len(paths) == 1

    # Test find_similar_exceptions
    recorder.record_exception(
        decision_id=dec2_id,
        policy_id="pol_1",
        reason="Market downturn special condition",
        approver="manager",
        approval_method="email",
        justification="Allowed due to macro factors"
    )
    exceptions = dq.find_similar_exceptions("Market downturn", limit=5)
    assert len(exceptions) == 1

    print("\nALL FALLBACK VERIFICATIONS PASSED")


# ---------------------------------------------------------------------------
# Unit tests: DecisionRecorder fallback
# ---------------------------------------------------------------------------

class TestDecisionRecorderFallback:

    def test_store_and_retrieve_decision_node(self, graph, recorder):
        """_store_decision_node must store all fields as flat node properties."""
        d = _make_decision()
        _store(recorder, d)

        nodes = graph.find_nodes(node_type="Decision")
        assert any(n["id"] == d.decision_id for n in nodes), (
            "Decision node not found; likely stored under wrong key"
        )
        node = next(n for n in nodes if n["id"] == d.decision_id)
        meta = node.get("metadata", {})
        assert meta.get("category") == d.category
        assert meta.get("outcome") == d.outcome

    def test_link_entities_creates_about_edges(self, graph, recorder):
        """link_entities must create ABOUT edges to each entity node."""
        d = _make_decision()
        _store(recorder, d, entities=["entity_A", "entity_B"])

        edges = graph.find_edges(edge_type="ABOUT")
        targets = {e["target"] for e in edges if e["source"] == d.decision_id}
        assert "entity_A" in targets
        assert "entity_B" in targets

    def test_record_exception_creates_nodes_and_edges(self, graph, recorder):
        """record_exception must persist exception node and GRANTED_EXCEPTION edge."""
        d = _make_decision()
        _store(recorder, d)

        exc_id = recorder.record_exception(
            decision_id=d.decision_id,
            policy_id="pol_001",
            reason="Urgent override",
            approver="manager",
            approval_method="slack_dm",
            justification="Time-sensitive case",
        )

        exc_nodes = graph.find_nodes(node_type="Exception")
        assert any(n["id"] == exc_id for n in exc_nodes)

        granted_edges = graph.find_edges(edge_type="GRANTED_EXCEPTION")
        assert any(e["source"] == d.decision_id and e["target"] == exc_id
                   for e in granted_edges)

    def test_link_precedents_creates_edges(self, graph, recorder):
        """link_precedents must create relationship edges between decisions."""
        d1 = _make_decision()
        d2 = _make_decision()
        _store(recorder, d1)
        _store(recorder, d2)

        recorder.link_precedents(d1.decision_id, [d2.decision_id], ["INFLUENCED_BY"])
        edges = graph.find_edges(edge_type="INFLUENCED_BY")
        assert any(e["source"] == d1.decision_id and e["target"] == d2.decision_id
                   for e in edges)


# ---------------------------------------------------------------------------
# Unit tests: DecisionQuery fallback
# ---------------------------------------------------------------------------

class TestDecisionQueryFallback:

    def test_find_precedents_basic_returns_decisions(self, graph, recorder, query):
        """_find_precedents_basic must return stored decisions via ContextGraph."""
        for _ in range(3):
            _store(recorder, _make_decision())

        results = query._find_precedents_basic("Test scenario", None, 10)
        assert len(results) == 3
        assert all(isinstance(r, Decision) for r in results)

    def test_find_by_category_filters_correctly(self, graph, recorder, query):
        """find_by_category must only return decisions matching the category."""
        _store(recorder, _make_decision(category="loan"))
        _store(recorder, _make_decision(category="loan"))
        _store(recorder, _make_decision(category="claim"))

        loans = query.find_by_category("loan")
        assert len(loans) == 2
        assert all(d.category == "loan" for d in loans)

    def test_find_by_entity_returns_linked_decisions(self, graph, recorder, query):
        """find_by_entity must return decisions linked via ABOUT edges."""
        d = _make_decision()
        _store(recorder, d, entities=["customer_99"])

        results = query.find_by_entity("customer_99")
        assert any(r.decision_id == d.decision_id for r in results)

    def test_find_by_time_range_filters_correctly(self, graph, recorder, query):
        """find_by_time_range must respect temporal bounds."""
        now = datetime.now()
        old = Decision(
            decision_id=str(uuid.uuid4()),
            category="x", scenario="old", reasoning="r", outcome="ok",
            confidence=0.5, timestamp=now - timedelta(days=10),
            decision_maker="agent",
        )
        recent = Decision(
            decision_id=str(uuid.uuid4()),
            category="x", scenario="recent", reasoning="r", outcome="ok",
            confidence=0.5, timestamp=now - timedelta(hours=1),
            decision_maker="agent",
        )
        recorder.record_decision(old, [], [])
        recorder.record_decision(recent, [], [])

        results = query.find_by_time_range(now - timedelta(days=2), now + timedelta(hours=1))
        ids = {d.decision_id for d in results}
        assert recent.decision_id in ids
        assert old.decision_id not in ids

    def test_find_by_time_range_tz_aware_naive_mix(self, graph, recorder, query):
        """find_by_time_range must not crash when start is tz-aware and stored ts is naive."""
        d = _make_decision()
        recorder.record_decision(d, [], [])

        start = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        end = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        results = query.find_by_time_range(start, end)
        assert isinstance(results, list)

    def test_multi_hop_reasoning_finds_connected_decisions(self, graph, recorder, query):
        """multi_hop_reasoning undirected BFS must find decisions via incoming edges."""
        d = _make_decision()
        _store(recorder, d, entities=["hub_entity"])

        # ABOUT edge: d.decision_id → hub_entity (outgoing from decision)
        # Undirected BFS from hub_entity should walk the edge in reverse and find d
        results = query.multi_hop_reasoning("hub_entity", "context", max_hops=2)
        assert any(r.decision_id == d.decision_id for r in results)

    def test_trace_decision_path_returns_paths(self, graph, recorder, query):
        """trace_decision_path must return path dicts from a stored decision."""
        d1 = _make_decision()
        d2 = _make_decision()
        recorder.record_decision(d1, [], [])
        recorder.record_decision(d2, [], [])
        recorder.link_precedents(d1.decision_id, [d2.decision_id], ["INFLUENCED_BY"])

        paths = query.trace_decision_path(d1.decision_id, ["INFLUENCED_BY"])
        assert len(paths) >= 1
        assert all("path_length" in p for p in paths)

    def test_find_similar_exceptions_returns_exception_objects(self, graph, recorder, query):
        """find_similar_exceptions must return PolicyException objects from ContextGraph."""
        d = _make_decision()
        _store(recorder, d)
        recorder.record_exception(
            decision_id=d.decision_id,
            policy_id="pol_002",
            reason="Budget exceeded",
            approver="director",
            approval_method="email",
            justification="Exceptional circumstances",
        )

        results = query.find_similar_exceptions("budget issue", limit=10)
        assert len(results) >= 1
        assert all(isinstance(e, PolicyException) for e in results)

    def test_isinstance_does_not_trigger_on_mock(self):
        """type() is ContextGraph must not fire for Mock(spec=ContextGraph)."""
        from unittest.mock import Mock
        mock_store = Mock(spec=ContextGraph)
        assert type(mock_store) is not ContextGraph
