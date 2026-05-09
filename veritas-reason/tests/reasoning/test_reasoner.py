import unittest
from veritasreason.reasoning.reasoner import Reasoner, Rule, RuleType, Fact, InferenceResult

class TestReasoner(unittest.TestCase):
    def setUp(self):
        self.reasoner = Reasoner()

    def test_add_rule_string(self):
        rule_str = "IF Person(?x) AND Parent(?x, ?y) THEN Child(?y, ?x)"
        rule = self.reasoner.add_rule(rule_str)
        self.assertEqual(len(self.reasoner.rules), 1)
        self.assertEqual(rule.conditions, ["Person(?x)", "Parent(?x, ?y)"])
        self.assertEqual(rule.conclusion, "Child(?y, ?x)")

    def test_add_rule_object(self):
        rule = Rule(
            rule_id="r1",
            name="Test Rule",
            conditions=["A(?x)"],
            conclusion="B(?x)",
            priority=10
        )
        self.reasoner.add_rule(rule)
        self.assertEqual(len(self.reasoner.rules), 1)
        self.assertEqual(self.reasoner.rules[0].priority, 10)

    def test_add_fact_string(self):
        self.reasoner.add_fact("Person(John)")
        self.assertIn("Person(John)", self.reasoner.facts)

    def test_add_fact_dict_entity(self):
        fact_dict = {"type": "Person", "name": "John"}
        self.reasoner.add_fact(fact_dict)
        self.assertIn("Person(John)", self.reasoner.facts)

    def test_add_fact_dict_relationship(self):
        fact_dict = {
            "type": "WorksAt",
            "source_name": "John",
            "target_name": "Google"
        }
        self.reasoner.add_fact(fact_dict)
        self.assertIn("WorksAt(John, Google)", self.reasoner.facts)

    def test_forward_chaining(self):
        self.reasoner.add_rule("IF Person(?x) AND Parent(?x, ?y) THEN Child(?y, ?x)")
        self.reasoner.add_fact("Person(John)")
        self.reasoner.add_fact("Parent(John, Jane)")
        
        results = self.reasoner.forward_chain()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].conclusion, "Child(Jane, John)")
        self.assertIn("Child(Jane, John)", self.reasoner.facts)

    def test_backward_chaining_simple(self):
        self.reasoner.add_rule("IF Person(?x) AND Parent(?x, ?y) THEN Child(?y, ?x)")
        self.reasoner.add_fact("Person(John)")
        self.reasoner.add_fact("Parent(John, Jane)")
        
        result = self.reasoner.backward_chain("Child(Jane, John)")
        self.assertIsNotNone(result)
        self.assertEqual(result.conclusion, "Child(Jane, John)")
        self.assertEqual(len(result.premises), 2)
        self.assertIn("Person(John)", result.premises)
        self.assertIn("Parent(John, Jane)", result.premises)

    def test_infer_facts(self):
        facts = ["Person(John)", "Parent(John, Jane)"]
        rules = ["IF Person(?x) AND Parent(?x, ?y) THEN Child(?y, ?x)"]
        
        inferred = self.reasoner.infer_facts(facts, rules)
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0], "Child(Jane, John)")

    def test_clear_reset(self):
        self.reasoner.add_fact("Fact(1)")
        self.reasoner.add_rule("IF A THEN B")
        self.reasoner.clear()
        self.assertEqual(len(self.reasoner.facts), 0)
        self.assertEqual(len(self.reasoner.rules), 0)

    # --- Bug #354: founded_by predicate inference ---

    def test_infer_facts_with_multi_word_values(self):
        """Bug #354 — _match_pattern must match facts whose values contain spaces."""
        reasoner = Reasoner()
        for f in [
            {"source_name": "Steve Jobs",    "target_name": "Apple", "type": "founded_by"},
            {"source_name": "Steve Wozniak", "target_name": "Apple", "type": "founded_by"},
            {"source_name": "Ronald Wayne",  "target_name": "Apple", "type": "founded_by"},
        ]:
            reasoner.add_fact(f)

        inferred = reasoner.infer_facts(
            [],
            rules=["IF founded_by(?person, ?org) THEN is_founder(?person, ?org)"],
        )

        self.assertEqual(len(inferred), 3)
        self.assertIn("is_founder(Steve Jobs, Apple)", inferred)
        self.assertIn("is_founder(Steve Wozniak, Apple)", inferred)
        self.assertIn("is_founder(Ronald Wayne, Apple)", inferred)

    def test_match_pattern_pre_bound_variable(self):
        """_match_pattern must enforce pre-bound variable values."""
        reasoner = Reasoner()
        bindings = {"org": "Apple"}
        result = reasoner._match_pattern(
            "founded_by(?person, ?org)",
            "founded_by(Steve Jobs, Apple)",
            bindings,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["person"], "Steve Jobs")
        self.assertEqual(result["org"], "Apple")

    def test_match_pattern_binding_conflict_returns_none(self):
        """_match_pattern must return None when a bound variable doesn't match."""
        reasoner = Reasoner()
        bindings = {"org": "Google"}
        result = reasoner._match_pattern(
            "founded_by(?person, ?org)",
            "founded_by(Steve Jobs, Apple)",
            bindings,
        )
        self.assertIsNone(result)

    def test_match_pattern_single_word_values(self):
        """_match_pattern must still work for single-word values (regression guard)."""
        reasoner = Reasoner()
        result = reasoner._match_pattern("Person(?x)", "Person(John)", {})
        self.assertIsNotNone(result)
        self.assertEqual(result["x"], "John")


if __name__ == "__main__":
    unittest.main()
