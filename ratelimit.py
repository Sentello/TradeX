"""Per-client failure throttling.

Deliberately keyed per client rather than applied to the endpoint as a
whole: a global lockout would let anyone disable trading by sending a few
bad requests, which is worse than the brute force it prevents.
"""

import ipaddress
import threading
import time
from collections import OrderedDict


class FailureThrottle:
    """Blocks a client after repeated failures, for a fixed cooldown."""

    def __init__(self, max_failures, lockout_seconds, max_tracked=4096):
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        # Bounded so an attacker rotating source addresses cannot grow this
        # without limit.
        self.max_tracked = max_tracked
        self._entries = OrderedDict()  # key -> (failures, blocked_until)
        self._lock = threading.Lock()

    def _now(self):
        return time.monotonic()

    def blocked_for(self, key):
        """Seconds of lockout remaining, 0 when the client may proceed."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return 0.0
            failures, blocked_until = entry
            remaining = blocked_until - self._now()
            if remaining <= 0:
                if blocked_until:
                    # Cooldown served, start the client over.
                    del self._entries[key]
                return 0.0
            self._entries.move_to_end(key)
            return remaining

    def record_failure(self, key):
        """Count a failure. Returns lockout seconds remaining, 0 if not blocked."""
        with self._lock:
            failures, blocked_until = self._entries.get(key, (0, 0.0))
            failures += 1
            if failures >= self.max_failures:
                blocked_until = self._now() + self.lockout_seconds
            self._entries[key] = (failures, blocked_until)
            self._entries.move_to_end(key)

            while len(self._entries) > self.max_tracked:
                self._entries.popitem(last=False)

            remaining = blocked_until - self._now()
            return max(remaining, 0.0)

    def reset(self, key):
        """Clear a client's history after a success."""
        with self._lock:
            self._entries.pop(key, None)


def parse_networks(raw):
    """Parse a comma-separated list of IPs and CIDR blocks."""
    networks = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        # strict=False so "10.0.0.5/24" is accepted as its containing network.
        networks.append(ipaddress.ip_network(part, strict=False))
    return tuple(networks)


def ip_allowed(address, networks):
    """True when no allowlist is configured, or the address falls inside it."""
    if not networks:
        return True
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(parsed in network for network in networks)
