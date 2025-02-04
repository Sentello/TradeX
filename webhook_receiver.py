import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
import json
import config
from signal_handler import process_signal

# Setup logging
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"  # Inside Docker
else:
    log_directory = "logs"  # Local execution
os.makedirs(log_directory, exist_ok=True)
log_file_path = os.path.join(log_directory, "webhook.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("webhook")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
# add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Webhook initialized!")

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def trade_signal():
    try:
        data = request.json
        if data is None:
            logger.warning("Received empty JSON request")
            return jsonify({"error": "No JSON data"}), 400

        # Validate PIN (if set)
        incoming_pin = data.get("PIN", "")
        if config.WEBHOOK_PIN and incoming_pin != config.WEBHOOK_PIN:
            logger.warning("Invalid webhook PIN received")
            return jsonify({"error": "Invalid pin"}), 403

        logger.info(f"Received webhook data: {data}")
        process_signal(data)

        return jsonify({"status": "ok"}), 200
    except json.JSONDecodeError:
        logger.error("Malformed JSON received in webhook")
        return jsonify({"error": "Malformed JSON"}), 400
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": str(e)}), 500
