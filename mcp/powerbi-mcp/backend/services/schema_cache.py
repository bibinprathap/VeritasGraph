"""
Schema caching service for Power BI datasets
Caches dataset structure (tables, columns) to avoid repeated API calls
"""
import asyncio
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _token_hash(token: str) -> str:
    """Create a short hash of the token for comparison"""
    if not token:
        return ""
    return hashlib.md5(token.encode()).hexdigest()[:8]


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
    token_hash: str = ""  # Track which token was used for this cache
    
    def is_expired(self) -> bool:
        return time.time() - self.cached_at > self.ttl_seconds
    
    def is_token_changed(self, current_token: str) -> bool:
        """Check if token has changed since caching"""
        current_hash = _token_hash(current_token)
        return self.token_hash != current_hash


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
            current_token_hash = _token_hash(access_token or "")
            
            # Check existing cache
            if workspace_id in self._workspaces and not force_refresh:
                cache = self._workspaces[workspace_id]
                
                # IMPORTANT: Invalidate cache if token changed
                # This handles the case where previous token was expired
                if cache.is_token_changed(access_token or ""):
                    logger.info(f"Token changed for workspace {workspace_id}, invalidating cache")
                    # Don't use cached data - token changed
                elif not cache.is_expired():
                    # Also don't use cache if it's empty (likely from failed auth)
                    if cache.datasets and len(cache.datasets) > 0:
                        logger.debug(f"Using cached workspace info for {workspace_id} ({len(cache.datasets)} datasets)")
                        return cache
                    else:
                        logger.info(f"Cache has 0 datasets for {workspace_id}, refreshing")
            
            # Fetch fresh data
            logger.info(f"Fetching workspace info for {workspace_id} with token hash: {current_token_hash}")
            datasets = await mcp_client.list_datasets(workspace_id, access_token=access_token)
            
            # Check if we got an error response (string instead of list)
            if isinstance(datasets, str):
                logger.warning(f"list_datasets returned string (likely error): {datasets[:100]}")
                datasets = []
            
            # Only cache if we got valid data (non-empty)
            # Don't cache empty results as they might be from auth errors
            if datasets and len(datasets) > 0:
                cache = WorkspaceCache(
                    workspace_id=workspace_id,
                    workspace_name=workspace_id,
                    datasets=datasets,
                    schemas=self._workspaces.get(workspace_id, WorkspaceCache(workspace_id, "")).schemas,
                    token_hash=current_token_hash
                )
                self._workspaces[workspace_id] = cache
                logger.info(f"Cached {len(datasets)} datasets for workspace {workspace_id}")
                return cache
            else:
                # Return empty cache but DON'T store it
                logger.warning(f"Got 0 datasets for workspace {workspace_id}, not caching (possible auth error)")
                return WorkspaceCache(
                    workspace_id=workspace_id,
                    workspace_name=workspace_id,
                    datasets=[],
                    token_hash=current_token_hash
                )
    
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
            current_token_hash = _token_hash(access_token or "")
            
            # Check existing cache
            if workspace_id in self._workspaces:
                workspace = self._workspaces[workspace_id]
                
                # Check if token changed - invalidate all schemas for this workspace
                if workspace.is_token_changed(access_token or ""):
                    logger.info(f"Token changed, invalidating schema cache for workspace {workspace_id}")
                    workspace.schemas.clear()
                elif dataset_id in workspace.schemas and not force_refresh:
                    schema = workspace.schemas[dataset_id]
                    if not schema.is_expired():
                        # Don't use empty cached schemas
                        if schema.tables and len(schema.tables) > 0:
                            logger.debug(f"Using cached schema for dataset {dataset_id} ({len(schema.tables)} tables)")
                            return schema
                        else:
                            logger.info(f"Cached schema for {dataset_id} is empty, refreshing")
            
            # Fetch fresh schema
            logger.info(f"Fetching schema for dataset {dataset_id}")
            tables = await mcp_client.list_tables(workspace_id, dataset_id, access_token=access_token)
            
            # Check for error response
            if isinstance(tables, str):
                logger.warning(f"list_tables returned string (likely error): {tables[:100]}")
                tables = []
            
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
                    if isinstance(columns, list):
                        schema.tables[table_name] = columns
            
            # Only cache if we got valid data
            if schema.tables and len(schema.tables) > 0:
                if workspace_id not in self._workspaces:
                    self._workspaces[workspace_id] = WorkspaceCache(
                        workspace_id=workspace_id,
                        workspace_name=workspace_id,
                        token_hash=current_token_hash
                    )
                self._workspaces[workspace_id].schemas[dataset_id] = schema
                self._workspaces[workspace_id].token_hash = current_token_hash  # Update token hash
                logger.info(f"Cached schema for dataset {dataset_id} ({len(schema.tables)} tables)")
            else:
                logger.warning(f"Got 0 tables for dataset {dataset_id}, not caching")
            
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

