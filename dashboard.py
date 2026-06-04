#!/usr/bin/env python3
"""
Professional Trading Dashboard — Binance Futures Testnet Bot
Run: python3 dashboard.py   →   http://localhost:8000
"""
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from bot.clients.client_factory import get_order_repository, get_trading_client
from bot.core.correlation import set_correlation_id
from bot.models.order_models import OrderRequest, OrderSide, OrderType
from bot.utils.config_loader import get_settings
from bot.utils.logging_config import setup_logging

app = FastAPI(title="Trading Bot Dashboard", docs_url=None, redoc_url=None)

# ── REST API ──────────────────────────────────────────────────────────────────

@app.get("/api/balance")
async def api_balance():
    try:
        return [b for b in get_trading_client().get_account_balance() if float(b.get("balance", 0)) > 0]
    except Exception as exc:
        raise HTTPException(503, detail=str(exc))


@app.get("/api/positions")
async def api_positions():
    try:
        return [p for p in get_trading_client().get_position_information()
                if float(p.get("positionAmt", 0)) != 0]
    except Exception as exc:
        raise HTTPException(503, detail=str(exc))


@app.get("/api/orders/history")
async def api_order_history():
    return get_order_repository().get_all()[-20:]


@app.get("/api/price/{symbol}")
async def api_price(symbol: str):
    try:
        p = get_trading_client().get_mark_price(symbol.upper())
        return {"symbol": symbol.upper(), "price": p}
    except Exception as exc:
        raise HTTPException(503, detail=str(exc))


@app.get("/api/klines/{symbol}/{interval}")
async def api_klines(symbol: str, interval: str = "1m", limit: int = 120):
    """Return close-price series for the Lightweight Charts area series."""
    valid = {"1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"}
    if interval not in valid:
        interval = "1m"
    try:
        client = get_trading_client()
        # futures_klines → list of [openTime, open, high, low, close, volume, ...]
        raw = client._call("futures_klines", symbol=symbol.upper(),
                           interval=interval, limit=limit)
        return [{"time": int(k[0]) // 1000, "value": float(k[4])} for k in raw]
    except Exception as exc:
        raise HTTPException(503, detail=str(exc))


@app.post("/api/order")
async def api_place_order(payload: Dict[str, Any]):
    set_correlation_id()
    try:
        from bot.clients.client_factory import get_order_service
        req = OrderRequest(
            symbol=payload["symbol"],
            side=OrderSide(payload["side"].upper()),
            order_type=OrderType(payload["type"].upper()),
            quantity=float(payload["quantity"]),
            price=float(payload["price"]) if payload.get("price") else None,
            stop_price=float(payload["stop_price"]) if payload.get("stop_price") else None,
            reduce_only=bool(payload.get("reduce_only", False)),
        )
        return get_order_service().place_order(req, dry_run=bool(payload.get("dry_run", False)))
    except Exception as exc:
        raise HTTPException(400, detail=str(exc))


# ── HTML Dashboard ────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Bot · Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#040d1a;--bg2:#060f1e;--panel:#07111d;
  --cyan:#00e5ff;--green:#00ff94;--red:#ff4466;--yellow:#ffd60a;--orange:#ff8c00;
  --text:#b8ccd8;--dim:#3a5570;
  --glow:0 0 12px #00e5ff55,0 0 28px #00e5ff22;
  --glow-g:0 0 12px #00ff9455,0 0 28px #00ff9422;
  --glow-r:0 0 12px #ff446655,0 0 28px #ff446622;
}
html,body{background:var(--bg);color:var(--text);font-family:'Share Tech Mono',monospace;min-height:100vh;overflow-x:hidden}

/* HEADER */
header{display:flex;align-items:center;justify-content:space-between;padding:10px 22px;
  border-bottom:1px solid #00e5ff18;background:var(--bg2);position:sticky;top:0;z-index:100;
  box-shadow:0 2px 20px #00000088}
.logo{font-family:'Orbitron',sans-serif;font-weight:900;font-size:1rem;letter-spacing:4px;
  color:var(--cyan);text-shadow:var(--glow)}
.logo em{color:var(--green);font-style:normal}
.hdr-r{display:flex;align-items:center;gap:12px;font-size:.72rem}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:var(--glow-g);
  animation:pulse 2s infinite;display:inline-block;margin-right:5px}
.dot.off{background:var(--red);box-shadow:var(--glow-r);animation:none}
#env{padding:2px 8px;border:1px solid var(--yellow);color:var(--yellow);border-radius:3px;
  font-size:.62rem;letter-spacing:2px}
.ibtn{background:none;border:1px solid #00e5ff25;color:var(--cyan);border-radius:3px;
  padding:4px 10px;cursor:pointer;font-family:'Orbitron',sans-serif;font-size:.6rem;
  letter-spacing:1px;transition:all .2s}
.ibtn:hover{border-color:var(--cyan);box-shadow:var(--glow)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* GRID */
main{display:grid;grid-template-columns:200px 1fr 310px;
  grid-template-rows:auto auto 1fr;gap:12px;padding:12px 16px;
  max-width:1700px;margin:0 auto}

/* PANEL */
.panel{background:var(--panel);border:1px solid #00e5ff12;border-radius:6px;
  padding:12px;position:relative;overflow:hidden}
.panel::before{content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,#00e5ff04 0%,transparent 50%);
  border-radius:6px;pointer-events:none}
.pt{font-family:'Orbitron',sans-serif;font-size:.58rem;letter-spacing:2px;
  color:var(--cyan);text-shadow:var(--glow);margin-bottom:10px;
  border-bottom:1px solid #00e5ff12;padding-bottom:6px}

/* CHART */
#chart-sec{grid-column:1/-1;background:var(--panel);border:1px solid #00e5ff12;
  border-radius:6px;padding:14px 16px;overflow:hidden}
.chart-top{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:12px}
.chart-price{font-family:'Orbitron',sans-serif;font-size:1.8rem;color:var(--green);
  text-shadow:var(--glow-g);letter-spacing:1px}
.chart-sym-name{font-family:'Orbitron',sans-serif;font-size:.7rem;color:var(--dim);
  letter-spacing:2px;margin-bottom:4px}
.chart-chg{font-size:.78rem;margin-top:3px}
.chart-chg.up{color:var(--green)} .chart-chg.dn{color:var(--red)}
.chart-right{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.sym-row,.iv-row{display:flex;gap:6px}
.sym-btn,.iv-btn{background:none;border:1px solid #00e5ff22;color:var(--dim);
  padding:3px 10px;border-radius:3px;cursor:pointer;
  font-family:'Share Tech Mono',monospace;font-size:.72rem;transition:all .2s}
.sym-btn.on,.sym-btn:hover,.iv-btn.on,.iv-btn:hover{
  border-color:var(--cyan);color:var(--cyan);background:#00e5ff0a;box-shadow:var(--glow)}
#chart-wrap{position:relative;height:340px;border-radius:4px;
  overflow:hidden;background:#030c17}
#lw-chart{width:100%;height:100%}
#tt{position:absolute;display:none;pointer-events:none;z-index:50;
  background:#0a1e2e;border:1px solid var(--cyan);border-radius:5px;
  padding:8px 12px;box-shadow:var(--glow);min-width:150px}
#tt-price{font-family:'Orbitron',sans-serif;font-size:.95rem;
  color:var(--green);text-shadow:var(--glow-g)}
#tt-time{font-size:.65rem;color:var(--dim);margin-top:3px}

/* BALANCE */
#bal-pan{grid-column:1;grid-row:2/4}
.bal-card{padding:8px 10px;border:1px solid #00e5ff12;border-radius:4px;margin-bottom:8px}
.bal-asset{font-family:'Orbitron',sans-serif;font-size:.68rem;color:var(--cyan);letter-spacing:1px}
.bal-amt{font-size:1.15rem;color:var(--green);text-shadow:var(--glow-g);margin-top:3px}
.bal-avl{font-size:.65rem;color:var(--dim);margin-top:2px}

/* POSITIONS */
#pos-pan{grid-column:2;grid-row:2}

/* HISTORY */
#hist-pan{grid-column:2;grid-row:3}

/* ════════════════════════════════════════
   PROFESSIONAL TRADING ORDER FORM
   ════════════════════════════════════════ */
#form-pan{grid-column:3;grid-row:2/4;padding:0;overflow:visible}

.trade-form{background:var(--panel);border:1px solid #00e5ff12;
  border-radius:6px;overflow:hidden;display:flex;flex-direction:column}

/* Available balance bar */
.form-bal-bar{display:flex;justify-content:space-between;align-items:center;
  padding:10px 14px 8px;border-bottom:1px solid #00e5ff0e;background:#050e1a}
.fbb-label{font-size:.6rem;color:var(--dim);letter-spacing:1px}
.fbb-val{font-family:'Orbitron',sans-serif;font-size:.78rem;color:var(--green);text-shadow:var(--glow-g)}

/* BUY / SELL tabs */
.bs-tabs{display:grid;grid-template-columns:1fr 1fr}
.bs-tab{padding:11px 0;border:none;cursor:pointer;font-family:'Orbitron',sans-serif;
  font-size:.68rem;letter-spacing:2px;transition:all .2s;background:transparent;
  border-bottom:2px solid transparent;color:var(--dim)}
.bs-tab.buy.active{color:var(--green);border-bottom-color:var(--green);
  background:#00ff9408;text-shadow:var(--glow-g)}
.bs-tab.sell.active{color:var(--red);border-bottom-color:var(--red);
  background:#ff446608;text-shadow:var(--glow-r)}
.bs-tab:not(.active):hover{background:#ffffff06;color:var(--text)}

/* Order-type sub-tabs */
.ot-tabs{display:flex;gap:0;padding:8px 14px 0;background:#050e1a;
  border-bottom:1px solid #00e5ff0e}
.ot-tab{flex:1;padding:6px 4px;background:none;border:none;border-bottom:2px solid transparent;
  color:var(--dim);cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.7rem;
  transition:all .2s;white-space:nowrap}
.ot-tab.active{color:var(--cyan);border-bottom-color:var(--cyan)}
.ot-tab:hover:not(.active){color:var(--text)}

/* Inner form body */
.form-body{padding:12px 14px;display:flex;flex-direction:column;gap:10px;flex:1}

/* Mark price */
.mk-row{display:flex;justify-content:space-between;align-items:center;
  padding:6px 8px;background:#050d18;border-radius:4px;
  border:1px solid #00e5ff0e}
.mk-label{font-size:.6rem;color:var(--dim);letter-spacing:1px}
.mk-val{font-family:'Orbitron',sans-serif;font-size:.82rem;color:var(--cyan)}

/* Fields */
.fg{display:flex;flex-direction:column;gap:3px}
.fg label{font-size:.6rem;color:var(--dim);letter-spacing:1px;
  display:flex;justify-content:space-between;align-items:center}
.fg label .unit{color:#00e5ff44;font-size:.58rem}
.fg input,.fg select{
  background:#050d18;border:1px solid #00e5ff18;border-radius:4px;
  color:var(--text);font-family:'Share Tech Mono',monospace;font-size:.82rem;
  padding:8px 10px;width:100%;outline:none;transition:all .2s}
.fg input:focus,.fg select:focus{border-color:var(--cyan);box-shadow:var(--glow)}
.fg input.buy-focus:focus{border-color:var(--green);box-shadow:var(--glow-g)}
.fg input.sell-focus:focus{border-color:var(--red);box-shadow:var(--glow-r)}
/* Highlight border on active side */
.side-buy  .fg input{border-color:#00ff941a}
.side-buy  .fg input:focus{border-color:var(--green);box-shadow:var(--glow-g)}
.side-sell .fg input{border-color:#ff44661a}
.side-sell .fg input:focus{border-color:var(--red);box-shadow:var(--glow-r)}

/* % buttons */
.pct-row{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:4px}
.pct-btn{padding:4px 0;background:#050d18;border:1px solid #00e5ff18;
  border-radius:3px;color:var(--dim);cursor:pointer;
  font-family:'Share Tech Mono',monospace;font-size:.68rem;transition:all .2s}
.pct-btn:hover{border-color:var(--cyan);color:var(--cyan);background:#00e5ff0a}
.side-buy  .pct-btn:hover{border-color:var(--green);color:var(--green)}
.side-sell .pct-btn:hover{border-color:var(--red);color:var(--red)}

/* Calc box */
.calc-box{background:#050d18;border:1px solid #00e5ff0e;border-radius:4px;padding:8px 10px}
.calc-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;font-size:.7rem}
.calc-row:last-child{margin-bottom:0}
.calc-row span:first-child{color:var(--dim)}
.calc-row span:last-child{color:var(--text);font-family:'Orbitron',sans-serif;font-size:.68rem}
#calc-total{color:var(--green)!important}

/* Options row */
.opts-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}

/* Toggle */
.toggle-row{display:flex;align-items:center;justify-content:space-between;
  padding:6px 0;border-top:1px solid #00e5ff0a}
.tgl-label{font-size:.65rem;color:var(--dim);letter-spacing:.5px}
.switch{position:relative;width:34px;height:18px;flex-shrink:0}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;inset:0;background:#0d1e2e;border:1px solid #00e5ff22;
  border-radius:9px;cursor:pointer;transition:.2s}
.slider:before{content:'';position:absolute;width:12px;height:12px;
  left:2px;bottom:2px;background:var(--dim);border-radius:50%;transition:.2s}
input:checked + .slider{background:#00e5ff18;border-color:var(--cyan)}
input:checked + .slider:before{transform:translateX(16px);background:var(--cyan)}

/* Place button */
.place-btn{padding:12px;border:none;border-radius:5px;
  font-family:'Orbitron',sans-serif;font-size:.72rem;letter-spacing:2px;
  cursor:pointer;transition:all .2s;width:100%;margin-top:4px;font-weight:700}
.place-btn.buy-btn{background:linear-gradient(135deg,#003d22,#006644);
  color:var(--green);border:1px solid #00ff9440;text-shadow:var(--glow-g)}
.place-btn.buy-btn:hover{background:linear-gradient(135deg,#005530,#009955);
  box-shadow:var(--glow-g)}
.place-btn.sell-btn{background:linear-gradient(135deg,#3d0011,#660022);
  color:var(--red);border:1px solid #ff446640;text-shadow:var(--glow-r)}
.place-btn.sell-btn:hover{background:linear-gradient(135deg,#550018,#990033);
  box-shadow:var(--glow-r)}
.place-btn:active{transform:scale(.98)}
.dry-btn{background:transparent;color:var(--yellow);border:1px solid #ffd60a30;
  border-radius:5px;padding:8px;font-family:'Orbitron',sans-serif;font-size:.62rem;
  letter-spacing:2px;cursor:pointer;transition:all .2s;width:100%;margin-top:4px}
.dry-btn:hover{border-color:var(--yellow);box-shadow:0 0 10px #ffd60a33}

/* Order result */
#o-res{font-size:.7rem;padding:7px 10px;border-radius:4px;
  display:none;white-space:pre-wrap;word-break:break-all;margin-top:4px}
#o-res.ok{background:#001a0d;border:1px solid var(--green);color:var(--green)}
#o-res.err{background:#1a0008;border:1px solid var(--red);color:var(--red)}

/* TABLES */
table{width:100%;border-collapse:collapse;font-size:.74rem}
th{text-align:left;font-family:'Orbitron',sans-serif;font-size:.55rem;
  letter-spacing:1px;color:var(--cyan);padding:5px 7px;
  border-bottom:1px solid #00e5ff1a}
td{padding:5px 7px;border-bottom:1px solid #00e5ff0a;
  color:var(--text);vertical-align:middle}
tr:hover td{background:#00e5ff05}
.badge{display:inline-block;padding:2px 7px;border-radius:3px;font-size:.63rem}
.b-buy{background:#002218;color:var(--green);border:1px solid #00ff9422}
.b-sell{background:#1e0010;color:var(--red);border:1px solid #ff446622}
.b-new{background:#001630;color:var(--cyan);border:1px solid #00e5ff22}
.b-fill{background:#001a10;color:var(--green);border:1px solid #00ff9422}
.b-dry{background:#141200;color:var(--yellow);border:1px solid #ffd60a22}
.pnl-p{color:var(--green);text-shadow:var(--glow-g)}
.pnl-n{color:var(--red);text-shadow:var(--glow-r)}
.empty{color:var(--dim);font-size:.76rem;padding:14px 0;text-align:center}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-thumb{background:#00e5ff18;border-radius:3px}
#ref{position:fixed;bottom:12px;right:16px;font-size:.62rem;color:var(--dim)}

/* GUIDE */
#guide{display:none;position:fixed;inset:0;background:#040d1af0;
  z-index:200;overflow-y:auto;padding:30px}
#guide.open{display:block}
.gbox{max-width:880px;margin:0 auto;background:var(--panel);
  border:1px solid var(--cyan);border-radius:8px;padding:28px;box-shadow:var(--glow)}
.gbox h1{font-family:'Orbitron',sans-serif;color:var(--cyan);font-size:1rem;
  letter-spacing:3px;margin-bottom:20px;text-shadow:var(--glow)}
.gbox h2{font-family:'Orbitron',sans-serif;color:var(--green);font-size:.68rem;
  letter-spacing:2px;margin:20px 0 8px;text-transform:uppercase}
.gbox p{font-size:.78rem;color:var(--text);line-height:1.7;margin-bottom:8px}
.gbox code{background:#0a1828;color:var(--cyan);padding:1px 7px;border-radius:3px;
  font-family:'Share Tech Mono',monospace;font-size:.76rem}
.gtbl{width:100%;border-collapse:collapse;font-size:.73rem;margin-top:6px}
.gtbl th{color:var(--cyan);font-family:'Orbitron',sans-serif;font-size:.56rem;
  letter-spacing:1px;padding:5px 9px;border-bottom:1px solid #00e5ff1a;text-align:left}
.gtbl td{padding:5px 9px;border-bottom:1px solid #00e5ff0a;color:var(--text)}
.gtbl td:first-child{color:var(--cyan);white-space:nowrap}
.cbtn{float:right;background:none;border:1px solid var(--red);color:var(--red);
  padding:4px 14px;border-radius:3px;cursor:pointer;
  font-family:'Orbitron',sans-serif;font-size:.6rem;letter-spacing:1px}
.cbtn:hover{box-shadow:var(--glow-r)}
.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}
.tc{background:#050d18;border:1px solid #00e5ff12;border-radius:4px;padding:10px}
.tc h3{color:var(--cyan);font-size:.65rem;letter-spacing:1px;margin-bottom:4px;
  font-family:'Orbitron',sans-serif}
.tc p{font-size:.7rem;color:var(--dim);line-height:1.6}
</style>
</head>
<body>

<header>
  <div class="logo">TRADING<em>BOT</em> &nbsp;⬡&nbsp; DASHBOARD</div>
  <div class="hdr-r">
    <span id="env">TESTNET</span>
    <span><span class="dot" id="dot"></span><span id="conn">CONNECTING</span></span>
    <span id="clk" style="color:var(--cyan)">—</span>
    <button class="ibtn" onclick="openGuide()">? GUIDE</button>
  </div>
</header>

<main>

  <!-- CHART -->
  <div id="chart-sec">
    <div class="chart-top">
      <div>
        <div class="chart-sym-name" id="chart-label">BTC / USDT · MARK PRICE</div>
        <div class="chart-price" id="chart-px">$——</div>
        <div class="chart-chg" id="chart-chg">——</div>
      </div>
      <div class="chart-right">
        <div class="sym-row">
          <button class="sym-btn on" onclick="setSym('BTCUSDT',this)">BTC/USDT</button>
          <button class="sym-btn" onclick="setSym('ETHUSDT',this)">ETH/USDT</button>
          <button class="sym-btn" onclick="setSym('BNBUSDT',this)">BNB/USDT</button>
        </div>
        <div class="iv-row">
          <button class="iv-btn on" onclick="setIv('1m',this)">1m</button>
          <button class="iv-btn" onclick="setIv('5m',this)">5m</button>
          <button class="iv-btn" onclick="setIv('15m',this)">15m</button>
          <button class="iv-btn" onclick="setIv('1h',this)">1h</button>
          <button class="iv-btn" onclick="setIv('4h',this)">4h</button>
          <button class="iv-btn" onclick="setIv('1d',this)">1d</button>
        </div>
      </div>
    </div>
    <div id="chart-wrap">
      <div id="lw-chart"></div>
      <div id="tt"><div id="tt-price"></div><div id="tt-time"></div></div>
    </div>
  </div>

  <!-- BALANCE -->
  <div class="panel" id="bal-pan">
    <div class="pt">WALLET</div>
    <div id="bal-list"><span class="empty">Loading...</span></div>
  </div>

  <!-- POSITIONS -->
  <div class="panel" id="pos-pan">
    <div class="pt">OPEN POSITIONS</div>
    <div id="pos-tbl"><span class="empty">Loading...</span></div>
  </div>

  <!-- ════ PROFESSIONAL TRADING FORM ════ -->
  <div id="form-pan">
  <div class="trade-form" id="trade-form">

    <!-- Available Balance -->
    <div class="form-bal-bar">
      <span class="fbb-label">AVAILABLE</span>
      <span class="fbb-val" id="form-avail">— USDT</span>
    </div>

    <!-- BUY / SELL -->
    <div class="bs-tabs">
      <button class="bs-tab buy active" id="tab-buy" onclick="setBS('BUY')">▲ BUY / LONG</button>
      <button class="bs-tab sell" id="tab-sell" onclick="setBS('SELL')">▼ SELL / SHORT</button>
    </div>

    <!-- Order Type -->
    <div class="ot-tabs">
      <button class="ot-tab active" onclick="setOT('MARKET',this)">Market</button>
      <button class="ot-tab" onclick="setOT('LIMIT',this)">Limit</button>
      <button class="ot-tab" onclick="setOT('STOP_MARKET',this)">Stop</button>
      <button class="ot-tab" onclick="setOT('TAKE_PROFIT_MARKET',this)">TP</button>
    </div>

    <div class="form-body side-buy" id="form-body">

      <!-- Symbol selector -->
      <div class="fg">
        <label>SYMBOL</label>
        <select id="f-sym" onchange="onSymChange()">
          <option>BTCUSDT</option>
          <option>ETHUSDT</option>
          <option>BNBUSDT</option>
          <option>SOLUSDT</option>
          <option>XRPUSDT</option>
        </select>
      </div>

      <!-- Mark price -->
      <div class="mk-row">
        <span class="mk-label">MARK PRICE</span>
        <span class="mk-val" id="form-mark">——</span>
      </div>

      <!-- Price (LIMIT) -->
      <div class="fg" id="price-row" style="display:none">
        <label>PRICE <span class="unit">USDT</span></label>
        <input id="f-px" type="number" step="0.01" placeholder="0.00" oninput="calcTotal()"/>
      </div>

      <!-- Stop Price (STOP / TP) -->
      <div class="fg" id="stop-row" style="display:none">
        <label>STOP TRIGGER <span class="unit">USDT</span></label>
        <input id="f-stop" type="number" step="0.01" placeholder="0.00" oninput="calcTotal()"/>
      </div>

      <!-- Quantity -->
      <div class="fg">
        <label>QUANTITY <span class="unit" id="qty-unit">BTC</span></label>
        <input id="f-qty" type="number" step="0.001" value="0.001" min="0.001" oninput="calcTotal()"/>
        <div class="pct-row">
          <button class="pct-btn" onclick="fillPct(25)">25%</button>
          <button class="pct-btn" onclick="fillPct(50)">50%</button>
          <button class="pct-btn" onclick="fillPct(75)">75%</button>
          <button class="pct-btn" onclick="fillPct(100)">100%</button>
        </div>
      </div>

      <!-- Order total calc -->
      <div class="calc-box">
        <div class="calc-row">
          <span>Est. Total</span>
          <span id="calc-total">— USDT</span>
        </div>
        <div class="calc-row">
          <span>Taker Fee (0.04%)</span>
          <span id="calc-fee">— USDT</span>
        </div>
        <div class="calc-row">
          <span>Order Type</span>
          <span id="calc-type" style="color:var(--cyan)">MARKET</span>
        </div>
      </div>

      <!-- TIF + Reduce Only -->
      <div class="opts-row">
        <div class="fg" id="tif-group">
          <label>TIME IN FORCE</label>
          <select id="f-tif">
            <option value="GTC">GTC</option>
            <option value="IOC">IOC</option>
            <option value="FOK">FOK</option>
          </select>
        </div>
        <div class="fg">
          <label>POST ONLY</label>
          <select id="f-postonly">
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        </div>
      </div>

      <div class="toggle-row">
        <span class="tgl-label">REDUCE ONLY</span>
        <label class="switch">
          <input type="checkbox" id="f-reduce"/>
          <span class="slider"></span>
        </label>
      </div>

      <!-- PLACE ORDER BUTTON -->
      <button class="place-btn buy-btn" id="place-btn" onclick="sendOrder(false)">
        ⚡ BUY / LONG BTCUSDT
      </button>
      <button class="dry-btn" onclick="sendOrder(true)">◎ DRY RUN (validate only)</button>

      <div id="o-res"></div>
    </div><!-- /form-body -->
  </div><!-- /trade-form -->
  </div><!-- /form-pan -->

  <!-- HISTORY -->
  <div class="panel" id="hist-pan">
    <div class="pt">RECENT ORDER HISTORY (last 20)</div>
    <div id="hist-tbl" style="overflow-x:auto"><span class="empty">Loading...</span></div>
  </div>

</main>
<div id="ref">⟳ auto-refresh 5s</div>

<!-- GUIDE -->
<div id="guide">
  <div class="gbox">
    <button class="cbtn" onclick="closeGuide()">✕ CLOSE</button>
    <h1>◈ USER GUIDE — TRADING BOT DASHBOARD</h1>
    <h2>Overview</h2>
    <p>Live connection to Binance Futures Testnet. Refreshes every 5 seconds. All orders hit <code>testnet.binancefuture.com</code> — no real money.</p>
    <h2>Trading Form (right panel)</h2>
    <table class="gtbl">
      <tr><th>Field</th><th>Meaning</th></tr>
      <tr><td>BUY / SELL</td><td>Direction. BUY = Long position, SELL = Short position</td></tr>
      <tr><td>Market</td><td>Execute immediately at best available price</td></tr>
      <tr><td>Limit</td><td>Set a specific price. Order fills when market reaches it</td></tr>
      <tr><td>Stop</td><td>Market order triggered when price hits your stop level (stop-loss)</td></tr>
      <tr><td>TP</td><td>Market order triggered at take-profit level</td></tr>
      <tr><td>Price</td><td>The limit price you want to enter/exit at (Limit orders only)</td></tr>
      <tr><td>Stop Trigger</td><td>The price at which a Stop or TP order activates</td></tr>
      <tr><td>Quantity</td><td>Amount in base asset (BTC, ETH…). Use % buttons to fill from balance</td></tr>
      <tr><td>25/50/75/100%</td><td>Auto-fills quantity as % of your available USDT ÷ mark price</td></tr>
      <tr><td>TIF: GTC</td><td>Good Till Cancel — stays open until filled or manually cancelled</td></tr>
      <tr><td>TIF: IOC</td><td>Immediate or Cancel — fill what you can right now, cancel the rest</td></tr>
      <tr><td>TIF: FOK</td><td>Fill or Kill — must fill entirely immediately or cancel</td></tr>
      <tr><td>Reduce Only</td><td>Order can only reduce an existing position, never open new one</td></tr>
      <tr><td>Dry Run</td><td>Validates risk + shows estimated cost — NEVER sent to Binance</td></tr>
    </table>
    <h2>CLI Commands</h2>
    <table class="gtbl">
      <tr><th>Command</th><th>Example</th></tr>
      <tr><td>place-order</td><td><code>python3 cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001</code></td></tr>
      <tr><td>bracket-order</td><td><code>python3 cli.py bracket-order --symbol BTCUSDT --side BUY --quantity 0.001 --entry 65000 --take-profit 68000 --stop-loss 63000</code></td></tr>
      <tr><td>twap-order</td><td><code>python3 cli.py twap-order --symbol BTCUSDT --side BUY --quantity 0.01 --slices 5 --interval 60</code></td></tr>
      <tr><td>menu</td><td><code>python3 cli.py menu</code></td></tr>
      <tr><td>balance / positions</td><td><code>python3 cli.py balance</code></td></tr>
      <tr><td>export-orders</td><td><code>python3 cli.py export-orders</code></td></tr>
    </table>
    <h2>Tips</h2>
    <div class="tgrid">
      <div class="tc"><h3>LIMIT ORDER FLOW</h3>
        <p>Place a LIMIT BUY at $60,000. Binance holds the order open. When BTC drops to $60,000, it fills automatically. Your balance updates once filled.</p></div>
      <div class="tc"><h3>STOP-LOSS</h3>
        <p>Place a STOP order with Reduce Only ON. When price hits your stop trigger, a MARKET order closes your position at best available price.</p></div>
      <div class="tc"><h3>BRACKET ORDER</h3>
        <p>Use CLI <code>bracket-order</code> to place entry + TP + SL simultaneously as 3 separate orders. Best way to manage full trade lifecycle.</p></div>
      <div class="tc"><h3>BALANCE UPDATES</h3>
        <p>Balance shown is real-time from testnet API. After a MARKET order, balance updates in 5 seconds. LIMIT orders update when filled by Binance.</p></div>
    </div>
  </div>
</div>

<script>
// ── Lightweight Charts ────────────────────────────────────────────────────────
const chartEl = document.getElementById('lw-chart');
const tt=document.getElementById('tt'),ttPx=document.getElementById('tt-price'),ttTm=document.getElementById('tt-time');
const chart = LightweightCharts.createChart(chartEl,{
  width:chartEl.parentElement.clientWidth,height:340,
  layout:{background:{type:'solid',color:'#030c17'},textColor:'#4a7090',fontSize:11,fontFamily:"'Share Tech Mono',monospace"},
  grid:{vertLines:{color:'#00e5ff09',style:1},horzLines:{color:'#00e5ff09',style:1}},
  crosshair:{mode:LightweightCharts.CrosshairMode.Normal,
    vertLine:{color:'#00e5ff55',width:1,style:3,labelBackgroundColor:'#0a2033'},
    horzLine:{color:'#00e5ff55',width:1,style:3,labelBackgroundColor:'#0a2033'}},
  rightPriceScale:{borderColor:'#00e5ff15',textColor:'#4a7090',scaleMargins:{top:.1,bottom:.1}},
  timeScale:{borderColor:'#00e5ff15',textColor:'#4a7090',timeVisible:true,secondsVisible:false},
  handleScroll:{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true},
  handleScale:{mouseWheel:true,pinch:true,axisPressedMouseMove:true},
  localization:{priceFormatter:p=>'$'+p.toLocaleString(undefined,{maximumFractionDigits:2})},
});
const series=chart.addAreaSeries({lineColor:'#00e5ff',topColor:'#00e5ff28',bottomColor:'#00e5ff00',
  lineWidth:2,priceLineVisible:false,lastValueVisible:true,
  crosshairMarkerVisible:true,crosshairMarkerRadius:5,
  crosshairMarkerBorderColor:'#00e5ff',crosshairMarkerBackgroundColor:'#040d1a'});
chart.subscribeCrosshairMove(param=>{
  if(!param.point||!param.time){tt.style.display='none';return}
  const d=param.seriesData.get(series);if(!d){tt.style.display='none';return}
  ttPx.textContent='$'+Number(d.value).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
  ttTm.textContent=new Date(param.time*1000).toLocaleString();
  const wrap=document.getElementById('chart-wrap');
  let l=param.point.x+15,t=param.point.y-50;
  if(l+165>wrap.clientWidth)l=param.point.x-175;if(t<0)t=5;
  tt.style.left=l+'px';tt.style.top=t+'px';tt.style.display='block';
});
window.addEventListener('resize',()=>chart.applyOptions({width:chartEl.parentElement.clientWidth}));

// ── Chart state ───────────────────────────────────────────────────────────────
let CUR_SYM='BTCUSDT',CUR_IV='1m',prevPx=0;

async function loadKlines(){
  try{const d=await fetch(`/api/klines/${CUR_SYM}/${CUR_IV}?limit=120`).then(r=>r.json());
    series.setData(d);chart.timeScale().fitContent();}
  catch(e){console.warn(e);}
}
async function tickPrice(){
  try{
    const d=await fetch('/api/price/'+CUR_SYM).then(r=>r.json());
    const px=Number(d.price);
    document.getElementById('chart-px').textContent='$'+px.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
    if(prevPx){const diff=px-prevPx,pct=((diff/prevPx)*100).toFixed(3);
      const el=document.getElementById('chart-chg');
      el.textContent=(diff>=0?'▲ +':'▼ ')+diff.toFixed(2)+' ('+pct+'%)';
      el.className='chart-chg '+(diff>=0?'up':'dn');}
    prevPx=px;
    series.update({time:Math.floor(Date.now()/1000),value:px});
    // Update form mark price
    if(document.getElementById('f-sym').value===CUR_SYM){
      document.getElementById('form-mark').textContent='$'+px.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
      formMarkPrice=px; calcTotal();
    }
    document.getElementById('dot').className='dot';
    document.getElementById('conn').textContent='CONNECTED';
  }catch(e){document.getElementById('dot').className='dot off';document.getElementById('conn').textContent='OFFLINE';}
}
function setSym(sym,btn){CUR_SYM=sym;prevPx=0;
  document.querySelectorAll('.sym-btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');
  document.getElementById('chart-label').textContent=sym.replace('USDT','')+' / USDT · MARK PRICE';
  loadKlines().then(tickPrice);}
function setIv(iv,btn){CUR_IV=iv;
  document.querySelectorAll('.iv-btn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');
  loadKlines();}

// ── Trading form state ────────────────────────────────────────────────────────
let formSide='BUY', formOT='MARKET', formMarkPrice=0, formAvailUsdt=0;

function setBS(side){
  formSide=side;
  const body=document.getElementById('form-body');
  document.getElementById('tab-buy').classList.toggle('active',side==='BUY');
  document.getElementById('tab-sell').classList.toggle('active',side==='SELL');
  body.className='form-body '+(side==='BUY'?'side-buy':'side-sell');
  const btn=document.getElementById('place-btn');
  btn.className='place-btn '+(side==='BUY'?'buy-btn':'sell-btn');
  const sym=document.getElementById('f-sym').value;
  btn.textContent=`⚡ ${side} / ${side==='BUY'?'LONG':'SHORT'} ${sym}`;
}

function setOT(ot,btn){
  formOT=ot;
  document.querySelectorAll('.ot-tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('price-row').style.display=ot==='LIMIT'?'flex':'none';
  document.getElementById('stop-row').style.display=(ot==='STOP_MARKET'||ot==='TAKE_PROFIT_MARKET')?'flex':'none';
  document.getElementById('tif-group').style.display=ot==='LIMIT'?'flex':'none';
  document.getElementById('calc-type').textContent=ot.replace('_',' ');
  calcTotal();
}

function onSymChange(){
  const sym=document.getElementById('f-sym').value;
  // Update qty unit label
  const base=sym.replace('USDT','').replace('BUSD','');
  document.getElementById('qty-unit').textContent=base;
  // Update place button
  document.getElementById('place-btn').textContent=`⚡ ${formSide} / ${formSide==='BUY'?'LONG':'SHORT'} ${sym}`;
  // Fetch mark price for this symbol
  fetch('/api/price/'+sym).then(r=>r.json()).then(d=>{
    formMarkPrice=Number(d.price);
    document.getElementById('form-mark').textContent='$'+formMarkPrice.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
    // Pre-fill price field for limit orders
    if(formOT==='LIMIT'&&!document.getElementById('f-px').value)
      document.getElementById('f-px').value=formMarkPrice.toFixed(2);
    calcTotal();
  }).catch(()=>{});
}

function fillPct(pct){
  if(!formMarkPrice||!formAvailUsdt)return;
  const price=formOT==='LIMIT'?(parseFloat(document.getElementById('f-px').value)||formMarkPrice):formMarkPrice;
  const qty=(formAvailUsdt*(pct/100))/price;
  document.getElementById('f-qty').value=qty.toFixed(3);
  calcTotal();
}

function calcTotal(){
  const qty=parseFloat(document.getElementById('f-qty').value)||0;
  let price=0;
  if(formOT==='LIMIT') price=parseFloat(document.getElementById('f-px').value)||formMarkPrice;
  else price=formMarkPrice;
  const total=qty*price;
  const fee=total*0.0004;
  document.getElementById('calc-total').textContent=total>0?total.toFixed(4)+' USDT':'— USDT';
  document.getElementById('calc-fee').textContent=fee>0?fee.toFixed(6)+' USDT':'— USDT';
}

async function sendOrder(dryRun){
  const res=document.getElementById('o-res');
  res.style.display='block';res.className='';res.textContent='⟳ Sending order...';
  const sym=document.getElementById('f-sym').value;
  const qty=document.getElementById('f-qty').value;
  const px=document.getElementById('f-px').value||null;
  const stop=document.getElementById('f-stop').value||null;
  const reduce=document.getElementById('f-reduce').checked;
  const payload={symbol:sym,side:formSide,type:formOT,quantity:qty,
    price:formOT==='LIMIT'?px:null,
    stop_price:(formOT==='STOP_MARKET'||formOT==='TAKE_PROFIT_MARKET')?stop:null,
    reduce_only:reduce,dry_run:dryRun};
  try{
    const r=await fetch('/api/order',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json();
    if(!r.ok) throw d.detail||JSON.stringify(d);
    res.className='ok';
    if(dryRun){
      res.textContent=`✓ DRY RUN — Order Valid\nEst. Notional: ${d.estimated_notional_usdt||'—'} USDT\nEst. Fee:      ${d.estimated_fee_usdt||'—'} USDT\nSide:          ${formSide}\nType:          ${formOT}\nQty:           ${qty}`;
    } else {
      res.textContent=`✓ ORDER PLACED\nOrder ID:  ${d.orderId||d.clientOrderId||'—'}\nStatus:    ${d.status||'—'}\nAvg Fill:  ${d.avgPrice&&Number(d.avgPrice)>0?'$'+Number(d.avgPrice).toFixed(2):'—'}\nLatency:   ${d._latency_ms||'—'}`;
    }
    loadHistory();loadBalance();
  }catch(e){res.className='err';res.textContent='✗ '+e;}
}

// ── Balance ───────────────────────────────────────────────────────────────────
async function loadBalance(){
  try{
    const data=await fetch('/api/balance').then(r=>r.json());
    const el=document.getElementById('bal-list');
    // Update form available USDT
    const usdt=data.find(b=>b.asset==='USDT');
    if(usdt){
      formAvailUsdt=Number(usdt.availableBalance||usdt.balance||0);
      document.getElementById('form-avail').textContent=formAvailUsdt.toFixed(4)+' USDT';
    }
    if(!data.length){el.innerHTML='<span class="empty">No balance</span>';return;}
    el.innerHTML=data.map(b=>`
      <div class="bal-card">
        <div class="bal-asset">${b.asset}</div>
        <div class="bal-amt">${Number(b.balance).toFixed(4)}</div>
        <div class="bal-avl">Avail: ${Number(b.availableBalance||b.withdrawAvailable||0).toFixed(4)}</div>
      </div>`).join('');
  }catch(e){document.getElementById('bal-list').innerHTML='<span class="empty">Error</span>';}
}

// ── Positions ─────────────────────────────────────────────────────────────────
function sideBadge(s){return`<span class="badge ${s==='BUY'?'b-buy':'b-sell'}">${s}</span>`;}
async function loadPositions(){
  try{
    const data=await fetch('/api/positions').then(r=>r.json());
    const el=document.getElementById('pos-tbl');
    if(!data.length){el.innerHTML='<span class="empty">No open positions</span>';return;}
    el.innerHTML=`<table>
      <tr><th>SYMBOL</th><th>SIDE</th><th>SIZE</th><th>ENTRY</th><th>MARK</th><th>PNL</th><th>LEV</th></tr>
      ${data.map(p=>{
        const amt=Number(p.positionAmt),pnl=Number(p.unRealizedProfit||p.unrealizedProfit||0);
        const pc=pnl>=0?'pnl-p':'pnl-n',ps=(pnl>=0?'+':'')+pnl.toFixed(4);
        return`<tr><td>${p.symbol}</td><td>${sideBadge(amt>0?'BUY':'SELL')}</td>
          <td>${Math.abs(amt).toFixed(4)}</td><td>${Number(p.entryPrice).toFixed(2)}</td>
          <td>${Number(p.markPrice).toFixed(2)}</td>
          <td class="${pc}">${ps}</td><td>${p.leverage?p.leverage+'x':'—'}</td></tr>`;
      }).join('')}</table>`;
  }catch(e){document.getElementById('pos-tbl').innerHTML=`<span class="empty">${e}</span>`;}
}

// ── History ───────────────────────────────────────────────────────────────────
function stBadge(s){
  if(s==='DRY_RUN')return'<span class="badge b-dry">DRY</span>';
  if(s==='FILLED')return'<span class="badge b-fill">FILLED</span>';
  return'<span class="badge b-new">'+(s||'—')+'</span>';
}
async function loadHistory(){
  try{
    const data=await fetch('/api/orders/history').then(r=>r.json());
    const el=document.getElementById('hist-tbl');
    if(!data.length){el.innerHTML='<span class="empty">No orders yet</span>';return;}
    el.innerHTML=`<table>
      <tr><th>ORDER ID</th><th>SYMBOL</th><th>SIDE</th><th>TYPE</th><th>QTY</th><th>PRICE</th><th>AVG FILL</th><th>STATUS</th><th>TIME</th></tr>
      ${[...data].reverse().map(o=>{
        const px=(o.price&&o.price>0)?Number(o.price).toFixed(2):'—';
        const avg=(o.avg_price&&o.avg_price>0)?`<span style="color:var(--green)">${Number(o.avg_price).toFixed(2)}</span>`:'—';
        return`<tr>
          <td style="color:var(--dim);font-size:.68rem">${o.order_id}</td>
          <td>${o.symbol}</td><td>${sideBadge(o.side)}</td>
          <td>${o.type}</td><td>${o.quantity}</td>
          <td>${px}</td><td>${avg}</td><td>${stBadge(o.status)}</td>
          <td style="color:var(--dim);font-size:.67rem">${(o.created_at||'').slice(0,16).replace('T',' ')}</td>
        </tr>`;}).join('')}
    </table>`;
  }catch(e){document.getElementById('hist-tbl').innerHTML=`<span class="empty">${e}</span>`;}
}

// ── Clock ─────────────────────────────────────────────────────────────────────
function tick(){document.getElementById('clk').textContent=new Date().toUTCString().slice(17,25)+' UTC';}

// ── Guide ─────────────────────────────────────────────────────────────────────
function openGuide(){document.getElementById('guide').classList.add('open');}
function closeGuide(){document.getElementById('guide').classList.remove('open');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeGuide();});

// ── Bootstrap ─────────────────────────────────────────────────────────────────
loadKlines().then(()=>tickPrice());
setBS('BUY');  // init form side
onSymChange(); // load initial mark price

async function refreshAll(){
  await Promise.all([loadBalance(),loadPositions(),loadHistory(),tickPrice()]);
  tick();
}
refreshAll();
setInterval(refreshAll,5000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=HTML)


if __name__ == "__main__":
    setup_logging()
    print("\n  🚀  Trading Bot Dashboard  →  http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
