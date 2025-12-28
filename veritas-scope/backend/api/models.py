"""
Pydantic models for Veritas-Scope API.
Defines the data structures for reasoning traces and graph visualization.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class NodeType(str, Enum):
    """Types of nodes in the reasoning graph."""
    ENTITY = "entity"
    TEXT_UNIT = "text_unit"
    COMMUNITY = "community"
    DOCUMENT = "document"
    QUERY = "query"
    ANSWER = "answer"


class NodeStatus(str, Enum):
    """Visual status of nodes during reasoning trace."""
    INACTIVE = "inactive"
    ENTRY_POINT = "entry_point"  # Initial vector search hits
    TRAVERSED = "traversed"      # Nodes visited during multi-hop
    ACTIVE = "active"            # Currently being processed
    FINAL = "final"              # Final answer nodes
    SOURCE = "source"            # Source document nodes


class GraphNode(BaseModel):
    """A node in the reasoning trace graph."""
    id: str = Field(..., description="Unique identifier for the node")
    label: str = Field(..., description="Display label for the node")
    type: NodeType = Field(..., description="Type of the node")
    status: NodeStatus = Field(default=NodeStatus.INACTIVE, description="Visual status")
    description: Optional[str] = Field(None, description="Node description")
    rank: Optional[float] = Field(None, description="Node importance rank")
    community_id: Optional[str] = Field(None, description="Community this node belongs to")
    source_text: Optional[str] = Field(None, description="Original source text snippet")
    document_id: Optional[str] = Field(None, description="Source document ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    # Visual properties
    size: Optional[float] = Field(default=10, description="Visual size of the node")
    color: Optional[str] = Field(None, description="Node color (hex)")
    x: Optional[float] = Field(None, description="X position")
    y: Optional[float] = Field(None, description="Y position")


class GraphLink(BaseModel):
    """A link/edge in the reasoning trace graph."""
    id: str = Field(..., description="Unique identifier for the link")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="Relationship type/description")
    weight: Optional[float] = Field(default=1.0, description="Edge weight")
    hop_order: Optional[int] = Field(None, description="Order in multi-hop traversal")
    is_reasoning_path: bool = Field(default=False, description="Part of reasoning path")
    
    # Visual properties
    color: Optional[str] = Field(None, description="Link color (hex)")
    width: Optional[float] = Field(default=1, description="Link width")
    animated: bool = Field(default=False, description="Whether to animate this link")


class ReasoningStep(BaseModel):
    """A single step in the multi-hop reasoning process."""
    step_number: int = Field(..., description="Step order in the reasoning chain")
    action: str = Field(..., description="Action taken (search, traverse, extract, etc.)")
    description: str = Field(..., description="Human-readable description of this step")
    nodes_involved: List[str] = Field(default_factory=list, description="Node IDs involved")
    links_traversed: List[str] = Field(default_factory=list, description="Link IDs traversed")
    timestamp: Optional[datetime] = Field(None, description="When this step occurred")
    confidence: Optional[float] = Field(None, description="Confidence score for this step")
    context_used: Optional[str] = Field(None, description="Context text used in this step")


class ProvenanceInfo(BaseModel):
    """Source attribution and provenance information."""
    source_id: str = Field(..., description="Source document/text unit ID")
    source_type: str = Field(..., description="Type of source (document, text_unit, etc.)")
    source_title: Optional[str] = Field(None, description="Title of the source")
    source_text: str = Field(..., description="The actual source text")
    relevance_score: Optional[float] = Field(None, description="Relevance to the answer")
    page_number: Optional[int] = Field(None, description="Page number in document")
    char_start: Optional[int] = Field(None, description="Character start position")
    char_end: Optional[int] = Field(None, description="Character end position")
    highlight_text: Optional[str] = Field(None, description="Specific text to highlight")


class ReasoningTraceGraph(BaseModel):
    """Complete reasoning trace graph for visualization."""
    nodes: List[GraphNode] = Field(default_factory=list, description="All nodes in the graph")
    links: List[GraphLink] = Field(default_factory=list, description="All links in the graph")
    reasoning_steps: List[ReasoningStep] = Field(default_factory=list, description="Ordered reasoning steps")
    provenance: List[ProvenanceInfo] = Field(default_factory=list, description="Source attributions")
    
    # Summary stats
    total_nodes: int = Field(default=0, description="Total number of nodes")
    total_links: int = Field(default=0, description="Total number of links")
    total_hops: int = Field(default=0, description="Number of reasoning hops")
    entry_nodes_count: int = Field(default=0, description="Number of entry point nodes")
    final_nodes_count: int = Field(default=0, description="Number of final answer nodes")


class QueryRequest(BaseModel):
    """Request model for a query with reasoning trace."""
    query: str = Field(..., description="The user's question")
    query_type: str = Field(default="local", description="Query type: 'local' or 'global'")
    output_folder: Optional[str] = Field(None, description="Output folder to search")
    community_level: int = Field(default=2, description="Community level for search")
    temperature: float = Field(default=0.5, description="LLM temperature")
    response_type: str = Field(default="Multiple Paragraphs", description="Response format")
    include_graph: bool = Field(default=True, description="Include reasoning trace graph")
    animate_trace: bool = Field(default=True, description="Enable trace animation data")


class QueryResponse(BaseModel):
    """Response model with answer and reasoning trace."""
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    reasoning_graph: Optional[ReasoningTraceGraph] = Field(None, description="Reasoning trace visualization")
    completion_time: float = Field(..., description="Time taken to complete")
    llm_calls: int = Field(default=1, description="Number of LLM calls made")
    confidence_score: Optional[float] = Field(None, description="Overall confidence")
    query_type: str = Field(..., description="Type of query performed")


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NodeDetailsRequest(BaseModel):
    """Request for detailed node information."""
    node_id: str = Field(..., description="Node ID to get details for")
    output_folder: str = Field(..., description="Output folder context")


class NodeDetailsResponse(BaseModel):
    """Detailed information about a specific node."""
    node: GraphNode = Field(..., description="The node details")
    connected_nodes: List[GraphNode] = Field(default_factory=list, description="Connected nodes")
    relationships: List[GraphLink] = Field(default_factory=list, description="Node relationships")
    source_documents: List[ProvenanceInfo] = Field(default_factory=list, description="Source documents")
