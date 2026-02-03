"""
VeritasGraph Vision Module
==========================

Vision-Native RAG components for processing PDFs with multimodal LLMs.
Bypasses OCR for accurate table and chart extraction.

Now with Hierarchical Tree Support:
- Combines PageIndex's TOC-based "human-like retrieval" 
- With the flexibility of graph-based semantic search
"""

import os
import json
import base64
import hashlib
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np
import networkx as nx
from PIL import Image

from veritasgraph.models import (
    VisualElement,
    DocumentPage,
    VisionDocument,
    GraphNode,
    TreeNode,
    HierarchicalStructure,
    SectionType,
    IngestMode,
)


@dataclass
class VisionRAGConfig:
    """
    Configuration for Vision-Native RAG.
    
    Supports multiple ingestion modes:
    - 'chunk': Traditional 500-token chunking
    - 'document-centric': No chunking - whole pages/sections as nodes
    - 'page': Each page becomes a single node
    - 'section': Each section from hierarchy becomes a node
    - 'auto': Automatically choose based on document structure
    
    The 'document-centric' mode implements: "Don't Chunk. Graph."
    """
    
    # Vision model settings
    vision_model: str = "llama3.2-vision:11b"
    text_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text:latest"
    
    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    
    # PDF processing settings
    pdf_dpi: int = 200
    max_image_size: Tuple[int, int] = (1568, 1568)
    
    # Extraction settings
    extract_tables: bool = True
    extract_charts: bool = True
    extract_text_regions: bool = True
    extract_diagrams: bool = True
    
    # Ingestion mode: "Don't Chunk. Graph."
    ingest_mode: str = "document-centric"  # chunk, document-centric, page, section, auto
    
    # Graph settings
    min_confidence: float = 0.7
    
    # Output paths
    output_dir: str = "./vision_rag_output"
    cache_dir: str = "./vision_rag_cache"
    
    def get_ingest_mode(self) -> IngestMode:
        """Get the IngestMode enum from string config."""
        mode_map = {
            "chunk": IngestMode.CHUNK,
            "document-centric": IngestMode.DOCUMENT_CENTRIC,
            "page": IngestMode.PAGE,
            "section": IngestMode.SECTION,
            "auto": IngestMode.AUTO,
        }
        return mode_map.get(self.ingest_mode.lower(), IngestMode.DOCUMENT_CENTRIC)


class VisionModelClient:
    """
    Client for interacting with local multimodal models via Ollama.
    Supports Llama 3.2 Vision, LLaVA, and other vision-capable models.
    """
    
    def __init__(self, config: VisionRAGConfig):
        self.config = config
        
        try:
            import ollama
            self.client = ollama.Client(host=config.ollama_host)
            self._ollama_available = True
        except ImportError:
            print("⚠️  ollama package not installed. Run: pip install ollama")
            self._ollama_available = False
            self.client = None
        
        if self._ollama_available:
            self._verify_models()
    
    def _verify_models(self):
        """Verify required models are available"""
        try:
            models = self.client.list()
            # Handle different ollama library versions
            if hasattr(models, 'models'):
                # Newer ollama API returns object with .models attribute
                model_list = models.models
                available = [m.model if hasattr(m, 'model') else m.get('name', '') for m in model_list]
            elif isinstance(models, dict):
                # Older API returns dict with 'models' key
                available = [m.get('name', m.get('model', '')) for m in models.get('models', [])]
            else:
                available = []
            
            print(f"📋 Available models: {available}")
            
            vision_available = any(self.config.vision_model.split(':')[0] in m for m in available)
            if not vision_available:
                print(f"⚠️  Vision model '{self.config.vision_model}' not found.")
                print(f"   Run: ollama pull {self.config.vision_model}")
                if any('llava' in m for m in available):
                    self.config.vision_model = 'llama3.2-vision:11b'
                    print(f"   Using fallback: {self.config.vision_model}")
            else:
                print(f"✅ Vision model ready: {self.config.vision_model}")
                
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            print("   Make sure Ollama is running: ollama serve")
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        if image.size[0] > self.config.max_image_size[0] or image.size[1] > self.config.max_image_size[1]:
            image.thumbnail(self.config.max_image_size, Image.Resampling.LANCZOS)
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Analyze an image using the vision model."""
        if not self._ollama_available:
            return ""
            
        image_b64 = self.image_to_base64(image)
        
        try:
            response = self.client.chat(
                model=self.config.vision_model,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                        'images': [image_b64]
                    }
                ],
                options={'temperature': 0.1}
            )
            return response['message']['content']
        except Exception as e:
            print(f"❌ Vision analysis error: {e}")
            return ""
    
    def analyze_with_json(self, image: Image.Image, prompt: str) -> Dict[str, Any]:
        """Analyze image and parse JSON response"""
        json_prompt = prompt + "\n\nRespond ONLY with valid JSON, no other text."
        response = self.analyze_image(image, json_prompt)
        
        try:
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.rfind('```')
                response = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.rfind('```')
                response = response[start:end].strip()
            
            return json.loads(response)
        except json.JSONDecodeError:
            response = response.replace("'", '"').replace('None', 'null').replace('True', 'true').replace('False', 'false')
            try:
                return json.loads(response)
            except:
                return {"raw_response": response, "parse_error": True}
    
    def get_embedding(self, text: str) -> List[float]:
        """Get text embedding using the embedding model"""
        if not self._ollama_available:
            return []
            
        try:
            response = self.client.embeddings(
                model=self.config.embedding_model,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            print(f"❌ Embedding error: {e}")
            return []
    
    def text_completion(self, prompt: str) -> str:
        """Get text completion using the text model"""
        if not self._ollama_available:
            return ""
            
        try:
            response = self.client.chat(
                model=self.config.text_model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.3}
            )
            return response['message']['content']
        except Exception as e:
            print(f"❌ Text completion error: {e}")
            return ""


class PDFProcessor:
    """Converts PDF documents to images for vision model processing."""
    
    def __init__(self, config: VisionRAGConfig, vision_client: VisionModelClient):
        self.config = config
        self.vision_client = vision_client
    
    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF pages to PIL Images."""
        print(f"📄 Converting PDF: {pdf_path}")
        
        try:
            import pdf2image
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=self.config.pdf_dpi,
                fmt='jpeg'
            )
            print(f"   ✅ Converted {len(images)} pages")
            return images
        except ImportError:
            print("❌ pdf2image not installed. Run: pip install pdf2image")
            return []
        except Exception as e:
            print(f"   ❌ PDF conversion error: {e}")
            print("   Make sure poppler is installed:")
            print("   - Windows: choco install poppler")
            print("   - Mac: brew install poppler")
            print("   - Linux: apt-get install poppler-utils")
            return []
    
    def save_page_images(self, images: List[Image.Image], doc_id: str) -> List[str]:
        """Save page images to cache directory"""
        paths = []
        cache_dir = os.path.join(self.config.cache_dir, doc_id)
        os.makedirs(cache_dir, exist_ok=True)
        
        for i, img in enumerate(images):
            path = os.path.join(cache_dir, f"page_{i+1:03d}.jpg")
            img.save(path, 'JPEG', quality=90)
            paths.append(path)
        
        return paths
    
    def process_pdf(self, pdf_path: str) -> Optional[VisionDocument]:
        """Process a PDF document completely."""
        doc_id = hashlib.md5(pdf_path.encode()).hexdigest()[:12]
        
        images = self.pdf_to_images(pdf_path)
        if not images:
            return None
        
        image_paths = self.save_page_images(images, doc_id)
        
        pages = []
        for i, (img, path) in enumerate(zip(images, image_paths)):
            page = DocumentPage(
                page_number=i + 1,
                image_path=path,
                image_base64=self.vision_client.image_to_base64(img),
                width=img.size[0],
                height=img.size[1]
            )
            pages.append(page)
        
        doc = VisionDocument(
            id=doc_id,
            source_path=pdf_path,
            title=os.path.basename(pdf_path),
            pages=pages,
            metadata={
                "total_pages": len(pages),
                "processed_at": datetime.now().isoformat()
            }
        )
        
        return doc


class VisualElementExtractor:
    """
    Extracts structured information from document pages using vision models.
    This is the core of Vision-Native RAG - no OCR needed!
    """
    
    PROMPTS = {
        "page_classification": """
Analyze this document page and classify it.

Return JSON with:
{
    "page_type": "cover" | "table_of_contents" | "content" | "chart_heavy" | "table_heavy" | "appendix" | "references",
    "has_tables": true/false,
    "has_charts": true/false,
    "has_diagrams": true/false,
    "has_images": true/false,
    "main_topic": "brief description of main content",
    "confidence": 0.0-1.0
}
""",
        
        "table_extraction": """
Extract ALL tables from this page. For each table:

1. Identify the table title/caption
2. Extract column headers
3. Extract all data rows
4. Note any footnotes or special formatting

Return JSON:
{
    "tables": [
        {
            "table_id": "table_1",
            "title": "Table title if visible",
            "headers": ["Column1", "Column2", ...],
            "rows": [
                ["value1", "value2", ...],
                ...
            ],
            "footnotes": ["any footnotes"],
            "table_type": "financial" | "statistical" | "comparison" | "summary" | "other"
        }
    ]
}

IMPORTANT: Extract EXACT values as shown. For numbers, keep formatting (commas, decimals, currency symbols).
""",
        
        "chart_extraction": """
Extract ALL charts/graphs from this page. For each chart:

1. Identify chart type (bar, line, pie, scatter, etc.)
2. Extract title and axis labels
3. Extract data points/values as accurately as possible
4. Note legends and any annotations

Return JSON:
{
    "charts": [
        {
            "chart_id": "chart_1",
            "chart_type": "bar" | "line" | "pie" | "scatter" | "area" | "combination" | "other",
            "title": "Chart title",
            "x_axis": {"label": "X axis label", "values": ["val1", "val2", ...]},
            "y_axis": {"label": "Y axis label", "unit": "$" | "%" | "units"},
            "data_series": [
                {
                    "name": "Series name",
                    "values": [10, 20, 30, ...]
                }
            ],
            "insights": "Key insight or trend shown",
            "time_period": "if applicable"
        }
    ]
}

IMPORTANT: Estimate numerical values from the chart as accurately as possible.
""",
        
        "key_metrics": """
Extract all KEY METRICS and NUMBERS from this page.

Look for:
- Financial figures (revenue, profit, costs, margins)
- Percentages and growth rates
- Dates and time periods
- Quantities and counts
- Comparisons (YoY, QoQ, vs benchmark)

Return JSON:
{
    "metrics": [
        {
            "name": "Metric name",
            "value": "$1.5B" or "15%" or "1,234",
            "numeric_value": 1500000000,
            "unit": "USD" | "%" | "count" | "other",
            "context": "What this metric represents",
            "time_period": "Q4 2024" or "FY2024" if applicable,
            "comparison": {"vs": "prior period", "change": "+10%"} if applicable
        }
    ]
}
""",
        
        "entity_extraction": """
Extract all NAMED ENTITIES from this page.

Look for:
- Company names
- Person names (executives, analysts)
- Product names
- Geographic locations
- Dates and time periods
- Technical terms

Return JSON:
{
    "entities": [
        {
            "name": "Entity name",
            "type": "company" | "person" | "product" | "location" | "date" | "concept",
            "context": "How it appears in the document",
            "related_entities": ["other entities it's connected to"]
        }
    ]
}
""",
        
        "page_summary": """
Provide a comprehensive summary of this document page.

Include:
1. Main topic or section
2. Key points and findings
3. Important numbers or metrics mentioned
4. Any conclusions or recommendations
5. How this page relates to a typical document structure

Return JSON:
{
    "summary": "Detailed summary paragraph",
    "key_points": ["point 1", "point 2", ...],
    "section_type": "executive_summary" | "analysis" | "data" | "conclusion" | "methodology" | "other",
    "importance": "high" | "medium" | "low"
}
"""
    }
    
    def __init__(self, vision_client: VisionModelClient, config: VisionRAGConfig):
        self.vision_client = vision_client
        self.config = config
        self.prompts = self.PROMPTS
    
    def extract_page_info(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """Extract all information from a single page"""
        print(f"   📖 Analyzing page {page_num}...")
        
        results = {}
        
        # Step 1: Classify the page
        classification = self.vision_client.analyze_with_json(
            image, 
            self.prompts["page_classification"]
        )
        results["classification"] = classification
        
        # Step 2: Extract tables if present
        if classification.get("has_tables", False) and self.config.extract_tables:
            print(f"      📊 Extracting tables...")
            tables = self.vision_client.analyze_with_json(
                image,
                self.prompts["table_extraction"]
            )
            results["tables"] = tables.get("tables", [])
        
        # Step 3: Extract charts if present
        if classification.get("has_charts", False) and self.config.extract_charts:
            print(f"      📈 Extracting charts...")
            charts = self.vision_client.analyze_with_json(
                image,
                self.prompts["chart_extraction"]
            )
            results["charts"] = charts.get("charts", [])
        
        # Step 4: Extract key metrics
        print(f"      🔢 Extracting metrics...")
        metrics = self.vision_client.analyze_with_json(
            image,
            self.prompts["key_metrics"]
        )
        results["metrics"] = metrics.get("metrics", [])
        
        # Step 5: Extract entities
        print(f"      🏷️ Extracting entities...")
        entities = self.vision_client.analyze_with_json(
            image,
            self.prompts["entity_extraction"]
        )
        results["entities"] = entities.get("entities", [])
        
        # Step 6: Generate page summary
        print(f"      📝 Generating summary...")
        summary = self.vision_client.analyze_with_json(
            image,
            self.prompts["page_summary"]
        )
        results["summary"] = summary
        
        return results
    
    def create_visual_elements(self, page_results: Dict, page_num: int) -> List[VisualElement]:
        """Convert extraction results to VisualElement objects"""
        elements = []
        
        # Create elements for tables
        for i, table in enumerate(page_results.get("tables", [])):
            element = VisualElement(
                id=f"page{page_num}_table_{i+1}",
                element_type="table",
                page_number=page_num,
                description=f"Table: {table.get('title', 'Untitled')}",
                structured_data=table,
                confidence=0.85,
                metadata={"table_type": table.get("table_type", "unknown")}
            )
            elements.append(element)
        
        # Create elements for charts
        for i, chart in enumerate(page_results.get("charts", [])):
            element = VisualElement(
                id=f"page{page_num}_chart_{i+1}",
                element_type="chart",
                page_number=page_num,
                description=f"{chart.get('chart_type', 'Chart')}: {chart.get('title', 'Untitled')}",
                structured_data=chart,
                confidence=0.80,
                metadata={
                    "chart_type": chart.get("chart_type"),
                    "insights": chart.get("insights", "")
                }
            )
            elements.append(element)
        
        # Create elements for metrics
        for i, metric in enumerate(page_results.get("metrics", [])):
            element = VisualElement(
                id=f"page{page_num}_metric_{i+1}",
                element_type="metric",
                page_number=page_num,
                description=f"{metric.get('name', 'Metric')}: {metric.get('value', 'N/A')}",
                structured_data=metric,
                confidence=0.90,
                metadata={"unit": metric.get("unit"), "context": metric.get("context")}
            )
            elements.append(element)
        
        return elements


class VisionKnowledgeGraph:
    """
    Builds a knowledge graph from visually extracted information.
    Connects entities, metrics, tables, and charts into a queryable structure.
    
    Now with Hierarchical Tree Support:
    - Parent (Section) -> Child (Subsection) relationships
    - Tree traversal for "human-like retrieval"
    - Combined tree + graph navigation
    
    "Don't Chunk. Graph." - Document-Centric Mode:
    - Treats whole pages/sections as single nodes (not arbitrary 500-token chunks)
    - Preserves document structure and context
    - Better for RAG with rich visual content
    """
    
    def __init__(self, vision_client: VisionModelClient, ingest_mode: IngestMode = IngestMode.DOCUMENT_CENTRIC):
        self.vision_client = vision_client
        self.ingest_mode = ingest_mode
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, GraphNode] = {}
        self.embeddings: Dict[str, List[float]] = {}
        self.hierarchies: Dict[str, HierarchicalStructure] = {}  # doc_id -> hierarchy
        self.content_nodes: Dict[str, str] = {}  # node_id -> full text content
    
    def add_document(self, doc: VisionDocument):
        """
        Add a processed document to the knowledge graph.
        
        "Don't Chunk. Graph." - The ingest_mode determines how content is stored:
        - CHUNK: Traditional 500-token chunks (legacy mode)
        - DOCUMENT_CENTRIC: Whole pages/sections as nodes (recommended)
        - PAGE: Each page becomes a single content node
        - SECTION: Each section becomes a single content node
        - AUTO: Automatically choose based on document structure
        """
        print(f"\n🔗 Building knowledge graph for: {doc.title}")
        print(f"   📋 Ingest mode: {self.ingest_mode.value}")
        
        doc_node_id = f"doc_{doc.id}"
        self.graph.add_node(
            doc_node_id,
            type="document",
            title=doc.title,
            pages=len(doc.pages)
        )
        
        # Add hierarchical tree structure if available
        if doc.hierarchy:
            self._add_hierarchy_to_graph(doc.hierarchy, doc_node_id, doc.id)
            self.hierarchies[doc.id] = doc.hierarchy
        
        # Determine effective ingest mode
        effective_mode = self._determine_effective_mode(doc)
        
        # "Don't Chunk. Graph." - Create content nodes based on ingest mode
        if effective_mode in (IngestMode.DOCUMENT_CENTRIC, IngestMode.PAGE, IngestMode.SECTION):
            self._add_document_centric_content(doc, doc_node_id, effective_mode)
        else:
            # Traditional chunking mode (legacy)
            self._add_chunked_content(doc, doc_node_id)
        
        self._connect_related_entities(doc)
        
        # Summary
        content_node_count = len([n for n in self.graph.nodes() if self.graph.nodes[n].get('type') == 'content'])
        print(f"   ✅ Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        if content_node_count > 0:
            print(f"   📄 Content nodes (no chunking): {content_node_count}")
        if doc.hierarchy:
            print(f"   🌳 Tree structure: {len(doc.hierarchy.nodes)} sections")
    
    def _determine_effective_mode(self, doc: VisionDocument) -> IngestMode:
        """Determine the effective ingest mode, handling AUTO mode."""
        if self.ingest_mode != IngestMode.AUTO:
            return self.ingest_mode
        
        # AUTO mode: choose based on document characteristics
        if doc.hierarchy and len(doc.hierarchy.nodes) > 0:
            # Document has structure - use section-based
            return IngestMode.SECTION
        elif len(doc.pages) <= 10:
            # Small document - use page-based
            return IngestMode.PAGE
        else:
            # Large unstructured document - fall back to section if hierarchy exists, else page
            return IngestMode.PAGE
    
    def _add_document_centric_content(
        self, 
        doc: VisionDocument, 
        doc_node_id: str,
        mode: IngestMode
    ):
        """
        "Don't Chunk. Graph." - Add content nodes for whole pages or sections.
        
        Unlike traditional RAG that chunks text into arbitrary 500-token pieces,
        this preserves document structure by treating complete pages or sections
        as single retrievable units.
        """
        print(f"   📄 Creating document-centric content nodes...")
        
        if mode == IngestMode.SECTION and doc.hierarchy:
            # Each section becomes a content node
            self._add_section_content_nodes(doc, doc_node_id)
        else:
            # Each page becomes a content node (PAGE or DOCUMENT_CENTRIC fallback)
            self._add_page_content_nodes(doc, doc_node_id)
    
    def _add_page_content_nodes(self, doc: VisionDocument, doc_node_id: str):
        """Add whole pages as content nodes (no chunking)."""
        for page in doc.pages:
            page_node_id = f"page_{doc.id}_{page.page_number}"
            
            # Aggregate all content from the page
            page_content = self._aggregate_page_content(page)
            
            self.graph.add_node(
                page_node_id,
                type="page",
                content_type="whole_page",  # Flag: this is a full page, not a chunk
                page_number=page.page_number,
                page_type=page.page_type,
                summary=page.page_summary,
                section_id=page.section_id,
                content_length=len(page_content),
                element_count=len(page.elements)
            )
            
            # Store the full content
            self.content_nodes[page_node_id] = page_content
            
            self.graph.add_edge(doc_node_id, page_node_id, relation="contains_page")
            
            # Connect page to its section in the hierarchy
            if page.section_id and doc.hierarchy:
                section_node_id = f"section_{doc.id}_{page.section_id}"
                if self.graph.has_node(section_node_id):
                    self.graph.add_edge(section_node_id, page_node_id, relation="contains_page")
            
            # Create embedding for the whole page
            embed_text = f"Page {page.page_number}: {page.page_summary}\n{page_content[:2000]}"
            embedding = self.vision_client.get_embedding(embed_text)
            if embedding:
                self.embeddings[page_node_id] = embedding
            
            # Also add individual elements for fine-grained search
            for element in page.elements:
                self._add_element_to_graph(element, page_node_id, doc.id, page.section_id)
    
    def _add_section_content_nodes(self, doc: VisionDocument, doc_node_id: str):
        """Add whole sections as content nodes (no chunking)."""
        # First, add page nodes for navigation
        page_content_by_section: Dict[str, List[str]] = {}
        
        for page in doc.pages:
            page_node_id = f"page_{doc.id}_{page.page_number}"
            
            self.graph.add_node(
                page_node_id,
                type="page",
                page_number=page.page_number,
                page_type=page.page_type,
                summary=page.page_summary,
                section_id=page.section_id
            )
            
            self.graph.add_edge(doc_node_id, page_node_id, relation="contains_page")
            
            # Aggregate content by section
            section_id = page.section_id or "root"
            if section_id not in page_content_by_section:
                page_content_by_section[section_id] = []
            page_content_by_section[section_id].append(self._aggregate_page_content(page))
            
            # Connect page to section
            if page.section_id and doc.hierarchy:
                section_node_id = f"section_{doc.id}_{page.section_id}"
                if self.graph.has_node(section_node_id):
                    self.graph.add_edge(section_node_id, page_node_id, relation="contains_page")
            
            # Add elements
            for element in page.elements:
                self._add_element_to_graph(element, page_node_id, doc.id, page.section_id)
        
        # Create content nodes for each section
        for section_id, tree_node in doc.hierarchy.nodes.items():
            section_node_id = f"section_{doc.id}_{section_id}"
            content_node_id = f"content_{doc.id}_{section_id}"
            
            # Get accumulated content for this section
            section_content = "\n\n".join(page_content_by_section.get(section_id, []))
            
            # Also include content from child sections
            children = doc.hierarchy.get_children(section_id)
            for child in children:
                child_content = page_content_by_section.get(child.id, [])
                section_content += "\n\n" + "\n\n".join(child_content)
            
            if section_content.strip():
                self.graph.add_node(
                    content_node_id,
                    type="content",
                    content_type="whole_section",  # Flag: this is a full section, not a chunk
                    section_id=section_id,
                    section_title=tree_node.title,
                    section_level=tree_node.level,
                    content_length=len(section_content)
                )
                
                self.content_nodes[content_node_id] = section_content
                
                # Connect to section node
                self.graph.add_edge(section_node_id, content_node_id, relation="has_content")
                
                # Create embedding for the whole section
                embed_text = f"Section: {tree_node.title}\n{section_content[:2000]}"
                embedding = self.vision_client.get_embedding(embed_text)
                if embedding:
                    self.embeddings[content_node_id] = embedding
    
    def _aggregate_page_content(self, page: DocumentPage) -> str:
        """Aggregate all content from a page into a single text block."""
        content_parts = []
        
        # Add page summary
        if page.page_summary:
            content_parts.append(f"Summary: {page.page_summary}")
        
        # Add element descriptions
        for element in page.elements:
            if element.description:
                content_parts.append(f"[{element.element_type.upper()}]: {element.description}")
            
            # Add structured data as text
            if element.structured_data:
                if element.element_type == "table":
                    table_text = self._table_to_text(element.structured_data)
                    if table_text:
                        content_parts.append(table_text)
                elif element.element_type == "metric":
                    name = element.structured_data.get("name", "")
                    value = element.structured_data.get("value", "")
                    unit = element.structured_data.get("unit", "")
                    content_parts.append(f"Metric: {name} = {value} {unit}".strip())
                elif element.element_type == "chart":
                    insights = element.structured_data.get("insights", "")
                    if insights:
                        content_parts.append(f"Chart Insights: {insights}")
        
        return "\n".join(content_parts)
    
    def _table_to_text(self, table_data: Dict) -> str:
        """Convert table structured data to readable text."""
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        if not headers and not rows:
            return ""
        
        text_parts = []
        if headers:
            text_parts.append("Table Headers: " + " | ".join(str(h) for h in headers))
        
        for i, row in enumerate(rows[:10]):  # Limit to 10 rows
            if isinstance(row, list):
                text_parts.append(f"Row {i+1}: " + " | ".join(str(cell) for cell in row))
            elif isinstance(row, dict):
                text_parts.append(f"Row {i+1}: " + " | ".join(f"{k}={v}" for k, v in row.items()))
        
        if len(rows) > 10:
            text_parts.append(f"... and {len(rows) - 10} more rows")
        
        return "\n".join(text_parts)
    
    def _add_chunked_content(self, doc: VisionDocument, doc_node_id: str):
        """Legacy chunking mode - adds pages and elements without full content nodes."""
        for page in doc.pages:
            page_node_id = f"page_{doc.id}_{page.page_number}"
            
            self.graph.add_node(
                page_node_id,
                type="page",
                page_number=page.page_number,
                page_type=page.page_type,
                summary=page.page_summary,
                section_id=page.section_id
            )
            
            self.graph.add_edge(doc_node_id, page_node_id, relation="contains_page")
            
            if page.section_id and doc.hierarchy:
                section_node_id = f"section_{doc.id}_{page.section_id}"
                if self.graph.has_node(section_node_id):
                    self.graph.add_edge(section_node_id, page_node_id, relation="contains_page")
            
            for element in page.elements:
                self._add_element_to_graph(element, page_node_id, doc.id, page.section_id)
    
    def get_content(self, node_id: str) -> Optional[str]:
        """Retrieve the full content for a content node."""
        return self.content_nodes.get(node_id)
    
    def _add_hierarchy_to_graph(
        self, 
        hierarchy: HierarchicalStructure, 
        doc_node_id: str,
        doc_id: str
    ):
        """
        Add hierarchical tree structure to the graph.
        Creates Parent -> Child edges for tree navigation.
        """
        print(f"   🌳 Adding hierarchical tree structure...")
        
        for node_id, tree_node in hierarchy.nodes.items():
            section_node_id = f"section_{doc_id}_{node_id}"
            
            # Add section node with tree metadata
            self.graph.add_node(
                section_node_id,
                type="section",
                node_type="tree_node",
                title=tree_node.title,
                structure=tree_node.structure,
                level=tree_node.level,
                section_type=tree_node.section_type.value,
                start_page=tree_node.start_page,
                end_page=tree_node.end_page,
                summary=tree_node.summary,
                is_leaf=tree_node.is_leaf
            )
            
            # Connect section to document
            if tree_node.structure == "root":
                self.graph.add_edge(
                    doc_node_id, 
                    section_node_id, 
                    relation="has_structure"
                )
            
            # Create embedding for section
            embed_text = f"Section: {tree_node.title}"
            if tree_node.summary:
                embed_text += f" | {tree_node.summary}"
            embedding = self.vision_client.get_embedding(embed_text)
            if embedding:
                self.embeddings[section_node_id] = embedding
        
        # Add parent-child relationships (tree edges)
        for node_id, tree_node in hierarchy.nodes.items():
            if tree_node.parent_id:
                parent_section_id = f"section_{doc_id}_{tree_node.parent_id}"
                child_section_id = f"section_{doc_id}_{node_id}"
                
                if self.graph.has_node(parent_section_id):
                    # Primary tree relationship
                    self.graph.add_edge(
                        parent_section_id,
                        child_section_id,
                        relation="parent_of",
                        edge_type="tree"
                    )
                    # Reverse edge for upward traversal
                    self.graph.add_edge(
                        child_section_id,
                        parent_section_id,
                        relation="child_of",
                        edge_type="tree"
                    )
            
            # Add sibling relationships
            siblings = hierarchy.get_siblings(node_id)
            for sibling in siblings:
                sibling_section_id = f"section_{doc_id}_{sibling.id}"
                section_id = f"section_{doc_id}_{node_id}"
                if not self.graph.has_edge(section_id, sibling_section_id):
                    self.graph.add_edge(
                        section_id,
                        sibling_section_id,
                        relation="sibling_of",
                        edge_type="tree"
                    )
    
    def _add_element_to_graph(
        self, 
        element: VisualElement, 
        page_node_id: str, 
        doc_id: str,
        section_id: Optional[str] = None
    ):
        """Add a visual element to the graph"""
        element_node_id = f"{doc_id}_{element.id}"
        
        attrs = {
            "type": element.element_type,
            "description": element.description,
            "confidence": element.confidence,
            "page_number": element.page_number,
            "section_id": section_id or element.section_id
        }
        
        if element.element_type == "table" and element.structured_data:
            attrs["table_data"] = element.structured_data
            attrs["headers"] = element.structured_data.get("headers", [])
            attrs["row_count"] = len(element.structured_data.get("rows", []))
            
        elif element.element_type == "chart" and element.structured_data:
            attrs["chart_data"] = element.structured_data
            attrs["chart_type"] = element.structured_data.get("chart_type")
            attrs["insights"] = element.structured_data.get("insights", "")
            
        elif element.element_type == "metric" and element.structured_data:
            attrs["metric_name"] = element.structured_data.get("name")
            attrs["metric_value"] = element.structured_data.get("value")
            attrs["numeric_value"] = element.structured_data.get("numeric_value")
            attrs["unit"] = element.structured_data.get("unit")
        
        self.graph.add_node(element_node_id, **attrs)
        self.graph.add_edge(page_node_id, element_node_id, relation=f"contains_{element.element_type}")
        
        # Connect element to its section if available
        if section_id:
            section_node_id = f"section_{doc_id}_{section_id}"
            if self.graph.has_node(section_node_id):
                self.graph.add_edge(
                    section_node_id, 
                    element_node_id, 
                    relation="contains_element"
                )
        
        embed_text = f"{element.element_type}: {element.description}"
        if element.structured_data:
            embed_text += f" | Data: {json.dumps(element.structured_data)[:500]}"
        
        embedding = self.vision_client.get_embedding(embed_text)
        if embedding:
            self.embeddings[element_node_id] = embedding
        
        self.nodes[element_node_id] = GraphNode(
            id=element_node_id,
            node_type=element.element_type,
            name=element.description,
            description=json.dumps(element.structured_data) if element.structured_data else "",
            source_element_id=element.id,
            source_page=element.page_number,
            properties=attrs,
            embedding=embedding,
            section_id=section_id
        )
    
    def _connect_related_entities(self, doc: VisionDocument):
        """Find and connect related entities across pages"""
        metrics_by_name = {}
        
        for page in doc.pages:
            for element in page.elements:
                if element.element_type == "metric" and element.structured_data:
                    name = element.structured_data.get("name", "").lower()
                    if name:
                        if name not in metrics_by_name:
                            metrics_by_name[name] = []
                        metrics_by_name[name].append(f"{doc.id}_{element.id}")
        
        for name, node_ids in metrics_by_name.items():
            if len(node_ids) > 1:
                for i in range(len(node_ids) - 1):
                    self.graph.add_edge(
                        node_ids[i], 
                        node_ids[i+1], 
                        relation="same_metric_different_page"
                    )
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """Search graph nodes by semantic similarity"""
        query_embedding = self.vision_client.get_embedding(query)
        if not query_embedding:
            return []
        
        similarities = []
        for node_id, embedding in self.embeddings.items():
            sim = self._cosine_similarity(query_embedding, embedding)
            node_data = dict(self.graph.nodes[node_id])
            similarities.append((node_id, sim, node_data))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def get_context_for_query(self, query: str, max_tokens: int = 4000) -> str:
        """Get relevant context for a query, including hierarchical tree context"""
        results = self.semantic_search(query, top_k=10)
        
        context_parts = []
        seen_sections = set()
        
        for node_id, score, data in results:
            if score < 0.5:
                continue
            
            # Get hierarchical context if available
            section_context = ""
            section_id = data.get("section_id")
            if section_id:
                section_context = self._get_section_breadcrumb(node_id, section_id)
                seen_sections.add(section_id)
            
            context = f"\n[{data['type'].upper()} | Page {data.get('page_number', 'N/A')} | Relevance: {score:.2f}]"
            if section_context:
                context += f"\n📍 Location: {section_context}"
            context += f"\n{data.get('description', '')}\n"
            
            if 'table_data' in data:
                table = data['table_data']
                context += f"Headers: {table.get('headers', [])}\n"
                context += f"Rows: {len(table.get('rows', []))} data rows\n"
                for row in table.get('rows', [])[:3]:
                    context += f"  {row}\n"
                    
            elif 'chart_data' in data:
                chart = data['chart_data']
                context += f"Chart Type: {chart.get('chart_type')}\n"
                context += f"Insight: {chart.get('insights', '')}\n"
                
            elif 'metric_value' in data:
                context += f"Value: {data['metric_value']}\n"
                context += f"Unit: {data.get('unit', 'N/A')}\n"
            
            context_parts.append(context)
        
        return "\n---\n".join(context_parts)
    
    def _get_section_breadcrumb(self, node_id: str, section_id: str) -> str:
        """Get the hierarchical path to a section"""
        # Extract doc_id from node_id
        parts = node_id.split('_')
        if len(parts) < 2:
            return ""
        
        doc_id = parts[0]
        hierarchy = self.hierarchies.get(doc_id)
        if not hierarchy:
            return ""
        
        path = hierarchy.get_path_to_root(section_id)
        if path:
            return " > ".join(path)
        return ""
    
    def get_tree_context(self, doc_id: str, section_title: str) -> Dict[str, Any]:
        """
        Get tree-based context for a specific section.
        
        This enables "human-like retrieval" by navigating the document tree.
        """
        hierarchy = self.hierarchies.get(doc_id)
        if not hierarchy:
            return {"error": "No hierarchy found for document"}
        
        # Find section by title
        matching_nodes = [
            n for n in hierarchy.nodes.values()
            if section_title.lower() in n.title.lower()
        ]
        
        if not matching_nodes:
            return {"error": f"Section '{section_title}' not found"}
        
        node = matching_nodes[0]
        
        return {
            "section": {
                "title": node.title,
                "structure": node.structure,
                "level": node.level,
                "pages": f"{node.start_page}-{node.end_page}" if node.start_page else "N/A"
            },
            "breadcrumb": hierarchy.get_path_to_root(node.id),
            "parent": self._node_summary(hierarchy.get_parent(node.id)),
            "children": [self._node_summary(c) for c in hierarchy.get_children(node.id)],
            "siblings": [self._node_summary(s) for s in hierarchy.get_siblings(node.id)]
        }
    
    def _node_summary(self, node: Optional[TreeNode]) -> Optional[Dict]:
        """Get summary dict for a tree node"""
        if not node:
            return None
        return {
            "title": node.title,
            "structure": node.structure,
            "pages": f"{node.start_page}-{node.end_page}" if node.start_page else "N/A"
        }
    
    def get_section_contents(self, doc_id: str, section_id: str) -> List[Dict]:
        """
        Get all content elements within a section.
        
        This allows retrieving everything under a specific part of the tree.
        """
        section_node_id = f"section_{doc_id}_{section_id}"
        if not self.graph.has_node(section_node_id):
            return []
        
        contents = []
        # Get direct children (elements and pages)
        for _, target, edge_data in self.graph.out_edges(section_node_id, data=True):
            node_data = dict(self.graph.nodes[target])
            if node_data.get("type") in ["table", "chart", "metric", "page"]:
                contents.append({
                    "id": target,
                    "type": node_data.get("type"),
                    "description": node_data.get("description", node_data.get("summary", "")),
                    "page": node_data.get("page_number")
                })
        
        return contents
    
    def visualize(self, figsize=(15, 10), show_tree: bool = True):
        """Visualize the knowledge graph with hierarchical tree structure"""
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=figsize)
        
        color_map = {
            'document': '#FF6B6B',
            'section': '#9B59B6',  # Purple for tree nodes
            'page': '#4ECDC4',
            'table': '#45B7D1',
            'chart': '#96CEB4',
            'metric': '#FFEAA7',
            'entity': '#DDA0DD'
        }
        
        colors = [color_map.get(self.graph.nodes[n].get('type', 'entity'), '#888888') 
                  for n in self.graph.nodes()]
        
        # Use hierarchical layout if tree structure exists
        if show_tree and any(self.graph.nodes[n].get('type') == 'section' for n in self.graph.nodes()):
            try:
                # Try to use hierarchical layout
                pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
            except:
                pos = nx.spring_layout(self.graph, k=2, iterations=50)
        else:
            pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        # Draw tree edges differently
        tree_edges = [(u, v) for u, v, d in self.graph.edges(data=True) 
                      if d.get('edge_type') == 'tree']
        other_edges = [(u, v) for u, v, d in self.graph.edges(data=True) 
                       if d.get('edge_type') != 'tree']
        
        # Draw other edges first (lighter)
        nx.draw_networkx_edges(self.graph, pos, edgelist=other_edges,
                               edge_color='#CCCCCC', arrows=True, arrowsize=10,
                               alpha=0.5)
        
        # Draw tree edges (stronger)
        nx.draw_networkx_edges(self.graph, pos, edgelist=tree_edges,
                               edge_color='#9B59B6', arrows=True, arrowsize=15,
                               width=2, alpha=0.8)
        
        # Draw nodes
        nx.draw_networkx_nodes(self.graph, pos, node_color=colors, node_size=500)
        
        for node_type, color in color_map.items():
            plt.scatter([], [], c=color, label=node_type, s=100)
        plt.legend(loc='upper left')
        
        plt.title("Vision-Native Knowledge Graph with Hierarchical Tree")
        plt.tight_layout()
        plt.show()
    
    def get_tree_visualization(self, doc_id: str) -> str:
        """Get ASCII tree visualization for a document"""
        hierarchy = self.hierarchies.get(doc_id)
        if not hierarchy:
            return "No hierarchy found for document"
        
        from veritasgraph.tree_extractor import TreeQueryEngine
        engine = TreeQueryEngine(hierarchy)
        return engine.get_tree_view()


class VisionRAGEngine:
    """
    Complete Vision-Native RAG engine.
    Combines visual extraction, knowledge graph, and LLM reasoning.
    """
    
    def __init__(
        self, 
        vision_client: VisionModelClient,
        knowledge_graph: VisionKnowledgeGraph,
        config: VisionRAGConfig
    ):
        self.vision_client = vision_client
        self.kg = knowledge_graph
        self.config = config
    
    def query(self, question: str, include_reasoning: bool = True) -> Dict[str, Any]:
        """Answer a question using Vision-Native RAG."""
        print(f"\n🔍 Processing query: {question}")
        
        context = self.kg.get_context_for_query(question)
        
        if not context:
            return {
                "answer": "I couldn't find relevant information in the documents.",
                "confidence": 0.0,
                "sources": []
            }
        
        search_results = self.kg.semantic_search(question, top_k=5)
        
        answer_prompt = f"""
You are an expert analyst answering questions about documents.
Answer based ONLY on the provided context from visual document analysis.

Question: {question}

Context from Document Analysis:
{context}

Instructions:
1. Answer the question directly and specifically
2. Cite page numbers and specific data points
3. If the information involves tables or charts, describe what they show
4. If you cannot answer from the context, say so clearly
5. Be precise with numbers and metrics

Answer:
"""
        
        answer = self.vision_client.text_completion(answer_prompt)
        
        verification = self._verify_answer(question, answer, context)
        
        result = {
            "answer": answer,
            "confidence": verification.get("confidence", 0.8),
            "verified": verification.get("is_grounded", True),
            "sources": [
                {
                    "node_id": node_id,
                    "type": data.get("type"),
                    "page": data.get("page_number"),
                    "relevance": f"{score:.2f}",
                    "description": data.get("description", "")[:100]
                }
                for node_id, score, data in search_results[:3]
            ]
        }
        
        if include_reasoning:
            result["reasoning"] = {
                "context_retrieved": len(search_results),
                "verification": verification
            }
        
        return result
    
    def _verify_answer(self, question: str, answer: str, context: str) -> Dict[str, Any]:
        """Verify answer is grounded in context"""
        verify_prompt = f"""
Verify if this answer is accurate and grounded in the context.

Question: {question}
Answer: {answer}
Context: {context[:2000]}

Return JSON:
{{
    "is_grounded": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list any problems"]
}}
"""
        
        result = self.vision_client.text_completion(verify_prompt)
        
        try:
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0]
            return json.loads(result)
        except:
            return {"is_grounded": True, "confidence": 0.7, "issues": []}
    
    def query_with_image(self, question: str, image: Image.Image) -> Dict[str, Any]:
        """Answer a question about a specific image/page."""
        analysis_prompt = f"""
Analyze this document image to answer the question.

Question: {question}

Provide a detailed answer based on what you can see in the image.
If the image contains tables or charts, extract and cite the specific data.
"""
        
        answer = self.vision_client.analyze_image(image, analysis_prompt)
        
        return {
            "answer": answer,
            "confidence": 0.85,
            "source": "direct_image_analysis"
        }


class VisionRAGPipeline:
    """
    Complete end-to-end Vision-Native RAG Pipeline.
    
    Now with Hierarchical Tree Support:
    - Combines PageIndex's TOC-based "human-like retrieval"
    - With the flexibility of graph-based semantic search
    - "The Power of PageIndex's Tree + The Flexibility of a Graph"
    """
    
    def __init__(self, config: VisionRAGConfig = None, extract_tree: bool = True):
        self.config = config or VisionRAGConfig()
        self.extract_tree = extract_tree
        
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.cache_dir, exist_ok=True)
        
        self.vision_client = VisionModelClient(self.config)
        self.pdf_processor = PDFProcessor(self.config, self.vision_client)
        self.extractor = VisualElementExtractor(self.vision_client, self.config)
        
        # "Don't Chunk. Graph." - Pass ingest mode to knowledge graph
        self.knowledge_graph = VisionKnowledgeGraph(
            self.vision_client, 
            ingest_mode=self.config.get_ingest_mode()
        )
        self.rag_engine = VisionRAGEngine(self.vision_client, self.knowledge_graph, self.config)
        
        # Tree extractor for hierarchical structure
        if self.extract_tree:
            from veritasgraph.tree_extractor import HierarchicalTreeExtractor
            self.tree_extractor = HierarchicalTreeExtractor(self.vision_client)
        else:
            self.tree_extractor = None
        
        self.documents: List[VisionDocument] = []
    
    def ingest_pdf(self, pdf_path: str, extract_tree: bool = None) -> Optional[VisionDocument]:
        """
        Ingest a PDF document through the complete pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            extract_tree: Override default tree extraction setting
        """
        print(f"\n{'='*60}")
        print(f"📥 INGESTING: {pdf_path}")
        print(f"{'='*60}")
        
        should_extract_tree = extract_tree if extract_tree is not None else self.extract_tree
        
        doc = self.pdf_processor.process_pdf(pdf_path)
        if not doc:
            print("❌ Failed to process PDF")
            return None
        
        # Step 1: Extract hierarchical tree structure
        if should_extract_tree and self.tree_extractor:
            print(f"\n🌳 Extracting hierarchical tree structure...")
            doc.hierarchy = self.tree_extractor.extract_hierarchy(doc.pages, doc.id)
            if doc.hierarchy:
                print(f"   ✅ Tree structure extracted: {len(doc.hierarchy.nodes)} sections")
                if doc.hierarchy.toc_detected:
                    print(f"   📑 TOC found on pages: {doc.hierarchy.toc_pages}")
        
        # Step 2: Analyze each page for visual elements
        print(f"\n🔬 Analyzing {len(doc.pages)} pages...")
        
        for page in doc.pages:
            image = Image.open(page.image_path)
            
            page_results = self.extractor.extract_page_info(image, page.page_number)
            
            page.page_type = page_results.get("classification", {}).get("page_type", "unknown")
            page.page_summary = page_results.get("summary", {}).get("summary", "")
            
            page.elements = self.extractor.create_visual_elements(page_results, page.page_number)
            
            # Link elements to their containing section
            if doc.hierarchy and page.section_id:
                for element in page.elements:
                    element.section_id = page.section_id
            
            for entity in page_results.get("entities", []):
                doc.extracted_entities.append({
                    **entity,
                    "source_page": page.page_number,
                    "section_id": page.section_id
                })
        
        # Step 3: Add to knowledge graph (with tree structure)
        self.knowledge_graph.add_document(doc)
        
        self.documents.append(doc)
        
        # Step 4: Generate document summary
        doc.document_summary = self._generate_document_summary(doc)
        
        # Print summary
        print(f"\n✅ Document ingested successfully!")
        print(f"   📄 Pages: {len(doc.pages)}")
        if doc.hierarchy:
            print(f"   🌳 Sections: {len(doc.hierarchy.nodes)}")
            max_depth = max((n.level for n in doc.hierarchy.nodes.values()), default=0)
            print(f"   📊 Tree depth: {max_depth} levels")
        print(f"   📊 Tables: {sum(len([e for e in p.elements if e.element_type == 'table']) for p in doc.pages)}")
        print(f"   📈 Charts: {sum(len([e for e in p.elements if e.element_type == 'chart']) for p in doc.pages)}")
        print(f"   🔢 Metrics: {sum(len([e for e in p.elements if e.element_type == 'metric']) for p in doc.pages)}")
        print(f"   🏷️ Entities: {len(doc.extracted_entities)}")
        
        return doc
    
    def get_document_tree(self, doc_id: str = None) -> str:
        """
        Get ASCII tree view of document structure.
        
        This shows the hierarchical organization like a Table of Contents.
        """
        if doc_id:
            return self.knowledge_graph.get_tree_visualization(doc_id)
        
        # Get tree for first/only document
        if self.documents:
            return self.knowledge_graph.get_tree_visualization(self.documents[0].id)
        
        return "No documents ingested"
    
    def navigate_to_section(self, section_title: str, doc_id: str = None) -> Dict[str, Any]:
        """
        Navigate to a section by title (tree-based retrieval).
        
        This enables "human-like retrieval" - finding content by navigating
        the document structure like a human would use a Table of Contents.
        """
        if not doc_id and self.documents:
            doc_id = self.documents[0].id
        
        if not doc_id:
            return {"error": "No document specified"}
        
        return self.knowledge_graph.get_tree_context(doc_id, section_title)
        
        return doc
    
    def _generate_document_summary(self, doc: VisionDocument) -> str:
        """Generate overall document summary"""
        page_summaries = [p.page_summary for p in doc.pages if p.page_summary]
        
        if not page_summaries:
            return "No summary available"
        
        summary_prompt = f"""
Create a comprehensive summary of this document based on page summaries.

Page Summaries:
{chr(10).join(page_summaries[:10])}

Provide:
1. Document type and purpose
2. Key findings or data points
3. Main topics covered
4. Important conclusions
"""
        
        return self.vision_client.text_completion(summary_prompt)
    
    def query(self, question: str) -> Dict[str, Any]:
        """Query the ingested documents using combined tree + graph search"""
        return self.rag_engine.query(question)
    
    def visualize_graph(self, show_tree: bool = True):
        """Visualize the knowledge graph with tree structure"""
        self.knowledge_graph.visualize(show_tree=show_tree)
    
    def export_to_json(self, output_path: str):
        """Export all extracted data to JSON, including tree structure"""
        export_data = {
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "summary": doc.document_summary,
                    "hierarchy": doc.hierarchy.to_dict() if doc.hierarchy else None,
                    "pages": [
                        {
                            "page_number": p.page_number,
                            "page_type": p.page_type,
                            "summary": p.page_summary,
                            "section_id": p.section_id,
                            "elements": [
                                {
                                    "id": e.id,
                                    "type": e.element_type,
                                    "description": e.description,
                                    "section_id": e.section_id,
                                    "data": e.structured_data
                                }
                                for e in p.elements
                            ]
                        }
                        for p in doc.pages
                    ],
                    "entities": doc.extracted_entities
                }
                for doc in self.documents
            ],
            "graph_stats": {
                "nodes": self.knowledge_graph.graph.number_of_nodes(),
                "edges": self.knowledge_graph.graph.number_of_edges(),
                "tree_nodes": sum(
                    len(h.nodes) for h in self.knowledge_graph.hierarchies.values()
                )
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Exported to {output_path}")


__all__ = [
    "VisionRAGConfig",
    "VisionModelClient",
    "PDFProcessor",
    "VisualElementExtractor",
    "VisionKnowledgeGraph",
    "VisionRAGEngine",
    "VisionRAGPipeline",
]

# Re-export tree extractor for convenience
try:
    from veritasgraph.tree_extractor import HierarchicalTreeExtractor, TreeQueryEngine
    __all__.extend(["HierarchicalTreeExtractor", "TreeQueryEngine"])
except ImportError:
    pass
