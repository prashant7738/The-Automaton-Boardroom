"""Per-user monthly OpenAI spend tracking and enforcement.

Spend is recorded in a small SQLite ledger keyed by (user, calendar month in UTC).
Costs are computed from the token usage returned by the API and the per-1M-token
prices configured via environment variables.
"""

import os
import sqlite3
import threading
from contextlib import closing
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MONTHLY_LIMIT_USD = 1.00
# Prices are configurable because they differ per model; override to match your plan.
DEFAULT_INPUT_PRICE_PER_1M = 2.50
DEFAULT_OUTPUT_PRICE_PER_1M = 10.00
DEFAULT_ANONYMOUS_USER = "anonymous"

_current_user: ContextVar[str | None] = ContextVar("usage_user_id", default=None)
_db_lock = threading.Lock()


class UsageLimitExceeded(RuntimeError):
    """Raised when a user has used up their monthly credit."""


def set_usage_user(user_id: str | None):
    """Scope the usage-tracking identity to the current context; returns a reset token."""
    return _current_user.set((user_id or "").strip() or None)


def reset_usage_user(token) -> None:
    _current_user.reset(token)


def current_user() -> str:
    return _current_user.get() or DEFAULT_ANONYMOUS_USER


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except ValueError:
        return default


def monthly_limit_usd() -> float:
    return _float_env("MONTHLY_USER_LIMIT_USD", DEFAULT_MONTHLY_LIMIT_USD)


def _db_path() -> Path:
    return Path(os.getenv("USAGE_DB_PATH") or ".usage/usage.db")


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS usage (
            user_id TEXT NOT NULL,
            period TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, period)
        )"""
    )
    return conn


def compute_cost_usd(input_tokens: int, output_tokens: int) -> float:
    in_price = _float_env("OPENAI_INPUT_PRICE_PER_1M", DEFAULT_INPUT_PRICE_PER_1M)
    out_price = _float_env("OPENAI_OUTPUT_PRICE_PER_1M", DEFAULT_OUTPUT_PRICE_PER_1M)
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def get_usage(user_id: str | None = None) -> dict:
    """Return this month's usage for the user: tokens, cost, limit and remaining credit."""
    user = user_id or current_user()
    with _db_lock, closing(_connect()) as conn:
        row = conn.execute(
            "SELECT input_tokens, output_tokens, cost_usd FROM usage WHERE user_id=? AND period=?",
            (user, _period()),
        ).fetchone()
    input_tokens, output_tokens, cost = row or (0, 0, 0.0)
    limit = monthly_limit_usd()
    return {
        "user_id": user,
        "period": _period(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "limit_usd": limit,
        "remaining_usd": max(limit - cost, 0.0),
    }


def check_limit(user_id: str | None = None) -> None:
    """Raise UsageLimitExceeded if the user has no credit left this month."""
    usage = get_usage(user_id)
    if usage["cost_usd"] >= usage["limit_usd"]:
        raise UsageLimitExceeded(
            f"Monthly usage limit reached: ${usage['cost_usd']:.2f} of "
            f"${usage['limit_usd']:.2f} used for {usage['period']}. "
            "The limit resets at the start of next month (UTC), or enter your own OpenAI API key "
            "in the sidebar."
        )


def record_usage(input_tokens: int, output_tokens: int, user_id: str | None = None) -> float:
    """Add a request's token usage to the user's monthly total; returns its cost in USD."""
    user = user_id or current_user()
    cost = compute_cost_usd(input_tokens, output_tokens)
    with _db_lock, closing(_connect()) as conn, conn:
        conn.execute(
            """INSERT INTO usage (user_id, period, input_tokens, output_tokens, cost_usd)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, period) DO UPDATE SET
                 input_tokens = input_tokens + excluded.input_tokens,
                 output_tokens = output_tokens + excluded.output_tokens,
                 cost_usd = cost_usd + excluded.cost_usd""",
            (user, _period(), input_tokens, output_tokens, cost),
        )
    return cost
