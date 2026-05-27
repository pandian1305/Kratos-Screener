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

MIN_PRICE         = 35
CPR_BUFFER_LOW    = 0.005
CPR_BUFFER_HIGH   = 0.015
SMA_BUFFER        = 0.01
WEEKLY_S2_BUFFER  = 0.01
MONTHLY_R2_BUFFER = 0.015

IST = pytz.timezone("Asia/Kolkata")

# ─── NSE SYMBOL LIST ──────────────────────────────────────
def get_nse_symbols():
    """Fetch all NSE equity symbols via multiple fallback methods."""
    # Method 1: GitHub hosted NSE symbol list (reliable, updated regularly)
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        # Use a better source - NSE symbols from public GitHub repo
        url2 = "https://raw.githubusercontent.com/NikhilBhutani/nse-data/master/data/nse_symbols.csv"
        resp = requests.get(url2, timeout=15)
        if resp.status_code == 200:
            lines = resp.text.strip().split("\n")
            symbols = [l.strip().split(",")[0].strip() for l in lines[1:] if l.strip()]
            symbols = [s for s in symbols if s and s.isalpha()]
            if len(symbols) > 100:
                print(f"Method 1: Loaded {len(symbols)} symbols")
                return symbols
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2: NSE India via requests with full browser headers + session
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        session.get("https://www.nseindia.com/", timeout=10)
        time.sleep(2)
        resp = session.get(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
            timeout=20
        )
        if resp.status_code == 200:
            df = pd.read_csv(pd.io.common.StringIO(resp.text))
            symbols = df["SYMBOL"].dropna().tolist()
            symbols = [s.strip() for s in symbols if isinstance(s, str) and s.strip().replace("-","").replace("&","").isalnum()]
            print(f"Method 2: Loaded {len(symbols)} symbols")
            return symbols
    except Exception as e:
        print(f"Method 2 failed: {e}")

    # Method 3: Use hardcoded Nifty 500 (guaranteed fallback)
    print("Using Nifty 500 fallback list")
    return get_nifty500_fallback()

def get_nifty500_fallback():
    return [
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","ITC",
        "SBIN","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI",
        "WIPRO","ULTRACEMCO","NESTLEIND","TATAMOTORS","SUNPHARMA","TITAN",
        "HCLTECH","BAJFINANCE","BAJAJFINSV","TECHM","NTPC","POWERGRID",
        "ONGC","COALINDIA","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL",
        "HINDALCO","VEDL","GRASIM","DIVISLAB","DRREDDY","CIPLA","APOLLOHOSP",
        "EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","MM","TATACONSUM","BRITANNIA",
        "DABUR","MARICO","PIDILITIND","BERGEPAINT","HAVELLS","VOLTAS",
        "SIEMENS","ABB","CUMMINSIND","THERMAX","BHEL","BEL","HAL","IRCTC",
        "DMART","ZOMATO","HDFCLIFE","SBILIFE","ICICIPRULI","MUTHOOTFIN",
        "CHOLAFIN","LICHSGFIN","RECLTD","PFC","IRFC","HUDCO","NHPC",
        "SJVN","TATAPOWER","ADANIGREEN","CESC","TORNTPOWER","JSWENERGY",
        "SUZLON","ZYDUSLIFE","LUPIN","AUROPHARMA","TORNTPHARM","ALKEM",
        "IPCALAB","NATCOPHARM","GRANULES","BIOCON","LAURUSLABS","DIVILAB",
        "PIDILITIND","SRF","ATUL","DEEPAKNTR","TATACHEM","GNFC","GSFC",
        "CHAMBLFERT","COROMANDEL","PIIND","ASTRAL","SUPREMEIND","APOLLOTYRE",
        "MRF","BALKRISIND","CEATLTD","MOTHERSON","BHARATFORG","JINDALSAW",
        "MPHASIS","LTIM","COFORGE","PERSISTENT","KPITTECH","TATAELXSI",
        "UNIONBANK","BANKBARODA","PNB","CANBK","BANDHANBNK","FEDERALBNK",
        "IDFCFIRSTB","RBLBANK","DCBBANK","CHOLAFIN","MANAPPURAM",
        "GMRAIRPORT","INDHOTEL","LEMONTREE","CHALET","MAHINDCIE",
        "SCHAEFFLER","TIMKEN","SKFINDIA","GRINDWELL","CRISIL","ICRA",
        "CDSL","BSE","MCX","ANGELONE","MOTILALOFS","IIFL","5PAISA",
        "NAUKRI","JUSTDIAL","INDIAMART","CARTRADE","EASEMYTRIP",
        "POLICYBZR","PAYTM","ZOMATO","SWIGGY","IXIGO","YATHARTH",
        "LALPATHLAB","METROPOLIS","THYROCARE","KRSNAA","VIJAYA",
        "MAXHEALTH","FORTIS","NARAYANHRU","KIMS","RAINBOW","MEDANTA",
        "TATACHEM","GHCL","VINATIORG","FINEORG","SUDARSCHEM","NAVINFLUOR",
        "FLUOROCHEM","CLEAN","AAVAS","HOMEFIRST","APTUS","CREDITACC",
        "SPANDANA","AROHAN","FUSION","UJJIVAN","EQUITASBNK","SURYODAY",
        "ESAFSFB","UTKARSHBNK","JSFB","NSLNISP","TEJASNET","STLTECH",
        "RAILTEL","IRCON","RVNL","NBCC","ENGINERSIN","HFCL","GTLINFRA",
        "TATACOMM","ROUTE","TANLA","INTELLECT","MASTEK","NIITTECH",
        "ZENSAR","RATEGAIN","MPHASIS","CYIENT","SASKEN","KSOLVES",
        "DATAMATICS","ECLERX","HINDPETRO","BPCL","IOC","MGL","IGL",
        "GUJGASLTD","MAHANAGAR","PETRONET","GAIL","GSPL","AEGISCHEM",
        "DEEPAKFERT","GNFC","RASHTRIYA","FACT","NFL","CHAMBAL","RCF",
        "PRAJIND","THERMAX","ELGIEQUIP","GREAVESCOT","ISGEC","AIAENG",
        "GMMPFAUDLR","KENNAMETAL","VOLTAMP","TEXMOPIPES","IFBIND",
        "BLUESTARCO","WHIRLPOOL","SYMPHONY","AMBER","DIXON","PG",
        "ORIENTELEC","BAJAJCON","CROMPTON","POLYCAB","FINOLEX","KEI",
        "VGUARD","HAVELLS","SOLARINDS","APOLLOMICRO","PARAS","MTAR",
        "DATAPATTNS","BHEL","BEML","MIDHANI","COCHINSHIP","GRSE",
        "MAZDOCK","GARFIBRES","ALOK","TRIDENT","VARDHMAN","RAYMOND",
        "WELSPUNIND","GOKEX","NITIN","SPENCERS","TRENT","SHOPERSTOP",
        "ABFRL","KPRMILL","PAGE","DOLLAR","RUPA","LUXIND","NITIN"
    ]

# ─── FETCH DATA VIA STOOQ ─────────────────────────────────
def fetch_daily_stooq(symbol, days=400):
    """
    Fetch daily OHLCV from Stooq.com — works from any IP globally.
    NSE symbols on stooq use format: SYMBOL.NS (e.g. RELIANCE.NS)
    """
    try:
        end   = date.today()
        start = end - timedelta(days=days)
        url = (
            f"https://stooq.com/q/d/l/"
            f"?s={symbol.lower()}.ns"
            f"&d1={start.strftime('%Y%m%d')}"
            f"&d2={end.strftime('%Y%m%d')}"
            f"&i=d"
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code != 200 or "No data" in resp.text or len(resp.text) < 50:
            return None

        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        if df.empty or len(df) < 10:
            return None

        df.columns = [c.strip() for c in df.columns]
        df = df.rename(columns={
            "Date": "Date", "Open": "Open", "High": "High",
            "Low": "Low", "Close": "Close", "Volume": "Volume"
        })
        df["Date"]   = pd.to_datetime(df["Date"])
        df["Open"]   = pd.to_numeric(df["Open"],   errors="coerce")
        df["High"]   = pd.to_numeric(df["High"],   errors="coerce")
        df["Low"]    = pd.to_numeric(df["Low"],    errors="coerce")
        df["Close"]  = pd.to_numeric(df["Close"],  errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
        df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
        return df if len(df) >= 10 else None
    except Exception as e:
        return None

def resample_weekly(df):
    d = df.set_index("Date")
    w = d.resample("W").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
    return w.reset_index()

def resample_monthly(df):
    d = df.set_index("Date")
    m = d.resample("ME").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
    return m.reset_index()

def fetch_data(symbol):
    """Fetch and prepare all timeframes."""
    try:
        daily = fetch_daily_stooq(symbol, days=400)
        if daily is None or len(daily) < 60:
            return None

        weekly = resample_weekly(daily)
        if weekly is None or len(weekly) < 8:
            return None

        monthly = resample_monthly(daily)
        if monthly is None or len(monthly) < 3:
            return None

        return {"daily": daily, "weekly": weekly, "monthly": monthly}
    except:
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
    return {"pivot":pivot,"bc":bc,"tc":tc,"r1":r1,"r2":r2,"s1":s1,"s2":s2}

# ─── SETUP 1: Monthly CPR Magnet ──────────────────────────
def check_setup1(data, symbol):
    try:
        daily, monthly = data["daily"], data["monthly"]
        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE: return None

        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50): return None
        if sma20 <= sma50: return None
        if not (min(sma20,sma50) <= close <= max(sma20,sma50)): return None

        pm = monthly.iloc[-2]
        cpr = calculate_cpr(pm["High"], pm["Low"], pm["Close"])
        nearest, name, min_dist = None, None, float("inf")
        for n, lv in {"BC":cpr["bc"],"Pivot":cpr["pivot"],"TC":cpr["tc"]}.items():
            d = abs(close - lv) / lv
            if CPR_BUFFER_LOW <= d <= CPR_BUFFER_HIGH and d < min_dist:
                min_dist, nearest, name = d, lv, n
        if nearest is None: return None

        return {
            "symbol":symbol,"price":round(close,2),
            "sma20":round(sma20,2),"sma50":round(sma50,2),
            "cpr_level":name,"cpr_value":round(nearest,2),
            "cpr_dist":round(min_dist*100,2),
            "volume":int(daily["Volume"].iloc[-1]),
            "setup":"Setup 1"
        }
    except: return None

# ─── SETUP 2: Weekly Level Watch ──────────────────────────
def check_setup2(data, symbol):
    try:
        daily, weekly = data["daily"], data["weekly"]
        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE: return None

        pwl = weekly["Low"].iloc[-2]
        cw  = weekly.iloc[-1]
        ws2 = calculate_cpr(cw["High"],cw["Low"],cw["Close"])["s2"]

        below_pwl = close < pwl
        s2_dist   = abs(close - ws2) / ws2
        near_s2   = s2_dist <= WEEKLY_S2_BUFFER
        if not (below_pwl or near_s2): return None

        trigger = []
        if below_pwl: trigger.append(f"Below PWL ₹{round(pwl,2)}")
        if near_s2:   trigger.append(f"Near W\\_S2 ₹{round(ws2,2)} ({round(s2_dist*100,2)}% away)")

        return {
            "symbol":symbol,"price":round(close,2),
            "pwl":round(pwl,2),"weekly_s2":round(ws2,2),
            "trigger":" | ".join(trigger),
            "volume":int(daily["Volume"].iloc[-1]),
            "setup":"Setup 2"
        }
    except: return None

# ─── SETUP 3: Monthly R2 Compression ──────────────────────
def check_setup3(data, symbol):
    try:
        daily, monthly = data["daily"], data["monthly"]
        close = daily["Close"].iloc[-1]
        if close < MIN_PRICE: return None

        pm   = monthly.iloc[-2]
        cpr  = calculate_cpr(pm["High"],pm["Low"],pm["Close"])
        mr1, mr2 = cpr["r1"], cpr["r2"]
        if close <= mr1: return None
        r2_dist = abs(close - mr2) / mr2
        if r2_dist > MONTHLY_R2_BUFFER: return None

        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50): return None
        sma_diff = abs(sma20 - sma50) / sma50
        if sma_diff > SMA_BUFFER: return None

        return {
            "symbol":symbol,"price":round(close,2),
            "monthly_r1":round(mr1,2),"monthly_r2":round(mr2,2),
            "r2_dist":round(r2_dist*100,2),
            "sma20":round(sma20,2),"sma50":round(sma50,2),
            "sma_diff":round(sma_diff*100,2),
            "volume":int(daily["Volume"].iloc[-1]),
            "setup":"Setup 3"
        }
    except: return None

# ─── TRADINGVIEW LINKS ────────────────────────────────────
def tv_discord(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[D]({b}D) | [W]({b}W) | [1H]({b}60)"

def tv_telegram(sym):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    return f"[D]({b}D) | [W]({b}W) | [1H]({b}60)"

# ─── FORMAT DISCORD ───────────────────────────────────────
def format_discord(r1, r2, r3, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    msgs = []
    msgs.append(
        f"```\n{'='*48}\n"
        f"  🔍 KRATOS SCREENER — DAILY SCAN\n"
        f"  {now_str}\n"
        f"{'='*48}\n```"
    )

    def section(title, results, detail_fn):
        lines = [f"**📌 {title}** — {len(results)} stocks\n"]
        if results:
            for r in results[:15]:
                lines.append(f"**{r['symbol']}** — ₹{r['price']}")
                for d in detail_fn(r):
                    lines.append(f"> {d}")
                lines.append(f"> Vol: {r['volume']:,}")
                lines.append(f"> 📊 {tv_discord(r['symbol'])}\n")
        else:
            lines.append("_No stocks matched today_\n")
        lines.append("─"*40)
        return "\n".join(lines)

    msgs.append(section("Setup 1 — Monthly CPR Magnet", r1,
        lambda r: [f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
                   f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}"]))
    msgs.append(section("Setup 2 — Weekly Level Watch", r2,
        lambda r: [f"Trigger: {r['trigger']}",
                   f"PWL: ₹{r['pwl']} | W\\_S2: ₹{r['weekly_s2']}"]))
    msgs.append(section("Setup 3 — Monthly R2 Compression", r3,
        lambda r: [f"R1: ₹{r['monthly_r1']} | R2: ₹{r['monthly_r2']} ({r['r2_dist']}% away)",
                   f"SMA20: ₹{r['sma20']} | SMA50: ₹{r['sma50']} (diff: {r['sma_diff']}%)"]))

    total = len(r1)+len(r2)+len(r3)
    msgs.append(f"```\nTotal Alerts : {total}\nNext Scan    : Tomorrow 6:00 PM IST\n{'='*48}\n```")
    return msgs

# ─── FORMAT TELEGRAM ──────────────────────────────────────
def format_telegram(r1, r2, r3, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    lines = [f"🔍 *KRATOS SCREENER*", f"📅 {now_str}", ""]

    def section(title, results, detail_fn):
        lines.append(f"*{title}* — {len(results)} stocks")
        lines.append("─"*20)
        if results:
            for r in results[:5]:
                lines.append(f"*{r['symbol']}* — ₹{r['price']}")
                for d in detail_fn(r): lines.append(d)
                lines.append(f"Vol: {r['volume']:,}")
                lines.append(f"📊 {tv_telegram(r['symbol'])}")
                lines.append("")
        else:
            lines.append("No stocks matched\n")

    section("📌 Setup 1 — Monthly CPR Magnet", r1,
        lambda r: [f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
                   f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}"])
    section("📌 Setup 2 — Weekly Level Watch", r2,
        lambda r: [f"Trigger: {r['trigger']}",
                   f"PWL: ₹{r['pwl']} | W\\_S2: ₹{r['weekly_s2']}"])
    section("📌 Setup 3 — Monthly R2 Compression", r3,
        lambda r: [f"R1: ₹{r['monthly_r1']} | R2: ₹{r['monthly_r2']} ({r['r2_dist']}% away)",
                   f"SMA diff: {r['sma_diff']}%"])

    total = len(r1)+len(r2)+len(r3)
    lines += [f"✅ *Total: {total} alerts*", "⏰ Next: Tomorrow 6 PM IST"]
    return "\n".join(lines)

# ─── SEND DISCORD ─────────────────────────────────────────
def send_discord(messages):
    for msg in messages:
        for chunk in [msg[i:i+1900] for i in range(0,len(msg),1900)]:
            requests.post(DISCORD_WEBHOOK, json={"content": chunk})
            time.sleep(0.5)

# ─── SEND TELEGRAM ────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chunk in [message[i:i+4000] for i in range(0,len(message),4000)]:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID, "text": chunk,
            "parse_mode": "Markdown", "disable_web_page_preview": True
        })
        time.sleep(0.5)

# ─── MAIN ─────────────────────────────────────────────────
def main():
    now_ist = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"Kratos Screener: {now_ist.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"Data source: Stooq.com")
    print(f"{'='*50}\n")

    symbols = get_nse_symbols()
    print(f"Scanning {len(symbols)} NSE stocks...\n")

    r1, r2, r3 = [], [], []
    scanned = skipped = 0

    for symbol in symbols:
        try:
            data = fetch_data(symbol)
            if data is None:
                skipped += 1
                continue

            s1 = check_setup1(data, symbol)
            s2 = check_setup2(data, symbol)
            s3 = check_setup3(data, symbol)

            if s1: r1.append(s1)
            if s2: r2.append(s2)
            if s3: r3.append(s3)

            scanned += 1
            if scanned % 25 == 0:
                print(f"  ✓ {scanned} scanned | {skipped} skipped | "
                      f"S1:{len(r1)} S2:{len(r2)} S3:{len(r3)}")

            time.sleep(0.2)

        except Exception as e:
            skipped += 1

    r1.sort(key=lambda x: x["volume"], reverse=True)
    r2.sort(key=lambda x: x["volume"], reverse=True)
    r3.sort(key=lambda x: x["volume"], reverse=True)

    print(f"\n{'='*50}")
    print(f"Scan Complete! Scanned:{scanned} Skipped:{skipped}")
    print(f"Setup1:{len(r1)} Setup2:{len(r2)} Setup3:{len(r3)}")
    print(f"{'='*50}\n")

    send_discord(format_discord(r1, r2, r3, now_ist))
    print("Discord sent ✅")

    send_telegram(format_telegram(r1, r2, r3, now_ist))
    print("Telegram sent ✅\nDone!")

if __name__ == "__main__":
    main()
