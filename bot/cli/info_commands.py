import logging
from typing import Annotated, Optional

import typer

from bot.clients.client_factory import get_order_repository, get_trading_client
from bot.exceptions import TradingBotError
from bot.repository.export_service import ExportService
from bot.utils.rich_ui import (
    console,
    print_balance_table,
    print_error,
    print_info,
    print_open_orders_table,
    print_portfolio_summary,
    print_positions_table,
    print_success,
    print_trade_history_table,
)

logger = logging.getLogger(__name__)


def balance():
    """Show current futures wallet balance."""
    client = get_trading_client()
    try:
        balances = client.get_account_balance()
        print_balance_table(balances)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def positions(
    symbol: Annotated[Optional[str], typer.Option("--symbol", "-s", help="Filter by trading pair")] = None,
):
    """Show all open futures positions."""
    client = get_trading_client()
    try:
        pos = client.get_position_information(symbol=symbol.upper() if symbol else None)
        print_positions_table(pos)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def open_orders(
    symbol: Annotated[Optional[str], typer.Option("--symbol", "-s", help="Filter by trading pair")] = None,
):
    """List all open futures orders."""
    client = get_trading_client()
    try:
        orders = client.get_open_orders(symbol=symbol.upper() if symbol else None)
        print_open_orders_table(orders)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def trade_history(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Number of recent trades to show")] = 20,
):
    """Show recent trade history for a symbol."""
    client = get_trading_client()
    try:
        trades = client.get_account_trades(symbol=symbol.upper(), limit=limit)
        print_trade_history_table(trades)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def portfolio():
    """Show portfolio summary: balance, open positions, and unrealized PnL."""
    client = get_trading_client()
    try:
        balances = client.get_account_balance()
        pos = client.get_position_information()
        print_portfolio_summary(balances, pos)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def export_orders(
    symbol: Annotated[Optional[str], typer.Option("--symbol", "-s", help="Filter by symbol")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="Export format (csv)")] = "csv",
):
    """Export local order history to CSV."""
    repo = get_order_repository()
    try:
        orders = repo.get_by_symbol(symbol.upper()) if symbol else repo.get_all()
        if not orders:
            print_info("No orders found to export.")
            raise typer.Exit(0)

        svc = ExportService()
        filename = svc.export_orders_csv(orders)
        print_success(f"Exported {len(orders)} order(s) to: {filename}")
    except typer.Exit:
        raise
    except Exception as exc:
        print_error(f"Export failed: {exc}")
        raise typer.Exit(1)
