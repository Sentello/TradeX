import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# Dashboard
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

# Flask session
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "hardcoded-default-key")
SESSION_LIFETIME_HOURS = float(os.getenv("SESSION_LIFETIME_HOURS", "12"))
SESSION_PERMANENT_LIFETIME = timedelta(hours=SESSION_LIFETIME_HOURS)

# Webhook
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5005"))
WEBHOOK_PIN = os.getenv("WEBHOOK_PIN", "")

# Bybit / Binance credentials
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# Which exchanges to enable (comma-separated list, e.g. "bybit,binance")
EXCHANGES = os.getenv("EXCHANGES", "bybit,binance").lower()

# Default mode for signal ingestion is webhook
MODE = os.getenv("MODE", "webhook").lower()  # "webhook", "email", or "both"

# Email (IMAP)
IMAP_SERVER = os.getenv("IMAP_SERVER", "")
IMAP_PORT = int(os.getenv("IMAP_PORT", ""))
IMAP_EMAIL = os.getenv("IMAP_EMAIL", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
IMAP_USE_SSL = os.getenv("IMAP_USE_SSL", "true").lower() in ["true", "1", "yes"]
IMAP_CHECK_INTERVAL = int(os.getenv("IMAP_CHECK_INTERVAL", "15"))  # seconds
