"""
Schema caching service for Power BI datasets
Caches dataset structure (tables, columns) to avoid repeated API calls
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CachedSchema:
    """Cached schema for a dataset"""
    workspace_id: str
    dataset_id: str
    dataset_name: str
    tables: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # table_name -> columns
    cached_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600  # 1 hour default TTL
    
    def is_expired(self) -> bool:
        return time.time() - self.cached_at > self.ttl_seconds
    
    def get_schema_text(self) -> str:
        """Format schema as text for LLM prompts"""
        lines = [f"Dataset: {self.dataset_name}"]
        lines.append("Tables and Columns:")
        for table_name, columns in self.tables.items():
            col_names = [col.get("name", "Unknown") for col in columns]
            lines.append(f"  - '{table_name}': {', '.join(col_names)}")
        return "\n".join(lines)


@dataclass 
class WorkspaceCache:
    """Cached information for a workspace"""
    workspace_id: str
    workspace_name: str
    datasets: List[Dict[str, Any]] = field(default_factory=list)
    schemas: Dict[str, CachedSchema] = field(default_factory=dict)  # dataset_id -> schema
    cached_at: float = field(default_factory=time.time)
    ttl_seconds: int = 3600
    
    def is_expired(self) -> bool:
        return time.time() - self.cached_at > self.ttl_seconds


class SchemaCache:
    """
    Singleton cache for Power BI workspace schemas
    Thread-safe with async lock
    """
    _instance: Optional["SchemaCache"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._workspaces: Dict[str, WorkspaceCache] = {}
        self._initialized = True
        logger.info("SchemaCache initialized")
    
    async def get_workspace_info(
        self,
        mcp_client,
        workspace_id: str,
        access_token: Optional[str] = None,
        force_refresh: bool = False
    ) -> WorkspaceCache:
        """Get or fetch workspace information including datasets"""
        async with self._lock:
            if workspace_id in self._workspaces and not force_refresh:
                cache = self._workspaces[workspace_id]
                if not cache.is_expired():
                    logger.debug(f"Using cached workspace info for {workspace_id}")
                    return cache
            
            # Fetch fresh data
            logger.info(f"Fetching workspace info for {workspace_id}")
            datasets = await mcp_client.list_datasets(workspace_id, access_token=access_token)
            
            cache = WorkspaceCache(
                workspace_id=workspace_id,
                workspace_name=workspace_id,  # Could fetch name if needed
                datasets=datasets,
                schemas=self._workspaces.get(workspace_id, WorkspaceCache(workspace_id, "")).schemas
            )
            self._workspaces[workspace_id] = cache
            return cache
    
    async def get_dataset_schema(
        self,
        mcp_client,
        workspace_id: str,
        dataset_id: str,
        dataset_name: str = "",
        access_token: Optional[str] = None,
        force_refresh: bool = False
    ) -> CachedSchema:
        """Get or fetch schema for a specific dataset"""
        async with self._lock:
            # Check existing cache
            if workspace_id in self._workspaces:
                workspace = self._workspaces[workspace_id]
                if dataset_id in workspace.schemas and not force_refresh:
                    schema = workspace.schemas[dataset_id]
                    if not schema.is_expired():
                        logger.debug(f"Using cached schema for dataset {dataset_id}")
                        return schema
            
            # Fetch fresh schema
            logger.info(f"Fetching schema for dataset {dataset_id}")
            tables = await mcp_client.list_tables(workspace_id, dataset_id, access_token=access_token)
            
            schema = CachedSchema(
                workspace_id=workspace_id,
                dataset_id=dataset_id,
                dataset_name=dataset_name or dataset_id
            )
            
            # Fetch columns for each table
            for table in tables:
                table_name = table.get("name", "")
                if table_name:
                    columns = await mcp_client.list_columns(
                        workspace_id, dataset_id, table_name, access_token=access_token
                    )
                    schema.tables[table_name] = columns
            
            # Store in cache
            if workspace_id not in self._workspaces:
                self._workspaces[workspace_id] = WorkspaceCache(
                    workspace_id=workspace_id,
                    workspace_name=workspace_id
                )
            self._workspaces[workspace_id].schemas[dataset_id] = schema
            
            return schema
    
    async def get_all_schemas_for_workspace(
        self,
        mcp_client,
        workspace_id: str,
        access_token: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, CachedSchema]:
        """Get schemas for all datasets in a workspace"""
        workspace_info = await self.get_workspace_info(mcp_client, workspace_id, access_token=access_token, force_refresh=force_refresh)
        
        schemas = {}
        for dataset in workspace_info.datasets:
            dataset_id = dataset.get("id")
            dataset_name = dataset.get("name", dataset_id)
            if dataset_id:
                schema = await self.get_dataset_schema(
                    mcp_client, workspace_id, dataset_id, dataset_name, access_token=access_token, force_refresh=force_refresh
                )
                schemas[dataset_id] = schema
        
        return schemas
    
    def clear_cache(self, workspace_id: Optional[str] = None):
        """Clear cache for specific workspace or all"""
        if workspace_id:
            if workspace_id in self._workspaces:
                del self._workspaces[workspace_id]
                logger.info(f"Cleared cache for workspace {workspace_id}")
        else:
            self._workspaces.clear()
            logger.info("Cleared all schema cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_schemas = sum(
            len(ws.schemas) for ws in self._workspaces.values()
        )
        return {
            "workspaces_cached": len(self._workspaces),
            "total_schemas_cached": total_schemas,
            "workspace_ids": list(self._workspaces.keys())
        }


# Global singleton instance
schema_cache = SchemaCache()

