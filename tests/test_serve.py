"""The bind address knobs must actually reach gunicorn.

DASHBOARD_HOST / WEBHOOK_HOST and the port variables were documented but
ignored: both main.py and supervisord.conf hardcoded 0.0.0.0 and a fixed
port, so setting them changed nothing.
"""

import pytest


def _serve(app_env, **env):
    return app_env(modules=["config", "serve"], **env)["serve"]


def test_dashboard_host_and_port_are_honoured(app_env):
    serve = _serve(app_env, DASHBOARD_HOST="127.0.0.1", DASHBOARD_PORT="8123")
    assert "-b" in serve.build_command("dashboard")
    assert "127.0.0.1:8123" in serve.build_command("dashboard")


def test_webhook_host_and_port_are_honoured(app_env):
    serve = _serve(app_env, WEBHOOK_HOST="10.0.0.5", WEBHOOK_PORT="9001")
    assert "10.0.0.5:9001" in serve.build_command("webhook")


def test_defaults_bind_all_interfaces(app_env):
    """Containers need 0.0.0.0 internally; compose limits what is published."""
    serve = _serve(app_env)
    assert "0.0.0.0:5000" in serve.build_command("dashboard")
    assert "0.0.0.0:5005" in serve.build_command("webhook")


def test_each_service_runs_a_single_worker(app_env):
    """The PIN and login lockouts are per-process, so a second worker would
    give an attacker two independent allowances."""
    serve = _serve(app_env)
    for service in ("dashboard", "webhook"):
        command = serve.build_command(service)
        assert command[command.index("-w") + 1] == "1"


def test_services_map_to_the_right_app(app_env):
    serve = _serve(app_env)
    assert serve.build_command("dashboard")[-1] == "dashboard_app:app"
    assert serve.build_command("webhook")[-1] == "webhook_receiver:app"


def test_unknown_service_is_rejected(app_env):
    serve = _serve(app_env)
    with pytest.raises(SystemExit):
        serve.build_command("nope")


def test_environment_tags_the_log_file(app_env):
    serve = _serve(app_env)
    assert serve.environment("webhook")["TRADEX_SERVICE"] == "webhook"


def test_deployment_files_do_not_hardcode_the_bind_address():
    """supervisord.conf and the HOWTO systemd units must go through serve.py,
    or the documented settings silently stop working again."""
    for path in ("supervisord.conf", "HOWTO.md"):
        text = open(path, encoding="utf-8").read()
        assert "-b 0.0.0.0:" not in text, f"{path} hardcodes a bind address"


def test_deployment_files_do_not_raise_the_worker_count():
    for path in ("supervisord.conf", "HOWTO.md"):
        text = open(path, encoding="utf-8").read()
        for bad in ("-w 2", "-w 4", "-w 8"):
            assert bad not in text, f"{path} runs multiple workers ({bad})"


def _published_ports(path="docker-compose.yml"):
    """Port mappings actually declared, ignoring commented-out examples."""
    ports, in_ports = [], False
    for raw in open(path, encoding="utf-8"):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip() == "ports:":
            in_ports = True
            continue
        if in_ports:
            if line.strip().startswith("- "):
                ports.append(line.strip()[2:].strip().strip('"\''))
            else:
                in_ports = False
    return ports


def test_compose_keeps_the_dashboard_off_the_public_network():
    """It serves no TLS and can close every open position, so a stock
    `docker-compose up` must not put it on all interfaces."""
    ports = _published_ports()
    dashboard = [p for p in ports if p.endswith(":5000")]

    assert dashboard == ["127.0.0.1:5000:5000"], f"published: {ports}"


def test_compose_still_exposes_the_webhook():
    """TradingView has to be able to POST to it."""
    assert "5005:5005" in _published_ports()


# --- deployment documentation ---

def _ini_blocks(path, marker):
    """Fenced ```ini blocks in a markdown file, split into lines."""
    blocks, current = [], None
    for line in open(path, encoding="utf-8"):
        if line.startswith("```ini"):
            current = []
        elif line.startswith("```") and current is not None:
            blocks.append(current)
            current = None
        elif current is not None:
            current.append(line.rstrip("\n"))
    return [b for b in blocks if any(marker in l for l in b)]


def test_systemd_units_have_no_trailing_comments():
    """systemd has no inline comments: `User=me  # note` sets the user to the
    whole string and the unit fails to start."""
    offenders = []
    for block in _ini_blocks("HOWTO.md", "[Unit]"):
        for line in block:
            if line.startswith("#") or not line.strip():
                continue
            if "=" in line and "#" in line.split("=", 1)[1]:
                offenders.append(line)
    assert not offenders, f"trailing comments break these: {offenders}"


def test_systemd_units_cover_every_service():
    units = _ini_blocks("HOWTO.md", "[Unit]")
    started = " ".join(l for b in units for l in b)
    assert "serve.py dashboard" in started
    assert "serve.py webhook" in started
    assert "email_reader.py" in started, "the email reader had no unit"


def test_host_supervisor_config_is_not_the_container_one():
    """The repo's supervisord.conf runs as PID 1 in the container: it sets
    nodaemon and points at /app, so it cannot be dropped into conf.d."""
    howto = open("HOWTO.md", encoding="utf-8").read()
    assert "sudo cp supervisord.conf /etc/supervisor" not in howto

    for block in _ini_blocks("HOWTO.md", "[program:"):
        joined = "\n".join(block)
        assert "nodaemon" not in joined
        assert "[supervisord]" not in joined
        assert "directory=/app" not in joined, "container path in a host config"


def test_host_supervisor_config_covers_every_service():
    blocks = _ini_blocks("HOWTO.md", "[program:")
    joined = "\n".join(l for b in blocks for l in b)
    assert "serve.py dashboard" in joined
    assert "serve.py webhook" in joined
    assert "email_reader.py" in joined


def test_host_supervisor_puts_the_venv_on_path():
    """serve.py execs gunicorn by name. The systemd units set PATH to the
    venv; without the same on the supervisor programs, start fails with
    No such file or directory: 'gunicorn'."""
    for block in _ini_blocks("HOWTO.md", "[program:"):
        joined = "\n".join(block)
        if "serve.py" not in joined:
            continue
        assert ".venv/bin" in joined
        assert "environment=PATH=" in joined
