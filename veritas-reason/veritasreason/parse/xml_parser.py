"""
XML Document Parser Module

This module handles XML file parsing using lxml and xml.etree for structured data
extraction, including namespace handling and element tree processing.

Key Features:
    - XML file and string parsing
    - Namespace handling
    - Element tree processing
    - Attribute and text extraction
    - XPath query support
    - Large file processing

Main Classes:
    - XMLParser: XML document parser
    - XMLElement: Dataclass for XML element representation
    - XMLData: Dataclass for XML document representation

Example Usage:
    >>> from veritasreason.parse import XMLParser
    >>> parser = XMLParser()
    >>> data = parser.parse("data.xml")
    >>> root = data.root
    >>> elements = parser.find_elements("data.xml", "//item")

Author: VeritasReason Contributors
License: MIT
"""

import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from lxml import etree

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class XMLElement:
    """XML element representation."""

    tag: str
    text: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List["XMLElement"] = field(default_factory=list)
    namespace: Optional[str] = None


@dataclass
class XMLData:
    """XML document representation."""

    root: XMLElement
    namespaces: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class XMLParser:
    """XML document parser."""

    def __init__(self, **config):
        """
        Initialize XML parser.

        Args:
            **config: Parser configuration
        """
        self.logger = get_logger("xml_parser")
        self.config = config
        self.progress_tracker = get_progress_tracker()

    def parse(self, file_path: Union[str, Path], **options) -> XMLData:
        """
        Parse XML file.

        Args:
            file_path: Path to XML file or XML string
            **options: Parsing options:
                - engine: Parser engine ('etree' or 'lxml', default: 'lxml')
                - validate: Whether to validate XML (default: False)
                - schema: XSD schema for validation
                - extract_namespaces: Whether to extract namespaces (default: True)

        Returns:
            XMLData: Parsed XML data
        """
        # Track XML parsing
        file_path_obj = None
        if isinstance(file_path, Path) or (
            isinstance(file_path, str) and Path(file_path).exists()
        ):
            file_path_obj = Path(file_path)

        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path_obj) if file_path_obj else None,
            module="parse",
            submodule="XMLParser",
            message=f"XML: {file_path_obj.name if file_path_obj else 'content'}",
        )

        try:
            engine = options.get("engine", "lxml")

            # Load XML content
            if file_path_obj:
                if not file_path_obj.exists():
                    raise ValidationError(f"XML file not found: {file_path_obj}")

                with open(file_path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    xml_string = f.read()
                source = str(file_path_obj)
            else:
                xml_string = file_path
                source = "string"

            try:
                if engine == "lxml":
                    result = self._parse_with_lxml(xml_string, source, options)
                else:
                    result = self._parse_with_etree(xml_string, source, options)

                self.progress_tracker.stop_tracking(
                    tracking_id, status="completed", message="Parsed XML successfully"
                )
                return result

            except Exception as e:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message=str(e)
                )
                self.logger.error(f"Failed to parse XML: {e}")
                raise ProcessingError(f"Failed to parse XML: {e}")

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def _parse_with_lxml(
        self, xml_string: str, source: str, options: Dict[str, Any]
    ) -> XMLData:
        """Parse XML using lxml."""
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_string.encode("utf-8"), parser)

        # Extract namespaces
        namespaces = {}
        if options.get("extract_namespaces", True):
            namespaces = root.nsmap or {}

        # Convert to XMLElement
        root_element = self._element_to_xml_element(root)

        return XMLData(
            root=root_element,
            namespaces=namespaces,
            metadata={"source": source, "engine": "lxml"},
        )

    def _parse_with_etree(
        self, xml_string: str, source: str, options: Dict[str, Any]
    ) -> XMLData:
        """Parse XML using xml.etree.ElementTree."""
        root = ET.fromstring(xml_string)

        # Extract namespaces
        namespaces = {}
        if options.get("extract_namespaces", True):
            # Extract from root element
            for prefix, uri in ET.iterparse(
                io.StringIO(xml_string), events=["start-ns"]
            ):
                namespaces[prefix or "default"] = uri

        # Convert to XMLElement
        root_element = self._etree_element_to_xml_element(root)

        return XMLData(
            root=root_element,
            namespaces=namespaces,
            metadata={"source": source, "engine": "etree"},
        )

    def _element_to_xml_element(self, element) -> XMLElement:
        """Convert lxml element to XMLElement."""
        tag = element.tag
        if "}" in tag:
            namespace, tag = tag.split("}", 1)
            namespace = namespace[1:]
        else:
            namespace = None

        xml_elem = XMLElement(
            tag=tag,
            text=(element.text or "").strip(),
            attributes=dict(element.attrib),
            namespace=namespace,
        )

        # Process children
        for child in element:
            xml_elem.children.append(self._element_to_xml_element(child))

        return xml_elem

    def _etree_element_to_xml_element(self, element: ET.Element) -> XMLElement:
        """Convert ElementTree element to XMLElement."""
        tag = element.tag
        if "}" in tag:
            namespace, tag = tag.split("}", 1)
            namespace = namespace[1:]
        else:
            namespace = None

        xml_elem = XMLElement(
            tag=tag,
            text=(element.text or "").strip(),
            attributes=dict(element.attrib),
            namespace=namespace,
        )

        # Process children
        for child in element:
            xml_elem.children.append(self._etree_element_to_xml_element(child))

        return xml_elem

    def find_elements(
        self, file_path: Union[str, Path], xpath: str, **options
    ) -> List[XMLElement]:
        """
        Find elements using XPath.

        Args:
            file_path: Path to XML file or XML string
            xpath: XPath expression
            **options: Parsing options

        Returns:
            list: Found XML elements
        """
        xml_data = self.parse(file_path, **options)

        # Use lxml for XPath queries
        xml_string = (
            file_path
            if isinstance(file_path, str) and not Path(file_path).exists()
            else Path(file_path).read_text()
        )
        root = etree.fromstring(xml_string.encode("utf-8"))

        # Register namespaces for XPath
        namespaces = xml_data.namespaces
        elements = root.xpath(xpath, namespaces=namespaces)

        return [self._element_to_xml_element(elem) for elem in elements]

    def extract_by_tag(
        self, file_path: Union[str, Path], tag_name: str, **options
    ) -> List[XMLElement]:
        """
        Extract elements by tag name.

        Args:
            file_path: Path to XML file or XML string
            tag_name: Tag name to find
            **options: Parsing options

        Returns:
            list: Found XML elements
        """
        xml_data = self.parse(file_path, **options)

        def find_by_tag(element: XMLElement, tag: str, results: List[XMLElement]):
            if element.tag == tag:
                results.append(element)
            for child in element.children:
                find_by_tag(child, tag, results)

        results = []
        find_by_tag(xml_data.root, tag_name, results)
        return results

    def to_dict(self, file_path: Union[str, Path], **options) -> Dict[str, Any]:
        """
        Convert XML to dictionary.

        Args:
            file_path: Path to XML file or XML string
            **options: Parsing options

        Returns:
            dict: XML data as dictionary
        """
        xml_data = self.parse(file_path, **options)
        return self._element_to_dict(xml_data.root)

    def _element_to_dict(self, element: XMLElement) -> Dict[str, Any]:
        """Convert XMLElement to dictionary."""
        result = {
            "tag": element.tag,
            "text": element.text,
            "attributes": element.attributes,
        }

        if element.children:
            # Group children by tag
            children_dict = {}
            for child in element.children:
                if child.tag not in children_dict:
                    children_dict[child.tag] = []
                children_dict[child.tag].append(self._element_to_dict(child))
            result["children"] = children_dict

        return result
