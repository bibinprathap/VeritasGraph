"""
GraphRAG FastAPI Server
Provides REST API endpoints for GraphRAG queries.
Lightweight version that imports search functions directly.
"""
import os
import sys
import asyncio
import time
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import pandas as pd
from os.path import join

# Add the graphrag-ollama-config directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(script_dir, '.env'))

# Import ingest functions (these have fewer dependencies)
from ingest import (
    ingest_text_content,
    trigger_graphrag_index,
    get_indexing_status,
    list_input_files
)

# GraphRAG imports for search
try:
    import tiktoken
    from graphrag.query.llm.oai.chat_openai import ChatOpenAI
    from graphrag.query.llm.oai.typing import OpenaiApiType
    from graphrag.query.llm.oai.embedding import OpenAIEmbedding
    from graphrag.query.indexer_adapters import (
        read_indexer_entities,
        read_indexer_reports,
        read_indexer_text_units,
        read_indexer_relationships,
    )
    from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
    from graphrag.query.structured_search.local_search.search import LocalSearch
    from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
    from graphrag.query.structured_search.global_search.search import GlobalSearch
    from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
    from graphrag.vector_stores.lancedb import LanceDBVectorStore
    from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
    GRAPHRAG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: GraphRAG search modules not available: {e}")
    GRAPHRAG_AVAILABLE = False

# Import LLM config from openai_config
try:
    from openai_config import get_llm_config, get_embedding_config
except ImportError:
    def get_llm_config():
        return {
            "api_key": os.getenv("GRAPHRAG_API_KEY", os.getenv("OPENAI_API_KEY", "ollama")),
            "api_base": os.getenv("GRAPHRAG_API_BASE", os.getenv("LLM_API_BASE", "http://127.0.0.1:11434/v1")),
            "model": os.getenv("GRAPHRAG_LLM_MODEL", os.getenv("LLM_MODEL", "llama3.1:latest")),
            "api_type": OpenaiApiType.OpenAI,
            "max_retries": 3,
        }
    def get_embedding_config():
        return {
            "api_key": os.getenv("GRAPHRAG_API_KEY", os.getenv("OPENAI_API_KEY", "ollama")),
            "api_base": os.getenv("GRAPHRAG_API_BASE", os.getenv("EMBEDDING_API_BASE", "http://127.0.0.1:11434/v1")),
            "api_type": OpenaiApiType.OpenAI,
            "model": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            "deployment_name": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            "max_retries": 3,
        }

app = FastAPI(
    title="VeritasGraph GraphRAG API",
    description="REST API for GraphRAG knowledge graph queries",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default paths
DEFAULT_OUTPUT_DIR = os.path.join(script_dir, "output", "artifacts")


class QueryRequest(BaseModel):
    query: str
    search_type: str = "local"  # "local" or "global"
    community_level: int = 2
    temperature: float = 0.5
    response_type: str = "Multiple Paragraphs"
    input_dir: Optional[str] = None


class IngestRequest(BaseModel):
    title: str
    content: str
    run_indexing: bool = False


class IndexRequest(BaseModel):
    update_mode: bool = False
    wait_for_completion: bool = True


class QueryResponse(BaseModel):
    response: str
    search_type: str
    query: str


class IngestResponse(BaseModel):
    success: bool
    message: str
    filepath: Optional[str] = None


class IndexingStatusResponse(BaseModel):
    status: str
    is_complete: bool


# OpenAI-compatible Chat Completion models
class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "graphrag"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False
    search_type: str = "local"  # GraphRAG-specific: "local" or "global"


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


@app.get("/")
async def root():
    return {
        "service": "VeritasGraph GraphRAG API",
        "version": "1.0.0",
        "endpoints": [
            "/v1/chat/completions - POST: OpenAI-compatible chat completion",
            "/query - POST: Execute GraphRAG query",
            "/ingest - POST: Ingest text content",
            "/index - POST: Trigger indexing",
            "/status - GET: Get indexing status",
            "/files - GET: List input files",
            "/health - GET: Health check",
            "/v1/models - GET: List available models"
        ]
    }


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "graphrag-local",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "veritasgraph",
                "description": "GraphRAG local search - best for specific entity queries"
            },
            {
                "id": "graphrag-global", 
                "object": "model",
                "created": int(time.time()),
                "owned_by": "veritasgraph",
                "description": "GraphRAG global search - best for broad summarization"
            }
        ]
    }


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completion endpoint.
    Uses GraphRAG to answer questions based on indexed knowledge.
    Supports system prompts for context/instructions.
    """
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG search modules not available"
        )
    
    # Extract system prompt if provided
    system_messages = [m for m in request.messages if m.role == "system"]
    system_prompt = system_messages[-1].content if system_messages else ""
    
    # Extract the user's query from messages
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message provided")
    
    # Use the last user message as the query
    user_query = user_messages[-1].content
    
    # Combine system prompt with user query for better context
    if system_prompt:
        query = f"Context/Instructions: {system_prompt}\n\nQuestion: {user_query}"
    else:
        query = user_query
    
    # Determine search type from model name or request
    search_type = request.search_type
    if "global" in request.model.lower():
        search_type = "global"
    elif "local" in request.model.lower():
        search_type = "local"
    
    # Check if index exists
    if not os.path.exists(DEFAULT_OUTPUT_DIR):
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content="No knowledge graph index found. Please run indexing first by calling POST /index or using the 'Index Schema' button."
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage()
        )
    
    try:
        # Build a query request and execute
        query_request = QueryRequest(
            query=query,
            search_type=search_type,
            temperature=request.temperature,
            input_dir=DEFAULT_OUTPUT_DIR
        )
        
        # Execute the query (reuse existing logic)
        result = await execute_query(query_request)
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=result.response
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=len(query.split()),
                completion_tokens=len(result.response.split()),
                total_tokens=len(query.split()) + len(result.response.split())
            )
        )
    except HTTPException as e:
        # Return error as assistant message for better UX
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=f"Error: {e.detail}"
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage()
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if output directory exists with parquet files
    has_index = os.path.exists(DEFAULT_OUTPUT_DIR) and any(
        f.endswith('.parquet') for f in os.listdir(DEFAULT_OUTPUT_DIR)
    ) if os.path.exists(DEFAULT_OUTPUT_DIR) else False
    
    return {
        "status": "healthy",
        "has_index": has_index,
        "output_dir": DEFAULT_OUTPUT_DIR
    }


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute a GraphRAG query using either local or global search.
    """
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG search modules not available"
        )
    
    input_dir = request.input_dir or DEFAULT_OUTPUT_DIR
    
    # Verify input directory exists
    if not os.path.exists(input_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Input directory not found: {input_dir}. Run indexing first."
        )
    
    # Check for required parquet files
    required_files = ["create_final_nodes.parquet", "create_final_community_reports.parquet"]
    missing = [f for f in required_files if not os.path.exists(os.path.join(input_dir, f))]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required index files: {missing}. Run indexing first."
        )
    
    try:
        # Load data using same file names as app.py
        ENTITY_TABLE = "create_final_nodes"
        ENTITY_EMBEDDING_TABLE = "create_final_entities"
        RELATIONSHIP_TABLE = "create_final_relationships"
        COMMUNITY_REPORT_TABLE = "create_final_community_reports"
        TEXT_UNIT_TABLE = "create_final_text_units"
        LANCEDB_URI = join(input_dir, "lancedb")
        
        entity_df = pd.read_parquet(join(input_dir, f"{ENTITY_TABLE}.parquet"))
        entity_embedding_df = pd.read_parquet(join(input_dir, f"{ENTITY_EMBEDDING_TABLE}.parquet"))
        relationship_df = pd.read_parquet(join(input_dir, f"{RELATIONSHIP_TABLE}.parquet"))
        report_df = pd.read_parquet(join(input_dir, f"{COMMUNITY_REPORT_TABLE}.parquet"))
        text_unit_df = pd.read_parquet(join(input_dir, f"{TEXT_UNIT_TABLE}.parquet"))
        
        # Get LLM and embedding config
        llm_config = get_llm_config()
        embedding_config = get_embedding_config()
        
        # Initialize LLM
        llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            api_base=llm_config["api_base"],
            model=llm_config["model"],
            api_type=llm_config["api_type"],
            max_retries=llm_config["max_retries"],
        )
        
        token_encoder = tiktoken.get_encoding("cl100k_base")
        
        if request.search_type.lower() == "global":
            # Global search
            reports = read_indexer_reports(report_df, entity_df, request.community_level)
            entities = read_indexer_entities(entity_df, entity_embedding_df, request.community_level)
            
            context_builder = GlobalCommunityContext(
                community_reports=reports,
                entities=entities,
                token_encoder=token_encoder,
            )
            search_engine = GlobalSearch(
                llm=llm,
                context_builder=context_builder,
                token_encoder=token_encoder,
                max_data_tokens=12000,
                map_llm_params={"max_tokens": 1000, "temperature": request.temperature},
                reduce_llm_params={"max_tokens": 2000, "temperature": request.temperature},
            )
            result = await search_engine.asearch(request.query)
            response = result.response
        else:
            # Local search
            entities = read_indexer_entities(entity_df, entity_embedding_df, request.community_level)
            relationships = read_indexer_relationships(relationship_df)
            reports = read_indexer_reports(report_df, entity_df, request.community_level)
            text_units = read_indexer_text_units(text_unit_df)
            
            # Connect to vector store
            description_embedding_store = LanceDBVectorStore(
                collection_name="entity_description_embeddings",
            )
            description_embedding_store.connect(db_uri=LANCEDB_URI)
            entity_description_embeddings = store_entity_semantic_embeddings(
                entities=entities, vectorstore=description_embedding_store
            )
            
            # Initialize text embedder
            text_embedder = OpenAIEmbedding(
                api_key=embedding_config["api_key"],
                api_base=embedding_config["api_base"],
                api_type=embedding_config["api_type"],
                model=embedding_config["model"],
                deployment_name=embedding_config["deployment_name"],
                max_retries=embedding_config["max_retries"],
            )
            
            context_builder = LocalSearchMixedContext(
                community_reports=reports,
                text_units=text_units,
                entities=entities,
                relationships=relationships,
                entity_text_embeddings=description_embedding_store,
                embedding_vectorstore_key=EntityVectorStoreKey.ID,
                text_embedder=text_embedder,
                token_encoder=token_encoder,
            )
            
            local_context_params = {
                "text_unit_prop": 0.5,
                "community_prop": 0.1,
                "top_k_mapped_entities": 10,
                "top_k_relationships": 10,
                "include_entity_rank": True,
                "include_relationship_weight": True,
                "max_tokens": 5000,
            }
            
            llm_params = {
                "max_tokens": 1500,
                "temperature": request.temperature,
            }
            
            search_engine = LocalSearch(
                llm=llm,
                context_builder=context_builder,
                token_encoder=token_encoder,
                llm_params=llm_params,
                context_builder_params=local_context_params,
                response_type=request.response_type,
            )
            result = await search_engine.asearch(request.query)
            response = result.response
        
        return QueryResponse(
            response=response,
            search_type=request.search_type,
            query=request.query
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=IngestResponse)
async def ingest_content(request: IngestRequest):
    """
    Ingest text content into the GraphRAG input directory.
    """
    try:
        success, message, filepath = ingest_text_content(
            title=request.title,
            content=request.content,
            auto_index=request.run_indexing
        )
        
        return IngestResponse(
            success=success,
            message=message,
            filepath=filepath
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index")
async def trigger_indexing(request: IndexRequest):
    """
    Trigger GraphRAG indexing of input files.
    """
    try:
        if request.wait_for_completion:
            success, message = trigger_graphrag_index(update_mode=request.update_mode)
            return {"success": success, "message": message}
        else:
            # Run in background
            asyncio.create_task(run_indexing_async(request.update_mode))
            return {"status": "started", "message": "Indexing started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_indexing_async(update_mode: bool = False):
    """Run indexing in background."""
    try:
        trigger_graphrag_index(update_mode=update_mode)
    except Exception as e:
        print(f"Indexing error: {e}")


@app.get("/status", response_model=IndexingStatusResponse)
async def indexing_status():
    """
    Get the current indexing status.
    """
    try:
        status_message, is_complete = get_indexing_status()
        return IndexingStatusResponse(
            status=status_message,
            is_complete=is_complete
        )
    except Exception as e:
        return IndexingStatusResponse(
            status=f"Error: {str(e)}",
            is_complete=False
        )


@app.get("/files")
async def get_input_files():
    """
    List all files in the input directory.
    """
    try:
        files = list_input_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GraphRAG API Server")
    parser.add_argument("--port", type=int, default=7860, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🚀 VeritasGraph GraphRAG API Server")
    print("="*60)
    print(f"🌐 API URL: http://{args.host}:{args.port}")
    print(f"📚 Docs URL: http://{args.host}:{args.port}/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host=args.host, port=args.port)
