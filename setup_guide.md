# Swiss Trader Setup Guide

## Prerequisites
- **Debian Linux Server** (or any Linux distro)
- **Python 3.11+** installed
- **Google Gemini API Key** (Get one from Google AI Studio)

## Installation

1.  **Clone/Upload the project** to your server:
    ```bash
    mkdir -p ~/swiss_trader
    # Copy swisstrader.py and requirements.txt to this folder
    cd ~/swiss_trader
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Key:**
    Open `swiss_trader.py` and replace `YOUR_API_KEY` with your actual Gemini API key.
    ```python
    API_KEY = "your_actual_api_key_here"
    ```

## Running Manually
To test that everything works:
```bash
~/swiss_trader/venv/bin/python3 ~/swiss_trader/swiss_trader.py
```

## Setting up Cron Job (Friday at 9 PM)

 We want the bot to run automatically every Friday at 9:00 PM (21:00).

1.  **Open Crontab:**
    ```bash
    crontab -e
    ```

2.  **Add the following line:**
    (Adjust the paths if you installed it somewhere else)
    ```cron
    0 21 * * 5 /home/yourusername/swiss_trader/venv/bin/python3 /home/yourusername/swiss_trader/swiss_trader.py >> /home/yourusername/swiss_trader/trade_log.txt 2>&1
    ```

    **Explanation:**
    - `0 21 * * 5`: At minute 0, hour 21 (9 PM), every day of month, every month, on Friday (5).
    - `>> .../trade_log.txt`: Appends the output to a log file.
    - `2>&1`: Redirects errors to the same log file.

3.  **Verify:**
    List your cron jobs to make sure it was saved:
    ```bash
    crontab -l
    ```
