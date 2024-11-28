from flask import Flask, request, jsonify, render_template
import logging
from bot_logic import execute_order, get_positions, get_pending_orders, close_position, close_all_positions, cancel_order
from config import WEBHOOK_PIN

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename='logs/bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/')
def index():
    positions = get_positions()
    pending_orders = get_pending_orders()
    return render_template('dashboard.html', positions=positions, pending_orders=pending_orders)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json

        # Validate PIN
        provided_pin = data.get("PIN")
        if provided_pin != WEBHOOK_PIN:
            logging.warning(f"Invalid PIN received: {provided_pin}")
            return jsonify({"status": "error", "message": "Invalid PIN"}), 403

        logging.info(f"Webhook received: {data}")
        result = execute_order(data)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/positions', methods=['GET'])
def positions():
    try:
        positions = get_positions()
        logging.info(f"Fetched positions: {positions}")
        return jsonify(positions)
    except Exception as e:
        logging.error(f"Error fetching positions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pending_orders', methods=['GET'])
def pending_orders():
    try:
        orders = get_pending_orders()
        return jsonify(orders)
    except Exception as e:
        logging.error(f"Error fetching pending orders: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/close_position', methods=['POST'])
def close_position_route():
    try:
        data = request.form
        result = close_position(data['EXCHANGE'], data['SYMBOL'])
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message=f"Closed position for {data['SYMBOL']}")
    except Exception as e:
        logging.error(f"Error closing position: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

@app.route('/close_all_positions', methods=['POST'])
def close_all_positions_route():
    try:
        result = close_all_positions()
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message="Closed all positions successfully.")
    except Exception as e:
        logging.error(f"Error closing all positions: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

@app.route('/cancel_order', methods=['POST'])
def cancel_order_route():
    try:
        data = request.form
        result = cancel_order(data['EXCHANGE'], data['ORDER_ID'], data['SYMBOL'])
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message=f"Canceled order {data['ORDER_ID']}")
    except Exception as e:
        logging.error(f"Error canceling order: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
