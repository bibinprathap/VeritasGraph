"""
Ontology Module Manager Module

This module manages modular ontology development, supporting imports, subdomain
organization, and coordinated multi-team ontology development. It handles ontology
imports, module creation, and import closure resolution.

Key Features:
    - Ontology import management
    - Modular ontology organization
    - Subdomain ontology coordination
    - Cross-module reference handling
    - Import closure resolution
    - Module versioning and dependencies
    - Module validation

Main Classes:
    - ModuleManager: Manager for ontology modules
    - OntologyModule: Dataclass representing an ontology module

Example Usage:
    >>> from veritasreason.ontology import ModuleManager
    >>> manager = ModuleManager()
    >>> module = manager.create_module("PersonModule", "https://example.org/person/", "1.0")
    >>> manager.add_import("PersonModule", "https://example.org/core/")
    >>> imports = manager.resolve_imports("PersonModule")

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class OntologyModule:
    """Ontology module definition."""

    name: str
    uri: str
    version: str
    imports: List[str] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    properties: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModuleManager:
    """
    Ontology module management system.

    • Ontology import management
    • Modular ontology organization
    • Subdomain ontology coordination
    • Cross-module reference handling
    • Import closure resolution
    • Module versioning and dependencies
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize module manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration options
        """
        self.logger = get_logger("module_manager")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.modules: Dict[str, OntologyModule] = {}

    def create_module(
        self, name: str, uri: str, version: str = "1.0", **options
    ) -> OntologyModule:
        """
        Create an ontology module.

        Args:
            name: Module name
            uri: Module URI
            version: Module version
            **options: Additional options

        Returns:
            Created module
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ModuleManager",
            message=f"Creating ontology module: {name}",
        )

        try:
            module = OntologyModule(
                name=name,
                uri=uri,
                version=version,
                imports=options.get("imports", []),
                classes=options.get("classes", []),
                properties=options.get("properties", []),
                metadata={
                    "created_at": datetime.now().isoformat(),
                    **options.get("metadata", {}),
                },
            )

            self.modules[name] = module
            self.logger.info(f"Created ontology module: {name}")
            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Created ontology module: {name}",
            )
            return module

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def add_import(self, module_name: str, import_uri: str) -> None:
        """
        Add import to module.

        Args:
            module_name: Module name
            import_uri: URI of ontology to import
        """
        if module_name not in self.modules:
            raise ValidationError(f"Module not found: {module_name}")

        module = self.modules[module_name]
        if import_uri not in module.imports:
            module.imports.append(import_uri)
            self.logger.debug(f"Added import to module {module_name}: {import_uri}")

    def resolve_imports(self, module_name: str) -> List[str]:
        """
        Resolve import closure for module.

        Args:
            module_name: Module name

        Returns:
            List of all imported URIs (including transitive)
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ModuleManager",
            message=f"Resolving imports for module: {module_name}",
        )

        try:
            if module_name not in self.modules:
                raise ValidationError(f"Module not found: {module_name}")

            module = self.modules[module_name]
            resolved = set(module.imports)

            # Resolve transitive imports
            self.progress_tracker.update_tracking(
                tracking_id, message="Resolving transitive imports..."
            )
            for import_uri in module.imports:
                # Find module with this URI
                for other_module in self.modules.values():
                    if other_module.uri == import_uri:
                        resolved.update(other_module.imports)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Resolved {len(resolved)} imports for module: {module_name}",
            )
            return list(resolved)

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def get_module(self, name: str) -> Optional[OntologyModule]:
        """Get module by name."""
        return self.modules.get(name)

    def list_modules(self) -> List[str]:
        """List all module names."""
        return list(self.modules.keys())

    def validate_module(self, module_name: str) -> Dict[str, Any]:
        """
        Validate module structure.

        Args:
            module_name: Module name

        Returns:
            Validation results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="ontology",
            submodule="ModuleManager",
            message=f"Validating module: {module_name}",
        )

        try:
            if module_name not in self.modules:
                raise ValidationError(f"Module not found: {module_name}")

            module = self.modules[module_name]
            errors = []
            warnings = []

            # Check required fields
            self.progress_tracker.update_tracking(
                tracking_id, message="Checking required fields..."
            )
            if not module.uri:
                errors.append("Module missing URI")
            if not module.classes and not module.properties:
                warnings.append("Module has no classes or properties")

            # Check import validity
            self.progress_tracker.update_tracking(
                tracking_id, message="Validating imports..."
            )
            for import_uri in module.imports:
                # Basic URI validation
                if not import_uri.startswith("http"):
                    warnings.append(f"Import URI may be invalid: {import_uri}")

            result = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Validation complete: {'Valid' if result['valid'] else 'Invalid'} ({len(errors)} errors, {len(warnings)} warnings)",
            )
            return result

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise
