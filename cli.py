#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot
Entry point — registers all CLI commands under a single Typer app.
"""
import typer  

from bot.cli.info_commands import (
    balance,     
    export_orders,
    open_orders,
    portfolio,
    positions,
    trade_history,
)
from bot.cli.order_commands import bracket_order, cancel_order, interactive_menu, place_order, twap_order
from bot.cli.risk_commands import set_leverage, set_margin
from bot.core.correlation import set_correlation_id
from bot.utils.config_loader import get_settings
from bot.utils.health_check import health
from bot.utils.logging_config import setup_logging

app = typer.Typer(
    name="trading-bot",
    help=(
        "[bold cyan]Binance Futures Testnet Trading Bot[/bold cyan]\n\n"
        "Professional CLI for placing, managing, and monitoring futures orders "
        "on the Binance Testnet environment."
    ),
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# ── Order Commands ────────────────────────────────────────────────────────────
app.command("place-order",   help="Place a futures order (MARKET, LIMIT, STOP_MARKET, etc.)")(place_order)
app.command("bracket-order", help="Entry + take-profit + stop-loss in one command")(bracket_order)
app.command("twap-order",    help="TWAP: split a large order into equal time-sliced market orders")(twap_order)
app.command("cancel-order",  help="Cancel an open order by ID")(cancel_order)
app.command("menu",          help="Interactive guided menu — place orders & view account")(interactive_menu)

# ── Account / Info Commands ───────────────────────────────────────────────────
app.command("balance", help="Show futures wallet balance")(balance)
app.command("positions", help="Show open futures positions")(positions)
app.command("open-orders", help="List open orders")(open_orders)
app.command("trade-history", help="Show recent trade history")(trade_history)
app.command("portfolio", help="Portfolio summary: balance + positions + PnL")(portfolio)
app.command("export-orders", help="Export local order history to CSV")(export_orders)

# ── Risk / Settings Commands ──────────────────────────────────────────────────
app.command("set-leverage", help="Set leverage for a symbol")(set_leverage)
app.command("set-margin", help="Set margin type (ISOLATED / CROSSED) for a symbol")(set_margin)

# ── Diagnostics ───────────────────────────────────────────────────────────────
app.command("health", help="Run health checks (connectivity, auth, testnet)")(health)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Initialise logging and correlation ID for every invocation."""
    cid = set_correlation_id()
    settings = get_settings()
    setup_logging(log_level=settings.log_level)


if __name__ == "__main__":
    app()
