import pytest


@pytest.fixture(autouse=True)
def _isolated_usage_db(tmp_path, monkeypatch):
    monkeypatch.setenv("USAGE_DB_PATH", str(tmp_path / "usage.db"))
    monkeypatch.delenv("MONTHLY_USER_LIMIT_USD", raising=False)
    monkeypatch.delenv("OPENAI_INPUT_PRICE_PER_1M", raising=False)
    monkeypatch.delenv("OPENAI_OUTPUT_PRICE_PER_1M", raising=False)
