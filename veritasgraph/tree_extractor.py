"""
VeritasGraph Tree Extractor
===========================

Hierarchical tree structure extraction for documents.
Inspired by PageIndex's Table-of-Contents (TOC) approach for "human-like retrieval".

This module combines:
- PageIndex's TOC detection and hierarchical numbering
- Vision-based structure analysis
- Intelligent parent-child relationship building

The result is a tree structure inside the knowledge graph that enables
both tree-based navigation AND graph-based semantic search.
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image

from veritasgraph.models import (
    TreeNode,
    HierarchicalStructure,
    SectionType,
    DocumentPage,
)


class HierarchicalTreeExtractor:
    """
    Extracts hierarchical tree structure from documents using vision models.
    
    This combines the power of:
    - PageIndex's TOC-based human-like retrieval
    - Graph-based flexibility for complex queries
    
    Key features:
    - Automatic TOC detection
    - Hierarchical numbering extraction (1, 1.1, 1.1.1, etc.)
    - Parent-child relationship building
    - Page range inference for sections
    """
    
    PROMPTS = {
        "toc_detection": """
Analyze this document page and determine if it contains a Table of Contents (TOC).

Look for:
- "Table of Contents", "Contents", "Index" headings
- Numbered or bulleted lists of section titles
- Section titles with page numbers (dots or spaces leading to numbers)
- Hierarchical structure indicators (1, 1.1, 1.2, 2, 2.1, etc.)

Return JSON:
{
    "is_toc_page": true/false,
    "confidence": 0.0-1.0,
    "toc_type": "explicit" | "implicit" | "none",
    "has_page_numbers": true/false,
    "structure_type": "numbered" | "bulleted" | "mixed" | "none",
    "reasoning": "brief explanation"
}

Note: Abstract, Summary, Notation List, Figure List, Table List are NOT Table of Contents.
""",
        
        "toc_extraction": """
Extract the complete Table of Contents from this page.

For each section entry, identify:
1. The hierarchical structure number (1, 1.1, 1.1.2, etc.) if present
2. The section title
3. The page number if visible

Return JSON:
{
    "toc_entries": [
        {
            "structure": "1" or "1.1" or null (hierarchical number as string),
            "title": "Section title exactly as shown",
            "page": page_number_if_visible_else_null,
            "level": inferred_depth_0_to_5
        }
    ],
    "total_entries": count,
    "has_page_numbers": true/false
}

IMPORTANT: 
- Extract titles EXACTLY as shown (preserve formatting)
- Use null for missing values, not empty strings
- Level 0 = document title, Level 1 = chapter, Level 2 = section, etc.
""",

        "page_structure_analysis": """
Analyze the structure of this document page to identify sections and subsections.

Look for:
- Section headers (usually larger, bold, or numbered text)
- Subsection headers (smaller than main sections but distinct from body)
- Chapter markers or numbered headings
- Any hierarchical organization of content

Return JSON:
{
    "sections_found": [
        {
            "title": "Section title as shown",
            "structure_number": "1.2.3" or null,
            "level": 1-5 (1=main section, 5=deepest subsection),
            "section_type": "chapter" | "section" | "subsection" | "heading" | "other",
            "appears_to_start_here": true/false,
            "confidence": 0.0-1.0
        }
    ],
    "page_type": "content" | "toc" | "cover" | "appendix" | "references",
    "has_clear_structure": true/false
}
""",

        "structure_continuation": """
You are continuing to extract the hierarchical tree structure of a document.

Previous structure extracted:
{previous_structure}

Current page content to analyze:
[Image provided]

Continue the structure by identifying any NEW sections that START on this page.
Maintain consistent numbering with the previous structure.

Return JSON:
{
    "new_sections": [
        {
            "structure": "x.x.x" (continuing from previous),
            "title": "Section title",
            "starts_on_page": page_number,
            "level": depth_level,
            "section_type": "chapter" | "section" | "subsection"
        }
    ],
    "continues_previous_section": true/false,
    "previous_section_title": "title if continues" or null
}
"""
    }
    
    def __init__(self, vision_client):
        """
        Initialize the tree extractor.
        
        Args:
            vision_client: VisionModelClient instance for image analysis
        """
        self.vision_client = vision_client
        self.prompts = self.PROMPTS
    
    def extract_hierarchy(
        self, 
        pages: List[DocumentPage],
        doc_id: str
    ) -> HierarchicalStructure:
        """
        Extract complete hierarchical structure from document pages.
        
        This is the main entry point that:
        1. Detects if document has a TOC
        2. Extracts TOC structure if present
        3. Falls back to page-by-page analysis if no TOC
        4. Builds parent-child relationships
        5. Infers page ranges for sections
        
        Args:
            pages: List of DocumentPage objects with images
            doc_id: Document identifier
            
        Returns:
            HierarchicalStructure with complete tree
        """
        print(f"\n🌳 Extracting hierarchical structure for document {doc_id}...")
        
        # Initialize structure
        hierarchy = HierarchicalStructure(
            document_id=doc_id,
            root_id=f"{doc_id}_root"
        )
        
        # Create root node
        root_node = TreeNode(
            id=hierarchy.root_id,
            title="Document Root",
            structure="root",
            level=0,
            section_type=SectionType.ROOT,
            parent_id=None
        )
        hierarchy.nodes[root_node.id] = root_node
        
        # Step 1: Detect TOC pages
        toc_pages, toc_data = self._detect_toc_pages(pages)
        hierarchy.toc_detected = len(toc_pages) > 0
        hierarchy.toc_pages = toc_pages
        
        if hierarchy.toc_detected:
            print(f"   📑 TOC detected on pages: {toc_pages}")
            # Step 2a: Extract structure from TOC
            self._extract_from_toc(hierarchy, toc_data, pages, doc_id)
        else:
            print(f"   📄 No TOC detected, analyzing page structure...")
            # Step 2b: Extract structure from page analysis
            self._extract_from_pages(hierarchy, pages, doc_id)
        
        # Step 3: Build parent-child relationships
        self._build_relationships(hierarchy)
        
        # Step 4: Infer page ranges
        self._infer_page_ranges(hierarchy, len(pages))
        
        # Step 5: Link pages to sections
        self._link_pages_to_sections(hierarchy, pages)
        
        print(f"   ✅ Extracted {len(hierarchy.nodes)} tree nodes")
        print(f"   📊 Max depth: {max((n.level for n in hierarchy.nodes.values()), default=0)}")
        
        return hierarchy
    
    def _detect_toc_pages(
        self, 
        pages: List[DocumentPage],
        max_pages_to_check: int = 10
    ) -> Tuple[List[int], List[Dict]]:
        """
        Detect which pages contain Table of Contents.
        
        Args:
            pages: Document pages to analyze
            max_pages_to_check: Maximum pages to check for TOC
            
        Returns:
            Tuple of (list of TOC page numbers, TOC analysis results)
        """
        toc_pages = []
        toc_data = []
        consecutive_non_toc = 0
        
        for i, page in enumerate(pages[:max_pages_to_check]):
            if consecutive_non_toc >= 3 and toc_pages:
                # Stop if we've found TOC and then had 3 non-TOC pages
                break
                
            try:
                image = Image.open(page.image_path) if page.image_path else None
                if not image:
                    continue
                    
                result = self.vision_client.analyze_with_json(
                    image,
                    self.prompts["toc_detection"]
                )
                
                if result.get("is_toc_page", False) and result.get("confidence", 0) > 0.6:
                    toc_pages.append(page.page_number)
                    toc_data.append({
                        "page_number": page.page_number,
                        "analysis": result
                    })
                    consecutive_non_toc = 0
                else:
                    if toc_pages:  # Only count after we've found at least one TOC page
                        consecutive_non_toc += 1
                        
            except Exception as e:
                print(f"      ⚠️ Error analyzing page {page.page_number}: {e}")
                continue
        
        return toc_pages, toc_data
    
    def _extract_from_toc(
        self,
        hierarchy: HierarchicalStructure,
        toc_data: List[Dict],
        pages: List[DocumentPage],
        doc_id: str
    ):
        """
        Extract hierarchical structure from detected TOC pages.
        """
        all_entries = []
        
        for toc_info in toc_data:
            page_num = toc_info["page_number"]
            page = next((p for p in pages if p.page_number == page_num), None)
            if not page:
                continue
                
            try:
                image = Image.open(page.image_path)
                result = self.vision_client.analyze_with_json(
                    image,
                    self.prompts["toc_extraction"]
                )
                
                entries = result.get("toc_entries", [])
                for entry in entries:
                    entry["source_toc_page"] = page_num
                all_entries.extend(entries)
                
            except Exception as e:
                print(f"      ⚠️ Error extracting TOC from page {page_num}: {e}")
        
        # Deduplicate entries (in case TOC spans multiple pages)
        seen_titles = set()
        unique_entries = []
        for entry in all_entries:
            title = entry.get("title", "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_entries.append(entry)
        
        # Create tree nodes from entries
        for i, entry in enumerate(unique_entries):
            structure = entry.get("structure") or str(i + 1)
            level = entry.get("level", self._infer_level_from_structure(structure))
            
            node_id = f"{doc_id}_section_{self._safe_id(entry.get('title', str(i)))}"
            
            node = TreeNode(
                id=node_id,
                title=entry.get("title", f"Section {i+1}"),
                structure=structure,
                level=level,
                section_type=self._infer_section_type(level),
                start_page=entry.get("page"),
                metadata={
                    "from_toc": True,
                    "toc_page": entry.get("source_toc_page")
                }
            )
            
            hierarchy.nodes[node_id] = node
    
    def _extract_from_pages(
        self,
        hierarchy: HierarchicalStructure,
        pages: List[DocumentPage],
        doc_id: str
    ):
        """
        Extract hierarchical structure by analyzing each page.
        Used when no TOC is detected.
        """
        current_structure_counters = [0] * 6  # Support up to 6 levels deep
        
        for page in pages:
            try:
                image = Image.open(page.image_path) if page.image_path else None
                if not image:
                    continue
                    
                result = self.vision_client.analyze_with_json(
                    image,
                    self.prompts["page_structure_analysis"]
                )
                
                sections = result.get("sections_found", [])
                
                for section in sections:
                    if not section.get("appears_to_start_here", False):
                        continue
                    if section.get("confidence", 0) < 0.5:
                        continue
                        
                    level = section.get("level", 1)
                    title = section.get("title", "").strip()
                    
                    if not title:
                        continue
                    
                    # Generate structure number if not provided
                    structure = section.get("structure_number")
                    if not structure:
                        # Auto-generate hierarchical number
                        current_structure_counters[level] += 1
                        # Reset deeper levels
                        for l in range(level + 1, len(current_structure_counters)):
                            current_structure_counters[l] = 0
                        structure = ".".join(
                            str(current_structure_counters[l]) 
                            for l in range(1, level + 1)
                            if current_structure_counters[l] > 0
                        )
                    
                    node_id = f"{doc_id}_section_{self._safe_id(title)}"
                    
                    # Skip if we already have this section
                    if node_id in hierarchy.nodes:
                        continue
                    
                    node = TreeNode(
                        id=node_id,
                        title=title,
                        structure=structure,
                        level=level,
                        section_type=self._infer_section_type(level),
                        start_page=page.page_number,
                        metadata={
                            "from_toc": False,
                            "detected_on_page": page.page_number,
                            "confidence": section.get("confidence", 0.5)
                        }
                    )
                    
                    hierarchy.nodes[node_id] = node
                    
            except Exception as e:
                print(f"      ⚠️ Error analyzing page {page.page_number}: {e}")
    
    def _build_relationships(self, hierarchy: HierarchicalStructure):
        """
        Build parent-child relationships based on structure numbering.
        
        For example:
        - "1" is parent of "1.1", "1.2"
        - "1.1" is parent of "1.1.1", "1.1.2"
        """
        root = hierarchy.nodes.get(hierarchy.root_id)
        if not root:
            return
        
        # Sort nodes by structure for proper ordering
        sorted_nodes = sorted(
            [n for n in hierarchy.nodes.values() if n.id != hierarchy.root_id],
            key=lambda x: self._structure_sort_key(x.structure)
        )
        
        for node in sorted_nodes:
            parent_structure = self._get_parent_structure(node.structure)
            
            if parent_structure == "root" or not parent_structure:
                # Top-level section - parent is root
                node.parent_id = hierarchy.root_id
                root.children_ids.append(node.id)
            else:
                # Find parent by structure
                parent = next(
                    (n for n in hierarchy.nodes.values() 
                     if n.structure == parent_structure),
                    None
                )
                
                if parent:
                    node.parent_id = parent.id
                    if node.id not in parent.children_ids:
                        parent.children_ids.append(node.id)
                else:
                    # Parent not found, attach to root
                    node.parent_id = hierarchy.root_id
                    root.children_ids.append(node.id)
    
    def _infer_page_ranges(self, hierarchy: HierarchicalStructure, total_pages: int):
        """
        Infer end pages for each section based on the start of the next section.
        """
        # Get all nodes sorted by start page
        nodes_with_pages = sorted(
            [n for n in hierarchy.nodes.values() 
             if n.start_page is not None and n.id != hierarchy.root_id],
            key=lambda x: (x.start_page, x.level)
        )
        
        for i, node in enumerate(nodes_with_pages):
            # Find the next section at same or higher level
            next_start = total_pages + 1
            for j in range(i + 1, len(nodes_with_pages)):
                next_node = nodes_with_pages[j]
                if next_node.level <= node.level:
                    next_start = next_node.start_page
                    break
            
            node.end_page = next_start - 1
        
        # Set root node range
        root = hierarchy.nodes.get(hierarchy.root_id)
        if root:
            root.start_page = 1
            root.end_page = total_pages
    
    def _link_pages_to_sections(
        self, 
        hierarchy: HierarchicalStructure,
        pages: List[DocumentPage]
    ):
        """
        Link each page to its most specific containing section.
        """
        for page in pages:
            section = hierarchy.get_section_for_page(page.page_number)
            if section:
                page.section_id = section.id
    
    # Helper methods
    
    def _safe_id(self, text: str) -> str:
        """Generate a safe ID from text"""
        if not text:
            return hashlib.md5(str(id(text)).encode()).hexdigest()[:8]
        # Remove special characters and limit length
        safe = re.sub(r'[^\w\s-]', '', text)
        safe = re.sub(r'[-\s]+', '_', safe)[:50]
        return safe or hashlib.md5(text.encode()).hexdigest()[:8]
    
    def _infer_level_from_structure(self, structure: str) -> int:
        """Infer tree level from structure number like '1.2.3'"""
        if not structure or structure == "root":
            return 0
        parts = structure.split('.')
        return len(parts)
    
    def _infer_section_type(self, level: int) -> SectionType:
        """Infer section type from level"""
        level_map = {
            0: SectionType.ROOT,
            1: SectionType.CHAPTER,
            2: SectionType.SECTION,
            3: SectionType.SUBSECTION,
            4: SectionType.SUBSUBSECTION,
        }
        return level_map.get(level, SectionType.PARAGRAPH)
    
    def _get_parent_structure(self, structure: str) -> str:
        """Get parent structure number from child"""
        if not structure or structure == "root":
            return "root"
        parts = structure.split('.')
        if len(parts) <= 1:
            return "root"
        return '.'.join(parts[:-1])
    
    def _structure_sort_key(self, structure: str) -> Tuple:
        """Create sort key for structure numbers like '1.2.3'"""
        if not structure or structure == "root":
            return (0,)
        try:
            parts = structure.split('.')
            return tuple(int(p) if p.isdigit() else ord(p[0]) for p in parts)
        except:
            return (999,)


class TreeQueryEngine:
    """
    Query engine optimized for tree-based retrieval.
    
    Enables "human-like retrieval" by:
    - Finding sections by title/topic
    - Navigating up/down the tree
    - Getting context from parent sections
    - Finding related sibling sections
    """
    
    def __init__(self, hierarchy: HierarchicalStructure):
        self.hierarchy = hierarchy
    
    def find_sections_by_title(
        self, 
        query: str, 
        fuzzy: bool = True
    ) -> List[TreeNode]:
        """
        Find sections matching a title query.
        
        Args:
            query: Search query for section titles
            fuzzy: Whether to do fuzzy matching
            
        Returns:
            List of matching TreeNode objects
        """
        query_lower = query.lower()
        matches = []
        
        for node in self.hierarchy.nodes.values():
            title_lower = node.title.lower()
            
            if fuzzy:
                # Fuzzy match - check if query words appear in title
                query_words = query_lower.split()
                if all(word in title_lower for word in query_words):
                    matches.append(node)
                elif query_lower in title_lower:
                    matches.append(node)
            else:
                # Exact match
                if query_lower == title_lower:
                    matches.append(node)
        
        # Sort by level (shallower first) then by structure
        return sorted(matches, key=lambda n: (n.level, n.structure))
    
    def get_section_with_context(self, node_id: str) -> Dict[str, Any]:
        """
        Get a section with full tree context.
        
        Returns:
            Dict with section, parent chain, children, and siblings
        """
        node = self.hierarchy.get_node(node_id)
        if not node:
            return {}
        
        return {
            "section": node,
            "breadcrumb": self.hierarchy.get_path_to_root(node_id),
            "parent": self.hierarchy.get_parent(node_id),
            "children": self.hierarchy.get_children(node_id),
            "siblings": self.hierarchy.get_siblings(node_id),
            "ancestors": self.hierarchy.get_ancestors(node_id),
            "page_range": (node.start_page, node.end_page)
        }
    
    def get_tree_view(self, max_depth: int = None) -> str:
        """
        Generate a text tree view of the hierarchy.
        
        Args:
            max_depth: Maximum depth to display
            
        Returns:
            String representation of the tree
        """
        lines = []
        root = self.hierarchy.get_root()
        if not root:
            return "Empty tree"
        
        self._build_tree_view(root, lines, "", max_depth)
        return "\n".join(lines)
    
    def _build_tree_view(
        self, 
        node: TreeNode, 
        lines: List[str], 
        prefix: str,
        max_depth: int = None
    ):
        """Recursively build tree view"""
        if max_depth is not None and node.level > max_depth:
            return
        
        # Format node line
        page_info = ""
        if node.start_page:
            if node.end_page and node.end_page != node.start_page:
                page_info = f" (pp. {node.start_page}-{node.end_page})"
            else:
                page_info = f" (p. {node.start_page})"
        
        structure = f"[{node.structure}] " if node.structure and node.structure != "root" else ""
        lines.append(f"{prefix}{structure}{node.title}{page_info}")
        
        # Add children
        children = self.hierarchy.get_children(node.id)
        for i, child in enumerate(children):
            is_last = (i == len(children) - 1)
            child_prefix = prefix + ("    " if is_last else "│   ")
            connector = "└── " if is_last else "├── "
            
            # Add connector before recursive call
            if lines:
                next_prefix = prefix + connector
            else:
                next_prefix = ""
                
            self._build_tree_view(
                child, 
                lines, 
                prefix + ("    " if is_last else "│   "),
                max_depth
            )


__all__ = [
    "HierarchicalTreeExtractor",
    "TreeQueryEngine",
]
