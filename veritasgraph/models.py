"""
VeritasGraph Data Models
========================

Core data structures for Vision-Native RAG with Hierarchical Tree Support.
Combines the power of PageIndex's tree structure with graph flexibility.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class IngestMode(Enum):
    """
    Ingestion modes for document processing.
    
    'chunk': Traditional chunking (500-token arbitrary chunks)
    'document_centric': No chunking - treats whole pages/sections as nodes
    
    The document_centric mode implements the "Don't Chunk. Graph." philosophy,
    neutralizing the main differentiator of PageIndex-style systems.
    """
    CHUNK = "chunk"                      # Traditional chunking approach
    DOCUMENT_CENTRIC = "document-centric"  # No chunking - whole pages/sections as nodes
    PAGE = "page"                         # Each page is a single node
    SECTION = "section"                   # Each section (from hierarchy) is a node
    AUTO = "auto"                         # Automatically choose based on document


class SectionType(Enum):
    """Types of document sections for hierarchical classification"""
    ROOT = "root"
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"
    SUBSUBSECTION = "subsubsection"
    PARAGRAPH = "paragraph"
    APPENDIX = "appendix"
    REFERENCE = "reference"
    TOC = "table_of_contents"
    UNKNOWN = "unknown"


@dataclass
class TreeNode:
    """
    Represents a node in the hierarchical document tree.
    Inspired by PageIndex's Table-of-Contents structure.
    
    The structure field uses hierarchical numbering (e.g., "1", "1.1", "1.1.2")
    to represent the position in the document hierarchy.
    """
    id: str
    title: str
    structure: str  # Hierarchical index like "1.2.3"
    level: int  # Depth in tree (0=root, 1=chapter, 2=section, etc.)
    section_type: SectionType = SectionType.UNKNOWN
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    summary: str = ""
    content_preview: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_leaf(self) -> bool:
        """Check if this node has no children"""
        return len(self.children_ids) == 0
    
    @property
    def depth(self) -> int:
        """Return the depth based on structure numbering"""
        if not self.structure or self.structure == "root":
            return 0
        return len(self.structure.split('.'))


@dataclass
class HierarchicalStructure:
    """
    Complete hierarchical tree structure of a document.
    This enables PageIndex-style "human-like retrieval" through
    Table-of-Contents navigation while maintaining graph flexibility.
    """
    document_id: str
    root_id: str
    nodes: Dict[str, TreeNode] = field(default_factory=dict)
    toc_detected: bool = False
    toc_pages: List[int] = field(default_factory=list)
    page_offset: int = 0  # Offset between logical and physical page numbers
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_node(self, node_id: str) -> Optional[TreeNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)
    
    def get_root(self) -> Optional[TreeNode]:
        """Get the root node"""
        return self.nodes.get(self.root_id)
    
    def get_children(self, node_id: str) -> List[TreeNode]:
        """Get all children of a node"""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]
    
    def get_parent(self, node_id: str) -> Optional[TreeNode]:
        """Get the parent of a node"""
        node = self.nodes.get(node_id)
        if not node or not node.parent_id:
            return None
        return self.nodes.get(node.parent_id)
    
    def get_ancestors(self, node_id: str) -> List[TreeNode]:
        """Get all ancestors from node to root"""
        ancestors = []
        current = self.nodes.get(node_id)
        while current and current.parent_id:
            parent = self.nodes.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break
        return ancestors
    
    def get_descendants(self, node_id: str) -> List[TreeNode]:
        """Get all descendants of a node (breadth-first)"""
        descendants = []
        queue = list(self.get_children(node_id))
        while queue:
            node = queue.pop(0)
            descendants.append(node)
            queue.extend(self.get_children(node.id))
        return descendants
    
    def get_siblings(self, node_id: str) -> List[TreeNode]:
        """Get all siblings of a node (excluding itself)"""
        node = self.nodes.get(node_id)
        if not node or not node.parent_id:
            return []
        parent = self.nodes.get(node.parent_id)
        if not parent:
            return []
        return [self.nodes[cid] for cid in parent.children_ids 
                if cid in self.nodes and cid != node_id]
    
    def get_path_to_root(self, node_id: str) -> List[str]:
        """Get the path from a node to root as list of titles"""
        path = []
        current = self.nodes.get(node_id)
        while current:
            path.append(current.title)
            if current.parent_id:
                current = self.nodes.get(current.parent_id)
            else:
                break
        return list(reversed(path))
    
    def get_nodes_at_level(self, level: int) -> List[TreeNode]:
        """Get all nodes at a specific depth level"""
        return [node for node in self.nodes.values() if node.level == level]
    
    def get_section_for_page(self, page_number: int) -> Optional[TreeNode]:
        """Find the most specific section containing a page"""
        candidates = []
        for node in self.nodes.values():
            if node.start_page and node.end_page:
                if node.start_page <= page_number <= node.end_page:
                    candidates.append(node)
            elif node.start_page and node.start_page <= page_number:
                candidates.append(node)
        
        # Return the most specific (deepest) section
        if candidates:
            return max(candidates, key=lambda n: n.level)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Export tree structure to dictionary"""
        return {
            "document_id": self.document_id,
            "root_id": self.root_id,
            "toc_detected": self.toc_detected,
            "toc_pages": self.toc_pages,
            "page_offset": self.page_offset,
            "nodes": {
                nid: {
                    "id": node.id,
                    "title": node.title,
                    "structure": node.structure,
                    "level": node.level,
                    "section_type": node.section_type.value,
                    "parent_id": node.parent_id,
                    "children_ids": node.children_ids,
                    "start_page": node.start_page,
                    "end_page": node.end_page,
                    "summary": node.summary
                }
                for nid, node in self.nodes.items()
            },
            "metadata": self.metadata
        }


@dataclass
class VisualElement:
    """Represents a visual element extracted from a document page"""
    id: str
    element_type: str  # 'table', 'chart', 'diagram', 'text_region', 'image'
    page_number: int
    description: str
    structured_data: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0
    bounding_box: Optional[Tuple[int, int, int, int]] = None
    image_base64: Optional[str] = None
    section_id: Optional[str] = None  # Link to hierarchical tree node
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentPage:
    """Represents a single page from a document"""
    page_number: int
    image_path: str
    image_base64: str
    width: int
    height: int
    elements: List[VisualElement] = field(default_factory=list)
    page_summary: str = ""
    page_type: str = "unknown"
    section_id: Optional[str] = None  # Link to hierarchical tree node


@dataclass
class VisionDocument:
    """Complete document with all visual analysis and hierarchical structure"""
    id: str
    source_path: str
    title: str
    pages: List[DocumentPage] = field(default_factory=list)
    document_summary: str = ""
    document_type: str = "unknown"
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    hierarchy: Optional[HierarchicalStructure] = None  # Tree structure
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphNode:
    """Knowledge graph node derived from visual content"""
    id: str
    node_type: str
    name: str
    description: str
    source_element_id: str
    source_page: int
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    section_id: Optional[str] = None  # Link to hierarchical tree node


__all__ = [
    "SectionType",
    "TreeNode",
    "HierarchicalStructure",
    "VisualElement",
    "DocumentPage", 
    "VisionDocument",
    "GraphNode",
]
