"""
Swiss Trader Dashboard - Live Portfolio Viewer
Run: python3 dashboard.py
Open: http://localhost:5000
"""
import os
import json
from flask import Flask, jsonify, render_template_string
import yfinance as yf

app = Flask(__name__)
PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
            if "trades" not in data:
                data["trades"] = []
            if "cost_basis" not in data:
                data["cost_basis"] = {}
            return data
    return {"cash": 50000.0, "holdings": {}, "cost_basis": {}, "trades": [], "history": []}

def get_live_prices(tickers):
    """Fetch current prices for a list of tickers."""
    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            if info.last_price:
                prices[ticker] = round(info.last_price, 2)
        except:
            pass
    return prices

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EscherBot</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: #1a2234;
            --bg-card-hover: #1f2a40;
            --border: #2a3549;
            --text-primary: #e2e8f0;
            --text-secondary: #8b95a5;
            --text-muted: #5a6577;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --green: #10b981;
            --green-bg: rgba(16, 185, 129, 0.1);
            --red: #ef4444;
            --red-bg: rgba(239, 68, 68, 0.1);
            --yellow: #f59e0b;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        .header {
            background: linear-gradient(135deg, #111827 0%, #1a0a2e 100%);
            border-bottom: 1px solid var(--border);
            padding: 20px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header h1 span { font-size: 24px; -webkit-text-fill-color: initial; }

        .live-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 24px 32px; }

        /* Summary Cards */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }

        .summary-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.2s ease;
        }

        .summary-card:hover { background: var(--bg-card-hover); transform: translateY(-1px); }

        .summary-card .label {
            font-size: 12px;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .summary-card .value {
            font-size: 28px;
            font-weight: 700;
        }

        .summary-card .sub {
            font-size: 13px;
            margin-top: 4px;
            font-weight: 500;
        }

        .positive { color: var(--green); }
        .negative { color: var(--red); }

        /* Section Titles */
        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Holdings Table */
        .table-wrap {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 28px;
        }

        table { width: 100%; border-collapse: collapse; }

        th {
            text-align: left;
            padding: 14px 20px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
            background: rgba(0,0,0,0.2);
        }

        td {
            padding: 16px 20px;
            font-size: 14px;
            border-bottom: 1px solid var(--border);
        }

        tr:last-child td { border-bottom: none; }

        tr:hover td { background: rgba(59, 130, 246, 0.03); }

        .ticker-cell {
            font-weight: 700;
            color: var(--accent-blue);
            font-size: 15px;
        }

        .price-cell { font-weight: 600; font-variant-numeric: tabular-nums; }

        .pl-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }

        .pl-positive { background: var(--green-bg); color: var(--green); }
        .pl-negative { background: var(--red-bg); color: var(--red); }

        .empty-state {
            text-align: center;
            padding: 48px;
            color: var(--text-muted);
            font-size: 15px;
        }

        .empty-state .icon { font-size: 40px; margin-bottom: 12px; }

        /* Trades Feed */
        .trades-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }

        .trade-feed {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            max-height: 420px;
        }

        .trade-feed-header {
            padding: 14px 20px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
            background: rgba(0,0,0,0.2);
        }

        .trade-list {
            overflow-y: auto;
            max-height: 370px;
            scrollbar-width: thin;
            scrollbar-color: var(--border) transparent;
        }

        .trade-item {
            display: flex;
            align-items: center;
            padding: 14px 20px;
            border-bottom: 1px solid var(--border);
            gap: 14px;
        }

        .trade-item:last-child { border-bottom: none; }

        .trade-action {
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            min-width: 40px;
            text-align: center;
        }

        .trade-buy { background: var(--green-bg); color: var(--green); }
        .trade-sell { background: var(--red-bg); color: var(--red); }

        .trade-info { flex: 1; }
        .trade-ticker { font-weight: 600; font-size: 14px; }
        .trade-detail { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
        .trade-reason { font-size: 11px; color: var(--text-muted); margin-top: 4px; font-style: italic; }
        .trade-date { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

        /* Chart */
        .chart-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }

        .chart-header {
            padding: 14px 20px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
            background: rgba(0,0,0,0.2);
        }

        .chart-body { padding: 20px; height: 340px; }

        canvas { width: 100% !important; }

        /* Weekly Reports */
        .reports-section { margin-top: 28px; }

        .report-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 16px;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }

        .report-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: linear-gradient(180deg, var(--accent-blue), var(--accent-purple));
        }

        .report-card:hover { background: var(--bg-card-hover); }

        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
            gap: 16px;
        }

        .report-title {
            font-size: 18px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .report-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-shrink: 0;
        }

        .report-date {
            font-size: 12px;
            color: var(--text-muted);
            background: rgba(59, 130, 246, 0.1);
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 500;
        }

        .report-change {
            font-size: 13px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
        }

        .report-body {
            font-size: 14px;
            line-height: 1.7;
            color: var(--text-secondary);
        }

        .report-body p { margin-bottom: 12px; }
        .report-body p:last-child { margin-bottom: 0; }
        .report-body strong { color: var(--text-primary); font-weight: 600; }

        .report-value {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }

        /* Responsive */
        @media (max-width: 900px) {
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
            .trades-grid { grid-template-columns: 1fr; }
            .container { padding: 16px; }
            .report-header { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>🤖</span> Swiss Trader Dashboard</h1>
        <div class="live-badge">
            <div class="live-dot"></div>
            <span>Auto-refresh 60s · Last update: <span id="last-update">--</span></span>
        </div>
    </div>

    <div class="container">
        <!-- Summary Cards -->
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">Portfolio Value</div>
                <div class="value" id="total-value">--</div>
                <div class="sub" id="total-change">--</div>
            </div>
            <div class="summary-card">
                <div class="label">Cash Available</div>
                <div class="value" id="cash">--</div>
                <div class="sub" style="color: var(--text-muted);" id="cash-pct">--</div>
            </div>
            <div class="summary-card">
                <div class="label">Invested Value</div>
                <div class="value" id="invested">--</div>
                <div class="sub" id="invested-pct" style="color: var(--text-muted);">--</div>
            </div>
            <div class="summary-card">
                <div class="label">Total P&L</div>
                <div class="value" id="total-pl">--</div>
                <div class="sub" id="total-pl-pct">--</div>
            </div>
        </div>

        <!-- Holdings Table -->
        <div class="section-title">📊 Current Holdings</div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Shares</th>
                        <th>Avg Cost</th>
                        <th>Current Price</th>
                        <th>Market Value</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                    </tr>
                </thead>
                <tbody id="holdings-body">
                    <tr><td colspan="7" class="empty-state"><div class="icon">📭</div>No holdings yet. Run the bot to start building your portfolio!</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Bottom Grid: Trades + Chart -->
        <div class="trades-grid">
            <div>
                <div class="section-title">⚡ Recent Trades</div>
                <div class="trade-feed">
                    <div class="trade-feed-header">Activity Log</div>
                    <div class="trade-list" id="trade-list">
                        <div class="empty-state" style="padding: 32px;"><div class="icon">📝</div>No trades yet</div>
                    </div>
                </div>
            </div>
            <div>
                <div class="section-title">📈 Portfolio Value Over Time</div>
                <div class="chart-card">
                    <div class="chart-header">Performance History</div>
                    <div class="chart-body">
                        <canvas id="chart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Weekly Reports -->
        <div class="reports-section">
            <div class="section-title">📋 Weekly Reports from the Bot</div>
            <div id="reports-container">
                <div class="empty-state" style="padding: 32px;"><div class="icon">🤖</div>No reports yet. The bot will write its first report after its first trading session.</div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script>
        const STARTING_CAPITAL = 50000;
        let chart = null;

        function formatMoney(n) {
            return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        function formatPct(n) {
            const sign = n >= 0 ? '+' : '';
            return sign + n.toFixed(2) + '%';
        }

        async function fetchData() {
            const resp = await fetch('/api/portfolio');
            return resp.json();
        }

        function renderSummary(data) {
            const { cash, total_value, invested_value, total_pl } = data;
            const plPct = invested_value > 0 ? (total_pl / (total_value - total_pl - cash)) * 100 : 0;
            const totalChange = total_value - STARTING_CAPITAL;
            const totalChangePct = (totalChange / STARTING_CAPITAL) * 100;

            document.getElementById('total-value').textContent = formatMoney(total_value);
            const changeEl = document.getElementById('total-change');
            changeEl.textContent = `${totalChange >= 0 ? '+' : ''}${formatMoney(totalChange)} (${formatPct(totalChangePct)}) from start`;
            changeEl.className = `sub ${totalChange >= 0 ? 'positive' : 'negative'}`;

            document.getElementById('cash').textContent = formatMoney(cash);
            document.getElementById('cash-pct').textContent = `${((cash / total_value) * 100).toFixed(1)}% of portfolio`;

            document.getElementById('invested').textContent = formatMoney(invested_value);
            document.getElementById('invested-pct').textContent = `${((invested_value / total_value) * 100).toFixed(1)}% of portfolio`;

            const plEl = document.getElementById('total-pl');
            plEl.textContent = `${total_pl >= 0 ? '+' : ''}${formatMoney(total_pl)}`;
            plEl.className = `value ${total_pl >= 0 ? 'positive' : 'negative'}`;

            const plPctEl = document.getElementById('total-pl-pct');
            const costBasis = invested_value - total_pl;
            const realPct = costBasis > 0 ? (total_pl / costBasis) * 100 : 0;
            plPctEl.textContent = formatPct(realPct) + ' return';
            plPctEl.className = `sub ${total_pl >= 0 ? 'positive' : 'negative'}`;
        }

        function renderHoldings(holdings) {
            const tbody = document.getElementById('holdings-body');
            if (!holdings || holdings.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><div class="icon">📭</div>No holdings yet. Run the bot to start building!</td></tr>';
                return;
            }

            tbody.innerHTML = holdings.map(h => {
                const pl = h.market_value - h.cost_basis;
                const plPct = h.cost_basis > 0 ? (pl / h.cost_basis) * 100 : 0;
                const cls = pl >= 0 ? 'positive' : 'negative';
                const pillCls = pl >= 0 ? 'pl-positive' : 'pl-negative';
                return `<tr>
                    <td class="ticker-cell">${h.ticker}</td>
                    <td>${h.shares}</td>
                    <td class="price-cell">${formatMoney(h.avg_cost)}</td>
                    <td class="price-cell">${formatMoney(h.current_price)}</td>
                    <td class="price-cell">${formatMoney(h.market_value)}</td>
                    <td><span class="pl-pill ${pillCls}">${pl >= 0 ? '+' : ''}${formatMoney(pl)}</span></td>
                    <td class="${cls}" style="font-weight:600;">${formatPct(plPct)}</td>
                </tr>`;
            }).join('');
        }

        function renderTrades(trades) {
            const list = document.getElementById('trade-list');
            if (!trades || trades.length === 0) {
                list.innerHTML = '<div class="empty-state" style="padding:32px"><div class="icon">📝</div>No trades yet</div>';
                return;
            }

            const recent = trades.slice(-20).reverse();
            list.innerHTML = recent.map(t => {
                const actionCls = t.action === 'BUY' ? 'trade-buy' : 'trade-sell';
                const dateStr = new Date(t.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                return `<div class="trade-item">
                    <span class="trade-action ${actionCls}">${t.action}</span>
                    <div class="trade-info">
                        <div class="trade-ticker">${t.ticker}</div>
                        <div class="trade-detail">${t.quantity} shares @ ${formatMoney(t.price)} = ${formatMoney(t.total)}</div>
                        ${t.reason ? `<div class="trade-reason">"${t.reason.substring(0, 100)}${t.reason.length > 100 ? '...' : ''}"</div>` : ''}
                    </div>
                    <div class="trade-date">${dateStr}</div>
                </div>`;
            }).join('');
        }

        function renderChart(history) {
            const ctx = document.getElementById('chart').getContext('2d');

            const labels = history.map(h => {
                const d = new Date(h.date);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            });
            const values = history.map(h => h.total_value);

            if (chart) chart.destroy();

            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(59, 130, 246, 0.15)');
            gradient.addColorStop(1, 'rgba(59, 130, 246, 0)');

            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Portfolio Value',
                        data: values,
                        borderColor: '#3b82f6',
                        backgroundColor: gradient,
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.3,
                        pointRadius: values.length > 20 ? 0 : 4,
                        pointBackgroundColor: '#3b82f6',
                        pointBorderColor: '#0a0e17',
                        pointBorderWidth: 2,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#1a2234',
                            borderColor: '#2a3549',
                            borderWidth: 1,
                            titleColor: '#e2e8f0',
                            bodyColor: '#8b95a5',
                            padding: 12,
                            callbacks: {
                                label: ctx => formatMoney(ctx.raw)
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#5a6577', font: { size: 11 } },
                            grid: { color: 'rgba(42, 53, 73, 0.4)' }
                        },
                        y: {
                            ticks: {
                                color: '#5a6577',
                                font: { size: 11 },
                                callback: v => '$' + (v/1000).toFixed(0) + 'k'
                            },
                            grid: { color: 'rgba(42, 53, 73, 0.4)' }
                        }
                    }
                }
            });
        }

        function renderReports(reports) {
            const container = document.getElementById('reports-container');
            if (!reports || reports.length === 0) {
                container.innerHTML = '<div class="empty-state" style="padding:32px"><div class="icon">🤖</div>No reports yet. The bot will write its first report after its first trading session.</div>';
                return;
            }

            const sorted = [...reports].reverse();
            container.innerHTML = sorted.map(r => {
                const dateStr = new Date(r.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
                const changeCls = r.change >= 0 ? 'pl-positive' : 'pl-negative';
                const changeSign = r.change >= 0 ? '+' : '';
                const body = r.summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').split('\\n').filter(p => p.trim()).map(p => `<p>${p}</p>`).join('');
                return `<div class="report-card">
                    <div class="report-header">
                        <div class="report-title">${r.title}</div>
                        <div class="report-meta">
                            <span class="report-change ${changeCls}">${changeSign}${formatMoney(r.change)} (${r.change_pct >= 0 ? '+' : ''}${r.change_pct.toFixed(2)}%)</span>
                            <span class="report-date">${dateStr}</span>
                        </div>
                    </div>
                    <div class="report-body">${body}</div>
                    <div class="report-value">Portfolio value at time of report: ${formatMoney(r.portfolio_value)}</div>
                </div>`;
            }).join('');
        }

        async function refresh() {
            try {
                const data = await fetchData();
                renderSummary(data);
                renderHoldings(data.holdings);
                renderTrades(data.trades);
                renderChart(data.history);
                renderReports(data.reports);
                document.getElementById('last-update').textContent =
                    new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            } catch (e) {
                console.error('Refresh failed:', e);
            }
        }

        // Initial load + auto-refresh every 60s
        refresh();
        setInterval(refresh, 60000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/portfolio')
def api_portfolio():
    portfolio = load_portfolio()
    tickers = list(portfolio["holdings"].keys())
    
    # Fetch live prices
    prices = get_live_prices(tickers) if tickers else {}
    
    # Build holdings list with P&L
    holdings = []
    total_invested = 0
    total_pl = 0
    
    for ticker, shares in portfolio["holdings"].items():
        current_price = prices.get(ticker, 0)
        cost_basis = portfolio.get("cost_basis", {}).get(ticker, 0)
        avg_cost = cost_basis / shares if shares > 0 else 0
        market_value = current_price * shares
        pl = market_value - cost_basis
        
        total_invested += market_value
        total_pl += pl
        
        holdings.append({
            "ticker": ticker,
            "shares": shares,
            "avg_cost": round(avg_cost, 2),
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "cost_basis": round(cost_basis, 2),
            "pl": round(pl, 2)
        })
    
    # Sort by market value descending
    holdings.sort(key=lambda x: x["market_value"], reverse=True)
    
    total_value = portfolio["cash"] + total_invested
    
    return jsonify({
        "cash": portfolio["cash"],
        "total_value": round(total_value, 2),
        "invested_value": round(total_invested, 2),
        "total_pl": round(total_pl, 2),
        "holdings": holdings,
        "trades": portfolio.get("trades", []),
        "history": portfolio.get("history", []),
        "reports": portfolio.get("reports", [])
    })

if __name__ == '__main__':
    print("\\n🚀 Swiss Trader Dashboard running at http://localhost:5050\\n")
    app.run(debug=True, host='0.0.0.0', port=5050)
