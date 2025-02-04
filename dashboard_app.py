import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import timedelta
import os

import config
from bot_logic import (
    execute_order,
    get_positions,
    get_pending_orders,
    close_position,
    close_all_positions,
    cancel_order
)

# Setup logging
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"  # Inside Docker
else:
    log_directory = "logs"  # Local execution
os.makedirs(log_directory, exist_ok=True)

# Set up RotatingFileHandler
log_file_path = os.path.join(log_directory, "dashboard.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("dashboard")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
# add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Dashboard initialized!")


# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
app.config.update(
    PERMANENT_SESSION_LIFETIME=config.SESSION_PERMANENT_LIFETIME,
    SESSION_COOKIE_SECURE=False,  # Set to True if using HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict"
)

# Authentication Decorator
def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        session.permanent = True
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == config.DASHBOARD_PASSWORD:
            session["logged_in"] = True
            session["user_authenticated"] = True
            session.permanent = True
            logger.info("User logged in successfully.")
            return redirect(url_for("index"))
        else:
            logger.warning("Invalid login attempt.")
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    logger.info("User logged out.")
    return redirect(url_for("login"))

# Dashboard Home
@app.route("/")
@login_required
def index():
    """Main dashboard page showing open positions and pending orders."""
    try:
        positions = get_positions()
        pending_orders = get_pending_orders()
        return render_template("dashboard.html", positions=positions, pending_orders=pending_orders)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template("dashboard.html", error=str(e))

# Fetch Positions (API)
@app.route("/positions", methods=["GET"])
@login_required
def positions():
    try:
        positions = get_positions()
        logger.info(f"Fetched positions: {positions}")
        return jsonify(positions)
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Fetch Pending Orders (API)
@app.route("/pending_orders", methods=["GET"])
@login_required
def pending_orders():
    try:
        orders = get_pending_orders()
        logger.info("Fetched pending orders.")
        return jsonify(orders)
    except Exception as e:
        logger.error(f"Error fetching pending orders: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Close a Specific Position
@app.route("/close_position", methods=["POST"])
@login_required
def close_position_route():
    try:
        data = request.form
        exchange_name = data['EXCHANGE']
        symbol = data['SYMBOL']
        result = close_position(exchange_name, symbol)
        logger.info(f"Closed position for {symbol} on {exchange_name}: {result}")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return redirect(url_for("index"))

# Close All Positions
@app.route("/close_all_positions", methods=["POST"])
@login_required
def close_all_positions_route():
    try:
        result = close_all_positions()
        logger.info("Closed all positions.")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        return redirect(url_for("index"))

# Cancel Order
@app.route("/cancel_order", methods=["POST"])
@login_required
def cancel_order_route():
    try:
        data = request.form
        exchange_name = data["EXCHANGE"]
        order_id = data["ORDER_ID"]
        symbol = data["SYMBOL"]
        result = cancel_order(exchange_name, order_id, symbol)
        logger.info(f"Canceled order {order_id} on {exchange_name}")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        return redirect(url_for("index"))

# Run Flask if executed directly
if __name__ == "__main__":
    app.run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)
