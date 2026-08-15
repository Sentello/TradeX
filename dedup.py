"""Duplicate signal suppression.

Protects against the same order being placed twice. The realistic case is
not an attacker but a lost response: if the connection drops after the
exchange accepted the order but before the sender saw the reply, the sender
cannot tell that from a genuine failure, and a retry would double the
position.

This is at-most-once within a time window, not true anti-replay. A sender
that cannot sign its requests (TradingView cannot) offers nothing to verify
freshness against, so an attacker who captures a request can still replay it
after the window expires. WEBHOOK_ALLOWED_IPS and a high-entropy
WEBHOOK_PIN are the controls for that.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict

# Fields excluded from the fingerprint: secrets, and the caller's own
# idempotency key which is handled separately.
_EXCLUDED = {"pin", "id"}


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
    """Remembers recently seen signals for `window_seconds`."""

    def __init__(self, window_seconds, max_tracked=4096):
        self.window_seconds = window_seconds
        self.max_tracked = max_tracked
        self._seen = OrderedDict()  # key -> first seen timestamp
        self._lock = threading.Lock()

    def _now(self):
        return time.monotonic()

    def _expire(self, now):
        """Drop entries older than the window. Keys are inserted in time
        order, so stopping at the first live one is enough."""
        cutoff = now - self.window_seconds
        while self._seen:
            key, seen_at = next(iter(self._seen.items()))
            if seen_at > cutoff:
                break
            del self._seen[key]

    def check(self, key):
        """Record the key. Returns True when it was already seen in-window."""
        if self.window_seconds <= 0:
            return False

        with self._lock:
            now = self._now()
            self._expire(now)

            seen_at = self._seen.get(key)
            if seen_at is not None and seen_at > now - self.window_seconds:
                # Deliberately not refreshed: a run of retries should not
                # extend the window indefinitely.
                return True

            self._seen[key] = now
            self._seen.move_to_end(key)
            # Enforce the cap after inserting, or the store settles one entry
            # above max_tracked.
            while len(self._seen) > self.max_tracked:
                self._seen.popitem(last=False)
            return False

    def forget(self, key):
        """Drop a key so an equivalent signal is accepted again."""
        with self._lock:
            self._seen.pop(key, None)
