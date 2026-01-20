"""
Power BI TOM (Tabular Object Model) Connector
Provides write operations: rename, update, create, delete for tables, columns, measures
Uses Microsoft.AnalysisServices.Tabular for model modifications
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Find and load TOM DLLs
def _find_tom_dll() -> Optional[Path]:
    """Find Microsoft.AnalysisServices.Tabular.dll"""
    possible_paths = [
        # Power BI Desktop installation (preferred)
        Path(r"C:\Program Files\Microsoft Power BI Desktop\bin"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\bin")),
        # SQL Server installations
        Path(r"C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\150\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\160\SDK\Assemblies"),
        # Update Cache
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
            # Check for Tabular DLL
            tabular_dll = path / "Microsoft.AnalysisServices.Tabular.dll"
            if tabular_dll.exists():
                return path
            # Also check subdirectories
            for dll in path.glob("**/Microsoft.AnalysisServices.Tabular.dll"):
                return dll.parent

    return None


# Initialize TOM
_tom_path = _find_tom_dll()
_tom_available = False
TOM = None
TOMServer = None

if _tom_path:
    path_str = str(_tom_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    if path_str not in os.environ.get('PATH', ''):
        os.environ['PATH'] = path_str + os.pathsep + os.environ.get('PATH', '')

    try:
        import clr
        clr.AddReference("Microsoft.AnalysisServices.Tabular")
        import Microsoft.AnalysisServices.Tabular as TOM
        _tom_available = True
        logger.info(f"Loaded TOM from: {_tom_path}")
    except Exception as e:
        logger.warning(f"Failed to load TOM: {e}")
else:
    logger.warning("TOM DLL not found - write operations unavailable")


@dataclass
class RenameOperation:
    """Represents a rename operation"""
    old_name: str
    new_name: str
    table_name: Optional[str] = None  # For columns/measures


@dataclass
class OperationResult:
    """Result of a write operation"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class PowerBITOMConnector:
    """
    TOM Connector for Power BI Desktop write operations

    Provides:
    - Rename tables, columns, measures
    - Update measure expressions
    - Batch operations for bulk changes
    """

    def __init__(self):
        """Initialize the TOM connector"""
        self.server = None
        self.database = None
        self.model = None
        self.current_port: Optional[int] = None
        self.connection_string: Optional[str] = None
        self._changes_pending = False

    @staticmethod
    def is_available() -> bool:
        """Check if TOM is available"""
        return _tom_available

    def connect(self, port: int) -> bool:
        """
        Connect to Power BI Desktop instance via TOM

        Args:
            port: Port number of the Power BI Desktop instance

        Returns:
            True if connection successful
        """
        if not _tom_available:
            logger.error("TOM not available - cannot connect for write operations")
            return False

        try:
            self.current_port = port
            self.connection_string = f"localhost:{port}"

            # Create TOM Server and connect
            self.server = TOM.Server()
            self.server.Connect(self.connection_string)

            # Get the database (Power BI Desktop has one database)
            if self.server.Databases.Count > 0:
                self.database = self.server.Databases[0]
                self.model = self.database.Model
                logger.info(f"TOM connected to: {self.database.Name}")
                return True
            else:
                logger.error("No database found in Power BI Desktop")
                return False

        except Exception as e:
            logger.error(f"TOM connection failed: {e}")
            self.server = None
            self.database = None
            self.model = None
            return False

    def disconnect(self):
        """Disconnect from the model"""
        if self.server:
            try:
                self.server.Disconnect()
            except:
                pass
        self.server = None
        self.database = None
        self.model = None
        self.current_port = None
        self._changes_pending = False

    def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection"""
        if not self.model:
            logger.error("Not connected - call connect() first")
            return False
        return True

    def save_changes(self) -> OperationResult:
        """Save pending changes to the model"""
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            self.model.SaveChanges()
            self._changes_pending = False
            logger.info("Changes saved successfully")
            return OperationResult(True, "Changes saved successfully")
        except Exception as e:
            logger.error(f"Failed to save changes: {e}")
            return OperationResult(False, f"Failed to save changes: {e}")

    def discard_changes(self) -> OperationResult:
        """Discard pending changes"""
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            self.model.UndoLocalChanges()
            self._changes_pending = False
            return OperationResult(True, "Changes discarded")
        except Exception as e:
            return OperationResult(False, f"Failed to discard changes: {e}")

    # ==================== DEPENDENCY SCANNING ====================

    def _find_table_references(self, table_name: str) -> Dict[str, List[Dict[str, str]]]:
        """
        Find all references to a table in measures, calculated columns, and relationships

        Args:
            table_name: Name of the table to search for

        Returns:
            Dictionary with lists of references found
        """
        references = {
            "measures": [],
            "calculated_columns": [],
            "relationships": [],
            "hierarchies": []
        }

        if not self._ensure_connected():
            return references

        try:
            # Search patterns for table references in DAX
            # Tables are referenced as 'TableName'[Column] or TableName[Column] or just 'TableName'
            import re
            patterns = [
                rf"'{re.escape(table_name)}'\s*\[",  # 'TableName'[Column]
                rf"(?<!['\w]){re.escape(table_name)}\s*\[",  # TableName[Column] (not preceded by ' or word char)
                rf"RELATED\s*\(\s*'{re.escape(table_name)}'",  # RELATED('TableName'
                rf"RELATEDTABLE\s*\(\s*'{re.escape(table_name)}'",  # RELATEDTABLE('TableName'
                rf"CALCULATETABLE\s*\(\s*'{re.escape(table_name)}'",  # CALCULATETABLE('TableName'
                rf"ALL\s*\(\s*'{re.escape(table_name)}'",  # ALL('TableName'
                rf"VALUES\s*\(\s*'{re.escape(table_name)}'",  # VALUES('TableName'
                rf"FILTER\s*\(\s*'{re.escape(table_name)}'",  # FILTER('TableName'
            ]
            combined_pattern = "|".join(patterns)

            # Check all measures
            for table in self.model.Tables:
                for measure in table.Measures:
                    if measure.Expression and re.search(combined_pattern, measure.Expression, re.IGNORECASE):
                        references["measures"].append({
                            "name": measure.Name,
                            "table": table.Name,
                            "expression": measure.Expression[:200] + "..." if len(measure.Expression) > 200 else measure.Expression
                        })

                # Check calculated columns
                for column in table.Columns:
                    if hasattr(column, 'Expression') and column.Expression:
                        if re.search(combined_pattern, column.Expression, re.IGNORECASE):
                            references["calculated_columns"].append({
                                "name": column.Name,
                                "table": table.Name,
                                "expression": column.Expression[:200] + "..." if len(column.Expression) > 200 else column.Expression
                            })

            # Check relationships
            for relationship in self.model.Relationships:
                if relationship.FromTable.Name == table_name:
                    references["relationships"].append({
                        "name": relationship.Name if relationship.Name else f"{relationship.FromTable.Name} -> {relationship.ToTable.Name}",
                        "type": "from_table",
                        "from_table": relationship.FromTable.Name,
                        "to_table": relationship.ToTable.Name
                    })
                elif relationship.ToTable.Name == table_name:
                    references["relationships"].append({
                        "name": relationship.Name if relationship.Name else f"{relationship.FromTable.Name} -> {relationship.ToTable.Name}",
                        "type": "to_table",
                        "from_table": relationship.FromTable.Name,
                        "to_table": relationship.ToTable.Name
                    })

        except Exception as e:
            logger.error(f"Error scanning references: {e}")

        return references

    def _update_expression_table_references(self, expression: str, old_table: str, new_table: str) -> str:
        """
        Update table references in a DAX expression

        Args:
            expression: The DAX expression to update
            old_table: Old table name
            new_table: New table name

        Returns:
            Updated expression
        """
        import re

        # Replace 'OldTable'[Column] with 'NewTable'[Column]
        expression = re.sub(
            rf"'{re.escape(old_table)}'\s*\[",
            f"'{new_table}'[",
            expression,
            flags=re.IGNORECASE
        )

        # Replace OldTable[Column] with NewTable[Column] (unquoted)
        # Be careful not to replace inside quotes
        expression = re.sub(
            rf"(?<!['\w]){re.escape(old_table)}(?=\s*\[)",
            new_table,
            expression,
            flags=re.IGNORECASE
        )

        # Replace 'OldTable' in function calls
        expression = re.sub(
            rf"'{re.escape(old_table)}'(?=\s*[,\)])",
            f"'{new_table}'",
            expression,
            flags=re.IGNORECASE
        )

        return expression

    def scan_table_dependencies(self, table_name: str) -> OperationResult:
        """
        Scan for all dependencies on a table before renaming

        Args:
            table_name: Name of the table to scan

        Returns:
            OperationResult with dependency details
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        table = self.model.Tables.Find(table_name)
        if not table:
            return OperationResult(False, f"Table '{table_name}' not found")

        refs = self._find_table_references(table_name)

        total_refs = sum(len(v) for v in refs.values())

        return OperationResult(
            True,
            f"Found {total_refs} references to table '{table_name}'",
            {
                "table_name": table_name,
                "total_references": total_refs,
                "measures": refs["measures"],
                "calculated_columns": refs["calculated_columns"],
                "relationships": refs["relationships"],
                "warning": "⚠️ IMPORTANT: Renaming tables will update model references (measures, relationships) but CANNOT update report visuals. Visuals using this table will break and need manual fixing in Power BI Desktop."
            }
        )

    # ==================== TABLE OPERATIONS ====================

    def rename_table(self, old_name: str, new_name: str, update_references: bool = True) -> OperationResult:
        """
        Rename a table and optionally update all references in measures/calculations

        NOTE: This will update model-level references (measures, calculated columns,
        relationships) but CANNOT update report-level visual bindings. Visuals
        that use this table will need to be manually updated in Power BI Desktop.

        Args:
            old_name: Current table name
            new_name: New table name
            update_references: Whether to update references in measures/calculations (default: True)

        Returns:
            OperationResult with success status and details of updated references
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            table = self.model.Tables.Find(old_name)
            if not table:
                return OperationResult(False, f"Table '{old_name}' not found")

            # Check if new name already exists
            if self.model.Tables.Find(new_name):
                return OperationResult(False, f"Table '{new_name}' already exists")

            updated_refs = {
                "measures": [],
                "calculated_columns": []
            }

            # Update references in measures and calculated columns if requested
            if update_references:
                for t in self.model.Tables:
                    # Update measures
                    for measure in t.Measures:
                        if measure.Expression:
                            new_expr = self._update_expression_table_references(measure.Expression, old_name, new_name)
                            if new_expr != measure.Expression:
                                measure.Expression = new_expr
                                updated_refs["measures"].append(f"{t.Name}[{measure.Name}]")

                    # Update calculated columns
                    for column in t.Columns:
                        if hasattr(column, 'Expression') and column.Expression:
                            new_expr = self._update_expression_table_references(column.Expression, old_name, new_name)
                            if new_expr != column.Expression:
                                column.Expression = new_expr
                                updated_refs["calculated_columns"].append(f"{t.Name}[{column.Name}]")

            # Now rename the table
            table.Name = new_name
            self._changes_pending = True

            total_updated = len(updated_refs["measures"]) + len(updated_refs["calculated_columns"])

            logger.info(f"Table renamed: '{old_name}' -> '{new_name}', updated {total_updated} references")

            return OperationResult(
                True,
                f"Table renamed: '{old_name}' -> '{new_name}'. Updated {total_updated} model references.",
                {
                    "old_name": old_name,
                    "new_name": new_name,
                    "updated_measures": updated_refs["measures"],
                    "updated_calculated_columns": updated_refs["calculated_columns"],
                    "warning": "⚠️ Report visuals using this table will need manual updating in Power BI Desktop."
                }
            )

        except Exception as e:
            logger.error(f"Failed to rename table: {e}")
            return OperationResult(False, f"Failed to rename table: {e}")

    def batch_rename_tables(self, renames: List[Dict[str, str]], auto_save: bool = True, update_references: bool = True) -> OperationResult:
        """
        Batch rename multiple tables with automatic reference updates

        NOTE: This will update model-level references (measures, calculated columns,
        relationships) but CANNOT update report-level visual bindings. Visuals
        that use renamed tables will need to be manually updated in Power BI Desktop.

        Args:
            renames: List of {"old_name": "...", "new_name": "..."} dicts
            auto_save: Whether to auto-save changes (default: True)
            update_references: Whether to update references in measures/calculations (default: True)

        Returns:
            OperationResult with details of each rename and updated references
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        results = []
        success_count = 0
        fail_count = 0
        all_updated_measures = []
        all_updated_columns = []

        for rename in renames:
            old_name = rename.get("old_name")
            new_name = rename.get("new_name")

            if not old_name or not new_name:
                results.append({"old_name": old_name, "new_name": new_name, "success": False, "error": "Missing name"})
                fail_count += 1
                continue

            result = self.rename_table(old_name, new_name, update_references=update_references)
            results.append({
                "old_name": old_name,
                "new_name": new_name,
                "success": result.success,
                "error": result.message if not result.success else None,
                "updated_measures": result.details.get("updated_measures", []) if result.details else [],
                "updated_calculated_columns": result.details.get("updated_calculated_columns", []) if result.details else []
            })

            if result.success:
                success_count += 1
                if result.details:
                    all_updated_measures.extend(result.details.get("updated_measures", []))
                    all_updated_columns.extend(result.details.get("updated_calculated_columns", []))
            else:
                fail_count += 1

        # Auto-save if requested and there were successes
        if auto_save and success_count > 0:
            save_result = self.save_changes()
            if not save_result.success:
                return OperationResult(False, f"Renamed {success_count} tables but failed to save: {save_result.message}", {"results": results})

        total_ref_updates = len(all_updated_measures) + len(all_updated_columns)
        message = f"Renamed {success_count} table(s), {fail_count} failed. Updated {total_ref_updates} model references."

        return OperationResult(
            success_count > 0,
            message,
            {
                "results": results,
                "success_count": success_count,
                "fail_count": fail_count,
                "total_updated_measures": len(all_updated_measures),
                "total_updated_calculated_columns": len(all_updated_columns),
                "updated_measures": all_updated_measures,
                "updated_calculated_columns": all_updated_columns,
                "warning": "⚠️ IMPORTANT: Report visuals using these tables will need manual updating in Power BI Desktop. The model references (measures, calculated columns) have been automatically updated."
            }
        )

    # ==================== COLUMN OPERATIONS ====================

    def _update_expression_column_references(self, expression: str, table_name: str, old_column: str, new_column: str) -> str:
        """
        Update column references in a DAX expression

        Args:
            expression: The DAX expression to update
            table_name: Table containing the column
            old_column: Old column name
            new_column: New column name

        Returns:
            Updated expression
        """
        import re

        # Replace 'TableName'[OldColumn] with 'TableName'[NewColumn]
        expression = re.sub(
            rf"'{re.escape(table_name)}'\s*\[\s*{re.escape(old_column)}\s*\]",
            f"'{table_name}'[{new_column}]",
            expression,
            flags=re.IGNORECASE
        )

        # Replace TableName[OldColumn] with TableName[NewColumn] (unquoted table)
        expression = re.sub(
            rf"(?<!['\w]){re.escape(table_name)}\s*\[\s*{re.escape(old_column)}\s*\]",
            f"{table_name}[{new_column}]",
            expression,
            flags=re.IGNORECASE
        )

        return expression

    def rename_column(self, table_name: str, old_name: str, new_name: str, update_references: bool = True) -> OperationResult:
        """
        Rename a column and optionally update all references in measures/calculations

        Args:
            table_name: Name of the table containing the column
            old_name: Current column name
            new_name: New column name
            update_references: Whether to update references in measures/calculations (default: True)

        Returns:
            OperationResult with success status
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            table = self.model.Tables.Find(table_name)
            if not table:
                return OperationResult(False, f"Table '{table_name}' not found")

            column = table.Columns.Find(old_name)
            if not column:
                return OperationResult(False, f"Column '{old_name}' not found in table '{table_name}'")

            # Check if new name already exists
            if table.Columns.Find(new_name):
                return OperationResult(False, f"Column '{new_name}' already exists in table '{table_name}'")

            updated_refs = {"measures": [], "calculated_columns": []}

            # Update references in measures and calculated columns if requested
            if update_references:
                for t in self.model.Tables:
                    # Update measures
                    for measure in t.Measures:
                        if measure.Expression:
                            new_expr = self._update_expression_column_references(measure.Expression, table_name, old_name, new_name)
                            if new_expr != measure.Expression:
                                measure.Expression = new_expr
                                updated_refs["measures"].append(f"{t.Name}[{measure.Name}]")

                    # Update calculated columns
                    for col in t.Columns:
                        if hasattr(col, 'Expression') and col.Expression:
                            new_expr = self._update_expression_column_references(col.Expression, table_name, old_name, new_name)
                            if new_expr != col.Expression:
                                col.Expression = new_expr
                                updated_refs["calculated_columns"].append(f"{t.Name}[{col.Name}]")

            column.Name = new_name
            self._changes_pending = True

            total_updated = len(updated_refs["measures"]) + len(updated_refs["calculated_columns"])
            logger.info(f"Column renamed: '{table_name}'[{old_name}] -> [{new_name}], updated {total_updated} references")

            return OperationResult(
                True,
                f"Column renamed: '{table_name}'[{old_name}] -> [{new_name}]. Updated {total_updated} model references.",
                {
                    "table_name": table_name,
                    "old_name": old_name,
                    "new_name": new_name,
                    "updated_measures": updated_refs["measures"],
                    "updated_calculated_columns": updated_refs["calculated_columns"]
                }
            )

        except Exception as e:
            logger.error(f"Failed to rename column: {e}")
            return OperationResult(False, f"Failed to rename column: {e}")

    def batch_rename_columns(self, renames: List[Dict[str, str]], auto_save: bool = True, update_references: bool = True) -> OperationResult:
        """
        Batch rename multiple columns with automatic reference updates

        Args:
            renames: List of {"table_name": "...", "old_name": "...", "new_name": "..."} dicts
            auto_save: Whether to auto-save changes (default: True)
            update_references: Whether to update references in measures/calculations (default: True)

        Returns:
            OperationResult with details of each rename and updated references
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        results = []
        success_count = 0
        fail_count = 0
        all_updated_measures = []
        all_updated_columns = []

        for rename in renames:
            table_name = rename.get("table_name")
            old_name = rename.get("old_name")
            new_name = rename.get("new_name")

            if not all([table_name, old_name, new_name]):
                results.append({"table_name": table_name, "old_name": old_name, "new_name": new_name, "success": False, "error": "Missing required field"})
                fail_count += 1
                continue

            result = self.rename_column(table_name, old_name, new_name, update_references=update_references)
            results.append({
                "table_name": table_name,
                "old_name": old_name,
                "new_name": new_name,
                "success": result.success,
                "error": result.message if not result.success else None,
                "updated_measures": result.details.get("updated_measures", []) if result.details else [],
                "updated_calculated_columns": result.details.get("updated_calculated_columns", []) if result.details else []
            })

            if result.success:
                success_count += 1
                if result.details:
                    all_updated_measures.extend(result.details.get("updated_measures", []))
                    all_updated_columns.extend(result.details.get("updated_calculated_columns", []))
            else:
                fail_count += 1

        # Auto-save if requested
        if auto_save and success_count > 0:
            save_result = self.save_changes()
            if not save_result.success:
                return OperationResult(False, f"Renamed {success_count} columns but failed to save: {save_result.message}", {"results": results})

        total_ref_updates = len(all_updated_measures) + len(all_updated_columns)
        message = f"Renamed {success_count} column(s), {fail_count} failed. Updated {total_ref_updates} model references."

        return OperationResult(
            success_count > 0,
            message,
            {
                "results": results,
                "success_count": success_count,
                "fail_count": fail_count,
                "total_updated_measures": len(all_updated_measures),
                "total_updated_calculated_columns": len(all_updated_columns),
                "updated_measures": all_updated_measures,
                "updated_calculated_columns": all_updated_columns
            }
        )

    # ==================== MEASURE OPERATIONS ====================

    def _update_expression_measure_references(self, expression: str, old_measure: str, new_measure: str) -> str:
        """
        Update measure references in a DAX expression

        Args:
            expression: The DAX expression to update
            old_measure: Old measure name
            new_measure: New measure name

        Returns:
            Updated expression
        """
        import re

        # Replace [OldMeasure] with [NewMeasure] (measures are referenced without table in DAX)
        expression = re.sub(
            rf"\[\s*{re.escape(old_measure)}\s*\]",
            f"[{new_measure}]",
            expression,
            flags=re.IGNORECASE
        )

        return expression

    def rename_measure(self, old_name: str, new_name: str, table_name: Optional[str] = None, update_references: bool = True) -> OperationResult:
        """
        Rename a measure and optionally update all references in other measures/calculations

        Args:
            old_name: Current measure name
            new_name: New measure name
            table_name: Optional table name (if not provided, searches all tables)
            update_references: Whether to update references in other measures (default: True)

        Returns:
            OperationResult with success status
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            measure = None
            found_table = None

            if table_name:
                table = self.model.Tables.Find(table_name)
                if not table:
                    return OperationResult(False, f"Table '{table_name}' not found")
                measure = table.Measures.Find(old_name)
                found_table = table
            else:
                # Search all tables for the measure
                for table in self.model.Tables:
                    measure = table.Measures.Find(old_name)
                    if measure:
                        found_table = table
                        break

            if not measure:
                return OperationResult(False, f"Measure '{old_name}' not found")

            # Check if new name already exists in the same table
            if found_table.Measures.Find(new_name):
                return OperationResult(False, f"Measure '{new_name}' already exists in table '{found_table.Name}'")

            updated_refs = {"measures": [], "calculated_columns": []}

            # Update references in other measures and calculated columns if requested
            if update_references:
                for t in self.model.Tables:
                    # Update other measures
                    for m in t.Measures:
                        if m.Name != old_name and m.Expression:  # Don't update the measure being renamed
                            new_expr = self._update_expression_measure_references(m.Expression, old_name, new_name)
                            if new_expr != m.Expression:
                                m.Expression = new_expr
                                updated_refs["measures"].append(f"{t.Name}[{m.Name}]")

                    # Update calculated columns
                    for col in t.Columns:
                        if hasattr(col, 'Expression') and col.Expression:
                            new_expr = self._update_expression_measure_references(col.Expression, old_name, new_name)
                            if new_expr != col.Expression:
                                col.Expression = new_expr
                                updated_refs["calculated_columns"].append(f"{t.Name}[{col.Name}]")

            measure.Name = new_name
            self._changes_pending = True

            total_updated = len(updated_refs["measures"]) + len(updated_refs["calculated_columns"])
            logger.info(f"Measure renamed: '{old_name}' -> '{new_name}', updated {total_updated} references")

            return OperationResult(
                True,
                f"Measure renamed: '{old_name}' -> '{new_name}'. Updated {total_updated} references.",
                {
                    "old_name": old_name,
                    "new_name": new_name,
                    "table_name": found_table.Name,
                    "updated_measures": updated_refs["measures"],
                    "updated_calculated_columns": updated_refs["calculated_columns"]
                }
            )

        except Exception as e:
            logger.error(f"Failed to rename measure: {e}")
            return OperationResult(False, f"Failed to rename measure: {e}")

    def update_measure_expression(self, measure_name: str, new_expression: str, table_name: Optional[str] = None) -> OperationResult:
        """
        Update a measure's DAX expression

        Args:
            measure_name: Name of the measure
            new_expression: New DAX expression
            table_name: Optional table name

        Returns:
            OperationResult with success status
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            measure = None

            if table_name:
                table = self.model.Tables.Find(table_name)
                if not table:
                    return OperationResult(False, f"Table '{table_name}' not found")
                measure = table.Measures.Find(measure_name)
            else:
                for table in self.model.Tables:
                    measure = table.Measures.Find(measure_name)
                    if measure:
                        break

            if not measure:
                return OperationResult(False, f"Measure '{measure_name}' not found")

            old_expression = measure.Expression
            measure.Expression = new_expression
            self._changes_pending = True
            logger.info(f"Measure '{measure_name}' expression updated")
            return OperationResult(True, f"Measure '{measure_name}' expression updated", {"old_expression": old_expression})

        except Exception as e:
            logger.error(f"Failed to update measure: {e}")
            return OperationResult(False, f"Failed to update measure: {e}")

    def batch_rename_measures(self, renames: List[Dict[str, str]], auto_save: bool = True, update_references: bool = True) -> OperationResult:
        """
        Batch rename multiple measures with automatic reference updates

        Args:
            renames: List of {"old_name": "...", "new_name": "...", "table_name": "..." (optional)} dicts
            auto_save: Whether to auto-save changes (default: True)
            update_references: Whether to update references in other measures (default: True)

        Returns:
            OperationResult with details of each rename and updated references
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        results = []
        success_count = 0
        fail_count = 0
        all_updated_measures = []
        all_updated_columns = []

        for rename in renames:
            old_name = rename.get("old_name")
            new_name = rename.get("new_name")
            table_name = rename.get("table_name")

            if not old_name or not new_name:
                results.append({"old_name": old_name, "new_name": new_name, "success": False, "error": "Missing name"})
                fail_count += 1
                continue

            result = self.rename_measure(old_name, new_name, table_name, update_references=update_references)
            results.append({
                "old_name": old_name,
                "new_name": new_name,
                "table_name": table_name,
                "success": result.success,
                "error": result.message if not result.success else None,
                "updated_measures": result.details.get("updated_measures", []) if result.details else [],
                "updated_calculated_columns": result.details.get("updated_calculated_columns", []) if result.details else []
            })

            if result.success:
                success_count += 1
                if result.details:
                    all_updated_measures.extend(result.details.get("updated_measures", []))
                    all_updated_columns.extend(result.details.get("updated_calculated_columns", []))
            else:
                fail_count += 1

        # Auto-save if requested
        if auto_save and success_count > 0:
            save_result = self.save_changes()
            if not save_result.success:
                return OperationResult(False, f"Renamed {success_count} measures but failed to save: {save_result.message}", {"results": results})

        total_ref_updates = len(all_updated_measures) + len(all_updated_columns)
        message = f"Renamed {success_count} measure(s), {fail_count} failed. Updated {total_ref_updates} references."

        return OperationResult(
            success_count > 0,
            message,
            {
                "results": results,
                "success_count": success_count,
                "fail_count": fail_count,
                "total_updated_measures": len(all_updated_measures),
                "total_updated_calculated_columns": len(all_updated_columns),
                "updated_measures": all_updated_measures,
                "updated_calculated_columns": all_updated_columns
            }
        )

    def batch_update_measures(self, updates: List[Dict[str, str]], auto_save: bool = True) -> OperationResult:
        """
        Batch update multiple measure expressions

        Args:
            updates: List of {"measure_name": "...", "expression": "...", "table_name": "..." (optional)} dicts
            auto_save: Whether to auto-save changes

        Returns:
            OperationResult with details of each update
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        results = []
        success_count = 0
        fail_count = 0

        for update in updates:
            measure_name = update.get("measure_name")
            expression = update.get("expression")
            table_name = update.get("table_name")

            if not measure_name or not expression:
                results.append({"measure_name": measure_name, "success": False, "error": "Missing required field"})
                fail_count += 1
                continue

            result = self.update_measure_expression(measure_name, expression, table_name)
            results.append({
                "measure_name": measure_name,
                "success": result.success,
                "error": result.message if not result.success else None
            })

            if result.success:
                success_count += 1
            else:
                fail_count += 1

        # Auto-save if requested
        if auto_save and success_count > 0:
            save_result = self.save_changes()
            if not save_result.success:
                return OperationResult(False, f"Updated {success_count} measures but failed to save: {save_result.message}", {"results": results})

        message = f"Updated {success_count} measure(s), {fail_count} failed"
        return OperationResult(success_count > 0, message, {"results": results, "success_count": success_count, "fail_count": fail_count})

    # ==================== CREATE OPERATIONS ====================

    def create_measure(self, table_name: str, measure_name: str, expression: str,
                       format_string: Optional[str] = None, description: Optional[str] = None) -> OperationResult:
        """
        Create a new measure

        Args:
            table_name: Table to add the measure to
            measure_name: Name of the new measure
            expression: DAX expression
            format_string: Optional format string
            description: Optional description

        Returns:
            OperationResult with success status
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            table = self.model.Tables.Find(table_name)
            if not table:
                return OperationResult(False, f"Table '{table_name}' not found")

            # Check if measure already exists
            if table.Measures.Find(measure_name):
                return OperationResult(False, f"Measure '{measure_name}' already exists in table '{table_name}'")

            # Create new measure
            measure = TOM.Measure()
            measure.Name = measure_name
            measure.Expression = expression

            if format_string:
                measure.FormatString = format_string
            if description:
                measure.Description = description

            table.Measures.Add(measure)
            self._changes_pending = True

            logger.info(f"Created measure: '{measure_name}' in table '{table_name}'")
            return OperationResult(True, f"Created measure: '{measure_name}' in table '{table_name}'")

        except Exception as e:
            logger.error(f"Failed to create measure: {e}")
            return OperationResult(False, f"Failed to create measure: {e}")

    def delete_measure(self, measure_name: str, table_name: Optional[str] = None) -> OperationResult:
        """
        Delete a measure

        Args:
            measure_name: Name of the measure to delete
            table_name: Optional table name

        Returns:
            OperationResult with success status
        """
        if not self._ensure_connected():
            return OperationResult(False, "Not connected")

        try:
            measure = None
            found_table = None

            if table_name:
                table = self.model.Tables.Find(table_name)
                if not table:
                    return OperationResult(False, f"Table '{table_name}' not found")
                measure = table.Measures.Find(measure_name)
                found_table = table
            else:
                for table in self.model.Tables:
                    measure = table.Measures.Find(measure_name)
                    if measure:
                        found_table = table
                        break

            if not measure:
                return OperationResult(False, f"Measure '{measure_name}' not found")

            found_table.Measures.Remove(measure)
            self._changes_pending = True

            logger.info(f"Deleted measure: '{measure_name}'")
            return OperationResult(True, f"Deleted measure: '{measure_name}'")

        except Exception as e:
            logger.error(f"Failed to delete measure: {e}")
            return OperationResult(False, f"Failed to delete measure: {e}")

    # ==================== UTILITY METHODS ====================

    def get_model_summary(self) -> Dict[str, Any]:
        """Get a summary of the model"""
        if not self._ensure_connected():
            return {"error": "Not connected"}

        try:
            tables = []
            total_measures = 0
            total_columns = 0

            for table in self.model.Tables:
                table_info = {
                    "name": table.Name,
                    "columns": [col.Name for col in table.Columns],
                    "measures": [m.Name for m in table.Measures],
                    "column_count": table.Columns.Count,
                    "measure_count": table.Measures.Count
                }
                tables.append(table_info)
                total_measures += table.Measures.Count
                total_columns += table.Columns.Count

            return {
                "database_name": self.database.Name if self.database else None,
                "table_count": len(tables),
                "total_columns": total_columns,
                "total_measures": total_measures,
                "tables": tables,
                "changes_pending": self._changes_pending
            }

        except Exception as e:
            logger.error(f"Failed to get model summary: {e}")
            return {"error": str(e)}
