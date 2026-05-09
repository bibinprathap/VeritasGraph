"""
Entity Normalization Module

This module provides comprehensive entity normalization capabilities for the
VeritasReason framework, enabling standardization of named entities and proper nouns
across various formats and naming conventions.

Key Features:
    - Entity name standardization
    - Alias resolution and mapping
    - Entity disambiguation (context-aware)
    - Name variant handling (titles, honorifics, formats)
    - Entity linking and resolution
    - Support for multiple entity types (Person, Organization, etc.)

Main Classes:
    - EntityNormalizer: Main entity normalization coordinator
    - AliasResolver: Entity alias resolution engine
    - EntityDisambiguator: Entity disambiguation engine
    - NameVariantHandler: Name variant processing engine

Example Usage:
    >>> from veritasreason.normalize import EntityNormalizer
    >>> normalizer = EntityNormalizer()
    >>> normalized = normalizer.normalize_entity("John Doe", entity_type="Person")
    >>> canonical = normalizer.resolve_aliases("J. Doe")

Author: VeritasReason Contributors
License: MIT
"""

import re
from typing import Any, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


class EntityNormalizer:
    """
    Entity normalization and standardization coordinator.

    This class provides comprehensive entity normalization capabilities, coordinating
    alias resolution, disambiguation, and name variant handling.

    Features:
        - Entity name normalization and standardization
        - Alias resolution and mapping
        - Entity disambiguation using context
        - Name format standardization
        - Entity linking to canonical forms
        - Support for multiple entity types

    Example Usage:
        >>> normalizer = EntityNormalizer()
        >>> normalized = normalizer.normalize_entity("John Doe", entity_type="Person")
        >>> canonical = normalizer.resolve_aliases("J. Doe")
        >>> linked = normalizer.link_entities(["John Doe", "J. Doe", "Johnny Doe"])
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize entity normalizer.

        Sets up the normalizer with alias resolver, disambiguator, and variant
        handler components.

        Args:
            config: Configuration dictionary (optional)
            **kwargs: Additional configuration options (merged into config)
        """
        self.logger = get_logger("entity_normalizer")
        self.config = config or {}
        self.config.update(kwargs)

        self.alias_resolver = AliasResolver(**self.config)
        self.disambiguator = EntityDisambiguator(**self.config)
        self.variant_handler = NameVariantHandler(**self.config)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("Entity normalizer initialized")

    def normalize_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        resolve_aliases: bool = True,
        **options,
    ) -> str:
        """
        Normalize entity name to standard form.

        This method normalizes an entity name by cleaning whitespace, resolving
        aliases, and standardizing the format based on entity type.

        Args:
            entity_name: Entity name to normalize
            entity_type: Entity type (optional, e.g., "Person", "Organization")
            resolve_aliases: Whether to resolve aliases (default: True)
            **options: Additional normalization options (unused)

        Returns:
            str: Normalized entity name in standard form
        """
        tracking_id = self.progress_tracker.start_tracking(
            message="VeritasReason: Normalizing entity", file=None
        )
        try:
            if not entity_name:
                self.progress_tracker.stop_tracking(tracking_id, status="completed")
                return ""

            normalized = entity_name.strip()

            # Clean and standardize
            normalized = re.sub(r"\s+", " ", normalized)
            normalized = normalized.title() if entity_type == "Person" else normalized

            # Resolve aliases
            if resolve_aliases:
                resolved = self.alias_resolver.resolve_aliases(
                    normalized, entity_type=entity_type
                )
                if resolved:
                    normalized = resolved

            # Handle name variants
            normalized = self.variant_handler.normalize_name_format(
                normalized, format_type="standard"
            )

            self.progress_tracker.stop_tracking(tracking_id, status="completed")
            return normalized
        except Exception as e:
            self.progress_tracker.stop_tracking(tracking_id, status="failed")
            raise

    def resolve_aliases(self, entity_name: str, **context) -> Optional[str]:
        """
        Resolve entity aliases and variants.

        This method attempts to resolve an entity name to its canonical form
        using alias mapping.

        Args:
            entity_name: Entity name to resolve
            **context: Context information (e.g., entity_type)

        Returns:
            Optional[str]: Resolved canonical form if found, None otherwise
        """
        tracking_id = self.progress_tracker.start_tracking(
            message="VeritasReason: Resolving aliases", file=None
        )
        try:
            result = self.alias_resolver.resolve_aliases(entity_name, **context)
            self.progress_tracker.stop_tracking(tracking_id, status="completed")
            return result
        except Exception as e:
            self.progress_tracker.stop_tracking(tracking_id, status="failed")
            raise

    def disambiguate_entity(self, entity_name: str, **context) -> Dict[str, Any]:
        """
        Disambiguate entity when multiple candidates exist.

        This method disambiguates an entity name when multiple candidates exist,
        using context information to select the most likely candidate.

        Args:
            entity_name: Entity name to disambiguate
            **context: Context information (e.g., entity_type, context text)

        Returns:
            dict: Disambiguation result containing:
                - entity_name: Original entity name
                - entity_type: Detected entity type
                - confidence: Confidence score (0.0 to 1.0)
                - candidates: List of candidate entity names
        """
        tracking_id = self.progress_tracker.start_tracking(
            message="VeritasReason: Disambiguating entity", file=None
        )
        try:
            result = self.disambiguator.disambiguate(entity_name, **context)
            self.progress_tracker.stop_tracking(tracking_id, status="completed")
            return result
        except Exception as e:
            self.progress_tracker.stop_tracking(tracking_id, status="failed")
            raise

    def link_entities(self, entities: List[str], **options) -> Dict[str, str]:
        """
        Link entities to canonical forms.

        This method links a list of entity names to their canonical forms,
        creating a mapping from original names to normalized names.

        Args:
            entities: List of entity names to link
            **options: Linking options (passed to normalize_entity)

        Returns:
            dict: Dictionary mapping original entity names to canonical forms
        """
        tracking_id = self.progress_tracker.start_tracking(
            message="VeritasReason: Linking entities", file=None
        )
        try:
            linked = {}

            for entity in entities:
                canonical = self.normalize_entity(entity, **options)
                linked[entity] = canonical

            self.progress_tracker.stop_tracking(tracking_id, status="completed")
            return linked
        except Exception as e:
            self.progress_tracker.stop_tracking(tracking_id, status="failed")
            raise


class AliasResolver:
    """
    Entity alias resolution engine.

    This class provides alias resolution capabilities, mapping entity name
    variations and aliases to canonical forms.

    Features:
        - Entity alias and nickname resolution
        - Name variation mapping
        - Support for different naming conventions
        - Cultural and linguistic variation handling

    Example Usage:
        >>> resolver = AliasResolver(alias_map={"j. doe": "John Doe"})
        >>> canonical = resolver.resolve_aliases("J. Doe")
    """

    def __init__(self, **config):
        """
        Initialize alias resolver.

        Sets up the resolver with alias mapping dictionary.

        Args:
            **config: Configuration options:
                - alias_map: Dictionary mapping aliases to canonical forms
        """
        self.logger = get_logger("alias_resolver")
        self.config = config
        self.alias_map = config.get("alias_map", {})

        self.logger.debug(f"Alias resolver initialized ({len(self.alias_map)} aliases)")

    def resolve_aliases(self, entity_name: str, **context) -> Optional[str]:
        """
        Resolve entity aliases to canonical form.

        This method looks up an entity name in the alias map and returns
        its canonical form if found.

        Args:
            entity_name: Entity name to resolve
            **context: Context information (e.g., entity_type, currently unused)

        Returns:
            Optional[str]: Resolved canonical form if found in alias map,
                          None otherwise
        """
        # Check alias map
        entity_lower = entity_name.lower()

        if entity_lower in self.alias_map:
            return self.alias_map[entity_lower]

        # Check for common aliases
        for alias, canonical in self.alias_map.items():
            if alias.lower() == entity_lower:
                return canonical

        return None

    def map_variants(self, entity_name: str, entity_type: str) -> str:
        """
        Map entity name variants.

        This method maps entity name variants to a standard form based on
        entity type. Currently returns the name as-is; can be extended for
        variant mapping.

        Args:
            entity_name: Entity name to map
            entity_type: Entity type (e.g., "Person", "Organization")

        Returns:
            str: Mapped variant (currently returns entity_name as-is)
        """
        # Simple variant mapping - can be extended
        return entity_name

    def handle_cultural_variations(
        self, entity_name: str, culture: Optional[str] = None
    ) -> str:
        """
        Handle cultural and linguistic variations.

        This method handles cultural and linguistic variations in entity names.
        Currently returns the name as-is; can be extended for cultural
        normalization.

        Args:
            entity_name: Entity name to process
            culture: Culture identifier (optional, e.g., "en-US", "zh-CN")

        Returns:
            str: Culturally appropriate form (currently returns entity_name as-is)
        """
        return entity_name


class EntityDisambiguator:
    """
    Entity disambiguation engine.

    This class provides entity disambiguation capabilities, using context
    information to resolve ambiguous entity references.

    Features:
        - Context-aware entity disambiguation
        - Entity type classification
        - Confidence score calculation
        - Candidate entity generation

    Example Usage:
        >>> disambiguator = EntityDisambiguator()
        >>> result = disambiguator.disambiguate("Apple", context="technology company")
        >>> entity_type = disambiguator.classify_entity_type("John Doe")
    """

    def __init__(self, **config):
        """
        Initialize entity disambiguator.

        Sets up the disambiguator with configuration options.

        Args:
            **config: Configuration options (currently unused)
        """
        self.logger = get_logger("entity_disambiguator")
        self.config = config

        self.logger.debug("Entity disambiguator initialized")

    def disambiguate(self, entity_name: str, **context) -> Dict[str, Any]:
        """
        Disambiguate entity using context.

        This method disambiguates an entity name using context information.
        Currently provides a basic implementation; can be extended with
        machine learning models for improved disambiguation.

        Args:
            entity_name: Entity name to disambiguate
            **context: Context information containing:
                - entity_type: Entity type (optional)
                - context: Text context (optional)

        Returns:
            dict: Disambiguation result containing:
                - entity_name: Original entity name
                - entity_type: Detected entity type
                - confidence: Confidence score (0.0 to 1.0)
                - candidates: List of candidate entity names
        """
        entity_type = context.get("entity_type")
        text_context = context.get("context", "")

        return {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "confidence": 0.8,
            "candidates": [entity_name],
        }

    def classify_entity_type(self, entity_name: str, **context) -> str:
        """
        Classify entity type for disambiguation.

        This method classifies the entity type using simple heuristics based
        on name format. Can be extended with more sophisticated classification.

        Args:
            entity_name: Entity name to classify
            **context: Context information (currently unused)

        Returns:
            str: Entity type classification:
                - "Person": If name starts with uppercase and contains space
                - "Organization": If name starts with uppercase
                - "Entity": Otherwise
        """
        if not entity_name:
            return "Entity"

        # Simple heuristic-based classification
        if entity_name[0].isupper() and " " in entity_name:
            return "Person"
        elif entity_name[0].isupper():
            return "Organization"
        else:
            return "Entity"

    def calculate_confidence(
        self, candidates: List[str], **context
    ) -> Dict[str, float]:
        """
        Calculate confidence scores for candidates.

        This method calculates confidence scores for candidate entities.
        Currently returns a default confidence of 0.8 for all candidates;
        can be extended with more sophisticated scoring.

        Args:
            candidates: List of candidate entity names
            **context: Context information (currently unused)

        Returns:
            dict: Dictionary mapping candidate names to confidence scores
                 (0.0 to 1.0)
        """
        return {candidate: 0.8 for candidate in candidates}


class NameVariantHandler:
    """
    Name variant processing engine.

    This class provides name variant handling capabilities, processing different
    name formats, titles, and honorifics.

    Features:
        - Name format normalization (standard, title, lower)
        - Title and honorific handling
        - Name variant generation
        - Format standardization

    Example Usage:
        >>> handler = NameVariantHandler()
        >>> normalized = handler.normalize_name_format("Dr. John Doe", "standard")
        >>> title_info = handler.handle_titles_and_honorifics("Mr. John Doe")
    """

    def __init__(self, **config):
        """
        Initialize name variant handler.

        Sets up the handler with titles dictionary and configuration.

        Args:
            **config: Configuration options:
                - titles: Set of title strings (optional, uses default if not provided)
        """
        self.logger = get_logger("name_variant_handler")
        self.config = config
        self.titles = config.get(
            "titles", {"Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sir", "Madam"}
        )

        self.logger.debug(
            f"Name variant handler initialized ({len(self.titles)} titles)"
        )

    def process_variants(self, entity_name: str, **options) -> List[str]:
        """
        Process entity name variants.

        This method generates a list of name variants for an entity, including
        the original name and normalized forms.

        Args:
            entity_name: Entity name to process
            **options: Processing options (unused)

        Returns:
            list: List of name variant strings
        """
        variants = [entity_name]

        # Generate common variants
        normalized = self.normalize_name_format(entity_name, "standard")
        if normalized != entity_name:
            variants.append(normalized)

        return variants

    def normalize_name_format(
        self, entity_name: str, format_type: str = "standard"
    ) -> str:
        """
        Normalize name format.

        This method normalizes the format of an entity name, removing titles
        and applying the specified format type.

        Args:
            entity_name: Entity name to normalize
            format_type: Format type (default: "standard"):
                - "standard": Title case for each word part
                - "title": Title case for entire name
                - "lower": Lowercase

        Returns:
            str: Formatted name with titles removed
        """
        # Remove titles
        name = entity_name
        for title in self.titles:
            # Case-insensitive removal of titles from the beginning of the name
            pattern = re.compile(r"^" + re.escape(title) + r"\s*", re.IGNORECASE)
            name = pattern.sub("", name)

        name = name.strip()

        if format_type == "standard":
            # Title case for names
            parts = name.split()
            name = " ".join(part.capitalize() for part in parts)
        elif format_type == "title":
            name = name.title()
        elif format_type == "lower":
            name = name.lower()

        return name

    def handle_titles_and_honorifics(self, entity_name: str) -> Dict[str, Any]:
        """
        Handle titles and honorifics in names.

        This method extracts titles and honorifics from entity names, returning
        the name without title and the extracted title.

        Args:
            entity_name: Entity name with potential title

        Returns:
            dict: Dictionary containing:
                - name: Name without title
                - title: Extracted title (None if no title found)
        """
        title = None
        name = entity_name

        for t in self.titles:
            if entity_name.startswith(t):
                title = t
                name = entity_name.replace(t, "").strip()
                break

        return {"name": name, "title": title}
