# TradeX

**TradeX** is an advanced, web-based trading bot designed to automate cryptocurrency trading across major exchanges like **Binance** and **Bybit**. It integrates seamlessly with **TradingView webhooks** and **email alerts**, enabling real-time trade execution based on custom signals. The system provides a secure and user-friendly dashboard for managing open positions, pending orders, and executing trades.

**Key features include:**
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

<img src="https://github.com/user-attachments/assets/ce33b5e5-0d4d-411e-9821-50e12414a7f2" alt="image" width="100px">   
<img src="https://github.com/user-attachments/assets/ab0da857-493e-4824-ab3e-0d87fb05a0b0" alt="image" width="100px">

- **Bybit Futures**
- **Binance Futures** (not fully tested)
- Additional exchanges can be added upon request or contributed via pull requests

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

  ![image](https://github.com/user-attachments/assets/6d3f4a4f-dde8-42ee-b853-f4d8b5801bea)

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
- Python 3.10 or later (every dependency requires `>=3.10`; the Docker image uses 3.14)
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

   Alternatively, you can use the `generate_credentials.py` script to generate secure credential values:
   ```bash
   python generate_credentials.py
   ```
   This will generate `FLASK_SECRET_KEY`, `WEBHOOK_PIN`, and a bcrypt `DASHBOARD_PASSWORD` hash to copy into your `.env` file. Paste the printed hash, not the password you typed.

5. **Run the Application Locally**:
   ```bash
   python main.py
   ```

6. **Access the Dashboard**:
   - Open your browser and go to `http://localhost:5000`.

### Running the Tests

The test suite covers signal validation, webhook authentication, position
closing and the dashboard login. `pytest` is not a runtime dependency, so
install it separately:

```bash
pip install pytest
pytest
```

To check the dependencies for known vulnerabilities:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

---

## Configuration

### Two different credentials

TradeX has **two separate secrets**, and mixing them up is the most common
setup mistake:

| Credential | Authenticates | Where you enter it |
|---|---|---|
| `WEBHOOK_PIN` | Incoming trade signals | Inside the JSON body of your TradingView alert (and email alerts) |
| `DASHBOARD_PASSWORD` | You, in a browser | The dashboard login form |

The webhook PIN will **not** log you into the dashboard. Use different
values for the two: the PIN travels in plaintext inside alert bodies, so
it should never also unlock the control panel.

### Required

The app refuses to start if any of these are missing, rather than falling
back to an insecure default. Generate all three with
`python generate_credentials.py`.

| Variable | Description |
|---|---|
| `FLASK_SECRET_KEY` | Signs dashboard session cookies. A predictable value lets anyone forge a login. |
| `DASHBOARD_PASSWORD` | **bcrypt hash** of the dashboard password, not the password itself. |
| `WEBHOOK_PIN` | Authenticates trade signals. This is the only credential on `/webhook`, so make it long and random. |

### Exchange API credentials

| Variable | Default | Description |
|---|---|---|
| `BYBIT_API_KEY` | — | API key for Bybit. |
| `BYBIT_API_SECRET` | — | API secret for Bybit. |
| `BINANCE_API_KEY` | — | API key for Binance. |
| `BINANCE_API_SECRET` | — | API secret for Binance. |
| `EXCHANGES` | `bybit,binance` | Which exchanges to enable. An exchange is only loaded if it is listed here *and* has both a key and a secret. |

### Signal ingestion

| Variable | Default | Description |
|---|---|---|
| `MODE` | `webhook` | `webhook`, `email`, or `both`. In `webhook` mode the email reader exits cleanly; in `email` mode `/webhook` returns `503`. |

### Email (IMAP) — required when `MODE` includes email

| Variable | Default | Description |
|---|---|---|
| `IMAP_SERVER` | — | IMAP server address (e.g. `imap.gmail.com`). |
| `IMAP_PORT` | `993` | IMAP server port. |
| `IMAP_EMAIL` | — | Mailbox receiving trade signals. |
| `IMAP_PASSWORD` | — | Password for that mailbox. |
| `IMAP_USE_SSL` | `true` | Use implicit SSL. When `false`, STARTTLS is used instead. |
| `IMAP_CHECK_INTERVAL` | `15` | Seconds between inbox checks. |

### Webhook security

| Variable | Default | Description |
|---|---|---|
| `WEBHOOK_ALLOWED_IPS` | *(empty — any address)* | Comma-separated IPs or CIDR blocks allowed to reach `/webhook`. **The most effective protection available**: restricting to TradingView's published IPs removes brute force as a concern entirely. |
| `WEBHOOK_MAX_FAILURES` | `5` | Bad PINs from one address before it is locked out. |
| `WEBHOOK_LOCKOUT_SECONDS` | `300` | How long that lockout lasts. Applied per source IP, never endpoint-wide, so an attacker cannot stop your real alerts by sending junk. |
| `TRUST_PROXY_HEADERS` | `false` | Read the client address from `X-Forwarded-For`. **Only enable behind a reverse proxy that overwrites the header** — if the app is directly exposed, a client can forge it and bypass both the allowlist and the lockout. |

### Dashboard and session

| Variable | Default | Description |
|---|---|---|
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` when serving the dashboard over HTTPS, so the session cookie is never sent in cleartext. |
| `SESSION_LIFETIME_HOURS` | `12` | How long a dashboard login stays valid. |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed logins from one address before lockout. |
| `LOGIN_LOCKOUT_SECONDS` | `300` | How long that lockout lasts. |

### Network

| Variable | Default | Description |
|---|---|---|
| `DASHBOARD_HOST` | `0.0.0.0` | Dashboard bind address. |
| `DASHBOARD_PORT` | `5000` | Dashboard port. |
| `WEBHOOK_HOST` | `0.0.0.0` | Webhook bind address. |
| `WEBHOOK_PORT` | `5005` | Webhook port. |

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

- **The app refuses to start**: the error names the missing variable. `FLASK_SECRET_KEY`, `WEBHOOK_PIN` and `DASHBOARD_PASSWORD` are required, and `DASHBOARD_PASSWORD` must be a bcrypt hash — run `python generate_credentials.py`.
- **Cannot log into the dashboard**: check you are not entering the `WEBHOOK_PIN`. It is a separate credential and will never work on the login form — see [Two different credentials](#two-different-credentials). If you have lost the password, generate a new hash and replace `DASHBOARD_PASSWORD` in `.env`.
- **Login returns "Too many failed attempts"**: you have hit `LOGIN_MAX_ATTEMPTS` from this address. Wait `LOGIN_LOCKOUT_SECONDS` (5 minutes by default), or restart the dashboard to clear the counter, which is held in memory.
- **Error: "No exchanges loaded!"**: ensure your API keys are set in `.env` and that the exchange is listed in `EXCHANGES`.
- **Webhook returns 403**: the `PIN` in the alert body does not match `WEBHOOK_PIN`, or the sender's address is not in `WEBHOOK_ALLOWED_IPS`.
- **Webhook returns 429**: that source IP is locked out after repeated bad PINs. See `WEBHOOK_LOCKOUT_SECONDS`.
- **Webhook returns 503**: `MODE` does not include `webhook`.
- **Email Reader Issues**: check IMAP credentials and ensure the email account allows IMAP access.
- **Dashboard Not Accessible**: ensure the Flask app is running and the correct port (`5000`) is exposed.

For further assistance, check the logs in the `logs/` directory. Each service writes its own file (`webhook.log`, `dashboard.log`, `email_reader.log`), also viewable from the dashboard.

---

## Security Best Practices

- **Restrict who can reach the webhook**: set `WEBHOOK_ALLOWED_IPS` to TradingView's published source IPs. This is the single most effective control, because it removes brute-forcing the PIN as a possibility rather than merely slowing it down.
- **Use a long, random `WEBHOOK_PIN`**: it is the only credential on an endpoint that places real orders. A 6-digit numeric PIN is a keyspace of 1,000,000 — crackable in about an hour at 100 requests/second. `python generate_credentials.py` produces a 43-character one.
- **Never reuse the PIN as the dashboard password**: the PIN travels in plaintext inside alert bodies and across mail servers.
- **Restrict access to the dashboard**: bind it to `127.0.0.1` or use a firewall. It has no TLS of its own, so the password and session cookie cross the network in cleartext unless you put it behind a reverse proxy.
- **Serve the dashboard over HTTPS** and set `SESSION_COOKIE_SECURE=true` once you do.
- **Regularly rotate API keys**: periodically update your exchange API keys to minimize risks.
- **Restrict exchange API key permissions**: enable trading, but disable withdrawals and restrict the key to your server's IP where the exchange supports it.
- **Never commit `.env`**: it is gitignored and excluded from the Docker image. Secrets are supplied at runtime via `env_file`.
- **Audit dependencies periodically**: `pip-audit -r requirements.txt`.

---

## Known Issues

- **Binance Futures**: Support for Binance Futures is not fully tested.
- **Email Parsing**: The email reader assumes trade signals are always in the subject line. This may fail if the format changes in the future.
- **Rate Limits**: High-frequency trading may trigger rate limits on exchanges.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏Support the Project
If you find this project useful and would like to support me, consider making a donation.

### Scan to Donate

#### Bitcoin (BTC SegWit)
`bc1qm4zv6fwxuf8n5sdkrfc6ylxyhs6vhmkkvxcjf0`

![image](https://github.com/user-attachments/assets/5476d500-b71a-4d4d-b688-6dcc35b2a858)


#### Ethereum (ETH ERC20)
`0xaa0ab64b0cdecb527eb5e7d5fc9ed94044c37a4c`

![image](https://github.com/user-attachments/assets/21981a90-50f2-46ef-aa29-7c68c9d1742b)


Thank You!

---
<img src="https://media1.tenor.com/m/ofDuH0hvGh8AAAAd/so-what-do-you-think.gif" width="200" title="Ray Romano saying What do you think?" alt="Ray Romano saying What do you think?"/>
