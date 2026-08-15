"""Validation and execution of an incoming trade signal.

Returns a result dict instead of swallowing failures, so the webhook can
answer with a status that reflects whether the order actually reached the
exchange.
"""

import exchanges as exchange_registry
from log_setup import get_logger, redact

logger = get_logger("signal_handler")

REQUIRED_FIELDS = ("EXCHANGE", "SYMBOL", "SIDE", "ORDER_TYPE", "QUANTITY")
VALID_SIDES = ("buy", "sell")
VALID_ORDER_TYPES = ("market", "limit")


def _error(message, code=400):
    logger.error(f"❌ {message}")
    return {"status": "error", "message": message, "code": code}


def _positive_number(data, field):
    """Parse a numeric field, rejecting zero, negatives and junk."""
    try:
        value = float(data[field])
    except (TypeError, ValueError):
        return None, f"Invalid {field}: must be a number"
    if value <= 0:
        return None, f"Invalid {field}: must be greater than zero"
    return value, None


def validate_signal(data):
    """Return (parsed_order, error_result). Exactly one is None."""
    if not isinstance(data, dict):
        return None, _error("Signal payload must be a JSON object")

    for field in REQUIRED_FIELDS:
        if field not in data:
            return None, _error(f"Missing required field: {field}")

    exchange_name = str(data["EXCHANGE"]).strip().lower()
    symbol = str(data["SYMBOL"]).strip()
    side = str(data["SIDE"]).strip().lower()
    order_type = str(data["ORDER_TYPE"]).strip().lower()

    if not symbol:
        return None, _error("Invalid SYMBOL: must not be empty")
    if side not in VALID_SIDES:
        return None, _error(f"Invalid SIDE: {side}. Must be 'buy' or 'sell'.")
    if order_type not in VALID_ORDER_TYPES:
        return None, _error(f"Unsupported ORDER_TYPE: {order_type}")

    quantity, problem = _positive_number(data, "QUANTITY")
    if problem:
        return None, _error(problem)

    price = None
    if order_type == "limit":
        if "PRICE" not in data:
            return None, _error("Missing required field 'PRICE' for limit order.")
        price, problem = _positive_number(data, "PRICE")
        if problem:
            return None, _error(problem)

    exchange = exchange_registry.get(exchange_name)
    if exchange is None:
        # Unconfigured exchanges used to reach the API with blank credentials.
        return None, _error(
            f"Exchange '{exchange_name}' is not configured or has no API credentials.",
            code=400,
        )

    order = {
        "exchange_name": exchange_name,
        "exchange": exchange,
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }
    return order, None


def process_signal(data):
    """Validate and place an order. Always returns a result dict."""
    try:
        order, problem = validate_signal(data)
        if problem:
            return problem

        logger.info(
            f"Placing order on {order['exchange_name']}: {redact(data)}"
        )
        placed = order["exchange"].create_order(
            order["symbol"],
            order["order_type"],
            order["side"],
            order["quantity"],
            order["price"],
        )
        logger.info(f"✅ Order placed successfully: {placed}")
        return {"status": "success", "order": placed, "code": 200}
    except Exception as e:
        # The exchange rejected it (margin, symbol, permissions, connectivity).
        logger.error(f"❌ Error processing signal: {e}")
        return {"status": "error", "message": str(e), "code": 502}
