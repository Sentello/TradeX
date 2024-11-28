from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import logging
from bot_logic import execute_order, get_positions, get_pending_orders, close_position, close_all_positions, cancel_order
from config import WEBHOOK_PIN
from config import DASHBOARD_PASSWORD

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Replace with a secure random key

# Configure logging
logging.basicConfig(
    filename='logs/bot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Middleware to require login for certain routes
def login_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return decorated_view

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route('/')
@login_required
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
@login_required
def positions():
    try:
        positions = get_positions()
        logging.info(f"Fetched positions: {positions}")
        return jsonify(positions)
    except Exception as e:
        logging.error(f"Error fetching positions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/pending_orders', methods=['GET'])
@login_required
def pending_orders():
    try:
        orders = get_pending_orders()
        return jsonify(orders)
    except Exception as e:
        logging.error(f"Error fetching pending orders: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/close_position', methods=['POST'])
@login_required
def close_position_route():
    try:
        data = request.form
        result = close_position(data['EXCHANGE'], data['SYMBOL'])
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message=f"Closed position for {data['SYMBOL']}")
    except Exception as e:
        logging.error(f"Error closing position: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

@app.route('/close_all_positions', methods=['POST'])
@login_required
def close_all_positions_route():
    try:
        result = close_all_positions()
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message="Closed all positions successfully.")
    except Exception as e:
        logging.error(f"Error closing all positions: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

@app.route('/cancel_order', methods=['POST'])
@login_required
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
