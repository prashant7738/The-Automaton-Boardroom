from types import SimpleNamespace

import pytest

from agency import nodes, usage


def _fake_openai(monkeypatch, input_tokens=1000, output_tokens=1000, with_usage=True):
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            resp = SimpleNamespace(output_text="ok")
            if with_usage:
                resp.usage = SimpleNamespace(
                    input_tokens=input_tokens, output_tokens=output_tokens
                )
            return resp

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(nodes.openai, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "server-key")
    return calls


def test_compute_cost_uses_configured_prices(monkeypatch):
    monkeypatch.setenv("OPENAI_INPUT_PRICE_PER_1M", "1")
    monkeypatch.setenv("OPENAI_OUTPUT_PRICE_PER_1M", "2")
    assert usage.compute_cost_usd(1_000_000, 500_000) == pytest.approx(2.0)


def test_model_records_usage_per_user(monkeypatch):
    _fake_openai(monkeypatch, input_tokens=100_000, output_tokens=10_000)

    token = usage.set_usage_user("alice@example.com")
    try:
        nodes.model("hi")
    finally:
        usage.reset_usage_user(token)

    alice = usage.get_usage("alice@example.com")
    assert alice["input_tokens"] == 100_000
    assert alice["cost_usd"] == pytest.approx(0.35)
    assert usage.get_usage("bob@example.com")["cost_usd"] == 0


def test_model_blocks_user_over_monthly_limit_without_calling_api(monkeypatch):
    calls = _fake_openai(monkeypatch)
    usage.record_usage(400_000, 0, user_id="alice")  # $1.00 at default price

    token = usage.set_usage_user("alice")
    try:
        with pytest.raises(usage.UsageLimitExceeded, match="Monthly usage limit reached"):
            nodes.model("hi")
    finally:
        usage.reset_usage_user(token)

    assert calls == []


def test_other_users_are_not_blocked_by_one_users_spend(monkeypatch):
    _fake_openai(monkeypatch)
    usage.record_usage(400_000, 0, user_id="alice")

    token = usage.set_usage_user("bob")
    try:
        assert nodes.model("hi").content == "ok"
    finally:
        usage.reset_usage_user(token)


def test_limit_is_configurable(monkeypatch):
    _fake_openai(monkeypatch)
    monkeypatch.setenv("MONTHLY_USER_LIMIT_USD", "5")
    usage.record_usage(400_000, 0, user_id="alice")

    assert usage.get_usage("alice")["limit_usd"] == 5
    usage.check_limit("alice")


def test_usage_resets_each_month(monkeypatch):
    usage.record_usage(400_000, 0, user_id="alice")
    monkeypatch.setattr(usage, "_period", lambda: "2099-01")

    usage.check_limit("alice")
    assert usage.get_usage("alice")["cost_usd"] == 0


def test_user_supplied_key_is_not_metered(monkeypatch):
    _fake_openai(monkeypatch)
    usage.record_usage(400_000, 0, user_id="alice")

    key_token = nodes.set_request_api_key("sk-own")
    user_token = usage.set_usage_user("alice")
    try:
        assert nodes.model("hi").content == "ok"
    finally:
        usage.reset_usage_user(user_token)
        nodes.reset_request_api_key(key_token)

    assert usage.get_usage("alice")["cost_usd"] == pytest.approx(1.0)


def test_usage_estimated_when_api_omits_it(monkeypatch):
    _fake_openai(monkeypatch, with_usage=False)

    nodes.model("a" * 400)

    assert usage.get_usage("anonymous")["input_tokens"] == 100
