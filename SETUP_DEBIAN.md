# 🤖 Swiss Trader — Debian Server Setup Guide

> Step-by-step instructions to deploy the trading bot and live dashboard on a Debian home server.

---

## Prerequisites

- A Debian-based server (Debian 11/12, Ubuntu 22.04+)
- SSH access to the server
- Python 3.9+ installed (check with `python3 --version`)
- Git installed

---

## Step 1: Transfer the Project to Your Server

**Option A: Using Git (Recommended)**

If your project is on GitHub:
```bash
ssh your-user@your-server-ip
cd ~
git clone https://github.com/YOUR_USERNAME/EscherBot.git
cd EscherBot
```

**Option B: Using SCP (Direct Copy)**

From your Mac, run:
```bash
scp -r /Users/alejandro/Documents/my-projects/EscherBot your-user@your-server-ip:~/EscherBot
```

Then SSH into the server:
```bash
ssh your-user@your-server-ip
cd ~/EscherBot
```

---

## Step 2: Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

---

## Step 3: Create a Virtual Environment & Install Packages

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Verify everything installed:
```bash
python3 -c "import yfinance, feedparser, flask; print('✅ All dependencies installed')"
```

---

## Step 4: Test the Bot Manually

Run a dry-run first to make sure everything works without making changes:
```bash
python3 swiss_trader.py --dry-run
```

You should see output like:
```
🚀 Swiss Trader Autonomous Agent Starting...
⚠️ DRY RUN MODE: No changes will be saved.
🌍 Phase 1: Market Discovery
🔍 Scanning Yahoo Finance for market news...
📡 Scanning RSS feeds (CNBC, Reuters, MarketWatch, Reddit)...
...
✅ Mission Complete.
```

If it works, run it for real once:
```bash
python3 swiss_trader.py
```

---

## Step 5: Set Up the Bot as a Weekly Cron Job

The bot should run automatically once a week. Open the crontab editor:
```bash
crontab -e
```

Add this line to run the bot **every Monday at 10:00 AM EST** (15:00 UTC) when US markets are open:
```cron
0 15 * * 1 cd /home/YOUR_USER/EscherBot && /home/YOUR_USER/EscherBot/venv/bin/python3 swiss_trader.py >> /home/YOUR_USER/EscherBot/cron_log.txt 2>&1
```

> ⚠️ **Replace `YOUR_USER`** with your actual Linux username.

**What this does:**
- `0 15 * * 1` — Every Monday at 15:00 UTC (10:00 AM New York time)
- `cd /home/YOUR_USER/EscherBot` — Navigate to the project directory
- `>> cron_log.txt 2>&1` — Append all output (including errors) to a log file

**Verify the cron job was saved:**
```bash
crontab -l
```

**To check the bot's output after it runs:**
```bash
cat ~/EscherBot/cron_log.txt
```

---

## Step 6: Set Up the Dashboard as a Background Service

The dashboard should run 24/7 so you can check your portfolio anytime.

### Option A: Using systemd (Recommended)

Create a service file:
```bash
sudo nano /etc/systemd/system/swiss-trader-dashboard.service
```

Paste this content (replace `YOUR_USER` with your username):
```ini
[Unit]
Description=Swiss Trader Dashboard
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/EscherBot
ExecStart=/home/YOUR_USER/EscherBot/venv/bin/python3 dashboard.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter`).

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable swiss-trader-dashboard
sudo systemctl start swiss-trader-dashboard
```

Verify it's running:
```bash
sudo systemctl status swiss-trader-dashboard
```

You should see `Active: active (running)`.

The dashboard is now accessible at:
```
http://YOUR-SERVER-IP:5050
```

**Useful commands:**
```bash
# Check status
sudo systemctl status swiss-trader-dashboard

# View live logs
sudo journalctl -u swiss-trader-dashboard -f

# Restart after code changes
sudo systemctl restart swiss-trader-dashboard

# Stop the dashboard
sudo systemctl stop swiss-trader-dashboard
```

### Option B: Using screen (Quick & Simple)

If you prefer something simpler:
```bash
sudo apt install screen
screen -S dashboard
cd ~/EscherBot
./venv/bin/python3 dashboard.py
```

Press `Ctrl+A` then `D` to detach. The dashboard keeps running.

To reattach later:
```bash
screen -r dashboard
```

---

## Step 7: Access the Dashboard from Your Network

The dashboard runs on port `5050`. To access it from any device on your home network:

```
http://YOUR-SERVER-IP:5050
```

To find your server's IP address:
```bash
hostname -I
```

### Accessing from Outside Your Home Network (Optional)

If you want to check your portfolio from your phone while away:

**Option A: Tailscale (Easiest)**
1. Install Tailscale on your server: https://tailscale.com/download/linux
2. Install Tailscale on your phone/laptop
3. Access via `http://YOUR-TAILSCALE-IP:5050`

**Option B: Reverse Proxy with Nginx**
```bash
sudo apt install nginx

sudo nano /etc/nginx/sites-available/swiss-trader
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
sudo ln -s /etc/nginx/sites-available/swiss-trader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Step 8: Set Up Log Rotation (Optional but Recommended)

To prevent `cron_log.txt` from growing forever:

```bash
sudo nano /etc/logrotate.d/swiss-trader
```

Paste:
```
/home/YOUR_USER/EscherBot/cron_log.txt {
    weekly
    rotate 12
    compress
    missingok
    notifempty
}
```

This keeps 12 weeks of logs and compresses old ones.

---

## File Overview

| File | Purpose |
|------|---------|
| `swiss_trader.py` | The trading bot — runs weekly via cron |
| `dashboard.py` | The live web dashboard — runs 24/7 via systemd |
| `portfolio.json` | Portfolio state (cash, holdings, trades, reports) |
| `requirements.txt` | Python dependencies |
| `cron_log.txt` | Bot output log (created after first cron run) |

---

## Quick Reference Commands

```bash
# Run the bot manually
cd ~/EscherBot && ./venv/bin/python3 swiss_trader.py

# Run a dry-run (no real trades)
cd ~/EscherBot && ./venv/bin/python3 swiss_trader.py --dry-run

# Check dashboard status
sudo systemctl status swiss-trader-dashboard

# View bot cron log
tail -100 ~/EscherBot/cron_log.txt

# Check portfolio directly
cat ~/EscherBot/portfolio.json | python3 -m json.tool

# Restart dashboard after code changes
sudo systemctl restart swiss-trader-dashboard
```

---

## Troubleshooting

### Bot doesn't run via cron
1. Check the cron log: `cat ~/EscherBot/cron_log.txt`
2. Make sure the paths in crontab are absolute
3. Test manually: `cd ~/EscherBot && ./venv/bin/python3 swiss_trader.py`

### Dashboard not accessible
1. Check if it's running: `sudo systemctl status swiss-trader-dashboard`
2. Check firewall: `sudo ufw allow 5050/tcp` (if using ufw)
3. Check the port isn't blocked: `curl http://localhost:5050`

### API rate limit errors
- The bot has built-in 60-second cooldowns between Gemini API calls
- If you still hit limits, increase the `time.sleep(60)` values in `swiss_trader.py`
- Consider upgrading to a paid Gemini API plan for heavier usage

### yfinance errors
- Yahoo Finance occasionally blocks requests. Wait and try again.
- If persistent, update yfinance: `pip install --upgrade yfinance`

---

## Security Notes

⚠️ **The Gemini API key is currently hardcoded in `swiss_trader.py`.**

For better security, move it to an environment variable:

1. Create a `.env` file:
```bash
echo 'GEMINI_API_KEY=your-api-key-here' > ~/EscherBot/.env
chmod 600 ~/EscherBot/.env
```

2. Update `swiss_trader.py` line 12 to:
```python
API_KEY = os.environ.get("GEMINI_API_KEY", "your-fallback-key")
```

3. Update the cron job to load the env file:
```cron
0 15 * * 1 cd /home/YOUR_USER/EscherBot && export $(cat .env | xargs) && ./venv/bin/python3 swiss_trader.py >> cron_log.txt 2>&1
```

4. Update the systemd service to include:
```ini
EnvironmentFile=/home/YOUR_USER/EscherBot/.env
```

---

*Last updated: February 14, 2026*
