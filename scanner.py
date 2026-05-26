import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import pytz
import time

# ─── CONFIG ───────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DISCORD_WEBHOOK  = os.environ["DISCORD_WEBHOOK"]

MIN_PRICE        = 35
CPR_BUFFER_LOW   = 0.005
CPR_BUFFER_HIGH  = 0.015
SMA_BUFFER       = 0.01
WEEKLY_S2_BUFFER = 0.01
MONTHLY_R2_BUFFER= 0.015

IST = pytz.timezone("Asia/Kolkata")

# ─── NSE SYMBOL LIST ──────────────────────────────────────
def get_nse_symbols():
    """Fetch all NSE equity symbols."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.nseindia.com/"
        }
        resp = requests.get(url, headers=headers, timeout=30)
        df = pd.read_csv(pd.io.common.StringIO(resp.text))
        symbols = df["SYMBOL"].dropna().tolist()
        # Filter out SME/delisted (no $ or special chars)
        clean = [s.strip() for s in symbols if s.strip().isalpha() or
                 all(c.isalnum() or c in '-&' for c in s.strip())]
        print(f"Loaded {len(clean)} NSE symbols")
        return clean
    except Exception as e:
        print(f"Error fetching NSE symbols: {e}")
        # Fallback Nifty 200 symbols
        return [
            "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC",
            "SBIN","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
            "WIPRO","ULTRACEMCO","NESTLEIND","TATAMOTORS","SUNPHARMA","TITAN",
            "HCLTECH","BAJFINANCE","BAJAJFINSV","TECHM","NTPC","POWERGRID",
            "ONGC","COALINDIA","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL",
            "HINDALCO","VEDL","GRASIM","DIVISLAB","DRREDDY","CIPLA","APOLLOHOSP",
            "EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","M&M","TATACONSUM","BRITANNIA",
            "DABUR","MARICO","PIDILITIND","BERGEPAINT","HAVELLS","VOLTAS",
            "SIEMENS","ABB","CUMMINSIND","THERMAX","BHEL","BEL","HAL","IRCTC",
            "DMART","NYKAA","ZOMATO","PAYTM","POLICYBZR","STARTUPIND",
            "HDFCLIFE","SBILIFE","ICICIPRULI","GICRE","NIACL","MUTHOOTFIN",
            "CHOLAFIN","BAJAJHLDNG","LICHSGFIN","PNBHOUSING","RECLTD","PFC",
            "IRFC","HUDCO","NHPC","SJVN","TATAPOWER","ADANIGREEN","CESC",
            "TORNTPOWER","JSWENERGY","INOXWIND","SUZLON","RPOWER","JPPOWER",
            "ZYDUSLIFE","LUPIN","AUROPHARMA","TORNTPHARM","ALKEM","IPCALAB",
            "NATCOPHARM","GRANULES","ABBOTINDIA","PFIZER","SANOFI","GLAXO",
            "BIOCON","LAURUSLABS","DIVILAB","SUDARSCHEM","NAVINFLUOR",
            "PIDILITIND","SRF","ATUL","DEEPAKNTR","TATACHEM","GNFC","GSFC",
            "CHAMBLFERT","COROMANDEL","PIIND","RALLIS","BAYER","ASTRAL",
            "SUPREMEIND","FINOLEX","PRINCEPIPE","APOLLOTYRE","MRF","BALKRISIND",
            "CEATLTD","JKTYRE","MOTHERSON","MINDAIND","BHARATFORG","RAMKRISHNA",
            "JINDALSAW","RATNAMANI","WELCORP","NPTC","NHPC","GMRAIRPORT",
            "ZEEL","SUNTV","PVRINOX","INOXLEISUR","NAZARA","NETWORK18",
            "TV18BRDCST","HATHWAY","DBCORP","JAGRAN","HMVL","SAREGAMA",
            "MPHASIS","LTIM","COFORGE","PERSISTENT","KPITTECH","TATAELXSI",
            "HEXAWARE","MASTEK","NIITTECH","ZENSAR","RATEGAIN","INTELLECT",
            "TANLA","ROUTE","TTML","STLTECH","TEJASNET","RAILTEL",
            "IRCON","RVNL","NBCC","ENGINERSIN","MTNL","BSNL",
            "UNIONBANK","BANKBARODA","PNB","CANBK","IOB","UCOBANK",
            "CENTRALBK","MAHABANK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB",
            "RBLBANK","DCBBANK","KTKBANK","LAKSHVILAS","CSB","UJJIVANSFB"
        ]

# ─── FETCH DATA VIA NSE API ───────────────────────────────
def fetch_nse_history(symbol, period="6mo"):
    """Fetch historical data from NSE India API."""
    try:
        session = requests.Session()
        # First hit NSE homepage to get cookies
        session.get("https://www.nseindia.com", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=10)

        today = date.today()
        if period == "6mo":
            from_date = today - timedelta(days=180)
        elif period == "1y":
            from_date = today - timedelta(days=365)
        elif period == "2y":
            from_date = today - timedelta(days=730)
        else:
            from_date = today - timedelta(days=180)

        url = (
            f"https://www.nseindia.com/api/historical/cm/equity"
            f"?symbol={symbol}"
            f"&series=[%22EQ%22]"
            f"&from={from_date.strftime('%d-%m-%Y')}"
            f"&to={today.strftime('%d-%m-%Y')}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }
        resp = session.get(url, headers=headers, timeout=15)
        data = resp.json()

        if "data" not in data or not data["data"]:
            return None

        records = data["data"]
        df = pd.DataFrame(records)
        df = df.rename(columns={
            "CH_TIMESTAMP": "Date",
            "CH_OPENING_PRICE": "Open",
            "CH_TRADE_HIGH_PRICE": "High",
            "CH_TRADE_LOW_PRICE": "Low",
            "CH_CLOSING_PRICE": "Close",
            "CH_TOT_TRADED_QTY": "Volume"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        df[["Open","High","Low","Close","Volume"]] = df[["Open","High","Low","Close","Volume"]].apply(pd.to_numeric, errors="coerce")
        return df

    except Exception as e:
        return None

def resample_to_weekly(daily_df):
    """Convert daily OHLCV to weekly."""
    try:
        df = daily_df.set_index("Date")
        weekly = df.resample("W").agg({
            "Open": "first", "High": "max",
            "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()
        return weekly.reset_index()
    except:
        return None

def resample_to_monthly(daily_df):
    """Convert daily OHLCV to monthly."""
    try:
        df = daily_df.set_index("Date")
        monthly = df.resample("ME").agg({
            "Open": "first", "High": "max",
            "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()
        return monthly.reset_index()
    except:
        return None

def fetch_data(symbol):
    """Fetch all timeframes for a symbol."""
    try:
        # Daily 6 months
        daily = fetch_nse_history(symbol, "6mo")
        if daily is None or len(daily) < 60:
            return None

        # Weekly from daily
        weekly = resample_to_weekly(daily)
        if weekly is None or len(weekly) < 8:
            return None

        # Monthly from 2yr daily
        daily_2y = fetch_nse_history(symbol, "2y")
        if daily_2y is None or len(daily_2y) < 60:
            return None
        monthly = resample_to_monthly(daily_2y)
        if monthly is None or len(monthly) < 3:
            return None

        # 1Hr — resample from daily (approximate using daily data)
        # Note: NSE free API doesn't provide intraday; use daily as proxy
        # For 1Hr SMA compression we use daily SMA as approximation
        return {
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "daily_2y": daily_2y
        }
    except Exception as e:
        return None

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

# ─── SETUP 1: Monthly CPR Magnet ──────────────────────────
def check_setup1(data, symbol):
    try:
        daily   = data["daily"]
        monthly = data["monthly"]

        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE:
            return None

        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50):
            return None
        if sma20 <= sma50:
            return None
        if not (min(sma20, sma50) <= close <= max(sma20, sma50)):
            return None

        prev_month = monthly.iloc[-2]
        cpr = calculate_cpr(prev_month["High"], prev_month["Low"], prev_month["Close"])
        cpr_levels = {"BC": cpr["bc"], "Pivot": cpr["pivot"], "TC": cpr["tc"]}

        nearest_level, nearest_name, min_dist = None, None, float("inf")
        for name, level in cpr_levels.items():
            dist = abs(close - level) / level
            if CPR_BUFFER_LOW <= dist <= CPR_BUFFER_HIGH and dist < min_dist:
                min_dist, nearest_level, nearest_name = dist, level, name

        if nearest_level is None:
            return None

        volume = int(daily["Volume"].iloc[-1])
        return {
            "symbol": symbol, "price": round(close, 2),
            "sma20": round(sma20, 2), "sma50": round(sma50, 2),
            "cpr_level": nearest_name, "cpr_value": round(nearest_level, 2),
            "cpr_dist": round(min_dist * 100, 2), "volume": volume,
            "setup": "Setup 1 — Monthly CPR Magnet"
        }
    except:
        return None

# ─── SETUP 2: Weekly Level Watch ──────────────────────────
def check_setup2(data, symbol):
    try:
        daily  = data["daily"]
        weekly = data["weekly"]

        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE:
            return None

        prev_week_low = weekly["Low"].iloc[-2]
        curr_week = weekly.iloc[-1]
        w_cpr = calculate_cpr(curr_week["High"], curr_week["Low"], curr_week["Close"])
        weekly_s2 = w_cpr["s2"]

        below_pwl = close < prev_week_low
        s2_dist   = abs(close - weekly_s2) / weekly_s2
        near_s2   = s2_dist <= WEEKLY_S2_BUFFER

        if not (below_pwl or near_s2):
            return None

        trigger = []
        if below_pwl:
            trigger.append(f"Below PWL ₹{round(prev_week_low,2)}")
        if near_s2:
            trigger.append(f"Near Weekly S2 ₹{round(weekly_s2,2)} ({round(s2_dist*100,2)}% away)")

        volume = int(daily["Volume"].iloc[-1])
        return {
            "symbol": symbol, "price": round(close, 2),
            "pwl": round(prev_week_low, 2), "weekly_s2": round(weekly_s2, 2),
            "trigger": " | ".join(trigger), "volume": volume,
            "setup": "Setup 2 — Weekly Level Watch"
        }
    except:
        return None

# ─── SETUP 3: Monthly R2 Compression ──────────────────────
def check_setup3(data, symbol):
    try:
        daily   = data["daily"]
        monthly = data["monthly"]

        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE:
            return None

        prev_month = monthly.iloc[-2]
        m_cpr = calculate_cpr(prev_month["High"], prev_month["Low"], prev_month["Close"])
        monthly_r1 = m_cpr["r1"]
        monthly_r2 = m_cpr["r2"]

        if close <= monthly_r1:
            return None

        r2_dist = abs(close - monthly_r2) / monthly_r2
        if r2_dist > MONTHLY_R2_BUFFER:
            return None

        # Use daily SMA as 1Hr SMA approximation
        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50):
            return None

        sma_diff = abs(sma20 - sma50) / sma50
        if sma_diff > SMA_BUFFER:
            return None

        volume = int(daily["Volume"].iloc[-1])
        return {
            "symbol": symbol, "price": round(close, 2),
            "monthly_r1": round(monthly_r1, 2), "monthly_r2": round(monthly_r2, 2),
            "r2_dist": round(r2_dist * 100, 2),
            "sma20": round(sma20, 2), "sma50": round(sma50, 2),
            "sma_diff": round(sma_diff * 100, 2), "volume": volume,
            "setup": "Setup 3 — Monthly R2 Compression"
        }
    except:
        return None

# ─── TRADINGVIEW LINKS ────────────────────────────────────
def tv_links_discord(sym):
    return (
        f"[Daily](https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval=D) | "
        f"[Weekly](https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval=W) | "
        f"[1Hr](https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval=60)"
    )

def tv_links_telegram(sym):
    base = "https://www.tradingview.com/chart/?symbol=NSE:"
    return (
        f"📊 [Daily]({base}{sym}&interval=D) | "
        f"[Weekly]({base}{sym}&interval=W) | "
        f"[1Hr]({base}{sym}&interval=60)"
    )

# ─── FORMAT DISCORD ───────────────────────────────────────
def format_discord(r1, r2, r3, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    msgs = []

    header = (
        f"```\n{'='*50}\n"
        f"  🔍 KRATOS SCREENER — DAILY SCAN\n"
        f"  {now_str}\n"
        f"{'='*50}\n```"
    )
    msgs.append(header)

    def section(title, results, fields):
        lines = [f"**📌 {title}** — {len(results)} stocks\n"]
        if results:
            for r in results[:15]:
                lines.append(f"**{r['symbol']}** — ₹{r['price']}")
                for f in fields(r):
                    lines.append(f"> {f}")
                lines.append(f"> Vol: {r['volume']:,}")
                lines.append(f"> 📊 {tv_links_discord(r['symbol'])}")
                lines.append("")
        else:
            lines.append("_No stocks matched today_\n")
        lines.append("─" * 40)
        return "\n".join(lines)

    msgs.append(section(
        "Setup 1 — Monthly CPR Magnet", r1,
        lambda r: [
            f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
            f"D20 SMA: ₹{r['sma20']} | D50 SMA: ₹{r['sma50']}"
        ]
    ))
    msgs.append(section(
        "Setup 2 — Weekly Level Watch", r2,
        lambda r: [
            f"Trigger: {r['trigger']}",
            f"PWL: ₹{r['pwl']} | Weekly S2: ₹{r['weekly_s2']}"
        ]
    ))
    msgs.append(section(
        "Setup 3 — Monthly R2 Compression", r3,
        lambda r: [
            f"Monthly R1: ₹{r['monthly_r1']} | R2: ₹{r['monthly_r2']} ({r['r2_dist']}% away)",
            f"SMA20: ₹{r['sma20']} | SMA50: ₹{r['sma50']} (diff: {r['sma_diff']}%)"
        ]
    ))

    total = len(r1) + len(r2) + len(r3)
    msgs.append(f"```\nTotal Alerts : {total}\nNext Scan    : Tomorrow 6:00 PM IST\n{'='*50}\n```")
    return msgs

# ─── FORMAT TELEGRAM ──────────────────────────────────────
def format_telegram(r1, r2, r3, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    lines   = [
        f"🔍 *KRATOS SCREENER — DAILY SCAN*",
        f"📅 {now_str}", ""
    ]

    def section(title, results, fields):
        lines.append(f"*{title}* — {len(results)} stocks")
        lines.append("─────────────────────")
        if results:
            for r in results[:5]:
                lines.append(f"*{r['symbol']}* — ₹{r['price']}")
                for f in fields(r):
                    lines.append(f)
                lines.append(f"Vol: {r['volume']:,}")
                lines.append(tv_links_telegram(r['symbol']))
                lines.append("")
        else:
            lines.append("No stocks matched\n")

    section(
        "📌 Setup 1 — Monthly CPR Magnet", r1,
        lambda r: [
            f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
            f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}"
        ]
    )
    section(
        "📌 Setup 2 — Weekly Level Watch", r2,
        lambda r: [f"Trigger: {r['trigger']}", f"PWL: ₹{r['pwl']} | W\\_S2: ₹{r['weekly_s2']}"]
    )
    section(
        "📌 Setup 3 — Monthly R2 Compression", r3,
        lambda r: [
            f"M\\_R1: ₹{r['monthly_r1']} | M\\_R2: ₹{r['monthly_r2']} ({r['r2_dist']}% away)",
            f"SMA diff: {r['sma_diff']}%"
        ]
    )

    total = len(r1) + len(r2) + len(r3)
    lines.append(f"✅ *Total Alerts: {total}*")
    lines.append(f"⏰ Next scan: Tomorrow 6:00 PM IST")
    return "\n".join(lines)

# ─── SEND DISCORD ─────────────────────────────────────────
def send_discord(messages):
    for msg in messages:
        chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
        for chunk in chunks:
            r = requests.post(DISCORD_WEBHOOK, json={"content": chunk})
            print(f"Discord: {r.status_code}")
            time.sleep(0.5)

# ─── SEND TELEGRAM ────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        })
        print(f"Telegram: {r.status_code}")
        time.sleep(0.5)

# ─── MAIN ─────────────────────────────────────────────────
def main():
    now_ist = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"Kratos Screener started: {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*50}\n")

    symbols = get_nse_symbols()
    print(f"Scanning {len(symbols)} NSE stocks...\n")

    results1, results2, results3 = [], [], []
    scanned, skipped = 0, 0

    for symbol in symbols:
        try:
            data = fetch_data(symbol)
            if data is None:
                skipped += 1
                continue

            r1 = check_setup1(data, symbol)
            r2 = check_setup2(data, symbol)
            r3 = check_setup3(data, symbol)

            if r1: results1.append(r1)
            if r2: results2.append(r2)
            if r3: results3.append(r3)

            scanned += 1
            if scanned % 25 == 0:
                print(f"Progress: {scanned} scanned, {skipped} skipped...")

            time.sleep(0.3)  # Be polite to NSE API

        except Exception as e:
            skipped += 1
            continue

    # Sort by volume descending
    results1.sort(key=lambda x: x["volume"], reverse=True)
    results2.sort(key=lambda x: x["volume"], reverse=True)
    results3.sort(key=lambda x: x["volume"], reverse=True)

    print(f"\n{'='*50}")
    print(f"Scan Complete!")
    print(f"Scanned: {scanned} | Skipped: {skipped}")
    print(f"Setup 1: {len(results1)} | Setup 2: {len(results2)} | Setup 3: {len(results3)}")
    print(f"{'='*50}\n")

    discord_msgs = format_discord(results1, results2, results3, now_ist)
    telegram_msg = format_telegram(results1, results2, results3, now_ist)

    print("Sending to Discord...")
    send_discord(discord_msgs)

    print("Sending to Telegram...")
    send_telegram(telegram_msg)

    print("\n✅ Done!")

if __name__ == "__main__":
    main()
