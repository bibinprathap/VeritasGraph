"""
API routes for the Power BI Natural Language Query API
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

# Add src to path for direct REST connector access
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from backend.mcp_client import PowerBIMCPClient
from backend.models.requests import NaturalLanguageQueryRequest, ChatRequest
from backend.models.responses import DAXQueryResponse, ChatResponse, ToolCall
from backend.llm_provider import llm_provider
from backend.services.chat_agent import ChatAgent
from backend.services.schema_cache import schema_cache
from backend.utils.parser import (
    sanitize_dax,
    enforce_table_quotes,
    repair_averagex_filter,
    validate_aggregatorx_usage,
    fix_unquoted_table_names,
    fix_distinct_in_row
)
import re
import json

# Import REST connector directly for DAX execution
try:
    from powerbi_rest_connector import PowerBIRestConnector
    REST_CONNECTOR_AVAILABLE = True
except ImportError:
    REST_CONNECTOR_AVAILABLE = False

from backend.utils.logger import setup_logger

# Set up logging
logger = setup_logger("powerbi-backend")

router = APIRouter()


# =========================
# MCP CLIENT SINGLETON
# =========================

_mcp_client: Optional[PowerBIMCPClient] = None


async def get_mcp_client() -> PowerBIMCPClient:
    global _mcp_client
    if _mcp_client is None:
        logger.info("Connecting to MCP server...")
        _mcp_client = PowerBIMCPClient()
        await _mcp_client.connect()

        try:
            tools = await _mcp_client.get_available_tools()
            logger.info(f"MCP tools available: {tools}")
        except Exception as e:
            logger.warning(f"Could not list MCP tools: {e}")

    return _mcp_client


async def shutdown_mcp_client():
    global _mcp_client
    if _mcp_client:
        await _mcp_client.disconnect()
        _mcp_client = None
        logger.info("MCP client disconnected")


@router.on_event("startup")
async def startup_event():
    await get_mcp_client()


@router.on_event("shutdown")
async def shutdown_event():
    await shutdown_mcp_client()


# =========================
# LLM PROMPT
# =========================

DAX_JSON_PROMPT = """
SCHEMA:
{schema_text}

USER QUESTION:
{user_query}

TASK:
Generate a DAX query to answer the question.

CRITICAL DAX SYNTAX RULES (MUST follow exactly):
1. Table names with spaces MUST be wrapped in single quotes: 'Table Name'
2. Column references MUST use: 'Table Name'[Column Name]
3. DAX MUST start with EVALUATE

QUERY PATTERNS (use these exact patterns):

For DISTINCT/UNIQUE VALUES (list all unique values in a column):
  EVALUATE DISTINCT('Table Name'[Column Name])

For COUNTING distinct values:
  EVALUATE ROW("Count", DISTINCTCOUNT('Table Name'[Column Name]))

For AGGREGATIONS (sum, average, count):
  EVALUATE ROW("Result", SUM('Table Name'[Column Name]))
  EVALUATE ROW("Result", AVERAGE('Table Name'[Column Name]))
  EVALUATE ROW("Result", COUNT('Table Name'[Column Name]))

For FILTERED aggregations:
  EVALUATE ROW("Result", CALCULATE(SUM('Table Name'[Column]), 'Table Name'[Filter Col] = "Value"))

For GROUPED data:
  EVALUATE SUMMARIZECOLUMNS('Table Name'[Group Column], "Total", SUM('Table Name'[Value Column]))

For TOP N:
  EVALUATE TOPN(10, 'Table Name', 'Table Name'[Column], DESC)

RULES:
- NEVER use ROW() with DISTINCT() - DISTINCT returns a table, not a scalar
- AVERAGEX/SUMX/COUNTX take exactly 2 arguments: (table, expression)
- Use FILTER() for row-level conditions inside iterator functions

OUTPUT:
Return ONLY valid JSON:
{
  "intent": "<scalar|list|grouped|tabular>",
  "dax": "EVALUATE ..."
}

NO explanations. NO markdown. NO extra text.
"""


# =========================
# HELPERS
# =========================

def extract_json(text: str) -> Dict:
    """Extract first JSON object from LLM output with error handling"""
    # Try to find JSON object boundaries more carefully
    # Look for opening brace and try to find matching closing brace
    start_idx = text.find('{')
    if start_idx == -1:
        raise ValueError("LLM did not return valid JSON: No opening brace found")
    
    # Try to find the matching closing brace by counting braces
    brace_count = 0
    end_idx = start_idx
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    
    if brace_count != 0:
        # Fallback: use regex if brace matching fails
        match = re.search(r"\{.*?\}", text[start_idx:], re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            raise ValueError("LLM did not return valid JSON: Unmatched braces")
    else:
        json_str = text[start_idx:end_idx]
    
    # Try to parse JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Try to fix common JSON issues
        # Remove trailing commas before closing braces/brackets
        fixed_json = re.sub(r',(\s*[}\]])', r'\1', json_str)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            # If still fails, raise with more context
            logger.error(f"Failed to parse JSON. Error: {e}. JSON string: {json_str[:200]}")
            raise ValueError(f"LLM returned malformed JSON: {str(e)}. JSON: {json_str[:200]}...")


def validate_dax(dax: str) -> str:
    dax = dax.strip().replace("```", "")
    if not dax.upper().startswith("EVALUATE"):
        raise ValueError("DAX must start with EVALUATE")

    banned = ["DROP", "DELETE", "INSERT", "UPDATE", "CREATE"]
    if any(b in dax.upper() for b in banned):
        raise ValueError("Invalid keywords in DAX")

    return dax


def format_schema(schema: Dict[str, List[str]]) -> str:
    lines = ["SCHEMA:"]
    for table, cols in schema.items():
        lines.append(f"- {table}: {', '.join(cols)}")
    return "\n".join(lines)


async def build_schema(
    client: PowerBIMCPClient,
    workspace_id: str,
    dataset_id: str,
    max_tables: int = 40
) -> Dict[str, List[str]]:
    """Fetch tables + columns using MCP tools"""
    schema: Dict[str, List[str]] = {}

    tables = await client.list_tables(workspace_id, dataset_id)
    print(tables,'tables')
    if not tables:
        return schema

    for table in tables[:max_tables]:
        table_name = table.get("name") or table.get("displayName")
        if not table_name:
            continue

        columns = await client.list_columns(workspace_id, dataset_id, table_name)
        col_names = []

        for col in columns or []:
            col_names.append(col.get("name") or col.get("displayName"))

        schema[table_name] = col_names

    return schema


# =========================
# MAIN ENDPOINT
# =========================

@router.post("/query", response_model=DAXQueryResponse)
async def natural_language_query(
    request: NaturalLanguageQueryRequest
) -> DAXQueryResponse:

    try:
        client = await get_mcp_client()

        # 1️⃣ Set access token (ONLY ONCE)
        await client.set_access_token(request.access_token)

        # 2️⃣ Resolve workspace
        workspace_id = request.workspace_id
        if not workspace_id:
            workspaces = await client.list_workspaces()
            if not workspaces:
                raise HTTPException(400, "No workspaces found")
            workspace_id = workspaces[0]["id"]

        # 3️⃣ Resolve dataset
        dataset_id = request.dataset_id
        if not dataset_id:
            datasets = await client.list_datasets(workspace_id)
            if not datasets:
                raise HTTPException(400, "No datasets found")
            dataset_id = datasets[0]["id"]

        # 4️⃣ Build schema
        schema = await build_schema(client, workspace_id, dataset_id)
        if not schema:
            raise HTTPException(400, "Could not fetch schema")

        schema_text = format_schema(schema)
        logger.info(f"Fetched schema:\n{schema_text}")

        # 5️⃣ Generate DAX via LLM
        llm = llm_provider.get_llm()
        prompt = f"""{DAX_JSON_PROMPT}

{schema_text}

QUESTION:
{request.query}
"""

        response = await llm.ainvoke(prompt)
        raw_output = response.content if hasattr(response, "content") else str(response)
        
        logger.debug(f"LLM raw output: {raw_output[:500]}")  # Log first 500 chars for debugging

        try:
            dax_payload = extract_json(raw_output)
        except ValueError as e:
            logger.error(f"Failed to extract JSON from LLM output: {e}")
            logger.error(f"Full LLM output: {raw_output}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM returned invalid JSON format: {str(e)}"
            )
        
        dax_query = dax_payload.get("dax", "")
        if not dax_query:
            logger.error(f"LLM returned JSON without 'dax' field. Payload: {dax_payload}")
            raise HTTPException(
                status_code=500,
                detail="LLM response missing 'dax' field"
            )

        # ==============================
        # 🛡️ DAX GUARDRAILS START HERE
        # ==============================

        tables_used = dax_payload.get("tables_used", [])

        dax_query = sanitize_dax(dax_query)
        dax_query = fix_unquoted_table_names(dax_query)  # Fix table names with spaces
        dax_query = fix_distinct_in_row(dax_query)  # Fix ROW(DISTINCT(...)) pattern
        dax_query = enforce_table_quotes(dax_query, tables_used)
        dax_query = repair_averagex_filter(dax_query)
        validate_aggregatorx_usage(dax_query)
        dax_query = validate_dax(dax_query)

        logger.info(f"Final DAX to execute:\n{dax_query}")

        # 6️⃣ Execute DAX (DO NOT re-pass token if MCP stores it)
        result = await client.execute_dax(
            workspace_id,
            dataset_id,
            dax_query
        )

        rows = result.get("result") if isinstance(result, dict) else result

        return DAXQueryResponse(
            natural_language_query=request.query,
            dax_query=dax_query,
            result=rows,
            metadata={
                "workspace_id": workspace_id,
                "dataset_id": dataset_id,
                "tables_used": tables_used,
                "columns_used": dax_payload.get("columns_used"),
            },
            error=None
        )

    except Exception as e:
        logger.error("Query failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "powerbi-nlq-api"}


@router.get("/tools")
async def list_tools() -> Dict[str, Any]:
    """List available MCP tools"""
    try:
        client = await get_mcp_client()
        tools = await client.get_available_tools()
        return {"status": "connected", "tools": tools, "count": len(tools)}
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces")
async def list_workspaces(access_token: str) -> Dict[str, Any]:
    """List Power BI workspaces"""
    try:
        client = await get_mcp_client()
        await client.set_access_token(access_token)
        workspaces = await client.list_workspaces(access_token)
        return {"workspaces": workspaces, "count": len(workspaces)}
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets")
async def list_datasets(workspace_id: str, access_token: str) -> Dict[str, Any]:
    """List datasets in a workspace"""
    try:
        client = await get_mcp_client()
        await client.set_access_token(access_token)
        datasets = await client.list_datasets(workspace_id, access_token)
        return {"datasets": datasets, "count": len(datasets)}
    except Exception as e:
        logger.error(f"Error listing datasets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def list_tables(workspace_id: str, dataset_id: str, access_token: str) -> Dict[str, Any]:
    """List tables in a dataset"""
    try:
        client = await get_mcp_client()
        await client.set_access_token(access_token)
        tables = await client.list_tables(workspace_id, dataset_id, access_token)
        return {"tables": tables, "count": len(tables)}
    except Exception as e:
        logger.error(f"Error listing tables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# CHAT ENDPOINT
# =========================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Conversational chat endpoint for Power BI data exploration and querying.
    
    Features:
    - Maintains conversation context via session_id
    - Automatically selects appropriate tools (list datasets, tables, columns, execute DAX)
    - Caches schema information for performance
    - Returns structured data along with natural language response
    
    Example requests:
    - "Show me all datasets" -> Lists datasets in workspace
    - "What tables are in the Sales dataset?" -> Lists tables
    - "Show me total revenue by region" -> Generates and executes DAX
    """
    try:
        print('here', request.message)
        # Validate access token
        if not request.access_token or not request.access_token.strip():
            logger.error("Chat request received with empty or missing access_token")
            raise HTTPException(
                status_code=400,
                detail="access_token is required and cannot be empty"
            )
        
        client = await get_mcp_client()
        
        # Create chat agent
        agent = ChatAgent(client)
        
        # Convert history to list of dicts
        history = None
        if request.history:
            history = [{"role": h.role, "content": h.content} for h in request.history]
        
        # Process the message
        result = await agent.process_message(
            message=request.message,
            workspace_id=request.workspace_id,
            access_token=request.access_token,
            session_id=request.session_id,
            history=history
        )
        
        # Convert tools_called to ToolCall models
        tools_called = []
        for tc in result.get("tools_called", []):
            tools_called.append(ToolCall(
                tool_name=tc.get("tool_name", ""),
                arguments=tc.get("arguments", {}),
                result_summary=tc.get("result_summary")
            ))
        
        print('tools',tools_called)
        
        return ChatResponse(
            message=result.get("message", ""),
            session_id=result.get("session_id", ""),
            data=result.get("data"),
            dax_query=result.get("dax_query"),
            tools_called=tools_called,
            metadata=result.get("metadata")
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{session_id}")
async def clear_chat_session(session_id: str) -> Dict[str, str]:
    """Clear a chat session and its history"""
    from backend.services.chat_agent import clear_session
    clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get schema cache statistics"""
    return schema_cache.get_cache_stats()


@router.delete("/cache")
async def clear_cache(workspace_id: Optional[str] = None) -> Dict[str, str]:
    """Clear schema cache for a workspace or all workspaces"""
    schema_cache.clear_cache(workspace_id)
    return {"status": "cleared", "workspace_id": workspace_id or "all"}
