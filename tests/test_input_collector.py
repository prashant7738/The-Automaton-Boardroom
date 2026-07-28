"""Unit tests for JSON parsing/validation in agency.nodes.input_collector_node.

The LLM call (agency.nodes.model) and the LangGraph interrupt() are monkeypatched
so these tests exercise only the parsing/validation logic, with no network calls.
"""

import json
from types import SimpleNamespace

import pytest

from agency import nodes


def _fake_model(content):
    """Return a stand-in for agency.nodes.model that yields a fixed LLM response."""
    def _model(prompt, temperature=0.0):
        return SimpleNamespace(content=content)
    return _model


BASE_STATE = {"app_idea": "Add two numbers", "specification": "A simple calculator spec"}


def test_parses_valid_json_array_and_forwards_to_interrupt(monkeypatch):
    fake_json = json.dumps([{"name": "num1", "type": "float", "description": "First number"}])
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"num1": "5"})

    result = nodes.input_collector_node(BASE_STATE)

    assert result["required_inputs"] == [
        {"name": "num1", "type": "float", "description": "First number"}
    ]
    assert result["user_inputs"] == {"num1": "5"}


def test_strips_markdown_fence_before_parsing(monkeypatch):
    fake_json = '```json\n[{"name": "city", "type": "str", "description": "City name"}]\n```'
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"city": "London"})

    result = nodes.input_collector_node(BASE_STATE)

    assert result["required_inputs"] == [
        {"name": "city", "type": "str", "description": "City name"}
    ]


def test_empty_array_skips_interrupt_entirely(monkeypatch):
    monkeypatch.setattr(nodes, "model", _fake_model("[]"))
    interrupt_calls = []
    monkeypatch.setattr(nodes, "interrupt", lambda payload: interrupt_calls.append(payload))

    result = nodes.input_collector_node(BASE_STATE)

    assert result == {"required_inputs": [], "user_inputs": {}}
    assert interrupt_calls == []  # no inputs needed -> interrupt() must not be called


def test_skips_malformed_entries_but_keeps_valid_ones(monkeypatch):
    fake_json = json.dumps(
        [
            {"name": "valid_name", "type": "int", "description": "ok"},
            {"name": "bad name!", "type": "int", "description": "invalid identifier"},
            {"name": "wrong_type", "type": "list", "description": "unsupported type"},
            {"name": "missing_desc"},
            "not_even_a_dict",
        ]
    )
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"valid_name": "1"})

    result = nodes.input_collector_node(BASE_STATE)

    assert result["required_inputs"] == [
        {"name": "valid_name", "type": "int", "description": "ok"}
    ]


@pytest.mark.parametrize("allowed_type", ["int", "float", "str"])
def test_accepts_all_allowed_types(monkeypatch, allowed_type):
    fake_json = json.dumps([{"name": "field", "type": allowed_type, "description": "d"}])
    monkeypatch.setattr(nodes, "model", _fake_model(fake_json))
    monkeypatch.setattr(nodes, "interrupt", lambda payload: {"field": "x"})

    result = nodes.input_collector_node(BASE_STATE)

    assert result["required_inputs"][0]["type"] == allowed_type


def test_malformed_json_response_falls_back_to_no_inputs(monkeypatch):
    monkeypatch.setattr(nodes, "model", _fake_model("this is not JSON at all"))

    result = nodes.input_collector_node(BASE_STATE)

    assert result == {"required_inputs": [], "user_inputs": {}}


def test_llm_failure_is_handled_gracefully(monkeypatch):
    def _raise(prompt, temperature=0.0):
        raise RuntimeError("Both LLM providers failed")

    monkeypatch.setattr(nodes, "model", _raise)

    result = nodes.input_collector_node(BASE_STATE)

    assert result == {"required_inputs": [], "user_inputs": {}}
