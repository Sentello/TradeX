"""Webhook authentication, parsing and status reporting."""

import json

from conftest import TEST_PIN


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


def _client(app_env, fake_exchange, **env):
    modules = app_env(
        modules=["config", "exchanges", "signal_handler", "webhook_receiver"], **env
    )
    stub = fake_exchange()
    modules["exchanges"].exchanges["bybit"] = stub
    client = modules["webhook_receiver"].app.test_client()
    return client, stub, modules


def test_wrong_pin_is_rejected(app_env, fake_exchange):
    client, stub, _ = _client(app_env, fake_exchange)
    response = client.post("/webhook", json=_payload(PIN="wrong"))
    assert response.status_code == 403
    assert stub.calls == []


def test_missing_pin_is_rejected(app_env, fake_exchange):
    client, stub, _ = _client(app_env, fake_exchange)
    payload = _payload()
    del payload["PIN"]
    response = client.post("/webhook", json=payload)
    assert response.status_code == 403
    assert stub.calls == []


def test_valid_signal_is_accepted(app_env, fake_exchange):
    client, stub, _ = _client(app_env, fake_exchange)
    response = client.post("/webhook", json=_payload())
    assert response.status_code == 200
    assert len(stub.calls) == 1


def test_text_plain_body_is_accepted(app_env, fake_exchange):
    """TradingView posts JSON as text/plain; request.json returned 415 for it."""
    client, stub, _ = _client(app_env, fake_exchange)
    response = client.post(
        "/webhook", data=json.dumps(_payload()), content_type="text/plain"
    )
    assert response.status_code == 200
    assert len(stub.calls) == 1


def test_malformed_body_returns_400(app_env, fake_exchange):
    client, _, _ = _client(app_env, fake_exchange)
    response = client.post("/webhook", data="not json", content_type="application/json")
    assert response.status_code == 400


def test_failed_order_does_not_return_200(app_env, fake_exchange):
    """process_signal used to swallow errors and the caller always saw 200 ok."""
    modules = app_env(
        modules=["config", "exchanges", "signal_handler", "webhook_receiver"]
    )
    modules["exchanges"].exchanges["bybit"] = fake_exchange(
        raises=RuntimeError("insufficient margin")
    )
    client = modules["webhook_receiver"].app.test_client()

    response = client.post("/webhook", json=_payload())

    assert response.status_code == 502
    assert "insufficient margin" in response.get_json()["error"]


def test_invalid_signal_returns_400(app_env, fake_exchange):
    client, _, _ = _client(app_env, fake_exchange)
    response = client.post("/webhook", json=_payload(QUANTITY="-5"))
    assert response.status_code == 400


def test_webhook_disabled_when_mode_is_email_only(app_env, fake_exchange, tmp_path):
    modules = app_env(
        modules=["config", "exchanges", "signal_handler", "webhook_receiver"],
        MODE="email",
        IMAP_SERVER="imap.example.com",
        IMAP_EMAIL="bot@example.com",
        IMAP_PASSWORD="secret",
    )
    stub = fake_exchange()
    modules["exchanges"].exchanges["bybit"] = stub
    client = modules["webhook_receiver"].app.test_client()

    response = client.post("/webhook", json=_payload())

    assert response.status_code == 503
    assert stub.calls == []


def test_pin_is_never_written_to_the_log(app_env, fake_exchange, tmp_path):
    """/logs serves these files to the dashboard, PIN must not be in them."""
    client, _, _ = _client(app_env, fake_exchange)
    client.post("/webhook", json=_payload())
    client.post("/webhook", json=_payload(PIN="a-wrong-pin-value"))

    written = "".join(
        p.read_text() for p in (tmp_path / "logs").glob("*.log")
    )
    assert written, "expected the webhook log to have been written"
    assert TEST_PIN not in written
    assert "a-wrong-pin-value" not in written
