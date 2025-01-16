import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Secure PIN for webhook
WEBHOOK_PIN = os.getenv("WEBHOOK_PIN", "default_pin")

# Dashboard login password
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "default_password")

# Bybit API credentials
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

# Binance API credentials
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

