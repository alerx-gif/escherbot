# 🤖 EscherBot — Debian Server Setup Guide

> Complete guide to running the **trading bot** (weekly cron job) and the **web dashboard** (persistent service) on a Debian home server.

---

## Architecture Overview

| Component | File | How it runs | Purpose |
|-----------|------|-------------|---------|
| **Trading Bot** | `swiss_trader.py` | One-shot, scheduled via **cron** | Analyzes markets, makes trades, writes weekly reports |
| **Web Dashboard** | `dashboard.py` | Persistent, managed via **systemd** | Shows portfolio, holdings, charts, and reports on port `5050` |
| **Portfolio State** | `portfolio.json` | Read/written by both scripts | Stores cash, holdings, trade history, and reports |

---

## Step 1: Get the Code on Your Server

```bash
ssh your-user@your-server-ip
cd ~
git clone https://github.com/alerx-gif/escherbot.git EscherBot
cd EscherBot
```

If the repo is already cloned, just pull the latest:
```bash
cd ~/EscherBot && git pull
```

---

## Step 2: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

---

## Step 3: Create Virtual Environment & Install Packages

```bash
cd ~/EscherBot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Verify:
```bash
python3 -c "import yfinance, feedparser, flask; print('✅ All dependencies installed')"
```

---

## Step 4: Configure Your API Key

Create a `.env` file with your Gemini API key:
```bash
echo 'GEMINI_API_KEY=your-actual-api-key-here' > ~/EscherBot/.env
chmod 600 ~/EscherBot/.env
```

> The bot reads `GEMINI_API_KEY` from the environment. Both the cron job and systemd service will load this file.

---

## Step 5: Test the Bot

Run a dry-run first (no trades saved):
```bash
cd ~/EscherBot
export $(cat .env | xargs)
./venv/bin/python3 swiss_trader.py --dry-run
```

You should see:
```
🚀 Swiss Trader Autonomous Agent Starting...
⚠️ DRY RUN MODE: No changes will be saved.
🌍 Phase 1: Market Discovery
...
✅ Mission Complete.
```

If everything looks good, run it for real once:
```bash
./venv/bin/python3 swiss_trader.py
```

---

## Step 6: Schedule the Trading Bot (Weekly Cron Job)

Open crontab:
```bash
crontab -e
```

Add this line (replace `YOUR_USER` with your actual Linux username):
```cron
0 15 * * 1 cd /home/YOUR_USER/EscherBot && export $(cat .env | xargs) && ./venv/bin/python3 swiss_trader.py >> cron_log.txt 2>&1
```

**What this does:**
- `0 15 * * 1` → Every **Monday at 15:00 UTC** (10:00 AM New York time, when US markets are open)
- Loads the `.env` file for the API key
- Appends all output to `cron_log.txt`

Verify it was saved:
```bash
crontab -l
```

Check output after it runs:
```bash
tail -100 ~/EscherBot/cron_log.txt
```

---

## Step 7: Set Up the Dashboard as a Persistent Service (systemd)

Create the service file:
```bash
sudo nano /etc/systemd/system/escherbot-dashboard.service
```

Paste this (replace `YOUR_USER` with your username):
```ini
[Unit]
Description=EscherBot Trading Dashboard
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/EscherBot
EnvironmentFile=/home/YOUR_USER/EscherBot/.env
ExecStart=/home/YOUR_USER/EscherBot/venv/bin/python3 dashboard.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Save and exit (`Ctrl+X`, `Y`, `Enter`).

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable escherbot-dashboard
sudo systemctl start escherbot-dashboard
```

Verify it's running:
```bash
sudo systemctl status escherbot-dashboard
```

You should see `Active: active (running)`. The dashboard is now live at:
```
http://YOUR-SERVER-IP:5050
```

Find your server IP with:
```bash
hostname -I
```

---

## Step 8: Open the Firewall (if needed)

```bash
sudo ufw allow 5050/tcp
```

---

## Quick Reference Commands

```bash
# === TRADING BOT ===
# Run manually (live)
cd ~/EscherBot && export $(cat .env | xargs) && ./venv/bin/python3 swiss_trader.py

# Run manually (dry-run, no trades saved)
cd ~/EscherBot && export $(cat .env | xargs) && ./venv/bin/python3 swiss_trader.py --dry-run

# Check cron log
tail -100 ~/EscherBot/cron_log.txt

# Edit cron schedule
crontab -e

# === DASHBOARD ===
# Check status
sudo systemctl status escherbot-dashboard

# View live logs
sudo journalctl -u escherbot-dashboard -f

# Restart (after code changes)
sudo systemctl restart escherbot-dashboard

# Stop
sudo systemctl stop escherbot-dashboard

# === UPDATES ===
# Pull latest code and restart dashboard
cd ~/EscherBot && git pull && sudo systemctl restart escherbot-dashboard

# Check portfolio state
cat ~/EscherBot/portfolio.json | python3 -m json.tool
```

---

## Accessing from Outside Your Network (Optional)

**Tailscale (Easiest):**
1. Install Tailscale on server: https://tailscale.com/download/linux
2. Install on your phone/laptop
3. Access via `http://YOUR-TAILSCALE-IP:5050`

**Nginx Reverse Proxy:**
```bash
sudo apt install nginx
sudo nano /etc/nginx/sites-available/escherbot
```

Paste:
```nginx
server {
    listen 80;
    server_name trader.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/escherbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot doesn't run via cron | Check `cron_log.txt`. Ensure all paths are absolute. Test manually first. |
| Dashboard not accessible | Run `sudo systemctl status escherbot-dashboard`. Check firewall with `sudo ufw allow 5050/tcp`. |
| API rate limit errors (429) | The bot uses `gemini-2.5-flash`. Built-in cooldowns exist between API calls. If still hitting limits, increase `time.sleep()` values. |
| yfinance errors | Yahoo Finance may temporarily block. Wait and retry, or run `pip install --upgrade yfinance`. |
| `.env` not loading in cron | Make sure the cron line includes `export $(cat .env | xargs)` before running the script. |

---

*Last updated: February 15, 2026*
