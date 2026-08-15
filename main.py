"""Local (non-Docker) entry point. The container uses supervisord instead."""

import logging
import signal
import subprocess
import sys
import threading

import config
import serve
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


def start_gunicorn(service):
    """Start Gunicorn for a given service (dashboard or webhook)."""
    command = serve.build_command(service)
    logging.info(f"Starting {service}: {' '.join(command)}")
    processes.append(subprocess.Popen(command, env=serve.environment(service)))


def start_email_reader():
    """Start the email reader in a background thread."""
    logging.info("Starting Email Reader...")
    email_thread = threading.Thread(target=run_email_reader, daemon=True)
    email_thread.start()
    return email_thread


if __name__ == "__main__":
    # MODE is validated in config, so no second check is needed here.
    if config.WEBHOOK_ENABLED:
        start_gunicorn("webhook")

    if config.EMAIL_ENABLED:
        start_email_reader()

    # Always start the dashboard
    start_gunicorn("dashboard")

    # Wait for Gunicorn processes to finish
    for proc in processes:
        proc.wait()
