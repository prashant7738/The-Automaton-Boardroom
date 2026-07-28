"""Unit tests for the conditional-edge routing logic in agency.graph."""

import pytest

from agency.graph import human_router, router


class TestTesterRouter:
    def test_routes_to_developer_when_error_present_within_iteration_budget(self):
        state = {"test_logs": "Traceback...\nError: something failed", "iterations": 2}
        assert router(state) == "developer"

    def test_routes_to_human_review_when_no_error_keywords_present(self):
        state = {"test_logs": "GET / -> 200\n[server ready: True]", "iterations": 1}
        assert router(state) == "human_review"

    def test_routes_to_human_review_once_iteration_budget_is_exhausted(self):
        # Even with a clear error, 5+ iterations should stop the auto-correct loop.
        state = {"test_logs": "SyntaxError: invalid syntax", "iterations": 5}
        assert router(state) == "human_review"

    @pytest.mark.parametrize(
        "keyword",
        [
            "ModuleNotFoundError",
            "ImportError",
            "npm ERR!",
            "command not found",
            "[test result] failed",
            "[tester exception]",
            "FAILED",
            "exit_code",
        ],
    )
    def test_detects_various_error_keywords(self, keyword):
        state = {"test_logs": f"some log line containing {keyword} here", "iterations": 0}
        assert router(state) == "developer"

    def test_missing_test_logs_defaults_to_human_review(self):
        state = {"iterations": 0}
        assert router(state) == "human_review"

    def test_missing_iterations_defaults_to_zero_and_still_loops_on_error(self):
        state = {"test_logs": "Error: boom"}
        assert router(state) == "developer"


class TestHumanRouter:
    def test_ends_workflow_when_human_approves(self):
        state = {"approved_by_human": True}
        assert human_router(state) == "__end__"

    def test_returns_to_developer_when_human_rejects(self):
        state = {"approved_by_human": False}
        assert human_router(state) == "developer"

    def test_defaults_to_developer_when_approval_key_missing(self):
        state = {}
        assert human_router(state) == "developer"
