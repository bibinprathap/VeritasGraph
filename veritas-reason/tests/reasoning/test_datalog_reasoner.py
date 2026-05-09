"""
Test suite for the DatalogReasoner module.
"""

import pytest
from typing import List, Dict, Any

from veritasreason.reasoning.datalog_reasoner import DatalogReasoner, DatalogFact

@pytest.fixture
def reasoner():
    """Provides a fresh DatalogReasoner instance for each test."""
    return DatalogReasoner()

class MockContextGraph:
    """A mock to simulate VeritasReason's actual ContextGraph structure."""
    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self._nodes = nodes
        self._edges = edges

    def find_nodes(self, node_type=None):
        return self._nodes

    def find_edges(self, edge_type=None):
        return self._edges


class TestBasicFacts:
    def test_add_string_fact(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        assert len(reasoner._all_facts) == 1
        fact = list(reasoner._all_facts)[0]
        assert fact.predicate == "parent"
        assert fact.args == ("tom", "bob")

    def test_add_dict_fact(self, reasoner):
        reasoner.add_fact({"subject": "bob", "predicate": "parent", "object": "ann"})
        assert len(reasoner._all_facts) == 1
        fact = list(reasoner._all_facts)[0]
        assert fact.predicate == "parent"
        assert fact.args == ("bob", "ann")

    def test_duplicate_fact_ignored(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_fact("parent(tom, bob)")
        assert len(reasoner._all_facts) == 1
        
    def test_empty_arguments_raise_error(self, reasoner):
        # Proves Issue #6 is fixed
        with pytest.raises(ValueError, match="Empty argument"):
            reasoner.add_fact("parent( )")
        with pytest.raises(ValueError, match="Empty argument"):
            reasoner.add_fact("parent(tom, )")


class TestRules:
    def test_single_rule(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
        
        derived = reasoner.derive_all()
        assert "ancestor(tom, bob)" in derived

    def test_recursive_ancestor(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_fact("parent(bob, ann)")
        
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).")
        
        derived = reasoner.derive_all()
        assert "ancestor(tom, bob)" in derived
        assert "ancestor(bob, ann)" in derived
        assert "ancestor(tom, ann)" in derived  

    def test_multi_hop_three_levels(self, reasoner):
        reasoner.add_fact("edge(1, 2)")
        reasoner.add_fact("edge(2, 3)")
        reasoner.add_fact("edge(3, 4)")
        
        reasoner.add_rule("reachable(X, Y) :- edge(X, Y).")
        reasoner.add_rule("reachable(X, Y) :- edge(X, Z), reachable(Z, Y).")
        
        derived = reasoner.derive_all()
        assert "reachable(1, 4)" in derived

    def test_two_body_atoms(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_fact("parent(bob, ann)")
        
        reasoner.add_rule("grandparent(X, Y) :- parent(X, Z), parent(Z, Y).")
        
        derived = reasoner.derive_all()
        assert "grandparent(tom, ann)" in derived
        assert "grandparent(tom, bob)" not in derived


class TestQuery:
    def test_variable_binding(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_fact("parent(tom, alex)")
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
        
        results = reasoner.query("ancestor(tom, ?Y)")
        y_bindings = sorted([res["Y"] for res in results])
        assert y_bindings == ["alex", "bob"]

    def test_lowercase_variable_query(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        results = reasoner.query("parent(tom, ?y)")
        assert len(results) == 1
        assert results[0]["y"] == "bob"

    def test_pre_bound_variable(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
        
        results_bob = reasoner.query("ancestor(tom, ?Y)", bindings={"Y": "bob"})
        assert len(results_bob) == 1
        assert results_bob[0]["Y"] == "bob"
        
        results_ann = reasoner.query("ancestor(tom, ?Y)", bindings={"Y": "ann"})
        assert len(results_ann) == 0

    def test_no_match_returns_empty(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        results = reasoner.query("parent(sarah, ?Y)")
        assert results == []


class TestContextGraphIntegration:
    def test_load_from_graph(self, reasoner):
        graph = MockContextGraph(
            nodes=[{"id": "microsoft", "type": "company"}],
            edges=[{"source": "microsoft", "target": "openai", "type": "invested_in"}]
        )

        added = reasoner.load_from_graph(graph)
        assert added == 2

        assert DatalogFact("company", ("microsoft",)) in reasoner._all_facts
        assert DatalogFact("invested_in", ("microsoft", "openai")) in reasoner._all_facts

    def test_edge_becomes_fact(self, reasoner):
        graph = MockContextGraph(
            nodes=[],
            edges=[
                {"source": "alice", "target": "bob", "type": "manages"},
                {"source": "bob", "target": "carol", "type": "manages"},
            ]
        )
        reasoner.load_from_graph(graph)

        assert DatalogFact("manages", ("alice", "bob")) in reasoner._all_facts
        assert DatalogFact("manages", ("bob", "carol")) in reasoner._all_facts

    def test_derive_after_load(self, reasoner):
        graph = MockContextGraph(
            nodes=[],
            edges=[
                {"source": "alice", "target": "bob", "type": "manages"},
                {"source": "bob", "target": "carol", "type": "manages"},
            ]
        )
        reasoner.load_from_graph(graph)

        reasoner.add_rule("transitive_manages(X, Y) :- manages(X, Y).")
        reasoner.add_rule("transitive_manages(X, Y) :- manages(X, Z), transitive_manages(Z, Y).")

        derived = reasoner.derive_all()
        assert "transitive_manages(alice, carol)" in derived


class TestEdgeCases:
    def test_empty_program(self, reasoner):
        derived = reasoner.derive_all()
        assert derived == []

    def test_derive_all_idempotent(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
        
        first_run = len(reasoner.derive_all())
        second_run = len(reasoner.derive_all())
        
        assert first_run == second_run
        assert first_run == 2  

    def test_clear_resets_state(self, reasoner):
        reasoner.add_fact("parent(tom, bob)")
        reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
        reasoner.derive_all()
        
        reasoner.clear()
        
        assert len(reasoner._all_facts) == 0
        assert len(reasoner._rules) == 0
        assert len(reasoner._delta_new) == 0
        assert len(reasoner._delta_old) == 0
        assert len(reasoner._fact_index) == 0