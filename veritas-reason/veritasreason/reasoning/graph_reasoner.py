"""
Graph Reasoner Module

This module provides a high-level GraphReasoner class that leverages LLMs
to perform natural language reasoning over knowledge graphs.
"""

from typing import Any, Dict, List, Optional, Union
from ..semantic_extract.providers import create_provider
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker

class GraphReasoner:
    """
    High-level Reasoner for Knowledge Graphs using LLMs.
    """

    def __init__(self, core=None, config=None, **kwargs):
        """
        Initialize the GraphReasoner.

        Args:
            core: VeritasReason core instance.
            config: Configuration dictionary.
            **kwargs: Additional configuration parameters.
        """
        self.logger = get_logger("graph_reasoner")
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True
        
        self.core = core
        # Priority: config arg -> core.config -> kwargs
        if config:
            self.config = config
        elif core and hasattr(core, "config"):
            self.config = core.config
        else:
            self.config = kwargs
            
        # Try to find provider and model info in various places
        # 1. From kwargs directly
        self.provider_name = kwargs.get("provider")
        self.model = kwargs.get("model")
        
        # 2. From config object/dict
        if not self.provider_name:
            if isinstance(self.config, dict):
                extraction_config = self.config.get("extraction") or self.config.get("llm_provider") or {}
                self.provider_name = extraction_config.get("provider")
                self.model = extraction_config.get("model")
            elif hasattr(self.config, "get"):
                extraction_config = self.config.get("extraction") or self.config.get("llm_provider") or {}
                if isinstance(extraction_config, dict):
                    self.provider_name = extraction_config.get("provider")
                    self.model = extraction_config.get("model")
                else:
                    # It might be an object
                    self.provider_name = getattr(extraction_config, "provider", None)
                    self.model = getattr(extraction_config, "model", None)

        # 3. Fallbacks
        self.provider_name = self.provider_name or "openai"
        
        # Initialize provider
        provider_config = {}
        if isinstance(self.config, dict):
            provider_config = self.config.get("extraction") or self.config.get("llm_provider") or {}
        elif hasattr(self.config, "get"):
            provider_config = self.config.get("extraction") or self.config.get("llm_provider") or {}

        # Merge with kwargs for overrides
        if isinstance(provider_config, dict):
            provider_config.update(kwargs)
        
        try:
            self.logger.info(f"Initializing GraphReasoner with provider: {self.provider_name}")
            self.provider = create_provider(self.provider_name, **provider_config)
        except Exception as e:
            self.logger.warning(f"Failed to initialize LLM provider for GraphReasoner: {e}")
            self.provider = None

    def reason(self, graph: Dict[str, Any], query: str, **options) -> str:
        """
        Reason over the provided knowledge graph to answer a query.

        Args:
            graph: The knowledge graph dictionary (entities, relationships).
            query: The natural language query.
            **options: Additional reasoning options.

        Returns:
            str: The reasoning result/answer.
        """
        if not self.provider:
            return "Error: LLM provider not initialized for GraphReasoner. Check your configuration."

        tracking_id = self.progress_tracker.start_tracking(
            module="reasoning",
            submodule="GraphReasoner",
            message=f"Reasoning over graph for query: {query[:50]}..."
        )

        try:
            # 1. Prepare graph context
            context = self._prepare_graph_context(graph)
            
            # 2. Build prompt
            prompt = self._build_reasoning_prompt(context, query)
            
            # 3. Generate response
            self.progress_tracker.update_tracking(tracking_id, message="Calling LLM for reasoning...")
            response = self.provider.generate(prompt, **options)
            
            self.progress_tracker.stop_tracking(tracking_id, status="completed")
            return response
            
        except Exception as e:
            self.logger.error(f"Reasoning failed: {e}")
            self.progress_tracker.stop_tracking(tracking_id, status="failed", message=str(e))
            return f"Error during reasoning: {str(e)}"

    def _prepare_graph_context(self, graph: Dict[str, Any]) -> str:
        """Convert graph to a text representation for the LLM."""
        entities = graph.get("entities", [])
        relationships = graph.get("relationships", [])
        
        context_lines = ["Knowledge Graph Context:"]
        
        if entities:
            context_lines.append("\nEntities:")
            for ent in entities:
                name = ent.get("name", ent.get("id", "Unknown"))
                etype = ent.get("type", "Entity")
                props = ent.get("properties", {})
                props_str = f" ({props})" if props else ""
                context_lines.append(f"- {name} [{etype}]{props_str}")
                
        if relationships:
            context_lines.append("\nRelationships:")
            for rel in relationships:
                src = rel.get("source", rel.get("source_id", "Unknown"))
                tgt = rel.get("target", rel.get("target_id", "Unknown"))
                rtype = rel.get("type", "Relationship")
                props = rel.get("properties", {})
                props_str = f" ({props})" if props else ""
                context_lines.append(f"- {src} --[{rtype}]--> {tgt}{props_str}")
                
        return "\n".join(context_lines)

    def _build_reasoning_prompt(self, context: str, query: str) -> str:
        """Build the expert reasoning prompt."""
        return f"""You are an advanced Knowledge Graph Reasoning Assistant. 
Use the following graph data to answer the user's question accurately.
If the information is not in the graph, state that clearly but try to provide the best possible reasoning based on what's available.

{context}

Question: {query}

Answer strictly based on the provided graph context. Provide a concise yet thorough explanation."""
