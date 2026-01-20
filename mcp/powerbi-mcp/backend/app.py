"""
FastAPI application entry point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.api.routes import router, get_mcp_client, shutdown_mcp_client
from backend.utils.logger import setup_logger

# Set up logging
logger = setup_logger("powerbi-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Starting Power BI Natural Language Query API...")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"MCP Server Path: {settings.MCP_SERVER_PATH}")
    
    # Connect to MCP server on startup
    try:
        client = await get_mcp_client()
        tools = await client.get_available_tools()
        logger.info(f"MCP Server connected successfully!")
        logger.info(f"Available tools ({len(tools)}): {', '.join(tools)}")
    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        logger.error("Make sure the MCP server path is correct and Python is available")
    
    yield
    
    # Disconnect on shutdown
    logger.info("Shutting down Power BI Natural Language Query API...")
    await shutdown_mcp_client()


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["Power BI"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Power BI Natural Language Query API",
        "version": settings.API_VERSION,
        "status": "running",
        "llm_provider": settings.LLM_PROVIDER,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

