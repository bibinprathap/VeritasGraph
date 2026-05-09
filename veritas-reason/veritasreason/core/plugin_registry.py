"""
Plugin Registry Module

This module provides comprehensive plugin management for the VeritasReason framework,
including dynamic plugin discovery, loading, dependency resolution, and lifecycle management.

Key Features:
    - Dynamic plugin discovery from file system
    - Plugin version management and compatibility checking
    - Automatic dependency resolution and loading
    - Plugin lifecycle management (load, unload, cleanup)
    - Plugin isolation and error handling

Example Usage:
    >>> from veritasreason.core import PluginRegistry
    >>> registry = PluginRegistry(plugin_paths=["./plugins"])
    >>> plugin = registry.load_plugin("my_plugin", config={"key": "value"})
    >>> plugins = registry.list_plugins()

Author: VeritasReason Contributors
License: MIT
"""

import importlib
import importlib.util
import inspect
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from ..utils.exceptions import ConfigurationError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class PluginInfo:
    """Plugin information."""

    name: str
    version: str
    plugin_class: Type
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedPlugin:
    """Loaded plugin instance."""

    info: PluginInfo
    instance: Any
    config: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[float] = None


class PluginRegistry:
    """
    Plugin registry and management system.

    This class manages the complete lifecycle of plugins including discovery,
    registration, loading, dependency resolution, and unloading. It supports
    automatic plugin discovery from file paths and manual registration.

    Features:
        - Automatic plugin discovery from directories
        - Dependency resolution and automatic loading
        - Plugin version management
        - Lifecycle management (load, unload, cleanup)
        - Plugin metadata and capability tracking

    Example Usage:
        >>> registry = PluginRegistry(plugin_paths=["./plugins", "./custom_plugins"])
        >>> # Auto-discover plugins from paths
        >>> plugin = registry.load_plugin("my_plugin", api_key="xxx")
        >>> info = registry.get_plugin_info("my_plugin")
    """

    def __init__(self, plugin_paths: Optional[List[Union[str, Path]]] = None):
        """
        Initialize plugin registry.

        Creates a new plugin registry and automatically discovers plugins
        from the provided paths.

        Args:
            plugin_paths: List of directory paths to search for plugins.
                         Can be strings or Path objects. If None, no
                         automatic discovery is performed.
        """
        self.logger = get_logger("plugin_registry")

        # Normalize plugin paths to Path objects
        self.plugin_paths: List[Path] = []
        if plugin_paths:
            for path in plugin_paths:
                normalized_path = Path(path) if isinstance(path, str) else path
                self.plugin_paths.append(normalized_path)

        # Plugin registries
        self.plugins: Dict[str, PluginInfo] = {}  # Registered plugins
        self.loaded_plugins: Dict[str, LoadedPlugin] = {}  # Currently loaded plugins
        self._discovered_plugins: Dict[str, Path] = {}  # Discovery cache

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()

        # Discover available plugins from paths
        if self.plugin_paths:
            self.logger.info(
                f"Discovering plugins from {len(self.plugin_paths)} path(s)"
            )
            self._discover_plugins()
            self.logger.info(f"Discovered {len(self.plugins)} plugin(s)")
        else:
            self.logger.debug("No plugin paths provided, skipping auto-discovery")

    def register_plugin(
        self,
        plugin_name: str,
        plugin_class: Type,
        version: str = "1.0.0",
        **metadata: Any,
    ) -> None:
        """
        Register a plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_class: Plugin class to register
            version: Plugin version
            **metadata: Additional plugin metadata:
                - description: Plugin description
                - author: Plugin author
                - dependencies: List of dependency plugin names
                - capabilities: List of plugin capabilities

        Raises:
            ValidationError: If plugin is invalid
        """
        try:
            # Validate plugin class
            if not inspect.isclass(plugin_class):
                raise ValidationError(
                    f"Plugin {plugin_name} must be a class, got {type(plugin_class)}"
                )

            # Check for required methods
            required_methods = ["initialize", "execute"]
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    raise ValidationError(
                        f"Plugin {plugin_name} must have {method}() method"
                    )

            # Create plugin info
            plugin_info = PluginInfo(
                name=plugin_name,
                version=version,
                plugin_class=plugin_class,
                description=metadata.get("description", ""),
                author=metadata.get("author", ""),
                dependencies=metadata.get("dependencies", []),
                capabilities=metadata.get("capabilities", []),
                metadata=metadata,
            )

            # Validate dependencies
            self._validate_dependencies(plugin_info)

            # Register plugin
            self.plugins[plugin_name] = plugin_info
            self.logger.info(f"Registered plugin: {plugin_name} v{version}")

        except Exception as e:
            self.logger.error(f"Failed to register plugin {plugin_name}: {e}")
            raise

    def load_plugin(self, plugin_name: str, **config: Any) -> Any:
        """
        Load and initialize a plugin.

        This method loads a plugin, resolves its dependencies automatically,
        creates an instance, and initializes it. If the plugin is already
        loaded, returns the existing instance.

        Args:
            plugin_name: Name of the plugin to load
            **config: Plugin configuration passed to plugin constructor

        Returns:
            Loaded and initialized plugin instance

        Raises:
            ConfigurationError: If plugin not found, dependencies missing,
                               or initialization fails

        Example:
            >>> plugin = registry.load_plugin("database_plugin", host="localhost")
            >>> # Dependencies are automatically loaded first
        """
        # Track plugin loading
        tracking_id = self.progress_tracker.start_tracking(
            file=None,
            module="core",
            submodule="PluginRegistry",
            message=f"Loading plugin: {plugin_name}",
        )

        try:
            # Check if plugin is already loaded (return existing instance)
            if plugin_name in self.loaded_plugins:
                self.logger.debug(
                    f"Plugin '{plugin_name}' already loaded, returning existing instance"
                )
                return self.loaded_plugins[plugin_name].instance

            # Check if plugin is registered
            if plugin_name not in self.plugins:
                # Try to discover and register the plugin
                self.logger.debug(
                    f"Plugin '{plugin_name}' not registered, attempting discovery"
                )
                self._discover_plugin(plugin_name)

                # Check again after discovery
                if plugin_name not in self.plugins:
                    available = list(self.plugins.keys())
                    error_msg = (
                        f"Plugin '{plugin_name}' not found. "
                        f"Available plugins: {available if available else 'none'}"
                    )
                    raise ConfigurationError(error_msg)

            plugin_info = self.plugins[plugin_name]
            self.logger.debug(f"Loading plugin '{plugin_name}' v{plugin_info.version}")

            # Load dependencies first (recursive)
            if plugin_info.dependencies:
                self.logger.debug(
                    f"Plugin '{plugin_name}' has {len(plugin_info.dependencies)} dependency(ies)"
                )
                for dep_name in plugin_info.dependencies:
                    if dep_name not in self.loaded_plugins:
                        self.logger.debug(f"Loading dependency: {dep_name}")
                        self.load_plugin(dep_name)  # Recursive call
                    else:
                        self.logger.debug(f"Dependency '{dep_name}' already loaded")

            # Create plugin instance
            plugin_class = plugin_info.plugin_class

            try:
                # Try to create instance with provided config
                plugin_instance = plugin_class(**config)
            except TypeError as e:
                # If initialization fails with config, try without
                self.logger.warning(
                    f"Failed to initialize '{plugin_name}' with config: {e}. "
                    "Trying without config."
                )
                try:
                    plugin_instance = plugin_class()
                except Exception as e2:
                    raise ConfigurationError(
                        f"Failed to initialize plugin '{plugin_name}': {e2}"
                    ) from e2

            # Initialize plugin if it has an initialize method
            if hasattr(plugin_instance, "initialize"):
                try:
                    plugin_instance.initialize()
                except Exception as e:
                    raise ConfigurationError(
                        f"Plugin '{plugin_name}' initialization failed: {e}"
                    ) from e

            # Store loaded plugin information
            loaded_plugin = LoadedPlugin(
                info=plugin_info,
                instance=plugin_instance,
                config=config,
                loaded_at=time.time(),
            )

            self.loaded_plugins[plugin_name] = loaded_plugin

            self.logger.info(
                f"Successfully loaded plugin '{plugin_name}' v{plugin_info.version}"
            )

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Plugin '{plugin_name}' loaded successfully",
            )
            return plugin_instance

        except ConfigurationError:
            # Re-raise configuration errors as-is
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="failed",
                message=f"Configuration error loading plugin '{plugin_name}'",
            )
            raise
        except Exception as e:
            # Wrap other exceptions
            error_msg = f"Failed to load plugin '{plugin_name}': {e}"
            self.logger.error(error_msg)
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=error_msg
            )
            raise ConfigurationError(error_msg) from e

    def unload_plugin(self, plugin_name: str) -> None:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of plugin to unload

        Raises:
            ConfigurationError: If plugin not loaded
        """
        if plugin_name not in self.loaded_plugins:
            raise ConfigurationError(f"Plugin {plugin_name} is not loaded")

        try:
            plugin_instance = self.loaded_plugins[plugin_name].instance

            # Call plugin cleanup if available
            if hasattr(plugin_instance, "cleanup"):
                plugin_instance.cleanup()
            elif hasattr(plugin_instance, "close"):
                plugin_instance.close()

            # Remove from loaded plugins
            del self.loaded_plugins[plugin_name]

            self.logger.info(f"Unloaded plugin: {plugin_name}")

        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            raise ConfigurationError(f"Failed to unload plugin {plugin_name}: {e}")

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        List all available plugins.

        Returns:
            List of plugin information dictionaries
        """
        plugins = []

        for name, plugin_info in self.plugins.items():
            plugin_data = {
                "name": plugin_info.name,
                "version": plugin_info.version,
                "description": plugin_info.description,
                "author": plugin_info.author,
                "dependencies": plugin_info.dependencies,
                "capabilities": plugin_info.capabilities,
                "loaded": name in self.loaded_plugins,
                "metadata": plugin_info.metadata,
            }

            if name in self.loaded_plugins:
                loaded_plugin = self.loaded_plugins[name]
                plugin_data["config"] = loaded_plugin.config
                plugin_data["loaded_at"] = loaded_plugin.loaded_at

            plugins.append(plugin_data)

        return plugins

    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get information about a plugin.

        Args:
            plugin_name: Name of plugin

        Returns:
            Dictionary with plugin information

        Raises:
            ConfigurationError: If plugin not found
        """
        if plugin_name not in self.plugins:
            raise ConfigurationError(f"Plugin {plugin_name} not found")

        plugin_info = self.plugins[plugin_name]

        info = {
            "name": plugin_info.name,
            "version": plugin_info.version,
            "description": plugin_info.description,
            "author": plugin_info.author,
            "dependencies": plugin_info.dependencies,
            "capabilities": plugin_info.capabilities,
            "metadata": plugin_info.metadata,
            "loaded": plugin_name in self.loaded_plugins,
        }

        if plugin_name in self.loaded_plugins:
            loaded_plugin = self.loaded_plugins[plugin_name]
            info["config"] = loaded_plugin.config
            info["loaded_at"] = loaded_plugin.loaded_at

        return info

    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """
        Check if a plugin is loaded.

        Args:
            plugin_name: Name of plugin

        Returns:
            True if plugin is loaded, False otherwise
        """
        return plugin_name in self.loaded_plugins

    def get_loaded_plugin(self, plugin_name: str) -> Optional[Any]:
        """
        Get loaded plugin instance.

        Args:
            plugin_name: Name of plugin

        Returns:
            Plugin instance or None if not loaded
        """
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name].instance
        return None

    def _discover_plugins(self) -> None:
        """
        Discover available plugins from configured plugin paths.

        This method scans all configured plugin paths for Python files that
        contain plugin classes. Each discovered plugin is automatically
        registered with the registry.

        Discovery Process:
            1. Iterate through all configured plugin paths
            2. For each directory, scan for .py files
            3. Attempt to load and register each plugin file
            4. Log discovery results
        """
        discovered_count = 0

        for plugin_path in self.plugin_paths:
            # Normalize path to Path object
            if isinstance(plugin_path, str):
                plugin_path = Path(plugin_path)

            # Check if path exists and is a directory
            if plugin_path.exists() and plugin_path.is_dir():
                self.logger.debug(f"Scanning plugin directory: {plugin_path}")
                before_count = len(self.plugins)
                self._scan_directory(plugin_path)
                after_count = len(self.plugins)
                discovered_count += after_count - before_count
            else:
                self.logger.debug(
                    f"Plugin path not found or not a directory: {plugin_path}"
                )

        if discovered_count > 0:
            self.logger.info(f"Discovered {discovered_count} plugin(s) from paths")

    def _discover_plugin(self, plugin_name: str) -> None:
        """
        Discover a specific plugin.

        Args:
            plugin_name: Name of plugin to discover
        """
        for plugin_path in self.plugin_paths:
            if isinstance(plugin_path, str):
                plugin_path = Path(plugin_path)

            # Try to find plugin module
            plugin_module_path = plugin_path / f"{plugin_name}.py"
            if plugin_module_path.exists():
                try:
                    self._load_plugin_from_file(plugin_module_path, plugin_name)
                    break
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load plugin from {plugin_module_path}: {e}"
                    )

    def _scan_directory(self, directory: Path) -> None:
        """
        Scan directory for plugin files and load them.

        This method finds all Python files in the directory (excluding __init__.py)
        and attempts to load them as plugins. Files that fail to load are logged
        but don't stop the scanning process.

        Args:
            directory: Directory path to scan for plugin files

        Process:
            - Finds all .py files in directory
            - Skips __init__.py files
            - Attempts to load each file as a plugin
            - Logs failures but continues scanning
        """
        plugin_files = list(directory.glob("*.py"))

        if not plugin_files:
            self.logger.debug(f"No Python files found in {directory}")
            return

        self.logger.debug(f"Scanning {len(plugin_files)} file(s) in {directory}")

        for file_path in plugin_files:
            # Skip __init__.py files
            if file_path.name == "__init__.py":
                continue

            plugin_name = file_path.stem
            try:
                self._load_plugin_from_file(file_path, plugin_name)
            except Exception as e:
                # Log but continue - file might not be a valid plugin
                self.logger.debug(
                    f"Failed to load plugin from {file_path}: {e}. "
                    "File may not be a valid plugin."
                )

    def _load_plugin_from_file(self, file_path: Path, plugin_name: str) -> None:
        """
        Load and register a plugin from a Python file.

        This method dynamically imports a Python module, finds the plugin class,
        extracts metadata, and registers the plugin with the registry.

        Plugin Class Detection:
            The method tries multiple strategies to find the plugin class:
            1. Common naming patterns (PluginName, PluginNamePlugin, etc.)
            2. Any class containing "Plugin" in its name
            3. Falls back to first class found if no pattern matches

        Metadata Extraction:
            Extracts plugin metadata from module attributes:
            - description: From __doc__ or module.description
            - author: From module.author
            - version: From module.version (default: "1.0.0")
            - dependencies: From module.dependencies
            - capabilities: From module.capabilities

        Args:
            file_path: Path to the Python file containing the plugin
            plugin_name: Name to use for the plugin (typically file stem)

        Raises:
            Exception: If file cannot be loaded or plugin class not found
        """
        try:
            # Create module spec from file path
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            if spec is None or spec.loader is None:
                self.logger.warning(f"Could not create module spec for {file_path}")
                return

            # Load and execute the module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class using multiple strategies
            plugin_class = None

            # Strategy 1: Try common naming patterns
            class_names = [
                plugin_name.capitalize(),  # "my_plugin" -> "My_plugin"
                plugin_name.capitalize() + "Plugin",  # "my_plugin" -> "My_pluginPlugin"
                plugin_name.replace("_", "").capitalize(),  # "my_plugin" -> "Myplugin"
            ]

            for class_name in class_names:
                if hasattr(module, class_name):
                    candidate = getattr(module, class_name)
                    if inspect.isclass(candidate):
                        plugin_class = candidate
                        self.logger.debug(
                            f"Found plugin class '{class_name}' using naming pattern"
                        )
                        break

            # Strategy 2: Look for any class with "Plugin" in name
            if plugin_class is None:
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and "Plugin" in name:
                        plugin_class = obj
                        self.logger.debug(
                            f"Found plugin class '{name}' by 'Plugin' keyword"
                        )
                        break

            # If still not found, cannot register plugin
            if plugin_class is None:
                self.logger.warning(
                    f"No plugin class found in {file_path}. "
                    "Expected class name patterns: PluginName, PluginNamePlugin, or *Plugin"
                )
                return

            # Extract metadata from module attributes
            metadata = {
                "description": (
                    getattr(module, "__doc__", "") or getattr(module, "description", "")
                ),
                "author": getattr(module, "author", ""),
                "version": getattr(module, "version", "1.0.0"),
                "dependencies": getattr(module, "dependencies", []),
                "capabilities": getattr(module, "capabilities", []),
            }

            # Register the discovered plugin
            self.register_plugin(
                plugin_name=plugin_name, plugin_class=plugin_class, **metadata
            )

            self.logger.debug(
                f"Successfully loaded plugin '{plugin_name}' from {file_path}"
            )

        except Exception as e:
            error_msg = f"Failed to load plugin from {file_path}: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e

    def _validate_dependencies(self, plugin_info: PluginInfo) -> None:
        """
        Validate plugin dependencies.

        Args:
            plugin_info: Plugin information

        Raises:
            ValidationError: If dependencies are invalid
        """
        for dep_name in plugin_info.dependencies:
            if dep_name not in self.plugins:
                # Try to discover dependency
                self._discover_plugin(dep_name)

                if dep_name not in self.plugins:
                    raise ValidationError(
                        f"Plugin {plugin_info.name} depends on {dep_name}, "
                        f"but {dep_name} is not available"
                    )
