"""
Integrity Verification Utilities

This module provides utilities for data integrity verification using
SHA-256 checksums, ensuring provenance data has not been tampered with.

Features:
    - SHA-256 checksum computation
    - Checksum verification
    - Data integrity validation
    - Tamper detection

Compliance:
    - FDA 21 CFR Part 11 (electronic records)
    - SOX (Sarbanes-Oxley)
    - HIPAA (healthcare data integrity)

Author: VeritasReason Contributors
License: MIT
"""

import hashlib
from typing import Any, Dict, Optional
from .schemas import ProvenanceEntry


def compute_checksum(entry: ProvenanceEntry) -> str:
    """
    Compute SHA-256 checksum for a provenance entry.
    
    Creates a deterministic checksum based on critical provenance fields
    to detect any tampering or corruption of provenance data.
    
    Args:
        entry: ProvenanceEntry to compute checksum for
        
    Returns:
        SHA-256 checksum as hexadecimal string
        
    Example:
        >>> entry = ProvenanceEntry(
        ...     entity_id="entity_123",
        ...     entity_type="entity",
        ...     activity_id="extraction",
        ...     source_document="DOI:10.1371/..."
        ... )
        >>> checksum = compute_checksum(entry)
        >>> print(checksum)
        'a3b2c1d4e5f6...'
    """
    # Concatenate critical fields for checksum
    data = (
        f"{entry.entity_id}"
        f"{entry.entity_type}"
        f"{entry.activity_id}"
        f"{entry.source_document}"
        f"{entry.timestamp}"
        f"{entry.confidence}"
    )
    
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def verify_checksum(entry: ProvenanceEntry, expected_checksum: Optional[str] = None) -> bool:
    """
    Verify checksum for a provenance entry.
    
    Computes the current checksum and compares it with the expected checksum
    to detect tampering or corruption.
    
    Args:
        entry: ProvenanceEntry to verify
        expected_checksum: Expected checksum (uses entry.checksum if None)
        
    Returns:
        True if checksum matches, False otherwise
        
    Example:
        >>> entry = ProvenanceEntry(...)
        >>> entry.checksum = compute_checksum(entry)
        >>> is_valid = verify_checksum(entry)
        >>> print(is_valid)
        True
    """
    if expected_checksum is None:
        expected_checksum = entry.checksum
    
    if expected_checksum is None:
        return False
    
    current_checksum = compute_checksum(entry)
    return current_checksum == expected_checksum


def compute_data_checksum(data: str) -> str:
    """
    Compute SHA-256 checksum for arbitrary data.
    
    Args:
        data: String data to compute checksum for
        
    Returns:
        SHA-256 checksum as hexadecimal string
        
    Example:
        >>> checksum = compute_data_checksum("some data")
        >>> print(checksum)
        'a3b2c1d4e5f6...'
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def verify_data_checksum(data: str, expected_checksum: str) -> bool:
    """
    Verify checksum for arbitrary data.
    
    Args:
        data: String data to verify
        expected_checksum: Expected checksum
        
    Returns:
        True if checksum matches, False otherwise
        
    Example:
        >>> data = "some data"
        >>> checksum = compute_data_checksum(data)
        >>> is_valid = verify_data_checksum(data, checksum)
        >>> print(is_valid)
        True
    """
    current_checksum = compute_data_checksum(data)
    return current_checksum == expected_checksum


def compute_dict_checksum(data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 checksum for dictionary data.
    
    Sorts keys to ensure deterministic checksum computation.
    
    Args:
        data: Dictionary data to compute checksum for
        
    Returns:
        SHA-256 checksum as hexadecimal string
        
    Example:
        >>> data = {"key1": "value1", "key2": "value2"}
        >>> checksum = compute_dict_checksum(data)
        >>> print(checksum)
        'a3b2c1d4e5f6...'
    """
    # Sort keys for deterministic checksum
    sorted_items = sorted(data.items())
    data_str = str(sorted_items)
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()


def verify_dict_checksum(data: Dict[str, Any], expected_checksum: str) -> bool:
    """
    Verify checksum for dictionary data.
    
    Args:
        data: Dictionary data to verify
        expected_checksum: Expected checksum
        
    Returns:
        True if checksum matches, False otherwise
        
    Example:
        >>> data = {"key1": "value1", "key2": "value2"}
        >>> checksum = compute_dict_checksum(data)
        >>> is_valid = verify_dict_checksum(data, checksum)
        >>> print(is_valid)
        True
    """
    current_checksum = compute_dict_checksum(data)
    return current_checksum == expected_checksum
