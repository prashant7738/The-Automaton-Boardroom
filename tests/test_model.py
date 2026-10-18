import httpx
import openai
import pytest
from types import SimpleNamespace

from agency import nodes


def _install_fake_client(monkeypatch, create, clients=None):
    class FakeResponses:
        def create(self, **kwargs):
            return create(**kwargs)

    class FakeClient:
        def __init__(self, **kwargs):
            if clients is not None:
                clients.append(kwargs)
            self.responses = FakeResponses()

    monkeypatch.setattr(nodes.openai, "OpenAI", FakeClient)


def _status_error(cls, status):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status, request=request)
    return cls("boom", response=response, body=None)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_model_uses_openai_responses_and_preserves_content_contract(monkeypatch):
    captured, clients = {}, []

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text="GPT response")

    _install_fake_client(monkeypatch, create, clients)

    response = nodes.model("Explain AI", temperature=0.0)

    assert response.content == "GPT response"
    assert clients[0]["api_key"] == "test-key"
    assert captured["model"] == "gpt-6-luna"
    assert captured["input"] == "Explain AI"
    assert captured["temperature"] == 0.0


def test_model_prefers_request_api_key_over_server_env(monkeypatch):
    clients = []
    monkeypatch.setenv("OPENAI_API_KEY", "server-key")
    _install_fake_client(
        monkeypatch, lambda **kw: SimpleNamespace(output_text="ok"), clients
    )

    token = nodes.set_request_api_key("  user-key  ")
    try:
        nodes.model("Explain AI")
    finally:
        nodes.reset_request_api_key(token)
    nodes.model("Explain AI")

    assert clients[0]["api_key"] == "user-key"
    assert clients[1]["api_key"] == "server-key"


def test_model_uses_configured_model(monkeypatch):
    captured = {}
    monkeypatch.setenv("OPENAI_MODEL", "gpt-custom")

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text="ok")

    _install_fake_client(monkeypatch, create)
    nodes.model("Explain AI")

    assert captured["model"] == "gpt-custom"


def test_model_retries_without_temperature_when_unsupported(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if "temperature" in kwargs:
            err = _status_error(openai.BadRequestError, 400)
            err.args = ("Unsupported parameter: 'temperature'",)
            raise err
        return SimpleNamespace(output_text="ok")

    _install_fake_client(monkeypatch, create)

    assert nodes.model("Explain AI").content == "ok"
    assert len(calls) == 2 and "temperature" not in calls[1]


def test_model_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OpenAI API key not set"):
        nodes.model("Explain AI")


def test_model_maps_rate_limit_error(monkeypatch):
    def create(**kwargs):
        raise _status_error(openai.RateLimitError, 429)

    _install_fake_client(monkeypatch, create)

    with pytest.raises(RuntimeError, match="rate limit or quota"):
        nodes.model("Explain AI")


def test_model_maps_authentication_error(monkeypatch):
    def create(**kwargs):
        raise _status_error(openai.AuthenticationError, 401)

    _install_fake_client(monkeypatch, create)

    with pytest.raises(RuntimeError, match="authentication failed"):
        nodes.model("Explain AI")


def test_model_raises_on_empty_output(monkeypatch):
    _install_fake_client(monkeypatch, lambda **kw: SimpleNamespace(output_text=""))

    with pytest.raises(RuntimeError, match="OpenAI failed"):
        nodes.model("Explain AI")


def test_developer_node_surfaces_generation_failure(monkeypatch):
    def failed_model(prompt, temperature=0.3):
        raise RuntimeError("OpenAI quota exceeded")

    monkeypatch.setattr(nodes, "model", failed_model)

    with pytest.raises(RuntimeError, match="Developer failed to generate source files"):
        nodes.developer_node(
            {
                "app_idea": "Create an ecommerce website",
                "specification": "Build a React storefront",
                "source_code": {},
                "test_logs": "",
                "iterations": 0,
                "approved_by_human": False,
                "human_feedback": "",
                "design_questions": [],
                "design_answers": {},
            }
        )