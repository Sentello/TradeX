import os
import threading
import logging
import signal
import sys
import subprocess
from dotenv import load_dotenv
from email_reader import run_email_reader

# Load environment variables
load_dotenv()

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
    proc = subprocess.Popen(["gunicorn", "-w", "2", "-b", f"0.0.0.0:{port}", f"{service_name}:app"])
    processes.append(proc)

def start_email_reader():
    """Start the email reader in a background thread."""
    logging.info("Starting Email Reader...")
    email_thread = threading.Thread(target=run_email_reader, daemon=True)
    email_thread.start()
    return email_thread

if __name__ == "__main__":
    mode = os.getenv("MODE", "both").strip().lower()

    if mode not in ["webhook", "email", "both"]:
        logging.error(f"Invalid MODE in .env: {mode}. Expected 'webhook', 'email', or 'both'.")
        sys.exit(1)

    # Start Gunicorn services
    if mode in ["webhook", "both"]:
        start_gunicorn("webhook_receiver", 5005)

    if mode in ["email", "both"]:
        email_thread = start_email_reader()

    # Always start the dashboard
    start_gunicorn("dashboard_app", 5000)

    # Wait for Gunicorn processes to finish
    for proc in processes:
        proc.wait()
