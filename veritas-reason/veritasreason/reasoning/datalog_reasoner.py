"""
Datalog reasoner module

This module provides a native Datalog engine using bottom-up semi-naive fixpoint evaluation. 
It supports recursive rules, multi-hop inference, and guarantees termination on finite graphs.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple, Union

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

# data structs

@dataclass(frozen=True)
class DatalogFact:
    """Represents a ground truth fact."""
    predicate: str
    args: Tuple[str, ...]

class BodyAtom(NamedTuple):
    """Represents a single predicate condition in a rule's body."""
    predicate: str
    args: Tuple[str, ...]
    
@dataclass
class DatalogRule:
    """Represents a Horn clause rule."""
    head_predicate: str
    head_args: Tuple[str, ...]
    body: List[BodyAtom]


# datalog reasoner

class DatalogReasoner:
    """
    Datalog reasoning engine supporting recursive rule evaluation via semi-naive
    bottom-up fixpoint computation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        self.logger = get_logger("datalog_reasoner")
        self.config = config or {}
        self.config.update(kwargs)
        
        self.progress_tracker = get_progress_tracker()

        self._fact_index: Dict[str, Set[DatalogFact]] = defaultdict(set)
        self._all_facts: Set[DatalogFact] = set()

        self._rules: List[DatalogRule] = []
        self._derived: bool = False

        self._delta_old: Set[DatalogFact] = set()
        self._delta_new: Set[DatalogFact] = set()
        
    def clear(self) -> None:
        """Clear all facts and rules from the engine."""
        self._fact_index.clear()
        self._all_facts.clear()
        self._rules.clear()
        self._derived = False
        self._delta_old.clear()
        self._delta_new.clear()
    
    def add_fact(self, fact: Any) -> None:
        """
        Add a ground fact to the engine.
        Accepts strings like "parent(tom, bob)" or standard VeritasReason Dicts. 
        """
        parsed_fact = None
        
        if isinstance(fact, str):
            parsed_fact = self._parse_fact_string(fact)
        elif isinstance(fact, dict):
            if "subject" in fact and "predicate" in fact and "object" in fact:
                parsed_fact = DatalogFact(
                    predicate=str(fact["predicate"]).replace(' ', '_').lower(),
                    args=(str(fact["subject"]).replace(' ', '_').lower(), str(fact["object"]).replace(' ', '_').lower())
                )
            elif "source" in fact or "source_id" in fact or "source_name" in fact:
                source = fact.get("source", fact.get("source_name", fact.get("source_id")))
                target = fact.get("target", fact.get("target_name", fact.get("target_id")))
                rtype = fact.get("type", fact.get("relation", "connected_to"))
                if source and target:
                    parsed_fact = DatalogFact(
                        predicate=str(rtype).replace(' ', '_').lower(),
                        args=(str(source).replace(' ', '_').lower(), str(target).replace(' ', '_').lower())
                    )
                    
            elif "type" in fact and ("id" in fact or "name" in fact):
                name = fact.get("id", fact.get("name"))
                etype = fact.get("type", "entity")
                if name:
                    parsed_fact = DatalogFact(
                        predicate=str(etype).replace(' ', '_').lower(),
                        args=(str(name).replace(' ', '_').lower(),)
                    )
            

            if parsed_fact:
                for arg in parsed_fact.args:
                    if not arg:
                        raise ValueError("Facts cannot contain empty arguments")
                    if arg[0].isupper():
                        raise ValueError(f"Facts must be constants only. Found variable '{arg}' in {fact}")
        
        if parsed_fact is None and isinstance(fact, dict):
            self.logger.warning(f"Unrecognised dict fact format, skipping: {fact}")
            return

        if parsed_fact and parsed_fact not in self._all_facts:
            self._all_facts.add(parsed_fact)
            self._fact_index[parsed_fact.predicate].add(parsed_fact)
            self._derived = False

    def add_rule(self, rule_str: str) -> None:
        """ Add a Datalog rule using Horn clause syntax."""
        rule = self._parse_rule_string(rule_str)
        self._rules.append(rule)
        self._derived = False

    # Parsing helpers

    def _parse_fact_string(self, s: str) -> DatalogFact:
        """Parse 'predicate(arg1, arg2)' into a DatalogFact."""
        match = re.match(r'^\s*([a-zA-Z0-9_]+)\s*\(\s*([^)]+)\s*\)\s*\.?\s*$', s.strip())
        if not match:
            raise ValueError(f"Invalid fact syntax: {s}")
        
        predicate = match.group(1)
        args_str = match.group(2)
        args = tuple(arg.strip() for arg in args_str.split(','))
        
        for arg in args:
            if not arg:
                raise ValueError(f"Empty argument found in fact: {s}")
            if arg[0].isupper():
                raise ValueError(f"Facts must be constants only (no variables). Found variable '{arg}' in {s}")
                
        return DatalogFact(predicate, args)

    def _parse_rule_string(self, s: str) -> DatalogRule:
        """Parse 'head(X, Y) :- body1(X, Z), body2(Z, Y).' into a DatalogRule."""
        s = s.strip()
        if ":-" not in s:
            raise ValueError(f"Invalid rule syntax (missing ':-'): {s}")
            
        head_str, body_str = s.split(":-", 1)
        head_str = head_str.strip()
        body_str = body_str.strip().rstrip('.')
        
        # Parse head
        head_match = re.match(r'^([a-zA-Z0-9_]+)\s*\(\s*([^)]+)\s*\)$', head_str)
        if not head_match:
            raise ValueError(f"Invalid rule head syntax: {head_str}")
            
        head_pred = head_match.group(1)
        head_args = tuple(arg.strip() for arg in head_match.group(2).split(','))
        
        # Parse body atoms
        body = []
        atom_matches = re.findall(r'([a-zA-Z0-9_]+)\s*\(\s*([^)]+)\s*\)', body_str)
        if not atom_matches:
            raise ValueError(f"No valid body atoms found in rule: {s}")
            
        for pred, args_str in atom_matches:
            args = tuple(arg.strip() for arg in args_str.split(','))
            body.append(BodyAtom(pred, args))
            
        return DatalogRule(head_pred, head_args, body)
    
    # Unification & Instantiation

    
    def _is_variable(self, term: str) -> bool:
        """Variables strictly start with an uppercase letter."""
        return bool(term and term[0].isupper())
    
    def _unify(
        self,
        pattern_args: Tuple[str, ...],
        fact_args: Tuple[str, ...],
        bindings: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """
        Unifies a rule atom's pattern with a concrete fact.
        Optimized to prevent unnecessary dictionary allocations.
        """
        if len(pattern_args) != len(fact_args):
            return None
        
        new_additions = {}
        
        for p_arg, f_arg in zip(pattern_args, fact_args):
            if self._is_variable(p_arg):
                if p_arg in bindings:
                    if bindings[p_arg] != f_arg:
                        return None
                elif p_arg in new_additions:
                    if new_additions[p_arg] != f_arg:
                        return None
                else:
                    new_additions[p_arg] = f_arg
            else:
                if p_arg != f_arg:
                    return None
        
        if new_additions:
            return {**bindings, **new_additions}
        return bindings
    
    def _instantiate(self, args: Tuple[str, ...], bindings: Dict[str, str]) -> Optional[Tuple[str, ...]]:
        """Replaces variables in a tuple with their bound values."""
        result = []
        for arg in args:
            if self._is_variable(arg):
                if arg not in bindings:
                    return None
                result.append(bindings[arg])
            else:
                result.append(arg)
        
        return tuple(result)
    
    def _instantiate_fact(
        self, predicate: str, args: Tuple[str, ...], bindings: Dict[str, str]
    ) -> Optional[DatalogFact]:
        """Creates a concrete DatalogFact from a predicate, arguments, and bindings."""
        ground_args = self._instantiate(args, bindings)
        if ground_args is None:
            return None
        return DatalogFact(predicate, ground_args)
    
    # Semi-Naive Fixpoint Evaluation


    def derive_all(self) -> List[str]:
        """
        Executes bottom-up semi-naive evaluation until fixpoint is reached.
        Returns a list of all derived facts as strings.
        """
        if self._derived:
            return [f"{f.predicate}({', '.join(f.args)})" for f in self._all_facts]

        tracking_id = self.progress_tracker.start_tracking(
            module="reasoning",
            submodule="DatalogReasoner",
            message="Starting semi-naive fixpoint evaluation"
        )

        iteration = 0
        newly_derived_count = 0

        try:
            self._delta_new = self._all_facts.copy()

            while self._delta_new:
                iteration += 1

                # Shift deltas
                self._delta_old = self._delta_new
                self._delta_new = set()

                delta_index = defaultdict(set)
                for f in self._delta_old:
                    delta_index[f.predicate].add(f)

                for rule in self._rules:
                    new_facts = self._apply_rule(rule, delta_index)

                    for fact in new_facts:
                        if fact not in self._all_facts:
                            self._delta_new.add(fact)
                            self._all_facts.add(fact)
                            self._fact_index[fact.predicate].add(fact)
                            newly_derived_count += 1

                self.logger.debug(f"Datalog Iteration {iteration}: derived {len(self._delta_new)} new facts")

            self._derived = True
        finally:
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Fixpoint reached in {iteration} iterations. {newly_derived_count} new facts derived."
            )

        return [f"{f.predicate}({', '.join(f.args)})" for f in self._all_facts]

    def _apply_rule(
        self, rule: DatalogRule, delta_index: Optional[Dict[str, Set[DatalogFact]]] = None
    ) -> Set[DatalogFact]:
        """
        Evaluates a single rule.
        Uses semi-naive strategy if delta_index is provided, otherwise falls back to naive evaluation.
        """
        results = set()
        
        if not rule.body:
            fact = self._instantiate_fact(rule.head_predicate, rule.head_args, {})
            if fact:
                results.add(fact)
            return results

        is_seminaive = delta_index is not None
        evaluation_paths = range(len(rule.body)) if is_seminaive else [0]

        for delta_index_pos in evaluation_paths:
            bindings_list = [{}]
            
            for i, atom in enumerate(rule.body):
                new_bindings_list = []
                
                if is_seminaive and i == delta_index_pos:
                    candidate_facts = delta_index.get(atom.predicate, set())
                else:
                    candidate_facts = self._fact_index.get(atom.predicate, set())
                    
                for bindings in bindings_list:
                    for fact in candidate_facts:
                        merged_bindings = self._unify(atom.args, fact.args, bindings)
                        if merged_bindings is not None:
                            new_bindings_list.append(merged_bindings)
                            
                bindings_list = new_bindings_list
                if not bindings_list:
                    break
                    
            for final_bindings in bindings_list:
                head_fact = self._instantiate_fact(rule.head_predicate, rule.head_args, final_bindings)
                if head_fact:
                    results.add(head_fact)
                    
        return results
    
    # Query & ContextGraph Integration


    def query(self, pattern: str, bindings: dict = None) -> List[dict]:
        """
        Queries the derived fact set. Automatically runs derive_all() if rules exist.
        Syntax: "ancestor(tom, ?Y)" or "ancestor(tom, ?y)"
        Returns: [{"Y": "bob"}] or [{"y": "bob"}]
        """
        if self._rules and not self._derived:
            self.derive_all()
            
        match = re.match(r'^\s*([a-zA-Z0-9_]+)\s*\(\s*([^)]+)\s*\)\s*\.?\s*$', pattern.strip())
        if not match:
            raise ValueError(f"Invalid query syntax: {pattern}")
            
        pred = match.group(1)
        raw_args = tuple(arg.strip() for arg in match.group(2).split(','))
        
        query_vars = {}  
        pattern_args = []
        
        for i, arg in enumerate(raw_args):
            if arg.startswith('?'):
                var_name = arg[1:]
                if not var_name:
                    raise ValueError("Empty variable name after '?'")
                internal_var = var_name[0].upper() + var_name[1:]
                query_vars[i] = (var_name, internal_var)
                pattern_args.append(internal_var)
            elif self._is_variable(arg):
                query_vars[i] = (arg, arg)
                pattern_args.append(arg)
            else:
                pattern_args.append(arg)
                
        initial_bindings = {}
        for k, v in (bindings or {}).items():
            internal_k = k[0].upper() + k[1:] if k and not k[0].isupper() else k
            initial_bindings[internal_k] = v

        for i, arg in enumerate(pattern_args):
            if self._is_variable(arg) and arg in initial_bindings:
                pattern_args[i] = initial_bindings[arg] 
                
        results = []
        candidates = self._fact_index.get(pred, set())
        
        for fact in candidates:
            match_bindings = self._unify(tuple(pattern_args), fact.args, {})
            if match_bindings is not None:
                result_row = {}
                for idx, (orig_var, internal_var) in query_vars.items():
                    if internal_var in match_bindings:
                        result_row[orig_var] = match_bindings[internal_var]
                    elif internal_var in initial_bindings:
                        result_row[orig_var] = initial_bindings[internal_var]
                
                if result_row and result_row not in results:
                    results.append(result_row)
                    
        return results
    
    def load_from_graph(self, graph: Any) -> int:
        """
        Loads a ContextGraph into Datalog facts using central add_fact validation.
        """
        initial_count = len(self._all_facts)
        
        if hasattr(graph, 'find_edges') and hasattr(graph, 'find_nodes'):
            for edge_dict in graph.find_edges():
                self.add_fact(edge_dict)
            for node_dict in graph.find_nodes():
                self.add_fact(node_dict)
        else:
            if hasattr(graph, 'edges'):
                edges = graph.edges() if callable(graph.edges) else graph.edges
                for edge in edges:
                    self.add_fact(edge if isinstance(edge, dict) else edge.__dict__)
            
            if hasattr(graph, 'nodes'):
                nodes = graph.nodes() if callable(graph.nodes) else graph.nodes
                if isinstance(nodes, dict): 
                    nodes = nodes.values()
                for node in nodes:
                    self.add_fact(node if isinstance(node, dict) else node.__dict__)
                        
        facts_added = len(self._all_facts) - initial_count
        self.logger.info(f"Loaded {facts_added} facts from ContextGraph.")
        return facts_added
    
    