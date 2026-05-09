"""
Decision Context Module

This module provides decision context management capabilities that integrate
vector stores and knowledge graphs for comprehensive decision tracking and
precedent search.

Key Features:
    - Decision context management with automatic embedding
    - Hybrid precedent search combining semantic + structural
    - Multi-hop reasoning for decision context
    - Integration with vector store and graph store
    - User-friendly API for decision operations

Main Classes:
    - DecisionContext: High-level interface for decision context management

Example Usage:
    >>> from veritasreason.context import DecisionContext
    >>> context = DecisionContext(vector_store=vs, graph_store=gs)
    >>> decision_id = context.record_decision(
    ...     scenario="Credit limit increase",
    ...     reasoning="Good payment history",
    ...     outcome="approved"
    ... )
    >>> precedents = context.find_similar_decisions("Credit limit increase")
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
from datetime import datetime, timezone

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from ..vector_store.decision_embedding_pipeline import DecisionEmbeddingPipeline
from ..vector_store.decision_vector_methods import set_global_vector_store
from .context_retriever import ContextRetriever, RetrievedContext


class DecisionContext:
    """
    Decision context manager for comprehensive decision tracking.
    
    This class provides a high-level interface for managing decision contexts,
    integrating vector stores for semantic embeddings and knowledge graphs for
    structural context, enabling sophisticated decision tracking and precedent search.
    
    Features:
        - Automatic decision embedding generation
        - Hybrid precedent search (semantic + structural)
        - Multi-hop reasoning for context expansion
        - Integration with vector and graph stores
        - User-friendly API with sensible defaults
        - Decision explanation generation
        - Batch processing capabilities
    
    Example Usage:
        >>> context = DecisionContext(vector_store=vs, graph_store=gs)
        >>> decision_id = context.record_decision(
        ...     scenario="Credit limit increase for high-value customer",
        ...     reasoning="Excellent payment history and low risk profile",
        ...     outcome="approved",
        ...     confidence=0.85
        ... )
        >>> precedents = context.find_similar_decisions(
        ...     scenario="Credit limit increase",
        ...     limit=5,
        ...     use_hybrid_search=True
        ... )
    """
    
    def __init__(
        self,
        vector_store: Any,
        graph_store: Optional[Any] = None,
        auto_embed: bool = True,
        semantic_weight: float = 0.7,
        structural_weight: float = 0.3,
        max_hops: int = 3,
        **kwargs
    ):
        """
        Initialize decision context manager.
        
        Args:
            vector_store: Vector store for semantic embeddings
            graph_store: Graph store for structural embeddings
            auto_embed: Whether to automatically generate embeddings
            semantic_weight: Weight for semantic similarity
            structural_weight: Weight for structural similarity
            max_hops: Maximum hops for context expansion
            **kwargs: Additional configuration options
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.auto_embed = auto_embed
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        self.max_hops = max_hops
        
        self.logger = get_logger(__name__)
        self.progress_tracker = get_progress_tracker()
        
        # Set global vector store for convenience functions
        set_global_vector_store(vector_store)
        
        # Initialize decision pipeline
        pipeline_kwargs = {}
        if "use_graph_features" in kwargs:
            pipeline_kwargs["use_graph_features"] = kwargs.pop("use_graph_features")
        self.decision_pipeline = DecisionEmbeddingPipeline(
            vector_store=vector_store,
            graph_store=graph_store,
            auto_embed=auto_embed,
            semantic_weight=semantic_weight,
            structural_weight=structural_weight,
            **pipeline_kwargs
        )
        
        # Initialize context retriever
        self.context_retriever = ContextRetriever(
            vector_store=vector_store,
            knowledge_graph=graph_store,
            max_expansion_hops=max_hops,
            **kwargs
        )
        
        # Initialize vector store decision pipeline if needed
        if hasattr(vector_store, 'initialize_decision_pipeline'):
            vector_store.initialize_decision_pipeline(
                graph_store=graph_store,
                auto_embed=auto_embed,
                semantic_weight=semantic_weight,
                structural_weight=structural_weight
            )
    
    def record_decision(
        self,
        scenario: Optional[str] = None,
        reasoning: Optional[str] = None,
        outcome: Optional[str] = None,
        confidence: Optional[float] = None,
        entities: Optional[List[str]] = None,
        category: Optional[str] = None,
        **additional_metadata
    ) -> str:
        """
        Record a decision with automatic embedding generation.
        
        Args:
            scenario: Decision scenario description
            reasoning: Decision reasoning
            outcome: Decision outcome
            confidence: Decision confidence score (0.0 to 1.0)
            entities: List of entities involved
            category: Decision category
            **additional_metadata: Additional metadata
            
        Returns:
            Decision vector ID
        """
        if not scenario:
            raise ValueError("Missing required field: scenario")
        # Sanitize scenario for logging (remove sensitive data)
        safe_scenario = scenario[:30] if scenario else "unknown"
        tracking_id = self.progress_tracker.start_tracking(
            module="decision_context",
            submodule="DecisionContext",
            message=f"Recording decision: {safe_scenario}..."
        )
        
        try:
            # Use vector store's decision method if available
            if hasattr(self.vector_store, 'store_decision'):
                decision_id = self.vector_store.store_decision(
                    scenario=scenario,
                    reasoning=reasoning,
                    outcome=outcome,
                    confidence=confidence,
                    entities=entities,
                    category=category,
                    **additional_metadata
                )
            else:
                # Use decision pipeline
                decision_data = {
                    "scenario": scenario,
                    "reasoning": reasoning or "",
                    "outcome": outcome or "unknown",
                    "confidence": confidence or 0.5,
                    "entities": entities or [],
                    "category": category or "general",
                    **additional_metadata
                }
                
                result = self.decision_pipeline.process_decision(decision_data)
                decision_id = result["vector_id"]
            
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Recorded decision with ID: {decision_id}"
            )
            
            return decision_id
            
        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise
    
    def find_similar_decisions(
        self,
        scenario: str,
        limit: int = 10,
        use_hybrid_search: bool = True,
        max_hops: Optional[int] = None,
        include_context: bool = True,
        semantic_weight: Optional[float] = None,
        structural_weight: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar decisions using hybrid search.
        
        Args:
            scenario: Decision scenario to search for
            limit: Number of results to return
            use_hybrid_search: Whether to use hybrid similarity
            max_hops: Maximum hops for context expansion
            include_context: Whether to include contextual information
            semantic_weight: Override semantic weight
            structural_weight: Override structural weight
            filters: Optional metadata filters
            
        Returns:
            List of similar decisions with scores and context
        """
        # Use provided weights or defaults
        sem_weight = semantic_weight or self.semantic_weight
        struct_weight = structural_weight or self.structural_weight
        hops = max_hops or self.max_hops
        
        # Use context retriever for hybrid search
        precedents = self.context_retriever.retrieve_decision_precedents(
            query=scenario,
            limit=limit,
            use_hybrid_search=use_hybrid_search,
            semantic_weight=sem_weight,
            structural_weight=struct_weight,
            max_hops=hops,
            include_context=include_context,
            filters=filters
        )
        
        return list(precedents)
    
    def query_decisions(
        self,
        query: str,
        max_hops: Optional[int] = None,
        include_context: bool = True,
        use_hybrid_search: bool = False,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query decisions with multi-hop reasoning capabilities.
        
        Args:
            query: Natural language query
            max_hops: Maximum hops for context expansion
            include_context: Whether to include contextual information
            use_hybrid_search: Whether to use hybrid search
            limit: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of query results
        """
        hops = max_hops or self.max_hops
        
        precedents = self.context_retriever.query_decisions(
            query=query,
            max_hops=hops,
            include_context=include_context,
            use_hybrid_search=use_hybrid_search,
            limit=limit,
            filters=filters
        )
        
        # Convert to dict format
        results = []
        for precedent in precedents:
            result = {
                "content": precedent.content,
                "score": precedent.score,
                "source": precedent.source,
                "metadata": precedent.metadata,
                "related_entities": precedent.related_entities,
                "related_relationships": precedent.related_relationships
            }
            results.append(result)
        
        return results
    
    def get_decision_context(
        self,
        decision_id: str,
        depth: int = 2,
        include_entities: bool = True,
        include_policies: bool = True,
        max_hops: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for a specific decision.
        
        Args:
            decision_id: Decision vector ID
            depth: Context depth
            include_entities: Whether to include entities
            include_policies: Whether to include policies
            max_hops: Maximum hops for context expansion
            
        Returns:
            Comprehensive decision context
        """
        hops = max_hops or self.max_hops
        
        context = self.context_retriever.get_decision_context(
            decision_id=decision_id,
            depth=depth,
            include_entities=include_entities,
            include_policies=include_policies,
            max_hops=hops
        )
        
        return {
            "content": context.content,
            "score": context.score,
            "source": context.source,
            "metadata": context.metadata,
            "related_entities": context.related_entities,
            "related_relationships": context.related_relationships
        }
    
    def explain_decision(
        self,
        decision_id: str,
        include_paths: bool = True,
        include_confidence: bool = True,
        include_weights: bool = True
    ) -> Dict[str, Any]:
        """
        Generate explanation for a decision.
        
        Args:
            decision_id: Decision vector ID
            include_paths: Whether to include reasoning paths
            include_confidence: Whether to include confidence scores
            include_weights: Whether to include similarity weights
            
        Returns:
            Decision explanation
        """
        if hasattr(self.vector_store, 'explain_decision'):
            return self.vector_store.explain_decision(
                decision_id=decision_id,
                include_paths=include_paths,
                include_confidence=include_confidence,
                include_weights=include_weights
            )
        else:
            # Fallback explanation
            metadata = self.vector_store.get_metadata(decision_id)
            if not metadata:
                raise ValueError(f"Decision {decision_id} not found")
            
            explanation = {
                "decision_id": decision_id,
                "scenario": metadata.get("scenario", ""),
                "reasoning": metadata.get("reasoning", ""),
                "outcome": metadata.get("outcome", ""),
                "timestamp": metadata.get("timestamp", "")
            }
            
            if include_confidence:
                explanation["confidence"] = metadata.get("confidence", 0.5)
            
            if include_weights:
                explanation["semantic_weight"] = self.semantic_weight
                explanation["structural_weight"] = self.structural_weight
            
            if include_paths:
                # Find similar decisions for reasoning paths
                similar_decisions = self.find_similar_decisions(
                    scenario=metadata.get("scenario", ""),
                    limit=3,
                    use_hybrid_search=True
                )
                explanation["similar_decisions"] = similar_decisions
            
            return explanation
    
    def process_decision_batch(
        self,
        decisions: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """
        Process multiple decisions efficiently in batch.
        
        Args:
            decisions: List of decision data dictionaries
            batch_size: Batch size for processing
            
        Returns:
            List of processed decision results
        """
        if hasattr(self.vector_store, 'process_decision_batch'):
            return self.vector_store.process_decision_batch(decisions, batch_size)
        else:
            # Use decision pipeline
            return self.decision_pipeline.process_decision_batch(
                decisions, batch_size=batch_size
            )
    
    def update_similarity_weights(
        self,
        semantic_weight: float,
        structural_weight: float
    ) -> None:
        """
        Update similarity weights for hybrid search.
        
        Args:
            semantic_weight: Weight for semantic similarity
            structural_weight: Weight for structural similarity
        """
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        
        # Update pipeline weights
        self.decision_pipeline.update_weights(semantic_weight, structural_weight)
        
        # Update vector store weights if available
        if hasattr(self.vector_store, 'decision_pipeline'):
            self.vector_store.decision_pipeline.update_weights(
                semantic_weight, structural_weight
            )
        
        self.logger.info(f"Updated similarity weights: semantic={semantic_weight}, structural={structural_weight}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get decision context statistics.
        
        Returns:
            Statistics about decisions and context
        """
        stats = {
            "semantic_weight": self.semantic_weight,
            "structural_weight": self.structural_weight,
            "max_hops": self.max_hops,
            "has_graph_store": self.graph_store is not None,
            "auto_embed": self.auto_embed
        }
        
        # Add vector store statistics
        if hasattr(self.vector_store, 'vectors'):
            stats["total_decisions"] = len(self.vector_store.vectors)
        
        # Add pipeline statistics
        if hasattr(self.decision_pipeline, 'get_statistics'):
            pipeline_stats = self.decision_pipeline.get_statistics()
            stats.update(pipeline_stats)
        
        return stats
