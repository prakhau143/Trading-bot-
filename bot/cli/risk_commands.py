import logging
from typing import Annotated

import typer

from bot.clients.client_factory import get_risk_manager, get_trading_client
from bot.exceptions import BinanceAPIError, RiskLimitExceeded, TradingBotError
from bot.utils.rich_ui import console, print_error, print_success, print_warning

logger = logging.getLogger(__name__)

VALID_MARGIN_TYPES = ("ISOLATED", "CROSSED")


def set_leverage(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    leverage: Annotated[int, typer.Option("--leverage", "-l", help="Leverage multiplier, e.g. 10")],
):
    """Set leverage for a futures symbol (with risk-limit validation)."""
    risk = get_risk_manager()
    try:
        risk.validate_leverage(leverage)
    except RiskLimitExceeded as exc:
        print_error(f"Risk Limit: {exc}")
        raise typer.Exit(1)

    client = get_trading_client()
    try:
        response = client.change_leverage(symbol=symbol.upper(), leverage=leverage)
        print_success(
            f"Leverage set to [bold]{response.get('leverage', leverage)}x[/bold] "
            f"for [cyan]{response.get('symbol', symbol.upper())}[/cyan]"
        )
        console.print(
            f"  [dim]Max notional at this leverage: "
            f"{response.get('maxNotionalValue', 'N/A')} USDT[/dim]"
        )
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def set_margin(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    margin_type: Annotated[str, typer.Option("--type", "-t", help="ISOLATED or CROSSED")],
):
    """Set margin type (ISOLATED or CROSSED) for a futures symbol."""
    margin_upper = margin_type.upper()
    if margin_upper not in VALID_MARGIN_TYPES:
        print_error(f"Invalid margin type '{margin_type}'. Must be one of: {VALID_MARGIN_TYPES}")
        raise typer.Exit(1)

    client = get_trading_client()
    try:
        client.change_margin_type(symbol=symbol.upper(), margin_type=margin_upper)
        print_success(
            f"Margin type set to [bold]{margin_upper}[/bold] for [cyan]{symbol.upper()}[/cyan]"
        )
    except TradingBotError as exc:
        # Binance returns an error if margin type is already set — treat that gracefully
        if "No need to change margin type" in str(exc):
            print_warning(
                f"Margin type is already [bold]{margin_upper}[/bold] for {symbol.upper()}."
            )
        else:
            print_error(f"Error: {exc}")
            raise typer.Exit(1)
