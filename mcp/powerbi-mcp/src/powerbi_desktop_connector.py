"""
Power BI Desktop Connector
Connects to locally running Power BI Desktop instances via msmdsrv.exe
No authentication required - connects to localhost
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import psutil for process discovery
try:
    import psutil
    _psutil_available = True
except ImportError:
    logger.warning("psutil not installed - run: pip install psutil")
    _psutil_available = False

# Find and load ADOMD.NET
def _find_adomd_dll() -> Optional[Path]:
    """Find ADOMD.NET DLL from Power BI Desktop or SQL Server installations"""
    possible_paths = [
        # Power BI Desktop installation (preferred for Desktop connectivity)
        Path(r"C:\Program Files\Microsoft Power BI Desktop\bin"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\bin")),
        # Windows Store version
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")),
        # SQL Server installations
        Path(r"C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\150\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\160\SDK\Assemblies"),
        # SQL Server Update Cache
        Path(r"C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Update Cache"),
    ]

    # Check Update Cache for latest version
    update_cache = Path(r"C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Update Cache")
    if update_cache.exists():
        update_folders = list(update_cache.glob("*/GDR/x64"))
        if update_folders:
            possible_paths.insert(0, sorted(update_folders)[-1])

    for path in possible_paths:
        if path.exists():
            dll_file = path / "Microsoft.AnalysisServices.AdomdClient.dll"
            if dll_file.exists():
                return path
            # Also check subdirectories
            for dll in path.glob("**/Microsoft.AnalysisServices.AdomdClient.dll"):
                return dll.parent

    return None


# Initialize ADOMD.NET
_adomd_path = _find_adomd_dll()
_adomd_available = False

if _adomd_path:
    path_str = str(_adomd_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    if path_str not in os.environ.get('PATH', ''):
        os.environ['PATH'] = path_str + os.pathsep + os.environ.get('PATH', '')

    try:
        import clr
        clr.AddReference("Microsoft.AnalysisServices.AdomdClient")
        from Microsoft.AnalysisServices.AdomdClient import AdomdConnection, AdomdCommand
        _adomd_available = True
        logger.info(f"Loaded ADOMD.NET from: {_adomd_path}")
    except Exception as e:
        logger.error(f"Failed to load ADOMD.NET: {e}")
else:
    logger.warning("ADOMD.NET not found - Desktop connectivity unavailable")


class PowerBIDesktopConnector:
    """Connector for Power BI Desktop instances running locally"""

    def __init__(self):
        """Initialize the Desktop connector"""
        self.current_port: Optional[int] = None
        self.current_model_name: Optional[str] = None
        self.connection_string: Optional[str] = None
        self.current_rls_role: Optional[str] = None  # Active RLS role for testing

    @staticmethod
    def is_available() -> bool:
        """Check if Desktop connectivity is available"""
        return _adomd_available and _psutil_available

    def discover_instances(self) -> List[Dict[str, Any]]:
        """
        Discover all running Power BI Desktop instances

        Returns:
            List of instances with port, pid, and model info
        """
        if not _psutil_available:
            logger.error("psutil not available - cannot discover instances")
            return []

        instances = []

        try:
            # Find all msmdsrv.exe processes (Analysis Services engine)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'msmdsrv.exe':
                        pid = proc.info['pid']

                        # Find the listening port
                        port = None
                        try:
                            for conn in proc.connections():
                                if conn.status == 'LISTEN' and conn.laddr.ip in ('127.0.0.1', '0.0.0.0'):
                                    port = conn.laddr.port
                                    break
                        except (psutil.AccessDenied, psutil.ZombieProcess):
                            continue

                        if port:
                            # Try to get model name from the connection
                            model_name = self._get_model_name(port)

                            instances.append({
                                'pid': pid,
                                'port': port,
                                'model_name': model_name or f"Model on port {port}",
                                'connection_string': f"Data Source=localhost:{port}"
                            })
                            logger.info(f"Found Power BI Desktop instance: port={port}, pid={pid}, model={model_name}")

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            logger.error(f"Error discovering instances: {e}")

        return instances

    def _get_model_name(self, port: int) -> Optional[str]:
        """Get the model/database name from an instance"""
        if not _adomd_available:
            return None

        try:
            conn_str = f"Data Source=localhost:{port}"
            conn = AdomdConnection(conn_str)
            conn.Open()

            # Query for database name
            cmd = AdomdCommand("SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS", conn)
            reader = cmd.ExecuteReader()

            model_name = None
            if reader.Read():
                model_name = str(reader[0])

            reader.Close()
            conn.Close()
            return model_name

        except Exception as e:
            logger.debug(f"Could not get model name for port {port}: {e}")
            return None

    def connect(self, port: Optional[int] = None, rls_role: Optional[str] = None) -> bool:
        """
        Connect to a Power BI Desktop instance

        Args:
            port: Specific port to connect to. If None, connects to first available instance.
            rls_role: Optional RLS role name to test. When specified, queries will be
                      filtered according to that role's DAX filters.

        Returns:
            True if connection successful
        """
        if not _adomd_available:
            logger.error("ADOMD.NET not available - cannot connect")
            return False

        try:
            # If no port specified, find available instances
            if port is None:
                instances = self.discover_instances()
                if not instances:
                    logger.error("No Power BI Desktop instances found. Please open a .pbix file.")
                    return False
                port = instances[0]['port']
                logger.info(f"Auto-selected instance on port {port}")

            self.current_port = port
            self.current_rls_role = rls_role

            # Build connection string with optional RLS role
            self.connection_string = f"Data Source=localhost:{port}"
            if rls_role:
                # The Roles parameter applies RLS filters for testing
                self.connection_string += f";Roles={rls_role}"
                logger.info(f"RLS role '{rls_role}' will be applied to queries")

            # Test connection
            conn = AdomdConnection(self.connection_string)
            conn.Open()

            # Get model name
            self.current_model_name = self._get_model_name(port)

            conn.Close()
            rls_info = f" with RLS role '{rls_role}'" if rls_role else ""
            logger.info(f"Connected to Power BI Desktop on port {port}{rls_info}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Power BI Desktop: {e}")
            self.current_port = None
            self.connection_string = None
            self.current_rls_role = None
            return False

    def execute_dax(self, dax_query: str, max_rows: int = 1000) -> List[Dict[str, Any]]:
        """
        Execute a DAX query against the connected model

        Args:
            dax_query: DAX query string
            max_rows: Maximum rows to return

        Returns:
            Query results as list of dictionaries
        """
        if not self.connection_string:
            raise Exception("Not connected - call connect() first")

        try:
            conn = AdomdConnection(self.connection_string)
            conn.Open()

            cmd = AdomdCommand(dax_query, conn)
            reader = cmd.ExecuteReader()

            # Get column names
            columns = [reader.GetName(i) for i in range(reader.FieldCount)]

            # Fetch rows
            rows = []
            row_count = 0
            while reader.Read() and row_count < max_rows:
                row = {}
                for i, col in enumerate(columns):
                    value = reader[i]
                    # Convert .NET types to Python
                    if value is not None:
                        row[col] = str(value) if not isinstance(value, (int, float, bool)) else value
                    else:
                        row[col] = None
                rows.append(row)
                row_count += 1

            reader.Close()
            conn.Close()

            logger.info(f"DAX query returned {len(rows)} rows")
            return rows

        except Exception as e:
            logger.error(f"DAX query failed: {e}")
            raise Exception(f"DAX query failed: {e}")

    def list_tables(self) -> List[Dict[str, Any]]:
        """
        List all visible tables in the model

        Returns:
            List of tables with name and properties
        """
        # Use INFO.VIEW.TABLES() which works in Power BI Desktop
        query = """
            EVALUATE
            SELECTCOLUMNS(
                INFO.VIEW.TABLES(),
                "Name", [Name],
                "IsHidden", [IsHidden]
            )
        """

        try:
            results = self.execute_dax(query)
            tables = []
            for row in results:
                name = row.get('[Name]', row.get('Name', ''))
                is_hidden = row.get('[IsHidden]', row.get('IsHidden', False))
                # Filter system and hidden tables
                if name and not is_hidden and not name.startswith(('$', 'DateTableTemplate_', 'LocalDateTable_')):
                    tables.append({
                        'name': name,
                        'type': 'TABLE'
                    })
            return tables
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []

    def list_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        List columns for a specific table

        Args:
            table_name: Name of the table

        Returns:
            List of columns with name and type
        """
        # Use INFO.VIEW.COLUMNS() and filter by table
        # Column names: [Name], [Table], [DataType], [IsHidden], [Description]
        query = f"""
            EVALUATE
            SELECTCOLUMNS(
                FILTER(
                    INFO.VIEW.COLUMNS(),
                    [Table] = "{table_name}"
                ),
                "Name", [Name],
                "DataType", [DataType],
                "IsHidden", [IsHidden],
                "Description", [Description]
            )
        """

        try:
            results = self.execute_dax(query)
            columns = []
            for row in results:
                is_hidden = row.get('[IsHidden]', row.get('IsHidden', False))
                if not is_hidden:
                    columns.append({
                        'name': row.get('[Name]', row.get('Name', '')),
                        'type': row.get('[DataType]', row.get('DataType', '')),
                        'description': row.get('[Description]', row.get('Description', '')) or ''
                    })
            return columns
        except Exception as e:
            logger.error(f"Failed to list columns: {e}")
            return []

    def list_measures(self) -> List[Dict[str, Any]]:
        """
        List all measures in the model

        Returns:
            List of measures with name, table, and expression
        """
        # Use INFO.VIEW.MEASURES() - correct column names: [Table], not [TableName]
        query = """
            EVALUATE
            SELECTCOLUMNS(
                INFO.VIEW.MEASURES(),
                "Name", [Name],
                "Table", [Table],
                "Expression", [Expression],
                "IsHidden", [IsHidden]
            )
        """

        try:
            results = self.execute_dax(query)
            measures = []
            for row in results:
                is_hidden = row.get('[IsHidden]', row.get('IsHidden', False))
                if not is_hidden:
                    measures.append({
                        'name': row.get('[Name]', row.get('Name', '')),
                        'table': row.get('[Table]', row.get('Table', '')),
                        'expression': row.get('[Expression]', row.get('Expression', ''))
                    })
            return measures
        except Exception as e:
            logger.error(f"Failed to list measures: {e}")
            return []

    def list_relationships(self) -> List[Dict[str, Any]]:
        """
        List all relationships in the model

        Returns:
            List of relationships
        """
        # Use INFO.VIEW.RELATIONSHIPS() - correct column names
        query = """
            EVALUATE
            SELECTCOLUMNS(
                INFO.VIEW.RELATIONSHIPS(),
                "FromTable", [FromTable],
                "FromColumn", [FromColumn],
                "ToTable", [ToTable],
                "ToColumn", [ToColumn],
                "IsActive", [IsActive],
                "FromCardinality", [FromCardinality],
                "ToCardinality", [ToCardinality]
            )
        """

        try:
            results = self.execute_dax(query)
            relationships = []
            for row in results:
                from_card = row.get('[FromCardinality]', row.get('FromCardinality', ''))
                to_card = row.get('[ToCardinality]', row.get('ToCardinality', ''))
                cardinality = f"{from_card}:{to_card}" if from_card and to_card else ""

                relationships.append({
                    'from_table': row.get('[FromTable]', row.get('FromTable', '')),
                    'from_column': row.get('[FromColumn]', row.get('FromColumn', '')),
                    'to_table': row.get('[ToTable]', row.get('ToTable', '')),
                    'to_column': row.get('[ToColumn]', row.get('ToColumn', '')),
                    'is_active': row.get('[IsActive]', row.get('IsActive', True)),
                    'cardinality': cardinality
                })
            return relationships
        except Exception as e:
            logger.error(f"Failed to list relationships: {e}")
            return []

    def get_vertipaq_stats(self) -> Dict[str, Any]:
        """
        Get VertiPaq storage statistics

        Returns:
            Storage statistics for tables and columns
        """
        stats = {
            'tables': [],
            'total_size': 0
        }

        # Table sizes
        table_query = """
            SELECT
                [TableName],
                [RowCount],
                [TableSize]
            FROM $SYSTEM.DISCOVER_STORAGE_TABLE_COLUMNS
        """

        try:
            results = self.execute_dax(table_query)

            table_sizes = {}
            for row in results:
                table = row.get('TableName', row.get('[TableName]', ''))
                size = row.get('TableSize', row.get('[TableSize]', 0))
                if table:
                    if table not in table_sizes:
                        table_sizes[table] = {'name': table, 'size': 0, 'rows': 0}
                    table_sizes[table]['size'] += int(size) if size else 0

            stats['tables'] = list(table_sizes.values())
            stats['total_size'] = sum(t['size'] for t in stats['tables'])

        except Exception as e:
            logger.error(f"Failed to get VertiPaq stats: {e}")

        return stats

    def list_rls_roles(self) -> List[Dict[str, Any]]:
        """
        List all RLS (Row-Level Security) roles defined in the model

        Returns:
            List of roles with name and description
        """
        # Query for roles using INFO.VIEW - Note: This may not be available in all versions
        # Fallback to TMSCHEMA_ROLES DMV
        queries = [
            # Try INFO.VIEW.ROLES first (newer models)
            """
            EVALUATE
            SELECTCOLUMNS(
                INFO.VIEW.ROLES(),
                "Name", [Name],
                "Description", [Description]
            )
            """,
            # Fallback to DMV
            """
            SELECT [Name], [Description]
            FROM $SYSTEM.TMSCHEMA_ROLES
            """
        ]

        for query in queries:
            try:
                results = self.execute_dax(query)
                roles = []
                for row in results:
                    name = row.get('[Name]', row.get('Name', ''))
                    if name:
                        roles.append({
                            'name': name,
                            'description': row.get('[Description]', row.get('Description', '')) or ''
                        })
                if roles:
                    logger.info(f"Found {len(roles)} RLS role(s)")
                    return roles
            except Exception as e:
                logger.debug(f"Role query failed: {e}")
                continue

        logger.info("No RLS roles found in model")
        return []

    def set_rls_role(self, role_name: Optional[str]) -> bool:
        """
        Set or clear the active RLS role for subsequent queries

        Args:
            role_name: Name of the RLS role to apply, or None to clear

        Returns:
            True if successful
        """
        if not self.current_port:
            logger.error("Not connected - cannot set RLS role")
            return False

        try:
            # Rebuild connection string with new role
            self.current_rls_role = role_name
            self.connection_string = f"Data Source=localhost:{self.current_port}"

            if role_name:
                self.connection_string += f";Roles={role_name}"
                logger.info(f"RLS role set to '{role_name}'")
            else:
                logger.info("RLS role cleared - full data access")

            # Test the connection with new settings
            conn = AdomdConnection(self.connection_string)
            conn.Open()
            conn.Close()
            return True

        except Exception as e:
            logger.error(f"Failed to set RLS role '{role_name}': {e}")
            # Revert to no role
            self.current_rls_role = None
            self.connection_string = f"Data Source=localhost:{self.current_port}"
            return False

    def get_rls_status(self) -> Dict[str, Any]:
        """
        Get current RLS status

        Returns:
            Dictionary with RLS status information
        """
        return {
            'rls_active': self.current_rls_role is not None,
            'current_role': self.current_rls_role,
            'available_roles': self.list_rls_roles() if self.current_port else []
        }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive model information

        Returns:
            Dictionary with model metadata including tables, measures, relationships
        """
        if not self.connection_string:
            return {'error': 'Not connected'}

        info = {
            'model_name': self.current_model_name,
            'port': self.current_port,
            'rls_active': self.current_rls_role is not None,
            'current_rls_role': self.current_rls_role,
            'tables': [],
            'measures': [],
            'relationships': [],
            'table_count': 0,
            'measure_count': 0,
            'relationship_count': 0
        }

        try:
            # Get tables
            tables = self.list_tables()
            info['tables'] = [t.get('name') for t in tables]
            info['table_count'] = len(tables)

            # Get measures
            measures = self.list_measures()
            info['measures'] = [{'name': m.get('name'), 'table': m.get('table')} for m in measures]
            info['measure_count'] = len(measures)

            # Get relationships
            relationships = self.list_relationships()
            info['relationships'] = relationships
            info['relationship_count'] = len(relationships)

        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            info['error'] = str(e)

        return info

    def close(self):
        """Close the connection"""
        self.current_port = None
        self.current_model_name = None
        self.current_rls_role = None
        self.connection_string = None
        logger.info("Desktop connection closed")
