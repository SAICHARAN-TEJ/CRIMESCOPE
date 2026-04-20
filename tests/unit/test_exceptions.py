# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for the core exceptions module."""

import pytest

from backend.core.exceptions import (
    CrimeScopeError,
    IngestionError,
    UnsupportedFileType,
    ExtractionTimeout,
    AgentError,
    AgentTimeout,
    AgentParseError,
    GraphError,
    GraphConnectionError,
    CaseNotFoundError,
)


class TestExceptionHierarchy:
    def test_base_exception(self):
        err = CrimeScopeError("test", detail="details", retryable=True)
        assert str(err) == "test"
        assert err.detail == "details"
        assert err.retryable is True

    def test_ingestion_error_is_crimescope(self):
        assert issubclass(IngestionError, CrimeScopeError)

    def test_extraction_timeout_is_retryable(self):
        err = ExtractionTimeout()
        assert err.retryable is True

    def test_agent_timeout_includes_id(self):
        err = AgentTimeout(agent_id="forensic_analyst_42")
        assert "forensic_analyst_42" in str(err)
        assert err.retryable is True

    def test_graph_connection_retryable(self):
        err = GraphConnectionError()
        assert err.retryable is True

    def test_case_not_found(self):
        err = CaseNotFoundError(case_id="test-001")
        assert "test-001" in str(err)
        assert err.case_id == "test-001"

    def test_catch_all_crimescope(self):
        """All custom exceptions should be catchable as CrimeScopeError."""
        errors = [
            IngestionError("test"),
            UnsupportedFileType("test"),
            AgentError("test"),
            GraphError("test"),
            CaseNotFoundError("test"),
        ]
        for err in errors:
            assert isinstance(err, CrimeScopeError)
