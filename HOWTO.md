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

2. Ensure your project directory contains the provided `supervisord.conf` file. If not, copy it into your project directory.

### **Steps**

#### 1. Copy the Provided `supervisord.conf` File
If you're running TradeX locally (not in Docker), copy the `supervisord.conf` file to the appropriate directory:
```bash
sudo cp supervisord.conf /etc/supervisor/conf.d/tradex.conf
```

For Docker-based setups, the `supervisord.conf` file is already integrated into the `Dockerfile`, so no additional setup is required.

#### 2. Reload Supervisor
After copying the configuration file, reload `supervisor` to recognize the new configuration:
```bash
sudo supervisorctl reread
sudo supervisorctl update
```

#### 3. Start the Services
Start all services defined in the `supervisord.conf` file:
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
tradex:dashboard_app      RUNNING   pid 1234, uptime 0:05:23
tradex:webhook_app        RUNNING   pid 1235, uptime 0:05:23
tradex:email_reader       RUNNING   pid 1236, uptime 0:05:23
```

#### 5. View Logs
To debug issues or monitor logs, check the log files specified in the `supervisord.conf` file:
```bash
tail -f /var/log/supervisor/dashboard_app.err.log
tail -f /var/log/supervisor/webhook_app.err.log
tail -f /var/log/supervisor/email_reader.err.log
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
```ini
[Unit]
Description=Gunicorn instance to serve TradeX Dashboard
After=network.target

[Service]
User=your_user  # Replace with your username (e.g., "ubuntu" or "root")
Group=www-data  # Replace with your group (optional)
WorkingDirectory=/path/to/tradex  # Replace with the absolute path to your project directory
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 dashboard_app:app
Restart=always
Environment="PATH=/path/to/venv/bin"  # Replace with the path to your virtual environment's bin folder
EnvironmentFile=/path/to/tradex/.env  # Optional: Load environment variables from .env

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
Description=Gunicorn instance to serve TradeX Webhook
After=network.target

[Service]
User=your_user  # Replace with your username
Group=www-data  # Replace with your group (optional)
WorkingDirectory=/path/to/tradex  # Replace with the absolute path to your project directory
ExecStart=/path/to/venv/bin/gunicorn -w 2 -b 0.0.0.0:5005 webhook_receiver:app
Restart=always
Environment="PATH=/path/to/venv/bin"  # Replace with the path to your virtual environment's bin folder
EnvironmentFile=/path/to/tradex/.env  # Optional: Load environment variables from .env

[Install]
WantedBy=multi-user.target
```

#### 4. Reload Systemd
Reload `systemd` to recognize the new services:
```bash
sudo systemctl daemon-reload
```

#### 5. Start the Services
Start both the dashboard and webhook services:
```bash
sudo systemctl start dashboard_app
sudo systemctl start webhook_app
```

#### 6. Enable the Services to Start on Boot
To ensure the services start automatically when the system boots:
```bash
sudo systemctl enable dashboard_app
sudo systemctl enable webhook_app
```

#### 7. Check the Status of the Services
Verify that both services are running without errors:
```bash
sudo systemctl status dashboard_app
sudo systemctl status webhook_app
```

If everything is working correctly, you should see output similar to:
```
● dashboard_app.service - Gunicorn instance to serve TradeX Dashboard
   Loaded: loaded (/etc/systemd/system/dashboard_app.service; enabled; vendor preset: enabled)
   Active: active (running) since ...
```

#### 8. View Logs
To debug issues or monitor logs, use `journalctl`:
```bash
sudo journalctl -u dashboard_app -f
sudo journalctl -u webhook_app -f
```

#### 9. Restart or Stop the Services
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
  - Ensure all paths in the `.service` or `supervisord.conf` files are correct.
  - Verify that the `.env` file exists and contains valid configuration.

- **Port Conflicts**:
  - If ports `5000` or `5005` are already in use, update the `ExecStart` commands in the `.service` files or the `command` fields in the `supervisord.conf` file to use different ports.

- **Gunicorn Not Found**:
  - Ensure Gunicorn is installed in your virtual environment. Run:
    ```bash
    pip install gunicorn
    ```

---
