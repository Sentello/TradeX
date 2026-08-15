"""Local (non-Docker) entry point. The container uses supervisord instead."""

import logging
import os
import signal
import subprocess
import sys
import threading

import config
from email_reader import run_email_reader

logging.basicConfig(level=logging.INFO)

# Store subprocesses (Gunicorn processes)
processes = []


def handle_exit_signal(signum, frame):
    """Graceful shutdown for all services."""
    logging.info("Shutting down all services...")
    for proc in processes:
        logging.info(f"Terminating process {proc.pid}...")
        proc.terminate()
    sys.exit(0)


# Attach signal handlers for Ctrl+C
signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)


def start_gunicorn(service_name, port):
    """Start Gunicorn for a given service (dashboard or webhook)."""
    logging.info(f"Starting {service_name} on port {port}...")
    env = dict(os.environ, TRADEX_SERVICE=service_name)
    # One worker: the login lockout counter is in-process, and a second worker
    # would duplicate the ccxt clients and race on the log files.
    proc = subprocess.Popen(
        ["gunicorn", "-w", "1", "-b", f"0.0.0.0:{port}", f"{service_name}:app"],
        env=env,
    )
    processes.append(proc)


def start_email_reader():
    """Start the email reader in a background thread."""
    logging.info("Starting Email Reader...")
    email_thread = threading.Thread(target=run_email_reader, daemon=True)
    email_thread.start()
    return email_thread


if __name__ == "__main__":
    # MODE is validated in config, so no second check is needed here.
    if config.WEBHOOK_ENABLED:
        start_gunicorn("webhook_receiver", config.WEBHOOK_PORT)

    if config.EMAIL_ENABLED:
        start_email_reader()

    # Always start the dashboard
    start_gunicorn("dashboard_app", config.DASHBOARD_PORT)

    # Wait for Gunicorn processes to finish
    for proc in processes:
        proc.wait()
