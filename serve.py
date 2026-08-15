"""Launch a gunicorn service on its configured address.

Single source of truth for how the WSGI services are started. main.py and
supervisord.conf both go through here, so DASHBOARD_HOST / WEBHOOK_HOST and
the port variables actually take effect. Previously both call sites
hardcoded 0.0.0.0 and the documented bind settings did nothing.

Usage: python serve.py {webhook|dashboard}
"""

import os
import sys

import config

# One worker per service, deliberately. The PIN lockout and the dashboard
# login lockout are held in process memory, so a second worker would give an
# attacker two independent allowances. Duplicate suppression is shared via
# SQLite and is not affected.
WORKERS = 1

SERVICES = {
    "webhook": ("webhook_receiver:app", "WEBHOOK_HOST", "WEBHOOK_PORT"),
    "dashboard": ("dashboard_app:app", "DASHBOARD_HOST", "DASHBOARD_PORT"),
}


def build_command(service):
    """gunicorn argv for a service, using the configured bind address."""
    try:
        app, host_attr, port_attr = SERVICES[service]
    except KeyError:
        raise SystemExit(
            f"Unknown service {service!r}. Expected one of: {', '.join(sorted(SERVICES))}"
        )

    host = getattr(config, host_attr)
    port = getattr(config, port_attr)
    return [
        "gunicorn",
        "-w", str(WORKERS),
        "-b", f"{host}:{port}",
        app,
    ]


def environment(service):
    """Env for the child, tagging which log file it should write."""
    return dict(os.environ, TRADEX_SERVICE=service)


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__.strip().splitlines()[-1])

    service = argv[1].strip().lower()
    command = build_command(service)
    os.environ["TRADEX_SERVICE"] = service
    # exec rather than spawn, so supervisor signals reach gunicorn directly.
    os.execvp(command[0], command)


if __name__ == "__main__":
    main(sys.argv)
