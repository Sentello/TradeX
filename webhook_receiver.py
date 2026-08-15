import hmac

import log_setup

# Configure logging before importing modules that create loggers.
log_setup.configure("webhook")

from flask import Flask, jsonify, request  # noqa: E402

import config  # noqa: E402
from log_setup import redact  # noqa: E402
from signal_handler import process_signal  # noqa: E402

logger = log_setup.get_logger("webhook")
logger.info("🎉 Webhook initialized!")

app = Flask(__name__)


def _pin_is_valid(incoming):
    """Constant-time comparison so the PIN can't be recovered by timing."""
    return hmac.compare_digest(str(incoming), config.WEBHOOK_PIN)


@app.route("/webhook", methods=["POST"])
def trade_signal():
    try:
        if not config.WEBHOOK_ENABLED:
            logger.warning(f"Webhook hit while MODE={config.MODE}, refusing.")
            return jsonify({"error": "Webhook ingestion is disabled"}), 503

        # force=True: senders such as TradingView post JSON as text/plain,
        # which request.json rejects with a 415 before we ever see the body.
        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            logger.warning("Received a request with no valid JSON object body")
            return jsonify({"error": "Malformed or missing JSON body"}), 400

        if not _pin_is_valid(data.get("PIN", "")):
            logger.warning("Invalid webhook PIN received")
            return jsonify({"error": "Invalid pin"}), 403

        logger.info(f"Received webhook data: {redact(data)}")
        result = process_signal(data)

        if result["status"] == "success":
            return jsonify({"status": "ok", "order": result["order"]}), 200

        # Report the failure instead of answering 200 for an order that
        # never reached the exchange.
        return jsonify({"error": result["message"]}), result.get("code", 400)
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        return jsonify({"error": "Internal error"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mode": config.MODE}), 200
