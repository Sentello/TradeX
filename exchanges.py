"""Single source of truth for ccxt exchange clients.

bot_logic.py and signal_handler.py used to build their own clients with
different settings. The dashboard read futures positions while the webhook
placed spot orders on Binance, because only bot_logic set defaultType.
Everything now shares the clients built here.
"""

import ccxt

import config
from log_setup import get_logger

logger = get_logger("exchanges")

SUPPORTED = ("bybit", "binance")


def _build_bybit():
    client = ccxt.bybit(
        {
            "apiKey": config.BYBIT_API_KEY,
            "secret": config.BYBIT_API_SECRET,
            "enableRateLimit": True,
        }
    )
    # Timestamp synchronization, otherwise Bybit rejects requests as invalid.
    client.options["recvWindow"] = 5000
    client.options["adjustForTimeDifference"] = True
    return client


def _build_binance():
    client = ccxt.binance(
        {
            "apiKey": config.BINANCE_API_KEY,
            "secret": config.BINANCE_API_SECRET,
            "enableRateLimit": True,
            # Must match what the dashboard reads back, or orders land on spot
            # while positions are fetched from futures.
            "options": {"defaultType": "future"},
        }
    )
    client.options["warnOnFetchOpenOrdersWithoutSymbol"] = False
    return client


_BUILDERS = {
    "bybit": (_build_bybit, lambda: (config.BYBIT_API_KEY, config.BYBIT_API_SECRET)),
    "binance": (_build_binance, lambda: (config.BINANCE_API_KEY, config.BINANCE_API_SECRET)),
}


def _load():
    loaded = {}
    for name in SUPPORTED:
        if name not in config.ENABLED_EXCHANGES:
            logger.info(f"⏭ {name} not listed in EXCHANGES, skipping.")
            continue

        builder, credentials = _BUILDERS[name]
        key, secret = credentials()
        if not key or not secret:
            # Building a client anyway would let orders be sent with blank
            # credentials and fail at the exchange instead of here.
            logger.warning(f"⏭ {name} has no API credentials configured, skipping.")
            continue

        logger.info(f"🔄 Setting up {name} API...")
        try:
            loaded[name] = builder()
            logger.info(f"✅ {name} successfully initialized!")
        except Exception as e:
            logger.error(f"❌ Error initializing {name}: {e}")

    if loaded:
        logger.info(f"🎉 Loaded exchanges: {list(loaded.keys())}")
    else:
        logger.error("❌ No exchanges loaded! Double-check API keys and config.")
    return loaded


exchanges = _load()


def get(name):
    """Return a configured client, or None if that exchange is unavailable."""
    return exchanges.get(name)
