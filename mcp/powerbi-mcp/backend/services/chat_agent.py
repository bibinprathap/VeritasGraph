"""
Chat Agent for Power BI conversational interface
Handles conversation, tool selection, and response generation
"""
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
import asyncio
ASYNC_TIMEOUT = 240  # seconds

from backend.llm_provider import llm_provider
from backend.mcp_client import PowerBIMCPClient
# Cache removed - using direct MCP calls
from backend.utils.parser import (
    sanitize_dax,
    fix_unquoted_table_names,
    fix_distinct_in_row,
    enforce_table_quotes,
    repair_averagex_filter,
    validate_aggregatorx_usage,
    fix_bare_scalar_functions
)

logger = logging.getLogger(__name__)


# Conversation sessions storage (in-memory, could be Redis in production)
_sessions: Dict[str, Dict[str, Any]] = {}


INTENT_CLASSIFICATION_PROMPT = """Classify the user's intent based on their message.

USER MESSAGE: {user_message}

Classify into one of these intents:

1. "list_datasets" - User wants to SEE/LIST the DATASETS themselves (the containers/files)
   Examples: 
   - "show me datasets", "list all datasets", "what datasets are there"
   - "show datasets", "datasets available", "what datasets do we have"
   - "list the datasets in this workspace"
   Key indicators: 
   - Asking about DATASETS (the files/containers themselves)
   - NOT asking about data CONTENT within datasets
   - Words like "datasets", "dataset files", "available datasets"

2. "explore_dataset" - User wants to EXPLORE the STRUCTURE/METADATA (tables, columns, schema)
   Examples: 
   - "show tables in X", "what columns in Y", "show schema"
   - "list tables", "what tables are in dataset X", "show me the structure"
   Key indicators: 
   - Asking about STRUCTURE/METADATA (tables, columns)
   - NOT asking about actual DATA VALUES
   - Words like "tables", "columns", "schema", "structure"

3. "data_question" - User asks about ACTUAL DATA VALUES (content, records, information)
   Examples: 
   - "tell me the types of scholarships", "give me the list of scholarships"
   - "show me total sales", "how many records", "what are the values"
   - "list of X", "show me X", "what are the X", "give me X"
   Key indicators: 
   - Asking about DATA CONTENT (scholarships, sales, records, etc.)
   - Asking for a LIST of DATA VALUES (not datasets)
   - Words like "list of [data]", "give me [data]", "show me [data]"
   - Asking "what are the [things]" or "give me [things]"

CRITICAL DISTINCTION:
- "list datasets" → list_datasets (asking about dataset files)
- "list of scholarships" → data_question (asking about scholarship data values)
- "show me datasets" → list_datasets (asking about dataset containers)
- "show me scholarships" → data_question (asking about scholarship data)

When user says "list of X" or "give me X" where X is NOT "datasets", classify as data_question.

Return ONLY a JSON object:
{{
    "intent": "<list_datasets|explore_dataset|data_question>",
    "confidence": "<high|medium|low>",
    "reasoning": "<brief reason>"
}}

NO explanations. NO markdown. ONLY JSON."""


DAX_GENERATION_PROMPT = """You are a Power BI DAX expert. Generate a DAX query to answer the user's question.

AVAILABLE SCHEMA:
{schema}

USER QUESTION:
{question}

=== CRITICAL SYNTAX RULES ===
1. Table names with spaces MUST be in single quotes: 'Table Name'
2. Column references: 'Table Name'[Column Name]
3. Measure references (NO table prefix): [Measure Name]
4. MUST start with EVALUATE
5. Use VAR/RETURN for multi-step calculations

=== SUMMARIZECOLUMNS SYNTAX (VERY IMPORTANT!) ===
SUMMARIZECOLUMNS takes arguments in this EXACT order:
1. Group-by COLUMNS (must be 'Table'[Column], NOT just 'Table')
2. Optional FILTER expressions
3. "Label", Value pairs (label in quotes, then measure or calculation)

CORRECT SYNTAX:
  SUMMARIZECOLUMNS('Table'[Column], "Label", [Measure])
  SUMMARIZECOLUMNS('Table'[Column], FILTER(...), "Label", [Measure])
  SUMMARIZECOLUMNS("Label", [Measure])  -- no grouping, just return value

WRONG (DO NOT DO THIS):
  SUMMARIZECOLUMNS('Table', ...)  -- WRONG: table without column!
  SUMMARIZECOLUMNS('Table1', 'Table2', ...)  -- WRONG: multiple tables!
  SUMMARIZECOLUMNS(..., [Measure])  -- WRONG: missing "Label" before measure!

=== CRITICAL: USE EXISTING MEASURES ===
If the question mentions a specific KPI/metric, USE THE MEASURE DIRECTLY!
DO NOT try to recreate calculations - just reference the measure with [Measure Name].

=== FEW-SHOT EXAMPLES ===

EXAMPLE 1: "What is the Revenue of my latest quarter?"
EVALUATE
VAR MaxYear = MAX('Revenue'[Revenue Reporting Year])
VAR MaxQuarter = CALCULATE(MAX('Revenue'[Revenue Reporting Quarter]), 'Revenue'[Revenue Reporting Year] = MaxYear)
RETURN
SUMMARIZECOLUMNS(
    "Latest Year", IGNORE(MaxYear),
    "Latest Quarter", IGNORE(MaxQuarter),
    "Latest Revenue", CALCULATE(SUM('Revenue'[Revenue]), 'Revenue'[Revenue Reporting Year] = MaxYear, 'Revenue'[Revenue Reporting Quarter] = MaxQuarter)
)

EXAMPLE 2: "Total Seizures This Year"
EVALUATE
ROW(
    "Total Seizures This Year",
    CALCULATE(COUNTROWS('Seizure'), 'Seizure'[Seizure Reporting Year] = YEAR(TODAY()))
)

EXAMPLE 3: "Center with Highest Seizures"
EVALUATE
TOPN(
    1,
    SUMMARIZE('Seizure', 'Seizure'[Center Description En], "Total Seizures", COUNTROWS('Seizure')),
    [Total Seizures], DESC
)

EXAMPLE 4: "Show me how many CSDT cases we have for each category"
EVALUATE
SUMMARIZECOLUMNS(
    'Seizure'[CSDT MAST Type En],
    "Count of CSDT Cases", COUNTROWS('Seizure')
)

EXAMPLE 5: "Count of institutes by gender for this year"
EVALUATE
SUMMARIZECOLUMNS(
    'HE Institutes'[Institute Gender EN],
    FILTER('HE Institutes', 'HE Institutes'[Academic Year] = YEAR(TODAY())),
    "Count of Institute by Gender", DISTINCTCOUNT('HE Institutes'[Institute Name EN])
)

EXAMPLE 6: "Count of institutes by gender for previous year"
EVALUATE
SUMMARIZECOLUMNS(
    'HE Institutes'[Institute Gender EN],
    FILTER('HE Institutes', 'HE Institutes'[Academic Year] = YEAR(TODAY()) - 1),
    "Count of Institute by Gender", DISTINCTCOUNT('HE Institutes'[Institute Name EN])
)

EXAMPLE 7: "Graduated Students working in Federal Government by institute" (USES EXISTING MEASURE)
EVALUATE
SUMMARIZECOLUMNS (
    'GDS LGDS'[INSTITUTE_ID],
    "Total", [Total Number of Graduated Students have been working in Federal Government]
)

EXAMPLE 8: "Graduated Students working in Federal Government THIS YEAR by institute" (USES MEASURE + FILTER)
EVALUATE
SUMMARIZECOLUMNS (
    'GDS LGDS'[INSTITUTE_ID],
    FILTER(
        'GDS LGDS',
        'GDS LGDS'[Report Year] = YEAR(TODAY())
    ),
    "Total", [Total Number of Graduated Students have been working in Federal Government]
)

EXAMPLE 9: "Graduated Students working in Other Sector" (USES EXISTING MEASURE - NO CALCULATION)
EVALUATE
SUMMARIZECOLUMNS (
    "Total",
    [Total Number of Graduated Students have been working in Other Sector]
)

EXAMPLE 10: "List of Internationally Accredited Programs" (USES EXISTING MEASURE)
EVALUATE
SUMMARIZECOLUMNS (
    "Total",
    [List of Internationally Accredited Higher Education Programs]
)

=== COMMON MISTAKES TO AVOID ===

WRONG: SUMMARIZECOLUMNS('GDS LGDS', 'HE Students', ...)
CORRECT: SUMMARIZECOLUMNS('GDS LGDS'[INSTITUTE_ID], ...)
WHY: First arg must be COLUMN, not TABLE!

WRONG: SUMMARIZECOLUMNS('Table'[Col], [Measure])
CORRECT: SUMMARIZECOLUMNS('Table'[Col], "Label", [Measure])
WHY: Measure must have a "Label" before it!

WRONG: SUMMARIZECOLUMNS('GDS LGDS', 'HE Institutes'[Name], FILTER(...), ...)
CORRECT: SUMMARIZECOLUMNS('GDS LGDS'[INSTITUTE_ID], FILTER(...), "Total", [Measure])
WHY: Don't mix tables! Use column from ONE table for grouping.

=== PATTERN RULES ===
- IF schema has a MEASURE that matches the question → USE IT DIRECTLY with [Measure Name]
- "by institute/category/type" → SUMMARIZECOLUMNS('Table'[GroupColumn], "Label", [Measure])
- "this year" → add FILTER('Table', 'Table'[Year] = YEAR(TODAY()))
- "previous/last year" → YEAR(TODAY()) - 1
- "highest/top" → TOPN(N, ..., [col], DESC)
- "lowest/bottom" → TOPN(N, ..., [col], ASC)
- Single value result → SUMMARIZECOLUMNS("Label", [Measure]) or ROW("Label", value)
- Table/list result → NO ROW()

Return ONLY valid JSON:
{{
    "dax": "EVALUATE ...",
    "explanation": "Brief explanation"
}}

NO markdown. NO extra text."""
# DAX_GENERATION_PROMPT = """
# You are a Power BI DAX expert. Generate a DAX query answering the user question.

# SCHEMA:
# {schema}

# QUESTION:
# {question}

# === CORE RULES ===
# - MUST start with EVALUATE
# - Use VAR / RETURN for multi-step logic
# - Table with spaces → 'Table Name'
# - Column → 'Table'[Column]
# - Measure → [Measure] (NO table prefix)

# === SUMMARIZECOLUMNS (STRICT ORDER) ===
# 1. Group-by COLUMNS only ('Table'[Column])
# 2. Optional FILTER()
# 3. "Label", Expression pairs

# VALID:
# SUMMARIZECOLUMNS('T'[Col], "Label", [Measure])
# SUMMARIZECOLUMNS('T'[Col], FILTER(...), "Label", [Measure])
# SUMMARIZECOLUMNS("Label", [Measure])

# INVALID:
# SUMMARIZECOLUMNS('Table', ...)
# SUMMARIZECOLUMNS('T1', 'T2', ...)
# SUMMARIZECOLUMNS('T'[Col], [Measure])

# === MEASURE RULE (CRITICAL) ===
# If a KPI/metric exists in schema → USE THE MEASURE DIRECTLY.
# DO NOT recreate calculations.

# === COMMON PATTERNS ===
# - "by X" → SUMMARIZECOLUMNS('Table'[X], "Label", [Measure])
# - "this year" → FILTER('Table', 'Table'[Year] = YEAR(TODAY()))
# - "last/previous year" → YEAR(TODAY()) - 1
# - "top/highest" → TOPN(N, ..., [Value], DESC)
# - "bottom/lowest" → TOPN(N, ..., [Value], ASC)
# - Single value → SUMMARIZECOLUMNS("Label", [Measure]) or ROW()
# - Table result → NO ROW()

# === ERROR PREVENTION ===
# - First SUMMARIZECOLUMNS arg MUST be a column, not a table
# - Every measure MUST have a preceding "Label"
# - Grouping columns must come from ONE table

# === OUTPUT FORMAT (JSON ONLY) ===
# {{
#   "dax": "EVALUATE ...",
#   "explanation": "Brief explanation"
# }}

# NO markdown. NO extra text.
# """

### ROLE
### OUTPUT FORMAT
# DAX_GENERATION_PROMPT ="""
# ### ROLE
# Senior Power BI DAX Expert. 

# ### CONSTRAINTS
# - Return ONLY JSON.
# - Every query MUST start with EVALUATE.
# - Columns MUST be aggregated: Use SUM('Table'[Col]), not 'Table'[Col].
# - Variables (VAR) must be at the top level, never inside functions.

# ### DAX TEMPLATE FOR LATEST DATA
# EVALUATE
# VAR _MaxYear = MAX('Table'[YearColumn])
# VAR _MaxPeriod = CALCULATE(MAX('Table'[PeriodColumn]), 'Table'[YearColumn] = _MaxYear)
# RETURN
# SUMMARIZECOLUMNS(
#     "Label", 
#     CALCULATE(SUM('Table'[ValueColumn]), 'Table'[YearColumn] = _MaxYear, 'Table'[PeriodColumn] = _MaxPeriod)
# )

# ### SCHEMA
# {schema}

# ### USER QUESTION
# {question}

# ### OUTPUT
# {{
#     "dax": "...",
#     "explanation": "..."
# }}
# """



DAX_CORRECTION_PROMPT = """You are a DAX expert. The following DAX query failed. Fix it.

ORIGINAL QUESTION: {question}

SCHEMA:
{schema}

FAILED DAX:
{failed_dax}

ERROR MESSAGE:
{error}

COMMON ISSUES TO CHECK:
1. Table names with spaces must be in single quotes: 'Table Name'
2. Column references: 'Table Name'[Column Name]
3. Scalar functions (COUNT, SUM) need ROW() wrapper when used alone
4. DISTINCT returns a table, cannot be inside ROW()
5. Check column/table names match the schema exactly
6. SUMMARIZECOLUMNS syntax: group columns first, then "Name", expression pairs

Return ONLY valid JSON with the corrected DAX:
{{
    "dax": "EVALUATE ...",
    "explanation": "What was fixed"
}}

NO markdown. NO extra text."""


DATASET_SELECTION_PROMPT = """Select the most relevant dataset for the user's question.

USER QUESTION: {question}

AVAILABLE DATASETS:
{datasets_info}

Analyze the user's question and select the ONE dataset that most likely contains the relevant data.

Return ONLY a JSON object:
{{
    "dataset_id": "<selected dataset ID>",
    "dataset_name": "<selected dataset name>",
    "reasoning": "<brief reason why this dataset was selected>"
}}

NO explanations. NO markdown. ONLY JSON."""


TABLE_SELECTION_PROMPT = """Select the relevant tables for the user's question.

USER QUESTION: {question}

AVAILABLE TABLES:
{tables_info}

Select ONLY the tables that are likely needed to answer this question.
Usually 1-3 tables are enough. Don't select all tables.

Return ONLY a JSON object:
{{
    "tables": ["table1", "table2"],
    "reasoning": "<brief reason>"
}}

NO markdown. ONLY JSON."""


SUMMARIZE_RESULTS_PROMPT = """Summarize the following DAX query results in a friendly, conversational way.

USER QUESTION: {question}

DAX QUERY: {dax_query}

RESULTS:
{results}

Provide a clear, concise summary of what the data shows. If there are many results, highlight key findings.
Keep the response friendly and helpful."""


async def _fetch_dataset_schema(
    mcp_client: PowerBIMCPClient,
    workspace_id: str,
    dataset_id: str,
    dataset_name: str,
    access_token: str
) -> Dict[str, Any]:
    """
    Fetch dataset schema directly from MCP (no caching).
    Uses list_tables() only (columns included via COLUMNSTATISTICS()).
    Returns:
    {
      "dataset_name": str,
      "tables": {
          table_name: [columns]
      }
    }
    """

    tables_list = await mcp_client.list_tables(
        workspace_id,
        dataset_id,
        access_token=access_token
    )

    # logger.info(
    #     "Fetched tables | type=%s | count=%s",
    #     type(tables_list),
    #     len(tables_list) if isinstance(tables_list, list) else "N/A"
    # )

    schema = {
        "dataset_name": dataset_name,
        "tables": {}
    }

    if not isinstance(tables_list, list):
        logger.error("Unexpected list_tables response: %s", tables_list)
        return schema

    for table in tables_list:
        if not isinstance(table, dict):
            logger.warning("Skipping invalid table entry: %s", table)
            continue

        table_name = table.get("name")
        columns = table.get("columns", [])

        if not table_name:
            logger.warning("Table without name: %s", table)
            continue

        if not isinstance(columns, list):
            logger.warning(
                "Invalid columns for table %s: %s",
                table_name,
                columns
            )
            columns = []

        schema["tables"][table_name] = columns
        
        # print('return schema -->',schema)

    return schema



class ChatAgent:
    """
    Conversational agent for Power BI data exploration and querying
    """
    
    def __init__(self, mcp_client: PowerBIMCPClient):
        self.mcp_client = mcp_client
        self.llm = llm_provider.get_llm()
    
    async def process_message(
        self,
        message: str,
        workspace_id: str,
        access_token: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return a response
        """
        # ============================================
        # STEP 0: VALIDATE ACCESS TOKEN BEFORE ANYTHING
        # ============================================
        if not access_token or not access_token.strip():
            logger.error(f"Empty or missing access token provided. Token length: {len(access_token) if access_token else 0}")
            return {
                "message": "⚠️ **Access token is required** but was not provided or is empty.\n\nPlease provide a valid Power BI access token to query data.",
                "session_id": session_id or str(uuid.uuid4()),
                "data": None,
                "dax_query": None,
                "tools_called": [],
                "metadata": {"error": "missing_access_token"}
            }
        
        # Basic token format validation
        token_stripped = access_token.strip()
        if len(token_stripped) < 100:  # Bearer tokens are typically 1000+ chars
            logger.warning(f"Access token seems too short ({len(token_stripped)} chars). May be invalid.")
        
        # Check if token looks like a Bearer token (starts with "ey" for JWT)
        if not token_stripped.startswith("ey"):
            logger.warning(f"Access token doesn't look like a JWT (doesn't start with 'ey'). Token prefix: {token_stripped[:10]}...")
        
        logger.info(f"Processing message with access token (length: {len(token_stripped)}, prefix: {token_stripped[:10]}...)")
        
        # Initialize or get session
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if session_id not in _sessions:
            _sessions[session_id] = {
                "history": [],
                "workspace_id": workspace_id,
                "current_dataset_id": None,
                "schemas_loaded": False,
                "access_token": access_token
            }
        
        session = _sessions[session_id]
        session["access_token"] = access_token  # Update token in case it changed
        
        # Add provided history if any
        if history:
            session["history"] = [
                {"role": h.get("role"), "content": h.get("content")}
                for h in history
            ]
        
        # Set access token in MCP client
        await self.mcp_client.set_access_token(access_token)
        
        tools_called = []
        
        # Step 1: Get workspace datasets directly (no cache)
        try:
            datasets = await self.mcp_client.list_datasets(workspace_id, access_token=access_token)
            logger.info(f"dataset ---> ",datasets)
            
            # Check if we got an error response instead of datasets
            if isinstance(datasets, str):
                datasets_str = datasets.lower()
                if "401" in datasets or "unauthorized" in datasets_str or "expired" in datasets_str:
                    logger.error(f"Token expired during dataset listing: {datasets}")
                    return {
                        "message": "🔐 **Authentication Error**\n\nYour access token appears to be **expired or invalid**.\n\n**Please:**\n1. Generate a new Power BI access token\n2. Update the token in your request\n3. Try your query again\n\n*Access tokens typically expire after 1 hour.*",
                        "session_id": session_id,
                        "data": None,
                        "dax_query": None,
                        "tools_called": [],
                        "metadata": {"error": "token_expired"}
                    }
                datasets = []  # Treat string response as empty
            
            # Ensure datasets is a list
            if not isinstance(datasets, list):
                datasets = []
                
        except Exception as e:
            error_str = str(e).lower()
            # Check if it's an auth error
            if "401" in str(e) or "unauthorized" in error_str or "expired" in error_str or "authentication" in error_str:
                logger.error(f"Token expired during dataset listing: {e}")
                return {
                    "message": "🔐 **Authentication Error**\n\nYour access token appears to be **expired or invalid**.\n\n**Please:**\n1. Generate a new Power BI access token\n2. Update the token in your request\n3. Try your query again\n\n*Access tokens typically expire after 1 hour.*",
                    "session_id": session_id,
                    "data": None,
                    "dax_query": None,
                    "tools_called": [],
                    "metadata": {"error": "token_expired"}
                }
            # Re-raise other errors
            raise
        
        tools_called.append({
            "tool_name": "list_datasets",
            "arguments": {"workspace_id": workspace_id},
            "result_summary": f"Found {len(datasets)} datasets"
        })
        
        # Step 2: Classify user intent
        intent_result = await self._classify_intent(message, datasets)
        intent = intent_result.get("intent", "general")
        mentioned_dataset = intent_result.get("dataset_name")
        mentioned_table = intent_result.get("table_name")
        
        logger.info(f"Classified intent: {intent}, dataset: {mentioned_dataset}, table: {mentioned_table}")
        
        # Step 3: Execute based on intent
        result = None
        
        if intent == "list_datasets":
            result = await self._handle_list_datasets(workspace_id, datasets, tools_called)
        
        elif intent == "explore_dataset":
            result = await self._handle_explore_dataset(
                workspace_id, datasets, mentioned_dataset, mentioned_table, session, tools_called
            )
        
        elif intent == "data_question":
            # For data questions, we need to:
            # 1. Load all schemas if not already loaded
            # 2. Find the relevant dataset/table
            # 3. Generate and execute DAX
            result = await self._handle_data_question(
                message, workspace_id, datasets, mentioned_dataset, session, tools_called
            )
        
        else:
            # General or unclear - try to be helpful
            result = {
                "message": self._generate_help_message(datasets),
                "data": None,
                "dax_query": None
            }
        
        # Update session history
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": result.get("message", "")})
        
        # Keep history manageable
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]
        
        result["session_id"] = session_id
        result["tools_called"] = tools_called
        result["metadata"] = {
            "workspace_id": workspace_id,
            "dataset_id": session.get("current_dataset_id"),
            "intent": intent
        }
        
        return result
    
    async def _classify_intent(self, message: str, datasets: List[Dict]) -> Dict[str, Any]:
        """Classify user intent using rule-based approach for reliability"""
        message_lower = message.lower().strip()
        
        # ========================================
        # RULE 1: Check if message is about DATASETS (the word dataset/datasets appears)
        # If so, classify based on what they're asking about datasets
        # ========================================
        if "dataset" in message_lower:
            # User is asking about datasets - check what kind of request
            # If asking to list/show datasets → list_datasets
            list_action_words = ["list", "show", "what", "which", "see", "get", "give", "all", "available"]
            if any(word in message_lower for word in list_action_words):
                logger.info(f"Rule-based: Classifying as list_datasets (contains 'dataset' + list action): {message}")
                return {"intent": "list_datasets", "confidence": "high", "reasoning": "dataset_with_list_action"}
        
        # ========================================
        # RULE 2: Check for EXPLORE DATASET indicators
        # User asks about tables, columns, schema
        # ========================================
        explore_patterns = [
            "show table", "list table", "what table", "tables in", "tables are",
            "show column", "list column", "what column", "columns in",
            "schema", "structure", "metadata", "explore"
        ]
        
        if any(pattern in message_lower for pattern in explore_patterns):
            logger.info(f"Rule-based: Classifying as explore_dataset: {message}")
            return {"intent": "explore_dataset", "confidence": "high", "reasoning": "explore_patterns"}
        
        # ========================================
        # RULE 3: Everything else is a DATA QUESTION
        # User is asking about actual data values
        # ========================================
        logger.info(f"Rule-based: Classifying as data_question: {message}")
        return {"intent": "data_question", "confidence": "high", "reasoning": "default_data_question"}
    
    async def _handle_list_datasets(
        self, workspace_id: str, datasets: List[Dict], tools_called: List
    ) -> Dict[str, Any]:
        """Handle request to list datasets"""
        if not datasets:
            return {
                "message": "I didn't find any datasets in this workspace.",
                "data": [],
                "dax_query": None
            }
        
        lines = [f"📊 **Found {len(datasets)} datasets in this workspace:**\n"]
        for i, ds in enumerate(datasets, 1):
            lines.append(f"{i}. **{ds.get('name', 'Unknown')}**")
            lines.append(f"   ID: `{ds.get('id', 'Unknown')}`")
        lines.append("\n💡 Ask me about any dataset to explore its tables and columns!")
        
        return {
            "message": "\n".join(lines),
            "data": datasets,
            "dax_query": None
        }
    
    async def _handle_explore_dataset(
        self,
        workspace_id: str,
        datasets: List[Dict],
        mentioned_dataset: Optional[str],
        mentioned_table: Optional[str],
        session: Dict,
        tools_called: List
    ) -> Dict[str, Any]:
        """Handle request to explore a dataset's structure"""
        # Find the dataset
        dataset = self._find_dataset(datasets, mentioned_dataset)
        
        if not dataset:
            # Use first dataset if none specified
            if datasets:
                dataset = datasets[0]
            else:
                return {
                    "message": "No datasets found in this workspace.",
                    "data": None,
                    "dax_query": None
                }
        
        dataset_id = dataset.get("id")
        dataset_name = dataset.get("name", dataset_id)
        session["current_dataset_id"] = dataset_id
        
        # Get schema directly (no cache)
        access_token = session.get("access_token")
        schema = await _fetch_dataset_schema(
            self.mcp_client, workspace_id, dataset_id, dataset_name, access_token=access_token
        )
        
        tools_called.append({
            "tool_name": "list_tables",
            "arguments": {"dataset_id": dataset_id},
            "result_summary": f"Found {len(schema['tables'])} tables"
        })
        
        # Format response
        lines = [f"📁 **Dataset: {dataset_name}**\n"]
        lines.append(f"Found **{len(schema['tables'])} tables**:\n")
        
        for table_name, columns in schema['tables'].items():
            lines.append(f"### 📋 {table_name}")
            col_names = [c.get("name", "?") for c in columns[:10]]
            lines.append(f"   Columns: {', '.join(col_names)}")
            if len(columns) > 10:
                lines.append(f"   ... and {len(columns) - 10} more columns")
            lines.append("")
        
        lines.append("\n💡 Now you can ask questions about this data!")
        
        data = [
            {"name": t, "columns": [c.get("name") for c in cols]}
            for t, cols in schema['tables'].items()
        ]
        
        return {
            "message": "\n".join(lines),
            "data": data,
            "dax_query": None
        }
    
    async def _handle_data_question(
        self,
        message: str,
        workspace_id: str,
        datasets: List[Dict],
        mentioned_dataset: Optional[str],
        session: Dict,
        tools_called: List
    ) -> Dict[str, Any]:
        """Handle a data question by selecting the correct dataset, then exploring its schema"""

        if not datasets:
            return {
                "message": "I couldn't find any datasets to query. Please check the workspace has datasets.",
                "data": None,
                "dax_query": None
            }

        try:
            # ------------------ Step 1: Dataset selection ------------------
            logger.info(f"Selecting relevant dataset from {len(datasets)} datasets")
            try:
                selected_dataset = await asyncio.wait_for(
                    self._select_dataset(message, datasets),
                    timeout=ASYNC_TIMEOUT
                )
            except Exception as e:
                logger.warning(f"Dataset selection failed: {e}")
                selected_dataset = None

            if not selected_dataset:
                selected_dataset = datasets[0]
                logger.warning("Fallback to first dataset")

            dataset_id = selected_dataset.get("id")
            dataset_name = selected_dataset.get("name", dataset_id)
            session["current_dataset_id"] = dataset_id

            access_token = session.get("access_token")

            # ------------------ Step 2: Schema fetch ------------------
            logger.info(f"Fetching schema for dataset: {dataset_name}")
            schema = await asyncio.wait_for(
                _fetch_dataset_schema(
                    self.mcp_client,
                    workspace_id,
                    dataset_id,
                    dataset_name,
                    access_token=access_token
                ),
                timeout=ASYNC_TIMEOUT
            )

            tools_called.append({
                "tool_name": "list_tables",
                "arguments": {"workspace_id": workspace_id, "dataset_id": dataset_id},
                "result_summary": f"Explored '{dataset_name}': {len(schema.get('tables', {}))} tables"
            })

            # ------------------ Step 3: Relevant tables ------------------
            relevant_tables = await asyncio.wait_for(
                self._select_relevant_tables(message, schema),
                timeout=ASYNC_TIMEOUT
            )
            
            print(relevant_tables,"relevant table --->")
              
            schema_text = self._format_schema_for_prompt(schema, relevant_tables)

            print(schema_text,"schema--->")
            
            # ------------------ Step 4: DAX generation ------------------
            dax_result = await asyncio.wait_for(
                self._generate_dax(message, schema_text),
                timeout=ASYNC_TIMEOUT
            )
            
            print(dax_result,'dax result -->')

            if not dax_result or not dax_result.get("dax"):
                tables = ", ".join(schema.get("tables", {}).keys())
                return {
                    "message": (
                        f"I explored the dataset **{dataset_name}** but couldn't generate a query.\n\n"
                        f"**Available tables:** {tables}\n\n"
                        "Could you rephrase your question or specify the table/column?"
                    ),
                    "data": None,
                    "dax_query": None
                }

            base_dax = self._apply_dax_guardrails(dax_result["dax"])

            # ------------------ Step 5: Pre-validation ------------------
            validation_errors = self._validate_dax_syntax(base_dax, schema)
            if validation_errors:
                correction = await asyncio.wait_for(
                    self._correct_dax(
                        message,
                        schema_text,
                        base_dax,
                        "; ".join(validation_errors)
                    ),
                    timeout=ASYNC_TIMEOUT
                )
                if correction and correction.get("dax"):
                    base_dax = self._apply_dax_guardrails(correction["dax"])

            # ------------------ Step 6: Execution with retries ------------------
            MAX_RETRIES = 3
            attempts_info = []

            for attempt in range(MAX_RETRIES):
                dax_query = base_dax  # keep attempts deterministic

                tools_called.append({
                    "tool_name": "execute_dax",
                    "arguments": {
                        "dataset": dataset_name,
                        "attempt": attempt + 1,
                        "dax_query": dax_query[:80] + "..."
                    },
                    "result_summary": f"Executing (attempt {attempt + 1}/{MAX_RETRIES})"
                })

                try:
                    result = await asyncio.wait_for(
                        self.mcp_client.execute_dax(
                            workspace_id,
                            dataset_id,
                            dax_query,
                            access_token=access_token
                        ),
                        timeout=ASYNC_TIMEOUT
                    )

                    result_str = str(result).lower()

                    # ---------- Auth errors (no retry) ----------
                    if any(k in result_str for k in [
                        "401", "unauthorized", "token expired",
                        "invalid token", "access denied"
                    ]):
                        return {
                            "message": (
                                "🔐 **Authentication Error**\n\n"
                                "Your access token has expired or is invalid.\n\n"
                                "Please regenerate the token and try again."
                            ),
                            "data": None,
                            "dax_query": dax_query,
                            "metadata": {"error": "token_expired"}
                        }

                    # ---------- Parse result ----------
                    data, is_empty, has_nulls = self._parse_dax_result(result)

                    if is_empty:
                        return {
                            "message": "Query executed successfully but returned no results.",
                            "data": [],
                            "dax_query": dax_query
                        }

                    if has_nulls and data:
                        return {
                            "message": "Query executed successfully but returned null values.",
                            "data": data,
                            "dax_query": dax_query
                        }

                    summary = await asyncio.wait_for(
                        self._summarize_results(message, dax_query, data),
                        timeout=ASYNC_TIMEOUT
                    )

                    return {
                        "message": summary,
                        "data": data,
                        "dax_query": dax_query
                    }

                except Exception as e:
                    error_msg = str(e)
                    attempts_info.append({
                        "attempt": attempt + 1,
                        "dax": dax_query,
                        "error": error_msg
                    })
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

                    if attempt < MAX_RETRIES - 1:
                        correction = await asyncio.wait_for(
                            self._correct_dax(message, schema_text, dax_query, error_msg),
                            timeout=ASYNC_TIMEOUT
                        )
                        if correction and correction.get("dax"):
                            base_dax = self._apply_dax_guardrails(correction["dax"])
                        else:
                            break

            # ------------------ Final failure ------------------
            return {
                "message": (
                    f"I tried {len(attempts_info)} times but couldn't execute the query.\n\n"
                    + "\n".join(
                        f"- Attempt {a['attempt']}: {a['error'][:100]}"
                        for a in attempts_info
                    )
                ),
                "data": None,
                "dax_query": base_dax
            }

        except Exception as fatal:
            logger.exception("Fatal error in _handle_data_question")
            return {
                "message": "An unexpected error occurred while processing your request.",
                "data": None,
                "dax_query": None
            }
        
    async def _select_dataset(self, message: str, datasets: List[Dict]) -> Optional[Dict]:
            """Select the most relevant dataset based on user query using LLM"""
            if len(datasets) == 1:
                return datasets[0]
            
            # Format datasets info
            datasets_info = "\n".join([
                f"- {d.get('name', 'Unknown')} (ID: {d.get('id', 'Unknown')})"
                for d in datasets
            ])
            
            prompt = DATASET_SELECTION_PROMPT.format(
                question=message,
                datasets_info=datasets_info
            )
            
            try:
                response = await self.llm.ainvoke(prompt)
                raw = response.content if hasattr(response, "content") else str(response)
                logger.debug(f"Dataset selection raw output: {raw[:500]}")
                
                # Parse JSON
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    result = json.loads(raw[start:end])
                    selected_id = result.get("dataset_id")
                    selected_name = result.get("dataset_name")
                    reasoning = result.get("reasoning", "")
                    
                    logger.info(f"LLM selected dataset: {selected_name} (Reason: {reasoning})")
                    
                    # Find the dataset
                    dataset = next(
                        (d for d in datasets if d.get("id") == selected_id or d.get("name") == selected_name),
                        None
                    )
                    
                    if dataset:
                        return dataset
            except Exception as e:
                logger.warning(f"Dataset selection failed: {e}")
            
            # Fallback: simple keyword matching
            message_lower = message.lower()
            for dataset in datasets:
                dataset_name = dataset.get("name", "").lower()
                # Check if dataset name keywords appear in the message
                if any(word in message_lower for word in dataset_name.split() if len(word) > 3):
                    logger.info(f"Fallback: Selected dataset by keyword match: {dataset.get('name')}")
                    return dataset
            
            return None
        
    def _find_dataset(self, datasets: List[Dict], name: Optional[str]) -> Optional[Dict]:
            """Find a dataset by name (fuzzy match)"""
            if not name:
                return None
            
            name_lower = name.lower()
            
            # Exact match
            for ds in datasets:
                if ds.get("name", "").lower() == name_lower:
                    return ds
            
            # Partial match
            for ds in datasets:
                if name_lower in ds.get("name", "").lower():
                    return ds
            
            return None
        
    async def _select_relevant_tables(self, question: str, schema: Dict[str, Any]) -> List[str]:
            """
            Select relevant tables based on user question.
            Uses keyword matching first, then LLM if needed.
            Returns list of relevant table names.
            """
            all_tables = list(schema['tables'].keys())
            
            # If only 1-3 tables, use all of them
            if len(all_tables) <= 3:
                logger.info(f"Using all {len(all_tables)} tables (small schema)")
                return all_tables
            
            # Step 1: Try keyword matching first (fast, no LLM call)
            question_lower = question.lower()
            matched_tables = []
            
            for table_name in all_tables:
                table_lower = table_name.lower()
                # Check if table name or its words appear in the question
                table_words = table_lower.replace("_", " ").split()
                for word in table_words:
                    if len(word) > 3 and word in question_lower:
                        matched_tables.append(table_name)
                        break
                # Also check columns for keyword matches
                columns = schema['tables'].get(table_name, [])
                for col in columns:
                    col_name = col.get("name", "").lower()
                    col_words = col_name.replace("_", " ").split()
                    for word in col_words:
                        if len(word) > 3 and word in question_lower:
                            if table_name not in matched_tables:
                                matched_tables.append(table_name)
                            break
            
            # If keyword matching found 1-5 tables, use those
            if 1 <= len(matched_tables) <= 5:
                logger.info(f"Keyword matching found {len(matched_tables)} relevant tables: {matched_tables}")
                return matched_tables
            
            # Step 2: Use LLM to select tables (more accurate but slower)
            tables_info = "\n".join([
                f"- '{t}': {', '.join([c.get('name', '') for c in schema['tables'].get(t, [])[:10]])}"
                for t in all_tables
            ])
            
            prompt = TABLE_SELECTION_PROMPT.format(
                question=question,
                tables_info=tables_info
            )
            
            try:
                response = await self.llm.ainvoke(prompt)
                raw = response.content if hasattr(response, "content") else str(response)
                
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    result = json.loads(raw[start:end])
                    selected = result.get("tables", [])
                    
                    # Validate selected tables exist
                    valid_tables = [t for t in selected if t in all_tables]
                    if valid_tables:
                        logger.info(f"LLM selected {len(valid_tables)} tables: {valid_tables}")
                        return valid_tables
            except Exception as e:
                logger.warning(f"Table selection LLM failed: {e}")
            
            # Fallback: return first 5 tables or all if less
            fallback = all_tables[:5]
            logger.info(f"Fallback: using first {len(fallback)} tables")
            return fallback
        
    def _format_schema_for_prompt(
        self,
        schema: Dict[str, Any],
        relevant_tables: Optional[List[str]] = None
    ) -> str:
        """
        Format schema as text for LLM prompts.
        Includes column metadata (cardinality, min, max) when available.
        """

        lines = [f"Dataset: {schema.get('dataset_name', 'Unknown')}\n"]
        lines.append("Tables and Columns:")

        tables = schema.get("tables", {})
        tables_to_include = relevant_tables if relevant_tables else list(tables.keys())

        for table_name in tables_to_include:
            if table_name not in tables:
                continue

            columns = tables.get(table_name, [])
            if not columns:
                continue

            lines.append(f"\nTable: '{table_name}'")

            for col in columns:
                col_name = col.get("name", "Unknown")
                line = f"  - {col_name}"

                cardinality = col.get("cardinality")
                min_val = col.get("min")
                max_val = col.get("max")

                # Cardinality hint
                if cardinality is not None:
                    if cardinality <= 20:
                        line += " (Low cardinality)"
                    else:
                        line += f" (Cardinality: {cardinality})"

                # Range hint (dates or numeric)
                if min_val is not None or max_val is not None:
                    line += " (Range:"
                    if min_val is not None:
                        line += f" {min_val}"
                    line += " →"
                    if max_val is not None:
                        line += f" {max_val}"
                    line += ")"

                lines.append(line)

        if relevant_tables and len(relevant_tables) < len(tables):
            lines.append(
                f"\n(Showing {len(relevant_tables)} of {len(tables)} tables relevant to your question)"
            )

        return "\n".join(lines)


            
    async def _generate_dax(self, question: str, schema: str) -> Optional[Dict[str, str]]:
                """Generate DAX query using LLM"""
                prompt = DAX_GENERATION_PROMPT.format(
                    schema=schema,
                    question=question
                )
                
                try:
                    response = await self.llm.ainvoke(prompt)
                    raw = response.content if hasattr(response, "content") else str(response)
                    logger.debug(f"DAX generation raw output: {raw[:500]}")
                    print(response, "response Generated DAX-->")
                    
                    # Method 1: Try to parse as JSON first
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    if start >= 0 and end > start:
                        try:
                            result = json.loads(raw[start:end])
                            if result.get("dax"):
                                logger.info(f"Parsed DAX from JSON: {result['dax'][:100]}...")
                                return result
                        except json.JSONDecodeError:
                            logger.debug("JSON parsing failed, trying code block extraction")
                    
                    # Method 2: Extract DAX from markdown code blocks
                    # Try ```dax ... ``` first
                    dax_block_match = re.search(r'```(?:dax)?\s*\n?(EVALUATE[\s\S]*?)```', raw, re.IGNORECASE)
                    if dax_block_match:
                        dax_query = dax_block_match.group(1).strip()
                        logger.info(f"Extracted DAX from code block: {dax_query[:100]}...")
                        return {"dax": dax_query, "explanation": "Extracted from code block"}
                    
                    # Method 3: Look for EVALUATE directly in the text
                    evaluate_match = re.search(r'(EVALUATE\s+[\s\S]+?)(?:\n\n|$|```)', raw, re.IGNORECASE)
                    if evaluate_match:
                        dax_query = evaluate_match.group(1).strip()
                        # Clean up any trailing explanation text
                        if '\n\nExplanation' in dax_query:
                            dax_query = dax_query.split('\n\nExplanation')[0].strip()
                        if '\n\nThis' in dax_query:
                            dax_query = dax_query.split('\n\nThis')[0].strip()
                        logger.info(f"Extracted DAX from text: {dax_query[:100]}...")
                        return {"dax": dax_query, "explanation": "Extracted from response text"}
                    
                    logger.warning(f"Could not extract DAX from LLM response: {raw[:300]}")
                    
                except Exception as e:
                    print(e, "DAX generation error")
                    logger.error(f"DAX generation failed: {e}")
                
                return None
          
            
    def _apply_dax_guardrails(self, dax: str) -> str:
                """Apply DAX guardrails to fix common issues"""
                dax = sanitize_dax(dax)
                dax = fix_unquoted_table_names(dax)
                dax = fix_distinct_in_row(dax)
                dax = fix_bare_scalar_functions(dax)  # Fix EVALUATE COUNT() → EVALUATE ROW("Count", COUNT())
                dax = repair_averagex_filter(dax)
                
                # Ensure starts with EVALUATE
                if not dax.strip().upper().startswith("EVALUATE"):
                    dax = "EVALUATE " + dax
                
                return dax
            
    def _validate_dax_syntax(self, dax: str, schema: Optional[Dict[str, Any]] = None) -> List[str]:
                """
                Validate DAX syntax before execution.
                Returns list of validation errors (empty if valid).
                """
                errors = []
                dax_upper = dax.upper()
                
                # Rule 1: Must start with EVALUATE
                if not dax.strip().upper().startswith("EVALUATE"):
                    errors.append("DAX must start with EVALUATE")
                
                # Rule 2: Check for unquoted table names with spaces
                # Pattern: word space word [ (without surrounding quotes)
                unquoted_pattern = r"(?<!')\b([A-Za-z]+\s+[A-Za-z]+)\["
                matches = re.findall(unquoted_pattern, dax)
                for match in matches:
                    if match not in ["ORDER BY", "GROUP BY"]:  # Exclude SQL keywords
                        errors.append(f"Table name '{match}' should be quoted: '{match}'")
                
                # Rule 3: Check for scalar functions directly under EVALUATE
                scalar_funcs = ["COUNT(", "SUM(", "AVERAGE(", "MIN(", "MAX(", "COUNTROWS("]
                content_after_evaluate = dax_upper[len("EVALUATE"):].strip() if dax_upper.startswith("EVALUATE") else ""
                for func in scalar_funcs:
                    if content_after_evaluate.startswith(func):
                        if not content_after_evaluate.startswith("ROW("):
                            errors.append(f"Scalar function {func[:-1]} directly under EVALUATE should be wrapped in ROW()")
                
                # Rule 4: Check DISTINCT inside ROW (invalid)
                if "ROW(" in dax_upper and "DISTINCT(" in dax_upper:
                    # More specific check - is DISTINCT directly inside ROW?
                    row_distinct_pattern = r"ROW\s*\([^)]*DISTINCT\s*\("
                    if re.search(row_distinct_pattern, dax_upper):
                        errors.append("DISTINCT() cannot be inside ROW() - DISTINCT returns a table, not scalar")
                
                # Rule 5: Check referenced tables exist in schema
                if schema and schema.get('tables'):
                    schema_tables = set(t.lower() for t in schema['tables'].keys())
                    # Find table references in DAX: 'TableName' or TableName[Column]
                    table_refs = re.findall(r"'([^']+)'\[|(?<!')(\b[A-Za-z_][A-Za-z0-9_]*)\[", dax)
                    for match in table_refs:
                        table_name = match[0] or match[1]
                        if table_name.lower() not in schema_tables:
                            errors.append(f"Table '{table_name}' not found in schema. Available: {list(schema['tables'].keys())}")
                
                return errors
            
    async def _correct_dax(self, question: str, schema_text: str, failed_dax: str, error: str) -> Optional[Dict[str, str]]:
                """
                Use LLM to correct a failed DAX query.
                """
                prompt = DAX_CORRECTION_PROMPT.format(
                    question=question,
                    schema=schema_text,
                    failed_dax=failed_dax,
                    error=error
                )
                
                try:
                    response = await self.llm.ainvoke(prompt)
                    raw = response.content if hasattr(response, "content") else str(response)
                    logger.info(f"DAX correction response: {raw[:500]}")
                    
                    # Parse JSON
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    if start >= 0 and end > start:
                        result = json.loads(raw[start:end])
                        return result
                except Exception as e:
                    logger.error(f"DAX correction failed: {e}")
                
                return None
            
    def _parse_dax_result(self, result: Any) -> Tuple[Any, bool, bool]:
                """
                Parse DAX result from MCP response.
                Returns: (data, is_empty, has_null_values)
                - data: parsed result data
                - is_empty: True if result has no rows
                - has_null_values: True if result contains null values
                """
                is_empty = False
                has_null_values = False
                data = None
                
                if isinstance(result, dict):
                    if "result" in result:
                        result_text = result["result"]
                        # Try to parse JSON from result
                        if isinstance(result_text, str):
                            try:
                                # Look for Power BI response format: { "results": [ { "tables": [ { "rows": [...] } ] } ] }
                                parsed = None
                                start = result_text.find("{")
                                end = result_text.rfind("}") + 1
                                if start >= 0 and end > start:
                                    parsed = json.loads(result_text[start:end])
                                
                                if parsed and "results" in parsed:
                                    # Power BI format
                                    tables = parsed.get("results", [{}])[0].get("tables", [])
                                    if tables:
                                        rows = tables[0].get("rows", [])
                                        data = rows
                                        
                                        # Check if empty
                                        if len(rows) == 0:
                                            is_empty = True
                                            logger.info("DAX returned empty result (0 rows)")
                                        
                                        # Check for null values
                                        elif rows:
                                            for row in rows:
                                                for key, value in row.items():
                                                    if value is None:
                                                        has_null_values = True
                                                        break
                                                if has_null_values:
                                                    break
                                            if has_null_values:
                                                logger.info(f"DAX returned null values: {rows}")
                                    else:
                                        is_empty = True
                                        data = []
                                else:
                                    # Try array format
                                    start = result_text.find("[")
                                    end = result_text.rfind("]") + 1
                                    if start >= 0 and end > start:
                                        data = json.loads(result_text[start:end])
                                        if len(data) == 0:
                                            is_empty = True
                            except Exception as e:
                                logger.warning(f"Failed to parse result JSON: {e}")
                                data = result_text
                        else:
                            data = result_text
                    else:
                        data = result
                else:
                    data = result
                
                return data, is_empty, has_null_values
            
    async def _summarize_results(self, question: str, dax_query: str, results: Any) -> str:
                """Generate a natural language summary of results"""
                # Format results for prompt
                if isinstance(results, list):
                    if len(results) == 0:
                        return "The query executed successfully but returned no results."
                    
                    results_text = json.dumps(results[:20], indent=2, default=str)
                    if len(results) > 20:
                        results_text += f"\n... and {len(results) - 20} more rows"
                else:
                    results_text = str(results)
                
                prompt = SUMMARIZE_RESULTS_PROMPT.format(
                    question=question,
                    dax_query=dax_query,
                    results=results_text
                )
                
                try:
                    response = await self.llm.ainvoke(prompt)
                    summary = response.content if hasattr(response, "content") else str(response)
                    return summary
                except Exception as e:
                    logger.warning(f"Summary generation failed: {e}")
                    # Fallback to simple summary
                    if isinstance(results, list):
                        return f"Found **{len(results)} results**. Here's the data:\n\n```json\n{json.dumps(results[:10], indent=2, default=str)}\n```"
                    return f"Result: {results}"
            
    def _generate_help_message(self, datasets: List[Dict]) -> str:
                """Generate a helpful message when intent is unclear"""
                if not datasets:
                    return "I don't see any datasets in this workspace. Please check the workspace ID."
                
                ds_names = [d.get("name", "Unknown") for d in datasets[:5]]
                
                return f"""I'm here to help you explore and query your Power BI data! 

        Here's what I can do:
        - **List datasets** - "Show me all datasets"
        - **Explore tables** - "What tables are in {ds_names[0]}?"  
        - **Query data** - "What are the total sales by region?"

        Available datasets: {', '.join(ds_names)}

        What would you like to know?"""


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history for a session"""
    if session_id in _sessions:
        return _sessions[session_id].get("history", [])
    return []


def clear_session(session_id: str):
    """Clear a conversation session"""
    if session_id in _sessions:
        del _sessions[session_id]
