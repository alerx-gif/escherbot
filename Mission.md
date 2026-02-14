# MISSION: Build "Swiss Trader" - An AI-Powered Swing Trading Bot

**Objective:**
Create a complete, headless Python application that acts as an autonomous Swing Trading portfolio manager. The bot will fetch market data from Yahoo Finance, use the Google Gemini API to analyze sentiment/news, and maintain a paper-trading portfolio in a JSON file.

**Target Environment:**
This app will be deployed on a headless Debian Linux server and scheduled via Cron. It must run without a GUI.

**Tech Stack:**
- Python 3.11+
- `yfinance` (for price and news data)
- `google-generativeai` (for the decision engine)
- Standard libraries: `json`, `os`, `datetime`

**Key Features to Implement:**
1. **Data Fetching:** - Create a function to fetch the Last Price and Top 3 News Headlines for a watchlist of 10 tech stocks (e.g., NVDA, AAPL, MSFT, GOOGL).
   - Handle network errors gracefully (retries).

2. **The Brain (Gemini Integration):**
   - Use `google.generativeai` to send a single consolidated prompt to the model containing the market data and news for all stocks.
   - The prompt must instruct the LLM to act as a "Conservative Swing Trader" and output decisions in strict JSON format.

3. **Portfolio Management:**
   - Load/Save state to `portfolio.json`.
   - Track: Cash balance (start with $50,000), Current Holdings (shares), and Total Portfolio Value history.
   - Logic: 
     - BUY if sentiment is positive and cash is available.
     - SELL if sentiment is negative.
     - HOLD otherwise.

4. **Output & Logging:**
   - The script should print clear, human-readable logs to stdout (so I can redirect them to a log file on Linux).
   - Example Log: "✅ BUY 5 NVDA @ $120.00 | Reason: Strong earnings report"

**Required Artifacts:**
1. `swiss_trader.py`: The main logic script.
2. `requirements.txt`: The dependencies.
3. `setup_guide.md`: A guide on how to install dependencies and specifically **how to set up the Cron job on Debian** to run this every Friday at 9 PM.

**Constraints:**
- Use a placeholder string "YOUR_API_KEY" for the API key.
- Ensure the JSON parsing is robust (strip markdown code blocks if the LLM adds them).