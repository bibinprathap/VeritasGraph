"""
MCP Parser Module

This module provides parsing capabilities for MCP (Model Context Protocol) server
responses and tool outputs, handling various response formats from any Python MCP server.

Key Features:
    - Generic parsing for any Python MCP server responses
    - Support for JSON, text, and binary formats
    - Structured data extraction from tool outputs
    - Integration with existing parsers

Main Classes:
    - MCPParser: Main MCP response parser

Example Usage:
    >>> from veritasreason.parse import MCPParser
    >>> parser = MCPParser()
    >>> parsed = parser.parse_resource_response(resource_data)
    >>> parsed = parser.parse_tool_output(tool_result)

Author: VeritasReason Contributors
License: MIT
"""

import json
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from .document_parser import DocumentParser
from .structured_data_parser import StructuredDataParser


class MCPParser:
    """
    Generic parser for MCP server responses and tool outputs.

    This class provides parsing capabilities for responses from any Python MCP server,
    handling various formats (JSON, text, binary) and extracting structured data.

    Features:
        - Generic parsing for any MCP server domain
        - Support for multiple response formats
        - Structured data extraction
        - Integration with existing parsers

    Example Usage:
        >>> parser = MCPParser()
        >>> parsed = parser.parse_resource_response(resource_data)
        >>> parsed = parser.parse_tool_output(tool_result)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize MCP parser.

        Args:
            config: Parser configuration dictionary
            **kwargs: Additional configuration parameters
        """
        self.logger = get_logger("mcp_parser")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize helper parsers
        self.structured_parser = StructuredDataParser(**self.config)
        self.document_parser = DocumentParser(**self.config)

        self.logger.debug("MCP parser initialized")

    def parse_resource_response(
        self, resource_data: Dict[str, Any], **options
    ) -> Dict[str, Any]:
        """
        Parse a resource response from an MCP server.

        Args:
            resource_data: Resource data dictionary from MCP server
            **options: Additional parsing options

        Returns:
            Parsed resource data dictionary
        """
        try:
            result = {
                "type": "resource",
                "raw": resource_data,
                "content": None,
                "metadata": {},
                "parsed_content": None,
            }

            # Extract content
            content = resource_data.get("contents", [])
            if content:
                # Handle multiple contents (MCP allows multiple)
                parsed_contents = []
                for item in content:
                    parsed_item = self._parse_content_item(item)
                    if parsed_item:
                        parsed_contents.append(parsed_item)

                result["content"] = parsed_contents
                result["parsed_content"] = (
                    parsed_contents[0] if len(parsed_contents) == 1 else parsed_contents
                )

            # Extract metadata
            result["metadata"] = resource_data.get("metadata", {})
            result["uri"] = resource_data.get("uri")
            result["mimeType"] = resource_data.get("mimeType")

            return result

        except Exception as e:
            self.logger.error(f"Failed to parse resource response: {e}")
            raise ProcessingError(f"Failed to parse resource response: {e}") from e

    def parse_tool_output(
        self, tool_result: Dict[str, Any], **options
    ) -> Dict[str, Any]:
        """
        Parse a tool output from an MCP server.

        Args:
            tool_result: Tool result dictionary from MCP server
            **options: Additional parsing options

        Returns:
            Parsed tool output dictionary
        """
        try:
            result = {
                "type": "tool_output",
                "raw": tool_result,
                "content": None,
                "metadata": {},
                "parsed_content": None,
            }

            # Extract content
            content = tool_result.get("content", [])
            if content:
                # Handle multiple contents
                parsed_contents = []
                for item in content:
                    parsed_item = self._parse_content_item(item)
                    if parsed_item:
                        parsed_contents.append(parsed_item)

                result["content"] = parsed_contents
                result["parsed_content"] = (
                    parsed_contents[0] if len(parsed_contents) == 1 else parsed_contents
                )

            # Extract metadata
            result["metadata"] = tool_result.get("metadata", {})
            result["isError"] = tool_result.get("isError", False)

            return result

        except Exception as e:
            self.logger.error(f"Failed to parse tool output: {e}")
            raise ProcessingError(f"Failed to parse tool output: {e}") from e

    def _parse_content_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single content item from MCP response.

        Args:
            item: Content item dictionary

        Returns:
            Parsed content dictionary or None
        """
        try:
            content_type = item.get("type", "text")
            text = item.get("text", "")
            data = item.get("data")
            mime_type = item.get("mimeType")

            parsed = {"type": content_type, "mimeType": mime_type, "raw": item}

            if content_type == "text":
                parsed["text"] = text
                # Try to parse as structured data if it looks like JSON
                if text.strip().startswith(("{", "[")):
                    try:
                        parsed["structured"] = json.loads(text)
                    except json.JSONDecodeError:
                        pass
            elif content_type == "resource":
                parsed["resource"] = item.get("resource")
            elif content_type == "image" and data:
                parsed["image_data"] = data
                parsed["image_format"] = mime_type
            else:
                parsed["data"] = data

            # If we have text and it looks like structured data, try parsing
            if "text" in parsed and not "structured" in parsed:
                text_content = parsed["text"]
                # Try JSON
                if text_content.strip().startswith(("{", "[")):
                    try:
                        parsed["structured"] = json.loads(text_content)
                    except json.JSONDecodeError:
                        pass
                # Try CSV-like
                elif "\t" in text_content or "," in text_content:
                    try:
                        lines = text_content.strip().split("\n")
                        if len(lines) > 1:
                            parsed["structured"] = self._parse_csv_like(text_content)
                    except Exception:
                        pass

            return parsed

        except Exception as e:
            self.logger.warning(f"Failed to parse content item: {e}")
            return None

    def _parse_csv_like(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse CSV-like text data.

        Args:
            text: CSV-like text

        Returns:
            List of dictionaries
        """
        lines = text.strip().split("\n")
        if not lines:
            return []

        # Detect delimiter
        delimiter = "\t" if "\t" in lines[0] else ","

        # Parse header
        header = [h.strip() for h in lines[0].split(delimiter)]

        # Parse rows
        rows = []
        for line in lines[1:]:
            if not line.strip():
                continue
            values = [v.strip() for v in line.split(delimiter)]
            if len(values) == len(header):
                rows.append(dict(zip(header, values)))

        return rows

    def parse_mcp_data(
        self, mcp_data: Any, data_type: Optional[str] = None, **options
    ) -> Dict[str, Any]:
        """
        Parse MCP data (generic method that auto-detects type).

        Args:
            mcp_data: MCP data to parse (can be resource or tool output)
            data_type: Optional data type hint ("resource" or "tool_output")
            **options: Additional parsing options

        Returns:
            Parsed data dictionary
        """
        try:
            # Auto-detect type if not provided
            if not data_type:
                if isinstance(mcp_data, dict):
                    if "contents" in mcp_data:
                        data_type = "resource"
                    elif "content" in mcp_data:
                        data_type = "tool_output"
                    else:
                        # Default to tool_output
                        data_type = "tool_output"
                else:
                    raise ProcessingError("Cannot determine MCP data type")

            if data_type == "resource":
                return self.parse_resource_response(mcp_data, **options)
            elif data_type == "tool_output":
                return self.parse_tool_output(mcp_data, **options)
            else:
                raise ProcessingError(f"Unknown MCP data type: {data_type}")

        except Exception as e:
            self.logger.error(f"Failed to parse MCP data: {e}")
            raise ProcessingError(f"Failed to parse MCP data: {e}") from e
