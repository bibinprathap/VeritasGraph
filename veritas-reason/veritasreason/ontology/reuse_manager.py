"""
Ontology Reuse Manager Module

This module manages ontology reuse including research, evaluation, and integration
of existing ontologies (internal and external) and non-ontological resources. It
helps identify reusable ontologies, assess compatibility, and manage imports.

Key Features:
    - Research existing ontologies
    - Evaluate ontology alignment and compatibility
    - Assess interoperability benefits
    - Manage external ontology imports
    - Handle internal ontology reuse
    - Convert non-ontological resources to ontologies
    - Track reuse decisions and dependencies
    - Known ontology catalog (FOAF, Dublin Core, Schema.org)

Main Classes:
    - ReuseManager: Manager for ontology reuse
    - ReuseDecision: Dataclass representing a reuse decision

Example Usage:
    >>> from veritasreason.ontology import ReuseManager
    >>> manager = ReuseManager()
    >>> info = manager.research_ontology("http://xmlns.com/foaf/0.1/")
    >>> alignment = manager.evaluate_alignment(source_uri, target_ontology)
    >>> ontology = manager.import_external_ontology(source_uri, target_ontology)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class ReuseDecision:
    """Ontology reuse decision record."""

    source_uri: str
    decision: str  # 'reuse', 'partial', 'reject'
    reason: str
    imported_elements: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReuseManager:
    """
    Ontology reuse management system.

    • Research existing ontologies
    • Evaluate ontology alignment and compatibility
    • Assess interoperability benefits
    • Manage external ontology imports
    • Handle internal ontology reuse
    • Convert non-ontological resources to ontologies
    • Track reuse decisions and dependencies
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize reuse manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("reuse_manager")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.reuse_decisions: List[ReuseDecision] = []
        self.known_ontologies: Dict[str, Dict[str, Any]] = {}

        self._load_known_ontologies()

    def _load_known_ontologies(self) -> None:
        """Load known ontology catalog."""
        # Common ontology URIs
        self.known_ontologies = {
            "foaf": {
                "uri": "http://xmlns.com/foaf/0.1/",
                "name": "FOAF",
                "description": "Friend of a Friend vocabulary",
            },
            "dublin-core": {
                "uri": "http://purl.org/dc/elements/1.1/",
                "name": "Dublin Core",
                "description": "Dublin Core metadata vocabulary",
            },
            "schema.org": {
                "uri": "https://schema.org/",
                "name": "Schema.org",
                "description": "Schema.org vocabulary",
            },
        }

    def research_ontology(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Research existing ontology.

        Args:
            uri: Ontology URI

        Returns:
            Ontology information or None
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ReuseManager",
            message=f"Researching ontology: {uri}",
        )

        try:
            # Check known ontologies
            self.progress_tracker.update_tracking(
                tracking_id, message="Checking known ontologies..."
            )
            for key, info in self.known_ontologies.items():
                if info["uri"] == uri:
                    self.progress_tracker.stop_tracking(
                        tracking_id,
                        status="completed",
                        message=f"Found ontology in catalog: {key}",
                    )
                    return info

            # Try to load from URI (placeholder)
            self.logger.warning(f"Ontology not found in catalog: {uri}")
            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="Ontology not found in catalog"
            )
            return None

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def evaluate_alignment(
        self, source_uri: str, target_ontology: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate ontology alignment and compatibility.

        Args:
            source_uri: Source ontology URI
            target_ontology: Target ontology dictionary

        Returns:
            Alignment evaluation results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ReuseManager",
            message=f"Evaluating alignment for {source_uri}",
        )

        try:
            # Basic alignment check
            self.progress_tracker.update_tracking(
                tracking_id, message="Researching source ontology..."
            )
            source_info = self.research_ontology(source_uri)

            if not source_info:
                result = {
                    "compatible": False,
                    "score": 0.0,
                    "issues": ["Source ontology not found"],
                }
                self.progress_tracker.stop_tracking(
                    tracking_id, status="completed", message="Source ontology not found"
                )
                return result

            # Check namespace compatibility
            self.progress_tracker.update_tracking(
                tracking_id, message="Checking namespace compatibility..."
            )
            target_namespace = target_ontology.get("uri", "")
            namespace_compatible = not target_namespace.startswith(source_uri)

            # Calculate compatibility score
            score = 0.5 if namespace_compatible else 0.0

            result = {
                "compatible": score > 0.3,
                "score": score,
                "namespace_compatible": namespace_compatible,
                "issues": [] if namespace_compatible else ["Namespace conflict"],
            }

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Alignment evaluation complete: compatible={result['compatible']}, score={score:.2f}",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def assess_interoperability(
        self, source_uri: str, target_ontology: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess interoperability benefits.

        Args:
            source_uri: Source ontology URI
            target_ontology: Target ontology dictionary

        Returns:
            Interoperability assessment
        """
        alignment = self.evaluate_alignment(source_uri, target_ontology)

        benefits = []
        if alignment["compatible"]:
            benefits.append("Can reuse existing classes and properties")
            benefits.append("Improved interoperability with other systems")

        return {
            "benefits": benefits,
            "compatibility_score": alignment["score"],
            "recommendation": "reuse" if alignment["compatible"] else "reject",
        }

    def import_external_ontology(
        self, source_uri: str, target_ontology: Dict[str, Any], **options
    ) -> Dict[str, Any]:
        """
        Import external ontology elements.

        Args:
            source_uri: Source ontology URI
            target_ontology: Target ontology dictionary
            **options: Additional options

        Returns:
            Updated ontology with imports
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ReuseManager",
            message=f"Importing external ontology: {source_uri}",
        )

        try:
            # Add import to ontology
            self.progress_tracker.update_tracking(
                tracking_id, message="Adding import to ontology..."
            )
            if "imports" not in target_ontology:
                target_ontology["imports"] = []

            if source_uri not in target_ontology["imports"]:
                target_ontology["imports"].append(source_uri)

            # Record reuse decision
            self.progress_tracker.update_tracking(
                tracking_id, message="Recording reuse decision..."
            )
            decision = ReuseDecision(
                source_uri=source_uri,
                decision="reuse",
                reason="External ontology import",
                metadata={"imported_at": datetime.now().isoformat()},
            )
            self.reuse_decisions.append(decision)

            self.logger.info(f"Imported external ontology: {source_uri}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Imported external ontology: {source_uri}",
            )
            return target_ontology

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def convert_non_ontological_resource(
        self, resource: Dict[str, Any], **options
    ) -> Dict[str, Any]:
        """
        Convert non-ontological resource to ontology.

        Args:
            resource: Resource dictionary
            **options: Additional options

        Returns:
            Converted ontology dictionary
        """
        # Basic conversion
        ontology = {
            "name": resource.get("name", "ConvertedOntology"),
            "uri": resource.get("uri", ""),
            "version": "1.0",
            "classes": resource.get("classes", []),
            "properties": resource.get("properties", []),
            "metadata": {
                "converted_from": resource.get("type", "unknown"),
                "converted_at": datetime.now().isoformat(),
            },
        }

        return ontology

    def track_reuse_decision(
        self, source_uri: str, decision: str, reason: str, **metadata
    ) -> ReuseDecision:
        """
        Track reuse decision.

        Args:
            source_uri: Source ontology URI
            decision: Decision ('reuse', 'partial', 'reject')
            reason: Reason for decision
            **metadata: Additional metadata

        Returns:
            Reuse decision record
        """
        reuse_decision = ReuseDecision(
            source_uri=source_uri,
            decision=decision,
            reason=reason,
            metadata={"decided_at": datetime.now().isoformat(), **metadata},
        )

        self.reuse_decisions.append(reuse_decision)
        self.logger.info(f"Tracked reuse decision: {decision} for {source_uri}")

        return reuse_decision

    def get_reuse_history(self) -> List[ReuseDecision]:
        """Get reuse decision history."""
        return list(self.reuse_decisions)

    def list_known_ontologies(self) -> List[str]:
        """List known ontology URIs."""
        return list(self.known_ontologies.keys())
    
    def suggest_alignments(
        self, target: Dict[str, Any], source: Dict[str, Any], **options
    ) -> List[Dict[str, str]]:
        """
        Suggest alignments between a source and target ontology based on heuristics.
        """
        suggestions = []
        
        # Nested function for DRY
        
        def find_matches(target_items, source_items, entity_type):
            predicate = (
                "http://www.w3.org/2002/07/owl#equivalentClass" 
                if entity_type == "class" 
                else "http://www.w3.org/2002/07/owl#equivalentProperty"
            )
            
            # Build hash map of target entities by normalized name
            target_map = {}
            for t_item in target_items:
                t_uri = t_item.get("uri")
                t_name = t_item.get("name", "").strip().lower()
                if t_uri and t_name:
                    target_map.setdefault(t_name, []).append(t_uri)
                    
            # Single pass through source items checking the hash map
            for s_item in source_items:
                s_uri = s_item.get("uri")
                s_name = s_item.get("name", "").strip().lower()
                if not s_uri or not s_name:
                    continue
                    
                if s_name in target_map:
                    for t_uri in target_map[s_name]:
                        if s_uri != t_uri:
                            suggestions.append({
                                "source_uri": s_uri,
                                "target_uri": t_uri,
                                "predicate": predicate,
                                "reason": f"Exact label match for {entity_type}: '{s_item.get('name')}'"
                            })

        find_matches(target.get("classes", []), source.get("classes", []), "class")
        find_matches(target.get("properties", []), source.get("properties", []), "property")
        
        return suggestions
                

    def merge_ontology_data(
        self, target: Dict[str, Any], source: Dict[str, Any], **options
    ) -> Dict[str, Any]:
        """
        Merge source ontology data into target ontology.

        Merges classes, properties, and metadata from source to target.
        Handles deduplication based on URI and name.

        Args:
            target: Target ontology dictionary (modified in-place)
            source: Source ontology dictionary
            **options: Merge options:
                - overwrite: Whether to overwrite existing elements (default: False)
                - merge_metadata: Whether to merge metadata (default: True)

        Returns:
            Merged target ontology
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ReuseManager",
            message=f"Merging ontology {source.get('name', 'unknown')} into {target.get('name', 'unknown')}",
        )

        try:
            overwrite = options.get("overwrite", False)
            
            # Helper to merge lists of dicts (classes/properties)
            def merge_lists(target_list, source_list, key_field="uri"):
                existing_keys = {item.get(key_field): i for i, item in enumerate(target_list) if item.get(key_field)}
                
                for item in source_list:
                    key = item.get(key_field)
                    if not key:
                        # Fallback to name if URI missing
                        key = item.get("name")
                        
                    if key in existing_keys:
                        if overwrite:
                            target_list[existing_keys[key]] = item
                    else:
                        target_list.append(item)
                        if key:
                            existing_keys[key] = len(target_list) - 1

            # Merge Classes
            if "classes" in source:
                if "classes" not in target:
                    target["classes"] = []
                merge_lists(target["classes"], source["classes"])

            # Merge Properties
            if "properties" in source:
                if "properties" not in target:
                    target["properties"] = []
                merge_lists(target["properties"], source["properties"])

            # Merge Metadata
            if options.get("merge_metadata", True) and "metadata" in source:
                if "metadata" not in target:
                    target["metadata"] = {}
                # Update with source metadata, preserving target's specific fields if needed
                # Here we just update
                target["metadata"].update(source["metadata"])
                
            # Merge Imports
            if "imports" in source:
                if "imports" not in target:
                    target["imports"] = []
                for imp in source["imports"]:
                    if imp not in target["imports"]:
                        target["imports"].append(imp)
            
            if options.get("compute_alignments", False):
                self.progress_tracker.update_tracking(
                    tracking_id, message="Computing suggested alignments..."
                )
                suggested = self.suggest_alignments(target, source, **options)
                if suggested:
                    if "suggested_alignments" not in target:
                        target["suggested_alignments"] = []
                    target["suggested_alignments"].extend(suggested)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Merged ontology data successfully",
            )
            return target

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise
