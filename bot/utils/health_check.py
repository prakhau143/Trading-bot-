import logging
from typing import Dict, Tuple

import typer

from bot.clients.binance_client import TradingClient
from bot.utils.config_loader import get_settings
from bot.utils.rich_ui import console, print_health_table

logger = logging.getLogger(__name__)


def run_health_checks(client: TradingClient) -> Dict[str, Tuple[bool, str]]:
    settings = get_settings()
    checks: Dict[str, Tuple[bool, str]] = {}

    # 1. API keys present
    key_ok = bool(settings.binance_api_key and settings.binance_secret_key)
    checks["API Keys Configured"] = (key_ok, "Keys found in environment" if key_ok else "Missing in .env")

    # 2. Binance connectivity
    ping_ok = client.ping()
    checks["Binance Reachable"] = (ping_ok, "Ping successful" if ping_ok else "Connection failed")

    # 3. Authentication (account access)
    auth_ok = False
    auth_detail = "Skipped (connectivity failed)"
    if ping_ok and key_ok:
        try:
            client.get_account_info()
            auth_ok = True
            auth_detail = "Account info retrieved"
        except Exception as exc:
            auth_detail = str(exc)
    checks["API Authentication"] = (auth_ok, auth_detail)

    # 4. Environment
    env = settings.environment
    checks["Environment"] = (True, env)

    # 5. Server time sync
    time_ok = False
    time_detail = "Skipped"
    if ping_ok:
        try:
            server_time = client.get_server_time()
            time_ok = True
            time_detail = f"Server time: {server_time}"
        except Exception as exc:
            time_detail = str(exc)
    checks["Server Time Sync"] = (time_ok, time_detail)

    return checks


def health():
    """Check Binance connectivity, API keys, and system health."""
    from bot.clients.client_factory import get_trading_client

    console.print("\n[bold cyan]Running health checks...[/bold cyan]\n")
    client = get_trading_client()
    checks = run_health_checks(client)
    print_health_table(checks)
    console.print()
