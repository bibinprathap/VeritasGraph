"""
Power BI MCP Server V2
Supports Power BI Service (Cloud) only
Features: PII Detection, Audit Logging, Access Policies
Uses user-based authentication via access tokens from MCP client
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.server.models import InitializationOptions

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("powerbi-mcp-v2")

from logging.handlers import RotatingFileHandler

# Determine repo root and logs directory
REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "mcp_debug.log"

# File handler for detailed MCP server logs
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,  # 5 MB per file
    backupCount=3,
    encoding="utf-8",
)
file_handler.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Attach to root logger so all modules inherit it
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

logger.info("File logging initialized. Writing to %s", LOG_FILE)


# Import connectors
from powerbi_rest_connector import PowerBIRestConnector
from powerbi_xmla_connector import PowerBIXmlaConnector

# Import security layer
from security import SecurityLayer, get_security_layer


class PowerBIMCPServer:
    """Power BI MCP Server supporting Cloud connectivity only with user-based authentication"""

    def __init__(self):
        self.server = Server("powerbi-mcp-v2")

        # User access token (provided by MCP client)
        self.access_token: Optional[str] = os.getenv("POWERBI_ACCESS_TOKEN", None)

        # Connector instances
        self.rest_connector: Optional[PowerBIRestConnector] = None
        self.xmla_connector_cache: Dict[str, PowerBIXmlaConnector] = {}

        # Initialize security layer
        config_path = Path(__file__).parent.parent / "config" / "policies.yaml"
        self.security = SecurityLayer(
            config_path=str(config_path) if config_path.exists() else None,
            enable_pii_detection=os.getenv("ENABLE_PII_DETECTION", "true").lower() == "true",
            enable_audit=os.getenv("ENABLE_AUDIT", "true").lower() == "true",
            enable_policies=os.getenv("ENABLE_POLICIES", "true").lower() == "true"
        )

        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP tool handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return list of available tools"""
            tools = [
                # === AUTHENTICATION TOOL ===
                Tool(
                    name="set_access_token",
                    description="Set or update the Power BI access token for user-based authentication. This token should be obtained from the MCP client using OAuth2 flow.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "access_token": {
                                "type": "string",
                                "description": "OAuth2 access token for Power BI API access"
                            }
                        },
                        "required": ["access_token"]
                    }
                ),
                # === CLOUD TOOLS ===
                Tool(
                    name="list_workspaces",
                    description="List all Power BI Service workspaces accessible to the authenticated user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "access_token": {
                                "type": "string",
                                "description": "Optional: OAuth2 access token. If not provided, uses the token set via set_access_token or POWERBI_ACCESS_TOKEN env var."
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="list_datasets",
                    description="List all datasets in a Power BI Service workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {
                                "type": "string",
                                "description": "ID of the workspace"
                            },
                            "access_token": {
                                "type": "string",
                                "description": "Optional: OAuth2 access token. If not provided, uses the token set via set_access_token or POWERBI_ACCESS_TOKEN env var."
                            }
                        },
                        "required": ["workspace_id"]
                    }
                ),
                Tool(
                    name="list_tables",
                    description="List all tables in a Power BI Service dataset using REST API with COLUMNSTATISTICS(). Works with semantic models.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {
                                "type": "string",
                                "description": "ID of the workspace (GUID) - required"
                            },
                            "dataset_id": {
                                "type": "string",
                                "description": "ID of the dataset (GUID) - required"
                            },
                            "access_token": {
                                "type": "string",
                                "description": "Optional: OAuth2 access token. If not provided, uses the token set via set_access_token or POWERBI_ACCESS_TOKEN env var."
                            }
                        },
                        "required": ["workspace_id", "dataset_id"]
                    }
                ),
                Tool(
                    name="list_columns",
                    description="List columns for a table in a Power BI Service dataset using REST API with COLUMNSTATISTICS(). Works with semantic models.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {
                                "type": "string",
                                "description": "ID of the workspace (GUID) - required"
                            },
                            "dataset_id": {
                                "type": "string",
                                "description": "ID of the dataset (GUID) - required"
                            },
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table (required)"
                            },
                            "access_token": {
                                "type": "string",
                                "description": "Optional: OAuth2 access token. If not provided, uses the token set via set_access_token or POWERBI_ACCESS_TOKEN env var."
                            }
                        },
                        "required": ["workspace_id", "dataset_id", "table_name"]
                    }
                ),
                Tool(
                    name="execute_dax",
                    description="Execute a DAX query against a Power BI Service dataset",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {
                                "type": "string",
                                "description": "Name of the workspace"
                            },
                            "dataset_id": {
                                "type": "string",
                                "description": "Name of the dataset"
                            },
                            "dax_query": {
                                "type": "string",
                                "description": "DAX query to execute"
                            },
                            "access_token": {
                                "type": "string",
                                "description": "Optional: OAuth2 access token. If not provided, uses the token set via set_access_token or POWERBI_ACCESS_TOKEN env var."
                            }
                        },
                        "required": ["workspace_id", "dataset_id", "dax_query"]
                    }
                ),
                Tool(
                    name="get_model_info",
                    description="Get comprehensive model info from a Power BI Service dataset using INFO.VIEW functions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_name": {
                                "type": "string",
                                "description": "Name of the workspace"
                            },
                            "dataset_name": {
                                "type": "string",
                                "description": "Name of the dataset"
                            },
                            "access_token": {
                                "type": "string",
                                "description": "Optional: OAuth2 access token. If not provided, uses the token set via set_access_token or POWERBI_ACCESS_TOKEN env var."
                            }
                        },
                        "required": ["workspace_name", "dataset_name"]
                    }
                ),
                # === SECURITY TOOLS ===
                Tool(
                    name="security_status",
                    description="Get the current security settings and status (PII detection, audit logging, access policies)",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="security_audit_log",
                    description="View recent entries from the security audit log",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "Number of recent entries to show (default: 10)",
                                "default": 10
                            }
                        },
                        "required": []
                    }
                )
            ]
            return tools

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> List[TextContent]:
            """Handle tool calls"""
            try:
                logger.info(f"Tool called: {name} with args: {arguments}")
                args = arguments or {}

                # Authentication tool
                if name == "set_access_token":
                    result = await self._handle_set_access_token(args)
                # Cloud tools
                elif name == "list_workspaces":
                    result = await self._handle_list_workspaces(args)
                elif name == "list_datasets":
                    result = await self._handle_list_datasets(args)
                elif name == "list_tables":
                    result = await self._handle_list_tables(args)
                elif name == "list_columns":
                    result = await self._handle_list_columns(args)
                elif name == "execute_dax":
                    result = await self._handle_execute_dax(args)
                elif name == "get_model_info":
                    result = await self._handle_get_model_info(args)
                # Security tools
                elif name == "security_status":
                    result = await self._handle_security_status()
                elif name == "security_audit_log":
                    result = await self._handle_security_audit_log(args)
                else:
                    result = f"Unknown tool: {name}"

                return [TextContent(type="text", text=result)]

            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]

    # ==================== AUTHENTICATION HANDLER ====================

    async def _handle_set_access_token(self, args: Dict[str, Any]) -> str:
        """Set or update the Power BI access token"""
        try:
            access_token = args.get("access_token")
            if not access_token:
                return "Error: access_token is required"

            self.access_token = access_token
            # Clear existing connectors to force re-authentication
            self.rest_connector = None
            self.xmla_connector_cache.clear()

            logger.info("Access token updated successfully")
            return "Access token set successfully. You can now use Power BI cloud tools."
        except Exception as e:
            logger.error(f"Set access token error: {e}")
            return f"Error setting access token: {str(e)}"

    def _get_access_token(self, args: Dict[str, Any]) -> Optional[str]:
        """Get access token from args or instance variable"""
        return args.get("access_token") or self.access_token

    # ==================== CLOUD HANDLERS ====================

    def _get_rest_connector(self, access_token: Optional[str] = None) -> Optional[PowerBIRestConnector]:
        """Get or create REST connector with access token"""
        token = access_token or self.access_token
        if not token:
            logger.warning("Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var.")
            return None

        # Create new connector if token changed
        if not self.rest_connector or self.rest_connector.access_token != token:
            self.rest_connector = PowerBIRestConnector(access_token=token)
        elif self.rest_connector.access_token != token:
            self.rest_connector.set_access_token(token)

        return self.rest_connector

    def _get_xmla_connector(self, workspace_name: str, dataset_name: str, access_token: Optional[str] = None) -> Optional[PowerBIXmlaConnector]:
        """Get or create XMLA connector for a specific workspace/dataset with access token"""
        token = access_token or self.access_token
        if not token:
            logger.warning("Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var.")
            return None

        cache_key = f"{workspace_name}:{dataset_name}"

        # Create new connector if not cached or token changed
        if cache_key not in self.xmla_connector_cache:
            connector = PowerBIXmlaConnector(access_token=token)
            if connector.connect(workspace_name, dataset_name):
                self.xmla_connector_cache[cache_key] = connector
            else:
                return None
        else:
            # Update token if changed
            connector = self.xmla_connector_cache[cache_key]
            if connector.access_token != token:
                connector.set_access_token(token)
                # Reconnect with new token
                if not connector.connect(workspace_name, dataset_name):
                    del self.xmla_connector_cache[cache_key]
                    return None

        return self.xmla_connector_cache.get(cache_key)

    async def _handle_list_workspaces(self, args: Dict[str, Any]) -> str:
        """List Power BI Service workspaces"""
        try:
            access_token = self._get_access_token(args)
            connector = self._get_rest_connector(access_token)
            if not connector:
                return "Error: Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var."

            logger.info(f"connector: {connector}")

            workspaces = await asyncio.get_event_loop().run_in_executor(
                None, connector.list_workspaces
            )

            logger.info(f"workspaces {workspaces}")

            if not workspaces:
                return "No workspaces found or authentication failed."

            result = f"Power BI Workspaces ({len(workspaces)}):\n\n"
            for ws in workspaces:
                result += f"  - {ws['name']}\n"
                result += f"    ID: {ws['id']}\n\n"

            return result

        except Exception as e:
            logger.error(f"List workspaces error: {e}")
            return f"Error listing workspaces: {str(e)}"

    async def _handle_list_datasets(self, args: Dict[str, Any]) -> str:
        """List datasets in a workspace"""
        try:
            access_token = self._get_access_token(args)
            connector = self._get_rest_connector(access_token)
            workspace_id = args.get("workspace_id")

            if not connector:
                return "Error: Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var."

            if not workspace_id:
                return "Error: workspace_id is required"

            datasets = await asyncio.get_event_loop().run_in_executor(
                None, connector.list_datasets, workspace_id
            )

            if not datasets:
                return "No datasets found in this workspace."

            result = f"Datasets ({len(datasets)}):\n\n"
            for ds in datasets:
                result += f"  - {ds['name']}\n"
                result += f"    ID: {ds['id']}\n"
                result += f"    Configured by: {ds.get('configuredBy', 'Unknown')}\n\n"

            return result

        except Exception as e:
            logger.error(f"List datasets error: {e}")
            return f"Error listing datasets: {str(e)}"

    async def _handle_list_tables(self, args: Dict[str, Any]) -> str:
        """List tables in a Cloud dataset using REST API with COLUMNSTATISTICS()"""
        try:
            workspace_id = args.get("workspace_id")
            dataset_id = args.get("dataset_id")
            access_token = self._get_access_token(args)

            if not workspace_id or not dataset_id:
                return "Error: workspace_id and dataset_id are required"

            rest_connector = self._get_rest_connector(access_token)
            if not rest_connector:
                return "Error: Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var."

            # Use REST API with COLUMNSTATISTICS() - works with semantic models
            tables = await asyncio.get_event_loop().run_in_executor(
                None, rest_connector.get_tables, workspace_id, dataset_id
            )

            if tables:
                result = f"Tables in dataset ({len(tables)}):\n\n"
                for table in tables:
                    result += f"  - {table['name']}\n"
                    result += f"    Columns: {len(table.get('columns', []))}\n"
                    result += "\n"
                return result
            else:
                return f"No tables found or error occurred. Check workspace_id and dataset_id are correct."

        except Exception as e:
            logger.error(f"List tables error: {e}", exc_info=True)
            return f"Error listing tables: {str(e)}"

    async def _handle_list_columns(self, args: Dict[str, Any]) -> str:
        """List columns for a table in Cloud dataset using REST API with COLUMNSTATISTICS()"""
        try:
            workspace_id = args.get("workspace_id")
            dataset_id = args.get("dataset_id")
            table_name = args.get("table_name")
            access_token = self._get_access_token(args)

            if not workspace_id or not dataset_id:
                return "Error: workspace_id and dataset_id are required"
            if not table_name:
                return "Error: table_name is required"

            rest_connector = self._get_rest_connector(access_token)
            if not rest_connector:
                return "Error: Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var."

            # Get all tables using COLUMNSTATISTICS()
            tables = await asyncio.get_event_loop().run_in_executor(
                None, rest_connector.get_tables, workspace_id, dataset_id
            )

            # Find the specific table
            target_table = None
            for table in tables:
                if table.get("name") == table_name:
                    target_table = table
                    break

            if target_table:
                columns = target_table.get("columns", [])
                if columns:
                    result = f"Columns in '{table_name}' ({len(columns)}):\n\n"
                    for col in columns:
                        col_name = col.get("name", "Unknown")
                        cardinality = col.get("cardinality")
                        min_val = col.get("min")
                        max_val = col.get("max")
                        
                        result += f"  - {col_name}"
                        if cardinality is not None:
                            result += f" [Cardinality: {cardinality}]"
                        if min_val is not None:
                            result += f" [Min: {min_val}]"
                        if max_val is not None:
                            result += f" [Max: {max_val}]"
                        result += "\n"
                    return result
                else:
                    return f"No columns found for table '{table_name}'."
            else:
                return f"Table '{table_name}' not found in dataset. Check table name spelling."

        except Exception as e:
            logger.error(f"List columns error: {e}", exc_info=True)
            return f"Error listing columns: {str(e)}"

    async def _handle_execute_dax(self, args: Dict[str, Any]) -> str:
        """Execute DAX on Cloud dataset"""
        try:
            workspace_id = args.get("workspace_id")
            dataset_id = args.get("dataset_id")
            dax_query = args.get("dax_query")
            access_token = self._get_access_token(args)

            if not all([workspace_id, dataset_id, dax_query]):
                return "Error: workspace_id, dataset_id, and dax_query are required"

            # Get REST connector
            rest_connector = self._get_rest_connector(access_token)
            if not rest_connector:
                return "Error: Access token not set. Use set_access_token tool or set POWERBI_ACCESS_TOKEN env var."

            # Execute query using REST connector
            rows = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: rest_connector.execute_dax_query(workspace_id, dataset_id, dax_query)
            )

            # Build response
            result = f"Query returned {len(rows)} row(s)\n\n"
            result += json.dumps(rows, indent=2, default=str)

            return result

        except Exception as e:
            logger.error(f"Execute DAX error: {e}", exc_info=True)
            return f"Error executing DAX: {str(e)}"

    async def _handle_get_model_info(self, args: Dict[str, Any]) -> str:
        """Get model info from Cloud dataset using INFO.VIEW functions"""
        try:
            workspace_name = args.get("workspace_name")
            dataset_name = args.get("dataset_name")
            access_token = self._get_access_token(args)

            if not workspace_name or not dataset_name:
                return "Error: workspace_name and dataset_name are required"

            connector = await asyncio.get_event_loop().run_in_executor(
                None, self._get_xmla_connector, workspace_name, dataset_name, access_token
            )

            if not connector:
                return f"Error: Could not connect to dataset '{dataset_name}'. Ensure access token is set."

            result = f"=== Semantic Model Info: {dataset_name} ===\n\n"

            # INFO.VIEW.TABLES
            try:
                tables = await asyncio.get_event_loop().run_in_executor(
                    None, connector.execute_dax, "EVALUATE INFO.VIEW.TABLES()"
                )
                result += f"--- TABLES ({len(tables)}) ---\n"
                for t in tables:
                    name = t.get("[Name]", t.get("Name", "Unknown"))
                    if not t.get("[IsHidden]", t.get("IsHidden", False)):
                        result += f"  - {name}\n"
                result += "\n"
            except Exception as e:
                result += f"--- TABLES ---\nError: {e}\n\n"

            # INFO.VIEW.MEASURES
            try:
                measures = await asyncio.get_event_loop().run_in_executor(
                    None, connector.execute_dax, "EVALUATE INFO.VIEW.MEASURES()"
                )
                result += f"--- MEASURES ({len(measures)}) ---\n"
                for m in measures:
                    name = m.get("[Name]", m.get("Name", "Unknown"))
                    result += f"  - {name}\n"
                result += "\n"
            except Exception as e:
                result += f"--- MEASURES ---\nError: {e}\n\n"

            # INFO.VIEW.RELATIONSHIPS
            try:
                rels = await asyncio.get_event_loop().run_in_executor(
                    None, connector.execute_dax, "EVALUATE INFO.VIEW.RELATIONSHIPS()"
                )
                result += f"--- RELATIONSHIPS ({len(rels)}) ---\n"
                for r in rels:
                    from_t = r.get("[FromTableName]", r.get("FromTableName", ""))
                    from_c = r.get("[FromColumnName]", r.get("FromColumnName", ""))
                    to_t = r.get("[ToTableName]", r.get("ToTableName", ""))
                    to_c = r.get("[ToColumnName]", r.get("ToColumnName", ""))
                    result += f"  - {from_t}[{from_c}] -> {to_t}[{to_c}]\n"
                result += "\n"
            except Exception as e:
                result += f"--- RELATIONSHIPS ---\nError: {e}\n\n"

            return result

        except Exception as e:
            logger.error(f"Get model info error: {e}")
            return f"Error getting model info: {str(e)}"

    # ==================== SECURITY HANDLERS ====================

    async def _handle_security_status(self) -> str:
        """Get security layer status"""
        try:
            status = self.security.get_status()
            policy_summary = self.security.get_policy_summary()

            result = "=== Power BI MCP Security Status ===\n\n"

            # Enabled features
            result += "--- Features ---\n"
            enabled = status.get('enabled', {})
            result += f"  PII Detection:    {'✅ Enabled' if enabled.get('pii_detection') else '❌ Disabled'}\n"
            result += f"  Audit Logging:    {'✅ Enabled' if enabled.get('audit_logging') else '❌ Disabled'}\n"
            result += f"  Access Policies:  {'✅ Enabled' if enabled.get('access_policies') else '❌ Disabled'}\n\n"

            # PII Detection settings
            if enabled.get('pii_detection'):
                pii = status.get('pii_detector', {})
                result += "--- PII Detection ---\n"
                result += f"  Strategy: {pii.get('strategy', 'N/A')}\n"
                result += f"  Types: {', '.join(pii.get('enabled_types', []))}\n\n"

            # Policy settings
            if enabled.get('access_policies'):
                result += "--- Access Policies ---\n"
                result += f"  Enabled: {policy_summary.get('enabled', False)}\n"
                result += f"  Max rows per query: {policy_summary.get('max_rows', 'N/A')}\n"
                result += f"  Tables with policies: {len(policy_summary.get('tables_with_policies', []))}\n\n"

            # Audit log info
            if enabled.get('audit_logging'):
                audit = status.get('audit', {})
                result += "--- Audit Log ---\n"
                result += f"  Session ID: {audit.get('session_id', 'N/A')}\n"
                result += f"  Queries logged: {audit.get('query_count', 0)}\n"
                result += f"  Log file: {audit.get('log_file', 'N/A')}\n"

            return result

        except Exception as e:
            logger.error(f"Security status error: {e}")
            return f"Error getting security status: {str(e)}"

    async def _handle_security_audit_log(self, args: Dict[str, Any]) -> str:
        """View recent audit log entries"""
        try:
            count = args.get("count", 10)

            if not self.security.enable_audit or not self.security.audit_logger:
                return "Audit logging is not enabled."

            events = self.security.audit_logger.get_recent_events(count)

            if not events:
                return "No audit log entries found."

            result = f"=== Recent Audit Log ({len(events)} entries) ===\n\n"

            for event in events[-count:]:
                timestamp = event.get('timestamp', 'N/A')
                event_type = event.get('event_type', 'unknown')
                severity = event.get('severity', 'info')

                result += f"[{timestamp}] [{severity.upper()}] {event_type}\n"

                # Show details based on event type
                if event_type in ('query_success', 'query_failure'):
                    query_info = event.get('query', {})
                    result_info = event.get('result', {})
                    pii_info = event.get('pii', {})

                    result += f"  Query: {query_info.get('fingerprint', 'N/A')}\n"
                    result += f"  Rows: {result_info.get('row_count', 0)}, Duration: {result_info.get('duration_ms', 0):.0f}ms\n"

                    if pii_info.get('detected'):
                        result += f"  ⚠️ PII: {pii_info.get('count', 0)} instances\n"

                elif event_type == 'policy_violation':
                    details = event.get('details', {})
                    result += f"  Policy: {details.get('policy', 'N/A')}\n"
                    result += f"  Violation: {details.get('violation', 'N/A')}\n"

                result += "\n"

            return result

        except Exception as e:
            logger.error(f"Audit log error: {e}")
            return f"Error reading audit log: {str(e)}"

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Power BI MCP Server V2 starting...")
            logger.info("Supports: Power BI Service (cloud) with user-based authentication")
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="powerbi-mcp-v2",
                    server_version="2.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


# Global server instance
server = PowerBIMCPServer()

def main():
    """Main entry point"""
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
