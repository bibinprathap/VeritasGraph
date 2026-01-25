#!/usr/bin/env python3
"""
VeritasGraph MCP Server - Exposes GraphRAG functionality through the Model Context Protocol (MCP)

This server allows Claude Desktop, Cursor, and other MCP-compatible agents to:
- Query the knowledge graph using local or global search
- Ingest new content into the graph
- Trigger indexing operations
- Get graph statistics and health information
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union
from os.path import join

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Load environment variables
# First try the graphrag-ollama-config .env, then local .env
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPHRAG_CONFIG_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "graphrag-ollama-config"))

# Load .env from graphrag-ollama-config directory first (this has the API keys)
graphrag_env = os.path.join(GRAPHRAG_CONFIG_DIR, ".env")
if os.path.exists(graphrag_env):
    load_dotenv(graphrag_env)
    
# Then load local .env for any overrides
load_dotenv()
sys.path.insert(0, GRAPHRAG_CONFIG_DIR)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# GraphRAG imports
GRAPHRAG_AVAILABLE = False
try:
    import tiktoken
    import pandas as pd
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
    logger.info("GraphRAG modules loaded successfully")
except ImportError as e:
    logger.warning(f"GraphRAG modules not available: {e}")

# Import ingest functions
try:
    from ingest import (
        ingest_text_content,
        ingest_url,
        trigger_graphrag_index,
        get_indexing_status,
        list_input_files,
        delete_input_file,
        is_youtube_url,
    )
    INGEST_AVAILABLE = True
    logger.info("Ingest modules loaded successfully")
except ImportError as e:
    logger.warning(f"Ingest modules not available: {e}")
    INGEST_AVAILABLE = False

# Import OpenAI config
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


# ============================================================================
# Configuration
# ============================================================================

class VeritasConfig(BaseModel):
    """Configuration for VeritasGraph MCP Server."""
    
    output_dir: str = Field(
        default_factory=lambda: os.path.join(GRAPHRAG_CONFIG_DIR, "output", "artifacts")
    )
    input_dir: str = Field(
        default_factory=lambda: os.path.join(GRAPHRAG_CONFIG_DIR, "input")
    )
    default_community_level: int = 2
    default_temperature: float = 0.5
    default_response_type: str = "Multiple Paragraphs"
    
    @classmethod
    def from_env(cls) -> 'VeritasConfig':
        """Create configuration from environment variables."""
        return cls(
            output_dir=os.environ.get(
                'VERITAS_OUTPUT_DIR',
                os.path.join(GRAPHRAG_CONFIG_DIR, "output", "artifacts")
            ),
            input_dir=os.environ.get(
                'VERITAS_INPUT_DIR',
                os.path.join(GRAPHRAG_CONFIG_DIR, "input")
            ),
            default_community_level=int(os.environ.get('VERITAS_COMMUNITY_LEVEL', '2')),
            default_temperature=float(os.environ.get('VERITAS_TEMPERATURE', '0.5')),
            default_response_type=os.environ.get('VERITAS_RESPONSE_TYPE', 'Multiple Paragraphs'),
        )


# Global configuration
config = VeritasConfig.from_env()


# ============================================================================
# MCP Server Instructions
# ============================================================================

VERITAS_MCP_INSTRUCTIONS = """
Welcome to VeritasGraph MCP Server - A GraphRAG-powered knowledge graph query system.

VeritasGraph uses Microsoft's GraphRAG technology to transform documents into a rich knowledge graph, 
enabling both local (entity-focused) and global (community-summarization) search capabilities.

## Key Capabilities:

### 1. Query the Knowledge Graph
- **Local Search** (`query_graph` with search_type="local"): Best for specific questions about entities, 
  relationships, and detailed facts. Uses vector similarity + graph traversal.
- **Global Search** (`query_graph` with search_type="global"): Best for broad questions requiring 
  synthesis across multiple topics. Uses community reports for comprehensive answers.

### 2. Ingest New Content
- **Text Content** (`ingest_text`): Add plain text documents to the knowledge base.
- **URLs** (`ingest_url`): Automatically extract content from web pages or YouTube videos.

### 3. Index Management
- **Trigger Indexing** (`trigger_index`): Build/update the knowledge graph from ingested content.
- **Check Status** (`get_index_status`): Monitor indexing progress.

### 4. Information Retrieval
- **List Files** (`list_files`): See all documents in the input directory.
- **Health Check** (`health_check`): Verify system status and graph availability.
- **Graph Statistics** (`get_graph_stats`): Get counts of entities, relationships, and communities.

## Usage Tips:
- Start with `health_check` to verify the system is ready.
- Use `get_graph_stats` to understand the knowledge graph's contents.
- For factual questions about specific topics, use local search.
- For summary or synthesis questions, use global search.
- After ingesting new content, run `trigger_index` to update the graph.

## Response Types:
- "Single Paragraph" - Brief, concise answers
- "Multiple Paragraphs" - Detailed explanations
- "List of 3-7 Points" - Bullet point format
- "Single Page" - Comprehensive single-page response
- "Multi-Page Report" - In-depth analysis

The knowledge graph is built from your indexed documents and enables semantic understanding 
of entities, their relationships, and community structures.
"""


# ============================================================================
# MCP Server Instance
# ============================================================================

mcp = FastMCP(
    'veritasgraph',
    instructions=VERITAS_MCP_INSTRUCTIONS,
)


# ============================================================================
# Helper Functions
# ============================================================================

def check_index_exists() -> tuple[bool, str]:
    """Check if the GraphRAG index exists and is ready."""
    if not os.path.exists(config.output_dir):
        return False, f"Output directory not found: {config.output_dir}"
    
    required_files = [
        "create_final_nodes.parquet",
        "create_final_community_reports.parquet",
        "create_final_entities.parquet",
        "create_final_relationships.parquet",
        "create_final_text_units.parquet",
    ]
    
    missing = [f for f in required_files if not os.path.exists(os.path.join(config.output_dir, f))]
    if missing:
        return False, f"Missing index files: {missing}"
    
    return True, "Index is ready"


async def execute_local_search(
    query: str,
    community_level: int = 2,
    temperature: float = 0.5,
    response_type: str = "Multiple Paragraphs"
) -> str:
    """Execute a local search query."""
    input_dir = config.output_dir
    LANCEDB_URI = join(input_dir, "lancedb")
    
    # Load parquet files
    entity_df = pd.read_parquet(join(input_dir, "create_final_nodes.parquet"))
    entity_embedding_df = pd.read_parquet(join(input_dir, "create_final_entities.parquet"))
    relationship_df = pd.read_parquet(join(input_dir, "create_final_relationships.parquet"))
    report_df = pd.read_parquet(join(input_dir, "create_final_community_reports.parquet"))
    text_unit_df = pd.read_parquet(join(input_dir, "create_final_text_units.parquet"))
    
    # Get configs
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
    
    # Read index data
    entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)
    relationships = read_indexer_relationships(relationship_df)
    reports = read_indexer_reports(report_df, entity_df, community_level)
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
    
    # Build context
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
        "temperature": temperature,
    }
    
    search_engine = LocalSearch(
        llm=llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
        response_type=response_type,
    )
    
    result = await search_engine.asearch(query)
    return result.response


async def execute_global_search(
    query: str,
    community_level: int = 2,
    temperature: float = 0.5,
    response_type: str = "Multiple Paragraphs"
) -> str:
    """Execute a global search query."""
    input_dir = config.output_dir
    
    # Load parquet files
    entity_df = pd.read_parquet(join(input_dir, "create_final_nodes.parquet"))
    entity_embedding_df = pd.read_parquet(join(input_dir, "create_final_entities.parquet"))
    report_df = pd.read_parquet(join(input_dir, "create_final_community_reports.parquet"))
    
    # Get config
    llm_config = get_llm_config()
    
    # Initialize LLM
    llm = ChatOpenAI(
        api_key=llm_config["api_key"],
        api_base=llm_config["api_base"],
        model=llm_config["model"],
        api_type=llm_config["api_type"],
        max_retries=llm_config["max_retries"],
    )
    
    token_encoder = tiktoken.get_encoding("cl100k_base")
    
    # Read index data
    reports = read_indexer_reports(report_df, entity_df, community_level)
    entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)
    
    # Build context
    context_builder = GlobalCommunityContext(
        community_reports=reports,
        entities=entities,
        token_encoder=token_encoder,
    )
    
    context_builder_params = {
        "use_community_summary": False,
        "shuffle_data": True,
        "include_community_rank": True,
        "min_community_rank": 0,
        "community_rank_name": "rank",
        "include_community_weight": True,
        "community_weight_name": "occurrence weight",
        "normalize_community_weight": True,
        "max_tokens": 12000,
        "context_name": "Reports",
    }
    
    map_llm_params = {
        "max_tokens": 1000,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    
    reduce_llm_params = {
        "max_tokens": 2000,
        "temperature": temperature,
    }
    
    search_engine = GlobalSearch(
        llm=llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        max_data_tokens=12000,
        map_llm_params=map_llm_params,
        reduce_llm_params=reduce_llm_params,
        allow_general_knowledge=False,
        json_mode=True,
        context_builder_params=context_builder_params,
        concurrent_coroutines=1,
        response_type=response_type,
    )
    
    result = await search_engine.asearch(query)
    return result.response


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def query_graph(
    query: str,
    search_type: str = "local",
    community_level: int = 2,
    temperature: float = 0.5,
    response_type: str = "Multiple Paragraphs",
) -> dict[str, Any]:
    """Query the VeritasGraph knowledge graph using GraphRAG.
    
    This is the primary tool for asking questions about the indexed knowledge base.
    
    Args:
        query: The question or query to search for in the knowledge graph.
        search_type: Type of search to perform:
            - "local": Entity-focused search, best for specific questions about 
              entities, relationships, and detailed facts. Uses vector similarity 
              and graph traversal.
            - "global": Community-based search, best for broad questions requiring 
              synthesis across multiple topics. Uses community reports.
        community_level: Depth of community analysis (1-5). Higher values = more 
            detailed community structure. Default: 2.
        temperature: LLM temperature for response generation (0.0-1.0). Lower = 
            more focused, higher = more creative. Default: 0.5.
        response_type: Format of the response:
            - "Single Paragraph": Brief, concise answer
            - "Multiple Paragraphs": Detailed explanation (default)
            - "List of 3-7 Points": Bullet point format
            - "Single Page": Comprehensive response
            - "Multi-Page Report": In-depth analysis
    
    Returns:
        Dictionary with:
            - response: The answer to the query
            - search_type: The search type used
            - query: The original query
            - error: Error message if query failed
    
    Examples:
        # Specific entity question (use local search)
        query_graph(
            query="What are the key features of the product mentioned in the documents?",
            search_type="local"
        )
        
        # Broad synthesis question (use global search)
        query_graph(
            query="Summarize the main themes across all documents",
            search_type="global",
            response_type="List of 3-7 Points"
        )
    """
    if not GRAPHRAG_AVAILABLE:
        return {"error": "GraphRAG modules not available. Please install graphrag package."}
    
    # Check if index exists
    index_ready, message = check_index_exists()
    if not index_ready:
        return {
            "error": f"Knowledge graph not ready: {message}. Run trigger_index first.",
            "suggestion": "Use the trigger_index tool to build the knowledge graph from your documents."
        }
    
    try:
        logger.info(f"Executing {search_type} search for query: {query[:50]}...")
        
        if search_type.lower() == "global":
            response = await execute_global_search(
                query=query,
                community_level=community_level,
                temperature=temperature,
                response_type=response_type,
            )
        else:
            response = await execute_local_search(
                query=query,
                community_level=community_level,
                temperature=temperature,
                response_type=response_type,
            )
        
        logger.info(f"Query completed successfully")
        return {
            "response": response,
            "search_type": search_type,
            "query": query,
        }
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return {"error": f"Query failed: {str(e)}"}


@mcp.tool()
async def ingest_text(
    title: str,
    content: str,
    auto_index: bool = False,
) -> dict[str, Any]:
    """Ingest text content into the VeritasGraph knowledge base.
    
    This tool adds new text documents to the input directory for indexing.
    After ingesting content, you should run trigger_index to update the knowledge graph.
    
    Args:
        title: Title for the document (used as filename). Should be descriptive.
        content: The text content to ingest. Can be plain text, markdown, or 
            structured content.
        auto_index: If True, automatically trigger indexing after ingestion.
            Default: False (you can batch multiple ingestions before indexing).
    
    Returns:
        Dictionary with:
            - success: Whether ingestion succeeded
            - message: Status message
            - filepath: Path to the created file
            - error: Error message if failed
    
    Examples:
        # Ingest a document
        ingest_text(
            title="Product Requirements",
            content="Our product must support real-time collaboration..."
        )
        
        # Ingest and immediately index
        ingest_text(
            title="Meeting Notes",
            content="Discussed Q4 roadmap...",
            auto_index=True
        )
    """
    if not INGEST_AVAILABLE:
        return {"error": "Ingest modules not available"}
    
    try:
        success, message, filepath = ingest_text_content(
            title=title,
            content=content,
            auto_index=auto_index
        )
        
        return {
            "success": success,
            "message": message,
            "filepath": filepath,
        }
    except Exception as e:
        logger.error(f"Ingest failed: {str(e)}")
        return {"error": f"Ingest failed: {str(e)}"}


@mcp.tool()
async def ingest_url(
    url: str,
    auto_index: bool = False,
) -> dict[str, Any]:
    """Ingest content from a URL into the VeritasGraph knowledge base.
    
    Supports:
    - Web articles: Automatically extracts main content using trafilatura
    - YouTube videos: Extracts transcripts/captions
    
    Args:
        url: The URL to ingest content from. Supported formats:
            - Web pages (https://example.com/article)
            - YouTube videos (https://youtube.com/watch?v=... or https://youtu.be/...)
        auto_index: If True, automatically trigger indexing after ingestion.
            Default: False.
    
    Returns:
        Dictionary with:
            - success: Whether ingestion succeeded
            - message: Status message with extracted content info
            - filepath: Path to the created file
            - metadata: Additional info about the extracted content
            - error: Error message if failed
    
    Examples:
        # Ingest a web article
        ingest_url(url="https://example.com/blog/ai-trends-2024")
        
        # Ingest a YouTube video transcript
        ingest_url(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            auto_index=True
        )
    """
    if not INGEST_AVAILABLE:
        return {"error": "Ingest modules not available"}
    
    try:
        success, message, filepath, metadata = ingest_url(
            url=url,
            auto_index=auto_index
        )
        
        return {
            "success": success,
            "message": message,
            "filepath": filepath,
            "metadata": metadata,
        }
    except Exception as e:
        logger.error(f"URL ingest failed: {str(e)}")
        return {"error": f"URL ingest failed: {str(e)}"}


@mcp.tool()
async def trigger_index(
    update_mode: bool = False,
    wait_for_completion: bool = True,
) -> dict[str, Any]:
    """Trigger GraphRAG indexing to build/update the knowledge graph.
    
    This processes all documents in the input directory and builds:
    - Entity extraction and relationships
    - Community detection and reports
    - Vector embeddings for semantic search
    
    Args:
        update_mode: If True, only process new/changed documents (incremental).
            If False, rebuild the entire index. Default: False.
        wait_for_completion: If True, wait for indexing to complete before 
            returning. If False, start indexing in background. Default: True.
    
    Returns:
        Dictionary with:
            - success: Whether indexing succeeded (if wait_for_completion=True)
            - status: Current status message
            - message: Detailed status information
            - error: Error message if failed
    
    Notes:
        - Indexing can take several minutes depending on document volume
        - Requires LLM API access for entity extraction
        - After indexing, use query_graph to search the knowledge base
    
    Examples:
        # Full index rebuild
        trigger_index()
        
        # Incremental update (faster for adding new docs)
        trigger_index(update_mode=True)
        
        # Start indexing in background
        trigger_index(wait_for_completion=False)
    """
    if not INGEST_AVAILABLE:
        return {"error": "Ingest modules not available"}
    
    try:
        if wait_for_completion:
            success, message = trigger_graphrag_index(update_mode=update_mode)
            return {
                "success": success,
                "status": "completed" if success else "failed",
                "message": message,
            }
        else:
            # Start in background
            asyncio.create_task(asyncio.to_thread(
                trigger_graphrag_index, update_mode
            ))
            return {
                "status": "started",
                "message": "Indexing started in background. Use get_index_status to check progress.",
            }
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        return {"error": f"Indexing failed: {str(e)}"}


@mcp.tool()
async def get_index_status() -> dict[str, Any]:
    """Get the current status of GraphRAG indexing.
    
    Returns:
        Dictionary with:
            - status: Status message describing current state
            - is_complete: Whether indexing is complete and ready for queries
            - index_ready: Whether the knowledge graph exists and is queryable
            - files_count: Number of files in input directory
    """
    try:
        # Check if index exists
        index_ready, index_message = check_index_exists()
        
        # Get indexing status if available
        if INGEST_AVAILABLE:
            status_message, is_complete = get_indexing_status()
        else:
            status_message = "Ingest modules not available"
            is_complete = index_ready
        
        # Count input files
        files_count = 0
        if os.path.exists(config.input_dir):
            files_count = len([f for f in os.listdir(config.input_dir) 
                             if os.path.isfile(os.path.join(config.input_dir, f))
                             and not f.startswith('.')])
        
        return {
            "status": status_message,
            "is_complete": is_complete,
            "index_ready": index_ready,
            "index_message": index_message,
            "files_count": files_count,
            "output_dir": config.output_dir,
        }
    except Exception as e:
        return {"error": f"Status check failed: {str(e)}"}


@mcp.tool()
async def list_files() -> dict[str, Any]:
    """List all files in the VeritasGraph input directory.
    
    Returns:
        Dictionary with:
            - files: List of filename strings in the input directory
            - count: Total number of files
            - input_dir: Path to the input directory
    """
    try:
        if INGEST_AVAILABLE:
            files = list_input_files()
        else:
            files = []
            if os.path.exists(config.input_dir):
                files = [f for f in os.listdir(config.input_dir)
                        if os.path.isfile(os.path.join(config.input_dir, f))
                        and not f.startswith('.')]
        
        return {
            "files": files,
            "count": len(files),
            "input_dir": config.input_dir,
        }
    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}"}


@mcp.tool()
async def delete_file(filename: str) -> dict[str, Any]:
    """Delete a file from the VeritasGraph input directory.
    
    Args:
        filename: Name of the file to delete (not full path).
    
    Returns:
        Dictionary with:
            - success: Whether deletion succeeded
            - message: Status message
    
    Notes:
        - After deleting files, you may want to rebuild the index
        - This only deletes from input directory, not from the built index
    """
    if not INGEST_AVAILABLE:
        return {"error": "Ingest modules not available"}
    
    try:
        success, message = delete_input_file(filename)
        return {
            "success": success,
            "message": message,
        }
    except Exception as e:
        return {"error": f"Delete failed: {str(e)}"}


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Check the health and status of the VeritasGraph system.
    
    Returns comprehensive status information about:
    - GraphRAG availability
    - Index status
    - Configuration
    - Input/output directories
    
    Use this tool to verify the system is ready before making queries.
    
    Returns:
        Dictionary with:
            - status: Overall health status ("healthy", "degraded", "unavailable")
            - graphrag_available: Whether GraphRAG modules are loaded
            - ingest_available: Whether ingest modules are loaded
            - index_ready: Whether knowledge graph is built and queryable
            - index_message: Details about index status
            - output_dir: Path to output artifacts
            - input_dir: Path to input documents
            - files_count: Number of input documents
    """
    try:
        index_ready, index_message = check_index_exists()
        
        # Count input files
        files_count = 0
        if os.path.exists(config.input_dir):
            files_count = len([f for f in os.listdir(config.input_dir)
                             if os.path.isfile(os.path.join(config.input_dir, f))
                             and not f.startswith('.')])
        
        # Determine overall status
        if GRAPHRAG_AVAILABLE and index_ready:
            status = "healthy"
        elif GRAPHRAG_AVAILABLE:
            status = "degraded"  # GraphRAG available but no index
        else:
            status = "unavailable"
        
        return {
            "status": status,
            "graphrag_available": GRAPHRAG_AVAILABLE,
            "ingest_available": INGEST_AVAILABLE,
            "index_ready": index_ready,
            "index_message": index_message,
            "output_dir": config.output_dir,
            "input_dir": config.input_dir,
            "files_count": files_count,
            "config": {
                "community_level": config.default_community_level,
                "temperature": config.default_temperature,
                "response_type": config.default_response_type,
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@mcp.tool()
async def get_graph_stats() -> dict[str, Any]:
    """Get statistics about the VeritasGraph knowledge graph.
    
    Returns counts and information about:
    - Entities (nodes) in the graph
    - Relationships (edges) between entities
    - Communities (clusters of related entities)
    - Text units (source document chunks)
    
    Returns:
        Dictionary with:
            - entities_count: Number of entities in the graph
            - relationships_count: Number of relationships
            - communities_count: Number of community reports
            - text_units_count: Number of text chunks
            - top_entities: List of most connected entities
            - error: Error message if stats unavailable
    """
    index_ready, message = check_index_exists()
    if not index_ready:
        return {"error": f"Index not ready: {message}"}
    
    try:
        input_dir = config.output_dir
        
        # Load parquet files
        entity_df = pd.read_parquet(join(input_dir, "create_final_nodes.parquet"))
        relationship_df = pd.read_parquet(join(input_dir, "create_final_relationships.parquet"))
        report_df = pd.read_parquet(join(input_dir, "create_final_community_reports.parquet"))
        text_unit_df = pd.read_parquet(join(input_dir, "create_final_text_units.parquet"))
        
        # Get top entities by degree (if available)
        top_entities = []
        if 'title' in entity_df.columns:
            # Count relationships per entity
            if 'source' in relationship_df.columns and 'target' in relationship_df.columns:
                source_counts = relationship_df['source'].value_counts()
                target_counts = relationship_df['target'].value_counts()
                combined = source_counts.add(target_counts, fill_value=0).sort_values(ascending=False)
                top_entities = combined.head(10).index.tolist()
            else:
                top_entities = entity_df['title'].head(10).tolist() if len(entity_df) > 0 else []
        
        return {
            "entities_count": len(entity_df),
            "relationships_count": len(relationship_df),
            "communities_count": len(report_df),
            "text_units_count": len(text_unit_df),
            "top_entities": top_entities,
        }
    except Exception as e:
        return {"error": f"Failed to get stats: {str(e)}"}


# ============================================================================
# Simple HTTP API for Testing (non-MCP)
# ============================================================================

def create_test_api():
    """Create a simple FastAPI app for testing tools via REST."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    app = FastAPI(title="VeritasGraph MCP Test API", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    
    @app.get("/")
    async def root():
        return {"service": "VeritasGraph MCP Test API", "endpoints": ["/health", "/stats", "/query", "/files"]}
    
    @app.get("/health")
    async def api_health():
        return await health_check()
    
    @app.get("/stats")
    async def api_stats():
        return await get_graph_stats()
    
    @app.get("/files")
    async def api_files():
        return await list_files()
    
    @app.get("/status")
    async def api_status():
        return await get_index_status()
    
    @app.post("/query")
    async def api_query(query: str, search_type: str = "local", response_type: str = "Multiple Paragraphs"):
        return await query_graph(query=query, search_type=search_type, response_type=response_type)
    
    @app.post("/ingest")
    async def api_ingest(title: str, content: str, auto_index: bool = False):
        return await ingest_text(title=title, content=content, auto_index=auto_index)
    
    return app


# ============================================================================
# Server Entry Point
# ============================================================================

def main():
    """Main entry point for the VeritasGraph MCP Server."""
    parser = argparse.ArgumentParser(
        description="VeritasGraph MCP Server - GraphRAG knowledge graph as MCP tools"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport protocol (stdio for local, sse for MCP network, http for REST API testing)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE/HTTP transport (set via FASTMCP_HOST env var)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE/HTTP transport (set via FASTMCP_PORT env var)"
    )
    parser.add_argument(
        "--output-dir",
        help="Override output directory for GraphRAG artifacts"
    )
    parser.add_argument(
        "--input-dir",
        help="Override input directory for documents"
    )
    
    args = parser.parse_args()
    
    # Update config if directories specified
    global config
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.input_dir:
        config.input_dir = args.input_dir
    
    # Set FastMCP settings via environment variables for SSE transport
    if args.transport == "sse":
        os.environ["FASTMCP_HOST"] = args.host
        os.environ["FASTMCP_PORT"] = str(args.port)
    
    logger.info("="*60)
    logger.info("🚀 VeritasGraph MCP Server")
    logger.info("="*60)
    logger.info(f"Transport: {args.transport}")
    if args.transport == "sse":
        logger.info(f"SSE URL: http://{args.host}:{args.port}/sse")
    logger.info(f"GraphRAG Available: {GRAPHRAG_AVAILABLE}")
    logger.info(f"Ingest Available: {INGEST_AVAILABLE}")
    logger.info(f"Output Dir: {config.output_dir}")
    logger.info(f"Input Dir: {config.input_dir}")
    
    index_ready, index_msg = check_index_exists()
    logger.info(f"Index Ready: {index_ready} ({index_msg})")
    logger.info("="*60)
    
    # Run the appropriate server
    if args.transport == "http":
        # Simple REST API for testing with curl/Postman
        import uvicorn
        app = create_test_api()
        logger.info(f"Starting HTTP REST API at http://{args.host}:{args.port}")
        logger.info("Endpoints: /health, /stats, /files, /status, /query, /ingest")
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # MCP server
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
