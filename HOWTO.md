# HOWTO:
# Running TradeX as a Service

This guide provides step-by-step instructions for running TradeX as a background service using either **Supervisor** (`supervisord`) or **Systemd**. These tools ensure that your application runs reliably and restarts automatically if it crashes.

---

## Table of Contents
- [Running TradeX with Supervisord](#running-tradex-with-supervisord)
- [Running TradeX with Systemd](#running-tradex-with-systemd)
- [Troubleshooting](#troubleshooting)

---

## Running TradeX with Supervisord

`Supervisord` is a process control system that allows you to manage multiple processes (like TradeX) as background services. Below are the steps to set up TradeX using `supervisord`.

### **Prerequisites**
1. Install `supervisor` on your system:
   ```bash
   sudo apt update
   sudo apt install supervisor
   ```

2. Have a working checkout and virtualenv. The host supervisor config is created in the next step — do not copy the repository's `supervisord.conf` (that file is for the container).

### **Steps**

#### 1. Create a Supervisor Config for Your Host

> **Do not copy the repository's `supervisord.conf`.** That file configures
> supervisor as PID 1 *inside the container*. It sets `nodaemon=true`, owns
> the `[supervisord]` and `[supervisorctl]` sections, and points every
> program at `/app`. Dropped into `conf.d/` on a host it collides with your
> system's own `[supervisord]` section and refers to paths that do not
> exist there.

Files in `/etc/supervisor/conf.d/` define programs only. Create
`/etc/supervisor/conf.d/tradex.conf`:

```bash
sudo nano /etc/supervisor/conf.d/tradex.conf
```

```ini
[program:tradex_dashboard]
command=/path/to/tradex/.venv/bin/python /path/to/tradex/serve.py dashboard
directory=/path/to/tradex
user=your_user
# serve.py execs gunicorn by name; without the venv on PATH that fails.
environment=PATH="/path/to/tradex/.venv/bin:%(ENV_PATH)s"
autostart=true
autorestart=true
startsecs=5
stopwaitsecs=10
stdout_logfile=/var/log/supervisor/tradex_dashboard.out.log
stderr_logfile=/var/log/supervisor/tradex_dashboard.err.log
priority=10

[program:tradex_webhook]
command=/path/to/tradex/.venv/bin/python /path/to/tradex/serve.py webhook
directory=/path/to/tradex
user=your_user
environment=PATH="/path/to/tradex/.venv/bin:%(ENV_PATH)s"
autostart=true
autorestart=true
startsecs=5
stopwaitsecs=10
stdout_logfile=/var/log/supervisor/tradex_webhook.out.log
stderr_logfile=/var/log/supervisor/tradex_webhook.err.log
priority=20

# Exits 0 immediately when MODE excludes email, so autorestart=unexpected
# stops supervisor from respawning it forever.
[program:tradex_email_reader]
command=/path/to/tradex/.venv/bin/python /path/to/tradex/email_reader.py
directory=/path/to/tradex
user=your_user
autostart=true
autorestart=unexpected
exitcodes=0
startsecs=0
stopwaitsecs=15
stdout_logfile=/var/log/supervisor/tradex_email_reader.out.log
stderr_logfile=/var/log/supervisor/tradex_email_reader.err.log
priority=30

[group:tradex]
programs=tradex_dashboard,tradex_webhook,tradex_email_reader
priority=999
```

Replace `/path/to/tradex` and `your_user` throughout, and use your
virtualenv's interpreter — a bare `python` may not be the one with the
dependencies installed. Ports are not set here: `serve.py` reads
`DASHBOARD_HOST`/`DASHBOARD_PORT` and `WEBHOOK_HOST`/`WEBHOOK_PORT` from
`.env`.

For Docker-based setups none of this applies — the container's
`supervisord.conf` is already wired into the `Dockerfile`.

#### 2. Reload Supervisor
After creating the configuration file, reload `supervisor` to recognize the new configuration:
```bash
sudo supervisorctl reread
sudo supervisorctl update
```

#### 3. Start the Services
Start all services defined in `tradex.conf`:
```bash
sudo supervisorctl start tradex:*
```

#### 4. Check the Status of the Services
Verify that all services are running without errors:
```bash
sudo supervisorctl status
```

You should see output similar to:
```
tradex:tradex_dashboard         RUNNING   pid 1234, uptime 0:05:23
tradex:tradex_webhook           RUNNING   pid 1235, uptime 0:05:23
tradex:tradex_email_reader      RUNNING   pid 1236, uptime 0:05:23
```

#### 5. View Logs
To debug issues or monitor logs, check the log files specified in `tradex.conf`:
```bash
tail -f /var/log/supervisor/tradex_dashboard.err.log
tail -f /var/log/supervisor/tradex_webhook.err.log
tail -f /var/log/supervisor/tradex_email_reader.err.log
```

#### 6. Restart or Stop the Services
To restart or stop the services:
```bash
sudo supervisorctl restart tradex:*
sudo supervisorctl stop tradex:*
```

---

## Running TradeX with Systemd

`Systemd` is a system and service manager for Linux operating systems. It allows you to manage services (like TradeX) as background processes that start automatically on boot. Below is a comprehensive guide to setting up TradeX as a `systemd` service.

### **Prerequisites**
1. Ensure your Python environment (including dependencies) is set up and working.
2. If using a virtual environment, ensure its path is known.
3. Ensure you have `sudo` privileges to create and manage `systemd` services.

### **Steps**

#### 1. Navigate to the Systemd Directory
All `systemd` service files are stored in `/etc/systemd/system/`. Navigate to this directory:
```bash
cd /etc/systemd/system/
```

#### 2. Create a Service File for the Dashboard
The dashboard app (`dashboard_app.py`) serves the web interface. Create a service file for it:
```bash
sudo nano dashboard_app.service
```

Add the following content:
> **systemd does not support trailing comments.** A line like
> `User=you  # your username` sets the user to the whole string including
> the comment, and the unit fails to start. Put comments on their own line,
> as below, and substitute the placeholder values directly.

```ini
[Unit]
Description=TradeX Dashboard
After=network.target

[Service]
# Replace your_user, and the two /path/to/... paths, with real values.
User=your_user
Group=your_user
WorkingDirectory=/path/to/tradex
ExecStart=/path/to/tradex/.venv/bin/python /path/to/tradex/serve.py dashboard
Restart=always
RestartSec=5
Environment="PATH=/path/to/tradex/.venv/bin"
EnvironmentFile=/path/to/tradex/.env

[Install]
WantedBy=multi-user.target
```

#### 3. Create a Service File for the Webhook
The webhook app (`webhook_receiver.py`) listens for incoming trade signals. Create a service file for it:
```bash
sudo nano webhook_app.service
```

Add the following content:
```ini
[Unit]
Description=TradeX Webhook Receiver
After=network.target

[Service]
# Replace your_user, and the two /path/to/... paths, with real values.
User=your_user
Group=your_user
WorkingDirectory=/path/to/tradex
ExecStart=/path/to/tradex/.venv/bin/python /path/to/tradex/serve.py webhook
Restart=always
RestartSec=5
Environment="PATH=/path/to/tradex/.venv/bin"
EnvironmentFile=/path/to/tradex/.env

[Install]
WantedBy=multi-user.target
```

#### 4. Create a Service File for the Email Reader
Only needed when `MODE` is `email` or `both`. The reader exits 0 immediately
if email ingestion is disabled, so `Restart=on-failure` stops systemd
restarting it forever in that case:
```bash
sudo nano email_reader.service
```

```ini
[Unit]
Description=TradeX Email Signal Reader
After=network.target

[Service]
# Replace your_user, and the two /path/to/... paths, with real values.
User=your_user
Group=your_user
WorkingDirectory=/path/to/tradex
ExecStart=/path/to/tradex/.venv/bin/python /path/to/tradex/email_reader.py
Restart=on-failure
RestartSec=5
Environment="PATH=/path/to/tradex/.venv/bin"
EnvironmentFile=/path/to/tradex/.env

[Install]
WantedBy=multi-user.target
```

#### 5. Reload Systemd
Reload `systemd` to recognize the new services:
```bash
sudo systemctl daemon-reload
```

#### 6. Start the Services
Start the services. Include `email_reader` only if `MODE` is `email` or `both`:
```bash
sudo systemctl start dashboard_app
sudo systemctl start webhook_app
sudo systemctl start email_reader
```

#### 7. Enable the Services to Start on Boot
```bash
sudo systemctl enable dashboard_app
sudo systemctl enable webhook_app
sudo systemctl enable email_reader
```

#### 8. Check the Status of the Services
Verify that the services are running without errors:
```bash
sudo systemctl status dashboard_app
sudo systemctl status webhook_app
sudo systemctl status email_reader
```

If everything is working correctly, you should see output similar to:
```
● dashboard_app.service - TradeX Dashboard
   Loaded: loaded (/etc/systemd/system/dashboard_app.service; enabled; vendor preset: enabled)
   Active: active (running) since ...
```

`email_reader` showing `inactive (dead)` with an exit status of `0` is
expected when `MODE=webhook` — it means the reader saw email ingestion was
disabled and stopped cleanly.

#### 9. View Logs
To debug issues or monitor logs, use `journalctl`:
```bash
sudo journalctl -u dashboard_app -f
sudo journalctl -u webhook_app -f
sudo journalctl -u email_reader -f
```

#### 10. Restart or Stop the Services
To restart or stop the services:
```bash
sudo systemctl restart dashboard_app
sudo systemctl stop dashboard_app

sudo systemctl restart webhook_app
sudo systemctl stop webhook_app
```

---

## Troubleshooting

### General Tips
1. **Check Logs**: Use `journalctl` (for `systemd`) or `tail -f` (for `supervisord`) to view logs and identify errors.
2. **Permissions**: Ensure the user running the service has read/write access to the project directory and logs.
3. **Ports**: Verify that ports `5000` (dashboard) and `5005` (webhook) are not already in use by another process.
4. **Dependencies**: Ensure all Python dependencies are installed in your virtual environment.

### Common Issues
- **Service Fails to Start**:
  - Check the logs for detailed error messages.
  - Ensure all paths in the `.service` files or `/etc/supervisor/conf.d/tradex.conf` are correct.
  - Verify that the `.env` file exists and contains valid configuration.

- **Port Conflicts**:
  - If ports `5000` or `5005` are already in use, set `DASHBOARD_PORT` / `WEBHOOK_PORT` in `.env`. `serve.py` reads them, so the service files do not need editing.

- **Gunicorn Not Found**:
  - Ensure Gunicorn is installed in your virtual environment. Run:
    ```bash
    pip install gunicorn
    ```

---
