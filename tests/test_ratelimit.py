"""Per-IP lockout and the webhook allowlist."""

import pytest

from conftest import TEST_PIN
from ratelimit import FailureThrottle, ip_allowed, parse_networks


def test_blocks_after_max_failures():
    throttle = FailureThrottle(max_failures=3, lockout_seconds=300)
    assert throttle.record_failure("1.2.3.4") == 0
    assert throttle.record_failure("1.2.3.4") == 0
    assert throttle.record_failure("1.2.3.4") > 0
    assert throttle.blocked_for("1.2.3.4") > 0


def test_lockout_is_per_client():
    """A global lock would let anyone disable trading with a few requests."""
    throttle = FailureThrottle(max_failures=2, lockout_seconds=300)
    throttle.record_failure("1.2.3.4")
    throttle.record_failure("1.2.3.4")

    assert throttle.blocked_for("1.2.3.4") > 0
    assert throttle.blocked_for("5.6.7.8") == 0


def test_success_clears_history():
    throttle = FailureThrottle(max_failures=3, lockout_seconds=300)
    throttle.record_failure("1.2.3.4")
    throttle.reset("1.2.3.4")
    assert throttle.record_failure("1.2.3.4") == 0


def test_lockout_expires(monkeypatch):
    throttle = FailureThrottle(max_failures=1, lockout_seconds=60)
    clock = [1000.0]
    monkeypatch.setattr(throttle, "_now", lambda: clock[0])

    throttle.record_failure("1.2.3.4")
    assert throttle.blocked_for("1.2.3.4") > 0

    clock[0] += 61
    assert throttle.blocked_for("1.2.3.4") == 0


def test_tracking_is_bounded():
    """An attacker rotating source addresses must not grow memory forever."""
    throttle = FailureThrottle(max_failures=5, lockout_seconds=300, max_tracked=10)
    for i in range(500):
        throttle.record_failure(f"10.0.0.{i}")
    assert len(throttle._entries) <= 10


@pytest.mark.parametrize(
    "address, allowed",
    [
        ("52.89.214.238", True),
        ("34.212.75.30", True),
        ("9.9.9.9", False),
        ("10.0.0.7", True),      # inside the CIDR
        ("10.0.1.7", False),     # outside it
        ("not-an-ip", False),
    ],
)
def test_ip_allowlist(address, allowed):
    networks = parse_networks("52.89.214.238, 34.212.75.30, 10.0.0.0/24")
    assert ip_allowed(address, networks) is allowed


def test_empty_allowlist_permits_everything():
    assert ip_allowed("9.9.9.9", parse_networks("")) is True


# --- webhook integration ---

def _payload(pin=TEST_PIN):
    return {
        "PIN": pin,
        "EXCHANGE": "bybit",
        "SYMBOL": "BTC/USDT:USDT",
        "SIDE": "buy",
        "ORDER_TYPE": "market",
        "QUANTITY": "0.01",
    }


def _client(app_env, fake_exchange, **env):
    modules = app_env(
        modules=["config", "exchanges", "signal_handler", "webhook_receiver"], **env
    )
    stub = fake_exchange()
    modules["exchanges"].exchanges["bybit"] = stub
    return modules["webhook_receiver"].app.test_client(), stub


def test_repeated_bad_pins_lock_the_client_out(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange, WEBHOOK_MAX_FAILURES="3")

    for _ in range(3):
        assert client.post("/webhook", json=_payload("000000")).status_code == 403

    response = client.post("/webhook", json=_payload("000000"))
    assert response.status_code == 429
    assert response.headers["Retry-After"]
    assert stub.calls == []


def test_lockout_applies_before_the_pin_is_checked(app_env, fake_exchange):
    """Once locked out, even a correct PIN is refused for the cooldown."""
    client, stub = _client(app_env, fake_exchange, WEBHOOK_MAX_FAILURES="2")

    for _ in range(2):
        client.post("/webhook", json=_payload("000000"))

    assert client.post("/webhook", json=_payload()).status_code == 429
    assert stub.calls == []


def test_correct_pin_resets_the_failure_count(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange, WEBHOOK_MAX_FAILURES="3")

    client.post("/webhook", json=_payload("000000"))
    client.post("/webhook", json=_payload("000000"))
    assert client.post("/webhook", json=_payload()).status_code == 200

    # Counter cleared, so the next bad PIN starts from zero rather than
    # tipping straight into a lockout.
    assert client.post("/webhook", json=_payload("000000")).status_code == 403
    assert len(stub.calls) == 1


def test_allowlist_blocks_unknown_source(app_env, fake_exchange):
    client, stub = _client(
        app_env, fake_exchange, WEBHOOK_ALLOWED_IPS="52.89.214.238,34.212.75.30"
    )
    # The Flask test client presents as 127.0.0.1.
    response = client.post("/webhook", json=_payload())
    assert response.status_code == 403
    assert stub.calls == []


def test_allowlist_permits_listed_source(app_env, fake_exchange):
    client, stub = _client(app_env, fake_exchange, WEBHOOK_ALLOWED_IPS="127.0.0.1")
    assert client.post("/webhook", json=_payload()).status_code == 200
    assert len(stub.calls) == 1


def test_forwarded_header_is_ignored_by_default(app_env, fake_exchange):
    """Otherwise a client spoofs X-Forwarded-For and walks past the allowlist."""
    client, stub = _client(app_env, fake_exchange, WEBHOOK_ALLOWED_IPS="52.89.214.238")

    response = client.post(
        "/webhook", json=_payload(), headers={"X-Forwarded-For": "52.89.214.238"}
    )

    assert response.status_code == 403
    assert stub.calls == []


def test_forwarded_header_is_used_when_trusted(app_env, fake_exchange):
    client, stub = _client(
        app_env,
        fake_exchange,
        WEBHOOK_ALLOWED_IPS="52.89.214.238",
        TRUST_PROXY_HEADERS="true",
    )

    response = client.post(
        "/webhook", json=_payload(), headers={"X-Forwarded-For": "52.89.214.238, 10.0.0.1"}
    )

    assert response.status_code == 200
    assert len(stub.calls) == 1
