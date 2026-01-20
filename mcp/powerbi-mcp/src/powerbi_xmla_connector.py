"""
Power BI XMLA Connector using pyadomd
Provides dynamic table discovery through XMLA endpoints
Requires: Windows + ADOMD.NET client libraries
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Add ADOMD.NET DLL path before importing pyadomd
def _add_adomd_to_path():
    """Find and add ADOMD.NET DLL directory to system path"""
    possible_paths = [
        # ADOMD.NET standalone installation (common location)
        Path(r"C:\Program Files\Microsoft.NET\ADOMD.NET\160"),
        Path(r"C:\Program Files\Microsoft.NET\ADOMD.NET\150"),
        Path(r"C:\Program Files\Microsoft.NET\ADOMD.NET\140"),
        Path(r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\160"),
        Path(r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\150"),
        Path(r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\140"),
        # NuGet package locations
        Path(os.path.expandvars(r"%USERPROFILE%\.nuget\packages\microsoft.analysisservices.adomdclient.retail.amd64")),
        Path(os.path.expandvars(r"%USERPROFILE%\.nuget\packages\microsoft.analysisservices.adomdclient")),
        # SQL Server Management Studio installations
        Path(r"C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\150\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\140\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\130\SDK\Assemblies"),
        # x86 versions
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\160\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\150\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\140\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\130\SDK\Assemblies"),
        # Power BI Desktop (if installed)
        Path(r"C:\Program Files\Microsoft Power BI Desktop\bin"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\bin")),
        # Windows Store Power BI
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")),
    ]

    # Search Update Cache for multiple SQL Server versions
    update_cache_paths = [
        Path(r"C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Update Cache"),
        Path(r"C:\Program Files\Microsoft SQL Server\150\Setup Bootstrap\Update Cache"),
    ]
    
    for cache_path in update_cache_paths:
        if cache_path.exists():
            update_folders = list(cache_path.glob("*/GDR/x64"))
            if update_folders:
                # Sort by folder name (KB number) and get the latest
                possible_paths.insert(0, sorted(update_folders)[-1])

    # Check common paths first
    for path in possible_paths:
        if path.exists():
            dll_file = path / "Microsoft.AnalysisServices.AdomdClient.dll"
            if dll_file.exists():
                logger.info(f"Found ADOMD.NET DLL at: {path}")
                # Add to system path
                path_str = str(path)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)
                if path_str not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = path_str + os.pathsep + os.environ.get('PATH', '')
                return True

    # If not found, try recursive search (slower but thorough)
    logger.warning("ADOMD.NET DLL not found in common paths, performing recursive search...")
    search_dirs = [
        Path(r"C:\Program Files\Microsoft.NET"),  # ADOMD.NET standalone installation
        Path(r"C:\Program Files (x86)\Microsoft.NET"),  # ADOMD.NET standalone installation (x86)
        Path(r"C:\Program Files\Microsoft SQL Server"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server"),
        Path(r"C:\Program Files\Microsoft Power BI Desktop"),
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            try:
                for dll_file in search_dir.rglob("Microsoft.AnalysisServices.AdomdClient.dll"):
                    dll_path = dll_file.parent
                    logger.info(f"Found ADOMD.NET DLL at: {dll_path} (via recursive search)")
                    path_str = str(dll_path)
                    if path_str not in sys.path:
                        sys.path.insert(0, path_str)
                    if path_str not in os.environ.get('PATH', ''):
                        os.environ['PATH'] = path_str + os.pathsep + os.environ.get('PATH', '')
                    return True
            except Exception as e:
                logger.debug(f"Recursive search error in {search_dir}: {e}")
                continue

    logger.error("ADOMD.NET client DLL not found")
    logger.error("Please install one of the following:")
    logger.error("1. SQL Server Management Studio (SSMS) - Recommended")
    logger.error("   Download: https://aka.ms/ssmsfullsetup")
    logger.error("2. Microsoft ADOMD.NET Redistributable")
    logger.error("   Download: https://docs.microsoft.com/sql/analysis-services/client-libraries")
    logger.error("3. Run 'python find_adomd.py' to search for existing installations")
    return False

# Configure ADOMD path
_adomd_available = _add_adomd_to_path()

# Now import pyadomd and .NET assemblies
if _adomd_available:
    try:
        from pyadomd import Pyadomd
        import clr
        clr.AddReference("Microsoft.AnalysisServices.AdomdClient")
        from Microsoft.AnalysisServices.AdomdClient import AdomdConnection, AdomdSchemaGuid
        logger.info("Successfully loaded ADOMD.NET assemblies")
    except Exception as e:
        logger.error(f"Failed to load ADOMD.NET: {e}")
        _adomd_available = False
else:
    Pyadomd = None
    AdomdSchemaGuid = None


class PowerBIXmlaConnector:
    """Power BI connector using XMLA endpoint with pyadomd"""

    def __init__(self, access_token: str):
        """
        Initialize connector with user access token
        
        Args:
            access_token: OAuth2 access token from MCP client (user-based authentication)
        """
        self.access_token = access_token
        self.connection_string = None
        self.connection = None
        self.workspace_name = None
        self.dataset_name = None
        self.effective_user: Optional[str] = None  # For RLS impersonation

    def set_access_token(self, access_token: str) -> None:
        """Set or update the access token"""
        self.access_token = access_token
        logger.info("Access token updated")

    def connect(self, workspace_name: str, dataset_name: str, effective_user: Optional[str] = None) -> bool:
        """
        Connect to Power BI dataset via XMLA endpoint

        Args:
            workspace_name: Name of the Power BI workspace
            dataset_name: Name of the dataset (semantic model)
            effective_user: Optional user email to impersonate for RLS.
                           When specified, queries are filtered by that user's RLS roles.

        Returns:
            True if connection successful
        """
        if not _adomd_available or Pyadomd is None:
            logger.error("ADOMD.NET libraries not available - cannot connect via XMLA")
            logger.error("Install SQL Server Management Studio or ADOMD.NET client libraries")
            return False

        try:
            self.workspace_name = workspace_name
            self.dataset_name = dataset_name
            self.effective_user = effective_user

            # Build XMLA endpoint URL
            # Format: powerbi://api.powerbi.com/v1.0/myorg/WorkspaceName
            xmla_endpoint = f"powerbi://api.powerbi.com/v1.0/myorg/{workspace_name}"

            # Build connection string with user-based bearer token authentication
            # IMPORTANT: Power BI XMLA endpoints do NOT support bearer tokens directly
            # XMLA endpoints require Service Principal authentication, not user bearer tokens
            # This will likely fail, and we should use REST API with DAX queries instead
            # However, we'll try it anyway in case the workspace has special configuration
            self.connection_string = (
                f"Provider=MSOLAP;"
                f"Data Source={xmla_endpoint};"
                f"Initial Catalog={dataset_name};"
                f"Password={self.access_token};"
            )
            
            logger.warning("Attempting XMLA connection with bearer token. "
                          "Note: Power BI XMLA endpoints typically require Service Principal authentication. "
                          "If this fails, REST API with DAX queries will be used as fallback.")

            # Add EffectiveUserName for RLS impersonation if specified
            if effective_user:
                self.connection_string += f"EffectiveUserName={effective_user};"
                logger.info(f"RLS enabled: Impersonating user '{effective_user}'")

            logger.info(f"Connecting to XMLA endpoint: {xmla_endpoint}")
            logger.info(f"Dataset: {dataset_name}")

            # Test connection
            try:
                with Pyadomd(self.connection_string) as conn:
                    # Check connection state
                    state = conn.conn.State
                    logger.info(f"Connection state: {state}")

                    # ConnectionState.Open can be 1 (int) or "Open" (string) depending on the library version
                    if state == 1 or str(state) == "Open" or str(state) == "1":
                        logger.info("Successfully connected to Power BI via XMLA")
                        return True
                    else:
                        logger.error(f"Connection state is not Open (State={state})")
                        return False

            except Exception as conn_error:
                logger.error(f"Pyadomd connection error: {str(conn_error)}")

                # Check for common error messages
                error_msg = str(conn_error).lower()
                if "login" in error_msg or "auth" in error_msg:
                    logger.error("Authentication failed - check Service Principal credentials")
                elif "catalog" in error_msg or "database" in error_msg:
                    logger.error("Dataset (catalog) not found - check dataset name")
                elif "workspace" in error_msg or "server" in error_msg:
                    logger.error("Workspace not found - check workspace name")

                import traceback
                logger.debug(traceback.format_exc())
                return False

        except Exception as e:
            logger.error(f"XMLA connection failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def discover_tables(self) -> List[Dict[str, Any]]:
        """
        Discover all tables in the dataset using XMLA schema discovery

        Returns:
            List of tables with their metadata
        """
        try:
            if not self.connection_string:
                logger.error("Not connected - call connect() first")
                return []

            logger.info("Discovering tables via XMLA...")

            tables = []

            with Pyadomd(self.connection_string) as pyadomd_conn:
                # Get the underlying ADOMD connection
                adomd_connection = pyadomd_conn.conn

                # Get schema dataset for tables
                tables_dataset = adomd_connection.GetSchemaDataSet(
                    AdomdSchemaGuid.Tables,
                    None
                )

                # Get the table containing schema information
                schema_table = tables_dataset.Tables[0]

                logger.info(f"Found {schema_table.Rows.Count} total tables in schema")

                # Get column names once
                column_names = [str(col.ColumnName) for col in schema_table.Columns]

                # Iterate through rows
                for row in schema_table.Rows:
                    table_name = str(row["TABLE_NAME"])

                    # Check for hidden status
                    is_hidden = False
                    if "TABLE_HIDDEN" in column_names:
                        try:
                            is_hidden = bool(row["TABLE_HIDDEN"])
                        except:
                            is_hidden = False

                    # Get description
                    description = ""
                    if "DESCRIPTION" in column_names:
                        try:
                            desc_value = row["DESCRIPTION"]
                            description = str(desc_value) if desc_value else ""
                        except:
                            description = ""

                    # Get table type
                    table_type = "TABLE"
                    if "TABLE_TYPE" in column_names:
                        try:
                            table_type = str(row["TABLE_TYPE"])
                        except:
                            table_type = "TABLE"

                    # Filter out system and hidden tables
                    system_prefixes = ("$", "DateTableTemplate_", "LocalDateTable_",
                                      "DBSCHEMA_", "MDSCHEMA_", "TMSCHEMA_",
                                      "DMSCHEMA_", "DISCOVER_")

                    if not table_name.startswith(system_prefixes) and not is_hidden:
                        tables.append({
                            "name": table_name,
                            "description": description or "No description available",
                            "type": table_type
                        })
                        logger.info(f"  - {table_name}")

            logger.info(f"Discovered {len(tables)} visible tables")
            return tables

        except Exception as e:
            logger.error(f"Table discovery failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get columns for a specific table using XMLA schema discovery

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table metadata and columns
        """
        try:
            if not self.connection_string:
                logger.error("Not connected - call connect() first")
                return {"table_name": table_name, "columns": []}

            logger.info(f"Getting schema for table: {table_name}")

            columns = []

            with Pyadomd(self.connection_string) as pyadomd_conn:
                adomd_connection = pyadomd_conn.conn

                # Get schema dataset for columns
                restrictions = [None, None, table_name, None]

                columns_dataset = adomd_connection.GetSchemaDataSet(
                    AdomdSchemaGuid.Columns,
                    restrictions
                )

                schema_table = columns_dataset.Tables[0]

                logger.info(f"Found {schema_table.Rows.Count} columns in table '{table_name}'")

                # Get column names once
                column_names = [str(col.ColumnName) for col in schema_table.Columns]

                for row in schema_table.Rows:
                    column_name = str(row["COLUMN_NAME"])

                    # Get data type
                    data_type = "Unknown"
                    if "DATA_TYPE" in column_names:
                        try:
                            data_type = str(row["DATA_TYPE"])
                        except:
                            data_type = "Unknown"

                    # Check if hidden
                    is_hidden = False
                    if "COLUMN_HIDDEN" in column_names:
                        try:
                            is_hidden = bool(row["COLUMN_HIDDEN"])
                        except:
                            is_hidden = False

                    # Get description
                    description = ""
                    if "DESCRIPTION" in column_names:
                        try:
                            desc_value = row["DESCRIPTION"]
                            description = str(desc_value) if desc_value else ""
                        except:
                            description = ""

                    # Only include visible columns
                    if not is_hidden:
                        columns.append({
                            "name": column_name,
                            "type": self._map_data_type(data_type),
                            "description": description or ""
                        })

            return {
                "table_name": table_name,
                "columns": columns
            }

        except Exception as e:
            logger.error(f"Failed to get schema for table '{table_name}': {str(e)}")
            return {"table_name": table_name, "columns": []}

    def _map_data_type(self, adomd_type: str) -> str:
        """Map ADOMD data types to readable names"""
        type_mapping = {
            "2": "Integer",
            "3": "Double",
            "5": "Float",
            "6": "Currency",
            "7": "DateTime",
            "8": "String",
            "11": "Boolean",
            "17": "Decimal",
            "130": "String",
            "131": "Decimal"
        }
        return type_mapping.get(str(adomd_type), f"Type_{adomd_type}")

    def execute_dax(self, dax_query: str) -> List[Dict[str, Any]]:
        """
        Execute a DAX query via XMLA

        Args:
            dax_query: DAX query string

        Returns:
            Query results as list of dictionaries
        """
        try:
            if not self.connection_string:
                logger.error("Not connected - call connect() first")
                return []

            logger.info(f"Executing DAX query: {dax_query[:100]}...")

            rows = []

            with Pyadomd(self.connection_string) as pyadomd_conn:
                # Execute query
                cursor = pyadomd_conn.cursor()
                cursor.execute(dax_query)

                # Get column names
                columns = [desc[0] for desc in cursor.description]

                # Fetch all rows
                for row in cursor.fetchall():
                    row_dict = {}
                    for i, value in enumerate(row):
                        row_dict[columns[i]] = value
                    rows.append(row_dict)

                logger.info(f"Query returned {len(rows)} rows")

            return rows

        except Exception as e:
            logger.error(f"DAX query execution failed: {str(e)}")
            raise Exception(f"DAX query failed: {str(e)}")

    def get_sample_data(self, table_name: str, num_rows: int = 5) -> List[Dict[str, Any]]:
        """
        Get sample data from a table

        Args:
            table_name: Name of the table
            num_rows: Number of rows to retrieve

        Returns:
            List of row dictionaries
        """
        try:
            # Quote table name if it contains spaces or special characters
            if ' ' in table_name or '&' in table_name or table_name.startswith('_'):
                quoted_name = f"'{table_name}'"
            else:
                quoted_name = table_name

            dax_query = f"EVALUATE TOPN({num_rows}, {quoted_name})"
            return self.execute_dax(dax_query)

        except Exception as e:
            logger.error(f"Failed to get sample data from '{table_name}': {str(e)}")
            return []

    def set_effective_user(self, user_email: Optional[str]) -> bool:
        """
        Set or clear the effective user for RLS impersonation

        Args:
            user_email: User email to impersonate, or None to clear

        Returns:
            True if successful
        """
        if not self.workspace_name or not self.dataset_name:
            logger.error("Not connected - cannot set effective user")
            return False

        return self.connect(
            self.workspace_name,
            self.dataset_name,
            effective_user=user_email
        )

    def get_rls_status(self) -> Dict[str, Any]:
        """
        Get current RLS status

        Returns:
            Dictionary with RLS status information
        """
        return {
            'rls_active': self.effective_user is not None,
            'effective_user': self.effective_user,
            'workspace': self.workspace_name,
            'dataset': self.dataset_name
        }

    def close(self):
        """Close the connection"""
        self.connection = None
        self.connection_string = None
        self.effective_user = None
        logger.info("Connection closed")
