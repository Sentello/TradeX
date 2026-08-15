"""Read and act on exchange state for the dashboard."""

import exchanges as exchange_registry
from log_setup import get_logger

logger = get_logger("bot_logic")

exchanges = exchange_registry.exchanges


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
                        "initial_margin": pos.get('initialMargin', None),
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

    exchange = exchange_registry.get(exchange_name)
    if exchange is None:
        logger.error(f"❌ Exchange {exchange_name} not available.")
        return {"status": "error", "message": f"Exchange {exchange_name} not found."}

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


def _close_from_snapshot(exchange, exchange_name, pos):
    """Send the reducing order for an already-fetched position."""
    side = "sell" if (pos["side"] == "buy" or pos["side"] == "long") else "buy"
    # reduceOnly matters: if the position closed between the fetch and this
    # call (stop-loss, partial fill, a concurrent close), a plain market order
    # would open a brand new position in the opposite direction.
    order = exchange.create_order(
        pos["symbol"], "market", side, pos["contracts"], None, {"reduceOnly": True}
    )
    logger.info(f"✅ Position closed on {exchange_name}: {order}")
    return {"status": "success", "order": order}


def close_position(exchange_name, symbol, positions=None):
    """Closes an open position. Pass `positions` to reuse an existing snapshot."""
    logger.info(f"❌ Closing position for {symbol} on {exchange_name}...")

    exchange = exchange_registry.get(exchange_name)
    if exchange is None:
        logger.error(f"❌ Exchange {exchange_name} not available.")
        return {"status": "error", "message": f"Exchange {exchange_name} not found."}

    try:
        if positions is None:
            positions = get_positions().get(exchange_name, [])

        for pos in positions:
            if pos["symbol"] == symbol:
                return _close_from_snapshot(exchange, exchange_name, pos)

        logger.warning(f"⚠ No open position found for {symbol}.")
        return {"status": "error", "message": "No open position found."}

    except Exception as e:
        logger.error(f"❌ Error closing position: {e}")
        return {"status": "error", "message": str(e)}


def close_all_positions():
    """Closes all open positions on all exchanges."""
    logger.info("❌ Closing all open positions...")

    results = {}
    # One snapshot for everything: this used to re-fetch every position for
    # every position, which trips exchange rate limits.
    all_positions = get_positions()

    for exchange_name, positions in all_positions.items():
        exchange = exchange_registry.get(exchange_name)
        if exchange is None:
            continue
        for pos in positions:
            try:
                results[pos["symbol"]] = _close_from_snapshot(exchange, exchange_name, pos)
            except Exception as e:
                logger.error(f"❌ Error closing {pos['symbol']} on {exchange_name}: {e}")
                results[pos["symbol"]] = {"status": "error", "message": str(e)}

    logger.info(f"✅ All positions closed: {results}")
    return results


def cancel_order(exchange_name, order_id, symbol):
    """Cancels a specific order."""
    logger.info(f"🚫 Cancelling order {order_id} on {exchange_name}...")

    exchange = exchange_registry.get(exchange_name)
    if exchange is None:
        logger.error(f"❌ Exchange {exchange_name} not available.")
        return {"status": "error", "message": f"Exchange {exchange_name} not found."}

    try:
        result = exchange.cancel_order(order_id, symbol)
        logger.info(f"✅ Order {order_id} cancelled successfully.")
        return {"status": "success", "order": result}
    except Exception as e:
        logger.error(f"❌ Error cancelling order {order_id}: {e}")
        return {"status": "error", "message": str(e)}


def _position_margin(pos):
    """Margin committed to a position, preferring the exchange's own figure."""
    initial_margin = pos.get("initial_margin")
    if initial_margin:
        return float(initial_margin)

    # Fall back to notional / leverage. The old code multiplied notional by
    # marginRatio, which is the *maintenance* margin ratio, not margin used.
    notional = pos.get("notional") or 0.0
    leverage = pos.get("leverage") or 0.0
    if notional and leverage:
        return float(notional) / float(leverage)
    return 0.0


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

    # Fetched once, not once per exchange.
    all_positions = get_positions()

    for exchange_name, exchange in exchanges.items():
        try:
            account_balance = exchange.fetch_balance()
            logger.info(f"🔍 [calculate_summary_stats] Balance breakdown for {exchange_name}: {account_balance.get('total', {})}")

            # Calculate portfolio value - check for USDT, USDC, BUSD, or other stablecoins
            total_balance = 0.0
            for currency, balance_info in account_balance.get('total', {}).items():
                if currency in ['USDT', 'USDC', 'BUSD', 'TUSD']:  # Common stablecoins
                    total_balance += balance_info or 0.0
                    logger.info(f"💰 [calculate_summary_stats] Found {balance_info} {currency} in {exchange_name}")
            summary_stats["portfolio_value"] += total_balance

            for pos in all_positions.get(exchange_name, []):
                summary_stats["total_pnl"] += pos.get('unrealized_pnl') or 0.0
                summary_stats["margin_used"] += _position_margin(pos)

        except Exception as e:
            logger.error(f"❌ Error fetching account balance for {exchange_name}: {e}")

    logger.info(f"📊 Summary statistics calculated: {summary_stats}")
    return summary_stats
