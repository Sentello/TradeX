"""Dashboard authentication, lockout and CSRF."""

from conftest import TEST_PASSWORD


def _boot(app_env, **env):
    modules = app_env(
        modules=["config", "exchanges", "bot_logic", "dashboard_app"], **env
    )
    dashboard = modules["dashboard_app"]
    dashboard.app.config["TESTING"] = True
    return dashboard, dashboard.app.test_client()


def test_correct_password_logs_in(app_env):
    _, client = _boot(app_env)
    response = client.post("/login", data={"password": TEST_PASSWORD})
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["logged_in"] is True


def test_wrong_password_is_rejected(app_env):
    _, client = _boot(app_env)
    response = client.post("/login", data={"password": "nope"})
    assert response.status_code == 401
    with client.session_transaction() as sess:
        assert "logged_in" not in sess


def test_missing_password_field_does_not_500(app_env):
    """password.encode() on None used to raise AttributeError."""
    _, client = _boot(app_env)
    response = client.post("/login", data={})
    assert response.status_code == 401


def test_repeated_failures_lock_the_client_out(app_env):
    _, client = _boot(app_env)  # LOGIN_MAX_ATTEMPTS=3 in the test env
    for _ in range(3):
        client.post("/login", data={"password": "nope"})

    # Even the right password is refused while locked out.
    response = client.post("/login", data={"password": TEST_PASSWORD})
    assert response.status_code == 429


def test_protected_routes_redirect_when_logged_out(app_env):
    _, client = _boot(app_env)
    for route in ("/", "/positions", "/logs", "/summary_stats"):
        assert client.get(route).status_code == 302


def test_state_changing_post_requires_csrf_token(app_env):
    _, client = _boot(app_env)
    client.post("/login", data={"password": TEST_PASSWORD})

    response = client.post(
        "/close_all_positions", data={}
    )
    assert response.status_code == 400
    assert "CSRF" in response.get_json()["message"]


def test_post_succeeds_with_csrf_token(app_env):
    _, client = _boot(app_env)
    client.post("/login", data={"password": TEST_PASSWORD})
    with client.session_transaction() as sess:
        token = sess["csrf_token"]

    response = client.post("/close_all_positions", data={"csrf_token": token})
    assert response.status_code == 302


def _logged_in(app_env):
    dashboard, client = _boot(app_env)
    client.post("/login", data={"password": TEST_PASSWORD})
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    return dashboard, client, token


def test_failed_close_is_shown_on_the_dashboard(app_env):
    dashboard, client, token = _logged_in(app_env)
    dashboard.close_position = lambda *a, **k: {
        "status": "error",
        "message": "reduceOnly rejected",
    }

    response = client.post(
        "/close_position",
        data={"csrf_token": token, "EXCHANGE": "bybit", "SYMBOL": "BTC/USDT:USDT"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"reduceOnly rejected" in response.data


def test_failed_cancel_is_shown_on_the_dashboard(app_env):
    dashboard, client, token = _logged_in(app_env)
    dashboard.cancel_order = lambda *a, **k: {
        "status": "error",
        "message": "order already filled",
    }

    response = client.post(
        "/cancel_order",
        data={
            "csrf_token": token,
            "EXCHANGE": "bybit",
            "ORDER_ID": "1",
            "SYMBOL": "BTC/USDT:USDT",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"order already filled" in response.data


def test_close_all_surfaces_partial_failures(app_env):
    dashboard, client, token = _logged_in(app_env)
    dashboard.close_all_positions = lambda: {
        "BTC/USDT:USDT": {"status": "success", "order": {}},
        "ETH/USDT:USDT": {"status": "error", "message": "reduceOnly rejected"},
    }

    response = client.post(
        "/close_all_positions",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"ETH/USDT:USDT: reduceOnly rejected" in response.data
    assert b"BTC/USDT:USDT" not in response.data


def test_logs_endpoint_is_tailed(app_env, tmp_path):
    dashboard, client = _boot(app_env)
    client.post("/login", data={"password": TEST_PASSWORD})

    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "big.log").write_text("".join(f"line {i}\n" for i in range(2000)))

    body = client.get("/logs").get_json()
    assert body["status"] == "success"
    assert len(body["logs"]["big.log"]) == dashboard.LOG_TAIL_LINES
    assert body["logs"]["big.log"][-1].strip() == "line 1999"
