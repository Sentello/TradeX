"""Duplicate signal suppression, shared across processes.

Protects against the same order being placed twice. Two cases matter:

- A lost response. If the connection drops after the exchange accepted the
  order but before the sender saw the reply, the sender cannot tell that
  from a genuine failure, and a retry would double the position.
- MODE=both. The webhook and the email reader run as separate processes,
  and a TradingView alert configured to send both a webhook and an email
  arrives twice, once down each path.

The second case is why the store is SQLite on disk rather than a dict: an
in-process cache cannot see what another process has already executed.
SQLite is in the standard library, is safe for concurrent writers, and
needs no service to run alongside.

This is at-most-once within a time window, not true anti-replay. A sender
that cannot sign its requests (TradingView cannot) offers nothing to verify
freshness against, so an attacker who captures a request can still replay it
after the window expires. WEBHOOK_ALLOWED_IPS and a high-entropy
WEBHOOK_PIN are the controls for that.
"""

import hashlib
import json
import os
import sqlite3
import threading
import time

import log_setup

logger = log_setup.get_logger("dedup")

# Fields excluded from the fingerprint: secrets, and the caller's own
# idempotency key which is handled separately.
_EXCLUDED = {"pin", "id"}

DB_FILENAME = "dedup.sqlite3"


def default_db_path():
    """Shared state lives beside the logs, which every service can write.

    The dashboard's /logs endpoint only serves *.log, so this file is not
    exposed by it.
    """
    return os.path.join(log_setup.log_directory(), DB_FILENAME)


def signal_key(payload):
    """Stable identity for a signal.

    Prefers an explicit ID supplied by the sender, which is the only way to
    distinguish a retry from a genuine second identical order. Falls back to
    a fingerprint of the payload.
    """
    for field in ("ID", "id", "Id"):
        value = payload.get(field)
        if value not in (None, ""):
            return f"id:{value}"

    material = {
        str(k): payload[k]
        for k in payload
        if str(k).lower() not in _EXCLUDED
    }
    encoded = json.dumps(material, sort_keys=True, default=str).encode()
    return "fingerprint:" + hashlib.sha256(encoded).hexdigest()


class DuplicateFilter:
    """Remembers recently seen signals for `window_seconds`, across processes."""

    def __init__(self, window_seconds, path=None, max_tracked=4096):
        self.window_seconds = window_seconds
        self.path = path or default_db_path()
        self.max_tracked = max_tracked
        # sqlite3 connections are not shareable between threads.
        self._local = threading.local()
        if self.window_seconds > 0:
            self._init_db()

    def _connect(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            # isolation_level=None: transactions are managed explicitly below.
            conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
            # WAL lets the webhook and the email reader write concurrently.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")
            self._local.conn = conn
        return conn

    def _reset_connection(self):
        """Drop a connection that has failed, so the next call reconnects.

        Without this a single failure is permanent: the broken handle stays
        cached on the thread and every later check fails open, silently
        disabling duplicate suppression for the life of the process.
        """
        conn = getattr(self._local, "conn", None)
        self._local.conn = None
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def _init_db(self):
        conn = self._connect()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seen ("
            "  key TEXT PRIMARY KEY,"
            "  ts  REAL NOT NULL"
            ")"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS seen_ts ON seen (ts)")

    def _now(self):
        # Wall clock, not monotonic: the value must be comparable across
        # processes that started at different times.
        return time.time()

    def check(self, key):
        """Record the key. Returns True when it was already seen in-window."""
        if self.window_seconds <= 0:
            return False

        now = self._now()
        cutoff = now - self.window_seconds
        try:
            conn = self._connect()
            # IMMEDIATE takes the write lock up front, so two processes
            # cannot both conclude they are the first to see this key.
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM seen WHERE ts <= ?", (cutoff,))
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO seen (key, ts) VALUES (?, ?)", (key, now)
                )
                duplicate = cursor.rowcount == 0
                if not duplicate:
                    # Keep only the newest max_tracked rows, so a flood of
                    # unique payloads cannot grow the file without limit.
                    conn.execute(
                        "DELETE FROM seen WHERE key IN ("
                        "  SELECT key FROM seen ORDER BY ts DESC LIMIT -1 OFFSET ?"
                        ")",
                        (self.max_tracked,),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            return duplicate
        except Exception as e:
            # Fail open, loudly. Refusing every order because a state file is
            # unwritable would be worse than the duplicate this prevents.
            # Discard the connection so this stays a transient failure.
            self._reset_connection()
            logger.error(f"❌ Duplicate check failed, allowing the signal through: {e}")
            return False

    def forget(self, key):
        """Drop a key so an equivalent signal is accepted again."""
        if self.window_seconds <= 0:
            return
        try:
            self._connect().execute("DELETE FROM seen WHERE key = ?", (key,))
        except Exception as e:
            self._reset_connection()
            logger.error(f"❌ Could not clear duplicate key {key}: {e}")

    def count(self):
        """Rows currently tracked. For tests and diagnostics."""
        if self.window_seconds <= 0:
            return 0
        try:
            return self._connect().execute("SELECT COUNT(*) FROM seen").fetchone()[0]
        except Exception:
            self._reset_connection()
            raise
