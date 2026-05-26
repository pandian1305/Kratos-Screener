import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import pytz

# ─── CONFIG ───────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DISCORD_WEBHOOK  = os.environ["DISCORD_WEBHOOK"]

MIN_PRICE        = 35       # Minimum stock price filter
CPR_BUFFER_LOW   = 0.005    # 0.5% buffer for Monthly CPR proximity
CPR_BUFFER_HIGH  = 0.015    # 1.5% buffer for Monthly CPR proximity
SMA_BUFFER       = 0.01     # 1% buffer for 1Hr SMA compression check
WEEKLY_S2_BUFFER = 0.01     # 1% buffer for Weekly S2 proximity
MONTHLY_R2_BUFFER= 0.015    # 1.5% buffer for Monthly R2 proximity

IST = pytz.timezone("Asia/Kolkata")

# ─── NSE STOCK LIST ───────────────────────────────────────
def get_nse_symbols():
    """Fetch all NSE equity symbols from NSE India."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=30)
        df = pd.read_csv(pd.io.common.StringIO(resp.text))
        symbols = df["SYMBOL"].dropna().tolist()
        # Convert to yfinance format (append .NS)
        return [f"{s.strip()}.NS" for s in symbols]
    except Exception as e:
        print(f"Error fetching NSE symbols: {e}")
        # Fallback: Nifty 500 sample if NSE fetch fails
        fallback = [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
            "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
            "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","WIPRO.NS",
            "ULTRACEMCO.NS","NESTLEIND.NS","TATAMOTORS.NS","SUNPHARMA.NS","TITAN.NS"
        ]
        return fallback

# ─── CPR CALCULATION ──────────────────────────────────────
def calculate_cpr(high, low, close):
    pivot = (high + low + close) / 3
    bc    = (high + low) / 2
    tc    = (2 * pivot) - bc
    r1    = (2 * pivot) - low
    r2    = pivot + (high - low)
    s1    = (2 * pivot) - high
    s2    = pivot - (high - low)
    return {"pivot": pivot, "bc": bc, "tc": tc,
            "r1": r1, "r2": r2, "s1": s1, "s2": s2}

# ─── FETCH DATA ───────────────────────────────────────────
def fetch_data(symbol):
    try:
        tk = yf.Ticker(symbol)

        # Daily data — 6 months
        daily = tk.history(period="6mo", interval="1d")
        if daily.empty or len(daily) < 60:
            return None

        # Weekly data — 1 year
        weekly = tk.history(period="1y", interval="1wk")
        if weekly.empty or len(weekly) < 8:
            return None

        # Monthly data — 2 years
        monthly = tk.history(period="2y", interval="1mo")
        if monthly.empty or len(monthly) < 3:
            return None

        # 1Hr data — 60 days
        hourly = tk.history(period="60d", interval="1h")
        if hourly.empty or len(hourly) < 50:
            return None

        return {"daily": daily, "weekly": weekly,
                "monthly": monthly, "hourly": hourly}
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# ─── SETUP 1: Monthly CPR Magnet ──────────────────────────
def check_setup1(data, symbol):
    """
    Price between Daily 20 & 50 SMA (20 > 50)
    + Price within 0.5%-1.5% of Monthly CPR
    """
    try:
        daily   = data["daily"]
        monthly = data["monthly"]

        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE:
            return None

        # Daily SMAs
        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]

        if pd.isna(sma20) or pd.isna(sma50):
            return None

        # Condition: 20 SMA > 50 SMA
        if sma20 <= sma50:
            return None

        # Condition: Price between 20 and 50 SMA
        price_between = (min(sma20, sma50) <= close <= max(sma20, sma50))
        if not price_between:
            return None

        # Monthly CPR (use previous completed month)
        prev_month = monthly.iloc[-2]
        cpr = calculate_cpr(prev_month["High"], prev_month["Low"], prev_month["Close"])

        # Check proximity to any CPR level (BC, Pivot, TC)
        cpr_levels = {"BC": cpr["bc"], "Pivot": cpr["pivot"], "TC": cpr["tc"]}
        nearest_level = None
        nearest_name  = None
        min_dist = float("inf")

        for name, level in cpr_levels.items():
            dist = abs(close - level) / level
            if CPR_BUFFER_LOW <= dist <= CPR_BUFFER_HIGH:
                if dist < min_dist:
                    min_dist      = dist
                    nearest_level = level
                    nearest_name  = name

        if nearest_level is None:
            return None

        volume = int(daily["Volume"].iloc[-1])

        return {
            "symbol":  symbol.replace(".NS", ""),
            "price":   round(close, 2),
            "sma20":   round(sma20, 2),
            "sma50":   round(sma50, 2),
            "cpr_level": nearest_name,
            "cpr_value": round(nearest_level, 2),
            "cpr_dist":  round(min_dist * 100, 2),
            "volume":  volume,
            "setup":   "Setup 1 — Monthly CPR Magnet"
        }
    except Exception as e:
        print(f"Setup1 error {symbol}: {e}")
        return None

# ─── SETUP 2: Weekly Level Watch ──────────────────────────
def check_setup2(data, symbol):
    """
    Price below Previous Week Low
    OR near Weekly S2 level (within 1%)
    """
    try:
        daily  = data["daily"]
        weekly = data["weekly"]

        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE:
            return None

        # Previous week low (second last completed week)
        prev_week_low = weekly["Low"].iloc[-2]

        # Weekly CPR (current week)
        curr_week = weekly.iloc[-1]
        w_cpr = calculate_cpr(curr_week["High"], curr_week["Low"], curr_week["Close"])
        weekly_s2 = w_cpr["s2"]

        # Condition A: Close below previous week low
        below_pwl = close < prev_week_low

        # Condition B: Near Weekly S2 (within 1%)
        s2_dist = abs(close - weekly_s2) / weekly_s2
        near_s2 = s2_dist <= WEEKLY_S2_BUFFER

        if not (below_pwl or near_s2):
            return None

        volume = int(daily["Volume"].iloc[-1])

        trigger = []
        if below_pwl:
            trigger.append(f"Below PWL ₹{round(prev_week_low,2)}")
        if near_s2:
            trigger.append(f"Near Weekly S2 ₹{round(weekly_s2,2)} ({round(s2_dist*100,2)}% away)")

        return {
            "symbol":   symbol.replace(".NS", ""),
            "price":    round(close, 2),
            "pwl":      round(prev_week_low, 2),
            "weekly_s2":round(weekly_s2, 2),
            "trigger":  " | ".join(trigger),
            "volume":   volume,
            "setup":    "Setup 2 — Weekly Level Watch"
        }
    except Exception as e:
        print(f"Setup2 error {symbol}: {e}")
        return None

# ─── SETUP 3: Monthly R2 Compression ──────────────────────
def check_setup3(data, symbol):
    """
    Price above Monthly R1 and near Monthly R2
    + 1Hr 20 SMA and 1Hr 50 SMA close to each other (within 0.5%-1%)
    """
    try:
        daily   = data["daily"]
        monthly = data["monthly"]
        hourly  = data["hourly"]

        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE:
            return None

        # Monthly CPR levels
        prev_month = monthly.iloc[-2]
        m_cpr = calculate_cpr(prev_month["High"], prev_month["Low"], prev_month["Close"])
        monthly_r1 = m_cpr["r1"]
        monthly_r2 = m_cpr["r2"]

        # Condition: Price above Monthly R1
        if close <= monthly_r1:
            return None

        # Condition: Price near Monthly R2 (within 1.5%)
        r2_dist = abs(close - monthly_r2) / monthly_r2
        if r2_dist > MONTHLY_R2_BUFFER:
            return None

        # 1Hr SMA compression
        h_sma20 = hourly["Close"].rolling(20).mean().iloc[-1]
        h_sma50 = hourly["Close"].rolling(50).mean().iloc[-1]

        if pd.isna(h_sma20) or pd.isna(h_sma50):
            return None

        sma_diff = abs(h_sma20 - h_sma50) / h_sma50
        if sma_diff > SMA_BUFFER:
            return None

        volume = int(daily["Volume"].iloc[-1])

        return {
            "symbol":    symbol.replace(".NS", ""),
            "price":     round(close, 2),
            "monthly_r1":round(monthly_r1, 2),
            "monthly_r2":round(monthly_r2, 2),
            "r2_dist":   round(r2_dist * 100, 2),
            "h_sma20":   round(h_sma20, 2),
            "h_sma50":   round(h_sma50, 2),
            "sma_diff":  round(sma_diff * 100, 2),
            "volume":    volume,
            "setup":     "Setup 3 — Monthly R2 Compression"
        }
    except Exception as e:
        print(f"Setup3 error {symbol}: {e}")
        return None

# ─── TRADINGVIEW LINK ─────────────────────────────────────
def tv_links(sym):
    s = sym.replace(".NS", "")
    return (
        f"[Daily](https://www.tradingview.com/chart/?symbol=NSE:{s}&interval=D) | "
        f"[Weekly](https://www.tradingview.com/chart/?symbol=NSE:{s}&interval=W) | "
        f"[1Hr](https://www.tradingview.com/chart/?symbol=NSE:{s}&interval=60)"
    )

def tv_links_telegram(sym):
    s = sym.replace(".NS", "")
    base = "https://www.tradingview.com/chart/?symbol=NSE:"
    return (
        f"📊 Daily: {base}{s}&interval=D\n"
        f"📊 Weekly: {base}{s}&interval=W\n"
        f"📊 1Hr: {base}{s}&interval=60"
    )

# ─── FORMAT DISCORD MESSAGE ───────────────────────────────
def format_discord(results1, results2, results3, scan_time, is_manual):
    now_str  = scan_time.strftime("%d %b %Y | %I:%M %p IST")
    mode_tag = "⚠️ Manual Scan — Market Closed\n" if is_manual else ""

    lines = []
    lines.append(f"```")
    lines.append(f"{'='*50}")
    lines.append(f"  🔍 KRATOS SCREENER — HIGH PROBABILITY SETUPS")
    lines.append(f"  {now_str}")
    if is_manual:
        lines.append(f"  ⚠️  Manual Scan — Market Closed")
    lines.append(f"{'='*50}")
    lines.append(f"```")

    # Setup 1
    lines.append(f"**📌 SETUP 1 — Monthly CPR Magnet** ({len(results1)} stocks)\n")
    if results1:
        for r in results1[:10]:  # Discord limit safety
            lines.append(
                f"**{r['symbol']}** — ₹{r['price']}\n"
                f"> CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)\n"
                f"> D20 SMA: ₹{r['sma20']} | D50 SMA: ₹{r['sma50']}\n"
                f"> Vol: {r['volume']:,}\n"
                f"> 📊 {tv_links(r['symbol'])}\n"
            )
    else:
        lines.append("_No stocks matched today_\n")

    lines.append("─" * 40)

    # Setup 2
    lines.append(f"\n**📌 SETUP 2 — Weekly Level Watch** ({len(results2)} stocks)\n")
    if results2:
        for r in results2[:10]:
            lines.append(
                f"**{r['symbol']}** — ₹{r['price']}\n"
                f"> Trigger: {r['trigger']}\n"
                f"> PWL: ₹{r['pwl']} | Weekly S2: ₹{r['weekly_s2']}\n"
                f"> Vol: {r['volume']:,}\n"
                f"> 📊 {tv_links(r['symbol'])}\n"
            )
    else:
        lines.append("_No stocks matched today_\n")

    lines.append("─" * 40)

    # Setup 3
    lines.append(f"\n**📌 SETUP 3 — Monthly R2 Compression** ({len(results3)} stocks)\n")
    if results3:
        for r in results3[:10]:
            lines.append(
                f"**{r['symbol']}** — ₹{r['price']}\n"
                f"> Monthly R1: ₹{r['monthly_r1']} | R2: ₹{r['monthly_r2']} ({r['r2_dist']}% away)\n"
                f"> 1Hr SMA20: ₹{r['h_sma20']} | SMA50: ₹{r['h_sma50']} (diff: {r['sma_diff']}%)\n"
                f"> Vol: {r['volume']:,}\n"
                f"> 📊 {tv_links(r['symbol'])}\n"
            )
    else:
        lines.append("_No stocks matched today_\n")

    total = len(results1) + len(results2) + len(results3)
    lines.append(f"\n```")
    lines.append(f"Total Alerts : {total}")
    lines.append(f"Next Scan    : Every 15 mins during market hours")
    lines.append(f"{'='*50}")
    lines.append(f"```")

    return "\n".join(lines)

# ─── FORMAT TELEGRAM MESSAGE ──────────────────────────────
def format_telegram(results1, results2, results3, scan_time, is_manual):
    now_str = scan_time.strftime("%d %b %Y | %I:%M %p IST")
    lines   = []
    lines.append(f"🔍 *KRATOS SCREENER*")
    lines.append(f"📅 {now_str}")
    if is_manual:
        lines.append(f"⚠️ Manual Scan — Market Closed")
    lines.append("")

    def add_setup(title, results):
        lines.append(f"*{title}* — {len(results)} stocks")
        lines.append("─────────────────────")
        if results:
            for r in results[:5]:  # Top 5 per setup on Telegram
                lines.append(f"*{r['symbol']}* — ₹{r['price']}")
                if "cpr_level" in r:
                    lines.append(f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)")
                    lines.append(f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}")
                elif "trigger" in r:
                    lines.append(f"Trigger: {r['trigger']}")
                    lines.append(f"PWL: ₹{r['pwl']} | W\\_S2: ₹{r['weekly_s2']}")
                elif "monthly_r2" in r:
                    lines.append(f"M\\_R1: ₹{r['monthly_r1']} | M\\_R2: ₹{r['monthly_r2']}")
                    lines.append(f"1Hr SMA diff: {r['sma_diff']}%")
                lines.append(f"Vol: {r['volume']:,}")
                lines.append(tv_links_telegram(r['symbol']))
                lines.append("")
        else:
            lines.append("No stocks matched")
        lines.append("")

    add_setup("📌 Setup 1 — Monthly CPR Magnet", results1)
    add_setup("📌 Setup 2 — Weekly Level Watch", results2)
    add_setup("📌 Setup 3 — Monthly R2 Compression", results3)

    total = len(results1) + len(results2) + len(results3)
    lines.append(f"✅ Total Alerts: {total}")
    return "\n".join(lines)

# ─── SEND DISCORD ─────────────────────────────────────────
def send_discord(message):
    # Discord has 2000 char limit — split if needed
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
    for chunk in chunks:
        payload = {"content": chunk}
        r = requests.post(DISCORD_WEBHOOK, json=payload)
        print(f"Discord: {r.status_code}")

# ─── SEND TELEGRAM ────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram has 4096 char limit — split if needed
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        payload = {
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       chunk,
            "parse_mode": "Markdown"
        }
        r = requests.post(url, json=payload)
        print(f"Telegram: {r.status_code}")

# ─── MAIN ─────────────────────────────────────────────────
def main():
    now_ist = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"Kratos Screener started at {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*50}")

    # Detect if market is open
    market_open  = now_ist.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    is_weekend   = now_ist.weekday() >= 5
    is_manual    = is_weekend or not (market_open <= now_ist <= market_close)

    print(f"Mode: {'MANUAL (Market Closed)' if is_manual else 'AUTO (Market Open)'}")

    # Fetch all NSE symbols
    print("\nFetching NSE symbol list...")
    symbols = get_nse_symbols()
    print(f"Total symbols to scan: {len(symbols)}")

    results1, results2, results3 = [], [], []
    scanned = 0

    for symbol in symbols:
        try:
            data = fetch_data(symbol)
            if data is None:
                continue

            r1 = check_setup1(data, symbol)
            r2 = check_setup2(data, symbol)
            r3 = check_setup3(data, symbol)

            if r1: results1.append(r1)
            if r2: results2.append(r2)
            if r3: results3.append(r3)

            scanned += 1
            if scanned % 50 == 0:
                print(f"Scanned {scanned}/{len(symbols)} stocks...")

        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    # Sort by volume descending
    results1.sort(key=lambda x: x["volume"], reverse=True)
    results2.sort(key=lambda x: x["volume"], reverse=True)
    results3.sort(key=lambda x: x["volume"], reverse=True)

    total = len(results1) + len(results2) + len(results3)
    print(f"\nScan complete — {scanned} stocks scanned")
    print(f"Setup 1: {len(results1)} | Setup 2: {len(results2)} | Setup 3: {len(results3)}")
    print(f"Total alerts: {total}")

    # Send alerts
    discord_msg  = format_discord(results1, results2, results3, now_ist, is_manual)
    telegram_msg = format_telegram(results1, results2, results3, now_ist, is_manual)

    print("\nSending Discord alert...")
    send_discord(discord_msg)

    print("Sending Telegram alert...")
    send_telegram(telegram_msg)

    print("\nDone! ✅")

if __name__ == "__main__":
    main()
