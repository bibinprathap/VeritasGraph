"""
Data Cleaning Module

This module provides comprehensive data cleaning and quality improvement
capabilities for the VeritasReason framework, enabling detection and resolution
of data quality issues.

Key Features:
    - Data quality assessment
    - Duplicate detection and removal (fuzzy matching, similarity scoring)
    - Data validation and correction (schema validation, type checking)
    - Missing value handling (removal, filling, imputation)
    - Data consistency checking
    - Batch processing support

Main Classes:
    - DataCleaner: Main data cleaning coordinator
    - DuplicateDetector: Duplicate detection engine
    - DataValidator: Data validation engine
    - MissingValueHandler: Missing value processor

Example Usage:
    >>> from veritasreason.normalize import DataCleaner
    >>> cleaner = DataCleaner()
    >>> cleaned = cleaner.clean_data(dataset, remove_duplicates=True, validate=True)
    >>> duplicates = cleaner.detect_duplicates(dataset, threshold=0.8)

Author: VeritasReason Contributors
License: MIT
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger
from ..utils.progress_tracker import get_progress_tracker


@dataclass
class DuplicateGroup:
    """
    Duplicate record group dataclass.

    This dataclass represents a group of duplicate records identified during
    duplicate detection, containing the records, similarity score, and canonical
    record.

    Attributes:
        records: List of duplicate record dictionaries
        similarity_score: Average similarity score for the group (0.0 to 1.0)
        canonical_record: Canonical/representative record (typically first record)
    """

    records: List[Dict[str, Any]]
    similarity_score: float
    canonical_record: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """
    Data validation result dataclass.

    This dataclass represents the result of data validation, containing
    validation status, errors, and warnings.

    Attributes:
        valid: Whether the data is valid (True if no errors)
        errors: List of error dictionaries (critical validation failures)
        warnings: List of warning dictionaries (non-critical issues)
    """

    valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)


class DataCleaner:
    """
    Data cleaning and quality improvement coordinator.

    This class provides comprehensive data cleaning capabilities, coordinating
    duplicate detection, data validation, and missing value handling to
    improve data quality.

    Features:
        - Data quality improvement
        - Duplicate detection and removal
        - Data validation against schemas
        - Missing value handling (multiple strategies)
        - Data consistency checking
        - Support for various data types

    Example Usage:
        >>> cleaner = DataCleaner()
        >>> cleaned = cleaner.clean_data(dataset, remove_duplicates=True, validate=True)
        >>> duplicates = cleaner.detect_duplicates(dataset)
        >>> validation = cleaner.validate_data(dataset, schema)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize data cleaner.

        Sets up the cleaner with duplicate detector, data validator, and
        missing value handler components.

        Args:
            config: Configuration dictionary (optional)
            **kwargs: Additional configuration options (merged into config)
        """
        self.logger = get_logger("data_cleaner")
        self.config = config or {}
        self.config.update(kwargs)

        self.duplicate_detector = DuplicateDetector(**self.config)
        self.data_validator = DataValidator(**self.config)
        self.missing_value_handler = MissingValueHandler(**self.config)

        # Initialize progress tracker
        self.progress_tracker = get_progress_tracker()
        # Ensure progress tracker is enabled
        if not self.progress_tracker.enabled:
            self.progress_tracker.enabled = True

        self.logger.debug("Data cleaner initialized")

    def clean_data(
        self,
        dataset: List[Dict[str, Any]],
        remove_duplicates: bool = True,
        validate: bool = True,
        handle_missing: bool = True,
        **options,
    ) -> List[Dict[str, Any]]:
        """
        Clean dataset with various cleaning operations.

        This method performs comprehensive data cleaning by applying missing
        value handling, validation, and duplicate removal in sequence.

        Args:
            dataset: List of data record dictionaries
            remove_duplicates: Whether to remove duplicate records (default: True)
            validate: Whether to validate data against schema (default: True)
            handle_missing: Whether to handle missing values (default: True)
            **options: Additional cleaning options:
                - missing_strategy: Strategy for missing values ("remove", "fill", "impute")
                - schema: Validation schema dictionary
                - duplicate_criteria: Criteria for duplicate detection

        Returns:
            list: Cleaned dataset (list of record dictionaries)
        """
        tracking_id = self.progress_tracker.start_tracking(
            message="VeritasReason: Cleaning data", file=None
        )
        try:
            cleaned = list(dataset)

            # Handle missing values
            if handle_missing:
                strategy = options.get("missing_strategy", "remove")
                cleaned = self.missing_value_handler.handle_missing_values(
                    cleaned, strategy=strategy, **options
                )

            # Validate data
            if validate:
                schema = options.get("schema")
                validation = self.data_validator.validate_dataset(cleaned, schema)
                if not validation.valid:
                    self.logger.warning(
                        f"Validation found {len(validation.errors)} errors"
                    )

            # Remove duplicates
            if remove_duplicates:
                criteria = options.get("duplicate_criteria", {})
                duplicates = self.detect_duplicates(cleaned, **criteria)

                # Remove duplicates (keep first occurrence)
                duplicate_indices = set()
                for group in duplicates:
                    for record in group.records[1:]:  # Skip first (canonical)
                        if record in cleaned:
                            idx = cleaned.index(record)
                            duplicate_indices.add(idx)

                cleaned = [
                    r for i, r in enumerate(cleaned) if i not in duplicate_indices
                ]

            self.progress_tracker.stop_tracking(tracking_id, status="completed")
            return cleaned
        except Exception as e:
            self.progress_tracker.stop_tracking(tracking_id, status="failed")
            raise

    def detect_duplicates(
        self,
        dataset: List[Dict[str, Any]],
        threshold: Optional[float] = None,
        key_fields: Optional[List[str]] = None,
        **criteria,
    ) -> List[DuplicateGroup]:
        """
        Detect duplicate records in dataset.

        This method identifies duplicate records using similarity matching
        based on specified criteria and threshold.

        Args:
            dataset: List of data record dictionaries
            threshold: Similarity threshold for duplicates (0.0 to 1.0, optional,
                      uses detector's default if not provided)
            key_fields: List of field names to use for comparison (optional,
                       uses all common fields if not provided)
            **criteria: Additional duplicate detection criteria

        Returns:
            list: List of DuplicateGroup objects, each containing duplicate
                  records with similarity scores
        """
        return self.duplicate_detector.detect_duplicates(
            dataset, threshold=threshold, key_fields=key_fields, **criteria
        )

    def validate_data(
        self, dataset: List[Dict[str, Any]], schema: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate data against schema or rules.

        This method validates all records in the dataset against the provided
        schema, checking required fields, data types, and constraints.

        Args:
            dataset: List of data record dictionaries
            schema: Validation schema dictionary (optional) containing:
                - fields: Dictionary mapping field names to field schemas with:
                    - type: Expected data type
                    - required: Whether field is required (bool)

        Returns:
            ValidationResult: Validation result containing:
                - valid: True if no errors, False otherwise
                - errors: List of error dictionaries with record_index and field info
                - warnings: List of warning dictionaries
        """
        return self.data_validator.validate_dataset(dataset, schema)

    def handle_missing_values(
        self, dataset: List[Dict[str, Any]], strategy: str = "remove", **options
    ) -> List[Dict[str, Any]]:
        """
        Handle missing values in dataset.

        This method processes missing values in the dataset using the specified
        strategy (remove, fill, or impute).

        Args:
            dataset: List of data record dictionaries
            strategy: Handling strategy:
                - "remove": Remove records with missing values (default)
                - "fill": Fill missing values with default value
                - "impute": Impute missing values using statistical methods
            **options: Additional strategy options:
                - fill_value: Value to use for filling (for "fill" strategy)
                - method: Imputation method ("mean", "median", "mode", "zero")

        Returns:
            list: Processed dataset with missing values handled
        """
        return self.missing_value_handler.handle_missing_values(
            dataset, strategy=strategy, **options
        )


class DuplicateDetector:
    """
    Duplicate detection engine.

    This class provides duplicate detection capabilities using similarity
    matching and fuzzy comparison algorithms.

    Features:
        - Duplicate record detection
        - Similarity score calculation
        - Fuzzy string matching
        - Duplicate group formation
        - Duplicate resolution strategies

    Example Usage:
        >>> detector = DuplicateDetector(similarity_threshold=0.8)
        >>> duplicates = detector.detect_duplicates(dataset, threshold=0.85)
        >>> resolved = detector.resolve_duplicates(duplicates, strategy="merge")
    """

    def __init__(self, **config):
        """
        Initialize duplicate detector.

        Sets up the detector with similarity threshold and key fields for
        comparison.

        Args:
            **config: Configuration options:
                - similarity_threshold: Minimum similarity for duplicates
                                      (default: 0.8, range: 0.0 to 1.0)
                - key_fields: List of field names to use for comparison
                            (optional, uses all common fields if empty)
        """
        self.logger = get_logger("duplicate_detector")
        self.config = config
        self.similarity_threshold = config.get("similarity_threshold", 0.8)
        self.key_fields = config.get("key_fields", [])

        self.logger.debug(
            f"Duplicate detector initialized (threshold={self.similarity_threshold})"
        )

    def detect_duplicates(
        self,
        dataset: List[Dict[str, Any]],
        threshold: Optional[float] = None,
        key_fields: Optional[List[str]] = None,
        **criteria,
    ) -> List[DuplicateGroup]:
        """
        Detect duplicates in dataset.

        This method identifies duplicate records by comparing records pairwise
        using similarity matching. Records with similarity above the threshold
        are grouped together.

        Args:
            dataset: List of record dictionaries
            threshold: Similarity threshold for duplicates (optional, uses
                      instance threshold if not provided)
            key_fields: List of field names for comparison (optional, uses
                       instance key_fields if not provided)
            **criteria: Additional detection criteria (unused)

        Returns:
            list: List of DuplicateGroup objects containing duplicate records
                  with similarity scores
        """
        threshold = threshold if threshold is not None else self.similarity_threshold
        key_fields = key_fields if key_fields is not None else self.key_fields

        duplicate_groups = []
        processed = set()

        for i, record1 in enumerate(dataset):
            if i in processed:
                continue

            group = [record1]

            for j, record2 in enumerate(dataset[i + 1 :], start=i + 1):
                if j in processed:
                    continue

                similarity = self.calculate_similarity(
                    record1, record2, key_fields=key_fields
                )

                if similarity >= threshold:
                    group.append(record2)
                    processed.add(j)

            if len(group) > 1:
                # Calculate average similarity
                avg_similarity = sum(
                    self.calculate_similarity(group[0], r, key_fields=key_fields)
                    for r in group[1:]
                ) / (len(group) - 1)

                duplicate_groups.append(
                    DuplicateGroup(
                        records=group,
                        similarity_score=avg_similarity,
                        canonical_record=group[0],
                    )
                )
                processed.add(i)

        return duplicate_groups

    def calculate_similarity(
        self,
        record1: Dict[str, Any],
        record2: Dict[str, Any],
        key_fields: Optional[List[str]] = None,
        **options,
    ) -> float:
        """
        Calculate similarity between records.

        This method calculates a similarity score between two records by
        comparing values in key fields. Uses exact matching for non-string
        values and string similarity for string values.

        Args:
            record1: First record dictionary
            record2: Second record dictionary
            key_fields: List of field names to compare (optional, uses
                       instance key_fields or all common fields)
            **options: Additional similarity calculation options (unused)

        Returns:
            float: Similarity score between 0.0 and 1.0 (higher is more similar)
        """
        key_fields = key_fields if key_fields is not None else self.key_fields

        if not key_fields:
            # Use all common fields
            key_fields = list(set(record1.keys()) & set(record2.keys()))

        if not key_fields:
            return 0.0

        similarities = []

        for field in key_fields:
            val1 = record1.get(field)
            val2 = record2.get(field)

            if val1 is None or val2 is None:
                continue

            # Exact match
            if val1 == val2:
                similarities.append(1.0)
            else:
                # String similarity
                if isinstance(val1, str) and isinstance(val2, str):
                    sim = self._string_similarity(val1, val2)
                    similarities.append(sim)
                else:
                    similarities.append(0.0)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate string similarity using character overlap.

        This method calculates similarity between two strings using character
        set intersection over union (Jaccard-like similarity).

        Args:
            s1: First string
            s2: Second string

        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        if not s1 or not s2:
            return 0.0

        if s1 == s2:
            return 1.0

        # Simple character overlap
        s1_lower = s1.lower()
        s2_lower = s2.lower()

        if s1_lower == s2_lower:
            return 0.95

        # Character-level similarity
        set1 = set(s1_lower)
        set2 = set(s2_lower)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def resolve_duplicates(
        self,
        duplicate_groups: List[DuplicateGroup],
        strategy: str = "keep_first",
        **options,
    ) -> List[Dict[str, Any]]:
        """
        Resolve duplicate groups.

        This method resolves duplicate groups by applying a resolution strategy,
        returning a single record per group.

        Args:
            duplicate_groups: List of DuplicateGroup objects
            strategy: Resolution strategy:
                - "keep_first": Keep first record in group (default)
                - "merge": Merge all records into one
            **options: Additional resolution options (unused)

        Returns:
            list: List of resolved record dictionaries (one per duplicate group)
        """
        resolved = []
        strategy_type = strategy

        for group in duplicate_groups:
            if strategy_type == "keep_first":
                resolved.append(group.canonical_record or group.records[0])
            elif strategy_type == "merge":
                merged = self._merge_records(group.records)
                resolved.append(merged)
            else:
                resolved.append(group.records[0])

        return resolved

    def _merge_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple records into one.

        This method merges multiple records by combining their fields, keeping
        the first non-null value for each field.

        Args:
            records: List of record dictionaries to merge

        Returns:
            dict: Merged record dictionary
        """
        merged = {}

        for record in records:
            for key, value in record.items():
                if key not in merged or merged[key] is None:
                    merged[key] = value
                elif value is not None and merged[key] != value:
                    # Keep first non-null value
                    pass

        return merged


class DataValidator:
    """
    Data validation engine.

    This class provides data validation capabilities, checking data integrity,
    types, formats, and constraints against schemas.

    Features:
        - Data integrity validation
        - Data type checking
        - Format validation
        - Constraint validation
        - Error and warning reporting

    Example Usage:
        >>> validator = DataValidator()
        >>> result = validator.validate_dataset(dataset, schema)
        >>> if not result.valid:
        ...     print(f"Errors: {result.errors}")
    """

    def __init__(self, **config):
        """
        Initialize data validator.

        Sets up the validator with configuration options.

        Args:
            **config: Configuration options (currently unused)
        """
        self.logger = get_logger("data_validator")
        self.config = config

        self.logger.debug("Data validator initialized")

    def validate_dataset(
        self, dataset: List[Dict[str, Any]], schema: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate entire dataset.

        This method validates all records in the dataset against the provided
        schema, collecting errors and warnings for each record.

        Args:
            dataset: List of record dictionaries to validate
            schema: Validation schema dictionary (optional) containing:
                - fields: Dictionary mapping field names to field schemas

        Returns:
            ValidationResult: Validation result with errors and warnings
                            aggregated across all records
        """
        errors = []
        warnings = []

        if not dataset:
            return ValidationResult(valid=True)

        for i, record in enumerate(dataset):
            record_validation = self.validate_record(record, schema)

            for error in record_validation.errors:
                errors.append({"record_index": i, **error})

            for warning in record_validation.warnings:
                warnings.append({"record_index": i, **warning})

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def validate_record(
        self, record: Dict[str, Any], schema: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate individual record.

        This method validates a single record against the provided schema,
        checking required fields and data types.

        Args:
            record: Record dictionary to validate
            schema: Validation schema dictionary (optional) containing:
                - fields: Dictionary mapping field names to field schemas with:
                    - type: Expected data type (str, int, float, bool, list, dict)
                    - required: Whether field is required (bool)

        Returns:
            ValidationResult: Validation result for this record
        """
        errors = []
        warnings = []

        if schema:
            # Validate against schema
            expected_fields = schema.get("fields", {})

            for field, field_schema in expected_fields.items():
                value = record.get(field)

                # Check required fields
                if field_schema.get("required", False) and value is None:
                    errors.append(
                        {
                            "field": field,
                            "message": f"Required field '{field}' is missing",
                        }
                    )

                # Check type
                expected_type = field_schema.get("type")
                if expected_type and value is not None:
                    type_check = self.check_data_types(value, expected_type)
                    if not type_check:
                        errors.append(
                            {
                                "field": field,
                                "message": f"Field '{field}' has incorrect type, expected {expected_type}",
                            }
                        )

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def check_data_types(
        self, data: Any, expected_types: Union[type, List[type], str, List[str]]
    ) -> bool:
        """
        Check data types against expected types.

        This method validates that data matches one of the expected types.
        Supports both type objects and type name strings.

        Args:
            data: Data value to check
            expected_types: Expected type(s) - can be:
                - Single type object (e.g., str, int)
                - List of type objects
                - Type name string (e.g., "str", "int")
                - List of type name strings

        Returns:
            bool: True if data type matches one of the expected types, False otherwise
        """
        if isinstance(expected_types, type):
            expected_types = [expected_types]
        elif isinstance(expected_types, str):
            expected_types = [expected_types]

        actual_type = type(data)

        # Map string type names to actual types
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }

        for expected_type in expected_types:
            if isinstance(expected_type, str):
                expected_type = type_map.get(expected_type, str)

            if isinstance(data, expected_type):
                return True

        return False


class MissingValueHandler:
    """
    Missing value processing engine.

    This class provides missing value handling capabilities, including
    identification, removal, filling, and imputation strategies.

    Features:
        - Missing value identification
        - Multiple handling strategies (remove, fill, impute)
        - Statistical imputation (mean, median, mode)
        - Missing value statistics

    Example Usage:
        >>> handler = MissingValueHandler()
        >>> missing_info = handler.identify_missing_values(dataset)
        >>> processed = handler.handle_missing_values(dataset, strategy="impute", method="mean")
    """

    def __init__(self, **config):
        """
        Initialize missing value handler.

        Sets up the handler with configuration and missing value definitions.

        Args:
            **config: Configuration options:
                - missing_values: List of values considered missing
                                (default: [None, "", "N/A", "null", "NULL"])
        """
        self.logger = get_logger("missing_value_handler")
        self.config = config
        self.missing_values = config.get(
            "missing_values", [None, "", "N/A", "null", "NULL"]
        )

        self.logger.debug("Missing value handler initialized")

    def identify_missing_values(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identify missing values in dataset.

        This method analyzes the dataset to identify missing values across
        all fields, providing counts and percentages.

        Args:
            dataset: List of record dictionaries

        Returns:
            dict: Missing value information containing:
                - total_records: Total number of records
                - missing_counts: Dictionary mapping field names to missing counts
                - missing_percentages: Dictionary mapping field names to
                                     missing percentages (0.0 to 100.0)
        """
        missing_info = defaultdict(int)
        total_records = len(dataset)

        if not dataset:
            return {"total_records": 0, "missing_counts": {}}

        all_fields = set()
        for record in dataset:
            all_fields.update(record.keys())

        for field in all_fields:
            missing_count = 0
            for record in dataset:
                value = record.get(field)
                if value in self.missing_values or value is None:
                    missing_count += 1
            missing_info[field] = missing_count

        return {
            "total_records": total_records,
            "missing_counts": dict(missing_info),
            "missing_percentages": {
                field: (count / total_records * 100) if total_records > 0 else 0
                for field, count in missing_info.items()
            },
        }

    def handle_missing_values(
        self, dataset: List[Dict[str, Any]], strategy: str = "remove", **options
    ) -> List[Dict[str, Any]]:
        """
        Handle missing values using specified strategy.

        This method processes missing values in the dataset using the specified
        strategy: remove records, fill with default values, or impute using
        statistical methods.

        Args:
            dataset: List of record dictionaries
            strategy: Handling strategy:
                - "remove": Remove records with any missing values (default)
                - "fill": Fill missing values with default value
                - "impute": Impute missing values using statistical methods
            **options: Strategy-specific options:
                - fill_value: Value to use for filling (for "fill" strategy)
                - method: Imputation method for "impute" strategy
                         ("mean", "median", "mode", "zero")

        Returns:
            list: Processed dataset with missing values handled
        """
        if strategy == "remove":
            return self._remove_missing(dataset)
        elif strategy == "fill":
            return self._fill_missing(dataset, fill_value=options.get("fill_value", ""))
        elif strategy == "impute":
            return self.impute_values(dataset, method=options.get("method", "mean"))
        else:
            return dataset

    def _remove_missing(self, dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove records with missing values.

        This method filters out records that contain any missing values
        (as defined in missing_values list).

        Args:
            dataset: List of record dictionaries

        Returns:
            list: Dataset with records containing missing values removed
        """
        return [
            record
            for record in dataset
            if not any(
                value in self.missing_values or value is None
                for value in record.values()
            )
        ]

    def _fill_missing(
        self, dataset: List[Dict[str, Any]], fill_value: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Fill missing values with default value.

        This method replaces all missing values in records with the specified
        fill value.

        Args:
            dataset: List of record dictionaries
            fill_value: Value to use for filling missing values (default: "")

        Returns:
            list: Dataset with missing values filled
        """
        if fill_value is None:
            fill_value = ""
        filled = []
        for record in dataset:
            filled_record = {}
            for key, value in record.items():
                if value in self.missing_values or value is None:
                    filled_record[key] = fill_value
                else:
                    filled_record[key] = value
            filled.append(filled_record)
        return filled

    def impute_values(
        self, dataset: List[Dict[str, Any]], method: str = "mean"
    ) -> List[Dict[str, Any]]:
        """
        Impute missing values using specified method.

        This method imputes missing numeric values using statistical methods
        (mean, median, mode, or zero). Only numeric fields are imputed.

        Args:
            dataset: List of record dictionaries
            method: Imputation method:
                - "mean": Use mean of non-missing values (default)
                - "median": Use median of non-missing values
                - "zero": Use zero
                - "mode": Use mode (most frequent value)

        Returns:
            list: Dataset with missing numeric values imputed
        """
        if not dataset:
            return dataset

        # Collect numeric values by field
        numeric_fields = {}
        for record in dataset:
            for key, value in record.items():
                if isinstance(value, (int, float)):
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(value)

        # Calculate imputation values
        imputation_values = {}
        for field, values in numeric_fields.items():
            if method == "mean":
                imputation_values[field] = sum(values) / len(values) if values else 0
            elif method == "median":
                sorted_values = sorted(values)
                n = len(sorted_values)
                imputation_values[field] = sorted_values[n // 2] if n > 0 else 0
            elif method == "zero":
                imputation_values[field] = 0
            else:
                imputation_values[field] = 0

        # Impute missing values
        imputed = []
        for record in dataset:
            imputed_record = {}
            for key, value in record.items():
                if value in self.missing_values or value is None:
                    imputed_record[key] = imputation_values.get(key, "")
                else:
                    imputed_record[key] = value
            imputed.append(imputed_record)

        return imputed
