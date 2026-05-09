"""
Tests for the ChangeLogEntry module.

This module tests the standardized metadata structures for version changes.
"""

import pytest
from datetime import datetime

from veritasreason.change_management import ChangeLogEntry
from veritasreason.utils.exceptions import ValidationError


class TestChangeLogEntry:
    """Test cases for ChangeLogEntry dataclass."""
    
    def test_valid_change_log_entry(self):
        """Test creating a valid change log entry."""
        entry = ChangeLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            author="alice@company.com",
            description="Added Customer entity"
        )
        
        assert entry.timestamp == "2024-01-15T10:30:00Z"
        assert entry.author == "alice@company.com"
        assert entry.description == "Added Customer entity"
        assert entry.change_id is None
        assert entry.related_changes == []
    
    def test_change_log_entry_with_optional_fields(self):
        """Test creating a change log entry with optional fields."""
        entry = ChangeLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            author="bob@company.com",
            description="Modified Product entity",
            change_id="CHG-001",
            related_changes=["CHG-000"]
        )
        
        assert entry.change_id == "CHG-001"
        assert entry.related_changes == ["CHG-000"]
    
    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid timestamp format"):
            ChangeLogEntry(
                timestamp="2024-01-15 10:30:00",  # Wrong format
                author="alice@company.com",
                description="Test change"
            )
    
    def test_invalid_email_format(self):
        """Test that invalid email format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            ChangeLogEntry(
                timestamp="2024-01-15T10:30:00Z",
                author="invalid-email",  # Invalid email
                description="Test change"
            )
    
    def test_empty_description(self):
        """Test that empty description raises ValidationError."""
        with pytest.raises(ValidationError, match="Description cannot be empty"):
            ChangeLogEntry(
                timestamp="2024-01-15T10:30:00Z",
                author="alice@company.com",
                description="   "  # Empty/whitespace only
            )
    
    def test_description_too_long(self):
        """Test that description over 500 chars raises ValidationError."""
        long_description = "x" * 501
        with pytest.raises(ValidationError, match="Description too long"):
            ChangeLogEntry(
                timestamp="2024-01-15T10:30:00Z",
                author="alice@company.com",
                description=long_description
            )
    
    def test_description_exactly_500_chars(self):
        """Test that description of exactly 500 chars is valid."""
        description_500 = "x" * 500
        entry = ChangeLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            author="alice@company.com",
            description=description_500
        )
        assert len(entry.description) == 500
    
    def test_create_now_class_method(self):
        """Test the create_now class method."""
        entry = ChangeLogEntry.create_now(
            author="charlie@company.com",
            description="Test change with current timestamp"
        )
        
        # Verify timestamp is recent (within last minute)
        entry_time = datetime.fromisoformat(entry.timestamp)
        now = datetime.now()
        time_diff = abs((now - entry_time).total_seconds())
        assert time_diff < 60  # Within 1 minute
        
        assert entry.author == "charlie@company.com"
        assert entry.description == "Test change with current timestamp"
    
    def test_create_now_with_optional_fields(self):
        """Test create_now with optional fields."""
        entry = ChangeLogEntry.create_now(
            author="dave@company.com",
            description="Test change",
            change_id="CHG-002",
            related_changes=["CHG-001", "CHG-000"]
        )
        
        assert entry.change_id == "CHG-002"
        assert entry.related_changes == ["CHG-001", "CHG-000"]
    
    def test_various_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "user@domain.com",
            "user.name@domain.co.uk",
            "user+tag@domain.org",
            "user123@domain123.net",
            "user_name@sub.domain.com"
        ]
        
        for email in valid_emails:
            entry = ChangeLogEntry(
                timestamp="2024-01-15T10:30:00Z",
                author=email,
                description="Test change"
            )
            assert entry.author == email
    
    def test_various_invalid_email_formats(self):
        """Test various invalid email formats."""
        invalid_emails = [
            "plainaddress",
            "@missingdomain.com",
            "missing@.com",
            "missing@domain",
            "spaces @domain.com",
            "double@@domain.com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError, match="Invalid email format"):
                ChangeLogEntry(
                    timestamp="2024-01-15T10:30:00Z",
                    author=email,
                    description="Test change"
                )
    
    def test_various_valid_timestamp_formats(self):
        """Test various valid ISO 8601 timestamp formats."""
        valid_timestamps = [
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00+00:00",
            "2024-01-15T10:30:00.123Z",
            "2024-01-15T10:30:00.123456Z",
            "2024-01-15T10:30:00+05:30",
            "2024-01-15T10:30:00-08:00"
        ]
        
        for timestamp in valid_timestamps:
            entry = ChangeLogEntry(
                timestamp=timestamp,
                author="test@company.com",
                description="Test change"
            )
            assert entry.timestamp == timestamp
