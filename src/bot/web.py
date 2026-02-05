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
      <title>智能交易控制台</title>
      <style>
        :root {
          --bg: #f5f7fb;
          --card: #ffffff;
          --text: #1f2937;
          --muted: #6b7280;
          --accent: #2563eb;
          --border: #e5e7eb;
          --success: #16a34a;
          --danger: #dc2626;
        }
        body { font-family: "PingFang SC", "Microsoft Yahei", sans-serif; margin: 0; background: var(--bg); color: var(--text); }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px 24px 40px; }
        .topbar { display: flex; align-items: center; justify-content: space-between; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; gap: 20px; }
        .symbol-area { display: flex; align-items: center; gap: 12px; }
        .symbol-title { font-size: 20px; font-weight: 600; }
        .price { font-size: 22px; font-weight: 600; }
        .price-up { color: var(--success); }
        .price-down { color: var(--danger); }
        .stats { display: grid; grid-template-columns: repeat(4, auto); gap: 16px; font-size: 12px; color: var(--muted); }
        .stats strong { display: block; font-size: 14px; color: var(--text); }
        .layout { display: grid; grid-template-columns: 3fr 1fr; gap: 16px; margin-top: 16px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
        .chart-card { display: flex; flex-direction: column; gap: 12px; }
        .toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
        .toolbar .group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .toolbar button { background: #eef2ff; color: var(--accent); border: 1px solid #dbeafe; }
        .chart-area { background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 8px; }
        .chart-area svg { width: 100%; height: 360px; display: block; }
        .right-panel { display: flex; flex-direction: column; gap: 16px; }
        .panel-title { margin: 0 0 8px 0; font-size: 14px; font-weight: 600; }
        .pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: #f3f4f6; font-size: 12px; }
        .pill.live { background: #dcfce7; color: #166534; }
        .pill.paper { background: #fee2e2; color: #991b1b; }
        .list { list-style: none; padding: 0; margin: 0; font-size: 12px; }
        .list li { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed var(--border); }
        .list li:last-child { border-bottom: none; }
        .tabs { display: flex; gap: 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }
        .tabs button { background: none; border: none; font-size: 14px; cursor: pointer; color: var(--muted); padding-bottom: 6px; border-bottom: 2px solid transparent; }
        .tabs button.active { color: var(--accent); border-color: var(--accent); font-weight: 600; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        button { padding: 8px 12px; background: var(--accent); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; }
        button.secondary { background: #f3f4f6; color: var(--text); border: 1px solid var(--border); }
        input, select { padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border); background: white; font-size: 12px; }
        pre { white-space: pre-wrap; background: #f8fafc; padding: 12px; border-radius: 8px; max-height: 240px; overflow: auto; font-size: 12px; color: #111827; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="topbar">
          <div class="symbol-area">
            <select id="symbolSelect"></select>
            <div>
              <div class="symbol-title" id="symbolTitle">BTC_USDT</div>
              <div class="price" id="latestPrice">--</div>
            </div>
            <div id="priceChange" class="price price-up">--</div>
          </div>
          <div class="stats">
            <div><span>24h 最高</span><strong id="statHigh">--</strong></div>
            <div><span>24h 最低</span><strong id="statLow">--</strong></div>
            <div><span>成交量</span><strong id="statVolume">--</strong></div>
            <div><span>机器人延迟</span><strong id="statLatency">--</strong></div>
          </div>
          <div>
            <div class="pill live" id="liveStatus">实盘: 未知</div>
            <div class="pill paper" id="paperStatus">模拟: 未知</div>
          </div>
        </div>

        <div class="layout">
          <div class="card chart-card">
            <div class="toolbar">
              <div class="group">
                <button class="secondary" onclick="setIntervalLabel('1分钟')">1分</button>
                <button class="secondary" onclick="setIntervalLabel('15分钟')">15分</button>
                <button class="secondary" onclick="setIntervalLabel('1小时')">1小时</button>
                <button class="secondary" onclick="setIntervalLabel('4小时')">4小时</button>
              </div>
              <div class="group">
                <button onclick="loadCandles()">刷新K线</button>
                <button class="secondary" onclick="runCycle()">执行一次</button>
              </div>
            </div>
            <div class="chart-area">
              <svg id="kline"></svg>
            </div>
            <pre id="signals"></pre>
          </div>
          <div class="right-panel">
            <div class="card">
              <h4 class="panel-title">交易状态</h4>
              <ul class="list" id="statusList"></ul>
              <div style="margin-top: 10px;">
                <button class="secondary" onclick="toggleAutoTrade(true)">开启自动交易</button>
                <button class="secondary" onclick="toggleAutoTrade(false)">关闭自动交易</button>
              </div>
            </div>
            <div class="card">
              <h4 class="panel-title">最近成交</h4>
              <ul class="list" id="tradeList"></ul>
            </div>
          </div>
        </div>

        <div class="card" style="margin-top:16px;">
          <div class="tabs">
            <button class="active" data-tab="models" onclick="switchTab('models')">模型</button>
            <button data-tab="balances" onclick="switchTab('balances')">余额</button>
            <button data-tab="positions" onclick="switchTab('positions')">持仓</button>
            <button data-tab="orders" onclick="switchTab('orders')">订单查询</button>
            <button data-tab="training" onclick="switchTab('training')">混合训练</button>
          </div>
          <div id="tab-models" class="tab-content active">
            <button class="secondary" onclick="loadModels()">查看模型权重</button>
            <pre id="models"></pre>
          </div>
          <div id="tab-balances" class="tab-content">
            <button class="secondary" onclick="loadBalances()">刷新余额</button>
            <pre id="balances"></pre>
          </div>
          <div id="tab-positions" class="tab-content">
            <button class="secondary" onclick="loadPositions()">刷新持仓</button>
            <pre id="positions"></pre>
          </div>
          <div id="tab-orders" class="tab-content">
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
          <div id="tab-training" class="tab-content">
            <div class="toolbar">
              <div class="group">
                <label>设备：</label>
                <select id="trainDevice">
                  <option value="auto">自动选择</option>
                  <option value="cpu">CPU</option>
                  <option value="cuda">GPU</option>
                </select>
                <label>训练轮数：</label>
                <input id="trainEpochs" value="30" type="number" min="1" style="width:80px;"/>
              </div>
              <button onclick="runTraining()">开始混合训练</button>
            </div>
            <pre id="training"></pre>
          </div>
        </div>
      </div>
      <script>
        // 通用接口请求封装（返回格式化 JSON）
        async function api(path, options) {
          const res = await fetch(path, options);
          const data = await res.json();
          return JSON.stringify(data, null, 2);
        }
        // 加载基础状态与交易对列表
        function formatMode(mode) {
          if (mode === 'paper') return '模拟';
          if (mode === 'live') return '实盘';
          return mode || '未知';
        }
        async function loadStatus() {
          const data = await fetch('/status').then(r => r.json());
          document.getElementById('liveStatus').textContent = `实盘: ${formatMode(data.mode)}`;
          document.getElementById('paperStatus').textContent = data.paper_trade ? '模拟: 开启' : '模拟: 关闭';
          const select = document.getElementById('symbolSelect');
          if (select.options.length === 0) {
            data.symbols.forEach(sym => {
              const opt = document.createElement('option');
              opt.value = sym;
              opt.text = sym;
              select.appendChild(opt);
            });
          }
          document.getElementById('symbolTitle').textContent = select.value || data.symbols[0];
          const statusList = document.getElementById('statusList');
          statusList.innerHTML = '';
          const items = [
            ['交易模式', formatMode(data.mode)],
            ['自动交易', data.auto_trade ? '开启' : '关闭'],
            ['风险等级', data.risk],
          ];
          items.forEach(([label, value]) => {
            const li = document.createElement('li');
            li.innerHTML = `<span>${label}</span><span>${value}</span>`;
            statusList.appendChild(li);
          });
        }
        // 信号、模型、余额、持仓与执行接口
        async function loadSignals() { document.getElementById('signals').textContent = await api('/signals'); }
        async function loadModels() { document.getElementById('models').textContent = await api('/models'); }
        async function loadBalances() { document.getElementById('balances').textContent = await api('/balances'); }
        async function loadPositions() { document.getElementById('positions').textContent = await api('/positions'); }
        async function runCycle() { document.getElementById('signals').textContent = await api('/cycle', { method: 'POST' }); }
        async function loadTrades() {
          const data = await fetch('/trades?limit=8').then(r => r.json());
          const list = document.getElementById('tradeList');
          list.innerHTML = '';
          data.trades.forEach(line => {
            const li = document.createElement('li');
            li.innerHTML = `<span>${line.slice(0, 28)}</span><span>${line.slice(-12)}</span>`;
            list.appendChild(li);
          });
        }
        // 拉取K线并刷新顶部统计
        async function loadCandles() {
          const symbol = document.getElementById('symbolSelect').value;
          const data = await fetch(`/candles?symbol=${encodeURIComponent(symbol)}`).then(r => r.json());
          const candles = data.candles || [];
          drawCandles(candles);
          updateHeaderStats(candles);
          await loadSignals();
        }
        // 读取后端延迟等指标
        async function loadMetrics() {
          const data = await fetch('/metrics').then(r => r.json());
          document.getElementById('statLatency').textContent = `${(data.last_cycle_ms || 0).toFixed(0)} 毫秒`;
        }
        // 订单查询
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
        // 自动交易开关
        async function toggleAutoTrade(enable) {
          const path = enable ? '/auto-trade/enable' : '/auto-trade/disable';
          document.getElementById('signals').textContent = await api(path, { method: 'POST' });
          await loadStatus();
        }
        // UI显示的周期标签（不改变后端周期）
        function setIntervalLabel(label) {
          const title = document.getElementById('symbolTitle');
          title.textContent = `${document.getElementById('symbolSelect').value} · ${label}`;
        }
        // 标签页切换
        function switchTab(name) {
          document.querySelectorAll('.tabs button').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === name);
          });
          document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.toggle('active', tab.id === `tab-${name}`);
          });
        }
        // 顶部行情统计展示
        function updateHeaderStats(candles) {
          if (candles.length === 0) return;
          const last = candles[candles.length - 1];
          const first = candles[0];
          const change = ((last.close - first.close) / first.close) * 100;
          const high = Math.max(...candles.map(c => c.high));
          const low = Math.min(...candles.map(c => c.low));
          const volume = candles.reduce((acc, c) => acc + (c.volume || 0), 0);
          const priceChange = document.getElementById('priceChange');
          document.getElementById('latestPrice').textContent = last.close.toFixed(2);
          priceChange.textContent = `${change.toFixed(2)}%`;
          priceChange.className = change >= 0 ? 'price price-up' : 'price price-down';
          document.getElementById('statHigh').textContent = high.toFixed(2);
          document.getElementById('statLow').textContent = low.toFixed(2);
          document.getElementById('statVolume').textContent = volume.toFixed(2);
        }
        // 混合训练入口
        async function runTraining() {
          const symbol = document.getElementById('symbolSelect').value;
          const device = document.getElementById('trainDevice').value;
          const epochs = document.getElementById('trainEpochs').value;
          const payload = await api(`/train?symbol=${encodeURIComponent(symbol)}&device=${device}&epochs=${epochs}`, { method: 'POST' });
          document.getElementById('training').textContent = payload;
        }
        // 简易K线绘制
        function drawCandles(candles) {
          const svg = document.getElementById('kline');
          while (svg.firstChild) svg.removeChild(svg.firstChild);
          if (candles.length === 0) return;
          const width = svg.clientWidth || 600;
          const height = svg.clientHeight || 360;
          const highs = candles.map(c => c.high);
          const lows = candles.map(c => c.low);
          const min = Math.min(...lows);
          const max = Math.max(...highs);
          const candleWidth = Math.max(4, (width - 20) / candles.length);
          candles.forEach((c, i) => {
            const x = 10 + i * candleWidth;
            const openY = height - ((c.open - min) / (max - min + 1e-8)) * (height - 20) - 10;
            const closeY = height - ((c.close - min) / (max - min + 1e-8)) * (height - 20) - 10;
            const highY = height - ((c.high - min) / (max - min + 1e-8)) * (height - 20) - 10;
            const lowY = height - ((c.low - min) / (max - min + 1e-8)) * (height - 20) - 10;
            const color = c.close >= c.open ? '#16a34a' : '#dc2626';
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x + candleWidth / 2);
            line.setAttribute('x2', x + candleWidth / 2);
            line.setAttribute('y1', highY);
            line.setAttribute('y2', lowY);
            line.setAttribute('stroke', color);
            line.setAttribute('stroke-width', '1');
            svg.appendChild(line);
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', x);
            rect.setAttribute('y', Math.min(openY, closeY));
            rect.setAttribute('width', candleWidth * 0.7);
            rect.setAttribute('height', Math.max(2, Math.abs(openY - closeY)));
            rect.setAttribute('fill', color);
            rect.setAttribute('rx', '1');
            svg.appendChild(rect);
          });
        }
        async function init() {
          await loadStatus();
          const select = document.getElementById('symbolSelect');
          select.addEventListener('change', async () => {
            document.getElementById('symbolTitle').textContent = select.value;
            await loadCandles();
          });
          await loadCandles();
          await loadTrades();
          await loadMetrics();
        }
        init();
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
    return {
        "candles": data[
            ["timestamp", "open", "high", "low", "close", "volume"]
        ].to_dict(orient="records")
    }


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


@app.post("/train")
async def train(symbol: str = Query(..., min_length=1), epochs: int = 30, device: str = "auto") -> dict:
    report = engine.train_hybrid(symbol, epochs=epochs, device=device)
    return report.__dict__


@app.post("/auto-trade/enable", response_model=ControlResponse)
async def enable_auto_trade() -> ControlResponse:
    settings.enable_auto_trade = True  # type: ignore[misc]
    return ControlResponse(status="enabled")


@app.post("/auto-trade/disable", response_model=ControlResponse)
async def disable_auto_trade() -> ControlResponse:
    settings.enable_auto_trade = False  # type: ignore[misc]
    return ControlResponse(status="disabled")
