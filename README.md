# TradeX

**TradeX** is a web-based trading bot dashboard designed to enhance your cryptocurrency trading experience by managing and monitoring positions across multiple exchanges. Key features include authentication measures and configurable PIN protection for trade execution, ensuring secure transactions. The platform allows users to execute trades on various crypto exchanges, streamlining the trading process. TradeX can accept webhooks from TradingView, enabling automated trade placements based on market signals. With its robust capabilities, TradeX aims to simplify the complexities of cryptocurrency trading, making it accessible for both novice and experienced traders.

---

## Features

- **Multi-Exchange Support**: Seamlessly works with Bybit, Binance, and other CCXT-supported exchanges.
- **Order Management**: Place, modify, and cancel orders directly from the dashboard.
- **Pending and Open Positions**: View all your active and pending orders in a user-friendly interface.
- **Close All Positions**: Quickly close all open positions with a single click.
- **Authentication**: Secure dashboard with password.
- **Trade PIN Protection**: Add an extra layer of security by requiring a PIN for order execution via webhooks.

---

## Screenshots

![App_Screenshot](https://github.com/user-attachments/assets/79bd5123-c81c-49b1-9e8e-5d064698f20d)

---

## Supported Exchanges
- Bybit Futures
- Binance Futures (not fully tested)
- Additional changes can be made upon request, or you can contribute by submitting a pull request
---

## Installation

### Prerequisites

- Python 3.8 or later
- `pip` package manager
- API keys for your supported exchanges (e.g., Bybit, Binance)

### Steps

1. Clone the repository:
    ```bash
    git clone https://github.com/Sentello/tradex.git
    cd tradex
    ```

2. Set up a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4. Configure your environment variables:
    - Edit the config file `config.py`.
    - Add your exchange API keys, dashboard password, and PIN in `config.py`.

5. Run the application:
    ```bash
    python app.py
    ```

6. Access the dashboard:
    Open your browser and go to `http://localhost:5000`.

---

## Usage

### Webhook Example (testing from curl)
To place an order via the webhook, use the following examples:

```bash
curl -X POST http://<server-ip>:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "buy",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.01
}'
```
Place a Limit Order

```bash
curl -X POST http://<server-ip>:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "binance",
    "SYMBOL": "ETHUSDT",
    "SIDE": "sell",
    "ORDER_TYPE": "limit",
    "QUANTITY": 0.5,
    "PRICE": 2000.50
}'
```

Place a Market Order

```bash
curl -X POST http://192.168.1.8:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "buy",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.001,
    "PRICE": 90001.50
}'
```

Place a Market Sell Order

```bash
curl -X POST http://192.168.1.8:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "sell",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.001
}'
```

Place a Limit Order with Stop Loss and Take Profit

```bash
curl -X POST http://<server-ip>:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "buy",
    "ORDER_TYPE": "limit",
    "QUANTITY": 0.01,
    "PRICE": 30000,
    "STOP_LOSS": 29000,
    "TAKE_PROFIT": 31000
}'
```

### Webhook Example (TradingView Webhook)
The same logic applies as with cURL, but keep the content within the curly brackets as it is, so it looks like this:
```bash
{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "buy",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.01
}
```
Please note that TradingView can only use webhooks on ports 80 or 443. This means you'll need to proxy your webhook port to either 80 or 443, depending on your requirements. I strongly recommend using port 80 to avoid potential SSL-related complications and suggest using Nginx as a proxy for this setup.

## Running the App as a Service

You can run the app as a service using two methods:

1. **Supervisor** (`supervisorctl`)
2. **systemd** (`systemctl`)

Choose the one that best fits your needs.

---

### Option 1: Using Supervisor

#### Steps:
Install `supervisor` on your system:
```bash
sudo apt update
sudo apt install supervisor
```
Create a configuration file for the dashboard_app:
```bash
sudo nano /etc/supervisor/conf.d/dashboard_app.conf:
```
Add the following content:
```bash
[program:dashboard_app]
command=gunicorn -w 4 -b 0.0.0.0:5000 app:dashboard_app
directory=/path/to/your/project
autostart=true
autorestart=true
stderr_logfile=/var/logs/dashboard_error.log
stdout_logfile=/var/logs/logs/dashboard_access.log
```
Create a configuration file for the webhook_app:
```bash
sudo nano /etc/supervisor/conf.d/webhook_app.conf:
```
Add the following content:
```bash
[program:webhook_app]
command=gunicorn -w 2 -b 0.0.0.0:5005 app:webhook_app
directory=/path/to/your/project
autostart=true
autorestart=true
stderr_logfile=/var/logs/webhook_error.log
stdout_logfile=/var/logs/webhook_access.log
```
...and eplace /path/to/ with the directory where your app is located, and your-username with your system's username.
 Apply the Configuration, reload Supervisor and start the service:
 ```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```
Check the status of your app:
 ```bash
sudo supervisorctl status
```
To stop or restart the app:
 ```bash
sudo supervisorctl stop dashboard_app
sudo supervisorctl restart dashboard_app
```
- Standard Output: /var/log/xxx
- Errors: /var/log/xxx

### Option 2: Using systemd

#### Steps:
Navigate to the /etc/systemd/system/ directory:
 ```bash
cd /etc/systemd/system/
```
Create a new file for dashboard_app:
 ```bash
nano dashboard_app.service
```
Add the following content:
 ```bash
[Unit]
Description=Gunicorn instance to serve dashboard_app
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/your/virtualenv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:dashboard_app
Restart=always

[Install]
WantedBy=multi-user.target
```
/path/to/your/project with the directory containing your app.py.
/path/to/your/virtualenv/bin/gunicorn with the Gunicorn binary in your virtual environment.
Create another service file for webhook_app:
 ```bash
nano webhook_app.service
```
Add the following configuration:
 ```bash
[Unit]
Description=Gunicorn instance to serve webhook_app
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/your/virtualenv/bin/gunicorn -w 2 -b 0.0.0.0:5005 app:webhook_app
Restart=always

[Install]
WantedBy=multi-user.target

```
Reload systemd to recognize the new service:
 ```bash
sudo systemctl daemon-reload
```
Start the services:
 ```bash
systemctl start dashboard_app
systemctl start webhook_app
```
Enable the services to start automatically on boot:
 ```bash
systemctl enable dashboard_app
systemctl enable webhook_app
```
Check the service status:
 ```bash
systemctl status dashboard_app
systemctl status webhook_app
```
View logs using journalctl:
 ```bash
journalctl -u dashboard_app
journalctl -u webhook_app
```
To stop or restart service:
 ```bash
systemctl restart dashboard_app
systemctl restart webhook_app

systemctl stop dashboard_app
systemctl stop webhook_app

```
