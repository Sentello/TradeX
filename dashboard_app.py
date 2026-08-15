import log_setup

# Configure logging before importing modules that create loggers.
log_setup.configure("dashboard")

import hmac  # noqa: E402
import os  # noqa: E402
import secrets  # noqa: E402
from collections import deque  # noqa: E402
from functools import wraps  # noqa: E402

import bcrypt  # noqa: E402
from flask import (  # noqa: E402
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import config  # noqa: E402
from bot_logic import (  # noqa: E402
    calculate_summary_stats,
    cancel_order,
    close_all_positions,
    close_position,
    get_pending_orders,
    get_positions,
)
from ratelimit import FailureThrottle  # noqa: E402

logger = log_setup.get_logger("dashboard")
log_directory = log_setup.log_directory()

logger.info("🎉 Dashboard initialized!")

# Lines returned per log file. The whole file used to be read into memory
# on every poll.
LOG_TAIL_LINES = 500

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
app.config.update(
    PERMANENT_SESSION_LIFETIME=config.SESSION_PERMANENT_LIFETIME,
    SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
)

# Failed logins per client address. Single gunicorn worker, so this is shared
# across all requests in the process.
_login_throttle = FailureThrottle(
    config.LOGIN_MAX_ATTEMPTS, config.LOGIN_LOCKOUT_SECONDS
)


def _client_id():
    if config.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _password_matches(password):
    """False rather than an exception for any malformed input."""
    if not password:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), config.DASHBOARD_PASSWORD.encode("utf-8")
        )
    except (ValueError, TypeError) as e:
        logger.error(f"DASHBOARD_PASSWORD is not a usable bcrypt hash: {e}")
        return False


def _csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


# Authentication Decorator
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session.permanent = True
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def csrf_protect(func):
    """Reject state-changing requests that don't carry the session token."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        submitted = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not hmac.compare_digest(submitted, expected):
            logger.warning(f"Rejected request with bad CSRF token from {_client_id()}")
            return jsonify({"status": "error", "message": "Invalid CSRF token"}), 400
        return func(*args, **kwargs)
    return wrapper


# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        client = _client_id()
        locked = _login_throttle.blocked_for(client)
        if locked:
            logger.warning(f"Login attempt from locked-out client {client}.")
            return render_template(
                "login.html",
                error=f"Too many failed attempts. Try again in {int(locked / 60) + 1} minute(s).",
                error_kind="warning",
            ), 429

        if _password_matches(request.form.get("password")):
            _login_throttle.reset(client)
            # New session identifier on privilege change.
            session.clear()
            session["logged_in"] = True
            session.permanent = True
            _csrf_token()
            logger.info(f"User logged in successfully from {client}.")
            return redirect(url_for("index"))

        locked = _login_throttle.record_failure(client)
        logger.warning(
            f"Invalid login attempt from {client}."
            + (f" Locked out for {locked:.0f}s." if locked else "")
        )
        return render_template("login.html", error="Invalid password", error_kind="danger"), 401
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
        return render_template(
            "dashboard.html",
            positions=positions,
            pending_orders=pending_orders,
            csrf_token=_csrf_token(),
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template("dashboard.html", error=str(e), csrf_token=_csrf_token())


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


# Fetch Summary Stats (API)
@app.route("/summary_stats", methods=["GET"])
@login_required
def summary_stats():
    try:
        stats = calculate_summary_stats()
        logger.info(f"Fetched summary stats: {stats}")
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error fetching summary stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def _flash_failed(result, fallback):
    """Surface a bot_logic error dict; a missing message still gets fallback."""
    if isinstance(result, dict) and result.get("status") == "success":
        return False
    message = fallback
    if isinstance(result, dict) and result.get("message"):
        message = result["message"]
    flash(message, "danger")
    return True


# Close a Specific Position
@app.route("/close_position", methods=["POST"])
@login_required
@csrf_protect
def close_position_route():
    try:
        exchange_name = request.form["EXCHANGE"]
        symbol = request.form["SYMBOL"]
        result = close_position(exchange_name, symbol)
        if _flash_failed(result, f"Failed to close {symbol}."):
            logger.warning(f"Close {symbol} on {exchange_name} did not succeed: {result}")
        else:
            logger.info(f"Closed position for {symbol} on {exchange_name}: {result}")
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        flash(str(e), "danger")
    return redirect(url_for("index"))


# Close All Positions
@app.route("/close_all_positions", methods=["POST"])
@login_required
@csrf_protect
def close_all_positions_route():
    try:
        results = close_all_positions()
        failures = []
        for symbol, result in (results or {}).items():
            if isinstance(result, dict) and result.get("status") == "success":
                continue
            detail = result.get("message") if isinstance(result, dict) else "failed"
            failures.append(f"{symbol}: {detail}")
        if failures:
            flash("Could not close: " + "; ".join(failures), "danger")
            logger.warning(f"Close-all had failures: {failures}")
        else:
            logger.info(f"Closed all positions: {results}")
    except Exception as e:
        logger.error(f"Error closing all positions: {e}")
        flash(str(e), "danger")
    return redirect(url_for("index"))


# Cancel Order
@app.route("/cancel_order", methods=["POST"])
@login_required
@csrf_protect
def cancel_order_route():
    try:
        exchange_name = request.form["EXCHANGE"]
        order_id = request.form["ORDER_ID"]
        symbol = request.form["SYMBOL"]
        result = cancel_order(exchange_name, order_id, symbol)
        if _flash_failed(result, f"Failed to cancel order {order_id}."):
            logger.warning(f"Cancel {order_id} on {exchange_name} did not succeed: {result}")
        else:
            logger.info(f"Canceled order {order_id} on {exchange_name}")
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        flash(str(e), "danger")
    return redirect(url_for("index"))


def _tail(path, lines):
    """Last `lines` lines of a file, without loading the whole thing."""
    with open(path, "r", errors="replace") as f:
        return list(deque(f, maxlen=lines))


# Fetch Logs (API)
@app.route("/logs", methods=["GET"])
@login_required
def logs():
    try:
        log_files = [f for f in os.listdir(log_directory) if f.endswith(".log")]
        all_logs = {}
        for log_file in sorted(log_files):
            try:
                all_logs[log_file] = _tail(
                    os.path.join(log_directory, log_file), LOG_TAIL_LINES
                )
            except Exception as e:
                all_logs[log_file] = [f"Error reading log file: {e}"]
        return jsonify({"status": "success", "logs": all_logs})
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Run Flask if executed directly (python dashboard_app.py)
if __name__ == "__main__":
    app.run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)
