# TradeX

**TradeX** is a web-based trading bot dashboard designed to manage and monitor your trading positions across multiple exchanges. It supports automation, order management, and secure operations with features like authentication and configurable PIN protection for trade execution.

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

### Webhook Example
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



