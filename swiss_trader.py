import os
import json
import time
import datetime
import random
import argparse
import yfinance as yf
import feedparser
from google import genai
from google.genai import types

# Configuration — API key loaded from .env file (never commit secrets!)
def load_env():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env()
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found. Create a .env file with: GEMINI_API_KEY=your-key-here")
    exit(1)
PORTFOLIO_FILE = "portfolio.json"
STARTING_CAPITAL = 50000.0

# ═══════════════════════════════════════════════
# RISK MANAGEMENT RULES (Hard-coded, AI can't override)
# ═══════════════════════════════════════════════
MAX_POSITION_PCT = 0.10       # Max 10% of portfolio in a single stock
MIN_CASH_RESERVE_PCT = 0.15   # Always keep at least 15% cash
STOP_LOSS_PCT = -0.10         # Auto-sell if a position drops 10%
TAKE_PROFIT_PCT = 0.20        # Auto-sell if a position gains 20%
MAX_POSITIONS = 12            # Max 12 concurrent positions
MIN_TRADE_VALUE = 500         # Don't bother with trades under $500

# Expanded Universe for Discovery (Fallback if news yields nothing)
UNIVERSE = [
    # US Tech
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "AMD", "INTC", "CSCO",
    # US Finance
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP",
    # US Healthcare
    "JNJ", "PFE", "MRK", "ABBV", "LLY", "UNH", "CVS",
    # US Energy
    "XOM", "CVX", "COP", "SLB", "EOG",
    # US Consumer
    "PG", "KO", "PEP", "WMT", "COST", "TGT",
    # US Media/Telecom
    "DIS", "NFLX", "CMCSA", "TMUS", "VZ", "T",
    # EU / Swiss - Major Stocks (US-listed ADRs & tickers)
    "SAP",    # SAP SE (Germany) - Tech
    "ASML",   # ASML (Netherlands) - Semiconductors
    "NVO",    # Novo Nordisk (Denmark) - Pharma
    "AZN",    # AstraZeneca (UK) - Pharma
    "SHEL",   # Shell (Netherlands/UK) - Energy
    "TTE",    # TotalEnergies (France) - Energy
    "UL",     # Unilever (UK/Netherlands) - Consumer
    "DEO",    # Diageo (UK) - Consumer
    "SNY",    # Sanofi (France) - Pharma
    "STLA",   # Stellantis (Netherlands) - Auto
    "ERIC",   # Ericsson (Sweden) - Telecom
    "NOK",    # Nokia (Finland) - Telecom
    "DB",     # Deutsche Bank (Germany) - Finance
    "ING",    # ING Group (Netherlands) - Finance
    "UBS",    # UBS (Switzerland) - Finance
    "CS",     # Credit Suisse / successor (Switzerland)
    "SPOT",   # Spotify (Sweden) - Tech
    "SHOP",   # Shopify - Tech
    "ARM",    # ARM Holdings (UK) - Semiconductors
    "GSK",    # GSK (UK) - Pharma
    "SIE.DE", # Siemens (Germany) - Industrial
    "BAS.DE", # BASF (Germany) - Chemicals
    "AIR.PA", # Airbus (France) - Aerospace
    "OR.PA",  # L'Oréal (France) - Consumer
    "MC.PA",  # LVMH (France) - Luxury
    "NESN.SW",# Nestlé (Switzerland) - Consumer
    "ROG.SW", # Roche (Switzerland) - Pharma
    "NOVN.SW",# Novartis (Switzerland) - Pharma
]

# RSS Feeds for Market Intelligence (keep it lean for free tier)
RSS_FEEDS = {
    "CNBC Top News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "MarketWatch Top": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "Reddit r/stocks": "https://www.reddit.com/r/stocks/hot.json?limit=5",
    "DW Business": "https://rss.dw.com/xml/rss-en-bus",
    "Investing.com News": "https://www.investing.com/rss/news.rss",
}

class PortfolioManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self.load()

    def load(self):
        """Loads the portfolio from a JSON file, or initializes a new one."""
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                data = json.load(f)
                if "trades" not in data:
                    data["trades"] = []
                if "cost_basis" not in data:
                    data["cost_basis"] = {}
                return data
        else:
            return {
                "cash": 50000.0,
                "holdings": {},
                "cost_basis": {},
                "trades": [],
                "history": []
            }

    def save(self):
        """Saves the portfolio to a JSON file."""
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_holdings_tickers(self):
        return list(self.data["holdings"].keys())

    def update_history(self, current_prices):
        total_value = self.data["cash"]
        for ticker, qty in self.data["holdings"].items():
            if ticker in current_prices:
                total_value += qty * current_prices[ticker]
            # If price unavailable, use last known value implies risk, 
            # but for now we skip or assume 0 change (not implemented here for brevity)

        self.data["history"].append({
            "date": str(datetime.datetime.now()),
            "total_value": total_value
        })
        return total_value

class MarketScanner:
    def __init__(self, client):
        self.client = client

    def fetch_market_news(self):
        """Fetches news from major indices to find trending topics."""
        print("🔍 Scanning Yahoo Finance for market news...")
        market_tickers = ["^GSPC", "^IXIC"] # S&P 500, Nasdaq
        all_news = []
        
        for ticker in market_tickers:
            try:
                stock = yf.Ticker(ticker)
                news = stock.news
                if news:
                    for n in news[:3]: # Top 3 stories per index
                        title = n.get('content', {}).get('title') or n.get('title')
                        if title:
                            all_news.append(title)
            except Exception as e:
                print(f"⚠️ Error fetching market news for {ticker}: {e}")

        return all_news

    def fetch_rss_headlines(self):
        """Fetches headlines from financial RSS feeds and Reddit."""
        print("📡 Scanning RSS feeds (CNBC, Reuters, MarketWatch, Reddit)...")
        all_headlines = []
        
        for source_name, url in RSS_FEEDS.items():
            try:
                if "reddit.com" in url:
                    # Reddit uses JSON, not RSS
                    import urllib.request
                    req = urllib.request.Request(url, headers={'User-Agent': 'SwissTrader/1.0'})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode())
                        posts = data.get('data', {}).get('children', [])
                        for post in posts[:5]:
                            title = post.get('data', {}).get('title', '')
                            if title:
                                all_headlines.append(f"[{source_name}] {title}")
                    continue

                feed = feedparser.parse(url)
                entries = feed.entries[:5]  # Top 5 per feed
                for entry in entries:
                    title = entry.get('title', '').strip()
                    if title:
                        all_headlines.append(f"[{source_name}] {title}")
                        
                print(f"   ✅ {source_name}: {len(entries)} headlines")
            except Exception as e:
                print(f"   ⚠️ {source_name}: Failed ({e})")
        
        print(f"📰 Total RSS headlines gathered: {len(all_headlines)}")
        return all_headlines

    def extract_tickers_from_news(self, news_items):
        """Uses Gemini to identify interesting tickers from news headlines."""
        if not news_items:
            return []

        prompt = f"""
        Analyze these financial news headlines and extract a list of stock tickers 
        that are mentioned or implied to be 'in play' (e.g., earnings, mergers, big moves).
        
        Headlines:
        {json.dumps(news_items, indent=2)}
        
        Output ONLY a JSON list of strings, e.g. ["AAPL", "TSLA"].
        If none found, return [].
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ Error extracting tickers from news: {e}")
            return []

    def get_discovery_list(self, owned_tickers):
        """Generates a list of tickers to analyze (Owned + News + RSS + Random Universe)."""
        # 1. Always check what we own
        targets = set(owned_tickers)
        
        # 2. Check Yahoo Finance news for hot stocks
        yf_news = self.fetch_market_news()
        
        # 3. Fetch RSS headlines from financial sites
        rss_headlines = self.fetch_rss_headlines()
        
        # 4. Combine all headlines and send ONE batch to Gemini
        all_headlines = yf_news + rss_headlines
        # Cap total headlines to keep Gemini prompt lean
        if len(all_headlines) > 30:
            all_headlines = all_headlines[:30]
        print(f"📊 Total headlines for analysis: {len(all_headlines)}")
        
        news_tickers = self.extract_tickers_from_news(all_headlines)
        if news_tickers:
            print(f"🧩 Gemini found interesting tickers in news: {news_tickers}")
            targets.update(news_tickers)
        
        # 5. Add random sample from Universe to keep discovering new things
        needed = 15 - len(targets)
        if needed > 0:
            sample = random.sample(UNIVERSE, min(needed, len(UNIVERSE)))
            targets.update(sample)
            
        return list(targets)

def fetch_detailed_data(ticker):
    """Fetches price and specific news for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        # Fast info fetch
        info = stock.fast_info
        last_price = info.last_price if info.last_price else stock.history(period="1d")['Close'].iloc[-1]
        
        # Get specific news
        news = stock.news
        top_news = []
        if news:
            for n in news[:3]:
                title = n.get('content', {}).get('title') or n.get('title')
                if title:
                    top_news.append(title)

        return {
            "ticker": ticker,
            "price": last_price,
            "news": top_news
        }
    except Exception as e:
        # print(f"⚠️ Could not fetch data for {ticker}: {e}") # specific error logging can be noisy
        return None

def get_trading_decisions(client, market_data_list, portfolio_state, total_portfolio_value):
    """Sends all data to Gemini for a holistic portfolio decision."""
    
    # Calculate context for the AI
    num_positions = len(portfolio_state['holdings'])
    cash_pct = (portfolio_state['cash'] / total_portfolio_value * 100) if total_portfolio_value > 0 else 100
    max_buy_amount = min(
        portfolio_state['cash'] - (total_portfolio_value * MIN_CASH_RESERVE_PCT),
        total_portfolio_value * MAX_POSITION_PCT
    )
    max_buy_amount = max(max_buy_amount, 0)
    slots_available = MAX_POSITIONS - num_positions
    
    # Build cost basis context for the AI
    holdings_detail = {}
    for ticker, shares in portfolio_state['holdings'].items():
        cb = portfolio_state.get('cost_basis', {}).get(ticker, 0)
        avg = cb / shares if shares > 0 else 0
        holdings_detail[ticker] = {
            "shares": shares,
            "avg_cost": round(avg, 2),
            "cost_basis": round(cb, 2)
        }
    
    prompt = f"""
    You are an Aggressive Growth Swing Trader managing a ${total_portfolio_value:.0f} portfolio.
    Your goal is to OUTPERFORM the S&P 500 by finding high-conviction momentum plays.
    
    ════════════════════════════════
    YOUR TRADING PHILOSOPHY
    ════════════════════════════════
    - You are GROWTH-ORIENTED and willing to take CALCULATED risks for higher returns.
    - You look for stocks with STRONG CATALYSTS: earnings beats, sector momentum, 
      breakout patterns, analyst upgrades, new product launches, M&A activity.
    - You are NOT a passive index investor. You actively hunt for 5-20% swing trades.
    - You prefer stocks that are TRENDING UP with news-driven catalysts.
    - You are willing to concentrate into high-conviction ideas — quality over diversification.
    - You cut losers FAST and let winners run. Don't hold onto hope.
    
    ════════════════════════════════
    CURRENT PORTFOLIO STATE
    ════════════════════════════════
    Cash: ${portfolio_state['cash']:.2f} ({cash_pct:.1f}% of portfolio)
    Holdings: {json.dumps(holdings_detail, indent=2)}
    Open Positions: {num_positions}/{MAX_POSITIONS}
    Slots Available: {slots_available}
    Max Buy Amount (per trade): ${max_buy_amount:.2f}
    
    ════════════════════════════════
    YOUR RULES (MUST FOLLOW)
    ════════════════════════════════
    1. BUY only if you have genuine conviction — don't buy just to be active.
       - Calculate quantity so the total cost stays UNDER ${max_buy_amount:.2f}.
       - Only BUY if slots_available > 0 (currently: {slots_available}).
       - Minimum trade size: ${MIN_TRADE_VALUE} (don't suggest tiny positions).
    2. SELL if:
       - The thesis is broken (bad news, missed earnings, sector downturn).
       - You've hit your target gain and want to lock profits.
       - You want to FREE UP CASH for a better opportunity.
       - Sell with quantity. You can do partial sells to lock in some profit.
    3. HOLD if the thesis is intact and you're waiting for the catalyst to play out.
    4. Be SPECIFIC in your reasoning — mention the actual news or catalyst.
    5. Prefer momentum — stocks making new highs with volume are better bets than 
       bargain hunting in falling knives.
    
    ════════════════════════════════
    MARKET INTELLIGENCE
    ════════════════════════════════
    {json.dumps(market_data_list, indent=2)}
    
    ════════════════════════════════
    OUTPUT FORMAT (strict JSON)
    ════════════════════════════════
    {{
        "market_mood": "bullish/bearish/neutral — one sentence on overall sentiment",
        "decisions": [
            {{ "ticker": "AAPL", "action": "BUY", "quantity": 15, "confidence": "high", "reason": "..." }},
            {{ "ticker": "MSFT", "action": "HOLD", "quantity": 0, "confidence": "medium", "reason": "..." }},
            {{ "ticker": "TSLA", "action": "SELL", "quantity": 10, "confidence": "high", "reason": "..." }}
        ]
    }}
    
    Confidence levels: "high" (>80% sure), "medium" (50-80%), "low" (<50%).
    Only act on "high" and "medium" confidence ideas. Skip "low" confidence.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        result = json.loads(response.text)
        mood = result.get('market_mood', 'unknown')
        print(f"   🌡️ Market Mood: {mood}")
        return result
    except Exception as e:
        print(f"❌ Error getting decision from Gemini: {e}")
        return {"decisions": []}

def execute_trade(decision, portfolio_mgr, current_prices, total_portfolio_value, dry_run=False):
    """Executes a single trade decision with risk management guardrails."""
    ticker = decision["ticker"]
    action = decision["action"]
    quantity = decision.get("quantity", 0)
    reason = decision.get("reason", "No reason provided")
    confidence = decision.get("confidence", "medium")
    
    # Skip low confidence trades
    if confidence == "low":
        print(f"⏭️ SKIP {ticker}: Low confidence — not worth the risk.")
        return
    
    price = current_prices.get(ticker)
    if not price:
        print(f"⚠️ Skipped {action} {ticker}: Price unavailable.")
        return

    pf = portfolio_mgr.data

    if action == "BUY":
        cost = price * quantity
        
        # GUARDRAIL: Minimum trade size
        if cost < MIN_TRADE_VALUE:
            print(f"⚠️ SKIP BUY {ticker}: Trade too small (${cost:.2f} < ${MIN_TRADE_VALUE}).")
            return
        
        # GUARDRAIL: Cash reserve
        cash_after = pf["cash"] - cost
        min_cash = total_portfolio_value * MIN_CASH_RESERVE_PCT
        if cash_after < min_cash:
            # Try to reduce quantity to respect cash reserve
            available_cash = pf["cash"] - min_cash
            if available_cash >= MIN_TRADE_VALUE:
                quantity = int(available_cash / price)
                cost = price * quantity
                if quantity <= 0:
                    print(f"⚠️ SKIP BUY {ticker}: Would breach {MIN_CASH_RESERVE_PCT*100:.0f}% cash reserve.")
                    return
                print(f"   📏 Adjusted quantity to {quantity} to maintain cash reserve.")
            else:
                print(f"⚠️ SKIP BUY {ticker}: Would breach {MIN_CASH_RESERVE_PCT*100:.0f}% cash reserve.")
                return
        
        # GUARDRAIL: Max position size
        existing_value = pf["holdings"].get(ticker, 0) * price
        max_position = total_portfolio_value * MAX_POSITION_PCT
        if existing_value + cost > max_position:
            allowed = max_position - existing_value
            if allowed >= MIN_TRADE_VALUE:
                quantity = int(allowed / price)
                cost = price * quantity
                if quantity <= 0:
                    print(f"⚠️ SKIP BUY {ticker}: Would exceed {MAX_POSITION_PCT*100:.0f}% position limit.")
                    return
                print(f"   📏 Adjusted quantity to {quantity} to stay within position limit.")
            else:
                print(f"⚠️ SKIP BUY {ticker}: Would exceed {MAX_POSITION_PCT*100:.0f}% position limit.")
                return
        
        # GUARDRAIL: Max positions
        if ticker not in pf["holdings"] and len(pf["holdings"]) >= MAX_POSITIONS:
            print(f"⚠️ SKIP BUY {ticker}: Already at max {MAX_POSITIONS} positions.")
            return
        
        if pf["cash"] >= cost:
            if not dry_run:
                pf["cash"] -= cost
                old_qty = pf["holdings"].get(ticker, 0)
                old_cost = pf["cost_basis"].get(ticker, 0)
                pf["holdings"][ticker] = old_qty + quantity
                pf["cost_basis"][ticker] = old_cost + cost
                pf["trades"].append({
                    "date": str(datetime.datetime.now()),
                    "ticker": ticker,
                    "action": "BUY",
                    "quantity": quantity,
                    "price": round(price, 2),
                    "total": round(cost, 2),
                    "confidence": confidence,
                    "reason": reason
                })
            print(f"✅ BUY {quantity} {ticker} @ ${price:.2f} (${cost:.2f}) [{confidence}] | {reason}")
        else:
            print(f"⚠️ SKIP BUY {ticker}: Insufficient funds (${cost:.2f} > ${pf['cash']:.2f}).")

    elif action == "SELL":
        owned = pf["holdings"].get(ticker, 0)
        if owned >= quantity and quantity > 0:
            proceeds = price * quantity
            if not dry_run:
                pf["holdings"][ticker] -= quantity
                pf["cash"] += proceeds
                if pf["holdings"][ticker] == 0:
                    del pf["holdings"][ticker]
                    if ticker in pf["cost_basis"]:
                        del pf["cost_basis"][ticker]
                else:
                    ratio = quantity / owned
                    pf["cost_basis"][ticker] = pf["cost_basis"].get(ticker, 0) * (1 - ratio)
                pf["trades"].append({
                    "date": str(datetime.datetime.now()),
                    "ticker": ticker,
                    "action": "SELL",
                    "quantity": quantity,
                    "price": round(price, 2),
                    "total": round(proceeds, 2),
                    "confidence": confidence,
                    "reason": reason
                })
            print(f"🔻 SELL {quantity} {ticker} @ ${price:.2f} (${proceeds:.2f}) [{confidence}] | {reason}")
        else:
            print(f"⚠️ SKIP SELL {ticker}: Not enough shares (Owned: {owned}, Sell: {quantity}).")
            
    elif action == "HOLD":
        print(f"✋ HOLD {ticker} [{confidence}] | {reason}")

def enforce_risk_rules(portfolio_mgr, current_prices, dry_run=False):
    """Hard-coded risk rules that override AI decisions. Runs BEFORE Gemini."""
    pf = portfolio_mgr.data
    forced_sells = []
    
    for ticker, shares in list(pf["holdings"].items()):
        price = current_prices.get(ticker)
        if not price or shares == 0:
            continue
            
        cost_basis = pf.get("cost_basis", {}).get(ticker, 0)
        avg_cost = cost_basis / shares if shares > 0 else 0
        
        if avg_cost == 0:
            continue
            
        pnl_pct = (price - avg_cost) / avg_cost
        
        # STOP LOSS: Auto-sell if down more than threshold
        if pnl_pct <= STOP_LOSS_PCT:
            print(f"🛑 STOP-LOSS TRIGGERED: {ticker} is at {pnl_pct*100:+.1f}% (limit: {STOP_LOSS_PCT*100:.0f}%)")
            forced_sells.append({
                "ticker": ticker,
                "action": "SELL",
                "quantity": shares,
                "confidence": "high",
                "reason": f"STOP-LOSS: Position down {pnl_pct*100:.1f}% from avg cost ${avg_cost:.2f}. Cutting losses."
            })
        
        # TAKE PROFIT: Auto-sell if up more than threshold
        elif pnl_pct >= TAKE_PROFIT_PCT:
            # Sell half to lock profits, let the rest ride
            sell_qty = max(1, shares // 2)
            print(f"🎯 TAKE-PROFIT TRIGGERED: {ticker} is at {pnl_pct*100:+.1f}% (limit: {TAKE_PROFIT_PCT*100:.0f}%)")
            forced_sells.append({
                "ticker": ticker,
                "action": "SELL",
                "quantity": sell_qty,
                "confidence": "high",
                "reason": f"TAKE-PROFIT: Position up {pnl_pct*100:.1f}%. Selling {sell_qty} of {shares} shares to lock gains."
            })
    
    return forced_sells

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulate trades without saving")
    args = parser.parse_args()

    print(f"\n🚀 Swiss Trader Autonomous Agent Starting... [{datetime.datetime.now()}]")
    if args.dry_run:
        print("⚠️ DRY RUN MODE: No changes will be saved.")

    # Initialize
    client = genai.Client(api_key=API_KEY)
    pm = PortfolioManager(PORTFOLIO_FILE)
    scanner = MarketScanner(client)
    
    # 1. Discovery Phase
    print("🌍 Phase 1: Market Discovery")
    targets = scanner.get_discovery_list(pm.get_holdings_tickers())
    
    # Limit targets to 10 to respect token limits and quotas
    if len(targets) > 10:
        print(f"⚠️ Limiting analysis to top 10 tickers (from {len(targets)}) to respect API limits.")
        targets = targets[:10]
        
    print(f"📋 Target List for Analysis: {targets}")
    
    # 2. Data Gathering Phase
    print(f"📊 Phase 2: Gathering Data for {len(targets)} stocks...")
    market_data = []
    current_prices = {}
    
    for ticker in targets:
        data = fetch_detailed_data(ticker)
        if data:
            market_data.append(data)
            current_prices[ticker] = data["price"]

    # Also fetch prices for existing holdings (for risk rules)
    for ticker in pm.get_holdings_tickers():
        if ticker not in current_prices:
            data = fetch_detailed_data(ticker)
            if data:
                current_prices[ticker] = data["price"]
            
    if not market_data:
        print("❌ No market data available. Exiting.")
        return

    # Calculate total portfolio value
    total_portfolio_value = pm.data["cash"]
    for ticker, shares in pm.data["holdings"].items():
        if ticker in current_prices:
            total_portfolio_value += shares * current_prices[ticker]
    print(f"   💼 Current Portfolio Value: ${total_portfolio_value:.2f}")

    # 3. Risk Management Phase (runs BEFORE AI decisions)
    print("🛡️ Phase 3: Enforcing Risk Rules...")
    forced_trades = enforce_risk_rules(pm, current_prices, dry_run=args.dry_run)
    if forced_trades:
        print(f"   ⚠️ {len(forced_trades)} forced trade(s) from risk rules")
        for ft in forced_trades:
            execute_trade(ft, pm, current_prices, total_portfolio_value, dry_run=args.dry_run)
    else:
        print("   ✅ All positions within risk limits")

    # 4. Decision Phase
    print("🧠 Phase 4: Consulting the Brain (Gemini)...")
    print("⏳ Waiting 90 seconds to cooldown API quota...")
    time.sleep(90)
    decisions = get_trading_decisions(client, market_data, pm.data, total_portfolio_value)
    
    # 5. Execution Phase
    print("⚡ Phase 5: Execution")
    executed_decisions = list(forced_trades)  # Include forced trades in report
    for d in decisions.get("decisions", []):
        # Don't re-sell something already force-sold
        forced_tickers = {ft["ticker"] for ft in forced_trades if ft["action"] == "SELL"}
        if d.get("action") == "BUY" or d["ticker"] not in forced_tickers:
            execute_trade(d, pm, current_prices, total_portfolio_value, dry_run=args.dry_run)
            executed_decisions.append(d)
        
    # 6. Wrap up
    if not args.dry_run:
        total_val = pm.update_history(current_prices)
        
        # 7. Generate Weekly Report
        print("📝 Phase 6: Generating Weekly Report...")
        print("⏳ Waiting 90 seconds to cooldown API quota...")
        time.sleep(90)
        generate_weekly_report(client, pm, executed_decisions, market_data, total_val)
        
        pm.save()
        print(f"💰 Portfolio Value: ${total_val:.2f}")
    
    print("✅ Mission Complete.\n")

def generate_weekly_report(client, portfolio_mgr, decisions, market_data, total_value):
    """Asks Gemini to write a weekly summary report of what the bot did."""
    pf = portfolio_mgr.data
    
    # Get recent trades (from this session)
    recent_trades = pf.get("trades", [])[-20:]  # Last 20 trades
    
    # Get history for performance context
    history = pf.get("history", [])
    prev_value = history[-2]["total_value"] if len(history) >= 2 else 50000.0
    change = total_value - prev_value
    change_pct = (change / prev_value) * 100 if prev_value > 0 else 0
    
    prompt = f"""
    You are the AI Portfolio Manager writing a weekly briefing for the portfolio owner.
    
    Write a concise, engaging weekly report (3-5 paragraphs) covering:
    1. **Market Overview**: What was the overall market sentiment this week based on the news you analyzed?
    2. **Actions Taken**: What did you buy or sell and why? Be specific about your reasoning.
    3. **Portfolio Performance**: How is the portfolio doing? Value went from ${prev_value:.2f} to ${total_value:.2f} ({change_pct:+.2f}%).
    4. **Outlook**: What are you watching for next week? Any concerns or opportunities?
    
    Context:
    - Current Holdings: {pf['holdings']}
    - Cash: ${pf['cash']:.2f}
    - Decisions made this session: {json.dumps(decisions, indent=2)}
    - Market data analyzed: {json.dumps([{{'ticker': d['ticker'], 'news': d['news']}} for d in market_data], indent=2)}
    
    Write in first person as the bot ("I"). Be conversational but professional.
    Keep it under 300 words.
    
    Output as JSON:
    {{
        "title": "Brief catchy title for this week's report",
        "summary": "The full report text in markdown format"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        report_data = json.loads(response.text)
        
        report = {
            "date": str(datetime.datetime.now()),
            "title": report_data.get("title", "Weekly Update"),
            "summary": report_data.get("summary", "No summary available."),
            "portfolio_value": round(total_value, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2)
        }
        
        if "reports" not in pf:
            pf["reports"] = []
        pf["reports"].append(report)
        
        print(f"📝 Report generated: \"{report['title']}\"")
        
    except Exception as e:
        print(f"❌ Error generating weekly report: {e}")
        # Still save a basic report even if Gemini fails
        if "reports" not in pf:
            pf["reports"] = []
        pf["reports"].append({
            "date": str(datetime.datetime.now()),
            "title": "Weekly Update",
            "summary": f"Portfolio value: ${total_value:.2f}. Change: ${change:.2f} ({change_pct:+.2f}%). Gemini report generation failed.",
            "portfolio_value": round(total_value, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2)
        })

if __name__ == "__main__":
    main()
