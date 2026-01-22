import logging
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


class PowerBIAuthenticationError(Exception):
    """Raised when authentication fails (token expired, invalid, etc.)"""
    pass


class PowerBIRestError(RuntimeError):
    """Raised when a Power BI REST API call fails with details."""
    pass


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
    
    def _handle_response(self, response: requests.Response, operation: str = "API call") -> None:
        """
        Handle API response and raise appropriate exceptions.
        Specifically detects authentication errors (401) for expired tokens.
        Extracts detailed error messages from Power BI API responses.
        """
        if response.status_code == 401:
            error_msg = f"Authentication failed for {operation}. Token may be expired or invalid."
            try:
                error_detail = response.json().get("error", {}).get("message", "")
                if error_detail:
                    error_msg += f" Details: {error_detail}"
            except:
                pass
            logger.error(error_msg)
            raise PowerBIAuthenticationError(error_msg)
        
        if response.status_code == 403:
            error_msg = f"Access denied for {operation}. You may not have permission to access this resource."
            logger.error(error_msg)
            raise PowerBIAuthenticationError(error_msg)
        
        # For 400 and other errors, extract detailed error message
        if response.status_code >= 400:
            error_msg = self._extract_error_message(response, operation)
            logger.error(error_msg)
            raise PowerBIRestError(error_msg)
    
    def _extract_error_message(self, response: requests.Response, operation: str) -> str:
        """Extract detailed error message from Power BI API response."""
        try:
            payload = response.json()
        except ValueError:
            return f"{operation} failed ({response.status_code}): {response.text}"
        
        # Try to get error from standard Power BI error format
        error = payload.get("error")
        if isinstance(error, dict):
            # Check for detailed error message
            message = error.get("message") or error.get("code")
            details = error.get("details", [])
            
            # Build comprehensive error message
            error_parts = []
            if message:
                error_parts.append(message)
            
            # Extract details if available (often contains the actual DAX error)
            for detail in details:
                if isinstance(detail, dict):
                    detail_msg = detail.get("message") or detail.get("detail")
                    if detail_msg and detail_msg not in error_parts:
                        error_parts.append(detail_msg)
            
            if error_parts:
                return f"{operation} failed ({response.status_code}): {' | '.join(error_parts)}"
        
        # Fallback to raw response
        return f"{operation} failed ({response.status_code}): {response.text[:500]}"

    def list_workspaces(self) -> List[Dict[str, Any]]:
        if not self.access_token:
            logger.error("Access token not set. Please provide an access token.")
            return []

        url = f"{self.BASE_URL}/groups"
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        self._handle_response(response, "list_workspaces")

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
        self._handle_response(response, "list_datasets")

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
            self._handle_response(response, "list_tables")
            
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

    def execute_dax_query(self, workspace_id: str, dataset_id: str, dax_query: str) -> Dict[str, Any]:
        """
        Execute a DAX query against a dataset using REST API
        
        Args:
            workspace_id: Workspace ID (GUID)
            dataset_id: Dataset ID (GUID)
            dax_query: DAX query string
            
        Returns:
            Dictionary with:
              - success: bool
              - rows: List of result rows (if success)
              - error: Error message (if failed)
              - query: The DAX query executed
        """
        if not self.access_token:
            logger.error("Access token not set. Please provide an access token.")
            return {
                "success": False,
                "error": "Access token not set. Please provide an access token using set_access_token tool.",
                "query": dax_query,
                "rows": []
            }

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
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=60)
            
            # Check for errors with detailed extraction
            if not response.ok:
                error_msg = self._extract_error_message(response, "execute_dax_query")
                logger.error(f"DAX query failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "query": dax_query,
                    "rows": [],
                    "status_code": response.status_code
                }
            
            result = response.json()
            if result.get("results") and len(result["results"]) > 0:
                tables = result["results"][0].get("tables", [])
                if tables and len(tables) > 0:
                    rows = tables[0].get("rows", [])
                    logger.info(f"Query returned {len(rows)} rows")
                    return {
                        "success": True,
                        "rows": rows,
                        "query": dax_query,
                        "row_count": len(rows)
                    }
            
            return {
                "success": True,
                "rows": [],
                "query": dax_query,
                "row_count": 0
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out after 60 seconds. The query may be too complex or the dataset too large.",
                "query": dax_query,
                "rows": []
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "query": dax_query,
                "rows": []
            }
