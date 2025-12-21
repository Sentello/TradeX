import ccxt
import logging
import config
import os
from logging.handlers import RotatingFileHandler

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

logger.info("🔄 Initializing exchanges...")


# Initialize exchanges dictionary
exchanges = {}

if config.BYBIT_API_KEY and config.BYBIT_API_SECRET:
    logger.info("🔄 Setting up Bybit API...")
    try:
        exchanges['bybit'] = ccxt.bybit({
            'apiKey': config.BYBIT_API_KEY,
            'secret': config.BYBIT_API_SECRET
        })
        # Enable timestamp synchronization to prevent "invalid request" errors
        exchanges['bybit'].options["recvWindow"] = 5000
        exchanges['bybit'].options["adjustForTimeDifference"] = True
        logger.info("✅ Bybit successfully initialized!")
    except Exception as e:
        logger.error(f"❌ Error initializing Bybit: {e}")

if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
    logger.info("🔄 Setting up Binance API...")
    try:
        exchanges['binance'] = ccxt.binance({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET,
            'options': {
                'defaultType': 'future'  # Use futures account by default
            }
        })
        # Suppress the warning about fetching open orders without specifying a symbol
        exchanges['binance'].options["warnOnFetchOpenOrdersWithoutSymbol"] = False
        logger.info("✅ Binance successfully initialized!")
    except Exception as e:
        logger.error(f"❌ Error initializing Binance: {e}")

# Log final exchange state
if exchanges:
    logger.info(f"🎉 Loaded exchanges: {list(exchanges.keys())}")
else:
    logger.error("❌ No exchanges loaded! Double-check API keys and config.")

# ==============================
# 🚀 Functions for Trading Logic
# ==============================

def get_positions():
    """Returns a dict of exchange_name -> list of open positions."""
    logger.info("📊 Fetching open positions...")
    positions_data = {}

    if not exchanges:
        logger.error("❌ No exchanges loaded! Check API keys and config.")
        return positions_data

    for exchange_name, exchange in exchanges.items():
        positions_data[exchange_name] = []
        try:
            all_positions = exchange.fetch_positions()
            for pos in all_positions:
                if (pos.get('contracts', 0) != 0) or (pos.get('notional', 0) != 0):  # Futures positions have non-zero contracts or notional
                    positions_data[exchange_name].append({
                        "symbol": pos.get('symbol', 'N/A'),
                        "side": pos.get('side', 'N/A'),
                        "contracts": pos.get('contracts', 0),
                        "notional": pos.get('notional', 0.0),
                        "entry_price": pos.get('entryPrice', 0.0),
                        "liquidation_price": pos.get('liquidationPrice', None),
                        "margin_ratio": pos.get('marginRatio', None),
                        "leverage": pos.get('leverage', None),
                        "unrealized_pnl": pos.get('unrealizedPnl', 0.0),
                        "exchange": exchange_name
                    })
        except Exception as e:
            logger.error(f"❌ [get_positions] Error fetching positions for {exchange_name}: {e}")

    logger.info(f"📊 Final positions data: {positions_data}")
    return positions_data


def get_pending_orders():
    """Fetches and returns pending (open) orders for each exchange."""
    logger.info("📋 Fetching pending orders...")
    pending_orders = {}

    if not exchanges:
        logger.error("❌ No exchanges loaded! Check API keys and config.")
        return pending_orders

    for exchange_name, exchange in exchanges.items():
        pending_orders[exchange_name] = []
        try:
            orders = exchange.fetch_open_orders()
            pending_orders[exchange_name] = orders
            logger.info(f"✅ [get_pending_orders] Successfully fetched {len(orders)} orders for {exchange_name}")
        except Exception as e:
            logger.error(f"❌ [get_pending_orders] Error fetching orders for {exchange_name}: {e}")
            pending_orders[exchange_name] = []

    return pending_orders


def execute_order(exchange_name, symbol, side, order_type, quantity, price=None):
    """Places an order on the specified exchange."""
    logger.info(f"📌 Executing order on {exchange_name}: {side} {quantity} {symbol} ({order_type}) at {price if price else 'market price'}")

    if exchange_name not in exchanges:
        logger.error(f"❌ Exchange {exchange_name} not available.")
        return {"status": "error", "message": f"Exchange {exchange_name} not found."}

    exchange = exchanges[exchange_name]

    try:
        if order_type == "market":
            order = exchange.create_market_order(symbol, side, quantity)
        elif order_type == "limit" and price:
            order = exchange.create_limit_order(symbol, side, quantity, price)
        else:
            logger.error(f"❌ Invalid order type: {order_type}")
            return {"status": "error", "message": "Invalid order type"}

        logger.info(f"✅ Order placed successfully: {order}")
        return {"status": "success", "order": order}

    except Exception as e:
        logger.error(f"❌ Error executing order on {exchange_name}: {e}")
        return {"status": "error", "message": str(e)}


def close_position(exchange_name, symbol):
    """Closes an open position."""
    logger.info(f"❌ Closing position for {symbol} on {exchange_name}...")

    if exchange_name not in exchanges:
        logger.error(f"❌ Exchange {exchange_name} not available.")
        return {"status": "error", "message": f"Exchange {exchange_name} not found."}

    exchange = exchanges[exchange_name]

    try:
        positions = get_positions().get(exchange_name, [])
        for pos in positions:
            if pos["symbol"] == symbol:
                side = "sell" if (pos["side"] == "buy" or pos["side"] == "long") else "buy"
                order = exchange.create_market_order(symbol, side, pos["contracts"])
                logger.info(f"✅ Position closed: {order}")
                return {"status": "success", "order": order}

        logger.warning(f"⚠ No open position found for {symbol}.")
        return {"status": "error", "message": "No open position found."}

    except Exception as e:
        logger.error(f"❌ Error closing position: {e}")
        return {"status": "error", "message": str(e)}


def close_all_positions():
    """Closes all open positions on all exchanges."""
    logger.info("❌ Closing all open positions...")

    results = {}
    for exchange_name, exchange in exchanges.items():
        positions = get_positions().get(exchange_name, [])
        for pos in positions:
            result = close_position(exchange_name, pos["symbol"])
            results[pos["symbol"]] = result

    logger.info(f"✅ All positions closed: {results}")
    return results


def cancel_order(exchange_name, order_id, symbol):
    """Cancels a specific order."""
    logger.info(f"🚫 Cancelling order {order_id} on {exchange_name}...")

    if exchange_name not in exchanges:
        logger.error(f"❌ Exchange {exchange_name} not available.")
        return {"status": "error", "message": f"Exchange {exchange_name} not found."}

    exchange = exchanges[exchange_name]

    try:
        result = exchange.cancel_order(order_id, symbol)
        logger.info(f"✅ Order {order_id} cancelled successfully.")
        return {"status": "success", "order": result}
    except Exception as e:
        logger.error(f"❌ Error cancelling order {order_id}: {e}")
        return {"status": "error", "message": str(e)}


def calculate_summary_stats():
    """Calculates and returns summary statistics for the dashboard."""
    logger.info("📊 Calculating summary statistics...")
    summary_stats = {
        "portfolio_value": 0.0,
        "total_pnl": 0.0,
        "margin_used": 0.0,
    }

    if not exchanges:
        logger.error("❌ No exchanges loaded! Cannot calculate summary stats.")
        return summary_stats

    for exchange_name, exchange in exchanges.items():
        try:
            # For futures accounts, fetch balance differently if needed
            account_balance = exchange.fetch_balance()

            # Log the balance breakdown for debugging
            logger.info(f"🔍 [calculate_summary_stats] Balance breakdown for {exchange_name}: {account_balance.get('total', {})}")

            positions = get_positions().get(exchange_name, [])

            # Calculate portfolio value - check for USDT, USDC, BUSD, or other stablecoins
            total_balance = 0.0
            for currency, balance_info in account_balance.get('total', {}).items():
                if currency in ['USDT', 'USDC', 'BUSD', 'TUSD']:  # Common stablecoins
                    total_balance += balance_info or 0.0
                    logger.info(f"💰 [calculate_summary_stats] Found {balance_info} {currency} in {exchange_name}")
            summary_stats["portfolio_value"] += total_balance

            # Calculate total PNL and margin used from positions
            for pos in positions:
                summary_stats["total_pnl"] += pos.get('unrealized_pnl', 0.0)
                summary_stats["margin_used"] += pos.get('notional', 0.0) * pos.get('margin_ratio', 0.0) if pos.get('margin_ratio') else 0.0

        except Exception as e:
            logger.error(f"❌ Error fetching account balance or positions for {exchange_name}: {e}")

    logger.info(f"📊 Summary statistics calculated: {summary_stats}")
    return summary_stats
