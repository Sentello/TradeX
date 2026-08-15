"""Position closing safety and API-call efficiency."""

POSITION = {
    "symbol": "BTC/USDT:USDT",
    "side": "long",
    "contracts": 0.5,
    "notional": 25000.0,
    "entryPrice": 50000.0,
    "liquidationPrice": 40000.0,
    "marginRatio": 0.01,
    "leverage": 10,
    "unrealizedPnl": 120.0,
}


def _boot(app_env, fake_exchange, positions=None):
    modules = app_env(modules=["config", "exchanges", "bot_logic"])
    stub = fake_exchange(positions=positions if positions is not None else [POSITION])
    modules["exchanges"].exchanges.clear()
    modules["exchanges"].exchanges["bybit"] = stub
    return modules["bot_logic"], stub


def test_close_position_is_reduce_only(app_env, fake_exchange):
    """Without reduceOnly a closed-in-the-meantime position gets re-opened,
    in the opposite direction."""
    bot_logic, stub = _boot(app_env, fake_exchange)

    result = bot_logic.close_position("bybit", "BTC/USDT:USDT")

    assert result["status"] == "success"
    assert stub.calls[0]["params"] == {"reduceOnly": True}
    assert stub.calls[0]["side"] == "sell"  # closing a long
    assert stub.calls[0]["amount"] == 0.5


def test_close_short_position_buys_back(app_env, fake_exchange):
    short = dict(POSITION, side="short")
    bot_logic, stub = _boot(app_env, fake_exchange, positions=[short])

    bot_logic.close_position("bybit", "BTC/USDT:USDT")

    assert stub.calls[0]["side"] == "buy"


def test_close_all_positions_fetches_once(app_env, fake_exchange):
    """This used to call get_positions() once per position: O(n^2) API calls."""
    positions = [
        dict(POSITION, symbol=f"SYM{i}/USDT:USDT") for i in range(5)
    ]
    bot_logic, stub = _boot(app_env, fake_exchange, positions=positions)

    bot_logic.close_all_positions()

    assert stub.fetch_positions_count == 1
    assert len([c for c in stub.calls if c["method"] == "create_order"]) == 5


def test_summary_stats_fetches_positions_once(app_env, fake_exchange):
    bot_logic, stub = _boot(app_env, fake_exchange)

    bot_logic.calculate_summary_stats()

    assert stub.fetch_positions_count == 1


def test_margin_used_is_notional_over_leverage(app_env, fake_exchange):
    """The old formula multiplied notional by the maintenance margin ratio."""
    bot_logic, _ = _boot(app_env, fake_exchange)

    stats = bot_logic.calculate_summary_stats()

    assert stats["margin_used"] == 2500.0  # 25000 notional / 10x leverage
    assert stats["total_pnl"] == 120.0


def test_unknown_exchange_is_reported(app_env, fake_exchange):
    bot_logic, _ = _boot(app_env, fake_exchange)
    result = bot_logic.close_position("kraken", "BTC/USDT:USDT")
    assert result["status"] == "error"
