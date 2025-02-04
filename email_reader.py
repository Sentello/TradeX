import time
import imaplib
import ssl
import email
import json
import logging
import os
import sys
import html
import re
import quopri
from logging.handlers import RotatingFileHandler

import config
from signal_handler import process_signal

# Setup logging
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"  # Inside Docker
else:
    log_directory = "logs"  # Local execution
os.makedirs(log_directory, exist_ok=True)

log_file_path = os.path.join(log_directory, "email_reader.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("email_reader")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Email Reader initialized!")


def parse_email_subject(msg):
    """Extracts and parses JSON data from the email subject."""
    subject = msg.get("Subject", "").strip()
    logger.info(f"[Email Reader] 📩 Checking email with subject: {subject}")

    if subject.startswith("Alert:"):
        try:
            # Extract the JSON part after "Alert:"
            json_part = subject.split("Alert:", 1)[1].strip()

            # Decode HTML entities (e.g., &nbsp;, &zwj;)
            json_part = html.unescape(json_part)

            # Remove invisible characters and whitespace artifacts
            json_part = re.sub(r'[\u200B-\u200D\uFEFF]', '', json_part)  # Remove zero-width spaces
            json_part = json_part.replace('\n', '').replace('\r', '')  # Remove newlines

            # Parse the cleaned JSON
            return json.loads(json_part)
        except json.JSONDecodeError as e:
            logger.error(f"[Email Reader] ❌ Could not parse subject as JSON: {e}")
    return None


def check_inbox():
    """Connects to the IMAP server, reads unread emails, and processes only trade-related alerts."""
    try:
        logger.info("[Email Reader] 🔄 Connecting to IMAP server...")
        if config.IMAP_USE_SSL:
            mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
        else:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4(config.IMAP_SERVER, config.IMAP_PORT)
            mail.starttls(ssl_context=context)
        mail.login(config.IMAP_EMAIL, config.IMAP_PASSWORD)
        mail.select("INBOX")
        logger.info("[Email Reader] ✅ IMAP connection successful.")

        # Search for unread emails
        status, data = mail.search(None, '(UNSEEN)')
        if status != "OK":
            logger.warning("[Email Reader] ⚠ No new emails or failed to search inbox.")
            mail.logout()
            return

        email_ids = data[0].split()
        logger.info(f"[Email Reader] 📩 {len(email_ids)} new emails found.")

        for e_id in email_ids:
            try:
                # Fetch email in "peek" mode to avoid marking it as seen
                status, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
                if status == "OK":
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Decode subject if necessary
                    subject = msg.get("Subject", "")
                    if msg.get_content_charset():
                        subject = subject.encode('latin-1').decode(msg.get_content_charset())
                    subject = quopri.decodestring(subject).decode('utf-8')  # Decode quoted-printable

                    msg.replace_header("Subject", subject)  # Replace the subject with the decoded version

                    alert_data = parse_email_subject(msg)
                    if alert_data:
                        logger.info(f"[Email Reader] ✅ Processing alert: {alert_data}")

                        # Validate PIN (if required)
                        if config.WEBHOOK_PIN:
                            incoming_pin = alert_data.get("PIN", "")
                            if incoming_pin != config.WEBHOOK_PIN:
                                logger.warning(f"[Email Reader] ❌ Invalid PIN in email alert: {incoming_pin}")
                                continue

                        process_signal(alert_data)
                        mail.store(e_id, "+FLAGS", "\\Seen")  # Mark only trade emails as read
                    else:
                        logger.info("[Email Reader] 📌 Non-trade email detected, leaving it UNSEEN.")
            except Exception as e:
                logger.error(f"[Email Reader] ❌ Error processing email {e_id}: {e}")

        mail.logout()
        logger.info("[Email Reader] ✅ Finished processing emails.")
    except imaplib.IMAP4.error as e:
        logger.error(f"[Email Reader] ❌ IMAP error: {e}")
    except Exception as e:
        logger.error(f"[Email Reader] ❌ Unexpected error: {e}")



def run_email_reader():
    """Runs the email reader in an infinite loop."""
    logger.info("[Email Reader] 🚀 Starting email reader...")
    try:
        while True:
            check_inbox()
            time.sleep(config.IMAP_CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[Email Reader] 🛑 Stopping manually.")
    except Exception as e:
        logger.error(f"[Email Reader] ❌ Fatal error: {e}")


if __name__ == "__main__":
    run_email_reader()
