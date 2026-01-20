"""
MCP Client wrapper for connecting to Power BI MCP Server
"""
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.config import settings

logger = logging.getLogger(__name__)


class PowerBIMCPClient:
    """Client for interacting with Power BI MCP Server"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._stdio_context = None
        self._session_context = None
        self.server_params = StdioServerParameters(
            command=settings.MCP_PYTHON_COMMAND,
            args=[settings.MCP_SERVER_PATH],
            env={
                "PYTHONPATH": settings.MCP_PYTHON_PATH,
            },
        )
    
    async def connect(self) -> None:
        """Connect to the MCP server"""
        if self.session is None:
            logger.info("Connecting to MCP server...")
            # Enter the stdio_client context manager
            self._stdio_context = stdio_client(self.server_params)
            read_stream, write_stream = await self._stdio_context.__aenter__()
            
            # Create and initialize session
            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()
            await self.session.initialize()
            logger.info("Connected to MCP server")
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server"""
        try:
            if self._session_context and self.session:
                await self._session_context.__aexit__(None, None, None)
                self._session_context = None
                self.session = None
        except Exception as e:
            logger.warning(f"Error closing session context: {e}")
        
        try:
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
                self._stdio_context = None
        except Exception as e:
            logger.warning(f"Error closing stdio context: {e}")
        
        logger.info("Disconnected from MCP server")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def set_access_token(self, access_token: str) -> str:
        """Set the access token for Power BI authentication"""
        if not self.session:
            await self.connect()
        
        result = await self.session.call_tool(
            "set_access_token",
            arguments={"access_token": access_token}
        )
        return result.content[0].text if result.content else ""
    
    async def list_workspaces(self, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all Power BI workspaces"""
        if not self.session:
            await self.connect()
        
        args = {}
        if access_token:
            args["access_token"] = access_token
        
        result = await self.session.call_tool("list_workspaces", arguments=args)
        response_text = result.content[0].text if result.content else ""
        
        # Parse the response text to extract workspace information
        # Format: "  - Workspace Name\n    ID: workspace-id"
        workspaces = []
        lines = response_text.split("\n")
        current_workspace = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                # New workspace name
                workspace_name = line[2:].strip()
                current_workspace = {"name": workspace_name, "id": None}
            elif "ID:" in line and current_workspace:
                # Extract ID
                workspace_id = line.split("ID:")[-1].strip()
                current_workspace["id"] = workspace_id
                workspaces.append(current_workspace)
                current_workspace = None
        
        return workspaces
    
    async def list_datasets(
        self, 
        workspace_id: str, 
        access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List datasets in a workspace"""
        if not self.session:
            await self.connect()
        
        args = {"workspace_id": workspace_id}
        if access_token:
            args["access_token"] = access_token
        
        result = await self.session.call_tool("list_datasets", arguments=args)
        response_text = result.content[0].text if result.content else ""
        
        # Parse response text
        # Format: "  - Dataset Name\n    ID: dataset-id"
        datasets = []
        lines = response_text.split("\n")
        current_dataset = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                dataset_name = line[2:].strip()
                current_dataset = {"name": dataset_name, "id": None}
            elif "ID:" in line and current_dataset:
                dataset_id = line.split("ID:")[-1].strip()
                current_dataset["id"] = dataset_id
                datasets.append(current_dataset)
                current_dataset = None
        
        return datasets
    
    async def list_tables(
        self,
        workspace_id: str,
        dataset_id: str,
        access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List tables in a dataset"""
        if not self.session:
            await self.connect()
        
        args = {
            "workspace_id": workspace_id,
            "dataset_id": dataset_id
        }
        if access_token:
            args["access_token"] = access_token
        
        result = await self.session.call_tool("list_tables", arguments=args)
        response_text = result.content[0].text if result.content else ""
        
        # Parse response text to extract table names
        tables = []
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                table_name = line[2:].strip()
                tables.append({"name": table_name})
        
        return tables
    
    async def list_columns(
        self,
        workspace_id: str,
        dataset_id: str,
        table_name: str,
        access_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List columns in a table"""
        if not self.session:
            await self.connect()
        
        args = {
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "table_name": table_name
        }
        if access_token:
            args["access_token"] = access_token
        
        result = await self.session.call_tool("list_columns", arguments=args)
        response_text = result.content[0].text if result.content else ""
        
        # Parse response text to extract column names
        columns = []
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                col_info = line[2:].strip()
                # Extract column name (before any brackets)
                col_name = col_info.split(" [")[0] if " [" in col_info else col_info
                columns.append({"name": col_name})
        
        return columns
    
    async def execute_dax(
        self,
        workspace_id: str,
        dataset_id: str,
        dax_query: str,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a DAX query"""
        if not self.session:
            await self.connect()
        
        args = {
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "dax_query": dax_query
        }
        if access_token:
            args["access_token"] = access_token
        
        result = await self.session.call_tool("execute_dax", arguments=args)
        response_text = result.content[0].text if result.content else ""
        
        # Try to parse JSON response if available
        try:
            import json
            # The response might be JSON formatted
            if response_text.startswith("{") or response_text.startswith("["):
                return json.loads(response_text)
        except:
            pass
        
        # Return as text if not JSON
        return {"result": response_text}
    
    async def get_available_tools(self) -> List[str]:
        """Get list of available MCP tools"""
        if not self.session:
            await self.connect()
        
        tools = await self.session.list_tools()
        return [tool.name for tool in tools.tools]

