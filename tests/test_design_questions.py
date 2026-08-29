"""Unit tests for JSON parsing/validation in agency.nodes.design_questions_node.

The LLM call (agency.nodes.model) and the LangGraph interrupt() are monkeypatched
so these tests exercise only the parsing/validation logic, with no network calls.
"""

import json
from types import SimpleNamespace

import pytest

from agency import nodes
from agency.guards import validate_design_questions


def _fake_model(content):
    """Return a stand-in for agency.nodes.model that yields a fixed LLM response."""
    def _model(prompt, temperature=0.0):
        return SimpleNamespace(content=content)
    return _model


BASE_STATE = {"app_idea": "A todo list app", "specification": "A simple todo list spec"}


def test_parses_valid_json_array_and_forwards_to_interrupt(monkeypatch):
    fake_json = json.dumps(
        [{"id": "q1", "question": "Support due dates?", "options": ["Yes", "No"]}]
    )
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"q1": "Yes"})

    result = nodes.design_questions_node(BASE_STATE)

    assert result["design_questions"] == [
        {"id": "q1", "question": "Support due dates?", "options": ["Yes", "No"]}
    ]
    assert result["design_answers"] == {"q1": "Yes"}


def test_interrupt_receives_design_questions_type(monkeypatch):
    fake_json = json.dumps(
        [{"id": "q1", "question": "Support due dates?", "options": ["Yes", "No"]}]
    )
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    captured = {}

    def _capture_interrupt(payload):
        captured.update(payload)
        return {"q1": "Yes"}

    monkeypatch.setattr(nodes, "interrupt", _capture_interrupt)

    nodes.design_questions_node(BASE_STATE)

    assert captured["type"] == "design_questions"
    assert captured["questions"][0]["id"] == "q1"


def test_strips_markdown_fence_before_parsing(monkeypatch):
    fake_json = (
        '```json\n[{"id": "q1", "question": "Which theme?", '
        '"options": ["Light", "Dark", "System"]}]\n```'
    )
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"q1": "Dark"})

    result = nodes.design_questions_node(BASE_STATE)

    assert result["design_questions"] == [
        {"id": "q1", "question": "Which theme?", "options": ["Light", "Dark", "System"]}
    ]


def test_empty_array_skips_interrupt_entirely(monkeypatch):
    monkeypatch.setattr(nodes, "model", _fake_model("[]"))
    interrupt_calls = []
    monkeypatch.setattr(nodes, "interrupt", lambda payload: interrupt_calls.append(payload))

    result = nodes.design_questions_node(BASE_STATE)

    assert result == {"design_questions": [], "design_answers": {}}
    assert interrupt_calls == []  # no decisions needed -> interrupt() must not be called


def test_skips_malformed_entries_but_keeps_valid_ones(monkeypatch):
    fake_json = json.dumps(
        [
            {"id": "valid_q", "question": "Include auth?", "options": ["Yes", "No"]},
            {"id": "bad id!", "question": "invalid identifier", "options": ["A", "B"]},
            {"id": "too_few_opts", "question": "only one option", "options": ["A"]},
            {"id": "missing_question", "options": ["A", "B"]},
            "not_even_a_dict",
        ]
    )
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"valid_q": "Yes"})

    result = nodes.design_questions_node(BASE_STATE)

    assert result["design_questions"] == [
        {"id": "valid_q", "question": "Include auth?", "options": ["Yes", "No"]}
    ]


def test_truncates_more_than_five_questions(monkeypatch):
    fake_questions = [
        {"id": f"q{i}", "question": f"Question {i}?", "options": ["A", "B"]}
        for i in range(1, 8)
    ]
    fake_json = json.dumps(fake_questions)
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {})

    result = nodes.design_questions_node(BASE_STATE)

    assert len(result["design_questions"]) == 5
    assert [q["id"] for q in result["design_questions"]] == [
        "q1", "q2", "q3", "q4", "q5"
    ]


# ---------------------------------------------------------------------------
# Direct unit tests for agency.guards.validate_design_questions
# ---------------------------------------------------------------------------

def test_validate_design_questions_accepts_well_formed_entries():
    parsed = [{"id": "q1", "question": "Include auth?", "options": ["Yes", "No"]}]
    assert validate_design_questions(parsed) == parsed


def test_validate_design_questions_rejects_non_list():
    assert validate_design_questions({"id": "q1"}) == []


@pytest.mark.parametrize(
    "item",
    [
        {"id": "bad id", "question": "q", "options": ["A", "B"]},  # bad identifier
        {"id": "q1", "question": "", "options": ["A", "B"]},  # empty question
        {"id": "q1", "question": "q", "options": ["A"]},  # too few options
        {"id": "q1", "question": "q", "options": ["A", "B", "C", "D", "E", "F", "G"]},  # too many
        {"id": "q1", "question": "q", "options": ["A", ""]},  # blank option
        {"id": "q1", "question": "q"},  # missing options
    ],
)
def test_validate_design_questions_rejects_malformed_entries(item):
    assert validate_design_questions([item]) == []
