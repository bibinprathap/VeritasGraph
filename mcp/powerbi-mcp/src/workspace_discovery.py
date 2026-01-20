"""
Dynamic Workspace Schema Discovery with Fuzzy Matching
Handles discovering all tables, columns, and values across a workspace
with support for typo tolerance using Levenshtein distance
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass, asdict

logger = logging.getLogger("workspace-discovery")


@dataclass
class ColumnInfo:
    """Represents a column in a table"""
    name: str
    type: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TableInfo:
    """Represents a table in a dataset"""
    name: str
    description: Optional[str] = None
    columns: List[ColumnInfo] = None

    def __post_init__(self):
        if self.columns is None:
            self.columns = []


@dataclass
class DatasetInfo:
    """Represents a dataset in a workspace"""
    id: str
    name: str
    description: Optional[str] = None
    tables: List[TableInfo] = None

    def __post_init__(self):
        if self.tables is None:
            self.tables = []


@dataclass
class WorkspaceSchema:
    """Complete workspace schema"""
    workspace_id: str
    workspace_name: str
    datasets: List[DatasetInfo] = None

    def __post_init__(self):
        if self.datasets is None:
            self.datasets = []


class FuzzyMatcher:
    """Implements fuzzy string matching using Levenshtein distance"""

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio (0-1) using SequenceMatcher"""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    @staticmethod
    def find_match(
        query: str,
        candidates: List[str],
        threshold: float = 0.7,
        max_results: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find fuzzy matches for a query string
        
        Args:
            query: Search term (may contain typos)
            candidates: List of candidate strings to match against
            threshold: Minimum similarity score (0-1)
            max_results: Maximum number of results to return
        
        Returns:
            List of (candidate, score) tuples, sorted by score descending
        """
        if not candidates:
            return []

        # Calculate similarity for each candidate
        scores = []
        for candidate in candidates:
            ratio = FuzzyMatcher.similarity_ratio(query, candidate)
            # Also consider edit distance as percentage
            max_len = max(len(query), len(candidate))
            edit_distance_ratio = 1 - (
                FuzzyMatcher.levenshtein_distance(query, candidate) / max_len
            ) if max_len > 0 else 1.0
            
            # Combine both metrics (average)
            combined_score = (ratio + edit_distance_ratio) / 2
            
            if combined_score >= threshold:
                scores.append((candidate, combined_score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:max_results]


class WorkspaceDiscoveryEngine:
    """Engine for discovering workspace schema and fuzzy searching values"""

    def __init__(self, rest_connector):
        """
        Initialize discovery engine
        
        Args:
            rest_connector: PowerBIRestConnector instance
        """
        self.rest_connector = rest_connector
        self._schema_cache: Dict[str, WorkspaceSchema] = {}
        self._column_values_cache: Dict[str, List[str]] = {}

    async def discover_workspace_schema(
        self,
        workspace_id: str,
        workspace_name: str = "",
        dataset_id: Optional[str] = None
    ) -> WorkspaceSchema:
        """
        Discover all tables and columns in a workspace or specific dataset
        
        Args:
            workspace_id: Workspace ID
            workspace_name: Optional workspace name
            dataset_id: Optional - if provided, only discover this dataset
        
        Returns:
            WorkspaceSchema with all discovered metadata
        """
        cache_key = f"{workspace_id}:{dataset_id or 'all'}"
        
        if cache_key in self._schema_cache:
            logger.info(f"Using cached schema for {cache_key}")
            return self._schema_cache[cache_key]

        schema = WorkspaceSchema(
            workspace_id=workspace_id,
            workspace_name=workspace_name or ""
        )

        try:
            # Get datasets
            if dataset_id:
                # Single dataset
                datasets = [
                    {"id": dataset_id, "name": ""}
                ]
            else:
                # All datasets in workspace
                logger.info(f"Listing datasets in workspace {workspace_id}")
                datasets = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.rest_connector.list_datasets,
                    workspace_id
                )

            for dataset in datasets:
                dataset_obj = DatasetInfo(
                    id=dataset.get("id", ""),
                    name=dataset.get("name", ""),
                    description=dataset.get("description")
                )

                # Get tables for this dataset
                logger.info(f"Listing tables for dataset {dataset_obj.name}")
                tables = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.rest_connector.list_tables,
                    workspace_id,
                    dataset_obj.id
                )

                for table in tables:
                    table_obj = TableInfo(
                        name=table.get("name", ""),
                        description=table.get("description")
                    )

                    # Get columns for this table
                    logger.info(f"Listing columns for table {table_obj.name}")
                    columns = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.rest_connector.list_columns,
                        workspace_id,
                        dataset_obj.id,
                        table_obj.name
                    )

                    for column in columns:
                        col_obj = ColumnInfo(
                            name=column.get("name", ""),
                            type=column.get("dataType"),
                            description=column.get("description")
                        )
                        table_obj.columns.append(col_obj)

                    dataset_obj.tables.append(table_obj)

                schema.datasets.append(dataset_obj)

            # Cache the schema
            self._schema_cache[cache_key] = schema
            logger.info(f"Schema cached for {cache_key}")

            return schema

        except Exception as e:
            logger.error(f"Error discovering schema: {e}")
            raise

    async def search_column_values(
        self,
        workspace_id: str,
        dataset_id: str,
        table_name: str,
        column_name: str,
        search_term: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for values in a column with fuzzy matching support
        
        Args:
            workspace_id: Workspace ID
            dataset_id: Dataset ID
            table_name: Table name
            column_name: Column name
            search_term: Search term (may contain typos)
            max_results: Maximum number of results
        
        Returns:
            Dict with exact matches, fuzzy matches, and suggestions
        """
        try:
            # Build DAX query to get distinct values
            dax_query = f"""
            EVALUATE
            TOPN(
                100,
                VALUES('{table_name}'[{column_name}])
            )
            """

            logger.info(f"Executing value discovery query for {table_name}[{column_name}]")

            # Execute query to get all values
            all_values = await asyncio.get_event_loop().run_in_executor(
                None,
                self.rest_connector.execute_dax,
                workspace_id,
                dataset_id,
                dax_query
            )

            # Parse results
            value_list = []
            if isinstance(all_values, str):
                try:
                    data = json.loads(all_values)
                    if "results" in data and len(data["results"]) > 0:
                        result_table = data["results"][0]
                        if "table" in result_table:
                            for row in result_table["table"]["rows"]:
                                if len(row) > 0:
                                    value_list.append(str(row[0]))
                except json.JSONDecodeError:
                    logger.error(f"Could not parse DAX results: {all_values}")

            if not value_list:
                return {
                    "exact_matches": [],
                    "fuzzy_matches": [],
                    "total_values": 0,
                    "search_term": search_term
                }

            # Search for exact matches first
            exact_matches = [
                v for v in value_list
                if v.lower() == search_term.lower()
            ]

            # Fuzzy search for typos
            fuzzy_matches = FuzzyMatcher.find_match(
                search_term,
                value_list,
                threshold=0.6,  # Lower threshold for typo tolerance
                max_results=max_results
            )

            # Remove exact matches from fuzzy results
            fuzzy_matches = [
                (match, score) for match, score in fuzzy_matches
                if match.lower() not in [e.lower() for e in exact_matches]
            ]

            return {
                "exact_matches": exact_matches,
                "fuzzy_matches": [
                    {"value": match, "confidence": round(score, 2)}
                    for match, score in fuzzy_matches
                ],
                "total_values": len(value_list),
                "search_term": search_term,
                "column": column_name,
                "table": table_name
            }

        except Exception as e:
            logger.error(f"Error searching column values: {e}")
            raise

    async def find_column_across_dataset(
        self,
        workspace_id: str,
        dataset_id: str,
        search_term: str
    ) -> List[Dict[str, Any]]:
        """
        Find which tables contain a column matching the search term
        
        Args:
            workspace_id: Workspace ID
            dataset_id: Dataset ID
            search_term: Column name search term (may contain typos)
        
        Returns:
            List of matching columns with table and dataset info
        """
        try:
            schema = await self.discover_workspace_schema(
                workspace_id,
                dataset_id=dataset_id
            )

            matches = []
            for dataset in schema.datasets:
                if dataset.id != dataset_id:
                    continue

                for table in dataset.tables:
                    column_names = [col.name for col in table.columns]
                    
                    # Try exact match first
                    exact_matches = FuzzyMatcher.find_match(
                        search_term,
                        column_names,
                        threshold=0.9,
                        max_results=5
                    )

                    for col_name, score in exact_matches:
                        col = next(
                            (c for c in table.columns if c.name == col_name),
                            None
                        )
                        if col:
                            matches.append({
                                "dataset": dataset.name,
                                "dataset_id": dataset.id,
                                "table": table.name,
                                "column": col.name,
                                "type": col.type,
                                "description": col.description,
                                "confidence": round(score, 2)
                            })

            # Sort by confidence
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            return matches

        except Exception as e:
            logger.error(f"Error finding column: {e}")
            raise

    def format_schema_for_llm(self, schema: WorkspaceSchema) -> str:
        """
        Format workspace schema as readable text for LLM context
        
        Args:
            schema: WorkspaceSchema object
        
        Returns:
            Formatted string representation
        """
        lines = [
            f"# Workspace Schema: {schema.workspace_name}",
            f"Workspace ID: {schema.workspace_id}",
            ""
        ]

        for dataset in schema.datasets:
            lines.append(f"## Dataset: {dataset.name}")
            lines.append(f"Dataset ID: {dataset.id}")
            if dataset.description:
                lines.append(f"Description: {dataset.description}")

            for table in dataset.tables:
                lines.append(f"  ### Table: {table.name}")
                if table.description:
                    lines.append(f"  Description: {table.description}")
                
                for col in table.columns:
                    col_type = f" ({col.type})" if col.type else ""
                    lines.append(f"    - {col.name}{col_type}")

            lines.append("")

        return "\n".join(lines)

    def clear_cache(self):
        """Clear cached schemas and values"""
        self._schema_cache.clear()
        self._column_values_cache.clear()
        logger.info("Discovery cache cleared")
