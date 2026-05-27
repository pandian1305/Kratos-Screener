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

MIN_PRICE        = 30
MAX_PRICE        = 600
MIN_VOLUME       = 100000
CPR_BUFFER_LOW   = 0.005    # 0.5%
CPR_BUFFER_HIGH  = 0.015    # 1.5%

IST = pytz.timezone("Asia/Kolkata")

# ─── NIFTY 500 SYMBOLS ────────────────────────────────────
def get_symbols():
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
        "SRF","ATUL","DEEPAKNTR","TATACHEM","GNFC","GSFC","CHAMBLFERT",
        "COROMANDEL","PIIND","ASTRAL","SUPREMEIND","APOLLOTYRE","MRF",
        "BALKRISIND","CEATLTD","MOTHERSON","BHARATFORG","MPHASIS","LTIM",
        "COFORGE","PERSISTENT","KPITTECH","TATAELXSI","UNIONBANK","BANKBARODA",
        "PNB","CANBK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","RBLBANK",
        "CHOLAFIN","MANAPPURAM","GMRAIRPORT","INDHOTEL","MAHINDCIE",
        "SCHAEFFLER","TIMKEN","SKFINDIA","GRINDWELL","CDSL","BSE","MCX",
        "ANGELONE","NAUKRI","INDIAMART","LALPATHLAB","METROPOLIS",
        "MAXHEALTH","FORTIS","NARAYANHRU","KIMS","HINDPETRO","BPCL",
        "IOC","MGL","IGL","GUJGASLTD","PETRONET","GAIL","AEGISCHEM",
        "DEEPAKFERT","FACT","CHAMBLFERT","PRAJIND","ELGIEQUIP","AIAENG",
        "BLUESTARCO","WHIRLPOOL","AMBER","DIXON","CROMPTON","POLYCAB",
        "KEI","VGUARD","SOLARINDS","DATAPATTNS","COCHINSHIP","GRSE",
        "MAZDOCK","TRIDENT","VARDHMAN","RAYMOND","WELSPUNIND","TRENT",
        "ABFRL","KPRMILL","PAGE","DOLLAR","RUPA","LUXIND",
        "ZEEL","SUNTV","PVRINOX","NAZARA","SAREGAMA","NETWORK18",
        "UJJIVAN","EQUITASBNK","SURYODAY","ESAFSFB","RAILTEL","IRCON",
        "RVNL","NBCC","ENGINERSIN","ROUTE","TANLA","INTELLECT",
        "MASTEK","ZENSAR","RATEGAIN","CYIENT","ECLERX","KSOLVES",
        "TATACHEM","PIIND","CLEAN","AAVAS","HOMEFIRST","APTUS",
        "CREDITACC","SPANDANA","FUSION","BAJAJHLDNG","RECLTD",
        "NPTC","INOXWIND","RPOWER","JPPOWER","SJVN","ADANIPOWER",
        "TORNTPOWER","CESC","JSWENERGY","TATAPOWER","ADANIGREEN",
        "NYKAA","PAYTM","POLICYBZR","IXIGO","YATHARTH","VIJAYA",
        "MEDANTA","RAINBOW","FORTIS","MAXHEALTH","APOLLOHOSP",
        "LTTS","HEXAWARE","NIITTECH","MPHASIS","SASKEN","DATAMATICS"
    ]

# ─── FETCH DATA ───────────────────────────────────────────
def fetch_daily(symbol, days=400):
    try:
        end   = date.today()
        start = end - timedelta(days=days)
        url = (f"https://stooq.com/q/d/l/?s={symbol.lower()}.ns"
               f"&d1={start.strftime('%Y%m%d')}&d2={end.strftime('%Y%m%d')}&i=d")
        resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        if resp.status_code != 200 or len(resp.text) < 50: return None
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        if df.empty or len(df) < 10: return None
        df.columns = [c.strip() for c in df.columns]
        df["Date"]   = pd.to_datetime(df["Date"])
        df["Close"]  = pd.to_numeric(df["Close"],  errors="coerce")
        df["High"]   = pd.to_numeric(df["High"],   errors="coerce")
        df["Low"]    = pd.to_numeric(df["Low"],    errors="coerce")
        df["Open"]   = pd.to_numeric(df["Open"],   errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
        df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
        return df if len(df) >= 50 else None
    except: return None

def resample_monthly(df):
    d = df.set_index("Date")
    m = d.resample("ME").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
    return m.reset_index()

# ─── CPR ──────────────────────────────────────────────────
def cpr(high, low, close):
    pivot = (high + low + close) / 3
    bc    = (high + low) / 2
    tc    = (2 * pivot) - bc
    return {"pivot":pivot, "bc":bc, "tc":tc}

# ─── SETUP 1: Monthly CPR Magnet ──────────────────────────
def check(data, symbol):
    """
    Price between Daily 20 SMA & 50 SMA (20 > 50)
    + Price within 0.5%–1.5% of Monthly CPR (BC, Pivot, or TC)
    + Price ₹30–₹600, Volume > 1,00,000
    """
    try:
        daily   = data["daily"]
        monthly = data["monthly"]

        close  = daily["Close"].iloc[-1]
        volume = int(daily["Volume"].iloc[-1])

        if not (MIN_PRICE <= close <= MAX_PRICE): return None
        if volume < MIN_VOLUME: return None

        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50): return None
        if sma20 <= sma50: return None
        if not (min(sma20, sma50) <= close <= max(sma20, sma50)): return None

        pm = monthly.iloc[-2]
        c  = cpr(pm["High"], pm["Low"], pm["Close"])

        nearest, name, min_dist = None, None, float("inf")
        for n, lv in {"BC":c["bc"], "Pivot":c["pivot"], "TC":c["tc"]}.items():
            d = abs(close - lv) / lv
            if CPR_BUFFER_LOW <= d <= CPR_BUFFER_HIGH and d < min_dist:
                min_dist, nearest, name = d, lv, n
        if nearest is None: return None

        return {
            "symbol": symbol, "price": round(close, 2),
            "sma20": round(sma20, 2), "sma50": round(sma50, 2),
            "cpr_level": name, "cpr_value": round(nearest, 2),
            "cpr_dist": round(min_dist * 100, 2),
            "volume": volume
        }
    except: return None

# ─── TRADINGVIEW ──────────────────────────────────────────
def tv(sym, platform="discord"):
    b = f"https://www.tradingview.com/chart/?symbol=NSE:{sym}&interval="
    if platform == "discord":
        return f"[Daily]({b}D) | [Weekly]({b}W) | [1Hr]({b}60)"
    return f"[D]({b}D) | [W]({b}W) | [1H]({b}60)"

# ─── SEND DISCORD ─────────────────────────────────────────
def send_discord(results, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")

    header = (
        f"```\n{'='*48}\n"
        f"  📌 SETUP 1 — Monthly CPR Magnet\n"
        f"  🔍 KRATOS SCREENER | {now_str}\n"
        f"  Price: ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}\n"
        f"  Condition: Price between D20 & D50 SMA\n"
        f"             Near Monthly CPR (0.5%–1.5%)\n"
        f"  Total Matches: {len(results)}\n"
        f"{'='*48}\n```"
    )
    send_discord_msg(header)

    if not results:
        send_discord_msg("_No stocks matched today for Setup 1_")
        return

    for r in results:
        msg = (
            f"**{r['symbol']}** — ₹{r['price']}\n"
            f"> CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)\n"
            f"> D20 SMA: ₹{r['sma20']} | D50 SMA: ₹{r['sma50']}\n"
            f"> Volume: {r['volume']:,}\n"
            f"> 📊 {tv(r['symbol'])}\n"
        )
        send_discord_msg(msg)
        time.sleep(0.3)

    send_discord_msg(f"```\nNext Scan: Tomorrow 5:00 PM IST\n{'='*48}\n```")

def send_discord_msg(msg):
    for chunk in [msg[i:i+1900] for i in range(0, len(msg), 1900)]:
        requests.post(DISCORD_WEBHOOK, json={"content": chunk})
        time.sleep(0.3)

# ─── SEND TELEGRAM ────────────────────────────────────────
def send_telegram(results, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    lines = [
        f"📌 *Setup 1 — Monthly CPR Magnet*",
        f"🔍 *KRATOS SCREENER*",
        f"📅 {now_str}",
        f"💰 ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}",
        f"Total: *{len(results)} stocks*",
        "─"*20, ""
    ]

    if not results:
        lines.append("No stocks matched today")
    else:
        for r in results[:20]:
            lines += [
                f"*{r['symbol']}* — ₹{r['price']}",
                f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
                f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}",
                f"Vol: {r['volume']:,}",
                f"📊 {tv(r['symbol'], 'telegram')}",
                ""
            ]

    lines += [f"⏰ Next: Tomorrow 5 PM IST"]

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    msg = "\n".join(lines)
    for chunk in [msg[i:i+4000] for i in range(0, len(msg), 4000)]:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID, "text": chunk,
            "parse_mode": "Markdown", "disable_web_page_preview": True
        })
        time.sleep(0.5)

# ─── MAIN ─────────────────────────────────────────────────
def main():
    now = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"Setup 1 — Monthly CPR Magnet")
    print(f"Started: {now.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*50}\n")

    symbols = get_symbols()
    print(f"Scanning {len(symbols)} stocks...\n")

    results = []
    scanned = skipped = 0

    for symbol in symbols:
        try:
            daily = fetch_daily(symbol, days=400)
            if daily is None:
                skipped += 1
                continue
            monthly = resample_monthly(daily)
            if monthly is None or len(monthly) < 3:
                skipped += 1
                continue

            r = check({"daily": daily, "monthly": monthly}, symbol)
            if r: results.append(r)

            scanned += 1
            if scanned % 25 == 0:
                print(f"  {scanned} scanned | {skipped} skipped | {len(results)} matched")

            time.sleep(0.1)
        except:
            skipped += 1

    results.sort(key=lambda x: x["volume"], reverse=True)

    print(f"\nDone! Scanned:{scanned} Skipped:{skipped} Matched:{len(results)}")

    send_discord(results, now)
    print("Discord ✅")
    send_telegram(results, now)
    print("Telegram ✅")

if __name__ == "__main__":
    main()
