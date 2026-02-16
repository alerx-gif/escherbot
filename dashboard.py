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
NEWS_MEMORY_FILE = "news_memory.json"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}

def load_portfolio():
    data = load_json(PORTFOLIO_FILE)
    # Ensure default structure
    defaults = {
        "cash": 50000.0, 
        "holdings": {}, 
        "cost_basis": {}, 
        "trades": [], 
        "history": [],
        "reports": [],
        "market_mood": "Neutral"
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    return data

def load_news_memory():
    data = load_json(NEWS_MEMORY_FILE)
    if isinstance(data, list):
        return data
    return []

def get_live_prices(tickers):
    """Fetch current prices and day change for a list of tickers.
       Returns: { 'TICKER': {'price': 150.0, 'prev_close': 148.0} }
    """
    data = {}
    if not tickers:
        return data
    
    # We iterate individually because yf.download can be fragile
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            price = None
            prev_close = None
            
            # 1. Try fast_info (most reliable)
            if hasattr(stock, 'fast_info'):
                try:
                    info = stock.fast_info
                    p = info.last_price
                    pc = info.previous_close # strict snake_case for property access usually
                    
                    if p is not None:
                        price = p
                    if pc is not None:
                        prev_close = pc
                except:
                    pass
            
            # 2. Key Error or None? Try history (slower but fallback)
            if price is None:
                try:
                    hist = stock.history(period="2d", interval="1m") # need 2d for prev close potentially
                    if not hist.empty:
                        price = float(hist['Close'].iloc[-1])
                        # If we have 2 days, we might find prev close, otherwise use Open of today?
                        # This is tricky with 1m data for just today.
                        # Let's just trust fast_info for prev_close mostly.
                        # For fallback, maybe just omit day change.
                except:
                    pass
            
            if price is not None:
                data[ticker] = {
                    'price': round(price, 2),
                    'prev_close': round(prev_close, 2) if prev_close else None
                }
            else:
                print(f"Warning: Could not fetch price for {ticker}")

        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
        
    return data

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EscherBot Dashboard 2.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        :root {
            --bg-dark: #0B0E14;
            --bg-panel: #151A25;
            --bg-card: #1C2333;
            --accent-blue: #3B82F6;
            --accent-green: #10B981;
            --accent-red: #EF4444;
            --accent-purple: #8B5CF6;
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
        }
        
        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
        }
        
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        
        /* Glassmorphism adjustments */
        .glass-panel {
            background: rgba(21, 26, 37, 0.95);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .card-hover:hover {
            border-color: rgba(59, 130, 246, 0.5);
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.1);
        }
        
        .scroll-hide::-webkit-scrollbar { display: none; }
        .scroll-hide { -ms-overflow-style: none; scrollbar-width: none; }
        
        /* Custom Scrollbar for visible lists */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: #2D3748; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #4A5568; }

        .mood-bullish { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .mood-bearish { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .mood-neutral { background: rgba(139, 92, 246, 0.15); color: #A78BFA; border: 1px solid rgba(139, 92, 246, 0.3); }
    </style>
</head>
<body class="min-h-screen pb-12">

    <!-- TOP BAR -->
    <nav class="border-b border-gray-800 bg-[#0f1219] sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white">E</div>
                <h1 class="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">EscherBot <span class="text-xs text-gray-500 font-normal ml-1">v2.0</span></h1>
            </div>
            <div class="flex items-center gap-4 text-sm">
                <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900 border border-gray-800">
                    <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span class="text-gray-400">System Online</span>
                </div>
                <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900 border border-gray-800">
                    <span class="text-gray-500 font-bold">S&P 500:</span>
                    <span id="sp500-val" class="font-mono text-gray-300">Loading...</span>
                </div>
                <div id="last-update" class="text-gray-500 font-mono text-xs">Waiting...</div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-6 mt-8">
        
        <!-- PORTFOLIO OVERVIEW -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <!-- Total Equity -->
            <div class="glass-panel p-6 rounded-xl border border-gray-800 card-hover relative overflow-hidden group">
                <div class="absolute right-0 top-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                    <svg class="w-24 h-24" fill="currentColor" viewBox="0 0 20 20"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"></path></svg>
                </div>
                <div class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-1">Total Equity</div>
                <div id="total-equity" class="text-3xl font-bold text-white mb-2 font-mono">--</div>
                <div id="total-pl-pill" class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-300">
                    --
                </div>
            </div>

            <!-- Cash vs Invested -->
            <div class="glass-panel p-4 rounded-xl border border-gray-800 flex items-center gap-4">
                <div class="relative w-24 h-24 flex-shrink-0">
                    <canvas id="allocationChart"></canvas>
                </div>
                <div class="flex flex-col justify-center gap-2 text-sm">
                    <div class="flex items-center gap-2">
                        <div class="w-3 h-3 rounded-full bg-blue-500"></div>
                        <span class="text-gray-400">Cash: <span id="cash-val" class="text-gray-200 font-mono">--</span></span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-3 h-3 rounded-full bg-purple-500"></div>
                        <span class="text-gray-400">Invested: <span id="invested-val" class="text-gray-200 font-mono">--</span></span>
                    </div>
                </div>
            </div>

            <!-- Day's P&L (Simulated for now as total PL) -->
            <div class="glass-panel p-6 rounded-xl border border-gray-800 flex flex-col justify-center">
                 <div class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-1">Total P&L</div>
                 <div id="total-pl-value" class="text-2xl font-bold font-mono">--</div>
                 <div id="total-pl-pct" class="text-sm font-medium mt-1">--</div>
            </div>
            
            <!-- Market Mood -->
            <div class="glass-panel p-6 rounded-xl border border-gray-800 flex flex-col relative overflow-hidden">
                <div class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2 z-10 flex items-center justify-between">
                    AI Market Mood
                    <span id="mood-icon" class="text-lg">🤖</span>
                </div>
                
                <div class="z-10 flex flex-col h-full">
                    <div id="mood-primary" class="text-2xl font-bold mb-2 tracking-tight">NEUTRAL</div>
                    <div class="relative flex-grow">
                        <p id="mood-desc" class="text-xs text-gray-400 leading-relaxed overflow-y-auto max-h-[100px] scroll-hide">
                            Analysis pending...
                        </p>
                    </div>
                </div>
                
                <!-- Background Glow -->
                <div id="mood-glow" class="absolute -right-4 -top-4 w-32 h-32 rounded-full opacity-10 blur-2xl bg-purple-500 transition-colors duration-700"></div>
            </div>
            
             <!-- Alpha / Performance -->
            <div class="glass-panel p-6 rounded-xl border border-gray-800 flex flex-col justify-center items-center text-center relative overflow-hidden">
                <div class="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Alpha vs S&P 500</div>
                <div id="alpha-val" class="text-3xl font-bold font-mono text-white">--</div>
                <div id="alpha-badge" class="mt-2 text-xs font-bold px-2 py-1 rounded bg-gray-800 text-gray-400">
                    --
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            <!-- LEFT COLUMN: Portfolio & Trades (2/3 width) -->
            <div class="lg:col-span-2 flex flex-col gap-8">
                
                <!-- Weekly Report (Newspaper Style) -->
                <div id="latest-report-card" class="hidden glass-panel rounded-xl border border-gray-800 overflow-hidden cursor-pointer group hover:border-blue-500/50 transition-all relative">
                    <div class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                         <span class="text-6xl">📰</span>
                    </div>
                    <div class="p-6">
                        <div class="flex items-center gap-3 mb-3">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">WEEKLY INSIGHTS</span>
                            <span id="report-date" class="text-xs text-gray-500 font-mono">--</span>
                        </div>
                        <h2 id="report-title" class="text-2xl font-bold text-white mb-3 group-hover:text-blue-400 transition-colors">--</h2>
                        <p id="report-preview" class="text-gray-400 text-sm leading-relaxed line-clamp-3">--</p>
                        <div class="mt-4 flex items-center gap-2 text-xs font-medium text-blue-400 group-hover:translate-x-1 transition-transform">
                            READ FULL REPORT <span>→</span>
                        </div>
                    </div>
                </div>

                <!-- Active Holdings -->
                <div class="glass-panel rounded-xl border border-gray-800 overflow-hidden">
                    <div class="px-6 py-4 border-b border-gray-800 flex justify-between items-center bg-[#11141d]">
                        <h2 class="font-semibold text-gray-200 flex items-center gap-2">
                            <span class="text-xl">💼</span> Active Holdings
                        </h2>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm">
                            <thead class="bg-[#0b0e14] text-gray-400 uppercase text-xs">
                                <tr>
                                    <th class="px-6 py-3 font-medium">Ticker</th>
                                    <th class="px-6 py-3 font-medium text-right">Shares</th>
                                    <th class="px-6 py-3 font-medium text-right">Avg Cost</th>
                                    <th class="px-6 py-3 font-medium text-right">Price</th>
                                    <th class="px-6 py-3 font-medium text-right">Day Chg</th>
                                    <th class="px-6 py-3 font-medium text-right">% Port</th>
                                    <th class="px-6 py-3 font-medium text-right">P&L</th>
                                </tr>
                            </thead>
                            <tbody id="holdings-list" class="divide-y divide-gray-800 text-gray-300">
                                <!-- Populated by JS -->
                                <tr><td colspan="6" class="px-6 py-8 text-center text-gray-500">Loading holdings...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Trade History -->
                <div class="glass-panel rounded-xl border border-gray-800 overflow-hidden">
                    <div class="px-6 py-4 border-b border-gray-800 bg-[#11141d]">
                        <h2 class="font-semibold text-gray-200 flex items-center gap-2">
                            <span class="text-xl">⚡</span> Trade History
                        </h2>
                    </div>
                    <div id="trade-history-list" class="max-h-[400px] overflow-y-auto divide-y divide-gray-800">
                        <!-- Populated by JS -->
                         <div class="px-6 py-8 text-center text-gray-500">No trades recorded yet.</div>
                    </div>
                </div>
                
                <!-- Performance Chart -->
                <div class="glass-panel rounded-xl border border-gray-800 overflow-hidden p-6">
                    <h2 class="font-semibold text-gray-200 mb-4 flex items-center gap-2"><span class="text-xl">📈</span> Performance vs Benchmark</h2>
                    <div class="h-64 w-full">
                        <canvas id="historyChart"></canvas>
                    </div>
                </div>

            </div>

            <!-- RIGHT COLUMN: The Brain (1/3 width) -->
            <div class="flex flex-col gap-6">
                
                <!-- Market Pulse (News) -->
                <div class="glass-panel rounded-xl border border-gray-800 overflow-hidden flex flex-col h-full max-h-[800px]">
                    <div class="px-6 py-4 border-b border-gray-800 bg-[#11141d]">
                        <h2 class="font-semibold text-gray-200 flex items-center gap-2">
                            <span class="text-xl">🧠</span> Market Pulse
                        </h2>
                        <p class="text-xs text-gray-500 mt-1">Top news driving AI decisions</p>
                    </div>
                    <div id="news-feed" class="overflow-y-auto p-4 flex flex-col gap-4">
                        <!-- Populated by JS -->
                        <div class="text-center text-gray-500 py-4">Scanning market...</div>
                    </div>
                </div>

            </div>
        </div>

        <!-- FOOTER -->
        <div class="mt-12 text-center text-gray-600 text-sm pb-8">
            <p>EscherBot 2.0 • Autonomous Trading Agent</p>
        </div>
    </div>
    
    <!-- REPORT MODAL -->
    <div id="report-modal" class="fixed inset-0 z-[100] hidden flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" onclick="closeModal()"></div>
        <div class="glass-panel w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl border border-gray-700 shadow-2xl relative z-10 animate-[fadeIn_0.2s_ease-out]">
            <div class="p-6 border-b border-gray-800 flex justify-between items-start bg-[#11141d]">
                <div>
                     <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">WEEKLY INSIGHTS</span>
                     <h2 id="modal-title" class="text-2xl font-bold text-white mt-2">--</h2>
                     <div id="modal-date" class="text-sm text-gray-500 mt-1 font-mono">--</div>
                </div>
                <button onclick="closeModal()" class="p-2 hover:bg-gray-800 rounded-full text-gray-400 hover:text-white transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="p-8 overflow-y-auto rich-text text-gray-300 leading-relaxed text-lg" id="modal-content">
                --
            </div>
            <div class="p-4 border-t border-gray-800 bg-[#11141d] flex justify-between items-center text-xs text-gray-500">
                <span>Generated by EscherBot AI</span>
                <span id="modal-perf">--</span>
            </div>
        </div>
    </div>

    <!-- MAIN SCRIPT -->
    <script>
        // --- UTILS ---
        const fmtMoney = (n) => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const fmtPct = (n) => (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
        
        let allocChart = null;
        let histChart = null;

        // --- RENDER FUNCTIONS ---

        function renderAllocationChart(cash, invested) {
            const ctx = document.getElementById('allocationChart').getContext('2d');
            if (allocChart) allocChart.destroy();
            
            allocChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Cash', 'Invested'],
                    datasets: [{
                        data: [cash, invested],
                        backgroundColor: ['#3B82F6', '#8B5CF6'],
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    cutout: '70%',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: false } }
                }
            });
        }

        function renderHistoryChart(history) {
             const ctx = document.getElementById('historyChart').getContext('2d');
             
             // Normalize to % change from start
             if (!history.length) return;
             
             const startVal = history[0].total_value;
             let startSP = history[0].sp500 || 0;
             
             // Find first valid SP500 value if missing in first record
             if (!startSP) {
                 const firstWithSP = history.find(h => h.sp500);
                 if (firstWithSP) startSP = firstWithSP.sp500;
             }

             const labels = history.map(h => new Date(h.date).toLocaleDateString());
             
             const dataPortfolio = history.map(h => ((h.total_value - startVal) / startVal) * 100);
             const dataSP500 = history.map(h => {
                 if (!h.sp500 || !startSP) return 0; // or null
                 return ((h.sp500 - startSP) / startSP) * 100;
             });

             // Calculate Alpha (latest)
             const lastP = dataPortfolio[dataPortfolio.length - 1] || 0;
             const lastS = dataSP500[dataSP500.length - 1] || 0;
             const alpha = lastP - lastS;
             
             document.getElementById('alpha-val').textContent = fmtPct(alpha);
             document.getElementById('alpha-val').className = `text-3xl font-bold font-mono ${alpha >= 0 ? 'text-green-400' : 'text-red-400'}`;
             
             const badge = document.getElementById('alpha-badge');
             badge.textContent = alpha >= 0 ? 'OUTPERFORMING' : 'UNDERPERFORMING';
             badge.className = `mt-2 text-[10px] font-bold px-2 py-0.5 rounded tracking-wider ${alpha >= 0 ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`;
             
             if (histChart) histChart.destroy();

             histChart = new Chart(ctx, {
                 type: 'line',
                 data: {
                     labels: labels,
                     datasets: [
                        {
                             label: 'My Portfolio (%)',
                             data: dataPortfolio,
                             borderColor: '#3B82F6',
                             backgroundColor: 'rgba(59, 130, 246, 0.1)',
                             fill: true,
                             tension: 0.4,
                             pointRadius: 3,
                             borderWidth: 2
                         },
                         {
                             label: 'S&P 500 (%)',
                             data: dataSP500,
                             borderColor: '#6B7280', // Gray
                             borderDash: [5, 5],
                             backgroundColor: 'transparent',
                             fill: false,
                             tension: 0.4,
                             pointRadius: 0,
                             borderWidth: 2
                         }
                     ]
                 },
                 options: {
                     responsive: true,
                     maintainAspectRatio: false,
                     interaction: { intersect: false, mode: 'index' },
                     scales: {
                         x: { display: false },
                         y: { 
                             grid: { color: '#1f2937' }, 
                             ticks: { color: '#9ca3af', callback: (v) => v + '%' } 
                         }
                     },
                     plugins: {
                         legend: { display: true, labels: { color: '#9ca3af', font: { size: 10 } } },
                         tooltip: { 
                             callbacks: { label: (ctx) => ctx.dataset.label + ': ' + ctx.raw.toFixed(2) + '%' }
                         }
                     }
                 }
             });
        }

        function updateMood(mood) {
            const primaryEl = document.getElementById('mood-primary');
            const descEl = document.getElementById('mood-desc');
            const glowEl = document.getElementById('mood-glow');
            const iconEl = document.getElementById('mood-icon');
            
            descEl.textContent = mood;
            
            const m = mood.toLowerCase();
            let colorClass = 'text-purple-400';
            let bgClass = 'bg-purple-500';
            let status = 'NEUTRAL';
            let icon = '⚖️';
            
            if (m.includes('bull')) {
                colorClass = 'text-green-400';
                bgClass = 'bg-green-500';
                status = 'BULLISH';
                icon = '🚀';
            } else if (m.includes('bear')) {
                colorClass = 'text-red-400';
                bgClass = 'bg-red-500';
                status = 'BEARISH';
                icon = '🐻';
            } else if (m.includes('uncertain') || m.includes('mixed')) {
                status = 'UNCERTAIN';
                icon = '🤔';
            }
            
            primaryEl.className = `text-2xl font-bold mb-2 tracking-tight ${colorClass}`;
            primaryEl.textContent = status;
            
            iconEl.textContent = icon;
            
            // Remove old bg classes and add new one
            glowEl.className = `absolute -right-4 -top-4 w-32 h-32 rounded-full opacity-10 blur-2xl transition-colors duration-700 ${bgClass}`;
        }

        function renderHoldings(holdings, totalValue) {
            const container = document.getElementById('holdings-list');
            if (!holdings.length) {
                container.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-gray-500">
                    <div class="text-2xl mb-2">📭</div>
                    No holdings yet. Waiting for entry signals.
                </td></tr>`;
                return;
            }
            
            container.innerHTML = holdings.map(h => {
                const plColor = h.pl >= 0 ? 'text-green-400' : 'text-red-400';
                const plBg = h.pl >= 0 ? 'bg-green-500/10' : 'bg-red-500/10';
                const pctPort = totalValue > 0 ? (h.market_value / totalValue) * 100 : 0;
                
                const dayChgColor = h.day_change_pct >= 0 ? 'text-green-400' : 'text-red-400';
                
                return `<tr class="hover:bg-gray-800/30 transition-colors">
                    <td class="px-6 py-4">
                        <div class="font-bold text-blue-400">${h.ticker}</div>
                    </td>
                    <td class="px-6 py-4 text-right font-mono text-gray-300">${h.shares}</td>
                    <td class="px-6 py-4 text-right font-mono text-gray-400">${fmtMoney(h.avg_cost)}</td>
                    <td class="px-6 py-4 text-right font-mono text-gray-200">${fmtMoney(h.current_price)}</td>
                    <td class="px-6 py-4 text-right font-mono ${dayChgColor}">${fmtPct(h.day_change_pct)}</td>
                    <td class="px-6 py-4 text-right font-mono text-gray-300">${fmtPct(pctPort)}</td>
                    <td class="px-6 py-4 text-right">
                        <div class="flex flex-col items-end">
                            <span class="${plColor} font-bold font-mono">${fmtMoney(h.pl)}</span>
                            <span class="${plColor} text-xs">${fmtPct(h.pl_pct)}</span>
                        </div>
                    </td>
                </tr>`;
            }).join('');
        }

        function renderTrades(trades) {
            const container = document.getElementById('trade-history-list');
            if (!trades.length) {
                container.innerHTML = '<div class="px-6 py-8 text-center text-gray-500">No trades yet.</div>';
                return;
            }
            
            // Show last 50
            const recent = trades.slice().reverse().slice(0, 50);
            
            container.innerHTML = recent.map(t => {
                const isBuy = t.action === 'BUY';
                const badgeClass = isBuy ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20';
                const date = new Date(t.date).toLocaleString(undefined, { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' });
                
                return `<div class="px-6 py-4 hover:bg-gray-800/30 transition-colors group">
                    <div class="flex justify-between items-start mb-1">
                        <div class="flex items-center gap-3">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeClass}">${t.action}</span>
                            <span class="font-bold text-gray-200">${t.ticker}</span>
                            <span class="text-xs text-gray-500">${t.quantity} @ ${fmtMoney(t.price)}</span>
                        </div>
                        <span class="text-xs text-gray-600 font-mono">${date}</span>
                    </div>
                    ${t.reason ? `
                    <div class="mt-2 text-xs text-gray-500 leading-relaxed pl-2 border-l-2 border-gray-800">
                        ${t.reason}
                    </div>` : ''}
                </div>`;
            }).join('');
        }

        function renderNews(news) {
            const container = document.getElementById('news-feed');
            if (!news || !news.length) {
                container.innerHTML = '<div class="text-center text-gray-500 py-4">No news in memory.</div>';
                return;
            }
            
            // Sort by importance
            const sorted = news.slice().sort((a,b) => b.importance - a.importance);
            
            container.innerHTML = sorted.map(n => {
                const heat = n.importance >= 8 ? 'bg-red-500' : (n.importance >= 6 ? 'bg-orange-500' : 'bg-blue-500');
                return `<div class="p-4 rounded-lg bg-[#151A25] border border-gray-800 hover:border-gray-700 transition-colors">
                    <div class="flex justify-between items-start mb-2 gap-2">
                        <div class="flex items-center gap-2">
                            <div class="w-1.5 h-1.5 rounded-full ${heat}"></div>
                            <span class="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Impact: ${n.importance}/10</span>
                        </div>
                        <span class="text-[10px] text-gray-600">${n.date}</span>
                    </div>
                    <h3 class="text-sm font-semibold text-gray-200 leading-snug mb-2">${n.headline}</h3>
                    <p class="text-xs text-gray-500 leading-relaxed mb-3">${n.summary}</p>
                    ${n.tickers && n.tickers.length ? `
                        <div class="flex flex-wrap gap-1">
                            ${n.tickers.map(t => `<span class="px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 text-[10px] border border-gray-700">${t}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>`;
            }).join('');
        }

        let latestReportData = null;

        function openModal() {
            if(!latestReportData) return;
            document.getElementById('modal-title').textContent = latestReportData.title;
            document.getElementById('modal-date').textContent = new Date(latestReportData.date).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            
            // Convert markdown-ish bold to strong tags
            let content = latestReportData.summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Convert newlines to paragraphs
            content = content.split('\\n').filter(p => p.trim()).map(p => `<p class="mb-4">${p}</p>`).join('');
            
            document.getElementById('modal-content').innerHTML = content;
            document.getElementById('modal-perf').textContent = `Portfolio Value: ${fmtMoney(latestReportData.portfolio_value)} (${fmtPct(latestReportData.change_pct || 0)} change)`;
            
            document.getElementById('report-modal').classList.remove('hidden');
        }

        function closeModal() {
            document.getElementById('report-modal').classList.add('hidden');
        }

        // Close on Escape key
        document.addEventListener('keydown', (e) => { if(e.key === 'Escape') closeModal(); });

        function renderReportCard(reports) {
            const card = document.getElementById('latest-report-card');
            
            if (!reports || !reports.length) {
                card.classList.add('hidden');
                return;
            }
            
            const r = reports[reports.length - 1]; // Get latest
            latestReportData = r;
            
            document.getElementById('report-title').textContent = r.title;
            document.getElementById('report-date').textContent = new Date(r.date).toLocaleDateString();
            document.getElementById('report-preview').textContent = r.summary.replace(/\*\*/g, ''); // strip markdown
            
            card.onclick = openModal;
            card.classList.remove('hidden');
        }

        async function refresh() {
            try {
                const res = await fetch('/api/portfolio');
                const data = await res.json();
                
                // Top Bar / Stats
                document.getElementById('total-equity').textContent = fmtMoney(data.total_value);
                document.getElementById('total-pl-value').textContent = (data.total_pl >= 0 ? '+' : '') + fmtMoney(data.total_pl);
                document.getElementById('total-pl-value').className = `text-2xl font-bold font-mono ${data.total_pl >= 0 ? 'text-green-400' : 'text-red-400'}`;
                
                const plPct = data.invested_value > 0 ? (data.total_pl / (data.invested_value - data.total_pl)) * 100 : 0;
                document.getElementById('total-pl-pct').textContent = fmtPct(plPct) + ' return on invested';
                document.getElementById('total-pl-pct').className = `text-sm font-medium mt-1 ${plPct >= 0 ? 'text-green-500' : 'text-red-500'}`;
                
                document.getElementById('cash-val').textContent = fmtMoney(data.cash);
                document.getElementById('invested-val').textContent = fmtMoney(data.invested_value);
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                
                if (data.sp500_price) {
                    document.getElementById('sp500-val').textContent = fmtMoney(data.sp500_price);
                } else {
                    document.getElementById('sp500-val').textContent = "--";
                }

                renderAllocationChart(data.cash, data.invested_value);
                updateMood(data.market_mood || 'Neutral');
                renderHoldings(data.holdings, data.total_value);
                renderTrades(data.trades);
                renderNews(data.news_memory);
                renderHistoryChart(data.history || []);
                renderReportCard(data.reports);

            } catch (e) {
                console.error("Refresh failed", e);
            }
        }

        // Init
        refresh();
        setInterval(refresh, 30000); // 30s auto refresh

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
    news_memory = load_news_memory()
    
    tickers = list(portfolio["holdings"].keys())
    # Add S&P 500 to fetch list
    tickers_to_fetch = tickers + ["^GSPC"]
    live_data = get_live_prices(tickers_to_fetch)
    
    # Extract S&P 500 data
    sp500_info = live_data.get("^GSPC", {})
    sp500_price = sp500_info.get('price', 0)
    
    holdings_data = []
    total_invested = 0
    total_pl = 0
    
    for ticker, shares in portfolio["holdings"].items():
        if shares <= 0: continue
        
        info = live_data.get(ticker, {})
        current_price = info.get('price', 0)
        prev_close = info.get('prev_close', None)
        
        cost_basis_total = portfolio.get("cost_basis", {}).get(ticker, 0)
        avg_cost = cost_basis_total / shares
        
        # If fetch failed, fallback
        if current_price == 0:
            current_price = avg_cost 

        market_val = shares * current_price
        pl = market_val - cost_basis_total
        pl_pct = (pl / cost_basis_total) * 100 if cost_basis_total > 0 else 0
        
        # Day Change Calculation
        day_change_pct = 0
        if prev_close and prev_close > 0:
            day_change_pct = ((current_price - prev_close) / prev_close) * 100
        
        holdings_data.append({
            "ticker": ticker,
            "shares": shares,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "market_value": market_val,
            "pl": pl,
            "pl_pct": pl_pct,
            "day_change_pct": day_change_pct
        })
        
        total_invested += market_val
        total_pl += pl
        
    total_value = portfolio["cash"] + total_invested
    
    response = {
        "cash": portfolio["cash"],
        "total_value": total_value,
        "invested_value": total_invested,
        "total_pl": total_pl,
        "holdings": holdings_data,
        "trades": portfolio.get("trades", []),
        "market_mood": portfolio.get("market_mood", "Neutral"),
        "news_memory": news_memory,
        "history": portfolio.get("history", []),
        "reports": portfolio.get("reports", []),
        "sp500_price": sp500_price
    }
    
    return jsonify(response)

if __name__ == '__main__':
    print("🚀 EscherBot Dashboard v2.0 running on http://localhost:5050")
    app.run(host='0.0.0.0', port=5050, debug=True)
