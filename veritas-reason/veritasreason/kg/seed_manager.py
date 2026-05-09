"""
Seed Management Module

This module provides comprehensive initial data loading and seeding capabilities
for the VeritasReason framework, enabling bootstrap data loading for knowledge
graph construction.

Key Features:
    - Seed data loading from various sources
    - File-based seed data loading (JSON)
    - Data normalization and validation
    - Source tracking for seed data
    - Seed data management (clear, retrieve)

Main Classes:
    - SeedManager: Main seed data management engine

Example Usage:
    >>> from veritasreason.kg import SeedManager
    >>> manager = SeedManager()
    >>> manager.load_seed_data("source_1", entities)
    >>> manager.load_from_file("seed_data.json", source="file_source")
    >>> seed_data = manager.get_seed_data()

Author: VeritasReason Contributors
License: MIT
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class SeedManager:
    """
    Seed data management engine.

    This class provides seed data loading and management capabilities for
    knowledge graph construction, enabling bootstrap data loading from various
    sources with normalization and validation.

    Features:
        - Seed data loading from dictionaries and lists
        - File-based seed data loading (JSON)
        - Data normalization and ID generation
        - Source tracking and metadata
        - Seed data retrieval and management

    Example Usage:
        >>> manager = SeedManager()
        >>> manager.load_seed_data("source_1", entities)
        >>> manager.load_from_file("seed_data.json")
        >>> seed_data = manager.get_seed_data()
    """

    def __init__(self, **config):
        """
        Initialize seed manager.

        Sets up the manager with configuration and initializes seed data storage.

        Args:
            **config: Configuration options (currently unused)
        """
        self.logger = get_logger("seed_manager")
        self.config = config
        self.seed_data: List[Dict[str, Any]] = []

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("Seed manager initialized")

    def load_seed_data(self, source: str, data: Any) -> None:
        """
        Load seed data.

        This method loads seed data from various formats (list of entities,
        dict with "entities" key, or single entity dict), normalizes the data,
        ensures required fields (ID, source), and stores it with metadata.

        Args:
            source: Source identifier (e.g., "initial_data", "bootstrap")
            data: Seed data to load (list of entities, dict with "entities" key,
                 or single entity dict)
        """
        # Track seed data loading
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="kg",
            submodule="SeedManager",
            message=f"Loading seed data from source: {source}",
        )

        try:
            self.logger.info(f"Loading seed data from source: {source}")

            self.progress_tracker.update_tracking(
                tracking_id, message="Normalizing data format..."
            )
            # Normalize data format
            if isinstance(data, list):
                entities = data
            elif isinstance(data, dict):
                entities = data.get("entities", [data])
            else:
                entities = [data]

            self.progress_tracker.update_tracking(
                tracking_id, message=f"Processing {len(entities)} entities..."
            )
            # Validate and process entities
            processed_entities = []
            for entity in entities:
                if not isinstance(entity, dict):
                    self.logger.warning(
                        f"Skipping invalid entity format: {type(entity)}"
                    )
                    continue

                # Ensure entity has required fields
                if "id" not in entity and "entity_id" not in entity:
                    # Generate ID if missing
                    entity["id"] = f"{source}_{len(processed_entities)}"

                # Add source metadata
                entity["source"] = source
                entity["seed_data"] = True

                processed_entities.append(entity)

            self.seed_data.append(
                {
                    "source": source,
                    "entities": processed_entities,
                    "count": len(processed_entities),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.logger.info(f"Loaded {len(processed_entities)} entities from {source}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Loaded {len(processed_entities)} entities from {source}",
            )

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def load_from_file(self, file_path: str, source: Optional[str] = None) -> None:
        """
        Load seed data from file.

        This method loads seed data from a JSON file. The source identifier
        defaults to the file stem (filename without extension) if not provided.

        Args:
            file_path: Path to seed data file (must be JSON format)
            source: Optional source identifier (defaults to file stem)

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file format is unsupported
        """
        import json
        from pathlib import Path

        path = Path(file_path)
        source = source or path.stem

        if not path.exists():
            raise FileNotFoundError(f"Seed data file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix == ".json":
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {path.suffix}")

            self.load_seed_data(source, data)

        except Exception as e:
            self.logger.error(f"Error loading seed data from file: {e}")
            raise

    def get_seed_data(self) -> List[Dict[str, Any]]:
        """
        Get loaded seed data.

        This method retrieves all loaded seed data with their metadata.

        Returns:
            list: List of seed data entry dictionaries, each containing:
                - source: Source identifier
                - entities: List of entity dictionaries
                - count: Number of entities
                - timestamp: ISO timestamp when data was loaded
        """
        return self.seed_data

    def clear_seed_data(self) -> None:
        """
        Clear all seed data.

        This method removes all loaded seed data from the manager. Useful
        for resetting state or freeing memory.
        """
        self.seed_data = []
        self.logger.debug("Cleared all seed data")
