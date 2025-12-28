"""
Reasoning Trace Builder for Veritas-Scope.
Transforms GraphRAG context data into visualization-ready graph structures.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
from datetime import datetime
import hashlib

from .models import (
    GraphNode, GraphLink, ReasoningStep, ProvenanceInfo,
    ReasoningTraceGraph, NodeType, NodeStatus
)

log = logging.getLogger(__name__)

# Color palette for different node types
NODE_COLORS = {
    NodeType.QUERY: "#FF6B6B",      # Red - Query
    NodeType.ENTITY: "#4ECDC4",     # Teal - Entities
    NodeType.TEXT_UNIT: "#45B7D1",  # Blue - Text Units
    NodeType.COMMUNITY: "#96CEB4",  # Green - Communities
    NodeType.DOCUMENT: "#FFEAA7",   # Yellow - Documents
    NodeType.ANSWER: "#DDA0DD",     # Plum - Answer
}

LINK_COLORS = {
    "reasoning_path": "#FF6B6B",    # Red for reasoning path
    "relationship": "#888888",       # Gray for regular relationships
    "source": "#45B7D1",            # Blue for source links
}


class ReasoningTraceBuilder:
    """Builds reasoning trace graphs from GraphRAG context data."""
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.links: List[GraphLink] = []
        self.reasoning_steps: List[ReasoningStep] = []
        self.provenance: List[ProvenanceInfo] = []
        self.hop_counter = 0
        self.step_counter = 0
        
    def reset(self):
        """Reset the builder for a new query."""
        self.nodes = {}
        self.links = []
        self.reasoning_steps = []
        self.provenance = []
        self.hop_counter = 0
        self.step_counter = 0
    
    def _generate_id(self, prefix: str, content: str) -> str:
        """Generate a unique ID for a node or link."""
        hash_input = f"{prefix}:{content}"
        return f"{prefix}_{hashlib.md5(hash_input.encode()).hexdigest()[:8]}"
    
    def add_query_node(self, query: str) -> GraphNode:
        """Add the initial query node."""
        node_id = self._generate_id("query", query)
        node = GraphNode(
            id=node_id,
            label=query[:50] + "..." if len(query) > 50 else query,
            type=NodeType.QUERY,
            status=NodeStatus.ACTIVE,
            description=query,
            color=NODE_COLORS[NodeType.QUERY],
            size=20,
            metadata={"full_query": query}
        )
        self.nodes[node_id] = node
        
        # Add reasoning step
        self._add_step(
            action="query_received",
            description=f"Received query: {query[:100]}...",
            nodes_involved=[node_id]
        )
        
        return node
    
    def add_entity_nodes(
        self, 
        entities_df: pd.DataFrame, 
        entry_entities: List[str] = None
    ) -> List[GraphNode]:
        """Add entity nodes from context data."""
        if entities_df is None or entities_df.empty:
            return []
        
        entry_entities = entry_entities or []
        added_nodes = []
        
        for _, row in entities_df.iterrows():
            entity_id = str(row.get('id', row.get('title', '')))
            entity_title = str(row.get('title', entity_id))
            
            is_entry = entity_title.lower() in [e.lower() for e in entry_entities]
            
            node = GraphNode(
                id=self._generate_id("entity", entity_id),
                label=entity_title,
                type=NodeType.ENTITY,
                status=NodeStatus.ENTRY_POINT if is_entry else NodeStatus.TRAVERSED,
                description=str(row.get('description', ''))[:500],
                rank=float(row.get('rank', 1)),
                community_id=str(row.get('community', '')) if pd.notna(row.get('community')) else None,
                color=NODE_COLORS[NodeType.ENTITY],
                size=12 + (float(row.get('rank', 1)) * 2),
                metadata={
                    "entity_type": str(row.get('type', 'unknown')),
                    "in_context": bool(row.get('in_context', True))
                }
            )
            self.nodes[node.id] = node
            added_nodes.append(node)
        
        if added_nodes:
            self._add_step(
                action="entity_extraction",
                description=f"Identified {len(added_nodes)} relevant entities via vector search",
                nodes_involved=[n.id for n in added_nodes[:10]]  # Limit for readability
            )
        
        return added_nodes
    
    def add_relationship_links(
        self, 
        relationships_df: pd.DataFrame,
        mark_reasoning_path: List[Tuple[str, str]] = None
    ) -> List[GraphLink]:
        """Add relationship links between entities."""
        if relationships_df is None or relationships_df.empty:
            return []
        
        mark_reasoning_path = mark_reasoning_path or []
        added_links = []
        
        for _, row in relationships_df.iterrows():
            source_title = str(row.get('source', ''))
            target_title = str(row.get('target', ''))
            
            # Find matching nodes
            source_node = None
            target_node = None
            
            for node_id, node in self.nodes.items():
                if node.label.lower() == source_title.lower():
                    source_node = node
                if node.label.lower() == target_title.lower():
                    target_node = node
            
            if source_node and target_node:
                is_reasoning = (source_title, target_title) in mark_reasoning_path
                
                link = GraphLink(
                    id=self._generate_id("rel", f"{source_node.id}-{target_node.id}"),
                    source=source_node.id,
                    target=target_node.id,
                    relationship=str(row.get('description', 'related_to'))[:100],
                    weight=float(row.get('weight', 1.0)),
                    is_reasoning_path=is_reasoning,
                    hop_order=self.hop_counter if is_reasoning else None,
                    color=LINK_COLORS["reasoning_path"] if is_reasoning else LINK_COLORS["relationship"],
                    width=3 if is_reasoning else 1,
                    animated=is_reasoning
                )
                self.links.append(link)
                added_links.append(link)
                
                if is_reasoning:
                    self.hop_counter += 1
        
        if added_links:
            reasoning_count = sum(1 for l in added_links if l.is_reasoning_path)
            self._add_step(
                action="relationship_traversal",
                description=f"Traversed {len(added_links)} relationships ({reasoning_count} in reasoning path)",
                links_traversed=[l.id for l in added_links if l.is_reasoning_path]
            )
        
        return added_links
    
    def add_text_unit_nodes(
        self, 
        text_units_df: pd.DataFrame
    ) -> List[GraphNode]:
        """Add text unit (source) nodes."""
        if text_units_df is None or text_units_df.empty:
            return []
        
        added_nodes = []
        
        for _, row in text_units_df.iterrows():
            unit_id = str(row.get('id', ''))
            text_content = str(row.get('text', ''))[:200]
            
            node = GraphNode(
                id=self._generate_id("text", unit_id),
                label=f"Source: {text_content[:30]}...",
                type=NodeType.TEXT_UNIT,
                status=NodeStatus.SOURCE,
                description=text_content,
                source_text=str(row.get('text', ''))[:1000],
                document_id=str(row.get('document_ids', '')) if pd.notna(row.get('document_ids')) else None,
                color=NODE_COLORS[NodeType.TEXT_UNIT],
                size=8,
                metadata={
                    "in_context": bool(row.get('in_context', True)),
                    "n_tokens": int(row.get('n_tokens', 0)) if pd.notna(row.get('n_tokens')) else 0
                }
            )
            self.nodes[node.id] = node
            added_nodes.append(node)
            
            # Add provenance
            self.provenance.append(ProvenanceInfo(
                source_id=unit_id,
                source_type="text_unit",
                source_text=str(row.get('text', ''))[:2000],
                relevance_score=float(row.get('rank', 0.5)) if pd.notna(row.get('rank')) else 0.5
            ))
        
        if added_nodes:
            self._add_step(
                action="source_retrieval",
                description=f"Retrieved {len(added_nodes)} source text units",
                nodes_involved=[n.id for n in added_nodes[:5]]
            )
        
        return added_nodes
    
    def add_community_nodes(
        self, 
        reports_df: pd.DataFrame
    ) -> List[GraphNode]:
        """Add community report nodes."""
        if reports_df is None or reports_df.empty:
            return []
        
        added_nodes = []
        
        for _, row in reports_df.iterrows():
            community_id = str(row.get('id', row.get('community', '')))
            title = str(row.get('title', f'Community {community_id}'))
            
            node = GraphNode(
                id=self._generate_id("comm", community_id),
                label=title[:40],
                type=NodeType.COMMUNITY,
                status=NodeStatus.TRAVERSED,
                description=str(row.get('summary', ''))[:500],
                rank=float(row.get('rank', 1)),
                community_id=community_id,
                color=NODE_COLORS[NodeType.COMMUNITY],
                size=15,
                metadata={
                    "full_content": str(row.get('full_content', '')),
                    "in_context": bool(row.get('in_context', True))
                }
            )
            self.nodes[node.id] = node
            added_nodes.append(node)
        
        if added_nodes:
            self._add_step(
                action="community_analysis",
                description=f"Analyzed {len(added_nodes)} community reports for high-level insights",
                nodes_involved=[n.id for n in added_nodes[:5]]
            )
        
        return added_nodes
    
    def add_answer_node(self, answer: str, source_node_ids: List[str] = None) -> GraphNode:
        """Add the final answer node and connect to sources."""
        node_id = self._generate_id("answer", answer[:100])
        node = GraphNode(
            id=node_id,
            label="Generated Answer",
            type=NodeType.ANSWER,
            status=NodeStatus.FINAL,
            description=answer[:500],
            color=NODE_COLORS[NodeType.ANSWER],
            size=25,
            metadata={"full_answer": answer}
        )
        self.nodes[node_id] = node
        
        # Connect answer to source nodes
        source_node_ids = source_node_ids or []
        for source_id in source_node_ids[:10]:  # Limit connections
            if source_id in self.nodes:
                link = GraphLink(
                    id=self._generate_id("ans_link", f"{source_id}-{node_id}"),
                    source=source_id,
                    target=node_id,
                    relationship="supports_answer",
                    is_reasoning_path=True,
                    hop_order=self.hop_counter,
                    color=LINK_COLORS["reasoning_path"],
                    width=2,
                    animated=True
                )
                self.links.append(link)
                self.hop_counter += 1
        
        self._add_step(
            action="answer_generation",
            description="Generated answer from aggregated context",
            nodes_involved=[node_id]
        )
        
        return node
    
    def _add_step(
        self, 
        action: str, 
        description: str, 
        nodes_involved: List[str] = None,
        links_traversed: List[str] = None
    ):
        """Add a reasoning step."""
        self.step_counter += 1
        step = ReasoningStep(
            step_number=self.step_counter,
            action=action,
            description=description,
            nodes_involved=nodes_involved or [],
            links_traversed=links_traversed or [],
            timestamp=datetime.utcnow()
        )
        self.reasoning_steps.append(step)
    
    def build_from_context_data(
        self,
        query: str,
        answer: str,
        context_data: Dict[str, pd.DataFrame],
        entry_entities: List[str] = None
    ) -> ReasoningTraceGraph:
        """Build complete reasoning trace from GraphRAG context data."""
        self.reset()
        
        # 1. Add query node
        query_node = self.add_query_node(query)
        
        # 2. Add entities
        entities_df = context_data.get('entities')
        entity_nodes = self.add_entity_nodes(entities_df, entry_entities)
        
        # Connect query to entry point entities
        for entity in entity_nodes[:5]:  # Top 5 entry points
            if entity.status == NodeStatus.ENTRY_POINT:
                link = GraphLink(
                    id=self._generate_id("q_link", f"{query_node.id}-{entity.id}"),
                    source=query_node.id,
                    target=entity.id,
                    relationship="vector_search_hit",
                    is_reasoning_path=True,
                    hop_order=0,
                    color=LINK_COLORS["reasoning_path"],
                    width=2,
                    animated=True
                )
                self.links.append(link)
        
        # 3. Add relationships
        relationships_df = context_data.get('relationships')
        self.add_relationship_links(relationships_df)
        
        # 4. Add text units (sources)
        sources_df = context_data.get('sources')
        source_nodes = self.add_text_unit_nodes(sources_df)
        
        # 5. Add community reports
        reports_df = context_data.get('reports')
        self.add_community_nodes(reports_df)
        
        # 6. Connect entities to their text units
        self._connect_entities_to_sources()
        
        # 7. Add answer node
        source_ids = [n.id for n in entity_nodes[:5]] + [n.id for n in source_nodes[:3]]
        self.add_answer_node(answer, source_ids)
        
        # 8. Mark final nodes
        self._mark_final_reasoning_path()
        
        # Build the final graph
        return self._build_graph()
    
    def _connect_entities_to_sources(self):
        """Create links between entities and their source text units."""
        for node_id, node in list(self.nodes.items()):
            if node.type == NodeType.ENTITY:
                # Find related text units
                for other_id, other_node in self.nodes.items():
                    if other_node.type == NodeType.TEXT_UNIT:
                        # Simple heuristic: connect if entity label appears in source
                        if node.label.lower() in (other_node.source_text or "").lower():
                            link = GraphLink(
                                id=self._generate_id("src_link", f"{node_id}-{other_id}"),
                                source=node_id,
                                target=other_id,
                                relationship="mentioned_in",
                                color=LINK_COLORS["source"],
                                width=1
                            )
                            self.links.append(link)
    
    def _mark_final_reasoning_path(self):
        """Mark nodes that are part of the final reasoning path."""
        # Get all nodes connected via reasoning path links
        reasoning_node_ids = set()
        for link in self.links:
            if link.is_reasoning_path:
                reasoning_node_ids.add(link.source)
                reasoning_node_ids.add(link.target)
        
        # Update node statuses
        for node_id in reasoning_node_ids:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if node.status not in [NodeStatus.ACTIVE, NodeStatus.FINAL]:
                    node.status = NodeStatus.TRAVERSED
    
    def _build_graph(self) -> ReasoningTraceGraph:
        """Build the final ReasoningTraceGraph."""
        nodes_list = list(self.nodes.values())
        
        # Count statistics
        entry_count = sum(1 for n in nodes_list if n.status == NodeStatus.ENTRY_POINT)
        final_count = sum(1 for n in nodes_list if n.status == NodeStatus.FINAL)
        
        return ReasoningTraceGraph(
            nodes=nodes_list,
            links=self.links,
            reasoning_steps=self.reasoning_steps,
            provenance=self.provenance,
            total_nodes=len(nodes_list),
            total_links=len(self.links),
            total_hops=self.hop_counter,
            entry_nodes_count=entry_count,
            final_nodes_count=final_count
        )


def build_reasoning_trace(
    query: str,
    answer: str,
    context_data: Dict[str, pd.DataFrame],
    entry_entities: List[str] = None
) -> ReasoningTraceGraph:
    """
    Convenience function to build a reasoning trace graph.
    
    Args:
        query: The user's question
        answer: The generated answer
        context_data: Dictionary of DataFrames from GraphRAG context builder
        entry_entities: List of entity names that were entry points
    
    Returns:
        ReasoningTraceGraph ready for visualization
    """
    builder = ReasoningTraceBuilder()
    return builder.build_from_context_data(query, answer, context_data, entry_entities)
