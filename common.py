"""
common.py — Shared utilities for all Kratos Screener setups.
Uses yfinance bulk download — fetches ALL NSE stocks in batches,
fast enough to complete well within GitHub Actions limits.
"""
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from io import StringIO
import time
import pytz

IST = pytz.timezone("Asia/Kolkata")

# ─── FETCH ALL NSE SYMBOLS ────────────────────────────────
def get_all_nse_symbols():
    """Fetch ALL NSE equity symbols from NSE archives."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.nseindia.com/"
        }, timeout=30)
        if resp.status_code == 200 and len(resp.text) > 1000:
            df = pd.read_csv(StringIO(resp.text))
            df.columns = [c.strip() for c in df.columns]
            symbols = df["SYMBOL"].dropna().tolist()
            symbols = [
                s.strip() for s in symbols
                if isinstance(s, str)
                and len(s.strip()) > 0
                and not s.strip().startswith("$")
                and s.strip().replace("-","").replace("&","").isalnum()
            ]
            if len(symbols) > 500:
                print(f"✅ Loaded {len(symbols)} NSE symbols")
                return symbols
    except Exception as e:
        print(f"NSE fetch failed: {e}")

    # Fallback
    print("⚠️ Using fallback symbol list")
    return get_fallback_symbols()


# ─── BULK DOWNLOAD VIA YFINANCE ───────────────────────────
def download_all_data(symbols, period="1y"):
    """
    Download OHLCV for ALL symbols at once using yfinance bulk download.
    Returns dict: {symbol: DataFrame}
    Much faster than one-by-one — yfinance batches internally.
    """
    import yfinance as yf

    # Convert to yfinance format
    tickers = [f"{s}.NS" for s in symbols]

    print(f"Downloading data for {len(tickers)} stocks...")
    start_time = time.time()

    # Download in batches of 200 to avoid memory issues
    all_data = {}
    batch_size = 200
    batches = [tickers[i:i+batch_size] for i in range(0, len(tickers), batch_size)]

    for batch_num, batch in enumerate(batches):
        try:
            print(f"  Batch {batch_num+1}/{len(batches)} ({len(batch)} stocks)...")
            raw = yf.download(
                batch,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
                timeout=60
            )

            # Parse multi-ticker download result
            if len(batch) == 1:
                sym = batch[0].replace(".NS","")
                if not raw.empty and len(raw) >= 20:
                    raw.index = pd.to_datetime(raw.index)
                    raw.columns = [c if isinstance(c, str) else c[0]
                                   for c in raw.columns]
                    all_data[sym] = raw.reset_index().rename(columns={"index":"Date","Datetime":"Date"})
            else:
                for ticker in batch:
                    sym = ticker.replace(".NS","")
                    try:
                        if ticker in raw.columns.get_level_values(0):
                            df = raw[ticker].copy()
                        elif hasattr(raw.columns, 'levels'):
                            df = raw.xs(ticker, axis=1, level=0)
                        else:
                            continue
                        df = df.dropna(subset=["Close"])
                        if len(df) < 20:
                            continue
                        df = df.reset_index().rename(columns={"index":"Date","Datetime":"Date","Price":"Date"})
                        if "Date" not in df.columns:
                            df = df.reset_index()
                            df.columns = ["Date"] + list(df.columns[1:])
                        df["Date"] = pd.to_datetime(df["Date"])
                        df = df.sort_values("Date").reset_index(drop=True)
                        all_data[sym] = df
                    except Exception:
                        continue

        except Exception as e:
            print(f"  Batch {batch_num+1} error: {e}")
            continue

        time.sleep(1)  # Small pause between batches

    elapsed = time.time() - start_time
    print(f"✅ Downloaded {len(all_data)} stocks in {elapsed:.0f}s")
    return all_data


def resample_weekly(df):
    try:
        d = df.set_index("Date")
        w = d.resample("W").agg({
            "Open":"first","High":"max",
            "Low":"min","Close":"last","Volume":"sum"
        }).dropna()
        return w.reset_index()
    except:
        return None


def resample_monthly(df):
    try:
        d = df.set_index("Date")
        m = d.resample("ME").agg({
            "Open":"first","High":"max",
            "Low":"min","Close":"last","Volume":"sum"
        }).dropna()
        return m.reset_index()
    except:
        return None


def calc_cpr(high, low, close):
    pivot = (high + low + close) / 3
    bc    = (high + low) / 2
    tc    = (2 * pivot) - bc
    r1    = (2 * pivot) - low
    r2    = pivot + (high - low)
    s1    = (2 * pivot) - high
    s2    = pivot - (high - low)
    return {"pivot":pivot,"bc":bc,"tc":tc,
            "r1":r1,"r2":r2,"s1":s1,"s2":s2}


def tv_discord(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[Daily]({b}D) | [Weekly]({b}W) | [1Hr]({b}60)"


def tv_telegram(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[D]({b}D) | [W]({b}W) | [1H]({b}60)"


def send_discord_msg(webhook, msg):
    for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
        try:
            requests.post(webhook, json={"content": chunk}, timeout=10)
        except: pass
        time.sleep(0.3)


def send_telegram_msg(token, chat_id, msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        try:
            requests.post(url, json={
                "chat_id": chat_id, "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=10)
        except: pass
        time.sleep(0.5)


def get_fallback_symbols():
    return [
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC",
        "SBIN","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
        "WIPRO","ULTRACEMCO","NESTLEIND","TATAMOTORS","SUNPHARMA","TITAN",
        "HCLTECH","BAJFINANCE","BAJAJFINSV","TECHM","NTPC","POWERGRID",
        "ONGC","COALINDIA","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL",
        "HINDALCO","VEDL","GRASIM","DIVISLAB","DRREDDY","CIPLA","APOLLOHOSP",
        "EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","TATACONSUM","BRITANNIA",
        "DABUR","MARICO","PIDILITIND","BERGEPAINT","HAVELLS","VOLTAS",
        "SIEMENS","ABB","CUMMINSIND","THERMAX","BHEL","BEL","HAL","IRCTC",
        "DMART","ZOMATO","HDFCLIFE","SBILIFE","ICICIPRULI","MUTHOOTFIN",
        "CHOLAFIN","LICHSGFIN","RECLTD","PFC","IRFC","HUDCO","NHPC",
        "SJVN","TATAPOWER","ADANIGREEN","CESC","TORNTPOWER","JSWENERGY",
        "SUZLON","ZYDUSLIFE","LUPIN","AUROPHARMA","TORNTPHARM","ALKEM",
        "IPCALAB","NATCOPHARM","GRANULES","BIOCON","LAURUSLABS","DIVILAB",
        "SRF","ATUL","DEEPAKNTR","TATACHEM","GNFC","GSFC","CHAMBLFERT",
        "COROMANDEL","PIIND","ASTRAL","SUPREMEIND","APOLLOTYRE","MRF",
        "BALKRISIND","CEATLTD","MOTHERSON","BHARATFORG","MPHASIS","LTIM",
        "COFORGE","PERSISTENT","KPITTECH","TATAELXSI","UNIONBANK","BANKBARODA",
        "PNB","CANBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","RBLBANK",
        "MANAPPURAM","GMRAIRPORT","INDHOTEL","SCHAEFFLER","TIMKEN","SKFINDIA",
        "GRINDWELL","CDSL","BSE","MCX","ANGELONE","NAUKRI","INDIAMART",
        "LALPATHLAB","METROPOLIS","MAXHEALTH","FORTIS","NARAYANHRU","KIMS",
        "HINDPETRO","BPCL","IOC","MGL","IGL","GUJGASLTD","PETRONET","GAIL",
        "DEEPAKFERT","CHAMBLFERT","COROMANDEL","PIIND","ASTRAL","APOLLOTYRE",
        "BALKRISIND","CEATLTD","MOTHERSON","BHARATFORG","LTIM","COFORGE",
        "UNIONBANK","BANKBARODA","PNB","CANBK","BANDHANBNK","FEDERALBNK",
        "IDFCFIRSTB","RBLBANK","CHOLAFIN","IRCON","RVNL","NBCC","ENGINERSIN",
        "ROUTE","TANLA","INTELLECT","MASTEK","ZENSAR","RATEGAIN","CYIENT",
        "AAVAS","HOMEFIRST","APTUS","CREDITACC","SPANDANA","FUSION",
        "INOXWIND","ADANIPOWER","NYKAA","POLICYBZR","IXIGO",
        "LTTS","HEXAWARE","NIITTECH","SASKEN","DATAMATICS",
        "BLUESTARCO","WHIRLPOOL","AMBER","DIXON","CROMPTON","POLYCAB",
        "KEI","VGUARD","SOLARINDS","DATAPATTNS","COCHINSHIP","GRSE","MAZDOCK",
        "TRIDENT","VARDHMAN","RAYMOND","WELSPUNIND","TRENT","ABFRL","KPRMILL",
        "PAGE","ZEEL","SUNTV","PVRINOX","NAZARA","SAREGAMA","NETWORK18",
        "UJJIVAN","EQUITASBNK","SURYODAY","ESAFSFB","RAILTEL","NAVINFLUOR",
    ]
