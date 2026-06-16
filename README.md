# Binance Futures Testnet Trading Bot

A production-grade Python CLI for placing and managing orders on Binance Futures Testnet (USDT-M).      
Built beyond the assignment spec to demonstrate real trading-system engineering: service layers, risk management, structured JSON logging with correlation IDs, SQLite order history, bracket orders, dry-run mode, and a rich terminal UI.

---

## Features
           
| Category | Feature |
|---|---|
| **Orders** | Market, Limit, Stop-Market, Take-Profit-Market, Bracket (entry + TP + SL) |
| **Account** | Balance, open positions, open orders, trade history, portfolio summary |
| **Risk** | Per-order notional cap, leverage whitelist, reduce-only enforcement |
| **Settings** | Set leverage (per-symbol), set margin type (Isolated / Crossed) |
| **UX** | Order preview + confirm prompt, dry-run mode (validates without executing) |
| **Export** | Export full order history to CSV |
| **CLI** | Typer + Rich — coloured tables, panels, help text on every command |
| **Logging** | Structured JSON logs with per-request correlation IDs |
| **Storage** | SQLite database — every order (live + dry-run) stored locally |
| **Tests** | 32 unit tests covering validators, risk manager, and order service |
| **Health** | `health` command — checks API keys, connectivity, auth, and server time |

---

## Architecture

```
CLI Layer  (cli.py + bot/cli/)
      │  Typer commands — validates input, formats output with Rich
      ▼
Order Service  (bot/core/order_service.py)
      │  Business logic: risk check → retry → execute → persist
      ▼
Risk Manager   (bot/core/risk_manager.py)
      │  Validates notional value and leverage against config limits
      ▼
Retry Handler  (bot/core/retry_handler.py)
      │  Exponential back-off for 502/network errors (1s → 2s → 4s)
      ▼
Binance Client (bot/clients/binance_client.py)
      │  Wrapper around python-binance — points to Testnet URLs
      ▼
Binance Futures Testnet
      https://testnet.binancefuture.com
```

---

## Project Structure

```
Trading_bot/
├── bot/
│   ├── cli/
│   │   ├── order_commands.py   # place-order, bracket-order, cancel-order
│   │   ├── info_commands.py    # balance, positions, open-orders, trade-history, portfolio, export
│   │   └── risk_commands.py    # set-leverage, set-margin
│   ├── clients/
│   │   ├── binance_client.py   # Thin wrapper around python-binance (testnet URL override)
│   │   └── client_factory.py   # Singleton factory — DI for service, repo, client
│   ├── core/
│   │   ├── order_service.py    # Main business logic
│   │   ├── risk_manager.py     # Notional cap + leverage validation
│   │   ├── retry_handler.py    # Exponential back-off with retryable error classification
│   │   └── correlation.py      # Per-request correlation ID (contextvars)
│   ├── models/
│   │   ├── order_models.py     # Pydantic v2 models with field validators
│   │   └── db_models.py        # SQLAlchemy 2.0 ORM models
│   ├── repository/
│   │   ├── order_repo.py       # SQLite repository
│   │   └── export_service.py   # CSV export
│   ├── utils/
│   │   ├── logging_config.py   # Structured JSON logging + correlation ID injection
│   │   ├── rich_ui.py          # All Rich tables / panels
│   │   ├── config_loader.py    # pydantic-settings + YAML config merge
│   │   └── health_check.py     # Health check logic
│   └── exceptions.py           # Custom exception hierarchy
├── config/
│   ├── testnet.yaml            # Risk limits, URLs, log settings
│   ├── development.yaml
│   └── production.yaml
├── data/
│   └── orders.db               # SQLite — auto-created on first run
├── logs/
│   └── app.log                 # Structured JSON log (auto-created)
├── reports/                    # CSV exports (auto-created)
├── tests/
│   ├── unit/
│   │   ├── test_validators.py  # 14 tests — Pydantic models + bracket logic
│   │   ├── test_risk_manager.py # 9 tests — notional cap, leverage checks
│   │   └── test_order_service.py # 7 tests — service layer with mocks
│   └── integration/
├── screenshots/                # CLI output screenshots
├── cli.py                      # Main entry point
├── .env.example                # Environment variable template
└── requirements.txt
```

---

## Setup

### 1. Get Testnet API Keys

1. Visit **https://testnet.binancefuture.com**
2. Register / log in → **API Management** → **Create**
3. Copy your API Key and Secret

### 2. Install dependencies

```bash
git clone <your-repo-url>
cd Trading_bot
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# Edit .env and add your keys:
# BINANCE_API_KEY=your_key_here
# BINANCE_SECRET_KEY=your_secret_here
```

### 4. Verify setup

```bash
python3 cli.py health
```

Expected output — all 5 checks green:
```
╭────────────────────────┬────────┬───────────────────────────╮
│ Check                  │ Status │ Detail                    │
├────────────────────────┼────────┼───────────────────────────┤
│ API Keys Configured    │  PASS  │ Keys found in environment │
│ Binance Reachable      │  PASS  │ Ping successful           │
│ API Authentication     │  PASS  │ Account info retrieved    │
│ Environment            │  PASS  │ testnet                   │
│ Server Time Sync       │  PASS  │ Server time: ...          │
╰────────────────────────┴────────┴───────────────────────────╯
╭───────────────────────────╮
│ All health checks passed. │
╰───────────────────────────╯
```

---

## Usage — Command Reference

### Place a Market Order

```bash
python3 cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### Place a Limit Order

```bash
python3 cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type LIMIT \
  --quantity 0.001 \
  --price 60000
```

### Preview Before Placing (shows estimated cost + confirm prompt)

```bash
python3 cli.py place-order \
  --symbol ETHUSDT \
  --side BUY \
  --type LIMIT \
  --quantity 0.01 \
  --price 1900 \
  --preview
```

### Dry Run (validates risk + estimates cost without executing)

```bash
python3 cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001 \
  --dry-run
```

### Bracket Order — Entry + Take-Profit + Stop-Loss

```bash
python3 cli.py bracket-order \
  --symbol BTCUSDT \
  --side BUY \
  --quantity 0.001 \
  --entry 65000 \
  --take-profit 68000 \
  --stop-loss 63000
```

### Account Information

```bash
python3 cli.py balance                                       # Wallet balances
python3 cli.py positions                                     # Open positions + unrealized PnL
python3 cli.py open-orders                                   # All open orders
python3 cli.py trade-history --symbol BTCUSDT --limit 20     # Recent fills
python3 cli.py portfolio                                     # Balance + positions combined
python3 cli.py cancel-order --symbol BTCUSDT --order-id 123  # Cancel by ID
```

### Risk & Settings

```bash
python3 cli.py set-leverage --symbol BTCUSDT --leverage 5
python3 cli.py set-margin   --symbol BTCUSDT --type ISOLATED
```

### Export & Diagnostics

```bash
python3 cli.py export-orders        # Exports to reports/orders_TIMESTAMP.csv
python3 cli.py health               # Full connectivity + auth health check
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `BINANCE_API_KEY` | — | **Required.** Testnet API key |
| `BINANCE_SECRET_KEY` | — | **Required.** Testnet secret key |
| `ENVIRONMENT` | `testnet` | `testnet`, `development`, or `production` |
| `MAX_ORDER_SIZE` | `1000` | Max order notional in USDT (risk limit) |
| `MAX_LEVERAGE` | `10` | Max leverage multiplier |
| `DEFAULT_RETRIES` | `3` | API retry attempts |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Logging

All events are written to **`logs/app.log`** as structured JSON with a per-request correlation ID:

```json
{
  "timestamp": "2026-06-03 17:09:52,148",
  "level": "INFO",
  "name": "bot.core.order_service",
  "message": "ORDER_PLACED",
  "order_id": 13986610780,
  "status": "NEW",
  "latency_ms": "230",
  "correlation_id": "REQ-20260603-173951-EA4C3D",
  "service": "trading_bot"
}
```

Every CLI invocation gets a unique `REQ-YYYYMMDD-HHMMSS-XXXXXX` correlation ID. All log lines for that invocation (risk check, API call, DB save) share the same ID — making end-to-end tracing trivial.

---

## Error Handling

| Error Type | Behaviour |
|---|---|
| Invalid input (wrong side, missing price for LIMIT) | Pydantic validation — clear message before any API call |
| Risk limit exceeded | Rejected before API call with notional / leverage detail |
| Binance API error | Displayed with `[code] message` |
| 502 / rate-limit from Binance | Auto-retried up to 3 times with 1s → 2s → 4s back-off |
| Network failure (timeout, connection reset) | Auto-retried with same back-off |
| Non-retryable Binance error | Raised immediately with full error detail |

---

## Running Tests

```bash
python3 -m pytest tests/ -v
```

```
32 passed in 0.44s
```

Test coverage:

| File | Tests | What is verified |
|---|---|---|
| `test_validators.py` | 14 | Symbol uppercasing, quantity > 0, price required for LIMIT, stop_price required for STOP_MARKET, bracket TP/SL direction logic |
| `test_risk_manager.py` | 9 | Notional cap, exact-limit edge case, leverage whitelist, zero/negative quantity |
| `test_order_service.py` | 7 | Full market order flow, dry-run isolation (API never called), bracket places 3 legs, cancel delegates correctly |

---

## Design Decisions

- **Typer + Rich** — type-safe CLI; Rich gives recruiter-friendly coloured output with zero extra code
- **Pydantic v2** — validation at the model boundary, not scattered `if` checks throughout the code
- **Service layer + repository pattern** — CLI is thin; all business logic in `OrderService`; storage in `OrderRepository`; both are independently unit-testable with mocks
- **Correlation IDs** — every request tagged end-to-end via Python `contextvars`; log lines from the same invocation share the same ID
- **SQLite** — zero-config persistent order history; every order (live + dry-run) stored for audit / CSV export
- **Exponential back-off** — 502 / rate-limit / network errors automatically retried; non-retryable Binance codes surface immediately
- **Dry-run mode** — validates risk + estimates cost without touching the exchange; useful for CI/testing and reviewing before real orders
- **Config layering** — `.env` overrides YAML; `config/testnet.yaml` sets risk limits and URLs; switching to production requires only changing `ENVIRONMENT=production`

---

## Assumptions

- Only **Binance Futures Testnet (USDT-M)** is tested; `config/production.yaml` exists but is not validated against live keys
- `quantity` must respect the symbol's step size — for BTCUSDT on testnet the minimum is `0.001`
- The testnet occasionally returns `502 Bad Gateway`; the retry handler catches and retries these automatically (up to 3 attempts with back-off)
- Bracket orders place 3 separate independent orders; if no open position exists when the TP/SL legs are sent, Binance may reject them with a `reduce-only` error
