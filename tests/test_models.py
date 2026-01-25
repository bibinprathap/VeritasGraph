"""Tests for veritasgraph.models module."""

import pytest
from veritasgraph.models import (
    VisualElement,
    DocumentPage,
    VisionDocument,
    GraphNode,
)


class TestVisualElement:
    """Tests for VisualElement dataclass."""

    def test_create_basic(self):
        """Test creating a basic VisualElement."""
        element = VisualElement(
            id="elem_001",
            element_type="table",
            page_number=1,
            description="A table showing sales data",
        )
        assert element.id == "elem_001"
        assert element.element_type == "table"
        assert element.page_number == 1
        assert element.description == "A table showing sales data"
        assert element.confidence == 0.0
        assert element.structured_data is None

    def test_create_with_all_fields(self):
        """Test creating a VisualElement with all fields."""
        element = VisualElement(
            id="elem_002",
            element_type="chart",
            page_number=2,
            description="Bar chart of revenue",
            structured_data={"type": "bar", "values": [1, 2, 3]},
            raw_text="Revenue: $1M, $2M, $3M",
            confidence=0.95,
            bounding_box=(10, 20, 300, 400),
            metadata={"source": "page_2"},
        )
        assert element.structured_data == {"type": "bar", "values": [1, 2, 3]}
        assert element.confidence == 0.95
        assert element.bounding_box == (10, 20, 300, 400)


class TestDocumentPage:
    """Tests for DocumentPage dataclass."""

    def test_create_basic(self):
        """Test creating a basic DocumentPage."""
        page = DocumentPage(
            page_number=1,
            image_path="/path/to/image.jpg",
            image_base64="base64data",
            width=800,
            height=600,
        )
        assert page.page_number == 1
        assert page.width == 800
        assert page.height == 600
        assert page.elements == []
        assert page.page_type == "unknown"


class TestVisionDocument:
    """Tests for VisionDocument dataclass."""

    def test_create_basic(self):
        """Test creating a basic VisionDocument."""
        doc = VisionDocument(
            id="doc_001",
            source_path="/path/to/doc.pdf",
            title="Test Document",
        )
        assert doc.id == "doc_001"
        assert doc.title == "Test Document"
        assert doc.pages == []
        assert doc.document_type == "unknown"


class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_create_basic(self):
        """Test creating a basic GraphNode."""
        node = GraphNode(
            id="node_001",
            node_type="entity",
            name="Test Entity",
            description="A test entity for unit testing",
            source_element_id="elem_001",
            source_page=1,
        )
        assert node.id == "node_001"
        assert node.node_type == "entity"
        assert node.name == "Test Entity"
        assert node.properties == {}
        assert node.embedding is None
