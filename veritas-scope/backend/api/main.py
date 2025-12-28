"""
Veritas-Scope API - FastAPI Backend
Interactive Reasoning Trace API for VeritasGraph.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

import pandas as pd
import tiktoken
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import models
from .models import (
    QueryRequest, QueryResponse, HealthCheck,
    NodeDetailsRequest, NodeDetailsResponse,
    ReasoningTraceGraph, GraphNode, GraphLink, ProvenanceInfo,
    NodeType, NodeStatus
)
from .trace_builder import build_reasoning_trace, ReasoningTraceBuilder

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Determine project root (adjust path as needed)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
GRAPHRAG_CONFIG_PATH = PROJECT_ROOT / "graphrag-ollama-config"

# Add graphrag to path
import sys
sys.path.insert(0, str(GRAPHRAG_CONFIG_PATH / "graphrag-ollama"))

# Import GraphRAG components
try:
    from graphrag.query.indexer_adapters import (
        read_indexer_entities, 
        read_indexer_reports,
        read_indexer_relationships,
        read_indexer_text_units,
    )
    from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
    from graphrag.query.structured_search.global_search.search import GlobalSearch
    from graphrag.query.llm.oai.chat_openai import ChatOpenAI
    from graphrag.query.llm.oai.typing import OpenaiApiType
    from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
    from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
    from graphrag.query.llm.oai.embedding import OpenAIEmbedding
    from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
    from graphrag.query.structured_search.local_search.search import LocalSearch
    from graphrag.vector_stores.lancedb import LanceDBVectorStore
    GRAPHRAG_AVAILABLE = True
except ImportError as e:
    log.warning(f"GraphRAG not available: {e}")
    GRAPHRAG_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    log.info("🚀 Starting Veritas-Scope API...")
    log.info(f"📁 Project root: {PROJECT_ROOT}")
    log.info(f"🔧 GraphRAG available: {GRAPHRAG_AVAILABLE}")
    yield
    log.info("👋 Shutting down Veritas-Scope API...")


# Create FastAPI app
app = FastAPI(
    title="Veritas-Scope API",
    description="Interactive Reasoning Trace API for VeritasGraph - Visualize Multi-Hop RAG Reasoning",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def list_output_folders() -> List[str]:
    """List available output folders."""
    output_dir = GRAPHRAG_CONFIG_PATH / "output"
    if not output_dir.exists():
        return []
    folders = [
        f.name for f in output_dir.iterdir() 
        if f.is_dir() and f.name[0].isdigit()
    ]
    return sorted(folders, reverse=True)


def get_input_dir(output_folder: str) -> Path:
    """Get the input directory for a given output folder."""
    return GRAPHRAG_CONFIG_PATH / "output" / output_folder / "artifacts"


async def perform_local_search_with_trace(
    query: str,
    input_dir: Path,
    community_level: int = 2,
    temperature: float = 0.5,
    response_type: str = "Multiple Paragraphs"
) -> tuple[str, dict]:
    """Perform local search and return both answer and context data."""
    
    api_key = os.environ.get("GRAPHRAG_API_KEY", "ollama")
    llm_model = os.environ.get("GRAPHRAG_LLM_MODEL", "llama3.1-12k")
    embedding_model = os.environ.get("GRAPHRAG_EMBEDDING_MODEL", "nomic-embed-text")
    api_llm_base = os.environ.get("GRAPHRAG_LLM_API_BASE", "http://localhost:11434/v1")
    api_embedding_base = os.environ.get("GRAPHRAG_EMBEDDING_API_BASE", "http://localhost:11434/v1")
    
    LANCEDB_URI = str(input_dir / "lancedb")
    
    # Load data
    entity_df = pd.read_parquet(input_dir / "create_final_nodes.parquet")
    entity_embedding_df = pd.read_parquet(input_dir / "create_final_entities.parquet")
    relationship_df = pd.read_parquet(input_dir / "create_final_relationships.parquet")
    report_df = pd.read_parquet(input_dir / "create_final_community_reports.parquet")
    text_unit_df = pd.read_parquet(input_dir / "create_final_text_units.parquet")
    
    entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)
    relationships = read_indexer_relationships(relationship_df)
    reports = read_indexer_reports(report_df, entity_df, community_level)
    text_units = read_indexer_text_units(text_unit_df)
    
    # Setup vector store
    description_embedding_store = LanceDBVectorStore(
        collection_name="entity_description_embeddings",
    )
    description_embedding_store.connect(db_uri=LANCEDB_URI)
    store_entity_semantic_embeddings(
        entities=entities, vectorstore=description_embedding_store
    )
    
    # Setup LLM
    llm = ChatOpenAI(
        api_key=api_key,
        api_base=api_llm_base,
        model=llm_model,
        api_type=OpenaiApiType.OpenAI,
        max_retries=10,
    )
    
    token_encoder = tiktoken.get_encoding("cl100k_base")
    
    text_embedder = OpenAIEmbedding(
        api_key=api_key,
        api_base=api_embedding_base,
        api_type=OpenaiApiType.OpenAI,
        model=embedding_model,
        deployment_name=embedding_model,
        max_retries=10,
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
        "conversation_history_max_turns": 5,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": True,  # Important: get full context data
        "embedding_vectorstore_key": EntityVectorStoreKey.ID,
        "max_tokens": 5000,
    }
    
    llm_params = {
        "max_tokens": 1500,
        "temperature": temperature,
    }
    
    # Create search engine
    search_engine = LocalSearch(
        llm=llm,
        context_builder=context_builder,
        token_encoder=token_encoder,
        llm_params=llm_params,
        context_builder_params=local_context_params,
        response_type=response_type,
    )
    
    # Execute search
    result = await search_engine.asearch(query)
    
    return result.response, result.context_data


async def perform_global_search_with_trace(
    query: str,
    input_dir: Path,
    community_level: int = 2,
    temperature: float = 0.5,
    response_type: str = "Multiple Paragraphs"
) -> tuple[str, dict]:
    """Perform global search and return both answer and context data."""
    
    api_key = os.environ.get("GRAPHRAG_API_KEY", "ollama")
    llm_model = os.environ.get("GRAPHRAG_LLM_MODEL", "llama3.1-12k")
    api_base = os.environ.get("GRAPHRAG_LLM_API_BASE", "http://localhost:11434/v1")
    
    # Load data
    entity_df = pd.read_parquet(input_dir / "create_final_nodes.parquet")
    report_df = pd.read_parquet(input_dir / "create_final_community_reports.parquet")
    entity_embedding_df = pd.read_parquet(input_dir / "create_final_entities.parquet")
    
    reports = read_indexer_reports(report_df, entity_df, community_level)
    entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)
    
    # Setup LLM
    llm = ChatOpenAI(
        api_key=api_key,
        api_base=api_base,
        model=llm_model,
        api_type=OpenaiApiType.OpenAI,
        max_retries=10,
    )
    
    token_encoder = tiktoken.get_encoding("cl100k_base")
    
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
        "max_tokens": 4000,
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
        max_data_tokens=5000,
        map_llm_params=map_llm_params,
        reduce_llm_params=reduce_llm_params,
        allow_general_knowledge=False,
        json_mode=True,
        context_builder_params=context_builder_params,
        concurrent_coroutines=1,
        response_type=response_type,
    )
    
    result = await search_engine.asearch(query)
    
    # Global search context is structured differently
    context_data = {
        "reports": pd.DataFrame([{
            "id": r.id,
            "title": r.title,
            "summary": r.summary,
            "rank": r.rank
        } for r in reports[:20]])
    }
    
    return result.response, context_data


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=HealthCheck)
async def root():
    """Root endpoint with health check."""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy" if GRAPHRAG_AVAILABLE else "degraded",
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


@app.get("/api/folders")
async def get_output_folders():
    """Get list of available output folders."""
    folders = list_output_folders()
    return {"folders": folders, "default": folders[0] if folders else None}


@app.post("/api/query", response_model=QueryResponse)
async def query_with_trace(request: QueryRequest):
    """
    Execute a query and return the answer with reasoning trace visualization data.
    
    This is the main endpoint for Veritas-Scope. It performs the GraphRAG query
    and returns both the answer and a visualization-ready reasoning trace graph.
    """
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="GraphRAG is not available. Please check your installation."
        )
    
    # Determine output folder
    output_folder = request.output_folder
    if not output_folder:
        folders = list_output_folders()
        if not folders:
            raise HTTPException(
                status_code=404,
                detail="No output folders found. Please run indexing first."
            )
        output_folder = folders[0]
    
    input_dir = get_input_dir(output_folder)
    if not input_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Input directory not found: {input_dir}"
        )
    
    start_time = datetime.utcnow()
    
    try:
        # Execute search based on type
        if request.query_type == "global":
            answer, context_data = await perform_global_search_with_trace(
                query=request.query,
                input_dir=input_dir,
                community_level=request.community_level,
                temperature=request.temperature,
                response_type=request.response_type
            )
        else:  # local
            answer, context_data = await perform_local_search_with_trace(
                query=request.query,
                input_dir=input_dir,
                community_level=request.community_level,
                temperature=request.temperature,
                response_type=request.response_type
            )
        
        # Build reasoning trace if requested
        reasoning_graph = None
        if request.include_graph:
            reasoning_graph = build_reasoning_trace(
                query=request.query,
                answer=answer,
                context_data=context_data
            )
        
        completion_time = (datetime.utcnow() - start_time).total_seconds()
        
        return QueryResponse(
            query=request.query,
            answer=answer,
            reasoning_graph=reasoning_graph,
            completion_time=completion_time,
            llm_calls=1,
            query_type=request.query_type
        )
        
    except Exception as e:
        log.exception(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@app.get("/api/graph/{output_folder}")
async def get_full_graph(
    output_folder: str,
    community_level: int = Query(default=2, ge=1, le=5)
):
    """
    Get the full knowledge graph for visualization.
    Returns all entities and relationships without a specific query.
    """
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG not available")
    
    input_dir = get_input_dir(output_folder)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    
    try:
        # Load all data
        entity_df = pd.read_parquet(input_dir / "create_final_nodes.parquet")
        entity_embedding_df = pd.read_parquet(input_dir / "create_final_entities.parquet")
        relationship_df = pd.read_parquet(input_dir / "create_final_relationships.parquet")
        
        entities = read_indexer_entities(entity_df, entity_embedding_df, community_level)
        relationships = read_indexer_relationships(relationship_df)
        
        # Build nodes
        nodes = []
        for entity in entities:
            nodes.append(GraphNode(
                id=entity.id,
                label=entity.title,
                type=NodeType.ENTITY,
                status=NodeStatus.INACTIVE,
                description=entity.description[:500] if entity.description else None,
                rank=entity.rank,
                community_id=entity.community_ids[0] if entity.community_ids else None,
                size=10 + (entity.rank or 1) * 2
            ))
        
        # Build links
        links = []
        entity_titles = {e.title.lower(): e.id for e in entities}
        
        for rel in relationships:
            source_id = entity_titles.get(rel.source.lower())
            target_id = entity_titles.get(rel.target.lower())
            
            if source_id and target_id:
                links.append(GraphLink(
                    id=rel.id,
                    source=source_id,
                    target=target_id,
                    relationship=rel.description[:100] if rel.description else "related_to",
                    weight=rel.weight
                ))
        
        return {
            "nodes": [n.model_dump() for n in nodes],
            "links": [l.model_dump() for l in links],
            "total_nodes": len(nodes),
            "total_links": len(links)
        }
        
    except Exception as e:
        log.exception(f"Error loading graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/node/details", response_model=NodeDetailsResponse)
async def get_node_details(request: NodeDetailsRequest):
    """Get detailed information about a specific node."""
    if not GRAPHRAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="GraphRAG not available")
    
    input_dir = get_input_dir(request.output_folder)
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail="Output folder not found")
    
    try:
        # Load data
        entity_df = pd.read_parquet(input_dir / "create_final_nodes.parquet")
        relationship_df = pd.read_parquet(input_dir / "create_final_relationships.parquet")
        text_unit_df = pd.read_parquet(input_dir / "create_final_text_units.parquet")
        
        # Find the entity
        entity_row = entity_df[entity_df['id'] == request.node_id]
        if entity_row.empty:
            entity_row = entity_df[entity_df['title'] == request.node_id]
        
        if entity_row.empty:
            raise HTTPException(status_code=404, detail="Node not found")
        
        entity = entity_row.iloc[0]
        
        # Build node details
        node = GraphNode(
            id=str(entity['id']),
            label=str(entity['title']),
            type=NodeType.ENTITY,
            status=NodeStatus.ACTIVE,
            description=str(entity.get('description', ''))[:1000],
            rank=float(entity.get('degree', 1)),
            metadata={
                "type": str(entity.get('type', '')),
                "community": str(entity.get('community', ''))
            }
        )
        
        # Find connected relationships
        entity_title = str(entity['title']).lower()
        related_rels = relationship_df[
            (relationship_df['source'].str.lower() == entity_title) |
            (relationship_df['target'].str.lower() == entity_title)
        ]
        
        relationships = []
        connected_nodes = []
        
        for _, rel in related_rels.iterrows():
            relationships.append(GraphLink(
                id=str(rel['id']),
                source=str(rel['source']),
                target=str(rel['target']),
                relationship=str(rel.get('description', 'related'))[:100],
                weight=float(rel.get('weight', 1.0))
            ))
            
            # Add connected node
            other_title = rel['target'] if rel['source'].lower() == entity_title else rel['source']
            other_row = entity_df[entity_df['title'].str.lower() == other_title.lower()]
            if not other_row.empty:
                other = other_row.iloc[0]
                connected_nodes.append(GraphNode(
                    id=str(other['id']),
                    label=str(other['title']),
                    type=NodeType.ENTITY,
                    status=NodeStatus.INACTIVE
                ))
        
        # Find source documents
        source_docs = []
        text_unit_ids = entity.get('text_unit_ids', [])
        if isinstance(text_unit_ids, str):
            text_unit_ids = text_unit_ids.split(',')
        
        for tu_id in text_unit_ids[:5]:
            tu_row = text_unit_df[text_unit_df['id'] == tu_id.strip()]
            if not tu_row.empty:
                tu = tu_row.iloc[0]
                source_docs.append(ProvenanceInfo(
                    source_id=str(tu['id']),
                    source_type="text_unit",
                    source_text=str(tu.get('text', ''))[:1000]
                ))
        
        return NodeDetailsResponse(
            node=node,
            connected_nodes=connected_nodes[:20],
            relationships=relationships[:20],
            source_documents=source_docs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error getting node details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run with: uvicorn api.main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
