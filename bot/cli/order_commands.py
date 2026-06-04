import logging
import time
from typing import Annotated, Optional

import typer
from rich.prompt import Confirm, FloatPrompt, Prompt

from bot.clients.client_factory import get_order_service, get_trading_client
from bot.exceptions import BinanceAPIError, RiskLimitExceeded, TradingBotError, ValidationError
from bot.models.order_models import BracketOrderRequest, OrderRequest, OrderSide, OrderType
from bot.utils.rich_ui import (
    console,
    print_bracket_order_result,
    print_error,
    print_order_preview,
    print_order_result,
    print_success,
    print_warning,
)

logger = logging.getLogger(__name__)


def place_order(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    side: Annotated[str, typer.Option("--side", help="BUY or SELL")],
    order_type: Annotated[str, typer.Option("--type", "-t", help="MARKET, LIMIT, STOP_MARKET, etc.")],
    quantity: Annotated[float, typer.Option("--quantity", "-q", help="Order quantity in base asset")],
    price: Annotated[Optional[float], typer.Option("--price", "-p", help="Limit price (required for LIMIT orders)")] = None,
    stop_price: Annotated[Optional[float], typer.Option("--stop-price", help="Stop price (required for STOP_MARKET / TAKE_PROFIT_MARKET)")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate order without sending to Binance")] = False,
    preview: Annotated[bool, typer.Option("--preview", help="Show order preview and confirm before placing")] = False,
):
    """Place a futures order: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET, and more."""
    try:
        request = OrderRequest(
            symbol=symbol,
            side=OrderSide(side.upper()),
            order_type=OrderType(order_type.upper()),
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except Exception as exc:
        print_error(f"Validation Error: {exc}")
        raise typer.Exit(1)

    service = get_order_service()

    if preview:
        try:
            mark_price = get_trading_client().get_mark_price(request.symbol)
            print_order_preview(request, mark_price)
            if not typer.confirm("\nProceed with this order?"):
                print_warning("Order cancelled by user.")
                raise typer.Exit(0)
        except TradingBotError as exc:
            print_error(f"Preview failed: {exc}")
            raise typer.Exit(1)

    try:
        response = service.place_order(request, dry_run=dry_run)
        print_order_result(response, dry_run=dry_run)
    except RiskLimitExceeded as exc:
        print_error(f"Risk Limit Exceeded: {exc}")
        raise typer.Exit(1)
    except BinanceAPIError as exc:
        print_error(f"Binance API Error: {exc}")
        raise typer.Exit(1)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def bracket_order(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    side: Annotated[str, typer.Option("--side", help="BUY or SELL")],
    quantity: Annotated[float, typer.Option("--quantity", "-q", help="Order quantity")],
    entry_price: Annotated[float, typer.Option("--entry", help="Entry limit price")],
    take_profit: Annotated[float, typer.Option("--take-profit", help="Take-profit trigger price")],
    stop_loss: Annotated[float, typer.Option("--stop-loss", help="Stop-loss trigger price")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate without executing")] = False,
):
    """Place a bracket order: entry limit + take-profit + stop-loss in one command."""
    try:
        req = BracketOrderRequest(
            symbol=symbol,
            side=OrderSide(side.upper()),
            quantity=quantity,
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
        )
    except Exception as exc:
        print_error(f"Validation Error: {exc}")
        raise typer.Exit(1)

    console.print(
        f"\n[bold cyan]Bracket Order:[/bold cyan] {req.symbol} | "
        f"Entry: {req.entry_price} | TP: {req.take_profit} | SL: {req.stop_loss}\n"
    )

    service = get_order_service()
    try:
        results = service.place_bracket_order(req, dry_run=dry_run)
        print_bracket_order_result(results, dry_run=dry_run)
        if not dry_run:
            print_success("All 3 bracket legs placed successfully.")
    except RiskLimitExceeded as exc:
        print_error(f"Risk Limit Exceeded: {exc}")
        raise typer.Exit(1)
    except BinanceAPIError as exc:
        print_error(f"Binance API Error: {exc}")
        raise typer.Exit(1)
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def cancel_order(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    order_id: Annotated[int, typer.Option("--order-id", help="Binance order ID to cancel")],
):
    """Cancel an open futures order by order ID."""
    if not typer.confirm(f"Cancel order {order_id} on {symbol.upper()}?"):
        print_warning("Cancellation aborted.")
        raise typer.Exit(0)

    service = get_order_service()
    try:
        response = service.cancel_order(symbol=symbol.upper(), order_id=order_id)
        print_success(f"Order {order_id} cancelled. Status: {response.get('status', 'N/A')}")
    except TradingBotError as exc:
        print_error(f"Error: {exc}")
        raise typer.Exit(1)


def twap_order(
    symbol: Annotated[str, typer.Option("--symbol", "-s", help="Trading pair, e.g. BTCUSDT")],
    side: Annotated[str, typer.Option("--side", help="BUY or SELL")],
    total_qty: Annotated[float, typer.Option("--quantity", "-q", help="Total quantity to execute")],
    slices: Annotated[int, typer.Option("--slices", help="Number of equal child orders")] = 5,
    interval: Annotated[int, typer.Option("--interval", help="Seconds between each slice")] = 60,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate without executing")] = False,
):
    """TWAP: split a large order into equal market slices spaced over time."""
    slice_qty = round(total_qty / slices, 6)

    console.print(
        f"\n[bold cyan]TWAP Order[/bold cyan] — {symbol.upper()} {side.upper()} "
        f"| Total: {total_qty} | {slices} slices × {slice_qty} every {interval}s"
    )
    if dry_run:
        console.print("[yellow]Dry-run mode: no orders will be sent.[/yellow]\n")

    service = get_order_service()
    results = []

    for i in range(1, slices + 1):
        console.print(f"\n[dim]── Slice {i}/{slices} ──[/dim]")
        try:
            request = OrderRequest(
                symbol=symbol,
                side=OrderSide(side.upper()),
                order_type=OrderType.MARKET,
                quantity=slice_qty,
            )
            resp = service.place_order(request, dry_run=dry_run)
            results.append(resp)
            print_order_result(resp, dry_run=dry_run)
        except TradingBotError as exc:
            print_error(f"Slice {i} failed: {exc}")
            if not typer.confirm("Continue with remaining slices?", default=True):
                break

        if i < slices and not dry_run:
            console.print(f"[dim]Waiting {interval}s before next slice...[/dim]")
            time.sleep(interval)

    filled = len(results)
    print_success(f"TWAP complete — {filled}/{slices} slices executed.")


def interactive_menu():
    """Interactive guided menu — place orders, check balance, view positions."""
    from rich.prompt import Confirm, FloatPrompt, Prompt

    from bot.cli.info_commands import balance, open_orders, portfolio, positions
    from bot.utils.health_check import health

    ORDER_TYPES = ["MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET", "BRACKET", "TWAP"]

    while True:
        console.clear()
        console.print("""
[bold cyan]╔══════════════════════════════════════╗
║    BINANCE FUTURES TRADING BOT       ║
║         Interactive Menu             ║
╚══════════════════════════════════════╝[/bold cyan]

  [bold white][1][/bold white] Place Order
  [bold white][2][/bold white] View Balance
  [bold white][3][/bold white] View Positions
  [bold white][4][/bold white] Open Orders
  [bold white][5][/bold white] Portfolio Summary
  [bold white][6][/bold white] Health Check
  [bold white][q][/bold white] Quit
""")
        choice = Prompt.ask(
            "[bold yellow]Select[/bold yellow]",
            choices=["1", "2", "3", "4", "5", "6", "q"],
            default="q",
        )

        if choice == "q":
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()

        if choice == "1":
            sym = Prompt.ask("Symbol", default="BTCUSDT").upper()
            sd = Prompt.ask("Side", choices=["BUY", "SELL"]).upper()
            ot = Prompt.ask("Order type", choices=ORDER_TYPES).upper()
            qty = FloatPrompt.ask("Quantity")
            price = stop = None

            if ot == "LIMIT":
                price = FloatPrompt.ask("Limit price")
            elif ot in ("STOP_MARKET", "TAKE_PROFIT_MARKET"):
                stop = FloatPrompt.ask("Stop trigger price")
            elif ot == "BRACKET":
                entry = FloatPrompt.ask("Entry price")
                tp_p = FloatPrompt.ask("Take-profit price")
                sl_p = FloatPrompt.ask("Stop-loss price")
                dr = Confirm.ask("Dry run?", default=False)
                bracket_order(sym, sd, qty, entry, tp_p, sl_p, dry_run=dr)
                Prompt.ask("\nPress Enter to continue")
                continue
            elif ot == "TWAP":
                n = int(Prompt.ask("Number of slices", default="5"))
                iv = int(Prompt.ask("Interval (seconds)", default="60"))
                dr = Confirm.ask("Dry run?", default=False)
                twap_order(sym, sd, qty, slices=n, interval=iv, dry_run=dr)
                Prompt.ask("\nPress Enter to continue")
                continue

            dr = Confirm.ask("Dry run?", default=False)
            prev = Confirm.ask("Preview before placing?", default=True)
            place_order(sym, sd, ot, qty, price, stop, dry_run=dr, preview=prev)

        elif choice == "2":
            balance()
        elif choice == "3":
            positions()
        elif choice == "4":
            open_orders()
        elif choice == "5":
            portfolio()
        elif choice == "6":
            health()

        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
