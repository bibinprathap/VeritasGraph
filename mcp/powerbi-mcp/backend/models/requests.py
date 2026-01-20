"""
Request models for the API
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language query"""
    access_token: str = Field(..., description="Power BI OAuth2 access token")
    query: str = Field(..., description="Natural language query to convert to DAX")
    workspace_id: str = Field(None, description="Optional: Workspace ID to scope the query")
    dataset_id: str = Field(None, description="Optional: Dataset ID to scope the query")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "query": "Show me the total sales by region for the last quarter",
                "workspace_id": "3fae44c2-94db-4d3b-8f39-f64b937a5d10",
                "dataset_id": "1e50eb69-ffac-4f25-8fac-57a289e5e6d6"
            }
        }


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    access_token: str = Field(..., description="Power BI OAuth2 access token")
    message: str = Field(..., description="User's chat message")
    workspace_id: str = Field(..., description="Workspace ID to chat about")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation history")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "message": "Show me all datasets in this workspace",
                "workspace_id": "3fae44c2-94db-4d3b-8f39-f64b937a5d10",
                "session_id": "session-123",
                "history": []
            }
        }

