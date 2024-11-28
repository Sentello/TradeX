# TradeX
![image](https://github.com/user-attachments/assets/869386f3-7cc4-4768-a619-7344bd16d4fc| width=100)

**TradeX** is a web-based trading bot dashboard designed to enhance your cryptocurrency trading experience by managing and monitoring positions across multiple exchanges. Key features include authentication measures and configurable PIN protection for trade execution, ensuring secure transactions. The platform allows users to execute trades on various crypto exchanges, streamlining the trading process. TradeX can accept webhooks from TradingView, enabling automated trade placements based on market signals. With its robust capabilities, TradeX aims to simplify the complexities of cryptocurrency trading, making it accessible for both novice and experienced traders.

---

## Features

- **Multi-Exchange Support**: Seamlessly works with Bybit, Binance, and other CCXT-supported exchanges.
- **Order Management**: Place, modify, and cancel orders directly from the dashboard.
- **Pending and Open Positions**: View all your active and pending orders in a user-friendly interface.
- **Close All Positions**: Quickly close all open positions with a single click.
- **Authentication**: Secure the dashboard with a username and password.
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
curl -X POST http://<server-ip>:5000/webhook -H "Content-Type: application/json" -d '{
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
curl -X POST http://<server-ip>:5000/webhook -H "Content-Type: application/json" -d '{
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
curl -X POST http://192.168.1.8:5000/webhook -H "Content-Type: application/json" -d '{
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
curl -X POST http://192.168.1.8:5000/webhook -H "Content-Type: application/json" -d '{
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
curl -X POST http://<server-ip>:5000/webhook -H "Content-Type: application/json" -d '{
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
Create a configuration file for the app:
```bash
sudo nano /etc/supervisor/conf.d/tradex.conf
```
Add the following content:
```bash
[program:tradex]
command=python3 /path/to/app.py
directory=/path/to/
autostart=true
autorestart=true
stderr_logfile=/var/log/tradex.err.log
stdout_logfile=/var/log/tradex.out.log
user=your-username
```
...and eplace /path/to/ with the directory where your app is located, and your-username with your system's username.
 Apply the Configuration, reload Supervisor and start the service:
 ```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start tradexlog/tradex.out.log
```
Check the status of your app:
 ```bash
sudo supervisorctl status
```
To stop or restart the app:
 ```bash
sudo supervisorctl stop tradex
sudo supervisorctl restart tradex
```
Standard Output: /var/log/tradex.out.log
Errors: /var/log/tradex.err.log

### Option 2: Using systemd

#### Steps:
Create a .service file for your app:
 ```bash
sudo nano /etc/systemd/system/tradex.service
```
Add the following content:
 ```bash
[Unit]
Description=TradeX Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/app.py
WorkingDirectory=/path/to/
Restart=always
User=your-username
Group=your-group
StandardOutput=append:/var/log/tradex.log
StandardError=append:/var/log/tradex.err.log

[Install]
WantedBy=multi-user.target
```
Replace /path/to/ with the directory where your app is located, and your-username and your-group with the appropriate system user and group.

Reload systemd to recognize the new service:
 ```bash
sudo systemctl daemon-reload
```
Enable the service to start on boot:
 ```bash
sudo systemctl enable tradex.service
```
Start the service:
 ```bash
sudo systemctl start tradex.service
```
Check the service status:
 ```bash
sudo systemctl status tradex.service
```
View logs using journalctl:
 ```bash
journalctl -u tradex.service -f
```
To stop or restart the service:
 ```bash
sudo systemctl stop tradex.service
sudo systemctl restart tradex.service
```
