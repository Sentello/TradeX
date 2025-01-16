from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import logging, secrets
from logging.handlers import RotatingFileHandler
from bot_logic import execute_order, get_positions, get_pending_orders, close_position, close_all_positions, cancel_order
from config import WEBHOOK_PIN
from config import DASHBOARD_PASSWORD
from datetime import timedelta
import os


# Web Dashboard
dashboard_app = Flask(__name__)
# dashboard_app.secret_key = secrets.token_hex(32)
dashboard_app.secret_key = os.getenv("FLASK_SECRET_KEY", "hardcoded-default-key")
dashboard_app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    SESSION_COOKIE_SECURE=False, # Set True if using HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict'
)

# Webhooks
webhook_app = Flask(__name__)

# Configure logging
file_handler = RotatingFileHandler('logs/bot.log', maxBytes=2000000, backupCount=5)
console_handler = logging.StreamHandler()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)

# Middleware to require login for certain routes
def login_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_view(*args, **kwargs):
        # Make the session permanent
        session.permanent = True
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return decorated_view

@dashboard_app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == DASHBOARD_PASSWORD:
            # Set session variables and make it permanent
            session["logged_in"] = True
            session["user_authenticated"] = True  # Example flag for security
            session.permanent = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")

@dashboard_app.route("/logout")
def logout():
    session.clear()  # Clear all session data instead of just "logged_in"
    return redirect(url_for("login"))

@dashboard_app.route('/')
@login_required
def index():
    positions = get_positions()
    pending_orders = get_pending_orders()
    return render_template('dashboard.html', positions=positions, pending_orders=pending_orders)

@webhook_app.route('/webhook', methods=['POST'])
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

@dashboard_app.route('/positions', methods=['GET'])
@login_required
def positions():
    try:
        positions = get_positions()
        logging.info(f"Fetched positions: {positions}")
        return jsonify(positions)
    except Exception as e:
        logging.error(f"Error fetching positions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@dashboard_app.route('/pending_orders', methods=['GET'])
@login_required
def pending_orders():
    try:
        orders = get_pending_orders()
        return jsonify(orders)
    except Exception as e:
        logging.error(f"Error fetching pending orders: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@dashboard_app.route('/close_position', methods=['POST'])
@login_required
def close_position_route():
    try:
        data = request.form
        result = close_position(data['EXCHANGE'], data['SYMBOL'])
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message=f"Closed position for {data['SYMBOL']}")
    except Exception as e:
        logging.error(f"Error closing position: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

@dashboard_app.route('/close_all_positions', methods=['POST'])
@login_required
def close_all_positions_route():
    try:
        result = close_all_positions()
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), message="Closed all positions successfully.")
    except Exception as e:
        logging.error(f"Error closing all positions: {e}")
        return render_template('dashboard.html', positions=get_positions(), pending_orders=get_pending_orders(), error=str(e))

@dashboard_app.route('/cancel_order', methods=['POST'])
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
    # Run both apps on different ports
    import threading

    threading.Thread(target=lambda: dashboard_app.run(host='0.0.0.0', port=5000)).start()
    threading.Thread(target=lambda: webhook_app.run(host='0.0.0.0', port=5005)).start()
