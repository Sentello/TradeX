import os
import logging
from logging.handlers import RotatingFileHandler
import config
import ccxt


# Setup logging
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"  # Inside Docker
else:
    log_directory = "logs"  # Local execution
os.makedirs(log_directory, exist_ok=True)
log_file_path = os.path.join(log_directory, "trading.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("trading")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
# add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Trading Signal Handler initialized!")


# Initialize exchanges
exchanges = {
    "bybit": ccxt.bybit({
        "apiKey": config.BYBIT_API_KEY,
        "secret": config.BYBIT_API_SECRET,
        "enableRateLimit": True,
    }),
    "binance": ccxt.binance({
        "apiKey": config.BINANCE_API_KEY,
        "secret": config.BINANCE_API_SECRET,
        "enableRateLimit": True,
    })
}

def process_signal(data):
    try:
        # Validate required fields
        required_fields = ["EXCHANGE", "SYMBOL", "SIDE", "ORDER_TYPE", "QUANTITY"]
        for field in required_fields:
            if field not in data:
                logger.error(f"❌ Missing required field: {field}")
                return

        exchange_name = data["EXCHANGE"].lower()
        symbol = data["SYMBOL"]
        side = data["SIDE"].lower()
        order_type = data["ORDER_TYPE"].lower()
        try:
            quantity = float(data["QUANTITY"])
        except ValueError:
            logger.error("❌ Invalid QUANTITY: must be a number")
            return

        # Validate side
        if side not in ["buy", "sell"]:
            logger.error(f"❌ Invalid SIDE: {side}. Must be 'buy' or 'sell'.")
            return

        # Validate required fields based on order type
        if order_type == "limit":
            if "PRICE" not in data:
                logger.error("❌ Missing required field 'PRICE' for limit order.")
                return
            try:
                price = float(data["PRICE"])
            except ValueError:
                logger.error("❌ Invalid PRICE: must be a number")
                return

        exchange = exchanges.get(exchange_name)
        if not exchange:
            logger.error(f"Exchange '{exchange_name}' is not configured.")
            return

        logger.info(f"Placing order on {exchange_name}: {data}")
        if order_type == "limit":
            order = exchange.create_order(symbol, order_type, side, quantity, price)
        elif order_type == "market":
            order = exchange.create_order(symbol, order_type, side, quantity)
        else:
            logger.error(f"❌ Unsupported order type: {order_type}")
            return

        logger.info(f"✅ Order placed successfully: {order}")
    except Exception as e:
        logger.error(f"❌ Error processing signal: {e}")
