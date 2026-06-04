from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_success(message: str) -> None:
    console.print(Panel(f"[bold green]{message}[/bold green]", border_style="green", expand=False))


def print_error(message: str) -> None:
    console.print(Panel(f"[bold red]{message}[/bold red]", border_style="red", expand=False))


def print_warning(message: str) -> None:
    console.print(
        Panel(f"[bold yellow]{message}[/bold yellow]", border_style="yellow", expand=False)
    )


def print_info(message: str) -> None:
    console.print(Panel(f"[bold cyan]{message}[/bold cyan]", border_style="cyan", expand=False))


def print_order_result(response: Dict[str, Any], dry_run: bool = False) -> None:
    title = "[bold yellow]DRY RUN — Order Validated[/bold yellow]" if dry_run else "[bold green]Order Executed Successfully[/bold green]"
    border = "yellow" if dry_run else "green"

    table = Table(title=title, box=box.DOUBLE_EDGE, border_style=border, show_header=True)
    table.add_column("Parameter", style="cyan", no_wrap=True, min_width=18)
    table.add_column("Value", style="white")

    # Binance may return orderId as int or string; fall back to clientOrderId
    order_id = response.get("orderId") or response.get("clientOrderId", "N/A")
    # origType is the authoritative type field for conditional orders (TP/SL)
    order_type = response.get("type") or response.get("origType", "N/A")
    # avgPrice: show only if non-zero (market orders fill at avg price)
    avg_price = response.get("avgPrice")
    avg_price_val = f"{float(avg_price):.4f}" if avg_price and float(avg_price) > 0 else None
    # executedQty: explicitly required by task spec
    exec_qty = response.get("executedQty")

    # Only show Price when Binance actually set one (non-zero); "0.00" means N/A for MARKET
    def _nonzero(val) -> bool:
        try:
            return val is not None and float(val) > 0
        except (ValueError, TypeError):
            return False

    price_raw    = response.get("price")
    stop_raw     = response.get("stopPrice")

    fields = {
        "Order ID":     order_id,
        "Symbol":       response.get("symbol", "N/A"),
        "Side":         response.get("side", "N/A"),
        "Type":         order_type,
        "Orig Qty":     response.get("origQty", response.get("quantity", "N/A")),
        "Executed Qty": exec_qty if exec_qty is not None else None,
        "Avg Price":    avg_price_val,
        # Show Price / Stop Price only when they carry a real value
        "Price":        f"{float(price_raw):.2f}" if _nonzero(price_raw) else None,
        "Stop Price":   f"{float(stop_raw):.2f}"  if _nonzero(stop_raw)  else None,
        "Status":       response.get("status", "N/A"),
    }
    # Drop rows where value is None (optional fields not present in this response)
    fields = {k: v for k, v in fields.items() if v is not None}
    if "_latency_ms" in response:
        fields["API Latency"] = response["_latency_ms"]
    if "estimated_notional_usdt" in response:
        fields["Est. Notional"] = f"{response['estimated_notional_usdt']:.4f} USDT"
    if "estimated_fee_usdt" in response:
        fields["Est. Fee"] = f"{response['estimated_fee_usdt']:.6f} USDT"

    for key, value in fields.items():
        table.add_row(key, str(value))

    console.print(table)
    if dry_run:
        console.print("\n[yellow]No order was sent to Binance. Dry Run mode is active.[/yellow]\n")


def print_bracket_order_result(results: Dict[str, Dict[str, Any]], dry_run: bool = False) -> None:
    label = "DRY RUN — " if dry_run else ""
    console.print(
        Panel(
            f"[bold green]{label}Bracket Order Summary[/bold green]",
            border_style="yellow" if dry_run else "green",
        )
    )
    for leg, response in results.items():
        leg_title = leg.replace("_", " ").title()
        print_order_result(response, dry_run=dry_run)
        console.print(f"  [dim]↑ {leg_title}[/dim]\n")


def print_balance_table(balances: List[Dict[str, Any]]) -> None:
    table = Table(title="[bold]Futures Wallet Balance[/bold]", box=box.ROUNDED, border_style="cyan")
    table.add_column("Asset", style="cyan", no_wrap=True)
    table.add_column("Total Balance", style="green", justify="right")
    table.add_column("Available", style="bright_green", justify="right")

    for b in balances:
        total = float(b.get("balance", 0))
        if total > 0:
            table.add_row(
                b.get("asset", ""),
                f"{total:.4f}",
                f"{float(b.get('availableBalance', b.get('withdrawAvailable', 0))):.4f}",
            )
    console.print(table)


def print_positions_table(positions: List[Dict[str, Any]]) -> None:
    open_pos = [p for p in positions if float(p.get("positionAmt", 0)) != 0]

    if not open_pos:
        print_info("No open positions found.")
        return

    table = Table(title="[bold]Open Positions[/bold]", box=box.ROUNDED, border_style="magenta")
    table.add_column("Symbol", style="cyan")
    table.add_column("Side", style="white")
    table.add_column("Size", justify="right")
    table.add_column("Entry Price", justify="right")
    table.add_column("Mark Price", justify="right")
    table.add_column("PnL", justify="right")       # shorter name avoids truncation
    table.add_column("Leverage", justify="right")

    for p in open_pos:
        amt = float(p.get("positionAmt", 0))
        # Binance position info uses "unRealizedProfit" (capital R & P)
        pnl = float(p.get("unRealizedProfit", p.get("unrealizedProfit", 0)))
        side_str = "[green]LONG[/green]" if amt > 0 else "[red]SHORT[/red]"
        pnl_str = (
            f"[green]+{pnl:.4f}[/green]" if pnl >= 0 else f"[red]{pnl:.4f}[/red]"
        )
        # Avoid "N/Ax" — only append "x" when leverage is a real value
        lev = p.get("leverage")
        lev_str = f"{lev}x" if lev is not None else "N/A"
        table.add_row(
            p.get("symbol", ""),
            side_str,
            f"{abs(amt):.4f}",
            p.get("entryPrice", "N/A"),
            p.get("markPrice", "N/A"),
            pnl_str,
            lev_str,
        )
    console.print(table)


def print_open_orders_table(orders: List[Dict[str, Any]]) -> None:
    if not orders:
        print_info("No open orders found.")
        return

    table = Table(title="[bold]Open Orders[/bold]", box=box.ROUNDED, border_style="blue")
    table.add_column("Order ID", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Side", style="white")
    table.add_column("Type", style="yellow")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Status", style="green")

    for o in orders:
        side_color = "green" if o.get("side") == "BUY" else "red"
        table.add_row(
            str(o.get("orderId", "")),
            o.get("symbol", ""),
            f"[{side_color}]{o.get('side', '')}[/{side_color}]",
            o.get("type", ""),
            o.get("origQty", ""),
            o.get("price", "N/A"),
            o.get("status", ""),
        )
    console.print(table)


def print_trade_history_table(trades: List[Dict[str, Any]]) -> None:
    if not trades:
        print_info("No trade history found.")
        return

    table = Table(title="[bold]Trade History[/bold]", box=box.ROUNDED, border_style="blue")
    table.add_column("Time", style="dim")
    table.add_column("Symbol", style="cyan")
    table.add_column("Side", style="white")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Realized PnL", justify="right")
    table.add_column("Commission", justify="right")

    for t in trades:
        from datetime import datetime
        ts = t.get("time", 0)
        try:
            dt = datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        except Exception:
            dt = str(ts)

        pnl = float(t.get("realizedPnl", 0))
        pnl_str = f"[green]+{pnl:.4f}[/green]" if pnl >= 0 else f"[red]{pnl:.4f}[/red]"
        side_color = "green" if t.get("side") == "BUY" else "red"

        table.add_row(
            dt,
            t.get("symbol", ""),
            f"[{side_color}]{t.get('side', '')}[/{side_color}]",
            t.get("qty", ""),
            t.get("price", ""),
            pnl_str,
            f"{float(t.get('commission', 0)):.6f}",
        )
    console.print(table)


def print_portfolio_summary(
    balances: List[Dict],
    positions: List[Dict],
) -> None:
    total_usdt = sum(
        float(b.get("balance", 0)) for b in balances if b.get("asset") == "USDT"
    )
    open_pos = [p for p in positions if float(p.get("positionAmt", 0)) != 0]
    # Binance uses "unRealizedProfit" (capital R & P) in position info response
    total_pnl = sum(
        float(p.get("unRealizedProfit", p.get("unrealizedProfit", 0)))
        for p in open_pos
    )

    pnl_color = "green" if total_pnl >= 0 else "red"
    pnl_sign = "+" if total_pnl >= 0 else ""

    console.print(
        Panel(
            f"[bold cyan]Total USDT Balance:[/bold cyan] [white]{total_usdt:.4f} USDT[/white]\n"
            f"[bold cyan]Open Positions:[/bold cyan]     [white]{len(open_pos)}[/white]\n"
            f"[bold cyan]Unrealized PnL:[/bold cyan]     [{pnl_color}]{pnl_sign}{total_pnl:.4f} USDT[/{pnl_color}]",
            title="[bold]Portfolio Summary[/bold]",
            border_style="magenta",
        )
    )
    if open_pos:
        print_positions_table(positions)


def print_order_preview(request: Any, mark_price: float) -> None:
    notional = request.estimated_notional(mark_price)
    fee = request.estimated_fee(mark_price)

    table = Table(
        title="[bold yellow]Order Preview[/bold yellow]",
        box=box.DOUBLE_EDGE,
        border_style="yellow",
    )
    table.add_column("Field", style="cyan", min_width=18)
    table.add_column("Value", style="white")

    table.add_row("Symbol", request.symbol)
    table.add_row("Side", request.side.value)
    table.add_row("Type", request.order_type.value)
    table.add_row("Quantity", str(request.quantity))
    if request.price:
        table.add_row("Price", f"{request.price:.2f} USDT")
    if request.stop_price:
        table.add_row("Stop Price", f"{request.stop_price:.2f} USDT")
    table.add_row("Mark Price", f"{mark_price:.2f} USDT")
    table.add_row("Est. Notional", f"{notional:.4f} USDT")
    table.add_row("Est. Taker Fee", f"{fee:.6f} USDT")

    console.print(table)


def print_health_table(checks: Dict[str, tuple]) -> None:
    table = Table(title="[bold]Health Check[/bold]", box=box.ROUNDED, border_style="cyan")
    table.add_column("Check", style="cyan", min_width=22)
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    all_ok = True
    for check, (ok, detail) in checks.items():
        status = "[bold green]PASS[/bold green]" if ok else "[bold red]FAIL[/bold red]"
        if not ok:
            all_ok = False
        table.add_row(check, status, detail)

    console.print(table)
    if all_ok:
        print_success("All health checks passed.")
    else:
        print_error("One or more health checks failed.")
