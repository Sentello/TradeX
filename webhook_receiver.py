import hmac

import log_setup

# Configure logging before importing modules that create loggers.
log_setup.configure("webhook")

from flask import Flask, jsonify, request  # noqa: E402

import config  # noqa: E402
from dedup import DuplicateFilter, signal_key  # noqa: E402
from log_setup import redact  # noqa: E402
from ratelimit import FailureThrottle, ip_allowed, parse_networks  # noqa: E402
from signal_handler import process_signal  # noqa: E402

logger = log_setup.get_logger("webhook")
logger.info("🎉 Webhook initialized!")

app = Flask(__name__)

ALLOWED_NETWORKS = parse_networks(config.WEBHOOK_ALLOWED_IPS)
if ALLOWED_NETWORKS:
    logger.info(f"🔒 /webhook restricted to: {config.WEBHOOK_ALLOWED_IPS}")
else:
    # Stated, not recommended: an allowlist is only workable when the sender
    # has stable addresses, and a stale entry silently rejects real signals.
    logger.info("/webhook accepts any source address (WEBHOOK_ALLOWED_IPS not set).")

_throttle = FailureThrottle(config.WEBHOOK_MAX_FAILURES, config.WEBHOOK_LOCKOUT_SECONDS)
_duplicates = DuplicateFilter(config.WEBHOOK_DEDUP_SECONDS)

if config.WEBHOOK_DEDUP_SECONDS > 0:
    logger.info(
        f"🔁 Ignoring repeat signals within {config.WEBHOOK_DEDUP_SECONDS}s. "
        "Send a unique ID field in the alert to distinguish a retry from a "
        "genuine second identical order."
    )
else:
    logger.warning("⚠ Duplicate signal suppression is disabled.")


def _client_ip():
    """Caller's address, trusting proxy headers only when told to."""
    if config.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _pin_is_valid(incoming):
    """Constant-time comparison so the PIN can't be recovered by timing."""
    return hmac.compare_digest(str(incoming), config.WEBHOOK_PIN)


@app.route("/webhook", methods=["POST"])
def trade_signal():
    try:
        if not config.WEBHOOK_ENABLED:
            logger.warning(f"Webhook hit while MODE={config.MODE}, refusing.")
            return jsonify({"error": "Webhook ingestion is disabled"}), 503

        client = _client_ip()

        if not ip_allowed(client, ALLOWED_NETWORKS):
            logger.warning(f"Rejected /webhook from disallowed address {client}")
            return jsonify({"error": "Forbidden"}), 403

        # Checked before the payload is parsed, so a locked-out client costs
        # us nothing per guess.
        locked = _throttle.blocked_for(client)
        if locked:
            logger.warning(
                f"Rejected /webhook from locked-out {client}, {locked:.0f}s remaining"
            )
            response = jsonify({"error": "Too many failed attempts"})
            response.headers["Retry-After"] = str(int(locked) + 1)
            return response, 429

        # force=True: senders such as TradingView post JSON as text/plain,
        # which request.json rejects with a 415 before we ever see the body.
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            logger.warning(f"Received a request with no valid JSON object body from {client}")
            return jsonify({"error": "Malformed or missing JSON body"}), 400

        if not _pin_is_valid(data.get("PIN", "")):
            locked = _throttle.record_failure(client)
            logger.warning(
                f"Invalid webhook PIN from {client}"
                + (f", locked out for {locked:.0f}s" if locked else "")
            )
            return jsonify({"error": "Invalid pin"}), 403

        # A correct PIN clears the history, so an attacker cannot strand a
        # legitimate sender that shares their address.
        _throttle.reset(client)

        logger.info(f"Received webhook data: {redact(data)}")

        key = signal_key(data)
        if _duplicates.check(key):
            # 200, not an error: this is the answer to "did my signal land?",
            # and a failure status would invite yet another retry.
            logger.warning(f"Ignoring duplicate signal from {client} ({key})")
            return jsonify({
                "status": "duplicate",
                "message": "Identical signal already accepted; no order placed.",
            }), 200

        result = process_signal(data)

        if result["status"] == "success":
            return jsonify({"status": "ok", "order": result["order"]}), 200

        # Validation failed locally, so nothing reached the exchange and a
        # corrected retry must not be suppressed. An exchange-side failure
        # (502) keeps the key, because we cannot prove the order did not land.
        if result.get("code") == 400:
            _duplicates.forget(key)

        # Report the failure instead of answering 200 for an order that
        # never reached the exchange.
        return jsonify({"error": result["message"]}), result.get("code", 400)
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        return jsonify({"error": "Internal error"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mode": config.MODE}), 200
