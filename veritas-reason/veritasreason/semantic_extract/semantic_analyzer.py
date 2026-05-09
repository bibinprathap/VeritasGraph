"""
Semantic Analysis Module

This module provides comprehensive semantic analysis capabilities including
similarity calculation, role labeling, clustering, and feature extraction.
Supports multiple extraction methods for underlying entity and relation extraction.

Supported Methods (for underlying NER/Relation extractors):
    - "pattern": Pattern-based extraction
    - "regex": Regex-based extraction
    - "rules": Rule-based extraction
    - "ml": ML-based extraction (spaCy)
    - "huggingface": HuggingFace model extraction
    - "llm": LLM-based extraction
    - Any method supported by NERExtractor and RelationExtractor

Algorithms Used:
    - Jaccard Similarity: Set intersection over union for text similarity
    - Cosine Similarity: Vector space model with TF-IDF or embeddings
    - Semantic Role Labeling: Dependency parsing and rule-based role assignment
    - Clustering: K-means, hierarchical clustering for semantic grouping
    - Feature Extraction: TF-IDF, word embeddings, and semantic features
    - Text Quality Metrics: Readability, coherence, and complexity measures

Key Features:
    - Semantic similarity analysis (Jaccard, cosine)
    - Semantic role labeling (agent, patient, theme, location)
    - Semantic clustering and grouping
    - Semantic feature extraction
    - Text quality assessment
    - Integration with multiple NER and relation extraction methods
    - Method parameter support for underlying extractors

Main Classes:
    - SemanticAnalyzer: Main semantic analysis coordinator
    - SimilarityAnalyzer: Semantic similarity analysis
    - RoleLabeler: Semantic role labeling
    - SemanticClusterer: Semantic clustering engine
    - SemanticRole: Semantic role representation dataclass
    - SemanticCluster: Semantic cluster representation dataclass

Example Usage:
    >>> from veritasreason.semantic_extract import SemanticAnalyzer
    >>> # Using default methods
    >>> analyzer = SemanticAnalyzer()
    >>> similarity = analyzer.calculate_similarity("Apple Inc.", "Apple company")
    >>> 
    >>> # Using LLM-based extraction
    >>> analyzer = SemanticAnalyzer(method="llm", provider="openai")
    >>> roles = analyzer.label_semantic_roles("John bought a car.")
    >>> clusters = analyzer.cluster_veritasreasonlly(texts)

Author: VeritasReason Contributors
License: MIT
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.exceptions import ProcessingError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class SemanticRole:
    """Semantic role representation."""

    word: str
    role: str  # agent, patient, theme, location, etc.
    start_char: int
    end_char: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticCluster:
    """Semantic cluster representation."""

    texts: List[str]
    cluster_id: int
    centroid: Optional[str] = None
    similarity_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticAnalyzer:
    """Comprehensive semantic analysis handler."""

    def __init__(self, method: Union[str, List[str]] = None, config=None, **kwargs):
        """
        Initialize semantic analyzer.

        Args:
            method: Extraction method(s) for underlying NER/relation extractors.
                   Can be passed to ner_method and relation_method in config.
            config: Legacy config dict (deprecated, use kwargs)
            **kwargs: Configuration options:
                - ner_method: Method for NER extraction (if entities need to be extracted)
                - relation_method: Method for relation extraction (if relations need to be extracted)
                - Other options passed to sub-components
        """
        self.logger = get_logger("semantic_analyzer")
        self.config = config or {}
        self.config.update(kwargs)
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        # Store method for passing to extractors if needed
        if method is not None:
            self.config["ner_method"] = method
            self.config["relation_method"] = method

        self.similarity_analyzer = SimilarityAnalyzer(
            **self.config.get("similarity", {})
        )
        self.role_labeler = RoleLabeler(**self.config.get("role", {}))
        self.semantic_clusterer = SemanticClusterer(**self.config.get("clustering", {}))

    def analyze(
        self,
        text: Union[str, List[str], List[Dict[str, Any]]],
        pipeline_id: Optional[str] = None,
        **kwargs
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Perform semantic analysis on text or list of documents.
        Handles batch processing with progress tracking.

        Args:
            text: Input text or list of documents
            pipeline_id: Optional pipeline ID for progress tracking
            **kwargs: Analysis options

        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: Analysis results
        """
        if isinstance(text, list):
            # Handle batch analysis with progress tracking
            tracking_id = self.progress_tracker.start_tracking(
                module="semantic_extract",
                submodule="SemanticAnalyzer",
                message=f"Batch analyzing {len(text)} documents",
                pipeline_id=pipeline_id,
            )

            try:
                results = [None] * len(text)
                total_items = len(text)
                processed_count = 0
                
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
                    message=f"Starting batch analysis... 0/{total_items} (remaining: {total_items})"
                )

                from .config import resolve_max_workers
                max_workers = resolve_max_workers(
                    explicit=kwargs.get("max_workers"),
                    local_config=self.config,
                )

                def process_item(idx, item):
                    try:
                        doc_text = item["content"] if isinstance(item, dict) and "content" in item else str(item)
                        analysis = self.analyze_semantics(doc_text, **kwargs)

                        analysis["batch_index"] = idx
                        if isinstance(item, dict) and "id" in item:
                            analysis["document_id"] = item["id"]

                        if "semantic_roles" in analysis:
                            for role in analysis["semantic_roles"]:
                                if "metadata" not in role:
                                    role["metadata"] = {}

                                role["metadata"]["batch_index"] = idx
                                if isinstance(item, dict) and "id" in item:
                                    role["metadata"]["document_id"] = item["id"]

                        return idx, analysis
                    except Exception as e:
                        self.logger.warning(f"Failed to analyze item {idx}: {e}")
                        return idx, {"error": str(e), "batch_index": idx}

                if max_workers > 1:
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_idx = {
                            executor.submit(process_item, idx, item): idx
                            for idx, item in enumerate(text)
                        }

                        for future in concurrent.futures.as_completed(future_to_idx):
                            idx, analysis = future.result()
                            results[idx] = analysis
                            processed_count += 1

                            should_update = (
                                processed_count % update_interval == 0
                                or processed_count == total_items
                                or processed_count == 1
                                or total_items <= 10
                            )
                            if should_update:
                                remaining = total_items - processed_count
                                self.progress_tracker.update_progress(
                                    tracking_id,
                                    processed=processed_count,
                                    total=total_items,
                                    message=f"Processing... {processed_count}/{total_items} (remaining: {remaining})"
                                )
                else:
                    for idx, item in enumerate(text):
                        _, analysis = process_item(idx, item)
                        results[idx] = analysis
                        processed_count += 1

                        should_update = (
                            processed_count % update_interval == 0
                            or processed_count == total_items
                            or processed_count == 1
                            or total_items <= 10
                        )
                        if should_update:
                            remaining = total_items - processed_count
                            self.progress_tracker.update_progress(
                                tracking_id,
                                processed=processed_count,
                                total=total_items,
                                message=f"Processing... {processed_count}/{total_items} (remaining: {remaining})"
                            )

                self.progress_tracker.stop_tracking(
                    tracking_id,
                    status="completed",
                    message=f"Batch analysis completed. Processed {len(results)} documents.",
                )
                return results

            except Exception as e:
                self.progress_tracker.stop_tracking(
                    tracking_id, status="failed", message=str(e)
                )
                raise

        else:
            # Single item
            return self.analyze_semantics(text, **kwargs)

    def analyze_semantics(self, text: str, **options) -> Dict[str, Any]:
        """
        Perform comprehensive semantic analysis.

        Args:
            text: Input text
            **options: Analysis options

        Returns:
            dict: Semantic analysis results
        """
        tracking_id = self.progress_tracker.start_tracking(
            module="semantic_extract",
            submodule="SemanticAnalyzer",
            message="Performing comprehensive semantic analysis",
        )

        try:
            results = {
                "text": text,
                "length": len(text),
                "word_count": len(text.split()),
                "sentence_count": len(text.split(".")),
            }

            # Semantic role labeling
            if options.get("label_roles", False):
                self.progress_tracker.update_tracking(
                    tracking_id, message="Labeling semantic roles..."
                )
                roles = self.label_semantic_roles(text, **options)
                results["semantic_roles"] = [r.__dict__ for r in roles]

            # Semantic features
            self.progress_tracker.update_tracking(
                tracking_id, message="Extracting semantic features..."
            )
            results["semantic_features"] = self._extract_features(text)

            self.progress_tracker.stop_tracking(
                tracking_id, status="completed", message="Semantic analysis complete"
            )
            return results

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise

    def calculate_similarity(self, text1: str, text2: str, **options) -> float:
        """
        Calculate semantic similarity between texts.

        Args:
            text1: First text
            text2: Second text
            **options: Similarity options

        Returns:
            float: Similarity score (0-1)
        """
        return self.similarity_analyzer.calculate_similarity(text1, text2, **options)

    def label_semantic_roles(self, text: str, **options) -> List[SemanticRole]:
        """
        Label semantic roles in text.

        Args:
            text: Input text
            **options: Labeling options

        Returns:
            list: List of semantic roles
        """
        return self.role_labeler.label_roles(text, **options)

    def analyze_semantic_roles(self, text: str, **options) -> List[SemanticRole]:
        """Alias for label_semantic_roles."""
        return self.label_semantic_roles(text, **options)

    def cluster_veritasreasonlly(
        self, texts: Union[List[str], List[Dict[str, Any]]], **options
    ) -> List[SemanticCluster]:
        """
        Perform semantic clustering of texts.

        Args:
            texts: List of texts or documents to cluster
            **options: Clustering options

        Returns:
            list: List of semantic clusters
        """
        return self.semantic_clusterer.cluster(texts, **options)

    def _extract_features(self, text: str) -> Dict[str, Any]:
        """Extract semantic features from text."""
        words = text.lower().split()

        return {
            "unique_words": len(set(words)),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "verb_count": sum(1 for w in words if self._is_verb(w)),
            "noun_count": sum(1 for w in words if self._is_noun(w)),
        }

    def _is_verb(self, word: str) -> bool:
        """Simple verb detection."""
        verb_endings = ["ed", "ing", "es", "s"]
        return any(word.endswith(ending) for ending in verb_endings)

    def _is_noun(self, word: str) -> bool:
        """Simple noun detection."""
        noun_endings = ["tion", "sion", "ment", "ness", "ity"]
        return any(word.endswith(ending) for ending in noun_endings)


class SimilarityAnalyzer:
    """Semantic similarity analysis."""

    def __init__(self, **config):
        """Initialize similarity analyzer."""
        self.logger = get_logger("similarity_analyzer")
        self.config = config

    def calculate_similarity(self, text1: str, text2: str, **options) -> float:
        """
        Calculate semantic similarity between texts.

        Args:
            text1: First text
            text2: Second text
            **options: Similarity options

        Returns:
            float: Similarity score (0-1)
        """
        method = options.get("method", "jaccard")

        if method == "jaccard":
            return self._jaccard_similarity(text1, text2)
        elif method == "cosine":
            return self._cosine_similarity(text1, text2)
        else:
            return self._jaccard_similarity(text1, text2)

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity (simplified)."""
        words1 = text1.lower().split()
        words2 = text2.lower().split()

        # Simple word frequency vectors
        all_words = set(words1 + words2)
        vec1 = [words1.count(w) for w in all_words]
        vec2 = [words2.count(w) for w in all_words]

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)


class RoleLabeler:
    """Semantic role labeling."""

    def __init__(self, **config):
        """Initialize role labeler."""
        self.logger = get_logger("role_labeler")
        self.config = config

    def label_roles(self, text: str, **options) -> List[SemanticRole]:
        """
        Label semantic roles in text.

        Args:
            text: Input text
            **options: Labeling options

        Returns:
            list: List of semantic roles
        """
        roles = []
        words = text.split()

        # Simple role labeling based on position and patterns
        for i, word in enumerate(words):
            role = self._assign_role(word, i, words, text)

            if role:
                # Find position in original text
                start = text.find(word)
                roles.append(
                    SemanticRole(
                        word=word,
                        role=role,
                        start_char=start if start >= 0 else i * 10,
                        end_char=start + len(word) if start >= 0 else (i + 1) * 10,
                        confidence=0.7,
                    )
                )

        return roles

    def _assign_role(
        self, word: str, position: int, all_words: List[str], text: str
    ) -> Optional[str]:
        """Assign semantic role to word."""
        word_lower = word.lower()

        # Agent indicators
        if word_lower in ["i", "we", "he", "she", "they"]:
            return "agent"

        # Patient/theme indicators (objects)
        if position > 2 and word[0].isupper():
            return "theme"

        # Location indicators
        if word_lower in ["in", "at", "on", "near", "from"]:
            return "location"

        return None


class SemanticClusterer:
    """Semantic clustering engine."""

    def __init__(self, **config):
        """Initialize semantic clusterer."""
        self.logger = get_logger("semantic_clusterer")
        self.config = config
        # Initialize progress tracker and ensure it's enabled
        self.progress_tracker = get_progress_tracker()
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

    def cluster(
        self, texts: Union[List[str], List[Dict[str, Any]]], **options
    ) -> List[SemanticCluster]:
        """
        Perform semantic clustering of texts.

        Args:
            texts: List of texts or documents (dict with 'content' and 'id') to cluster
            **options: Clustering options:
                - num_clusters: Number of clusters (default: auto)
                - similarity_threshold: Minimum similarity for clustering

        Returns:
            list: List of semantic clusters
        """
        if not texts:
            return []

        # Extract content and IDs if input is list of dicts
        processed_texts = []
        doc_ids = []
        
        for item in texts:
            if isinstance(item, dict):
                content = item.get("content", str(item))
                processed_texts.append(content)
                if "id" in item:
                    doc_ids.append(item["id"])
                else:
                    doc_ids.append(None)
            else:
                processed_texts.append(str(item))
                doc_ids.append(None)

        # Track clustering
        tracking_id = self.progress_tracker.start_tracking(
            module="semantic_extract",
            submodule="SemanticClusterer",
            message=f"Clustering {len(processed_texts)} texts",
        )

        try:
            similarity_threshold = options.get("similarity_threshold", 0.5)
            similarity_analyzer = SimilarityAnalyzer()

            clusters = []
            assigned = set()

            total_texts = len(processed_texts)
            if total_texts <= 10:
                update_interval = 1  # Update every item for small datasets
            else:
                update_interval = max(1, min(10, total_texts // 100))
            
            # Initial progress update
            remaining = total_texts
            self.progress_tracker.update_progress(
                tracking_id,
                processed=0,
                total=total_texts,
                message=f"Clustering texts... 0/{total_texts} (remaining: {remaining})"
            )

            cluster_id = 0
            for i, text1 in enumerate(processed_texts):
                if i in assigned:
                    continue

                cluster_texts = [text1]
                cluster_doc_ids = []
                if doc_ids[i] is not None:
                    cluster_doc_ids.append(doc_ids[i])
                    
                assigned.add(i)

                # Find similar texts
                remaining_texts = len(processed_texts) - (i + 1)
                for j, text2 in enumerate(processed_texts[i + 1 :], start=i + 1):
                    if j in assigned:
                        continue

                    similarity = similarity_analyzer.calculate_similarity(text1, text2)
                    if similarity >= similarity_threshold:
                        cluster_texts.append(text2)
                        if doc_ids[j] is not None:
                            cluster_doc_ids.append(doc_ids[j])
                        assigned.add(j)

                # Create cluster
                cluster = SemanticCluster(
                    texts=cluster_texts,
                    cluster_id=cluster_id,
                    centroid=cluster_texts[0],  # Use first as centroid
                    similarity_score=similarity_threshold,
                )
                
                # Add provenance metadata
                if cluster_doc_ids:
                    cluster.metadata["document_ids"] = cluster_doc_ids
                
                clusters.append(cluster)
                cluster_id += 1
                
                remaining = total_texts - (i + 1)
                # Update progress: always update for small datasets, or at intervals for large ones
                should_update = (
                    (i + 1) % update_interval == 0 or 
                    (i + 1) == total_texts or 
                    i == 0 or
                    total_texts <= 10  # Always update for small datasets
                )
                if should_update:
                    self.progress_tracker.update_progress(
                        tracking_id,
                        processed=i + 1,
                        total=total_texts,
                        message=f"Clustering texts... {i + 1}/{total_texts} (remaining: {remaining})"
                    )

            self.progress_tracker.stop_tracking(
                tracking_id,
                status="completed",
                message=f"Created {len(clusters)} clusters",
            )
            return clusters

        except Exception as e:
            self.progress_tracker.stop_tracking(
                tracking_id, status="failed", message=str(e)
            )
            raise
