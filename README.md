# TradeX

**TradeX** is an advanced, web-based trading bot designed to automate cryptocurrency trading across major exchanges like **Binance** and **Bybit**. It integrates seamlessly with **TradingView webhooks** and **email alerts**, enabling real-time trade execution based on custom signals. The system provides a secure and user-friendly dashboard for managing open positions, pending orders, and executing trades.

Key features include:
- Multi-exchange support (Bybit, Binance).
- Secure authentication and PIN protection for trade execution.
- Real-time monitoring of open positions and pending orders.
- Support for both webhook and email-based signal ingestion.
- Containerized deployment using Docker.

---

## Table of Contents
- [Features](#features)
- [Screenshots](#screenshots)
- [Supported Exchanges](#supported-exchanges)
- [Supported Modes](#supported-modes)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Running TradeX as a Service](#running-tradex-as-a-service)
- [Running TradeX in Docker](#running-tradex-in-docker) recommended
- [Using Nginx as a Proxy for Webhooks](#using-nginx-as-a-proxy-for-webhooks)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [Known Issues](#known-issues)
- [License](#license)
- [Support the Project](#support-the-project)

---

## Features
- **Multi-Exchange Support**: Seamlessly integrates with **Bybit and Binance Futures**.
- **Order Management**: Cancel positions and orders directly from the dashboard.
- **Real-Time Monitoring**: View all active and pending orders in a user-friendly interface.
- **Close All Positions**: Quickly close all open positions with a single click.
- **Signal Ingestion**: Supports both **webhook** and **email-based trade signals**.
- **Authentication**: Secure dashboard with password protection.
- **PIN Protection**: Add an extra layer of **security by requiring a PIN** for order execution via webhooks or emails.
- **Logging**: Comprehensive logging for debugging and monitoring.

---

## Screenshots
![App_Screenshot](https://github.com/user-attachments/assets/79bd5123-c81c-49b1-9e8e-5d064698f20d)

---

## Supported Exchanges
- **Bybit Futures**
- **Binance Futures** (not fully tested)
- Additional exchanges can be added upon request or contributed via pull requests

---
Here’s the combined and enhanced version of your **Supported Modes** section, incorporating the additional context about TradingView's webhook reliability and how to configure alerts effectively:

---

## Supported Modes

TradeX offers two distinct modes for receiving trade signals: **Webhook Mode** and **Email Mode**. These modes provide flexibility depending on your infrastructure, preferences, and technical setup. You can configure the mode using the `MODE` environment variable in the `.env` file (`MODE=webhook`, `MODE=email`, or `MODE=both`).

---

### 1. Webhook Mode
**Webhook Mode** allows TradeX to listen for real-time trade signals sent via HTTP POST requests. This mode is ideal for users with stable internet connections, a public IP address, and access to domain hosting.

#### Key Features:
- **Real-Time Execution**: Signals are processed instantly as soon as they are received.
- **Low Latency**: Minimal delay between signal generation (e.g., from TradingView) and order execution.
- **Secure Authentication**: Requires a configurable PIN (`WEBHOOK_PIN`) to ensure only authorized signals are processed.
- **Integration with TradingView**: Easily integrates with TradingView alerts using webhooks.

#### Requirements:
- A **public IP address** or domain name pointing to your server.
- A **stable internet connection** to ensure uninterrupted communication.
- Ports `80` or `443` must be open and accessible (or proxied via Nginx/Apache).
- Optional: SSL/TLS certificate for secure HTTPS communication.

#### Use Case:
If you have a dedicated server or VPS with a public IP and want the fastest possible execution of trades, **Webhook Mode** is the best choice. It’s particularly suited for advanced traders who rely on real-time market data and fast execution.

#### Important Note:
It’s worth noting that **TradingView webhooks are not guaranteed to be delivered without delays or failures**. While TradingView provides webhook functionality for sending alerts, there are inherent limitations:
- **Delivery Delays**: Webhooks may experience delays due to high volatility.
- **Response Time Requirements**: TradingView expects a quick response (typically within milliseconds). If your application takes too long to respond, TradingView may retry the request or consider it failed.
- **No Delivery Guarantees**: There are numerous reports online of missed or failed webhook deliveries.

To mitigate these issues, consider using **Email Mode** as a fallback or running TradeX in **Dual Mode** (`MODE=both`) for redundancy.

---

### 2. Email Mode
**Email Mode** allows TradeX to process trade signals sent via email. This mode is perfect for users who do not have a public IP, stable internet, or access to domain hosting. Instead of relying on HTTP requests, TradeX monitors an email inbox for unread emails containing trade signals.

#### Key Features:
- **No Public IP Required**: Works entirely through email, so there’s no need for port forwarding or domain hosting.
- **Offline-Friendly**: Even if your internet connection drops temporarily, emails will be queued by the email provider and processed once the connection is restored.
- **Simple Setup**: Just configure your email credentials (IMAP) and send trade signals via email.
- **Flexible Signal Format**: Trade signals can be embedded in the email subject line as JSON.

#### Requirements:
- An email account with IMAP access enabled.
- Properly formatted trade signals in the email subject line (JSON format).
- No need for a public IP, domain, or open ports.

#### Use Case:
If you don’t have access to a public IP or stable internet, **Email Mode** is the ideal solution. It’s also a great fallback option for users who want redundancy in case their webhook setup fails.

---

### 3. Dual Mode (Both Webhook and Email)
For maximum flexibility, TradeX supports running in **Dual Mode** (`MODE=both`). In this mode, TradeX listens for signals from both webhooks and emails simultaneously. This ensures you never miss a trade signal, regardless of your connectivity or infrastructure.

#### Benefits:
- **Versatility**: Combine the speed of webhooks with the reliability of email-based signals.
- **Customizable Workflow**: Use webhooks for high-priority, real-time signals and emails for less time-sensitive trades.

#### Example Use Case:
A trader uses **TradingView webhooks** for real-time signals during active trading hours but switches to **email alerts** for overnight or low-priority trades. By enabling both modes, they ensure continuous operation without manual intervention.

#### Important Note:
When running in **Dual Mode**, it’s important to configure your TradingView alerts carefully to avoid duplicate signal processing:
- **Tick "Send Email" Only**: Use this for signals that don't require instant execution but need guaranteed delivery.
- **Tick "Webhook URL" Only**: Use this for signals that require fast execution.
- **Avoid Ticking Both Boxes**: If both options are selected, the same signal will be sent twice—once via webhook and once via email. This could result in duplicate orders being placed.

TradeX does not currently include a deduplication mechanism, so it’s up to the user to configure TradingView alerts appropriately. For example:
- High-priority signals (e.g., scalping strategies) can be sent via webhook for fast execution.
- Lower-priority signals (e.g., long-term position adjustments) can be sent via email for guaranteed delivery.

---

### How to Configure the Mode
Set the `MODE` variable in your `.env` file to one of the following options:
- `MODE=webhook`: Only listen for webhook signals.
- `MODE=email`: Only process email signals.
- `MODE=both`: Listen for both webhook and email signals simultaneously.


---

### Additional Notes
- **Security**: Both modes support PIN protection (`WEBHOOK_PIN`) to prevent unauthorized signal processing.
- **Testing**: You can test both modes independently to ensure they work as expected before deploying in production.


---

## Installation

### Prerequisites
- Python 3.8 or later
- `pip` package manager
- API keys for supported exchanges (e.g., Bybit, Binance)
- Docker (optional, for containerized deployment)

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Sentello/tradex.git
   cd tradex
   ```

2. **Set Up a Virtual Environment** (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   - Rename `.env.example` to `.env` or create a new `.env` file.
   - Add your exchange API keys, dashboard password, webhook PIN, and other required configurations.

5. **Run the Application Locally**:
   ```bash
   python main.py
   ```

6. **Access the Dashboard**:
   - Open your browser and go to `http://localhost:5000`.

---

## Configuration

The following environment variables must be configured in the `.env` file:

| Variable               | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| `DASHBOARD_PASSWORD`   | Password for accessing the dashboard.                                      |
| `WEBHOOK_PIN`          | PIN for securing webhook trade signals.                                    |
| `BYBIT_API_KEY`        | API key for Bybit.                                                         |
| `BYBIT_API_SECRET`      | API secret for Bybit.                                                      |
| `BINANCE_API_KEY`       | API key for Binance.                                                       |
| `BINANCE_API_SECRET`    | API secret for Binance.                                                    |
| `MODE`                 | Signal ingestion mode: `"webhook"`, `"email"`, or `"both"`.                |
| `IMAP_SERVER`          | IMAP server address (e.g., `imap.gmail.com`).                              |
| `IMAP_PORT`            | IMAP server port (usually `993` for SSL).                                  |
| `IMAP_EMAIL`           | Email address for receiving trade signals.                                |
| `IMAP_PASSWORD`        | Password for the email account.                                           |



---

## Usage

### Webhook Example (Testing with `curl`)
The webhook listener runs on port `5005`. Use the following examples to test placing orders via webhooks:

#### Place a Market Order
```bash
curl -X POST http://localhost:5005/webhook \
-H "Content-Type: application/json" \
-d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "buy",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.01
}'
```

```bash
curl -X POST http://<server-ip>:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "sell",
    "ORDER_TYPE": "market",
    "QUANTITY": 0.001
}'
```

#### Place a Limit Order
```bash
curl -X POST http://localhost:5005/webhook \
-H "Content-Type: application/json" \
-d '{
    "PIN": "123456",
    "EXCHANGE": "binance",
    "SYMBOL": "ETHUSDT",
    "SIDE": "sell",
    "ORDER_TYPE": "limit",
    "QUANTITY": 0.5,
    "PRICE": 2000.50
}'
```
```bash
curl -X POST http://<server-ip>:5005/webhook -H "Content-Type: application/json" -d '{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "buy",
    "ORDER_TYPE": "limit",
    "QUANTITY": 0.05,
    "PRICE": 91000
}'
```

#### TradingView Webhook Integration
When integrating with TradingView, ensure placeholders are properly quoted to avoid JSON parsing errors. Example:
```json
{
    "PIN": "123456",
    "EXCHANGE": "bybit",
    "SYMBOL": "BTCUSDT",
    "SIDE": "{{strategy.order.action}}",
    "ORDER_TYPE": "market",
    "QUANTITY": "{{strategy.order.contracts}}"
}
```

**Note**: TradingView requires webhooks to use ports `80` or `443`. Use Nginx as a reverse proxy to forward requests to port `5005`. I strongly recommend using port 80 to avoid potential SSL-related complications and suggest using Nginx as a proxy for this setup.

---

## Running TradeX as a Service

You can run TradeX as a service using either **Supervisor** or **systemd**.
See the [HOWTO.md](HOWTO.md) file for details.

---

## Running TradeX in Docker

1. Build and start the application:
   ```bash
   docker-compose build --no-cache
   docker-compose up --build -d
   ```

   or use `build_and_run.sh`.

2. Check the status of the containers:
   ```bash
   docker ps | grep tradex
   ```

3. View logs:
   ```bash
   docker-compose logs -f
   ```

4. Stop the application:
   ```bash
   docker-compose down
   ```

---

## Using Nginx as a Proxy for Webhooks

You need to expose the webhook listener on port `80` or `443`, use Nginx as a reverse proxy:

1. Install Nginx:
   ```bash
   sudo apt update
   sudo apt install nginx
   ```

2. Create a new configuration file:
   ```bash
   sudo nano /etc/nginx/sites-available/tradex-webhook
   ```

3. Add the following content:
   ```nginx
   server {
       listen 80;
       server_name your.domain.com;

       location /webhook {
           proxy_pass http://127.0.0.1:5005;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

4. Enable the configuration and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/tradex-webhook /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. Update Your Webhook URL: 
When sending webhooks (from TradingView), use the URL pointing to your domain or server IP on port 80: `http://your.domain.com/webhook`

---

## Troubleshooting

- **Error: "No exchanges loaded!"**: Ensure your API keys are correctly configured in `.env`.
- **Webhook Errors**: Verify the `WEBHOOK_PIN` matches the one in your `.env` file.
- **Email Reader Issues**: Check IMAP credentials and ensure the email account allows IMAP access.
- **Dashboard Not Accessible**: Ensure the Flask app is running and the correct port (`5000`) is exposed.

For further assistance, check the logs in the `logs/` directory.

---

## Security Best Practices

- **Restrict Access**: Limit access to the dashboard by binding it to `127.0.0.1` or using a firewall.
- **Regularly Rotate API Keys**: Periodically update your exchange API keys to minimize risks.

---

## Known Issues

- **Binance Futures**: Support for Binance Futures is not fully tested.
- **Email Parsing**: The email reader assumes trade signals are always in the subject line. This may fail if the format changes in the future.
- **Rate Limits**: High-frequency trading may trigger rate limits on exchanges.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Support the Project
If you find this project useful and would like to support me, consider making a donation.

### Scan to Donate

#### Bitcoin (BTC)
![Bitcoin QR Code](path/to/bitcoin_qr_code.png)

#### Ethereum (ETH)
![Ethereum QR Code](path/to/ethereum_qr_code.png)

Thank You!

---
<img src="https://media1.tenor.com/m/ofDuH0hvGh8AAAAd/so-what-do-you-think.gif" width="200" title="Ray Romano saying What do you think?" alt="Ray Romano saying What do you think?"/>