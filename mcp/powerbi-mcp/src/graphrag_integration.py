"""
GraphRAG Integration for Power BI MCP
Provides knowledge graph-based context for dataset selection and DAX query generation.
"""
import asyncio
import json
import os
import logging
import subprocess
import sys
import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# GraphRAG server configuration
GRAPHRAG_API_URL = os.getenv("GRAPHRAG_API_URL", "http://localhost:7860")
GRAPHRAG_INPUT_DIR = os.getenv("GRAPHRAG_INPUT_DIR", None)
GRAPHRAG_CONFIG_DIR = os.getenv("GRAPHRAG_CONFIG_DIR", None)


class GraphRAGIntegration:
    """
    Integration with VeritasGraph/GraphRAG for Power BI schema knowledge.
    Enables intelligent dataset selection and DAX query generation using
    knowledge graph context.
    """

    def __init__(self, api_url: str = None, input_dir: str = None):
        self.api_url = api_url or GRAPHRAG_API_URL
        self.input_dir = input_dir or GRAPHRAG_INPUT_DIR
        self.config_dir = GRAPHRAG_CONFIG_DIR
        
        # If no input_dir specified, try to find it relative to the project
        if not self.input_dir:
            possible_paths = [
                Path(__file__).parent.parent.parent.parent / "graphrag-ollama-config" / "input",
                Path(__file__).parent.parent / "graphrag_input",
                # Absolute fallback path
                Path("c:/Projects/graphrag/VeritasGraph/graphrag-ollama-config/input"),
            ]
            for p in possible_paths:
                if p.exists():
                    self.input_dir = str(p)
                    logger.info(f"Found input directory: {self.input_dir}")
                    break
        
        if not self.input_dir:
            # Create default directory
            default_dir = Path(__file__).parent.parent.parent.parent / "graphrag-ollama-config" / "input"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.input_dir = str(default_dir)
            logger.info(f"Created default input directory: {self.input_dir}")
        
        # Find config directory (where settings.yaml lives)
        if not self.config_dir:
            possible_config_paths = [
                Path(__file__).parent.parent.parent.parent / "graphrag-ollama-config",
                Path("c:/Projects/graphrag/VeritasGraph/graphrag-ollama-config"),
            ]
            for p in possible_config_paths:
                if (p / "settings.yaml").exists():
                    self.config_dir = str(p)
                    logger.info(f"Found config directory: {self.config_dir}")
                    break
        
        logger.info(f"GraphRAG Integration initialized: API={self.api_url}, InputDir={self.input_dir}, ConfigDir={self.config_dir}")

    async def _run_indexing_directly(self) -> Tuple[bool, str]:
        """
        Run GraphRAG indexing directly via subprocess as fallback when API is unavailable.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.config_dir:
            return False, "Config directory not found for direct indexing"
        
        try:
            logger.info(f"Running GraphRAG indexing directly from {self.config_dir}")
            
            # Find Python executable in venv
            venv_python = Path(self.config_dir).parent / ".venv" / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = Path(self.config_dir) / ".venv" / "Scripts" / "python.exe"
            if not venv_python.exists():
                venv_python = sys.executable  # Fallback to current Python
            
            # Run graphrag index command
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    [str(venv_python), "-m", "graphrag", "index", "--root", self.config_dir],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    cwd=self.config_dir
                )
            )
            
            if result.returncode == 0:
                logger.info("GraphRAG indexing completed successfully")
                return True, "Indexing completed successfully"
            else:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"GraphRAG indexing failed: {error_msg}")
                return False, f"Indexing failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            logger.error("GraphRAG indexing timed out")
            return False, "Indexing timed out (>5 minutes)"
        except Exception as e:
            logger.error(f"Error running direct indexing: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

    async def index_powerbi_schema(
        self,
        workspaces: List[Dict],
        datasets: Dict[str, List[Dict]],  # workspace_id -> datasets
        tables: Dict[str, Dict[str, List[Dict]]],  # workspace_id -> dataset_id -> tables
        columns: Dict[str, Dict[str, Dict[str, List[Dict]]]],  # workspace_id -> dataset_id -> table_name -> columns
        measures: Optional[Dict[str, Dict[str, List[Dict]]]] = None,  # workspace_id -> dataset_id -> measures
        relationships: Optional[Dict[str, Dict[str, List[Dict]]]] = None,  # workspace_id -> dataset_id -> relationships
    ) -> Tuple[bool, str, str]:
        """
        Index Power BI schema into GraphRAG knowledge base.
        
        This creates a comprehensive document describing the Power BI schema
        that GraphRAG can use for context-aware query generation.
        
        Returns:
            Tuple of (success, message, filepath)
        """
        try:
            logger.info(f"Starting schema indexing: {len(workspaces)} workspaces, input_dir={self.input_dir}")
            
            # Build comprehensive schema document
            doc_lines = [
                "# Power BI Schema Knowledge Base",
                f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "# This document contains the complete schema of Power BI datasets for intelligent query generation.",
                "",
                "---",
                "",
            ]
            
            # Index workspaces
            doc_lines.append("## Power BI Workspaces")
            doc_lines.append("")
            for ws in workspaces:
                ws_id = ws.get("id", "unknown")
                ws_name = ws.get("name", "Unknown Workspace")
                ws_type = ws.get("type", "Unknown")
                doc_lines.append(f"### Workspace: {ws_name}")
                doc_lines.append(f"- **ID:** {ws_id}")
                doc_lines.append(f"- **Type:** {ws_type}")
                doc_lines.append("")
                
                # Add datasets for this workspace
                ws_datasets = datasets.get(ws_id, [])
                if ws_datasets:
                    doc_lines.append("#### Datasets in this workspace:")
                    for ds in ws_datasets:
                        ds_id = ds.get("id", "unknown")
                        ds_name = ds.get("name", "Unknown Dataset")
                        doc_lines.append(f"- **{ds_name}** (ID: {ds_id})")
                        
                        # Add tables for this dataset
                        ds_tables = tables.get(ws_id, {}).get(ds_id, [])
                        if ds_tables:
                            doc_lines.append(f"  Tables in {ds_name}:")
                            for tbl in ds_tables:
                                tbl_name = tbl.get("name", "Unknown Table")
                                doc_lines.append(f"    - **{tbl_name}**")
                                
                                # Add columns for this table
                                tbl_columns = columns.get(ws_id, {}).get(ds_id, {}).get(tbl_name, [])
                                if tbl_columns:
                                    col_list = ", ".join([
                                        f"{c.get('name', '?')} ({c.get('dataType', 'unknown')})"
                                        for c in tbl_columns[:10]  # Limit for readability
                                    ])
                                    if len(tbl_columns) > 10:
                                        col_list += f" ... and {len(tbl_columns) - 10} more"
                                    doc_lines.append(f"      Columns: {col_list}")
                        
                        # Add measures if available
                        ds_measures = measures.get(ws_id, {}).get(ds_id, []) if measures else []
                        if ds_measures:
                            doc_lines.append(f"  Measures in {ds_name}:")
                            for measure in ds_measures[:10]:
                                m_name = measure.get("name", "Unknown")
                                m_expr = measure.get("expression", "")[:100]
                                doc_lines.append(f"    - **{m_name}**: {m_expr}...")
                        
                        doc_lines.append("")
                doc_lines.append("")
            
            # Add DAX query examples section
            doc_lines.extend([
                "## DAX Query Patterns",
                "",
                "### Common DAX Query Patterns for this schema:",
                "",
                "1. **Basic table scan:**",
                "   ```dax",
                "   EVALUATE TableName",
                "   ```",
                "",
                "2. **Filtered query:**",
                "   ```dax",
                "   EVALUATE FILTER(TableName, ColumnName = \"Value\")",
                "   ```",
                "",
                "3. **Aggregation:**",
                "   ```dax",
                "   EVALUATE SUMMARIZECOLUMNS(",
                "       TableName[GroupColumn],",
                "       \"Sum\", SUM(TableName[ValueColumn])",
                "   )",
                "   ```",
                "",
                "4. **Top N:**",
                "   ```dax",
                "   EVALUATE TOPN(10, TableName, TableName[Column], DESC)",
                "   ```",
                "",
            ])
            
            # Create the document
            content = "\n".join(doc_lines)
            
            # Save to GraphRAG input directory
            if self.input_dir:
                os.makedirs(self.input_dir, exist_ok=True)
                filename = f"powerbi_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filepath = os.path.join(self.input_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Power BI schema saved to {filepath}")
                
                # Trigger GraphRAG indexing via API or direct fallback
                indexing_message = ""
                indexing_success = False
                
                # First try API
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{self.api_url}/index",
                            json={
                                "update_mode": False,
                                "wait_for_completion": False  # Don't block - indexing runs in background
                            }
                        )
                        if response.status_code == 200:
                            result = response.json()
                            indexing_message = f" GraphRAG indexing started: {result.get('message', 'Background indexing initiated')}"
                            indexing_success = True
                            logger.info(f"GraphRAG indexing triggered successfully via API")
                        else:
                            logger.warning(f"GraphRAG API returned {response.status_code}, trying direct indexing")
                except httpx.ConnectError:
                    logger.warning("GraphRAG API not available, trying direct indexing fallback")
                except Exception as api_err:
                    logger.warning(f"GraphRAG API error: {api_err}, trying direct indexing fallback")
                
                # Fallback to direct indexing if API failed
                if not indexing_success:
                    direct_success, direct_message = await self._run_indexing_directly()
                    if direct_success:
                        indexing_message = f" {direct_message}"
                        indexing_success = True
                    else:
                        indexing_message = f" Warning: {direct_message}"
                
                return True, f"Schema indexed successfully with {len(workspaces)} workspaces.{indexing_message}", filepath
            else:
                logger.warning("No input directory configured for GraphRAG")
                return False, "GraphRAG input directory not configured", ""
                
        except Exception as e:
            logger.error(f"Error indexing Power BI schema: {e}", exc_info=True)
            return False, f"Error indexing schema: {str(e)}", ""

    async def query_schema_context(
        self,
        user_query: str,
        workspace_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query GraphRAG for relevant schema context based on user's question.
        
        This helps the LLM understand which datasets/tables/columns are relevant
        for generating the DAX query.
        
        Returns:
            Dict with schema context and suggestions
        """
        try:
            # Build context query
            context_query = f"Power BI schema for: {user_query}"
            if workspace_name:
                context_query += f" in workspace {workspace_name}"
            if dataset_name:
                context_query += f" using dataset {dataset_name}"
            
            # Call GraphRAG API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}/query",
                    json={
                        "query": context_query,
                        "search_type": "local",  # Use local search for specific entities
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "context": result.get("response", ""),
                        "entities": result.get("entities", []),
                        "source": "graphrag"
                    }
                else:
                    logger.warning(f"GraphRAG query failed: {response.status_code}")
                    return {
                        "success": False,
                        "context": "",
                        "entities": [],
                        "error": f"GraphRAG returned {response.status_code}"
                    }
                    
        except httpx.ConnectError:
            logger.warning("GraphRAG server not available")
            return {
                "success": False,
                "context": "",
                "entities": [],
                "error": "GraphRAG server not available"
            }
        except Exception as e:
            logger.error(f"Error querying GraphRAG: {e}", exc_info=True)
            return {
                "success": False,
                "context": "",
                "entities": [],
                "error": str(e)
            }

    async def suggest_dataset(
        self,
        user_query: str,
        available_workspaces: List[Dict],
        available_datasets: Dict[str, List[Dict]],
    ) -> Dict[str, Any]:
        """
        Use GraphRAG knowledge to suggest the best dataset for a user query.
        
        Returns:
            Dict with suggested workspace_id, dataset_id, and reasoning
        """
        try:
            # First, try to get context from GraphRAG
            context_result = await self.query_schema_context(user_query)
            
            # Build a prompt to analyze which dataset to use
            dataset_list = []
            for ws in available_workspaces:
                ws_id = ws.get("id")
                ws_name = ws.get("name")
                for ds in available_datasets.get(ws_id, []):
                    dataset_list.append({
                        "workspace_id": ws_id,
                        "workspace_name": ws_name,
                        "dataset_id": ds.get("id"),
                        "dataset_name": ds.get("name"),
                    })
            
            if not dataset_list:
                return {
                    "success": False,
                    "error": "No datasets available",
                    "suggested_workspace_id": None,
                    "suggested_dataset_id": None,
                }
            
            # If only one dataset, return it
            if len(dataset_list) == 1:
                ds = dataset_list[0]
                return {
                    "success": True,
                    "suggested_workspace_id": ds["workspace_id"],
                    "suggested_workspace_name": ds["workspace_name"],
                    "suggested_dataset_id": ds["dataset_id"],
                    "suggested_dataset_name": ds["dataset_name"],
                    "reasoning": "Only one dataset available",
                    "graphrag_context": context_result.get("context", "")
                }
            
            # Use GraphRAG context to help select
            graphrag_context = context_result.get("context", "")
            
            # Simple keyword matching as fallback
            user_query_lower = user_query.lower()
            best_match = None
            best_score = 0
            
            for ds in dataset_list:
                score = 0
                ds_name_lower = ds["dataset_name"].lower()
                ws_name_lower = ds["workspace_name"].lower()
                
                # Check for name matches
                for word in user_query_lower.split():
                    if len(word) > 3:  # Skip short words
                        if word in ds_name_lower:
                            score += 10
                        if word in ws_name_lower:
                            score += 5
                
                # Check GraphRAG context for mentions
                if graphrag_context:
                    if ds["dataset_name"] in graphrag_context:
                        score += 20
                    if ds["workspace_name"] in graphrag_context:
                        score += 10
                
                if score > best_score:
                    best_score = score
                    best_match = ds
            
            if best_match:
                return {
                    "success": True,
                    "suggested_workspace_id": best_match["workspace_id"],
                    "suggested_workspace_name": best_match["workspace_name"],
                    "suggested_dataset_id": best_match["dataset_id"],
                    "suggested_dataset_name": best_match["dataset_name"],
                    "reasoning": f"Best match based on query analysis (score: {best_score})",
                    "graphrag_context": graphrag_context
                }
            else:
                # Return first dataset as default
                ds = dataset_list[0]
                return {
                    "success": True,
                    "suggested_workspace_id": ds["workspace_id"],
                    "suggested_workspace_name": ds["workspace_name"],
                    "suggested_dataset_id": ds["dataset_id"],
                    "suggested_dataset_name": ds["dataset_name"],
                    "reasoning": "Default selection (first available)",
                    "graphrag_context": graphrag_context
                }
                
        except Exception as e:
            logger.error(f"Error suggesting dataset: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "suggested_workspace_id": None,
                "suggested_dataset_id": None,
            }

    async def generate_dax_context(
        self,
        user_query: str,
        workspace_name: str,
        dataset_name: str,
        tables: List[Dict],
        columns: Dict[str, List[Dict]],  # table_name -> columns
    ) -> str:
        """
        Generate enriched context for DAX query generation using GraphRAG.
        
        Returns:
            Enhanced system prompt context for DAX generation
        """
        try:
            # Query GraphRAG for relevant context
            context_result = await self.query_schema_context(
                user_query, workspace_name, dataset_name
            )
            
            # Build schema context
            schema_parts = [
                f"## Dataset: {dataset_name} (Workspace: {workspace_name})",
                "",
                "### Available Tables and Columns:",
            ]
            
            for table in tables:
                table_name = table.get("name", "Unknown")
                schema_parts.append(f"\n**{table_name}**:")
                
                table_columns = columns.get(table_name, [])
                for col in table_columns:
                    col_name = col.get("name", "?")
                    col_type = col.get("dataType", "unknown")
                    schema_parts.append(f"  - {col_name} ({col_type})")
            
            schema_context = "\n".join(schema_parts)
            
            # Combine with GraphRAG context
            graphrag_context = context_result.get("context", "")
            
            full_context = f"""
{schema_context}

### Knowledge Graph Context:
{graphrag_context if graphrag_context else "No additional context available from knowledge graph."}

### User Query:
{user_query}

### Instructions:
Based on the schema above and the knowledge graph context, generate a valid DAX query.
- Use EVALUATE for table queries
- Use proper column references: TableName[ColumnName]
- Apply appropriate filters and aggregations
"""
            
            return full_context
            
        except Exception as e:
            logger.error(f"Error generating DAX context: {e}", exc_info=True)
            return f"Error generating context: {str(e)}"


# Singleton instance
_graphrag_integration: Optional[GraphRAGIntegration] = None


def get_graphrag_integration() -> GraphRAGIntegration:
    """Get or create GraphRAG integration instance"""
    global _graphrag_integration
    if _graphrag_integration is None:
        _graphrag_integration = GraphRAGIntegration()
    return _graphrag_integration
