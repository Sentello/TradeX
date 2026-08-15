"""Email ingestion, with emphasis on what reaches the log files.

The dashboard serves logs/*.log over HTTP via /logs, so anything written
there is effectively published to whoever can reach the dashboard.
"""

import json

from conftest import TEST_PIN


def _log_text(tmp_path):
    return "".join(p.read_text() for p in (tmp_path / "logs").glob("*.log"))


def _boot(app_env, **env):
    return app_env(
        modules=["config", "exchanges", "signal_handler", "email_reader"], **env
    )["email_reader"]


def _alert_subject(pin=TEST_PIN, **overrides):
    payload = {
        "PIN": pin,
        "EXCHANGE": "bybit",
        "SYMBOL": "BTC/USDT:USDT",
        "SIDE": "buy",
        "ORDER_TYPE": "market",
        "QUANTITY": "0.01",
    }
    payload.update(overrides)
    return "Alert: " + json.dumps(payload)


def test_pin_never_reaches_the_log_file(app_env, tmp_path):
    """The subject was logged raw before redaction, so the PIN landed in
    email_reader.log, which /logs then serves."""
    reader = _boot(app_env)

    parsed = reader.parse_email_subject(_alert_subject())

    assert parsed["EXCHANGE"] == "bybit", "the signal must still parse"
    written = _log_text(tmp_path)
    assert written, "expected something to have been logged"
    assert TEST_PIN not in written


def test_numeric_pin_is_also_masked(app_env, tmp_path):
    """A short numeric PIN is unquoted in JSON and must not slip through."""
    reader = _boot(app_env, WEBHOOK_PIN="778899")
    reader.parse_email_subject('Alert: {"PIN": 778899, "EXCHANGE": "bybit"}')
    assert "778899" not in _log_text(tmp_path)


def test_non_alert_subjects_are_still_logged(app_env, tmp_path):
    """Redaction must not blind the log to ordinary mail."""
    reader = _boot(app_env)
    assert reader.parse_email_subject("Your monthly statement") is None
    assert "Your monthly statement" in _log_text(tmp_path)


def test_signal_still_parses_after_redaction(app_env):
    reader = _boot(app_env)
    parsed = reader.parse_email_subject(_alert_subject(QUANTITY="0.5"))
    assert parsed["QUANTITY"] == "0.5"
    assert parsed["PIN"] == TEST_PIN, "redaction is for logs only, not the payload"


def test_malformed_alert_is_reported_without_leaking(app_env, tmp_path):
    reader = _boot(app_env)
    assert reader.parse_email_subject('Alert: {"PIN": "' + TEST_PIN + '", broken') is None
    assert TEST_PIN not in _log_text(tmp_path)


def test_html_entity_subject_does_not_leak_the_pin(app_env, tmp_path):
    """TradingView/mail clients may HTML-escape the subject. It still parses
    as a signal, but redaction looked for a real "PIN": and missed it, so the
    secret reached the log."""
    reader = _boot(app_env)

    parsed = reader.parse_email_subject(
        "Alert: {&quot;PIN&quot;: &quot;" + TEST_PIN + "&quot;, "
        "&quot;EXCHANGE&quot;: &quot;bybit&quot;}"
    )

    assert parsed["EXCHANGE"] == "bybit", "the escaped signal must still parse"
    assert TEST_PIN not in _log_text(tmp_path)


def test_zero_width_obfuscated_subject_does_not_leak_the_pin(app_env, tmp_path):
    reader = _boot(app_env)
    reader.parse_email_subject(
        'Alert: {"P​IN": "' + TEST_PIN + '", "EXCHANGE": "bybit"}'
    )
    assert TEST_PIN not in _log_text(tmp_path)
