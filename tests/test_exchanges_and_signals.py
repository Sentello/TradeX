"""The critical trading-path fixes."""

import pytest


def test_binance_client_uses_futures(app_env):
    """The webhook used to place SPOT orders while the dashboard read futures."""
    exchanges = app_env(modules=["config", "exchanges"])["exchanges"]
    assert exchanges.get("binance").options["defaultType"] == "future"


def test_exchange_without_credentials_is_not_loaded(app_env):
    """A blank-credential client used to be built and fail at the exchange."""
    exchanges = app_env(
        modules=["config", "exchanges"], BINANCE_API_KEY=None, BINANCE_API_SECRET=None
    )["exchanges"]
    assert exchanges.get("binance") is None
    assert exchanges.get("bybit") is not None


def test_exchanges_allowlist_is_honoured(app_env):
    """config.EXCHANGES was defined but never read."""
    exchanges = app_env(modules=["config", "exchanges"], EXCHANGES="bybit")["exchanges"]
    assert exchanges.get("binance") is None
    assert exchanges.get("bybit") is not None


def _signal(**overrides):
    payload = {
        "EXCHANGE": "bybit",
        "SYMBOL": "BTC/USDT:USDT",
        "SIDE": "buy",
        "ORDER_TYPE": "market",
        "QUANTITY": "0.01",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "payload, expected",
    [
        (_signal(QUANTITY="-1"), "greater than zero"),
        (_signal(QUANTITY="0"), "greater than zero"),
        (_signal(QUANTITY="abc"), "must be a number"),
        (_signal(SIDE="sideways"), "Invalid SIDE"),
        (_signal(ORDER_TYPE="stop"), "Unsupported ORDER_TYPE"),
        (_signal(ORDER_TYPE="limit"), "PRICE"),
        ({"EXCHANGE": "bybit"}, "Missing required field"),
    ],
)
def test_invalid_signals_are_rejected(app_env, payload, expected):
    modules = app_env(modules=["config", "exchanges", "signal_handler"])
    result = modules["signal_handler"].process_signal(payload)
    assert result["status"] == "error"
    assert expected in result["message"]


def test_unconfigured_exchange_is_rejected_before_any_api_call(app_env):
    modules = app_env(
        modules=["config", "exchanges", "signal_handler"],
        BINANCE_API_KEY=None,
        BINANCE_API_SECRET=None,
    )
    result = modules["signal_handler"].process_signal(_signal(EXCHANGE="binance"))
    assert result["status"] == "error"
    assert "not configured" in result["message"]


def test_successful_market_order(app_env, fake_exchange):
    modules = app_env(modules=["config", "exchanges", "signal_handler"])
    stub = fake_exchange()
    modules["exchanges"].exchanges["bybit"] = stub

    result = modules["signal_handler"].process_signal(_signal())

    assert result["status"] == "success"
    assert stub.calls[0]["type"] == "market"
    assert stub.calls[0]["side"] == "buy"
    assert stub.calls[0]["amount"] == 0.01


def test_exchange_failure_is_reported_not_swallowed(app_env, fake_exchange):
    modules = app_env(modules=["config", "exchanges", "signal_handler"])
    modules["exchanges"].exchanges["bybit"] = fake_exchange(
        raises=RuntimeError("insufficient margin")
    )

    result = modules["signal_handler"].process_signal(_signal())

    assert result["status"] == "error"
    assert "insufficient margin" in result["message"]
    assert result["code"] == 502
