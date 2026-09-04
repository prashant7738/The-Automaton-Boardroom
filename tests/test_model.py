from types import SimpleNamespace

import pytest

from agency import nodes


def test_model_uses_gemini_interactions_and_preserves_content_contract(monkeypatch):
    captured = {}

    class FakeInteractions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                outputs=[SimpleNamespace(text="Gemini response")]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.interactions = FakeInteractions()

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(nodes.genai, "Client", FakeClient)

    response = nodes.model("Explain AI", temperature=0.0)

    assert response.content == "Gemini response"
    assert captured["client"] == {"api_key": "test-key"}
    assert captured["model"] == "gemini-3.7-flash"
    assert captured["input"] == "Explain AI"
    assert "generation_config" not in captured


def test_model_supports_output_text_response_shape(monkeypatch):
    class FakeInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(output_text="Gemini response")

    class FakeClient:
        def __init__(self, **kwargs):
            self.interactions = FakeInteractions()

    monkeypatch.setattr(nodes.genai, "Client", FakeClient)

    assert nodes.model("Explain AI").content == "Gemini response"


def test_model_uses_configured_gemini_model(monkeypatch):
    captured = {}

    class FakeInteractions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="Gemini response")

    class FakeClient:
        def __init__(self, **kwargs):
            self.interactions = FakeInteractions()

    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(nodes.genai, "Client", FakeClient)

    nodes.model("Explain AI")

    assert captured["model"] == "gemini-2.5-flash"


def test_model_raises_clear_error_when_gemini_fails(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            raise ValueError("invalid API key")

    monkeypatch.setattr(nodes.genai, "Client", FakeClient)

    with pytest.raises(RuntimeError, match="Gemini failed"):
        nodes.model("Explain AI")