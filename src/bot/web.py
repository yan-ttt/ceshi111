from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path

from bot.config import load_settings
from bot.backtest import Backtester
from bot.engine import TradingEngine
from bot.risk import RiskSettings

app = FastAPI(title="Gate.io AI Trading Bot", version="0.1.0")
settings = load_settings()
engine = TradingEngine(settings)
backtester = Backtester(
    engine.ensemble,
    RiskSettings(
        stop_loss_pct=settings.stop_loss_pct,
        take_profit_pct=settings.take_profit_pct,
        max_drawdown_pct=settings.max_drawdown_pct,
        dynamic_position=settings.dynamic_position,
    ),
)


class ControlResponse(BaseModel):
    status: str


@app.get("/", response_class=HTMLResponse)
async def ui() -> str:
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8">
      <title>Gate.io AI Bot 控制台</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 24px; background: #0f172a; color: #e2e8f0; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .card { background: #111827; border: 1px solid #1f2937; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
        button { padding: 8px 12px; margin-right: 8px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
        button.secondary { background: #4b5563; }
        pre { white-space: pre-wrap; background: #0b1220; padding: 12px; border-radius: 6px; max-height: 240px; overflow: auto; }
        input, select { padding: 6px; border-radius: 6px; border: 1px solid #334155; background: #0b1220; color: #e2e8f0; }
        .section-title { margin: 0 0 8px 0; font-size: 16px; color: #93c5fd; }
        .status-pill { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #1e293b; margin-left: 8px; font-size: 12px; }
        .chart { background: #0b1220; border-radius: 8px; padding: 8px; }
      </style>
    </head>
    <body>
      <h1>Gate.io AI Bot 控制台</h1>
      <div class="grid">
        <div class="card">
          <h3 class="section-title">实时交易面板 <span class="status-pill" id="liveStatus">未知</span></h3>
          <button onclick="loadStatus()">刷新状态</button>
          <button class="secondary" onclick="runCycle()">执行一次</button>
          <pre id="status"></pre>
        </div>
        <div class="card">
          <h3 class="section-title">模拟交易面板 <span class="status-pill" id="paperStatus">未知</span></h3>
          <button class="secondary" onclick="loadTrades()">查看最近交易</button>
          <pre id="trades"></pre>
        </div>
      </div>

      <div class="card">
        <h3 class="section-title">K线图（简化显示）</h3>
        <div>
          <label>交易对：</label>
          <select id="symbolSelect"></select>
          <button class="secondary" onclick="loadCandles()">刷新K线</button>
        </div>
        <div class="chart">
          <svg id="kline" width="100%" height="220"></svg>
        </div>
        <pre id="signals"></pre>
      </div>

      <div class="grid">
        <div class="card">
          <h3 class="section-title">模型与理由</h3>
          <button class="secondary" onclick="loadModels()">查看模型权重</button>
          <pre id="models"></pre>
        </div>
        <div class="card">
          <h3 class="section-title">余额 / 持仓</h3>
          <button class="secondary" onclick="loadBalances()">余额</button>
          <button class="secondary" onclick="loadPositions()">持仓</button>
          <pre id="balances"></pre>
          <pre id="positions"></pre>
        </div>
      </div>

      <div class="card">
        <h3 class="section-title">订单查询</h3>
        <div>
          <input id="spotOrderId" placeholder="现货订单ID"/>
          <input id="spotSymbol" placeholder="现货交易对，如 BTC_USDT"/>
          <button class="secondary" onclick="querySpotOrder()">查询现货订单</button>
        </div>
        <div style="margin-top:8px;">
          <input id="futuresOrderId" placeholder="合约订单ID"/>
          <button class="secondary" onclick="queryFuturesOrder()">查询合约订单</button>
        </div>
        <pre id="orders"></pre>
      </div>
      <script>
        async function api(path, options) {
          const res = await fetch(path, options);
          const data = await res.json();
          return JSON.stringify(data, null, 2);
        }
        async function loadStatus() {
          const data = await fetch('/status').then(r => r.json());
          document.getElementById('status').textContent = JSON.stringify(data, null, 2);
          document.getElementById('liveStatus').textContent = data.mode;
          document.getElementById('paperStatus').textContent = data.paper_trade ? '模拟开启' : '模拟关闭';
          const select = document.getElementById('symbolSelect');
          if (select.options.length === 0) {
            data.symbols.forEach(sym => {
              const opt = document.createElement('option');
              opt.value = sym;
              opt.text = sym;
              select.appendChild(opt);
            });
          }
        }
        async function loadSignals() { document.getElementById('signals').textContent = await api('/signals'); }
        async function loadModels() { document.getElementById('models').textContent = await api('/models'); }
        async function loadBalances() { document.getElementById('balances').textContent = await api('/balances'); }
        async function loadPositions() { document.getElementById('positions').textContent = await api('/positions'); }
        async function runCycle() { document.getElementById('cycle').textContent = await api('/cycle', { method: 'POST' }); }
        async function runBacktest() { document.getElementById('cycle').textContent = await api('/backtest', { method: 'POST' }); }
        async function loadTrades() { document.getElementById('trades').textContent = await api('/trades?limit=20'); }
        async function loadCandles() {
          const symbol = document.getElementById('symbolSelect').value;
          const data = await fetch(`/candles?symbol=${encodeURIComponent(symbol)}`).then(r => r.json());
          const candles = data.candles || [];
          drawKline(candles);
          await loadSignals();
        }
        async function querySpotOrder() {
          const id = document.getElementById('spotOrderId').value;
          const symbol = document.getElementById('spotSymbol').value;
          if (!id || !symbol) return;
          document.getElementById('orders').textContent = await api(`/orders/spot/${id}?symbol=${encodeURIComponent(symbol)}`);
        }
        async function queryFuturesOrder() {
          const id = document.getElementById('futuresOrderId').value;
          if (!id) return;
          document.getElementById('orders').textContent = await api(`/orders/futures/${id}`);
        }
        function drawKline(candles) {
          const svg = document.getElementById('kline');
          while (svg.firstChild) svg.removeChild(svg.firstChild);
          if (candles.length === 0) return;
          const width = svg.clientWidth || 600;
          const height = svg.clientHeight || 220;
          const closes = candles.map(c => c.close);
          const min = Math.min(...closes);
          const max = Math.max(...closes);
          const points = closes.map((c, i) => {
            const x = (i / (closes.length - 1)) * (width - 10) + 5;
            const y = height - ((c - min) / (max - min + 1e-8)) * (height - 10) - 5;
            return `${x},${y}`;
          }).join(' ');
          const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
          poly.setAttribute('points', points);
          poly.setAttribute('fill', 'none');
          poly.setAttribute('stroke', '#22d3ee');
          poly.setAttribute('stroke-width', '2');
          svg.appendChild(poly);
        }
        loadStatus();
      </script>
    </body>
    </html>
    """

@app.get("/status")
async def status() -> dict:
    return {
        "mode": settings.trading_mode,
        "auto_trade": settings.enable_auto_trade,
        "paper_trade": settings.enable_paper_trade,
        "symbols": settings.symbols,
        "risk": settings.risk_level,
    }


@app.get("/signals")
async def signals() -> dict:
    data = {}
    for symbol in settings.symbols:
        signal = engine.analyze(symbol)
        data[symbol] = signal.__dict__
    return data


@app.get("/models")
async def models() -> dict:
    return {
        "weights": engine.model_weights,
        "scores": engine.model_scores,
        "available": engine.registry.list_models(),
    }


@app.get("/metrics")
async def metrics() -> dict:
    return engine.stats()


@app.get("/balances")
async def balances() -> dict:
    return {"balances": engine.balances()}


@app.get("/positions")
async def positions() -> dict:
    return {"positions": engine.positions()}


@app.get("/candles")
async def candles(symbol: str = Query(..., min_length=1)) -> dict:
    data = engine.fetch_candles(symbol)
    return {"candles": data[["timestamp", "open", "high", "low", "close"]].to_dict(orient="records")}


@app.get("/trades")
async def trades(limit: int = 20) -> dict:
    log_path = engine.trade_logger.trade_log
    if not log_path.exists():
        return {"trades": []}
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    return {"trades": lines[-limit:]}


@app.get("/orders/spot/{order_id}")
async def spot_order(order_id: str, symbol: str) -> dict:
    return {"order": engine.get_spot_order_status(order_id, symbol)}


@app.get("/orders/futures/{order_id}")
async def futures_order(order_id: str) -> dict:
    return {"order": engine.get_futures_order_status(order_id)}


@app.post("/cycle")
async def cycle() -> dict:
    decisions = engine.cycle_once()
    results = [engine.execute(decision) for decision in decisions]
    return {"decisions": [d.__dict__ for d in decisions], "results": results}


@app.post("/backtest")
async def backtest() -> dict:
    data = {symbol: engine.fetch_candles(symbol) for symbol in settings.symbols}
    results = backtester.run_multi(data)
    return {"results": [r.__dict__ for r in results]}


@app.post("/auto-trade/enable", response_model=ControlResponse)
async def enable_auto_trade() -> ControlResponse:
    settings.enable_auto_trade = True  # type: ignore[misc]
    return ControlResponse(status="enabled")


@app.post("/auto-trade/disable", response_model=ControlResponse)
async def disable_auto_trade() -> ControlResponse:
    settings.enable_auto_trade = False  # type: ignore[misc]
    return ControlResponse(status="disabled")
