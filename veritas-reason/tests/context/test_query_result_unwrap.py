"""Regression tests for execute_query wrapper result handling."""

from datetime import datetime
from unittest.mock import Mock

from veritasreason.context.causal_analyzer import CausalChainAnalyzer
from veritasreason.context.decision_query import DecisionQuery


def test_decision_query_unwraps_execute_query_records_wrapper():
    graph_store = Mock()
    graph_store.execute_query.return_value = {
        "success": True,
        "records": [
            {
                "d": {
                    "decision_id": "decision_001",
                    "category": "credit_approval",
                    "scenario": "Credit increase",
                    "reasoning": "Strong history",
                    "outcome": "approved",
                    "confidence": 0.9,
                    "timestamp": datetime.now().isoformat(),
                    "decision_maker": "agent",
                }
            }
        ],
    }

    query = DecisionQuery(graph_store=graph_store)
    results = query.find_precedents_hybrid(
        scenario="credit increase", category="credit_approval", limit=10
    )

    assert len(results) == 1
    assert results[0].decision_id == "decision_001"


def test_causal_analyzer_unwraps_execute_query_records_wrapper():
    graph_store = Mock()
    graph_store.execute_query.return_value = {
        "success": True,
        "records": [
            {
                "end": {
                    "decision_id": "decision_002",
                    "category": "credit_approval",
                    "scenario": "Escalation",
                    "reasoning": "Policy exception",
                    "outcome": "approved",
                    "confidence": 0.8,
                    "timestamp": datetime.now().isoformat(),
                    "decision_maker": "agent",
                },
                "distance": 1,
            }
        ],
    }

    analyzer = CausalChainAnalyzer(graph_store=graph_store)
    results = analyzer.get_causal_chain(
        decision_id="decision_001", direction="downstream", max_depth=3
    )

    assert len(results) == 1
    assert results[0].decision_id == "decision_002"
    assert results[0].metadata.get("causal_distance") == 1
