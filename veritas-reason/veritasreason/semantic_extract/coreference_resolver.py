"""
Coreference Resolution Module

This module provides comprehensive coreference resolution capabilities for resolving
pronoun references and entity coreferences in text, enabling better understanding
of entity mentions and references. Supports multiple extraction methods for
underlying entity extraction.

Supported Methods (for underlying NER extractors):
    - "pattern": Pattern-based extraction
    - "regex": Regex-based extraction
    - "rules": Rule-based extraction
    - "ml": ML-based extraction (spaCy)
    - "huggingface": HuggingFace model extraction
    - "llm": LLM-based extraction
    - Any method supported by NERExtractor

Algorithms Used:
    - Pronoun Resolution: Rule-based and distance-based antecedent resolution
    - Entity Coreference: String matching and similarity-based coreference detection
    - Coreference Chain Building: Graph-based chain construction algorithms
    - Mention Extraction: Pattern-based and ML-based mention detection
    - Ambiguity Resolution: Context-aware disambiguation algorithms
    - Distance Metrics: Character distance and sentence distance calculations

Key Features:
    - Pronoun resolution (he, she, it, they, etc.)
    - Entity coreference detection
    - Coreference chain construction
    - Ambiguity resolution
    - Cross-document coreference support
    - Mention extraction and tracking
    - Integration with multiple NER extraction methods
    - Method parameter support for underlying extractors

Main Classes:
    - CoreferenceResolver: Main coreference resolution coordinator
    - PronounResolver: Pronoun resolution engine
    - EntityCoreferenceDetector: Entity coreference detection
    - CoreferenceChainBuilder: Coreference chain construction
    - Mention: Mention representation dataclass
    - CoreferenceChain: Coreference chain representation dataclass

Example Usage:
    >>> from veritasreason.semantic_extract import CoreferenceResolver
    >>> # Using default methods
    >>> resolver = CoreferenceResolver()
    >>> chains = resolver.resolve_coreferences("John went to the store. He bought milk.")
    >>> 
    >>> # Using LLM-based extraction for entities
    >>> resolver = CoreferenceResolver(method="llm", provider="openai")
    >>> chains = resolver.resolve_coreferences("John went to the store. He bought milk.")
    >>> 
    >>> pronouns = resolver.resolve_pronouns("Mary said she would come.")

Author: VeritasReason Contributors
License: MIT
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker
from .ner_extractor import Entity


@dataclass
class Mention:
    """Mention representation."""

    text: str
    start_char: int
    end_char: int
    mention_type: str  # pronoun, entity, nominal
    entity_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoreferenceChain:
    """Coreference chain representation."""

    mentions: List[Mention]
    representative: Mention
    entity_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CoreferenceResolver:
    """Coreference resolution handler."""

    def __init__(self, method: Union[str, List[str]] = None, config=None, **kwargs):
        """
        Initialize coreference resolver.

        Args:
            method: Extraction method(s) for underlying NER extractors.
                   Can be passed to ner_method in config.
            config: Legacy config dict (deprecated, use kwargs)
            **kwargs: Configuration options:
                - ner_method: Method for NER extraction (if entities need to be extracted)
                - Other options passed to sub-components
        """
        self.logger = get_logger("coreference_resolver")
        self.config = config or {}
        self.config.update(kwargs)
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        # Store method for passing to extractors if needed
        if method is not None:
            self.config["ner_method"] = method

        self.pronoun_resolver = PronounResolver(**self.config.get("pronoun", {}))
        self.entity_detector = EntityCoreferenceDetector(
            **self.config.get("entity", {})
        )
        self.chain_builder = CoreferenceChainBuilder(**self.config.get("chain", {}))

    def resolve_coreferences(
        self,
        text: str,
        entities: Optional[List[Entity]] = None,
        **options
    ) -> List[CoreferenceChain]:
        """
        Resolve coreferences in text.

        Args:
            text: Input text
            entities: List of entities (optional)
            **options: Resolution options

        Returns:
            list: List of coreference chains
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="semantic_extract",
            submodule="CoreferenceResolver",
            message="Resolving coreferences in text",
        )

        try:
            from .ner_extractor import NERExtractor

            total_steps = 4  # Extract mentions, resolve pronouns, detect coreferences, build chains
            current_step = 0
            
            # Step 1: Extract mentions
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Extracting mentions... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            
            # Extract pronouns
            mentions = self._extract_mentions(text)

            # Add entities as mentions
            if entities is None:
                # Extract entities if not provided
                ner_config = self.config.get("ner", {})
                if "ner_method" in self.config:
                    ner_config["method"] = self.config["ner_method"]
                ner = NERExtractor(
                    **ner_config,
                    **{
                        k: v
                        for k, v in self.config.items()
                        if k not in ["ner", "relation", "chain", "entity", "pronoun"]
                    },
                )
                entities = ner.extract_entities(text, **options)

            if entities:
                for entity in entities:
                    mentions.append(
                        Mention(
                            text=entity.text,
                            start_char=entity.start_char,
                            end_char=entity.end_char,
                            mention_type="entity",
                            metadata={"entity_label": entity.label, "confidence": entity.confidence},
                        )
                    )
            
            # Step 2: Resolve pronouns
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Resolving pronouns... ({current_step}/{total_steps}, {len(mentions)} mentions, remaining: {remaining_steps} steps)"
            )
            pronoun_resolutions = self.pronoun_resolver.resolve_pronouns(
                text, mentions, **options
            )

            # Step 3: Detect entity coreferences
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Detecting entity coreferences... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            entity_corefs = self.entity_detector.detect_entity_coreferences(
                text, mentions, **options
            )

            # Step 4: Build chains
            current_step += 1
            remaining_steps = total_steps - current_step
            self.progress_tracker.update_progress(
                tracking_id,
                processed=current_step,
                total=total_steps,
                message=f"Building coreference chains... ({current_step}/{total_steps}, remaining: {remaining_steps} steps)"
            )
            chains = self.chain_builder.build_coreference_chains(mentions, **options)

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Resolved {len(chains)} coreference chains",
            )
            return chains

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            verbose_mode = options.get("verbose", False) or self.config.get("verbose", False)
            if verbose_mode:
                import sys
                print(f"    [CoreferenceResolver] ERROR: Resolution failed: {e}", flush=True, file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
            raise

    def resolve(
        self,
        text: Union[str, List[str], List[Dict[str, Any]]],
        entities: Optional[Union[List[Entity], List[List[Entity]]]] = None,
        pipeline_id: Optional[str] = None,
        **kwargs
    ) -> Union[List[CoreferenceChain], List[List[CoreferenceChain]]]:
        """
        Resolve coreferences in text or list of documents.
        Handles batch processing with progress tracking.

        Args:
            text: Input text or list of documents
            entities: List of entities or list of list of entities (optional)
            pipeline_id: Optional pipeline ID for progress tracking
            **kwargs: Resolution options

        Returns:
            Union[List[CoreferenceChain], List[List[CoreferenceChain]]]: Resolved coreference chains
        """
        if isinstance(text, list):
            # Handle batch resolution with progress tracking
            tracking_id = self.progress_tracker.start_tracking(
                module="semantic_extract",
                submodule="CoreferenceResolver",
                message=f"Batch resolving coreferences from {len(text)} documents",
                pipeline_id=pipeline_id,
            )

            try:
                results = []
                total_items = len(text)
                total_chains_count = 0
                
                # Determine update interval
                if total_items <= 10:
                    update_interval = 1
                else:
                    update_interval = max(1, min(10, total_items // 100))
                
                # Initial progress update
                self.progress_tracker.update_progress(
                    tracking_id,
                    processed=0,
                    total=total_items,
                    message=f"Starting batch resolution... 0/{total_items} (remaining: {total_items})"
                )

                for idx, item in enumerate(text):
                    # Prepare arguments for single item
                    doc_text = item["content"] if isinstance(item, dict) and "content" in item else str(item)
                    
                    doc_entities = None
                    if entities and idx < len(entities):
                        doc_entities = entities[idx]

                    # Resolve
                    chains = self.resolve_coreferences(doc_text, entities=doc_entities, **kwargs)

                    # Add provenance metadata
                    for chain in chains:
                        # Update chain metadata
                        if chain.metadata is None:
                            chain.metadata = {}
                        chain.metadata["batch_index"] = idx
                        if isinstance(item, dict) and "id" in item:
                            chain.metadata["document_id"] = item["id"]

                        # Update mentions metadata
                        for mention in chain.mentions:
                            if mention.metadata is None:
                                mention.metadata = {}
                            mention.metadata["batch_index"] = idx
                            if isinstance(item, dict) and "id" in item:
                                mention.metadata["document_id"] = item["id"]
                        
                        # Update representative metadata
                        if chain.representative:
                            if chain.representative.metadata is None:
                                chain.representative.metadata = {}
                            chain.representative.metadata["batch_index"] = idx
                            if isinstance(item, dict) and "id" in item:
                                chain.representative.metadata["document_id"] = item["id"]

                    results.append(chains)
                    total_chains_count += len(chains)

                    # Update progress
                    if (idx + 1) % update_interval == 0 or (idx + 1) == total_items:
                        remaining = total_items - (idx + 1)
                        self.progress_tracker.update_progress(
                            tracking_id,
                            processed=idx + 1,
                            total=total_items,
                            message=f"Processing... {idx + 1}/{total_items} (remaining: {remaining}) - Resolved {total_chains_count} chains"
                        )

                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Batch resolution completed. Processed {len(results)} documents, resolved {total_chains_count} chains.",
                )
                return results

            except Exception as e:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message=str(e)
                )
                raise

        else:
            # Single item
            return self.resolve_coreferences(text, entities=entities, **kwargs)

    def _extract_mentions(self, text: str) -> List[Mention]:
        """Extract all mentions from text."""
        mentions = []

        # Extract pronouns
        pronoun_patterns = {
            "he": r"\bhe\b",
            "she": r"\bshe\b",
            "it": r"\bit\b",
            "they": r"\bthey\b",
            "his": r"\bhis\b",
            "her": r"\bher\b",
            "their": r"\btheir\b",
        }

        total_patterns = len(pronoun_patterns)
        if total_patterns <= 10:
            pattern_update_interval = 1  # Update every pattern for small datasets
        else:
            pattern_update_interval = max(1, min(5, total_patterns // 20))

        for pattern_idx, (pronoun, pattern) in enumerate(pronoun_patterns.items(), 1):
            # Count matches first
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            total_matches = len(matches)
            
            for match in matches:
                mentions.append(
                    Mention(
                        text=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        mention_type="pronoun",
                        metadata={"pronoun": pronoun},
                    )
                )

        return mentions

    def build_coreference_chains(
        self, mentions: List[Mention], **options
    ) -> List[CoreferenceChain]:
        """
        Build coreference chains from mentions.

        Args:
            mentions: List of mentions
            **options: Chain building options

        Returns:
            list: List of coreference chains
        """
        return self.chain_builder.build_coreference_chains(mentions, **options)

    def resolve_pronouns(self, text: str, **options) -> List[Tuple[str, str]]:
        """
        Resolve pronoun references in text.

        Args:
            text: Input text
            **options: Resolution options

        Returns:
            list: List of (pronoun, antecedent) tuples
        """
        mentions = self._extract_mentions(text)
        return self.pronoun_resolver.resolve_pronouns(text, mentions, **options)

    def detect_entity_coreferences(
        self, text: str, entities: List[Entity], **options
    ) -> List[CoreferenceChain]:
        """
        Detect entity coreferences in text.

        Args:
            text: Input text
            entities: List of entities
            **options: Detection options

        Returns:
            list: List of coreference chains
        """
        # Convert entities to mentions
        mentions = [
            Mention(
                text=e.text,
                start_char=e.start_char,
                end_char=e.end_char,
                mention_type="entity",
                metadata={"entity_label": e.label},
            )
            for e in entities
        ]

        return self.entity_detector.detect_entity_coreferences(
            text, mentions, **options
        )


class PronounResolver:
    """Pronoun resolution engine."""

    def __init__(self, **config):
        """Initialize pronoun resolver."""
        self.logger = get_logger("pronoun_resolver")
        self.config = config

    def resolve_pronouns(
        self, text: str, mentions: List[Mention], **options
    ) -> List[Tuple[str, str]]:
        """
        Resolve pronoun references in text.

        Args:
            text: Input text
            mentions: List of mentions
            **options: Resolution options

        Returns:
            list: List of (pronoun, antecedent) tuples
        """
        resolutions = []

        # Get pronouns and entities
        pronouns = [m for m in mentions if m.mention_type == "pronoun"]
        entities = [
            m
            for m in mentions
            if m.mention_type == "entity" or m.mention_type == "nominal"
        ]

        # Simple resolution: find closest preceding entity with compatible type
        pronoun_types = {
            "he": ["PERSON"],
            "him": ["PERSON"],
            "his": ["PERSON"],
            "she": ["PERSON"],
            "her": ["PERSON"],
            "it": ["ORG", "GPE", "LOC", "PRODUCT", "EVENT", "FAC", "WORK_OF_ART", "LAW", "LANGUAGE", "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"],
            "its": ["ORG", "GPE", "LOC", "PRODUCT", "EVENT", "FAC", "WORK_OF_ART", "LAW", "LANGUAGE", "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"],
            "they": ["ORG", "GPE", "PERSON", "NORP"], # Can be groups of people or organizations
            "them": ["ORG", "GPE", "PERSON", "NORP"],
            "their": ["ORG", "GPE", "PERSON", "NORP"],
        }

        for pronoun in pronouns:
            # Find preceding entities
            preceding = [e for e in entities if e.end_char < pronoun.start_char]

            if preceding:
                pronoun_lower = pronoun.text.lower()
                compatible_types = pronoun_types.get(pronoun_lower)
                
                antecedent = None
                
                if compatible_types:
                    # Filter by type
                    compatible = [
                        e for e in preceding 
                        if e.metadata and e.metadata.get("entity_label") in compatible_types
                    ]
                    if compatible:
                        # Take closest compatible
                        antecedent = max(compatible, key=lambda e: e.end_char)
                
                # Fallback to closest if no compatible found or pronoun type unknown
                if antecedent is None:
                    antecedent = max(preceding, key=lambda e: e.end_char)

                resolutions.append((pronoun.text, antecedent.text))
                
                # Update pronoun metadata and link to antecedent
                pronoun.entity_id = antecedent.text
                pronoun.metadata["antecedent_text"] = antecedent.text

        return resolutions


class EntityCoreferenceDetector:
    """Entity coreference detection."""

    def __init__(self, **config):
        """Initialize entity coreference detector."""
        self.logger = get_logger("entity_coreference_detector")
        self.config = config

    def detect_entity_coreferences(
        self, text: str, mentions: List[Mention], **options
    ) -> List[CoreferenceChain]:
        """
        Detect entity coreferences in text.

        Args:
            text: Input text
            mentions: List of mentions
            **options: Detection options

        Returns:
            list: List of coreference chains
        """
        chains = []

        # Group mentions by text similarity
        entity_mentions = [
            m for m in mentions if m.mention_type in ["entity", "nominal"]
        ]

        # Simple grouping by exact text match
        text_groups = {}
        for mention in entity_mentions:
            key = mention.text.lower()
            if key not in text_groups:
                text_groups[key] = []
            text_groups[key].append(mention)

        # Create chains from groups
        for key, group_mentions in text_groups.items():
            if len(group_mentions) > 1:
                # Use first mention as representative
                representative = group_mentions[0]
                chain = CoreferenceChain(
                    mentions=group_mentions, representative=representative
                )
                chains.append(chain)

        return chains


class CoreferenceChainBuilder:
    """Coreference chain construction."""

    def __init__(self, **config):
        """Initialize coreference chain builder."""
        self.logger = get_logger("coreference_chain_builder")
        self.config = config

    def build_coreference_chains(
        self, mentions: List[Mention], **options
    ) -> List[CoreferenceChain]:
        """
        Build coreference chains from mentions.

        Args:
            mentions: List of mentions
            **options: Chain building options

        Returns:
            list: List of coreference chains
        """
        chains = []
        processed_indices = set()

        for i, mention in enumerate(mentions):
            if i in processed_indices:
                continue

            # Start a new group
            group = [mention]
            processed_indices.add(i)

            # Find related mentions
            for j, other in enumerate(mentions):
                if j in processed_indices:
                    continue

                is_related = False

                # 1. Text similarity
                if (
                    other.text.lower() == mention.text.lower()
                    or self._similar_mentions(mention.text, other.text)
                ):
                    is_related = True
                
                # 2. Pronoun resolution (entity_id matches text or entity_id matches entity_id)
                elif mention.entity_id and (
                    mention.entity_id == other.text 
                    or mention.entity_id == other.entity_id
                ):
                    is_related = True
                elif other.entity_id and (
                    other.entity_id == mention.text
                    or other.entity_id == mention.entity_id
                ):
                    is_related = True

                if is_related:
                    group.append(other)
                    processed_indices.add(j)

            if len(group) > 1:
                # Representative is first (leftmost) mention, or prefer entity over pronoun
                # Prefer entity mention as representative
                entities = [m for m in group if m.mention_type != "pronoun"]
                if entities:
                    representative = min(entities, key=lambda m: m.start_char)
                else:
                    representative = min(group, key=lambda m: m.start_char)

                chain = CoreferenceChain(
                    mentions=group,
                    representative=representative,
                    entity_type=representative.metadata.get("entity_label"),
                )
                chains.append(chain)

        return chains

    def _similar_mentions(self, text1: str, text2: str) -> bool:
        """Check if two mentions are similar."""
        t1_lower = text1.lower()
        t2_lower = text2.lower()

        # Exact match
        if t1_lower == t2_lower:
            return True

        # One contains the other
        if t1_lower in t2_lower or t2_lower in t1_lower:
            return True

        # Word overlap
        words1 = set(t1_lower.split())
        words2 = set(t2_lower.split())
        overlap = (
            len(words1 & words2) / max(len(words1), len(words2))
            if words1 or words2
            else 0
        )

        return overlap > 0.7
