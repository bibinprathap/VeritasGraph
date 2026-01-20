"""
Response models for the API
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DAXQueryResponse(BaseModel):
    """Response model for DAX query execution"""
    dax_query: str = Field(default="", description="Generated DAX query")
    natural_language_query: str = Field(..., description="Original natural language query")
    result: Optional[Any] = Field(default=None, description="Query execution results")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dax_query": "EVALUATE SUMMARIZECOLUMNS('Sales'[Region], 'Date'[Quarter], \"Total Sales\", SUM('Sales'[Amount]))",
                "natural_language_query": "Show me the total sales by region for the last quarter",
                "result": [
                    {"Region": "North", "Quarter": "Q4", "Total Sales": 150000},
                    {"Region": "South", "Quarter": "Q4", "Total Sales": 200000}
                ],
                "error": None,
                "metadata": {
                    "row_count": 2,
                    "execution_time_ms": 150
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid access token",
                "detail": "The provided access token has expired or is invalid"
            }
        }


class ToolCall(BaseModel):
    """Information about a tool that was called"""
    tool_name: str = Field(..., description="Name of the tool called")
    arguments: Dict[str, Any] = Field(default={}, description="Arguments passed to the tool")
    result_summary: Optional[str] = Field(None, description="Summary of tool result")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    message: str = Field(..., description="Assistant's response message")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    data: Optional[Any] = Field(default=None, description="Structured data if query returned results")
    dax_query: Optional[str] = Field(default=None, description="DAX query if one was executed")
    tools_called: Optional[List[ToolCall]] = Field(default=[], description="Tools that were called")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I found 3 datasets in this workspace:\n1. Sales Data\n2. HR Data\n3. Finance Data",
                "session_id": "session-123",
                "data": [
                    {"name": "Sales Data", "id": "dataset-1"},
                    {"name": "HR Data", "id": "dataset-2"},
                    {"name": "Finance Data", "id": "dataset-3"}
                ],
                "dax_query": None,
                "tools_called": [{"tool_name": "list_datasets", "arguments": {"workspace_id": "..."}}],
                "metadata": {"workspace_id": "..."}
            }
        }
