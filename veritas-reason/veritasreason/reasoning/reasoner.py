"""
Reasoner Module

This module provides a high-level Reasoner class that unifies various reasoning strategies
supported by the VeritasReason framework. It serves as a facade for different reasoning engines.
"""

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

class RuleType(Enum):
    """Rule types."""
    IMPLICATION = "implication"
    EQUIVALENCE = "equivalence"
    CONSTRAINT = "constraint"
    TRANSFORMATION = "transformation"

@dataclass
class Rule:
    """Simplified rule definition."""
    rule_id: str
    name: str
    conditions: List[Any]
    conclusion: Any
    rule_type: RuleType = RuleType.IMPLICATION
    confidence: float = 1.0
    priority: int = 0
    handler: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Fact:
    """Simple fact representation."""
    fact_id: str
    predicate: str
    arguments: List[Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.predicate}({', '.join(map(str, self.arguments))})"

@dataclass
class InferenceResult:
    """Result of an inference step."""
    conclusion: str
    rule_used: Optional[Rule] = None
    premises: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class Reasoner:
    """
    High-level Reasoner class for knowledge graph inference.
    
    This class provides a unified interface for applying reasoning rules to facts
    or knowledge graphs.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the Reasoner.
        
        Args:
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("reasoner")
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True
        self.config = kwargs
        
        self.rules: List[Rule] = []
        self.facts: Set[str] = set()
        self.rule_counter = 0
            
    def add_rule(self, rule_def: Union[str, Rule]) -> Rule:
        """Add a rule to the reasoner."""
        if isinstance(rule_def, Rule):
            rule = rule_def
        else:
            rule = self._parse_rule_definition(rule_def)
            
        self.rules.append(rule)
        # Sort rules by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        return rule
        
    def add_fact(self, fact: Union[str, Dict[str, Any]]) -> None:
        """Add a fact to working memory."""
        if isinstance(fact, str):
            self.facts.add(fact.strip())
        elif isinstance(fact, dict):
            # Convert KG-style dict to fact strings
            if "type" in fact and ("name" in fact or "id" in fact):
                name = fact.get("name", fact.get("id"))
                etype = fact.get("type", "Entity")
                self.facts.add(f"{etype}({name})")
            elif "source_id" in fact or "source_name" in fact:
                source = fact.get("source_name", fact.get("source_id"))
                target = fact.get("target_name", fact.get("target_id"))
                rtype = fact.get("type", "Relationship")
                self.facts.add(f"{rtype}({source}, {target})")

    def infer_facts(
        self, 
        facts: Union[List[Any], Dict[str, Any]], 
        rules: Optional[List[Union[str, Rule]]] = None
    ) -> List[Any]:
        """
        Infer new facts from existing facts or a knowledge graph.
        
        Args:
            facts: List of initial facts or a knowledge graph dictionary.
            rules: List of rules to apply (strings or Rule objects)
            
        Returns:
            List of inferred facts (conclusions)
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="reasoning",
            submodule="Reasoner",
            message="Inferring facts"
        )
        
        try:
            if isinstance(facts, list):
                for f in facts:
                    self.add_fact(f)
            else:
                self.add_fact(facts)

            if rules:
                for rule in rules:
                    self.add_rule(rule)
            
            # Perform inference
            results = self.forward_chain()
                
            # Extract conclusions from results
            inferred_facts = [result.conclusion for result in results]
            
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Inferred {len(inferred_facts)} new facts"
            )
            
            return inferred_facts
            
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, 
                status="failed", 
                message=str(e)
            )
            self.logger.error(f"Inference failed: {e}")
            raise

    def forward_chain(self) -> List[InferenceResult]:
        """Derive all possible new facts using forward chaining."""
        tracking_id = self.progress_tracker.start_tracking(
            module="reasoning",
            submodule="Reasoner",
            message="Performing forward chaining"
        )
        
        results = []
        new_facts_added = True
        max_iterations = self.config.get("max_iterations", 50)
        iteration = 0
        
        while new_facts_added and iteration < max_iterations:
            new_facts_added = False
            iteration += 1
            
            for rule in self.rules:
                matches = self._match_rule(rule)
                for conclusion in matches:
                    if conclusion not in self.facts:
                        self.facts.add(conclusion)
                        results.append(InferenceResult(
                            conclusion=conclusion,
                            rule_used=rule,
                            confidence=rule.confidence
                        ))
                        new_facts_added = True
                        
        self.progress_tracker.stop_tracking(
            tracking_id,
            status="completed",
            message=f"Forward chaining completed: {len(results)} new facts inferred"
        )
        return results

    def backward_chain(self, goal: str, max_depth: int = 10) -> Optional[InferenceResult]:
        """
        Prove a goal using backward chaining.
        
        Args:
            goal: The fact string to prove
            max_depth: Maximum recursion depth
            
        Returns:
            InferenceResult if proven, None otherwise
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="reasoning",
            submodule="Reasoner",
            message="Performing backward chaining"
        )
        
        try:
            result = self._prove_goal(goal, depth=0, max_depth=max_depth)
            
            status = "completed" if result else "not_proven"
            self.progress_tracker.stop_tracking(
                tracking_id,
                status=status,
                message=f"Backward chaining finished: {'Proven' if result else 'Not proven'}"
            )
            return result
        except Exception as e:
            self.progress_tracker.stop_tracking(tracking_id, status="failed", message=str(e))
            raise

    def _prove_goal(self, goal: str, depth: int, max_depth: int) -> Optional[InferenceResult]:
        """Recursive goal prover."""
        if depth > max_depth:
            return None
            
        # 1. Check if goal is already in facts
        if goal in self.facts:
            return InferenceResult(conclusion=goal, premises=[])
            
        # 2. Check if goal matches a known fact pattern (unification)
        for fact in self.facts:
            if self._match_pattern(goal, fact, {}) is not None:
                return InferenceResult(conclusion=fact, premises=[])
                
        # 3. Try to prove via rules
        for rule in self.rules:
            # Check if rule conclusion can match the goal
            initial_bindings = self._match_pattern(rule.conclusion, goal, {})
            if initial_bindings is not None:
                # Try to prove all conditions
                all_conditions_proven = True
                premises = []
                current_bindings = initial_bindings.copy()
                
                for condition in rule.conditions:
                    instantiated_cond = self._substitute(condition, current_bindings)
                    cond_result = self._prove_goal(instantiated_cond, depth + 1, max_depth)
                    
                    if cond_result:
                        premises.append(cond_result.conclusion)
                        # Update bindings from the actual fact that matched
                        new_bindings = self._match_pattern(condition, cond_result.conclusion, current_bindings)
                        if new_bindings:
                            current_bindings = new_bindings
                    else:
                        all_conditions_proven = False
                        break
                        
                if all_conditions_proven:
                    instantiated_conclusion = self._substitute(rule.conclusion, current_bindings)
                    return InferenceResult(
                        conclusion=instantiated_conclusion,
                        rule_used=rule,
                        premises=premises,
                        confidence=rule.confidence
                    )
                    
        return None

    def _parse_rule_definition(self, definition: str) -> Rule:
        """Parse IF-THEN rule strings."""
        definition = definition.strip()
        if_match = re.match(r"IF\s+(.+?)\s+THEN\s+(.+)$", definition, re.IGNORECASE | re.DOTALL)
        
        if not if_match:
            # Fallback or error
            self.rule_counter += 1
            return Rule(f"rule_{self.rule_counter}", f"Rule {self.rule_counter}", [], definition)
            
        conditions_str = if_match.group(1)
        conclusion_str = if_match.group(2)
        
        # Split conditions by AND
        conditions = [c.strip() for c in re.split(r"\s+AND\s+", conditions_str, flags=re.IGNORECASE)]
        
        self.rule_counter += 1
        return Rule(
            rule_id=f"rule_{self.rule_counter}",
            name=f"Rule {self.rule_counter}",
            conditions=conditions,
            conclusion=conclusion_str.strip()
        )
        
    def _match_rule(self, rule: Rule) -> List[str]:
        """Match rule conditions against facts and return instantiated conclusions."""
        if not rule.conditions:
            return []
            
        bindings_list = [{}] # List of possible variable bindings
        
        for condition in rule.conditions:
            new_bindings_list = []
            for bindings in bindings_list:
                for fact in self.facts:
                    match_bindings = self._match_pattern(condition, fact, bindings)
                    if match_bindings is not None:
                        new_bindings_list.append(match_bindings)
            bindings_list = new_bindings_list
            if not bindings_list:
                break
                
        results = []
        for bindings in bindings_list:
            instantiated_conclusion = self._substitute(rule.conclusion, bindings)
            results.append(instantiated_conclusion)
            
        return results
        
    def _match_pattern(self, pattern: str, fact: str, initial_bindings: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Match a pattern against a fact with initial bindings."""
        # Split on ?var placeholders first, then escape only the literal segments.
        # This avoids re.escape() mangling the surrounding parentheses and ?
        # before the variable substitution step.
        segments = re.split(r"(\?\w+)", pattern)
        seen_vars: set = set()
        p_regex = ""
        for seg in segments:
            if seg.startswith("?"):
                var_name = seg[1:]
                if var_name in initial_bindings:
                    # Already bound — require the exact literal value
                    p_regex += re.escape(initial_bindings[var_name])
                elif var_name in seen_vars:
                    # Same variable used twice — use a backreference
                    p_regex += f"(?P={var_name})"
                else:
                    p_regex += f"(?P<{var_name}>.+?)"
                    seen_vars.add(var_name)
            else:
                p_regex += re.escape(seg)
        p_regex = f"^{p_regex}$"

        # Simple regex-based matcher for patterns like "Person(?x)" and facts like "Person(John)"
        
        try:
            match = re.match(p_regex, fact)
            if match:
                new_bindings = initial_bindings.copy()
                for var, value in match.groupdict().items():
                    if var in new_bindings and new_bindings[var] != value:
                        return None  # Binding conflict
                    new_bindings[var] = value
                return new_bindings
        except Exception as e:
            self.logger.warning(f"Error matching pattern '{pattern}' (regex: '{p_regex}') against fact '{fact}': {e}")
            
        return None
        
    def _substitute(self, pattern: str, bindings: Dict[str, str]) -> str:
        """Substitute variables in a pattern with bound values."""
        result = pattern
        for var, value in bindings.items():
            result = result.replace(f"?{var}", value)
        return result
        
    def clear(self) -> None:
        """Clear facts and rules."""
        self.facts.clear()
        self.rules.clear()
        self.rule_counter = 0

    def reset(self) -> None:
        """Alias for clear()."""
        self.clear()
