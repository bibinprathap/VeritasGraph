"""
LangGraph agent for converting natural language to DAX queries
"""
import json
import logging
from typing import Annotated, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

from backend.config import settings
from backend.llm_provider import llm_provider
from backend.mcp_client import PowerBIMCPClient

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the Power BI agent"""
    messages: Annotated[List[BaseMessage], "Chat messages"]
    access_token: str
    workspace_id: Optional[str]
    dataset_id: Optional[str]
    dax_query: Optional[str]
    query_result: Optional[Dict]
    error: Optional[str]


class PowerBIAgent:
    """Agent that converts natural language to DAX and executes queries"""
    
    def __init__(self, mcp_client: PowerBIMCPClient):
        self.mcp_client = mcp_client
        self.llm = llm_provider.get_llm()
        self.graph = self._build_graph()
    
    def _create_tools(self) -> List:
        """Create LangChain tools from MCP client methods"""
        from langchain_core.tools import tool
        
        @tool
        async def list_workspaces(access_token: str) -> str:
            """List all Power BI workspaces"""
            workspaces = await self.mcp_client.list_workspaces(access_token)
            return json.dumps(workspaces, indent=2)
        
        @tool
        async def list_datasets(workspace_id: str, access_token: str) -> str:
            """List datasets in a workspace"""
            datasets = await self.mcp_client.list_datasets(workspace_id, access_token)
            return json.dumps(datasets, indent=2)
        
        @tool
        async def list_tables(workspace_id: str, dataset_id: str, access_token: str) -> str:
            """List tables in a dataset"""
            tables = await self.mcp_client.list_tables(workspace_id, dataset_id, access_token)
            return json.dumps(tables, indent=2)
        
        @tool
        async def list_columns(
            workspace_id: str, 
            dataset_id: str, 
            table_name: str, 
            access_token: str
        ) -> str:
            """List columns in a table"""
            columns = await self.mcp_client.list_columns(
                workspace_id, dataset_id, table_name, access_token
            )
            return json.dumps(columns, indent=2)
        
        @tool
        async def execute_dax(
            workspace_id: str,
            dataset_id: str,
            dax_query: str,
            access_token: str
        ) -> str:
            """Execute a DAX query against a Power BI dataset"""
            result = await self.mcp_client.execute_dax(
                workspace_id, dataset_id, dax_query, access_token
            )
            return json.dumps(result, indent=2)
        
        return [
            list_workspaces,
            list_datasets,
            list_tables,
            list_columns,
            execute_dax,
        ]
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph"""
        graph = StateGraph(AgentState)
        
        # Create tools
        tools = self._create_tools()
        tool_node = ToolNode(tools)
        
        # Add nodes
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", tool_node)
        graph.add_node("execute_query", self._execute_query_node)
        
        # Set entry point
        graph.set_entry_point("agent")
        
        # Add edges
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "execute": "execute_query",
                "end": END,
            }
        )
        
        graph.add_edge("tools", "agent")
        graph.add_edge("execute_query", END)
        
        return graph.compile()
    
    async def _agent_node(self, state: AgentState) -> AgentState:
        """Agent node that processes messages and decides next action"""
        messages = state["messages"]
        logger.info(f"Agent node called with {len(messages)} messages")
        
        # Get tools for the prompt
        tools = self._create_tools()
        tools_description = "\n".join([
            f"- {tool.name}: {tool.description}" for tool in tools
        ])
        
        # Create enhanced system prompt with tools
        workspace_id = state.get("workspace_id")
        dataset_id = state.get("dataset_id")
        
        enhanced_prompt = f"""{self._get_system_prompt()}

Available Tools:
{tools_description}

Current Context:
- Workspace ID: {workspace_id or "Not provided"}
- Dataset ID: {dataset_id or "Not provided"}

Instructions:
1. If workspace_id and dataset_id are provided, first explore the dataset structure using list_tables and list_columns tools
2. Based on the user's query, generate an appropriate DAX query
3. The DAX query should be a complete, executable query starting with EVALUATE or CALCULATE
4. Include the DAX query in your response in this format:

DAX Query:
EVALUATE ...

When you have a complete DAX query ready, include it in your response."""
        
        # Create system prompt
        system_prompt = SystemMessage(content=enhanced_prompt)
        
        # Add system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages
        else:
            messages[0] = system_prompt
        
        logger.info(f"Calling LLM with {len(messages)} messages")
        
        # Get LLM response - try to bind tools if supported, otherwise use regular invoke
        try:
            # Try to bind tools (works for OpenAI-compatible models)
            llm_with_tools = self.llm.bind_tools(tools)
            response = await llm_with_tools.ainvoke(messages)
            logger.info("LLM response received (with tool binding)")
        except (NotImplementedError, AttributeError, TypeError) as e:
            # Fallback for models that don't support bind_tools (like Ollama)
            # Use regular invoke and let the LLM respond with tool calls in text
            logger.info(f"bind_tools not supported ({type(e).__name__}), using regular invoke")
            response = await self.llm.ainvoke(messages)
            logger.info("LLM response received (regular invoke)")
        
        # Log response content
        if hasattr(response, "content"):
            content_preview = str(response.content)[:500] if response.content else "None"
            logger.info(f"LLM response content preview: {content_preview}")
        
        state["messages"].append(response)
        return state
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """You are a Power BI DAX query expert. Your task is to:
1. Understand natural language queries about Power BI data
2. Use available tools to explore the dataset structure (workspaces, datasets, tables, columns)
3. Generate accurate DAX queries based on the user's request
4. Execute the DAX query and return results

Important guidelines:
- Always explore the dataset structure first if workspace_id and dataset_id are provided
- Use list_tables and list_columns to understand available data
- Generate valid DAX queries that follow DAX syntax rules
- Use EVALUATE for table queries, CALCULATE for measure queries
- Always use execute_dax tool to run the generated query
- Return results in a clear, structured format

When the user provides a natural language query:
1. If workspace_id/dataset_id are provided, first explore the schema
2. Generate the appropriate DAX query
3. Execute it using execute_dax tool
4. Return the results to the user"""
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine the next step based on agent response"""
        messages = state["messages"]
        last_message = messages[-1]
        
        logger.info(f"_should_continue called. Last message type: {type(last_message).__name__}")
        
        # Check if the agent wants to call a tool (structured tool calls)
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(f"Found {len(last_message.tool_calls)} tool calls")
            # Check if it's execute_dax
            for tool_call in last_message.tool_calls:
                tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                logger.info(f"Tool call: {tool_name}")
                if tool_name == "execute_dax":
                    return "execute"
            return "continue"
        
        # Check for DAX query in text response (for models without structured tool calls)
        if isinstance(last_message, AIMessage) and hasattr(last_message, "content"):
            content = last_message.content
            if isinstance(content, str):
                logger.info(f"Checking content for DAX query. Content length: {len(content)}")
                # Check if DAX query is present
                if "EVALUATE" in content.upper() or "CALCULATE" in content.upper():
                    logger.info("Found EVALUATE or CALCULATE in content, extracting DAX query...")
                    # Extract and store DAX query
                    dax_query = self._extract_dax_from_content(content)
                    if dax_query:
                        logger.info(f"Extracted DAX query: {dax_query[:100]}...")
                        state["dax_query"] = dax_query
                        return "execute"
                    else:
                        logger.warning("DAX keywords found but extraction failed")
                else:
                    logger.info("No DAX keywords found in content")
        
        # If we have a DAX query ready, execute it
        if state.get("dax_query"):
            logger.info("DAX query found in state, executing...")
            return "execute"
        
        logger.info("No action determined, ending")
        return "end"
    
    def _extract_dax_from_content(self, content: str) -> Optional[str]:
        """Extract DAX query from LLM response content"""
        if not isinstance(content, str):
            return None
        
        # Look for DAX query in code blocks
        if "```dax" in content:
            start = content.find("```dax") + 6
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        elif "```" in content:
            # Try generic code block
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                potential_dax = content[start:end].strip()
                if "EVALUATE" in potential_dax.upper() or "CALCULATE" in potential_dax.upper():
                    return potential_dax
        
        # Look for DAX keywords in the content
        lines = content.split("\n")
        dax_lines = []
        in_dax = False
        
        for line in lines:
            line_upper = line.upper()
            if "EVALUATE" in line_upper or "CALCULATE" in line_upper or in_dax:
                in_dax = True
                dax_lines.append(line.strip())
                # Stop at empty line after DAX or non-DAX content
                if line.strip() == "" and len(dax_lines) > 1:
                    break
        
        if dax_lines:
            return " ".join(dax_lines)
        
        return None
    
    async def _execute_query_node(self, state: AgentState) -> AgentState:
        """Execute the DAX query"""
        try:
            # Extract DAX query from messages or state
            dax_query = state.get("dax_query")
            
            if not dax_query:
                # Try to extract from last message or tool calls
                last_message = state["messages"][-1]
                
                # Check if there's a tool call for execute_dax
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    for tool_call in last_message.tool_calls:
                        if tool_call["name"] == "execute_dax":
                            dax_query = tool_call.get("args", {}).get("dax_query")
                            break
                
                # If still not found, try to extract from message content
                if not dax_query and isinstance(last_message, AIMessage):
                    content = last_message.content
                    # Look for DAX query in code blocks or direct text
                    if "```dax" in content:
                        # Extract from code block
                        start = content.find("```dax") + 6
                        end = content.find("```", start)
                        if end > start:
                            dax_query = content[start:end].strip()
                    elif "EVALUATE" in content or "CALCULATE" in content:
                        # Extract DAX query from content
                        lines = content.split("\n")
                        dax_lines = []
                        in_dax = False
                        for line in lines:
                            if "EVALUATE" in line or "CALCULATE" in line or in_dax:
                                in_dax = True
                                dax_lines.append(line.strip())
                                # Stop at empty line or non-DAX content
                                if line.strip() == "" and len(dax_lines) > 1:
                                    break
                        if dax_lines:
                            dax_query = " ".join(dax_lines)
            
            if not dax_query:
                state["error"] = "Could not extract DAX query from agent response"
                return state
            
            # Execute the query
            workspace_id = state.get("workspace_id")
            dataset_id = state.get("dataset_id")
            access_token = state.get("access_token")
            
            if not workspace_id or not dataset_id:
                state["error"] = "workspace_id and dataset_id are required to execute queries"
                return state
            
            result = await self.mcp_client.execute_dax(
                workspace_id, dataset_id, dax_query, access_token
            )
            
            state["dax_query"] = dax_query
            state["query_result"] = result
            
            # Add result to messages
            state["messages"].append(
                AIMessage(content=f"Query executed successfully. Results: {json.dumps(result, indent=2)}")
            )
            
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            state["error"] = str(e)
            state["messages"].append(AIMessage(content=f"Error executing query: {str(e)}"))
        
        return state
    
    async def process_query(
        self,
        query: str,
        access_token: str,
        workspace_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> Dict:
        """Process a natural language query"""
        logger.info(f"Processing query: {query}")
        logger.info(f"Workspace ID: {workspace_id}, Dataset ID: {dataset_id}")
        
        # Set access token
        try:
            await self.mcp_client.set_access_token(access_token)
            logger.info("Access token set successfully")
        except Exception as e:
            logger.error(f"Error setting access token: {e}", exc_info=True)
            return {
                "dax_query": None,
                "query_result": None,
                "error": f"Failed to set access token: {str(e)}",
                "messages": [],
            }
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "access_token": access_token,
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "dax_query": None,
            "query_result": None,
            "error": None,
        }
        
        logger.info("Starting graph execution...")
        
        # Run the graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
            logger.info(f"Graph execution completed. Final state keys: {final_state.keys()}")
            logger.info(f"DAX query: {final_state.get('dax_query')}")
            logger.info(f"Error: {final_state.get('error')}")
            logger.info(f"Number of messages: {len(final_state.get('messages', []))}")
            
            # Log last few messages for debugging
            messages = final_state.get("messages", [])
            if messages:
                logger.info("Last 3 messages:")
                for i, msg in enumerate(messages[-3:]):
                    if hasattr(msg, "content"):
                        content_preview = str(msg.content)[:200] if msg.content else "None"
                        logger.info(f"  Message {i}: {type(msg).__name__} - {content_preview}")
        except Exception as e:
            logger.error(f"Error in graph execution: {e}", exc_info=True)
            return {
                "dax_query": None,
                "query_result": None,
                "error": f"Graph execution error: {str(e)}",
                "messages": [],
            }
        
        # Extract results
        return {
            "dax_query": final_state.get("dax_query"),
            "query_result": final_state.get("query_result"),
            "error": final_state.get("error"),
            "messages": [str(msg.content) if hasattr(msg, "content") and msg.content else str(msg) for msg in final_state.get("messages", [])],
        }

