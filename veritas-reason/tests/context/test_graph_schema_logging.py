"""Regression tests for graph schema migration logging behavior."""

import logging
from unittest.mock import Mock

from veritasreason.context.graph_schema import create_decision_constraints


def test_create_decision_constraints_logs_legacy_drop_failure(caplog):
    graph_store = Mock()

    def _execute_query(query, *args, **kwargs):
        if "DROP CONSTRAINT policy_id_unique IF EXISTS" in query:
            raise RuntimeError("drop failed")
        return {"records": []}

    graph_store.execute_query = Mock(side_effect=_execute_query)

    with caplog.at_level(logging.WARNING):
        create_decision_constraints(graph_store)

    assert "Failed to drop legacy policy_id_unique constraint" in caplog.text
