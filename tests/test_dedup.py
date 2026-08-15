"""Duplicate signal suppression."""

from conftest import TEST_PIN
from dedup import DuplicateFilter, signal_key


def _payload(**overrides):
    payload = {
        "PIN": TEST_PIN,
        "EXCHANGE": "bybit",
        "SYMBOL": "BTC/USDT:USDT",
        "SIDE": "buy",
        "ORDER_TYPE": "market",
        "QUANTITY": "0.01",
    }
    payload.update(overrides)
    return payload


# --- key derivation ---

def test_identical_payloads_share_a_key():
    assert signal_key(_payload()) == signal_key(_payload())


def test_key_ignores_the_pin():
    """Rotating the PIN must not make an in-flight retry look like a new order."""
    assert signal_key(_payload()) == signal_key(_payload(PIN="something-else"))


def test_key_ignores_field_order():
    a = {"EXCHANGE": "bybit", "SIDE": "buy", "QUANTITY": "1"}
    b = {"QUANTITY": "1", "EXCHANGE": "bybit", "SIDE": "buy"}
    assert signal_key(a) == signal_key(b)


def test_different_quantity_is_a_different_signal():
    assert signal_key(_payload()) != signal_key(_payload(QUANTITY="0.02"))


def test_explicit_id_takes_precedence():
    """Two genuinely separate orders are distinguishable when IDs are sent."""
    assert signal_key(_payload(ID="a")) != signal_key(_payload(ID="b"))
    assert signal_key(_payload(ID="a")).startswith("id:")


def test_explicit_id_matches_across_differing_payloads():
    assert signal_key(_payload(ID="x")) == signal_key(_payload(ID="x", QUANTITY="99"))


# --- the filter ---

def test_second_sighting_is_a_duplicate():
    f = DuplicateFilter(window_seconds=60)
    assert f.check("k") is False
    assert f.check("k") is True


def test_distinct_keys_do_not_collide():
    f = DuplicateFilter(window_seconds=60)
    assert f.check("a") is False
    assert f.check("b") is False


def test_window_expiry_allows_the_signal_again(monkeypatch):
    f = DuplicateFilter(window_seconds=60)
    clock = [1000.0]
    monkeypatch.setattr(f, "_now", lambda: clock[0])

    assert f.check("k") is False
    clock[0] += 30
    assert f.check("k") is True
    clock[0] += 31          # now past the original 60s window
    assert f.check("k") is False


def test_retries_do_not_extend_the_window(monkeypatch):
    """Otherwise a run of retries could suppress a later genuine signal."""
    f = DuplicateFilter(window_seconds=60)
    clock = [1000.0]
    monkeypatch.setattr(f, "_now", lambda: clock[0])

    f.check("k")
    for _ in range(5):
        clock[0] += 10
        f.check("k")
    clock[0] += 15          # 65s after first sighting
    assert f.check("k") is False


def test_zero_window_disables_suppression():
    f = DuplicateFilter(window_seconds=0)
    assert f.check("k") is False
    assert f.check("k") is False


def test_forget_allows_immediate_resend():
    f = DuplicateFilter(window_seconds=60)
    f.check("k")
    f.forget("k")
    assert f.check("k") is False


def test_tracking_is_bounded():
    f = DuplicateFilter(window_seconds=3600, max_tracked=10)
    for i in range(500):
        f.check(f"key-{i}")
    assert len(f._seen) <= 10


# --- webhook integration ---

def _client(app_env, fake_exchange, **env):
    modules = app_env(
        modules=["config", "exchanges", "signal_handler", "webhook_receiver"], **env
    )
    stub = fake_exchange()
    modules["exchanges"].exchanges["bybit"] = stub
    return modules["webhook_receiver"].app.test_client(), stub


def test_replayed_request_places_only_one_order(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange)

    first = client.post("/webhook", json=_payload())
    second = client.post("/webhook", json=_payload())

    assert first.status_code == 200
    assert first.get_json()["status"] == "ok"
    assert second.status_code == 200
    assert second.get_json()["status"] == "duplicate"
    assert len(stub.calls) == 1, "the exchange must only see the order once"


def test_distinct_signals_both_execute(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange)

    client.post("/webhook", json=_payload())
    client.post("/webhook", json=_payload(QUANTITY="0.02"))

    assert len(stub.calls) == 2


def test_unique_ids_allow_repeat_identical_orders(app_env, fake_exchange):
    """A strategy legitimately firing the same order twice, with IDs."""
    client, stub = _client(app_env, fake_exchange)

    client.post("/webhook", json=_payload(ID="alert-1"))
    client.post("/webhook", json=_payload(ID="alert-2"))

    assert len(stub.calls) == 2


def test_dedup_can_be_disabled(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange, WEBHOOK_DEDUP_SECONDS="0")

    client.post("/webhook", json=_payload())
    client.post("/webhook", json=_payload())

    assert len(stub.calls) == 2


def test_validation_failure_does_not_block_a_corrected_retry(app_env, fake_exchange):
    """Nothing reached the exchange, so the fixed signal must go through."""
    client, stub = _client(app_env, fake_exchange)

    bad = client.post("/webhook", json=_payload(QUANTITY="-1"))
    assert bad.status_code == 400

    good = client.post("/webhook", json=_payload(QUANTITY="-1", SIDE="buy"))
    assert good.status_code == 400  # still invalid, but not reported as duplicate
    assert good.get_json().get("error")

    ok = client.post("/webhook", json=_payload())
    assert ok.status_code == 200
    assert len(stub.calls) == 1


def test_exchange_failure_keeps_the_key(app_env, fake_exchange):
    """We cannot prove the order did not land, so suppress the retry."""
    modules = app_env(
        modules=["config", "exchanges", "signal_handler", "webhook_receiver"]
    )
    modules["exchanges"].exchanges["bybit"] = fake_exchange(
        raises=RuntimeError("exchange timeout")
    )
    client = modules["webhook_receiver"].app.test_client()

    first = client.post("/webhook", json=_payload())
    second = client.post("/webhook", json=_payload())

    assert first.status_code == 502
    assert second.get_json()["status"] == "duplicate"


def test_duplicate_does_not_count_against_the_lockout(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange, WEBHOOK_MAX_FAILURES="2")

    for _ in range(5):
        client.post("/webhook", json=_payload())

    # A correct PIN each time, so the throttle must never engage.
    assert client.post("/webhook", json=_payload(QUANTITY="0.05")).status_code == 200
    assert len(stub.calls) == 2
