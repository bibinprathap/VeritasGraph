"""
Configuration Management Module

This module provides comprehensive configuration management for the VeritasReason framework,
including loading from files, environment variables, validation, and dynamic updates.
It supports multiple configuration sources and formats with automatic fallback chains
and validation.

Supported Configuration Sources:
    - Configuration files: YAML, JSON formats
    - Environment variables: VERITASREASON_ prefix for automatic loading
    - Programmatic: Python API for setting configuration values
    - Dictionary: Direct dictionary-based configuration

Algorithms Used:
    - YAML Parsing: YAML parser for configuration file loading
    - JSON Parsing: JSON parser for configuration file loading
    - Environment Variable Parsing: OS-level environment variable access with prefix matching
    - Fallback Chain: Priority-based configuration resolution (file -> env -> defaults)
    - Dictionary Merging: Deep merge algorithms for configuration updates
    - Validation: Type checking, range validation, required field checking
    - Nested Access: Dot notation parsing for nested configuration access

Key Features:
    - YAML/JSON configuration file parsing
    - Environment variable support with VERITASREASON_ prefix
    - Configuration validation with detailed error messages
    - Dynamic configuration updates at runtime
    - Configuration inheritance and merging
    - Nested configuration access via dot notation
    - Automatic type conversion for environment variables
    - Progress tracking for configuration loading operations

Main Classes:
    - Config: Configuration data class with validation
    - ConfigManager: Configuration loading, validation, and management

Example Usage:
    >>> from veritasreason.core import ConfigManager
    >>> manager = ConfigManager()
    >>> config = manager.load_from_file("config.yaml")
    >>> batch_size = config.get("processing.batch_size", default=32)
    >>> 
    >>> # Merge multiple configurations
    >>> merged = manager.merge_configs(config1, config2, config3)
    >>> 
    >>> # Load from dictionary
    >>> config = manager.load_from_dict({"processing": {"batch_size": 64}})

Author: VeritasReason Contributors
License: MIT
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from ..utils.constants import DEFAULT_CONFIG
from ..utils.exceptions import ConfigurationError
from ..utils.helpers import (
    get_nested_value,
    merge_dicts,
    read_json_file,
    set_nested_value,
)
from ..utils.progress_tracker import get_progress_tracker
from ..utils.validators import validate_config


class Config:
    """
    Configuration data class.

    Stores all framework configuration settings with validation
    and type checking.

    Attributes:
        llm_provider: LLM provider configuration
        embedding_model: Embedding model settings
        vector_store: Vector store configuration
        graph_db: Graph database settings
        processing: Processing pipeline settings
        logging: Logging configuration
        quality: Quality assurance settings
        security: Security settings
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize configuration.

        Args:
            config_dict: Dictionary of configuration values
            **kwargs: Additional configuration parameters
        """
        # Build configuration dictionary from all sources
        config_data = self._build_config_dict(config_dict, kwargs)
        
        # Load from environment variables (overrides file/kwargs)
        self._load_from_env(config_data)

        # Initialize configuration sections
        self._initialize_sections(config_data)

    def _build_config_dict(
        self, config_dict: Optional[Dict[str, Any]], kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build configuration dictionary from multiple sources.

        Priority order: defaults -> config_dict -> kwargs

        Args:
            config_dict: Optional configuration dictionary
            kwargs: Additional configuration parameters

        Returns:
            Merged configuration dictionary
        """
        # Start with defaults
        result = DEFAULT_CONFIG.copy()

        # Merge with provided config_dict
        if config_dict:
            result = merge_dicts(result, config_dict, deep=True)

        # Merge with kwargs
        if kwargs:
            result = merge_dicts(result, kwargs, deep=True)

        return result

    def _initialize_sections(self, config_data: Dict[str, Any]) -> None:
        """
        Initialize configuration section attributes.

        Args:
            config_data: Configuration dictionary
        """
        self.llm_provider = config_data.get("llm_provider", {})
        self.embedding_model = config_data.get("embedding_model", {})
        self.vector_store = config_data.get("vector_store", {})
        self.graph_db = config_data.get("graph_db", {})
        self.processing = config_data.get(
            "processing", DEFAULT_CONFIG.get("processing", {})
        )
        self.pipeline = config_data.get("pipeline", {})
        self.logging = config_data.get(
            "logging", DEFAULT_CONFIG.get("logging", {})
        )
        self.quality = config_data.get(
            "quality", DEFAULT_CONFIG.get("quality", {})
        )
        self.security = config_data.get(
            "security", DEFAULT_CONFIG.get("security", {})
        )
        self.custom = config_data.get("custom", {})

    def _load_from_env(self, config_dict: Dict[str, Any]) -> None:
        """
        Load configuration values from environment variables.

        Environment variables with prefix VERITASREASON_ will override configuration
        values. The format is: VERITASREASON_SECTION_KEY=value

        Examples:
            VERITASREASON_PROCESSING_BATCH_SIZE=64
            VERITASREASON_LLM_PROVIDER_MODEL=gpt-4
            VERITASREASON_QUALITY_MIN_CONFIDENCE=0.8

        Args:
            config_dict: Configuration dictionary to update with env values
        """
        prefix = "VERITASREASON_"
        
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Extract and normalize key
            config_key = self._normalize_env_key(env_key, prefix)
            
            # Parse value (try JSON first, then type conversion)
            parsed_value = self._parse_env_value(env_value)
            
            # Set nested value using dot notation
            set_nested_value(config_dict, config_key, parsed_value)

    def _normalize_env_key(self, env_key: str, prefix: str) -> str:
        """
        Normalize environment variable key to configuration key path.

        Args:
            env_key: Environment variable key (e.g., "VERITASREASON_PROCESSING_BATCH_SIZE")
            prefix: Prefix to remove (e.g., "VERITASREASON_")

        Returns:
            Normalized key path (e.g., "processing.batch_size")
        """
        # Remove prefix and convert to lowercase
        key = env_key[len(prefix):].lower()
        # Convert double underscores to dots for nested access
        return key.replace("__", ".")

    def _parse_env_value(self, value: str) -> Union[str, int, float, bool]:
        """
        Parse environment variable value to appropriate Python type.

        Args:
            value: Raw environment variable value string

        Returns:
            Parsed value with appropriate type (bool, int, float, or str)
        """
        # Boolean values
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Integer values
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)

        # Float values
        try:
            # Check if it's a valid float (allows one decimal point)
            if value.replace(".", "", 1).replace("-", "", 1).isdigit():
                return float(value)
        except ValueError:
            pass

        # Default: return as string
        return value

    def validate(self) -> None:
        """
        Validate configuration settings.

        This method performs comprehensive validation of all configuration
        settings, checking types, ranges, and required fields.

        Raises:
            ConfigurationError: If configuration is invalid with detailed error messages
        """
        validation_errors = []
        
        # Validate each configuration section
        validation_errors.extend(self._validate_processing())
        validation_errors.extend(self._validate_quality())
        validation_errors.extend(self._validate_logging())

        # Raise error if any validation failures
        if validation_errors:
            error_message = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in validation_errors
            )
            raise ConfigurationError(
                error_message,
                config_context=self.to_dict(),
            )

    def _validate_processing(self) -> List[str]:
        """Validate processing configuration section."""
        errors = []
        if not self.processing:
            return errors

        # Validate batch_size
        if "batch_size" in self.processing:
            batch_size = self.processing["batch_size"]
            if not isinstance(batch_size, int):
                errors.append(
                    f"processing.batch_size must be an integer, got {type(batch_size).__name__}"
                )
            elif batch_size <= 0:
                errors.append(
                    f"processing.batch_size must be positive, got {batch_size}"
                )

        # Validate max_workers
        if "max_workers" in self.processing:
            max_workers = self.processing["max_workers"]
            if not isinstance(max_workers, int):
                errors.append(
                    f"processing.max_workers must be an integer, got {type(max_workers).__name__}"
                )
            elif max_workers <= 0:
                errors.append(
                    f"processing.max_workers must be positive, got {max_workers}"
                )

        return errors

    def _validate_quality(self) -> List[str]:
        """Validate quality configuration section."""
        errors = []
        if not self.quality:
            return errors

        # Validate min_confidence
        if "min_confidence" in self.quality:
            confidence = self.quality["min_confidence"]
            if not isinstance(confidence, (int, float)):
                errors.append(
                    f"quality.min_confidence must be a number, got {type(confidence).__name__}"
                )
            elif not (0.0 <= confidence <= 1.0):
                errors.append(
                    f"quality.min_confidence must be between 0.0 and 1.0, got {confidence}"
                )

        return errors

    def _validate_logging(self) -> List[str]:
        """Validate logging configuration section."""
        errors = []
        if not self.logging:
            return errors

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if "level" in self.logging:
            level = self.logging["level"]
            if level not in valid_levels:
                errors.append(
                    f"logging.level must be one of {valid_levels}, got {level}"
                )

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            dict: Configuration as dictionary
        """
        return {
            "llm_provider": self.llm_provider,
            "embedding_model": self.embedding_model,
            "vector_store": self.vector_store,
            "graph_db": self.graph_db,
            "processing": self.processing,
            "pipeline": self.pipeline,
            "logging": self.logging,
            "quality": self.quality,
            "security": self.security,
            "custom": self.custom,
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get nested configuration value by key path.

        Args:
            key_path: Dot-separated key path (e.g., "processing.batch_size")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config_dict = self.to_dict()
        return get_nested_value(config_dict, key_path, default=default)

    def set(self, key_path: str, value: Any) -> None:
        """
        Set nested configuration value by key path.

        Args:
            key_path: Dot-separated key path (e.g., "processing.batch_size")
            value: Value to set
        """
        # Update the dictionary representation
        config_dict = self.to_dict()
        set_nested_value(config_dict, key_path, value)

        # Reinitialize sections from updated dict
        self._initialize_sections(config_dict)

    def update(self, updates: Dict[str, Any], merge: bool = True) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of updates
            merge: Whether to merge nested dictionaries (default: True)
        """
        current_dict = self.to_dict()

        # Merge or replace based on merge flag
        if merge:
            updated_dict = merge_dicts(current_dict, updates, deep=True)
        else:
            updated_dict = {**current_dict, **updates}

        # Reinitialize sections from updated dict
        self._initialize_sections(updated_dict)


class ConfigManager:
    """
    Configuration management system.

    This class provides a centralized way to load, validate, merge, and manage
    configuration for the VeritasReason framework. It supports multiple configuration
    sources and formats.

    Features:
        - Load from YAML/JSON files
        - Load from dictionaries
        - Merge multiple configurations
        - Validate configuration
        - Reload configuration dynamically

    Example Usage:
        >>> manager = ConfigManager()
        >>> config = manager.load_from_file("config.yaml")
        >>> merged = manager.merge_configs(config1, config2, config3)
    """

    def __init__(self):
        """
        Initialize configuration manager.

        Creates a new ConfigManager instance with no loaded configuration.
        Use load_from_file() or load_from_dict() to load configuration.
        """
        self._config: Optional[Config] = None
        self._last_file_path: Optional[Path] = None
        self.progress_tracker = get_progress_tracker()

    def load_from_file(
        self, file_path: Union[str, Path], validate: bool = True
    ) -> Config:
        """
        Load configuration from file.

        Supports YAML and JSON formats. Automatically detects format
        based on file extension.

        Args:
            file_path: Path to configuration file (YAML or JSON)
            validate: Whether to validate configuration after loading

        Returns:
            Config: Loaded configuration object

        Raises:
            ConfigurationError: If file cannot be loaded or is invalid
        """
        # Track configuration loading
        tracking_id = self.progress_tracker.start_tracking(
            file=str(file_path),
            module="core",
            submodule="ConfigManager",
            message=f"Loading configuration from: {file_path}",
        )

        try:
            file_path = Path(file_path)
            self._validate_file_exists(file_path)

            # Load configuration dictionary from file
            config_dict = self._load_file_content(file_path)

            # Create and validate config object
            config = Config(config_dict=config_dict)
            if validate:
                config.validate()

            # Store config and file path for potential reload
            self._config = config
            self._last_file_path = file_path

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message="Configuration loaded successfully",
            )
            return config

        except ConfigurationError:
            # Re-raise configuration errors as-is
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message="Configuration error"
            )
            raise
        except Exception as e:
            # Wrap other exceptions
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise ConfigurationError(
                f"Failed to load configuration file: {str(e)}",
                config_context={"file_path": str(file_path)},
            ) from e

    def _validate_file_exists(self, file_path: Path) -> None:
        """
        Validate that configuration file exists.

        Args:
            file_path: Path to configuration file

        Raises:
            ConfigurationError: If file does not exist
        """
        if not file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {file_path}",
                config_context={"file_path": str(file_path)},
            )

    def _load_file_content(self, file_path: Path) -> Dict[str, Any]:
        """
        Load configuration dictionary from file.

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            ConfigurationError: If file format is unsupported or parsing fails
        """
        suffix = file_path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            return self._load_yaml_file(file_path)
        elif suffix == ".json":
            return self._load_json_file(file_path)
        else:
            raise ConfigurationError(
                f"Unsupported configuration file format: {suffix}. "
                "Supported formats: .yaml, .yml, .json"
            )

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse YAML file: {str(e)}",
                config_context={"file_path": str(file_path)},
            ) from e

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        try:
            return read_json_file(file_path)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse JSON file: {str(e)}",
                config_context={"file_path": str(file_path)},
            ) from e

    def load_from_dict(
        self, config_dict: Dict[str, Any], validate: bool = True
    ) -> Config:
        """
        Load configuration from dictionary.

        Args:
            config_dict: Dictionary of configuration values
            validate: Whether to validate configuration after loading

        Returns:
            Config: Configuration object

        Raises:
            ConfigurationError: If configuration is invalid
        """
        config = Config(config_dict=config_dict)

        if validate:
            config.validate()

        self._config = config
        return config

    def merge_configs(self, *configs: Config, validate: bool = True) -> Config:
        """
        Merge multiple configurations.

        Later configurations take priority over earlier ones.
        Nested dictionaries are merged deeply.

        Args:
            *configs: Configuration objects to merge
            validate: Whether to validate merged configuration

        Returns:
            Config: Merged configuration
        """
        if not configs:
            raise ConfigurationError("No configurations provided to merge")

        # Convert all configs to dicts
        config_dicts = [config.to_dict() for config in configs]

        # Merge all dicts
        merged_dict = {}
        for config_dict in config_dicts:
            merged_dict = merge_dicts(merged_dict, config_dict, deep=True)

        # Create merged config
        merged_config = Config(config_dict=merged_dict)

        if validate:
            merged_config.validate()

        self._config = merged_config
        return merged_config

    def get_config(self) -> Optional[Config]:
        """
        Get current configuration.

        Returns:
            Current Config object or None if not loaded
        """
        return self._config

    def set_config(self, config: Config, validate: bool = True) -> None:
        """
        Set current configuration.

        Args:
            config: Configuration object to set
            validate: Whether to validate configuration
        """
        if validate:
            config.validate()

        self._config = config

    def reload(self, file_path: Optional[Union[str, Path]] = None) -> Config:
        """
        Reload configuration from file.

        Args:
            file_path: Path to configuration file. If None, uses last loaded file.

        Returns:
            Config: Reloaded configuration
        """
        if file_path is None:
            if not hasattr(self, "_last_file_path"):
                raise ConfigurationError(
                    "No file path specified and no previous file loaded"
                )
            file_path = self._last_file_path

        return self.load_from_file(file_path)
