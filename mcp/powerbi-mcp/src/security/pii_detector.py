"""
PII Detection and Auto-Masking Module
Detects and masks personally identifiable information in query results
"""
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MaskingStrategy(Enum):
    """How to mask detected PII"""
    FULL = "full"           # Replace entirely: "John" -> "****"
    PARTIAL = "partial"     # Partial mask: "john@email.com" -> "j***@e****.com"
    HASH = "hash"           # SHA256 hash: "John" -> "a8cfcd74..."
    REDACT = "redact"       # Replace with label: "John" -> "[REDACTED]"
    NONE = "none"           # No masking (for testing/debugging)


class PIIType(Enum):
    """Types of PII that can be detected"""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    BANK_ACCOUNT = "bank_account"
    NAME = "name"  # Requires column name heuristics


# PII Detection Patterns
PII_PATTERNS = {
    PIIType.SSN: [
        r'\b\d{3}-\d{2}-\d{4}\b',           # 123-45-6789
        r'\b\d{3}\s\d{2}\s\d{4}\b',         # 123 45 6789
        r'\b\d{9}\b',                        # 123456789 (context needed)
    ],
    PIIType.CREDIT_CARD: [
        r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Visa
        r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Mastercard
        r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b',  # Amex
        r'\b6(?:011|5\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Discover
    ],
    PIIType.EMAIL: [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ],
    PIIType.PHONE: [
        r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
        r'\b\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1-123-456-7890
        r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',  # 123-456-7890
    ],
    PIIType.IP_ADDRESS: [
        r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
    ],
    PIIType.DATE_OF_BIRTH: [
        r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',  # MM/DD/YYYY
        r'\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])\b',  # YYYY-MM-DD
    ],
}

# Column names that likely contain PII (case-insensitive matching)
PII_COLUMN_INDICATORS = {
    PIIType.SSN: ['ssn', 'social_security', 'socialsecurity', 'social security', 'sin'],
    PIIType.CREDIT_CARD: ['credit_card', 'creditcard', 'card_number', 'cardnumber', 'cc_number', 'ccn'],
    PIIType.EMAIL: ['email', 'e_mail', 'email_address', 'emailaddress', 'mail'],
    PIIType.PHONE: ['phone', 'telephone', 'mobile', 'cell', 'phone_number', 'phonenumber', 'tel'],
    PIIType.NAME: ['name', 'first_name', 'last_name', 'firstname', 'lastname', 'full_name', 'fullname',
                   'customer_name', 'employee_name', 'contact_name', 'person'],
    PIIType.DATE_OF_BIRTH: ['dob', 'birth_date', 'birthdate', 'date_of_birth', 'birthday'],
    PIIType.IP_ADDRESS: ['ip', 'ip_address', 'ipaddress', 'client_ip', 'user_ip'],
    PIIType.BANK_ACCOUNT: ['bank_account', 'account_number', 'accountnumber', 'iban', 'routing'],
    PIIType.PASSPORT: ['passport', 'passport_number', 'passportnumber'],
    PIIType.DRIVERS_LICENSE: ['license', 'drivers_license', 'driverslicense', 'dl_number'],
}


class PIIDetector:
    """
    Detects and masks PII in query results

    Usage:
        detector = PIIDetector(default_strategy=MaskingStrategy.PARTIAL)
        masked_results = detector.process_results(query_results)
    """

    def __init__(
        self,
        default_strategy: MaskingStrategy = MaskingStrategy.PARTIAL,
        enabled_types: Optional[List[PIIType]] = None,
        column_overrides: Optional[Dict[str, MaskingStrategy]] = None
    ):
        """
        Initialize PII detector

        Args:
            default_strategy: Default masking strategy for detected PII
            enabled_types: List of PII types to detect (None = all)
            column_overrides: Per-column masking strategy overrides
        """
        self.default_strategy = default_strategy
        self.enabled_types = enabled_types or list(PIIType)
        self.column_overrides = column_overrides or {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self._compiled_patterns = {}
        for pii_type, patterns in PII_PATTERNS.items():
            if pii_type in self.enabled_types:
                self._compiled_patterns[pii_type] = [
                    re.compile(p, re.IGNORECASE) for p in patterns
                ]

    def detect_pii_type_from_column(self, column_name: str) -> Optional[PIIType]:
        """
        Detect likely PII type based on column name

        Args:
            column_name: Name of the column

        Returns:
            Detected PII type or None
        """
        col_lower = column_name.lower().strip('[]')

        for pii_type, indicators in PII_COLUMN_INDICATORS.items():
            for indicator in indicators:
                if indicator in col_lower or col_lower in indicator:
                    return pii_type
        return None

    def detect_pii_in_value(self, value: str) -> List[Tuple[PIIType, str, int, int]]:
        """
        Detect PII patterns in a string value

        Args:
            value: String to scan for PII

        Returns:
            List of (pii_type, matched_text, start, end) tuples
        """
        if not isinstance(value, str):
            return []

        detections = []

        for pii_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(value):
                    detections.append((
                        pii_type,
                        match.group(),
                        match.start(),
                        match.end()
                    ))

        return detections

    def mask_value(
        self,
        value: str,
        pii_type: PIIType,
        strategy: Optional[MaskingStrategy] = None
    ) -> str:
        """
        Mask a PII value using the specified strategy

        Args:
            value: The PII value to mask
            pii_type: Type of PII detected
            strategy: Masking strategy (uses default if None)

        Returns:
            Masked value
        """
        strategy = strategy or self.default_strategy

        if strategy == MaskingStrategy.NONE:
            return value

        if strategy == MaskingStrategy.REDACT:
            return f"[REDACTED-{pii_type.value.upper()}]"

        if strategy == MaskingStrategy.HASH:
            hash_val = hashlib.sha256(value.encode()).hexdigest()[:12]
            return f"[HASH:{hash_val}]"

        if strategy == MaskingStrategy.FULL:
            return '*' * min(len(value), 10)

        if strategy == MaskingStrategy.PARTIAL:
            return self._partial_mask(value, pii_type)

        return value

    def _partial_mask(self, value: str, pii_type: PIIType) -> str:
        """Apply partial masking based on PII type"""

        if pii_type == PIIType.EMAIL:
            # j***@e****.com
            if '@' in value:
                local, domain = value.rsplit('@', 1)
                parts = domain.rsplit('.', 1)
                if len(parts) == 2:
                    domain_name, tld = parts
                    return f"{local[0]}***@{domain_name[0]}****.{tld}"
            return f"{value[0]}***@***.***"

        elif pii_type == PIIType.PHONE:
            # (***) ***-1234
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"(***) ***-{digits[-4:]}"
            return "***-***-****"

        elif pii_type == PIIType.SSN:
            # ***-**-6789
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"***-**-{digits[-4:]}"
            return "***-**-****"

        elif pii_type == PIIType.CREDIT_CARD:
            # ****-****-****-1234
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"****-****-****-{digits[-4:]}"
            return "****-****-****-****"

        elif pii_type == PIIType.NAME:
            # J*** S****
            words = value.split()
            masked_words = []
            for word in words:
                if len(word) > 1:
                    masked_words.append(f"{word[0]}{'*' * (len(word) - 1)}")
                else:
                    masked_words.append('*')
            return ' '.join(masked_words)

        elif pii_type == PIIType.IP_ADDRESS:
            # 192.168.***.***
            parts = value.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.***.***"
            return "***.***.***.***"

        else:
            # Default: show first and last char
            if len(value) > 2:
                return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"
            return '*' * len(value)

    def process_value(
        self,
        value: Any,
        column_name: Optional[str] = None
    ) -> Tuple[Any, List[Dict]]:
        """
        Process a single value, detecting and masking PII

        Args:
            value: Value to process
            column_name: Optional column name for context

        Returns:
            Tuple of (processed_value, list of detections)
        """
        if value is None or not isinstance(value, str):
            return value, []

        detections = []
        processed_value = value

        # Check column name for PII indicators
        column_pii_type = None
        if column_name:
            column_pii_type = self.detect_pii_type_from_column(column_name)

            # Get strategy for this column
            strategy = self.column_overrides.get(
                column_name.lower().strip('[]'),
                self.default_strategy
            )

            if column_pii_type and column_pii_type in self.enabled_types:
                detections.append({
                    'type': column_pii_type.value,
                    'source': 'column_name',
                    'original': value,
                    'column': column_name
                })
                processed_value = self.mask_value(value, column_pii_type, strategy)
                return processed_value, detections

        # Scan value for PII patterns
        pii_found = self.detect_pii_in_value(value)

        if pii_found:
            # Sort by position (reverse) to replace from end to start
            pii_found.sort(key=lambda x: x[2], reverse=True)

            for pii_type, matched, start, end in pii_found:
                strategy = self.column_overrides.get(
                    column_name.lower().strip('[]') if column_name else '',
                    self.default_strategy
                )

                masked = self.mask_value(matched, pii_type, strategy)
                processed_value = processed_value[:start] + masked + processed_value[end:]

                detections.append({
                    'type': pii_type.value,
                    'source': 'pattern',
                    'original': matched,
                    'masked': masked,
                    'column': column_name
                })

        return processed_value, detections

    def process_row(self, row: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict]]:
        """
        Process a single row, detecting and masking PII in all columns

        Args:
            row: Dictionary representing a row of data

        Returns:
            Tuple of (processed_row, list of all detections)
        """
        processed_row = {}
        all_detections = []

        for column, value in row.items():
            processed_value, detections = self.process_value(value, column)
            processed_row[column] = processed_value
            all_detections.extend(detections)

        return processed_row, all_detections

    def process_results(
        self,
        results: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process query results, detecting and masking PII

        Args:
            results: List of row dictionaries from query

        Returns:
            Tuple of (processed_results, detection_summary)
        """
        processed_results = []
        all_detections = []

        for row in results:
            processed_row, detections = self.process_row(row)
            processed_results.append(processed_row)
            all_detections.extend(detections)

        # Build summary
        summary = {
            'total_detections': len(all_detections),
            'rows_affected': len(set(d.get('column') for d in all_detections)),
            'types_detected': list(set(d['type'] for d in all_detections)),
            'detections': all_detections if len(all_detections) <= 10 else all_detections[:10]
        }

        if all_detections:
            logger.info(f"PII Detection: Found {len(all_detections)} PII instances across {summary['rows_affected']} columns")

        return processed_results, summary


# Convenience function
def mask_pii(
    results: List[Dict[str, Any]],
    strategy: MaskingStrategy = MaskingStrategy.PARTIAL
) -> List[Dict[str, Any]]:
    """
    Quick function to mask PII in query results

    Args:
        results: Query results to process
        strategy: Masking strategy to use

    Returns:
        Processed results with PII masked
    """
    detector = PIIDetector(default_strategy=strategy)
    processed, _ = detector.process_results(results)
    return processed
