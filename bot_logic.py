import ccxt
import logging
from config import BYBIT_API_KEY, BYBIT_API_SECRET, BINANCE_API_KEY, BINANCE_API_SECRET

# Initialize CCXT exchanges dynamically
exchanges = {}

if BYBIT_API_KEY and BYBIT_API_SECRET:
    exchanges["bybit"] = ccxt.bybit({
        'apiKey': BYBIT_API_KEY,
        'secret': BYBIT_API_SECRET,
        'enableRateLimit': True,
    })

if BINANCE_API_KEY and BINANCE_API_SECRET:
    exchanges["binance"] = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_API_SECRET,
        'enableRateLimit': True,
    })

def initialize_bot():
    """Initialize the bot by loading markets for all configured exchanges."""
    for exchange_name, exchange in exchanges.items():
        try:
            exchange.load_markets()
            logging.info(f"Markets loaded for {exchange_name}")
        except Exception as e:
            logging.error(f"Failed to load markets for {exchange_name}: {e}")

def execute_order(data):
    try:
        exchange_name = data['EXCHANGE'].lower()
        if exchange_name not in exchanges:
            raise ValueError(f"Exchange {exchange_name} is not supported.")

        exchange = exchanges[exchange_name]
        symbol = data['SYMBOL']
        side = data['SIDE'].lower()
        order_type = data['ORDER_TYPE'].lower()
        quantity = float(data['QUANTITY'])
        price = float(data.get('PRICE', 0))
        stop_loss = float(data.get('STOP_LOSS', 0))
        take_profit = float(data.get('TAKE_PROFIT', 0))

        logging.info(f"Placing order on {exchange_name}: {data}")

        # Place main order
        response = exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=quantity,
            price=price if order_type == 'limit' else None
        )
        logging.info(f"{exchange_name.capitalize()} main order response: {response}")

        if exchange_name == "bybit":
            # TP and SL logic for Bybit
            handle_bybit_tp_sl(exchange, symbol, side, quantity, price, take_profit, stop_loss)

        elif exchange_name == "binance":
            # TP and SL logic for Binance
            handle_binance_tp_sl(exchange, symbol, side, quantity, take_profit, stop_loss)

        return {"status": "success", "data": response}

    except Exception as e:
        logging.error(f"Failed to place order: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

def handle_bybit_tp_sl(exchange, symbol, side, quantity, base_price, take_profit, stop_loss):
    try:
        if take_profit > 0:
            tp_response = exchange.private_post_v5_order_create({
                "symbol": symbol,
                "side": "Sell" if side == "buy" else "Buy",
                "orderType": "TakeProfit",
                "qty": quantity,
                "basePrice": base_price,
                "stopPx": take_profit,
                "triggerBy": "LastPrice",
                "reduce_only": True,
                "category": "linear"
            })
            logging.info(f"Bybit Take Profit Response: {tp_response}")
        if stop_loss > 0:
            sl_response = exchange.private_post_v5_order_create({
                "symbol": symbol,
                "side": "Sell" if side == "buy" else "Buy",
                "orderType": "StopLoss",
                "qty": quantity,
                "basePrice": base_price,
                "stopPx": stop_loss,
                "triggerBy": "LastPrice",
                "reduce_only": True,
                "category": "linear"
            })
            logging.info(f"Bybit Stop Loss Response: {sl_response}")
    except Exception as e:
        logging.error(f"Error in Bybit TP/SL creation: {str(e)}")

def handle_binance_tp_sl(exchange, symbol, side, quantity, take_profit, stop_loss):
    try:
        if take_profit > 0 or stop_loss > 0:
            oco_params = {
                "symbol": symbol.replace('/', ''),
                "side": "sell" if side == "buy" else "buy",
                "quantity": quantity,
                "price": take_profit,
                "stopPrice": stop_loss,
                "stopLimitPrice": stop_loss,
                "stopLimitTimeInForce": "GTC",
            }
            oco_response = exchange.sapi_post_order_oco(**oco_params)
            logging.info(f"Binance OCO Order Response: {oco_response}")
    except Exception as e:
        logging.error(f"Error in Binance OCO creation: {str(e)}")

def get_positions():
    positions_data = {}
    for exchange_name, exchange in exchanges.items():
        positions_data[exchange_name] = []
        try:
            # Fetch positions from the exchange
            positions = exchange.fetch_positions()

            # Process the positions
            for position in positions:
                if position.get('contracts') and position['contracts'] > 0:
                    positions_data[exchange_name].append({
                        "symbol": position.get('symbol', 'N/A'),
                        "contracts": position.get('contracts', 'N/A'),
                        "value": position.get('notional', 'N/A'),
                        "entry_price": position.get('entryPrice', 'N/A'),
                        "liquidation_price": position.get('liquidationPrice', 'N/A') or "N/A",
                        "position_margin": position.get('initialMargin', 'N/A'),
                        "unrealized_pnl": position.get('unrealizedPnl', 'N/A'),
                        "exchange": exchange_name,
                    })
        except Exception as e:
            logging.error(f"Error fetching positions for {exchange_name}: {e}")
    return positions_data

def get_pending_orders():
    pending_orders = {}
    for exchange_name, exchange in exchanges.items():
        try:
            orders = exchange.fetch_open_orders()
            pending_orders[exchange_name] = [
                {
                    "id": order['id'],
                    "symbol": order['symbol'],
                    "type": order['type'],
                    "side": order['side'],
                    "price": order['price'],
                    "quantity": order['amount']
                }
                for order in orders
            ]
        except Exception as e:
            logging.error(f"Error fetching pending orders from {exchange_name}: {e}")
            pending_orders[exchange_name] = []
    return pending_orders

def close_position(exchange_name, symbol):
    if exchange_name not in exchanges:
        return {"status": "error", "message": f"Exchange {exchange_name} is not supported."}

    exchange = exchanges[exchange_name]
    try:
        positions = exchange.fetch_positions()
        position_to_close = next((pos for pos in positions if pos['symbol'] == symbol), None)

        if not position_to_close or position_to_close['contracts'] == 0:
            return {"status": "error", "message": f"No open position found for {symbol} on {exchange_name}."}

        side = "sell" if position_to_close['side'] == "long" else "buy"
        amount = abs(position_to_close['contracts'])

        response = exchange.create_order(
            symbol=symbol,
            type="market",
            side=side,
            amount=amount
        )
        return {"status": "success", "response": response}
    except Exception as e:
        logging.error(f"Error closing position on {exchange_name}: {e}")
        return {"status": "error", "message": str(e)}

def close_all_positions():
    results = {}
    for exchange_name, exchange in exchanges.items():
        try:
            positions = exchange.fetch_positions()
            for position in positions:
                if position['contracts'] > 0:
                    symbol = position['symbol']
                    side = "sell" if position['side'] == "long" else "buy"
                    amount = abs(position['contracts'])

                    response = exchange.create_order(
                        symbol=symbol,
                        type="market",
                        side=side,
                        amount=amount
                    )
                    results[symbol] = {"status": "success", "response": response}
        except Exception as e:
            logging.error(f"Error closing all positions for {exchange_name}: {e}")
            results[exchange_name] = {"status": "error", "message": str(e)}

    return results

def cancel_order(exchange_name, order_id, symbol):
    if exchange_name not in exchanges:
        return {"status": "error", "message": f"Exchange {exchange_name} is not supported."}

    exchange = exchanges[exchange_name]
    try:
        response = exchange.cancel_order(order_id, symbol)
        return {"status": "success", "response": response}
    except Exception as e:
        logging.error(f"Error canceling order on {exchange_name}: {e}")
        return {"status": "error", "message": str(e)}
