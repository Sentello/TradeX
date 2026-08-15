"""Config must refuse to start rather than fall back to insecure defaults."""

import pytest


def test_missing_secret_key_is_rejected(app_env):
    with pytest.raises(Exception) as exc:
        app_env(modules=["config"], FLASK_SECRET_KEY=None)
    assert "FLASK_SECRET_KEY" in str(exc.value)


def test_missing_webhook_pin_is_rejected(app_env):
    """An empty PIN used to mean 'no authentication at all' on /webhook."""
    with pytest.raises(Exception) as exc:
        app_env(modules=["config"], WEBHOOK_PIN=None)
    assert "WEBHOOK_PIN" in str(exc.value)


def test_plaintext_dashboard_password_is_rejected(app_env):
    with pytest.raises(Exception) as exc:
        app_env(modules=["config"], DASHBOARD_PASSWORD="hunter2")
    assert "bcrypt" in str(exc.value)


def test_invalid_mode_is_rejected(app_env):
    with pytest.raises(Exception) as exc:
        app_env(modules=["config"], MODE="banana")
    assert "MODE" in str(exc.value)


def test_missing_imap_port_does_not_crash_webhook_only_setup(app_env):
    """int(os.getenv("IMAP_PORT", "")) used to raise and stop every service."""
    config = app_env(modules=["config"], MODE="webhook")["config"]
    assert config.IMAP_PORT == 993


def test_email_mode_requires_imap_settings(app_env):
    with pytest.raises(Exception) as exc:
        app_env(modules=["config"], MODE="email")
    assert "IMAP_SERVER" in str(exc.value)


def test_mode_flags(app_env):
    config = app_env(modules=["config"], MODE="webhook")["config"]
    assert config.WEBHOOK_ENABLED is True
    assert config.EMAIL_ENABLED is False
