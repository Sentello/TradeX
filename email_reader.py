import log_setup

# Configure logging before importing modules that create loggers.
log_setup.configure("email_reader")

import email  # noqa: E402
import hmac  # noqa: E402
import html  # noqa: E402
import imaplib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import ssl  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from email.header import decode_header, make_header  # noqa: E402

import config  # noqa: E402
from dedup import DuplicateFilter, signal_key  # noqa: E402
from log_setup import redact  # noqa: E402
from signal_handler import process_signal  # noqa: E402

logger = log_setup.get_logger("email_reader")
logger.info("🎉 Email Reader initialized!")

# The \Seen flag stops the same message being reprocessed; this catches a
# genuinely duplicated delivery, which arrives as a different message.
_duplicates = DuplicateFilter(config.WEBHOOK_DEDUP_SECONDS)


def decode_subject(msg):
    """Decode an RFC 2047 encoded subject header.

    The previous latin-1 round-trip used the *body* charset and broke on
    base64-encoded (=?utf-8?B?...) subjects.
    """
    raw = msg.get("Subject", "")
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw))).strip()
    except Exception as e:
        logger.warning(f"[Email Reader] ⚠ Could not decode subject header: {e}")
        return raw.strip()


def parse_email_subject(subject):
    """Extracts and parses JSON data from the email subject."""
    logger.info(f"[Email Reader] 📩 Checking email with subject: {subject[:80]}")

    if not subject.startswith("Alert:"):
        return None

    try:
        # Extract the JSON part after "Alert:"
        json_part = subject.split("Alert:", 1)[1].strip()

        # Decode HTML entities (e.g., &nbsp;, &zwj;)
        json_part = html.unescape(json_part)

        # Remove invisible characters and whitespace artifacts
        json_part = re.sub(r'[\u200B-\u200D\uFEFF]', '', json_part)  # Remove zero-width spaces
        json_part = json_part.replace('\n', '').replace('\r', '')  # Remove newlines

        return json.loads(json_part)
    except json.JSONDecodeError as e:
        logger.error(f"[Email Reader] ❌ Could not parse subject as JSON: {e}")
    return None


def _connect():
    if config.IMAP_USE_SSL:
        return imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
    context = ssl.create_default_context()
    mail = imaplib.IMAP4(config.IMAP_SERVER, config.IMAP_PORT)
    mail.starttls(ssl_context=context)
    return mail


def _handle_message(mail, e_id):
    status, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
    if status != "OK":
        return

    msg = email.message_from_bytes(msg_data[0][1])
    alert_data = parse_email_subject(decode_subject(msg))

    if not alert_data:
        logger.info("[Email Reader] 📌 Non-trade email detected, leaving it UNSEEN.")
        return

    if not isinstance(alert_data, dict):
        logger.warning("[Email Reader] ❌ Alert payload is not a JSON object.")
        return

    if not hmac.compare_digest(str(alert_data.get("PIN", "")), config.WEBHOOK_PIN):
        logger.warning("[Email Reader] ❌ Invalid PIN in email alert.")
        return

    # Flag before trading. If the process dies mid-order, an unflagged mail
    # would be picked up again on restart and place the order a second time;
    # a missed signal is preferable to a duplicated one.
    mail.store(e_id, "+FLAGS", "\\Seen")

    key = signal_key(alert_data)
    if _duplicates.check(key):
        logger.warning(f"[Email Reader] 🔁 Ignoring duplicate signal ({key})")
        return

    logger.info(f"[Email Reader] ✅ Processing alert: {redact(alert_data)}")
    result = process_signal(alert_data)
    if result["status"] != "success":
        logger.error(f"[Email Reader] ❌ Signal rejected: {result['message']}")
        if result.get("code") == 400:
            # Nothing reached the exchange, so do not suppress a corrected retry.
            _duplicates.forget(key)


def check_inbox():
    """Connects to the IMAP server, reads unread emails, and processes only trade-related alerts."""
    mail = None
    try:
        logger.info("[Email Reader] 🔄 Connecting to IMAP server...")
        mail = _connect()
        mail.login(config.IMAP_EMAIL, config.IMAP_PASSWORD)
        mail.select("INBOX")
        logger.info("[Email Reader] ✅ IMAP connection successful.")

        # Search for unread emails
        status, data = mail.search(None, '(UNSEEN)')
        if status != "OK":
            logger.warning("[Email Reader] ⚠ No new emails or failed to search inbox.")
            return

        email_ids = data[0].split()
        logger.info(f"[Email Reader] 📩 {len(email_ids)} new emails found.")

        for e_id in email_ids:
            try:
                _handle_message(mail, e_id)
            except Exception as e:
                logger.error(f"[Email Reader] ❌ Error processing email {e_id}: {e}")

        logger.info("[Email Reader] ✅ Finished processing emails.")
    except imaplib.IMAP4.error as e:
        logger.error(f"[Email Reader] ❌ IMAP error: {e}")
    except Exception as e:
        logger.error(f"[Email Reader] ❌ Unexpected error: {e}")
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass


def run_email_reader():
    """Runs the email reader in an infinite loop."""
    if not config.EMAIL_ENABLED:
        # Supervisor treats a clean exit as "do not restart".
        logger.info(f"[Email Reader] ⏭ MODE={config.MODE}, email ingestion disabled.")
        return

    logger.info("[Email Reader] 🚀 Starting email reader...")
    try:
        while True:
            check_inbox()
            time.sleep(config.IMAP_CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[Email Reader] 🛑 Stopping manually.")


if __name__ == "__main__":
    run_email_reader()
    sys.exit(0)
