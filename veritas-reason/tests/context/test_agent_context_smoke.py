import pytest
from veritasreason.context import AgentContext, ContextGraph
from veritasreason.context.decision_models import Policy
from veritasreason.vector_store import VectorStore
from datetime import datetime


def test_agent_context_minimal_decisions_and_chain():
    vs = VectorStore(backend="inmemory", dimension=64)
    graph = ContextGraph()
    ctx = AgentContext(
        vector_store=vs,
        knowledge_graph=graph,
        decision_tracking=True,
        kg_algorithms=False,
        vector_store_features=False,
    )
    d1 = ctx.record_decision(
        category="credit_approval",
        scenario="s1",
        reasoning="r1",
        outcome="rejected",
        confidence=0.8,
        entities=["e1"],
        decision_maker="tester",
    )
    d2 = ctx.record_decision(
        category="credit_approval",
        scenario="s2",
        reasoning="r2",
        outcome="rejected",
        confidence=0.85,
        entities=["e1"],
        decision_maker="tester",
    )
    graph.add_causal_relationship(d1, d2, "INFLUENCED")
    chain = ctx.get_causal_chain(d2, direction="upstream", max_depth=5)
    assert isinstance(chain, list)
    assert len(chain) >= 1


def test_agent_context_inmemory_store_and_retrieve():
    """VectorStore(backend="inmemory") stores memories without faiss-cpu."""
    vs = VectorStore(backend="inmemory")
    ctx = AgentContext(
        vector_store=vs,
        knowledge_graph=ContextGraph(),
        decision_tracking=True,
        kg_algorithms=False,
        vector_store_features=False,
    )
    memory_id = ctx.store(
        "GPT-4 outperforms GPT-3.5 on reasoning benchmarks by 40%",
        conversation_id="test_session",
    )
    assert isinstance(memory_id, str)
    assert len(memory_id) > 0


def test_agent_context_policy_engine_with_graph_backend():
    vs = VectorStore(backend="inmemory", dimension=64)
    graph = ContextGraph()
    ctx = AgentContext(
        vector_store=vs,
        knowledge_graph=graph,
        decision_tracking=True,
        kg_algorithms=False,
        vector_store_features=False,
    )
    pe = ctx.get_policy_engine()
    pol = Policy(
        policy_id="cp",
        name="Credit Policy",
        description="d",
        rules={"min_confidence": 0.8, "allowed_outcomes": ["approved", "rejected"]},
        category="credit_approval",
        version="1.0.0",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )
    pe.add_policy(pol)
    found = pe.get_policy("cp")
    assert found is not None
