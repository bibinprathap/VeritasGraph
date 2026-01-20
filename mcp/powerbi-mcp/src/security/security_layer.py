"""
Unified Security Layer
Integrates PII detection, audit logging, and access policies
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .pii_detector import PIIDetector, MaskingStrategy
from .audit_logger import AuditLogger, get_audit_logger
from .access_policy import AccessPolicyEngine, PolicyAction, PolicyCheckResult

logger = logging.getLogger(__name__)


class SecurityLayer:
    """
    Unified security layer for Power BI MCP Server

    Provides:
    - Pre-query policy checks
    - Post-query PII detection and masking
    - Comprehensive audit logging

    Usage:
        security = SecurityLayer(config_path="config/policies.yaml")

        # Before executing query
        check = security.pre_query_check(query, tables=['Sales'])
        if not check.allowed:
            return error(check.reason)

        # After getting results
        safe_results, report = security.process_results(
            results,
            query=query,
            table='Sales'
        )
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_pii_detection: bool = True,
        enable_audit: bool = True,
        enable_policies: bool = True
    ):
        """
        Initialize the security layer

        Args:
            config_path: Path to policies.yaml
            enable_pii_detection: Enable PII detection
            enable_audit: Enable audit logging
            enable_policies: Enable policy enforcement
        """
        self.enable_pii_detection = enable_pii_detection
        self.enable_audit = enable_audit
        self.enable_policies = enable_policies

        # Initialize components
        self.pii_detector = PIIDetector(
            default_strategy=MaskingStrategy.PARTIAL
        ) if enable_pii_detection else None

        self.audit_logger = get_audit_logger() if enable_audit else None

        self.policy_engine = AccessPolicyEngine(
            config_path=config_path
        ) if enable_policies else None

        # Load config if provided
        if config_path:
            self._load_config(config_path)

        logger.info(f"Security layer initialized (PII: {enable_pii_detection}, Audit: {enable_audit}, Policies: {enable_policies})")

    def _load_config(self, config_path: str):
        """Load configuration from YAML file"""
        import yaml

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Security config not found: {config_path}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Configure PII detector
            if self.pii_detector and 'pii' in config:
                pii_config = config['pii']
                strategies = pii_config.get('strategies', {})
                # Map string strategies to MaskingStrategy enum
                strategy_map = {
                    'partial': MaskingStrategy.PARTIAL,
                    'full': MaskingStrategy.FULL,
                    'hash': MaskingStrategy.HASH,
                    'redact': MaskingStrategy.REDACT,
                }
                default_strategy = strategy_map.get(
                    pii_config.get('default_strategy', 'partial'),
                    MaskingStrategy.PARTIAL
                )
                self.pii_detector.default_strategy = default_strategy

            # Configure audit logger
            if self.audit_logger and 'audit' in config:
                audit_config = config['audit']
                # Audit logger was already initialized, but we can update settings
                self.audit_logger.include_query_text = audit_config.get('include_query_text', True)
                self.audit_logger.redact_sensitive = audit_config.get('redact_sensitive', True)

            logger.info(f"Loaded security config from: {config_path}")

        except Exception as e:
            logger.error(f"Failed to load security config: {e}")

    def pre_query_check(
        self,
        query: str,
        tables: Optional[List[str]] = None,
        columns: Optional[List[str]] = None
    ) -> PolicyCheckResult:
        """
        Check if a query is allowed before execution

        Args:
            query: The DAX query
            tables: Tables being accessed
            columns: Columns being accessed

        Returns:
            PolicyCheckResult with decision
        """
        if not self.enable_policies or not self.policy_engine:
            return PolicyCheckResult(allowed=True, action=PolicyAction.ALLOW)

        return self.policy_engine.check_query(query, tables, columns)

    def process_results(
        self,
        results: List[Dict[str, Any]],
        query: str = "",
        source: str = "desktop",
        model_name: Optional[str] = None,
        port: Optional[int] = None,
        table_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process query results through security layer

        Args:
            results: Raw query results
            query: The executed query
            source: "desktop" or "cloud"
            model_name: Name of the model
            port: Port (for desktop)
            table_name: Primary table queried
            duration_ms: Query duration
            success: Whether query succeeded
            error_message: Error if failed

        Returns:
            Tuple of (processed_results, security_report)
        """
        start_time = time.time()
        processed_results = results
        security_report = {
            'pii_detected': False,
            'pii_count': 0,
            'pii_types': [],
            'policy_applied': False,
            'columns_masked': [],
            'columns_blocked': []
        }

        # Apply access policies
        if self.enable_policies and self.policy_engine and results:
            processed_results, policy_report = self.policy_engine.apply_to_results(
                processed_results,
                table_name=table_name
            )
            security_report['policy_applied'] = policy_report.get('applied', False)
            security_report['columns_blocked'] = policy_report.get('blocked_columns', [])

        # Apply PII detection and masking
        if self.enable_pii_detection and self.pii_detector and processed_results:
            processed_results, pii_summary = self.pii_detector.process_results(processed_results)
            security_report['pii_detected'] = pii_summary['total_detections'] > 0
            security_report['pii_count'] = pii_summary['total_detections']
            security_report['pii_types'] = pii_summary['types_detected']
            security_report['columns_masked'].extend(
                [d.get('column', '') for d in pii_summary.get('detections', [])]
            )

        processing_time = (time.time() - start_time) * 1000

        # Log to audit
        if self.enable_audit and self.audit_logger:
            self.audit_logger.log_query(
                query=query,
                source=source,
                model_name=model_name,
                port=port,
                result_count=len(results) if results else 0,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                pii_detected=security_report['pii_detected'],
                pii_types=security_report['pii_types'],
                pii_count=security_report['pii_count'],
                policy_applied=table_name if security_report['policy_applied'] else None
            )

            # Log PII detection event separately if detected
            if security_report['pii_detected']:
                self.audit_logger.log_pii_detection(
                    pii_types=security_report['pii_types'],
                    count=security_report['pii_count'],
                    columns_affected=list(set(security_report['columns_masked'])),
                    action_taken='masked'
                )

        security_report['processing_time_ms'] = processing_time

        return processed_results, security_report

    def log_connection(
        self,
        source: str,
        model_name: Optional[str] = None,
        port: Optional[int] = None,
        workspace: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log a connection event"""
        if self.enable_audit and self.audit_logger:
            self.audit_logger.log_connection(
                source=source,
                model_name=model_name,
                port=port,
                workspace=workspace,
                success=success,
                error_message=error_message
            )

    def log_policy_violation(
        self,
        policy_name: str,
        violation_type: str,
        table: Optional[str] = None,
        column: Optional[str] = None,
        query: Optional[str] = None
    ):
        """Log a policy violation"""
        if self.enable_audit and self.audit_logger:
            self.audit_logger.log_policy_violation(
                policy_name=policy_name,
                violation_type=violation_type,
                table=table,
                column=column,
                action_taken='blocked',
                query=query
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current security layer status"""
        status = {
            'enabled': {
                'pii_detection': self.enable_pii_detection,
                'audit_logging': self.enable_audit,
                'access_policies': self.enable_policies
            },
            'pii_detector': {
                'strategy': self.pii_detector.default_strategy.value if self.pii_detector else None,
                'enabled_types': [t.value for t in self.pii_detector.enabled_types] if self.pii_detector else []
            },
            'audit': self.audit_logger.get_session_summary() if self.audit_logger else None,
            'policies': {
                'table_count': len(self.policy_engine.table_policies) if self.policy_engine else 0,
                'global_enabled': self.policy_engine.global_policy.enabled if self.policy_engine else False
            }
        }
        return status

    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of active policies"""
        if not self.policy_engine:
            return {'enabled': False}

        return {
            'enabled': self.policy_engine.global_policy.enabled,
            'max_rows': self.policy_engine.global_policy.max_rows_per_query,
            'pii_detection': self.policy_engine.global_policy.enable_pii_detection,
            'pii_action': self.policy_engine.global_policy.pii_default_action.value,
            'tables_with_policies': list(self.policy_engine.table_policies.keys()),
            'blocked_patterns_count': len(self.policy_engine.global_policy.blocked_patterns)
        }


# Global security layer instance
_security_layer: Optional[SecurityLayer] = None


def get_security_layer() -> SecurityLayer:
    """Get or create the global security layer"""
    global _security_layer
    if _security_layer is None:
        # Look for config in default location
        config_path = Path(__file__).parent.parent.parent / "config" / "policies.yaml"
        _security_layer = SecurityLayer(
            config_path=str(config_path) if config_path.exists() else None
        )
    return _security_layer


def configure_security_layer(**kwargs) -> SecurityLayer:
    """Configure and return the global security layer"""
    global _security_layer
    _security_layer = SecurityLayer(**kwargs)
    return _security_layer
