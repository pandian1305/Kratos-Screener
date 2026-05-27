"""
common.py — Shared utilities for Kratos Screener.
Render.com compatible version.
- No Cloudflare WARP (not available on Render)
- Uses yfinance with retry logic and rotating user-agents
- Smaller batches + longer delays to avoid Yahoo Finance rate limiting
"""
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from io import StringIO
import time
import random
import pytz

IST = pytz.timezone("Asia/Kolkata")

# Rotating user agents to reduce Yahoo Finance blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",
]


# ─── FETCH ALL NSE SYMBOLS ────────────────────────────────
def get_all_nse_symbols():
    """Fetch complete NSE equity list — all listed stocks."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = requests.get(url, headers={
            "User-Agent": random.choice(USER_AGENTS),
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
                print(f"✅ Loaded {len(symbols)} NSE symbols from NSE archives")
                return symbols
    except Exception as e:
        print(f"NSE fetch failed: {e}")

    print("⚠️ Using fallback Nifty 500 list")
    return get_fallback_symbols()


# ─── DOWNLOAD DATA WITH RETRY ─────────────────────────────
def _download_single_with_retry(ticker, period="1y", retries=3):
    """
    Download a single ticker with retries and exponential backoff.
    Returns DataFrame or None.
    """
    import yfinance as yf
    for attempt in range(retries):
        try:
            raw = yf.download(
                ticker,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=30,
            )
            if raw is not None and not raw.empty and len(raw) >= 20:
                return raw
        except Exception as e:
            wait = (2 ** attempt) + random.uniform(0.5, 1.5)
            print(f"  Retry {attempt+1}/{retries} for {ticker}: {e}")
            time.sleep(wait)
    return None


# ─── DOWNLOAD ALL NSE DATA IN BATCHES ─────────────────────
def download_all_data(symbols, period="1y"):
    """
    Download OHLCV for all symbols using yfinance.
    Render-compatible: smaller batches (5), longer delays (5–8s),
    per-ticker retry on failure.
    Returns dict: {symbol: DataFrame with Date,Open,High,Low,Close,Volume}
    """
    import yfinance as yf

    tickers    = [f"{s}.NS" for s in symbols]
    all_data   = {}
    batch_size = 5          # Smaller batches — Render has no WARP
    delay_min  = 5          # Seconds between batches (min)
    delay_max  = 8          # Seconds between batches (max)
    batches    = [tickers[i:i+batch_size] for i in range(0, len(tickers), batch_size)]
    total      = len(tickers)
    done       = 0
    failed     = 0

    print(f"Downloading {total} stocks in {len(batches)} batches of {batch_size}...")
    print(f"Estimated time: {len(batches) * 6 / 60:.0f}–{len(batches) * 9 / 60:.0f} mins")
    start_time = time.time()

    for batch_num, batch in enumerate(batches):
        try:
            raw = yf.download(
                batch,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=30,
            )

            if raw is None or raw.empty:
                # Retry each ticker individually on batch failure
                for ticker in batch:
                    sym = ticker.replace(".NS", "")
                    df  = _download_single_with_retry(ticker, period)
                    if df is not None:
                        df = _clean_df(df)
                        if df is not None:
                            all_data[sym] = df
                            done += 1
                        else:
                            failed += 1; done += 1
                    else:
                        failed += 1; done += 1
                continue

            for ticker in batch:
                sym = ticker.replace(".NS", "")
                try:
                    if len(batch) == 1:
                        df = raw.copy()
                    else:
                        if ticker not in raw.columns.get_level_values(0):
                            # Single ticker missing — retry individually
                            df_retry = _download_single_with_retry(ticker, period)
                            if df_retry is not None:
                                df_retry = _clean_df(df_retry)
                                if df_retry is not None:
                                    all_data[sym] = df_retry
                            failed += 1
                            done   += 1
                            continue
                        df = raw[ticker].copy()

                    df = _clean_df(df)
                    if df is not None:
                        all_data[sym] = df
                        done += 1
                    else:
                        failed += 1
                        done   += 1

                except Exception:
                    failed += 1
                    done   += 1
                    continue

        except Exception as e:
            print(f"  Batch {batch_num+1} failed: {e} — retrying individually")
            for ticker in batch:
                sym = ticker.replace(".NS", "")
                df  = _download_single_with_retry(ticker, period)
                if df is not None:
                    df = _clean_df(df)
                    if df is not None:
                        all_data[sym] = df
                        done += 1
                    else:
                        failed += 1; done += 1
                else:
                    failed += 1; done += 1

        # Progress every 10 batches
        if (batch_num + 1) % 10 == 0:
            elapsed = time.time() - start_time
            pct     = done / total * 100
            print(f"  [{batch_num+1}/{len(batches)}] {done}/{total} ({pct:.0f}%) "
                  f"| Got:{len(all_data)} Failed:{failed} | {elapsed:.0f}s elapsed")

        # Random delay between batches — avoids Yahoo Finance throttling
        time.sleep(random.uniform(delay_min, delay_max))

    elapsed = time.time() - start_time
    print(f"\n✅ Download complete: {len(all_data)} stocks in {elapsed:.0f}s "
          f"({elapsed/60:.1f} mins)")
    return all_data


def _clean_df(df):
    """Normalise a raw yfinance DataFrame. Returns cleaned df or None."""
    try:
        df = df.dropna(subset=["Close"])
        if len(df) < 20:
            return None
        df = df.reset_index()
        for col in ["Date", "Datetime", "index"]:
            if col in df.columns:
                df = df.rename(columns={col: "Date"})
                break
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                return None
        return df
    except Exception:
        return None


# ─── RESAMPLE HELPERS ─────────────────────────────────────
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


# ─── CPR CALCULATION ──────────────────────────────────────
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


# ─── TRADINGVIEW LINKS ────────────────────────────────────
def tv_discord(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[Daily]({b}D) | [Weekly]({b}W) | [1Hr]({b}60)"

def tv_telegram(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[D]({b}D) | [W]({b}W) | [1H]({b}60)"


# ─── SEND HELPERS ─────────────────────────────────────────
def send_discord_msg(webhook, msg):
    for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
        try:
            requests.post(webhook, json={"content": chunk}, timeout=10)
        except:
            pass
        time.sleep(0.3)


def send_telegram_msg(token, chat_id, msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        try:
            requests.post(url, json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=10)
        except:
            pass
        time.sleep(0.5)


# ─── FALLBACK SYMBOL LIST ─────────────────────────────────
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
        "DEEPAKFERT","IRCON","RVNL","NBCC","ENGINERSIN","ROUTE","TANLA",
        "INTELLECT","MASTEK","ZENSAR","RATEGAIN","CYIENT","AAVAS","HOMEFIRST",
        "APTUS","CREDITACC","SPANDANA","FUSION","INOXWIND","ADANIPOWER",
        "NYKAA","POLICYBZR","IXIGO","LTTS","HEXAWARE","NIITTECH","SASKEN",
        "BLUESTARCO","WHIRLPOOL","AMBER","DIXON","CROMPTON","POLYCAB",
        "KEI","VGUARD","SOLARINDS","DATAPATTNS","COCHINSHIP","GRSE","MAZDOCK",
        "TRIDENT","VARDHMAN","RAYMOND","WELSPUNIND","TRENT","ABFRL","KPRMILL",
        "PAGE","ZEEL","SUNTV","PVRINOX","NAZARA","SAREGAMA","RAILTEL",
        "UJJIVAN","EQUITASBNK","SURYODAY","ESAFSFB","NAVINFLUOR","NETWORK18",
    ]
