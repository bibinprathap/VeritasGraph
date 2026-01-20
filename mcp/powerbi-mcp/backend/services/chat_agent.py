"""
Chat Agent for Power BI conversational interface
Handles conversation, tool selection, and response generation
"""
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.llm_provider import llm_provider
from backend.mcp_client import PowerBIMCPClient
from backend.services.schema_cache import schema_cache, CachedSchema
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

CRITICAL DAX SYNTAX RULES:
1. Table names with spaces MUST be wrapped in single quotes: 'Table Name'
2. Column references MUST use: 'Table Name'[Column Name]
3. DAX MUST start with EVALUATE

MANDATORY QUERY PATTERNS (use EXACTLY these patterns):

For DISTINCT/UNIQUE VALUES (listing all unique values):
  EVALUATE DISTINCT('Table Name'[Column Name])

For COUNTING rows or values (returns a single number):
  EVALUATE ROW("Count", COUNTROWS('Table Name'))
  EVALUATE ROW("Count", COUNT('Table Name'[Column Name]))
  EVALUATE ROW("Count", DISTINCTCOUNT('Table Name'[Column Name]))

For SUM/AVERAGE (returns a single number):
  EVALUATE ROW("Total", SUM('Table Name'[Column Name]))
  EVALUATE ROW("Average", AVERAGE('Table Name'[Column Name]))

For GROUPED aggregations (returns multiple rows):
  EVALUATE SUMMARIZECOLUMNS('Table'[GroupCol], "Total", SUM('Table'[ValueCol]))

IMPORTANT:
- COUNT, SUM, AVERAGE return scalar values - MUST wrap in ROW()
- DISTINCT, SUMMARIZECOLUMNS return tables - do NOT wrap in ROW()
- NEVER write: EVALUATE COUNT(...) - this is INVALID
- ALWAYS write: EVALUATE ROW("Count", COUNT(...))

Return ONLY valid JSON:
{{
    "dax": "EVALUATE ...",
    "explanation": "Brief explanation"
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


SUMMARIZE_RESULTS_PROMPT = """Summarize the following DAX query results in a friendly, conversational way.

USER QUESTION: {question}

DAX QUERY: {dax_query}

RESULTS:
{results}

Provide a clear, concise summary of what the data shows. If there are many results, highlight key findings.
Keep the response friendly and helpful."""


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
        # Validate access token first
        if not access_token or not access_token.strip():
            logger.error(f"Empty or missing access token provided. Token length: {len(access_token) if access_token else 0}")
            return {
                "message": "Access token is required but was not provided or is empty. Please provide a valid Power BI access token.",
                "session_id": session_id or str(uuid.uuid4()),
                "data": None,
                "dax_query": None,
                "tools_called": [],
                "metadata": {"error": "missing_access_token"}
            }
        
        logger.info(f"Processing message with access token (length: {len(access_token)})")
        
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
        
        # Step 1: Get workspace datasets (cached) - pass access_token explicitly
        workspace_info = await schema_cache.get_workspace_info(
            self.mcp_client, workspace_id, access_token=access_token
        )
        datasets = workspace_info.datasets
        
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
        
        # Get schema - use access_token from session
        access_token = session.get("access_token")
        schema = await schema_cache.get_dataset_schema(
            self.mcp_client, workspace_id, dataset_id, dataset_name, access_token=access_token
        )
        
        tools_called.append({
            "tool_name": "list_tables",
            "arguments": {"dataset_id": dataset_id},
            "result_summary": f"Found {len(schema.tables)} tables"
        })
        
        # Format response
        lines = [f"📁 **Dataset: {dataset_name}**\n"]
        lines.append(f"Found **{len(schema.tables)} tables**:\n")
        
        for table_name, columns in schema.tables.items():
            lines.append(f"### 📋 {table_name}")
            col_names = [c.get("name", "?") for c in columns[:10]]
            lines.append(f"   Columns: {', '.join(col_names)}")
            if len(columns) > 10:
                lines.append(f"   ... and {len(columns) - 10} more columns")
            lines.append("")
        
        lines.append("\n💡 Now you can ask questions about this data!")
        
        data = [
            {"name": t, "columns": [c.get("name") for c in cols]}
            for t, cols in schema.tables.items()
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
        
        # Step 1: Select the most relevant dataset based on user query
        logger.info(f"Selecting relevant dataset from {len(datasets)} datasets for: {message}")
        selected_dataset = await self._select_dataset(message, datasets)
        
        if not selected_dataset:
            # Fallback: use first dataset
            selected_dataset = datasets[0]
            logger.warning(f"Could not select dataset, using first one: {selected_dataset.get('name')}")
        
        dataset_id = selected_dataset.get("id")
        dataset_name = selected_dataset.get("name", dataset_id)
        session["current_dataset_id"] = dataset_id
        
        logger.info(f"Selected dataset: {dataset_name} (ID: {dataset_id})")
        
        # Step 2: Explore ONLY the selected dataset's schema (tables and columns)
        logger.info(f"Exploring schema for dataset: {dataset_name}")
        access_token = session.get("access_token")
        schema = await schema_cache.get_dataset_schema(
            self.mcp_client, workspace_id, dataset_id, dataset_name, access_token=access_token
        )
        
        tools_called.append({
            "tool_name": "list_tables",
            "arguments": {"workspace_id": workspace_id, "dataset_id": dataset_id},
            "result_summary": f"Explored '{dataset_name}': {len(schema.tables)} tables"
        })
        
        # Step 3: Format schema for DAX generation
        schema_text = self._format_schema_for_prompt(schema)
        logger.info(f"Schema for DAX generation:\n{schema_text[:1000]}...")
        
        # Step 4: Generate DAX query based on the selected dataset's schema
        dax_result = await self._generate_dax(message, schema_text)
        
        if not dax_result or not dax_result.get("dax"):
            # Provide helpful info about what was found
            tables_list = list(schema.tables.keys())
            return {
                "message": f"I explored the dataset **{dataset_name}** but couldn't generate a query for your question.\n\n**Available tables:** {', '.join(tables_list)}\n\nCould you rephrase your question or specify which table/column you're looking for?",
                "data": None,
                "dax_query": None
            }
        
        dax_query = dax_result.get("dax", "")
        
        # Step 5: Apply DAX guardrails
        dax_query = self._apply_dax_guardrails(dax_query)
        logger.info(f"Generated DAX for dataset '{dataset_name}': {dax_query}")
        
        tools_called.append({
            "tool_name": "execute_dax",
            "arguments": {"dataset": dataset_name, "dax_query": dax_query[:80] + "..."},
            "result_summary": "Executing query..."
        })
        
        # Step 6: Execute DAX
        try:
            result = await self.mcp_client.execute_dax(
                workspace_id, dataset_id, dax_query, access_token=access_token
            )
            
            # Parse result
            data = self._parse_dax_result(result)
            
            # Step 7: Generate summary
            summary = await self._summarize_results(message, dax_query, data)
            
            tools_called[-1]["result_summary"] = f"Returned {len(data) if isinstance(data, list) else 1} results"
            
            return {
                "message": summary,
                "data": data,
                "dax_query": dax_query
            }
            
        except Exception as e:
            logger.error(f"DAX execution error: {e}", exc_info=True)
            return {
                "message": f"I generated a query but encountered an error executing it:\n\n**Dataset:** {dataset_name}\n**Query:** `{dax_query}`\n\n**Error:** {str(e)}\n\nWould you like me to try a different approach?",
                "data": None,
                "dax_query": dax_query
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
    
    def _format_schema_for_prompt(self, schema: CachedSchema) -> str:
        """Format schema as text for LLM prompts"""
        lines = [f"Dataset: {schema.dataset_name}\n"]
        lines.append("Tables and Columns:")
        
        for table_name, columns in schema.tables.items():
            col_names = [f"'{table_name}'[{col.get('name', 'Unknown')}]" for col in columns]
            lines.append(f"\nTable: '{table_name}'")
            lines.append(f"  Columns: {', '.join(col_names)}")
        
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
            
            # Parse JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
                return result
        except Exception as e:
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
    
    def _parse_dax_result(self, result: Any) -> Any:
        """Parse DAX result from MCP response"""
        if isinstance(result, dict):
            if "result" in result:
                result_text = result["result"]
                # Try to parse JSON from result
                if isinstance(result_text, str):
                    try:
                        # Look for array
                        start = result_text.find("[")
                        end = result_text.rfind("]") + 1
                        if start >= 0 and end > start:
                            return json.loads(result_text[start:end])
                    except:
                        pass
                    try:
                        # Look for object
                        start = result_text.find("{")
                        end = result_text.rfind("}") + 1
                        if start >= 0 and end > start:
                            return json.loads(result_text[start:end])
                    except:
                        pass
                return result_text
            return result
        return result
    
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
