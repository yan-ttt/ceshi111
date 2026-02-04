from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

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
        .card { background: #111827; border: 1px solid #1f2937; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
        button { padding: 8px 12px; margin-right: 8px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
        button.secondary { background: #4b5563; }
        pre { white-space: pre-wrap; background: #0b1220; padding: 12px; border-radius: 6px; }
        input { padding: 6px; border-radius: 6px; border: 1px solid #334155; background: #0b1220; color: #e2e8f0; }
      </style>
    </head>
    <body>
      <h1>Gate.io AI Bot 控制台</h1>
      <div class="card">
        <h3>状态</h3>
        <button onclick="loadStatus()">刷新状态</button>
        <pre id="status"></pre>
      </div>
      <div class="card">
        <h3>信号</h3>
        <button onclick="loadSignals()">获取信号</button>
        <pre id="signals"></pre>
      </div>
      <div class="card">
        <h3>模型</h3>
        <button onclick="loadModels()">查看模型权重</button>
        <pre id="models"></pre>
      </div>
      <div class="card">
        <h3>余额与持仓（真实交易模式）</h3>
        <button class="secondary" onclick="loadBalances()">余额</button>
        <button class="secondary" onclick="loadPositions()">持仓</button>
        <pre id="balances"></pre>
        <pre id="positions"></pre>
      </div>
      <div class="card">
        <h3>执行与回测</h3>
        <button onclick="runCycle()">执行一次</button>
        <button class="secondary" onclick="runBacktest()">回测</button>
        <pre id="cycle"></pre>
      </div>
      <div class="card">
        <h3>订单查询</h3>
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
        async function loadStatus() { document.getElementById('status').textContent = await api('/status'); }
        async function loadSignals() { document.getElementById('signals').textContent = await api('/signals'); }
        async function loadModels() { document.getElementById('models').textContent = await api('/models'); }
        async function loadBalances() { document.getElementById('balances').textContent = await api('/balances'); }
        async function loadPositions() { document.getElementById('positions').textContent = await api('/positions'); }
        async function runCycle() { document.getElementById('cycle').textContent = await api('/cycle', { method: 'POST' }); }
        async function runBacktest() { document.getElementById('cycle').textContent = await api('/backtest', { method: 'POST' }); }
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
