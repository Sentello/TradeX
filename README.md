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

## Installation

### Prerequisites

- Python 3.8 or later
- `pip` package manager
- API keys for your supported exchanges (e.g., Bybit, Binance)

### Steps

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/tradex.git
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
    - Copy the `config.example.py` file to `config.py`.
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
To place an order via the webhook, use the following example:
```bash
curl -X POST http://<server-ip>:5000/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "sell",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.001
}'
