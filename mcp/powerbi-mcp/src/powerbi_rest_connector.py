import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class PowerBIRestConnector:
    BASE_URL = "https://api.powerbi.com/v1.0/myorg"

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize REST connector with user access token
        
        Args:
            access_token: OAuth2 access token from MCP client (user-based authentication)
        """
        self.access_token = access_token

    def set_access_token(self, access_token: str) -> None:
        """Set or update the access token"""
        self.access_token = access_token
        logger.info("Access token updated")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def list_workspaces(self) -> List[Dict[str, Any]]:
        if not self.access_token:
            logger.error("Access token not set. Please provide an access token.")
            return []

        url = f"{self.BASE_URL}/groups"
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        response.raise_for_status()

        return [
            {
                "id": ws["id"],
                "name": ws["name"],
                "type": ws.get("type"),
                "state": ws.get("state"),
            }
            for ws in response.json().get("value", [])
        ]

    def list_datasets(self, workspace_id: str) -> List[Dict[str, Any]]:
        if not self.access_token:
            logger.error("Access token not set. Please provide an access token.")
            return []

        url = f"{self.BASE_URL}/groups/{workspace_id}/datasets"
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        response.raise_for_status()

        return [
            {
                "id": ds["id"],
                "name": ds["name"],
                "configuredBy": ds.get("configuredBy"),
                "isRefreshable": ds.get("isRefreshable"),
            }
            for ds in response.json().get("value", [])
        ]

    def get_tables(self, workspace_id: str, dataset_id: str) -> List[Dict[str, Any]]:
        """
        Get tables from a dataset using REST API with COLUMNSTATISTICS() DAX query
        This works with semantic models (imported datasets), not just push datasets
        
        Args:
            workspace_id: Workspace ID (GUID)
            dataset_id: Dataset ID (GUID)
            
        Returns:
            List of tables with their columns
        """
        if not self.access_token:
            logger.error("Access token not set. Please provide an access token.")
            return []

        # Use COLUMNSTATISTICS() DAX function to get table and column metadata
        # This works with semantic models via REST API /executeQueries endpoint
        dax_query = "EVALUATE COLUMNSTATISTICS()"
        
        try:
            # Use groups/{workspace_id}/datasets/{dataset_id}/executeQueries format
            url = f"{self.BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
            
            payload = {
                "queries": [
                    {
                        "query": dax_query
                    }
                ],
                "serializerSettings": {
                    "includeNulls": True
                }
            }
            
            logger.info(f"Calling REST API: {url}")
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # Parse COLUMNSTATISTICS() response
            if result.get("results") and len(result["results"]) > 0:
                tables_data = result["results"][0].get("tables", [])
                if tables_data and len(tables_data) > 0:
                    rows = tables_data[0].get("rows", [])
                    
                    # Group by table name
                    tables_dict: Dict[str, Dict[str, Any]] = {}
                    
                    for row in rows:
                        table_name = row.get("[Table Name]", row.get("Table Name", ""))
                        column_name = row.get("[Column Name]", row.get("Column Name", ""))
                        
                        # Skip system tables and internal columns
                        if table_name.startswith("DateTableTemplate_") or table_name.startswith("$"):
                            continue
                        if column_name.startswith("RowNumber-"):
                            continue
                        
                        if table_name not in tables_dict:
                            tables_dict[table_name] = {
                                "name": table_name,
                                "description": "",
                                "columns": []
                            }
                        
                        # Add column if not already added
                        existing_column_names = [col["name"] for col in tables_dict[table_name]["columns"]]
                        if column_name not in existing_column_names:
                            tables_dict[table_name]["columns"].append({
                                "name": column_name,
                                "dataType": "Unknown",  # COLUMNSTATISTICS doesn't provide data type directly
                                "isHidden": False,
                                "formatString": "",
                                "cardinality": row.get("[Cardinality]", row.get("Cardinality")),
                                "min": row.get("[Min]", row.get("Min")),
                                "max": row.get("[Max]", row.get("Max")),
                            })
                    
                    logger.info(f"Found {len(tables_dict)} tables via COLUMNSTATISTICS()")
                    return list(tables_dict.values())
            
            return []
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to get tables via REST API COLUMNSTATISTICS: {e}")
            if e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error getting tables: {str(e)}")
            return []

    def execute_dax_query(self, workspace_id: str, dataset_id: str, dax_query: str) -> List[Dict[str, Any]]:
        """
        Execute a DAX query against a dataset using REST API
        
        Args:
            workspace_id: Workspace ID (GUID)
            dataset_id: Dataset ID (GUID)
            dax_query: DAX query string
            
        Returns:
            Query results as list of dictionaries
        """
        if not self.access_token:
            logger.error("Access token not set. Please provide an access token.")
            return []

        # Use groups/{workspace_id}/datasets/{dataset_id}/executeQueries format
        url = f"{self.BASE_URL}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
        
        payload = {
            "queries": [
                {
                    "query": dax_query
                }
            ],
            "serializerSettings": {
                "includeNulls": True
            }
        }
        
        logger.info(f"Executing DAX query: {dax_query[:100]}...")
        response = requests.post(url, headers=self._get_headers(), json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if result.get("results") and len(result["results"]) > 0:
            tables = result["results"][0].get("tables", [])
            if tables and len(tables) > 0:
                rows = tables[0].get("rows", [])
                logger.info(f"Query returned {len(rows)} rows")
                return rows  # Return raw rows directly
        
        return []
