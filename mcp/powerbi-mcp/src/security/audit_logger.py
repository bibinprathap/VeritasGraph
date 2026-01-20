"""
Query Audit Logging Module
Logs all queries with metadata for compliance and security monitoring
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of auditable events"""
    QUERY_EXECUTE = "query_execute"
    QUERY_SUCCESS = "query_success"
    QUERY_FAILURE = "query_failure"
    CONNECTION = "connection"
    DISCONNECTION = "disconnection"
    POLICY_VIOLATION = "policy_violation"
    PII_DETECTED = "pii_detected"
    ACCESS_DENIED = "access_denied"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """
    Comprehensive audit logging for Power BI MCP queries

    Features:
    - JSON-formatted logs for easy parsing
    - Rotation support
    - Thread-safe logging
    - Query fingerprinting for deduplication
    - Sensitive data redaction in logs

    Usage:
        audit = AuditLogger(log_dir="./logs")
        audit.log_query(
            query="EVALUATE Sales",
            result_count=100,
            duration_ms=250,
            pii_detected=True
        )
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        log_file: str = "audit.log",
        max_file_size_mb: int = 10,
        backup_count: int = 5,
        include_query_text: bool = True,
        redact_sensitive: bool = True
    ):
        """
        Initialize the audit logger

        Args:
            log_dir: Directory for log files (default: ./logs)
            log_file: Name of the log file
            max_file_size_mb: Max size before rotation
            backup_count: Number of backup files to keep
            include_query_text: Whether to include full query text
            redact_sensitive: Redact potentially sensitive values in logs
        """
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent.parent / "logs"
        self.log_file = self.log_dir / log_file
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self.include_query_text = include_query_text
        self.redact_sensitive = redact_sensitive

        self._lock = threading.Lock()
        self._session_id = self._generate_session_id()
        self._query_count = 0

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Audit logger initialized: {self.log_file}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        timestamp = datetime.now(timezone.utc).isoformat()
        return hashlib.sha256(f"{timestamp}{os.getpid()}".encode()).hexdigest()[:16]

    def _generate_query_fingerprint(self, query: str) -> str:
        """Generate a fingerprint for query deduplication"""
        # Normalize whitespace and case
        normalized = ' '.join(query.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    def _rotate_if_needed(self):
        """Rotate log file if it exceeds max size"""
        if self.log_file.exists() and self.log_file.stat().st_size > self.max_file_size:
            # Rotate existing backups
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = self.log_dir / f"{self.log_file.stem}.{i}{self.log_file.suffix}"
                new_backup = self.log_dir / f"{self.log_file.stem}.{i + 1}{self.log_file.suffix}"
                if old_backup.exists():
                    old_backup.rename(new_backup)

            # Rotate current log
            backup_1 = self.log_dir / f"{self.log_file.stem}.1{self.log_file.suffix}"
            self.log_file.rename(backup_1)

            logger.info(f"Rotated audit log: {self.log_file}")

    def _redact_value(self, value: Any) -> Any:
        """Redact potentially sensitive values"""
        if not self.redact_sensitive:
            return value

        if isinstance(value, str):
            # Redact long strings that might contain data
            if len(value) > 100:
                return f"{value[:50]}... [TRUNCATED {len(value)} chars]"

        return value

    def _write_log(self, event: Dict[str, Any]):
        """Thread-safe log writing"""
        with self._lock:
            self._rotate_if_needed()

            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(event, default=str) + '\n')
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Log a generic audit event

        Args:
            event_type: Type of event
            severity: Severity level
            message: Human-readable message
            details: Additional details
            **kwargs: Extra fields to include

        Returns:
            The logged event record
        """
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'session_id': self._session_id,
            'event_type': event_type.value,
            'severity': severity.value,
            'message': message,
            'details': details or {},
            **kwargs
        }

        self._write_log(event)
        return event

    def log_query(
        self,
        query: str,
        source: str = "desktop",
        model_name: Optional[str] = None,
        port: Optional[int] = None,
        result_count: Optional[int] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        tables_accessed: Optional[List[str]] = None,
        columns_accessed: Optional[List[str]] = None,
        pii_detected: bool = False,
        pii_types: Optional[List[str]] = None,
        pii_count: int = 0,
        policy_applied: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log a DAX query execution

        Args:
            query: The DAX query text
            source: "desktop" or "cloud"
            model_name: Name of the Power BI model
            port: Port number (for desktop)
            result_count: Number of rows returned
            duration_ms: Query execution time in milliseconds
            success: Whether query succeeded
            error_message: Error message if failed
            tables_accessed: List of tables accessed
            columns_accessed: List of columns accessed
            pii_detected: Whether PII was detected
            pii_types: Types of PII detected
            pii_count: Number of PII instances detected
            policy_applied: Name of access policy applied
            user_context: Additional user context

        Returns:
            The logged event record
        """
        self._query_count += 1

        event_type = AuditEventType.QUERY_SUCCESS if success else AuditEventType.QUERY_FAILURE
        severity = AuditSeverity.INFO if success else AuditSeverity.ERROR

        # Elevate severity if PII was detected
        if pii_detected:
            severity = AuditSeverity.WARNING

        query_text = query if self.include_query_text else "[REDACTED]"
        query_fingerprint = self._generate_query_fingerprint(query)

        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'session_id': self._session_id,
            'query_id': f"{self._session_id}_{self._query_count}",
            'query_number': self._query_count,
            'event_type': event_type.value,
            'severity': severity.value,
            'source': source,
            'model': model_name,
            'port': port,
            'query': {
                'text': query_text,
                'fingerprint': query_fingerprint,
                'length': len(query)
            },
            'result': {
                'success': success,
                'row_count': result_count,
                'duration_ms': duration_ms,
                'error': error_message
            },
            'access': {
                'tables': tables_accessed or [],
                'columns': columns_accessed or [],
                'policy': policy_applied
            },
            'pii': {
                'detected': pii_detected,
                'types': pii_types or [],
                'count': pii_count
            },
            'context': user_context or {}
        }

        self._write_log(event)

        # Log summary to standard logger
        status = "SUCCESS" if success else f"FAILED: {error_message}"
        pii_info = f", PII: {pii_count} instances" if pii_detected else ""
        logger.info(f"Query [{query_fingerprint}]: {result_count or 0} rows, {duration_ms or 0:.0f}ms, {status}{pii_info}")

        return event

    def log_connection(
        self,
        source: str,
        model_name: Optional[str] = None,
        port: Optional[int] = None,
        workspace: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a connection event"""
        event_type = AuditEventType.CONNECTION
        severity = AuditSeverity.INFO if success else AuditSeverity.ERROR

        message = f"Connected to {source}"
        if model_name:
            message += f": {model_name}"
        if not success:
            message = f"Connection failed to {source}: {error_message}"

        return self.log_event(
            event_type=event_type,
            severity=severity,
            message=message,
            details={
                'source': source,
                'model': model_name,
                'port': port,
                'workspace': workspace,
                'success': success,
                'error': error_message
            }
        )

    def log_policy_violation(
        self,
        policy_name: str,
        violation_type: str,
        table: Optional[str] = None,
        column: Optional[str] = None,
        action_taken: str = "blocked",
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a policy violation"""
        query_fingerprint = self._generate_query_fingerprint(query) if query else None

        return self.log_event(
            event_type=AuditEventType.POLICY_VIOLATION,
            severity=AuditSeverity.WARNING,
            message=f"Policy violation: {policy_name} - {violation_type}",
            details={
                'policy': policy_name,
                'violation': violation_type,
                'table': table,
                'column': column,
                'action': action_taken,
                'query_fingerprint': query_fingerprint
            }
        )

    def log_pii_detection(
        self,
        pii_types: List[str],
        count: int,
        columns_affected: List[str],
        action_taken: str = "masked"
    ) -> Dict[str, Any]:
        """Log PII detection event"""
        return self.log_event(
            event_type=AuditEventType.PII_DETECTED,
            severity=AuditSeverity.WARNING,
            message=f"PII detected: {count} instances of {', '.join(pii_types)}",
            details={
                'types': pii_types,
                'count': count,
                'columns': columns_affected,
                'action': action_taken
            }
        )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session"""
        return {
            'session_id': self._session_id,
            'query_count': self._query_count,
            'log_file': str(self.log_file)
        }

    def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """Read recent events from the log file"""
        events = []

        if not self.log_file.exists():
            return events

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-count:]:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")

        return events


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(**kwargs) -> AuditLogger:
    """Configure and return the global audit logger"""
    global _audit_logger
    _audit_logger = AuditLogger(**kwargs)
    return _audit_logger
