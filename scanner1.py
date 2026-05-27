"""
SETUP 1 — Monthly CPR Magnet
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Price between Daily 20 & 50 SMA (20 > 50)
+ Price within 0.5–1.5% of Monthly CPR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import os
import pandas as pd
from datetime import datetime
import pytz
from common import (
    get_all_nse_symbols, download_all_data,
    resample_monthly, calc_cpr,
    tv_discord, tv_telegram,
    send_discord_msg, send_telegram_msg
)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DISCORD_WEBHOOK  = os.environ["DISCORD_WEBHOOK"]

MIN_PRICE       = 30
MAX_PRICE       = 600
MIN_VOLUME      = 100000
CPR_BUFFER_LOW  = 0.005
CPR_BUFFER_HIGH = 0.015
IST = pytz.timezone("Asia/Kolkata")


def check(symbol, daily):
    try:
        close  = daily["Close"].iloc[-1]
        volume = int(daily["Volume"].iloc[-1])
        if not (MIN_PRICE <= close <= MAX_PRICE): return None
        if volume < MIN_VOLUME: return None

        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50): return None
        if sma20 <= sma50: return None
        if not (min(sma20,sma50) <= close <= max(sma20,sma50)): return None

        monthly = resample_monthly(daily)
        if monthly is None or len(monthly) < 3: return None

        pm  = monthly.iloc[-2]
        cpr = calc_cpr(pm["High"], pm["Low"], pm["Close"])

        nearest, name, min_dist = None, None, float("inf")
        for n, lv in {"BC":cpr["bc"],"Pivot":cpr["pivot"],"TC":cpr["tc"]}.items():
            d = abs(close - lv) / lv
            if CPR_BUFFER_LOW <= d <= CPR_BUFFER_HIGH and d < min_dist:
                min_dist, nearest, name = d, lv, n
        if nearest is None: return None

        return {
            "symbol":symbol, "price":round(close,2),
            "sma20":round(sma20,2), "sma50":round(sma50,2),
            "cpr_level":name, "cpr_value":round(nearest,2),
            "cpr_dist":round(min_dist*100,2), "volume":volume
        }
    except: return None


def send_alerts(results, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    send_discord_msg(DISCORD_WEBHOOK,
        f"```\n{'='*48}\n"
        f"  📌 SETUP 1 — Monthly CPR Magnet\n"
        f"  🔍 KRATOS SCREENER | {now_str}\n"
        f"  Price ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}\n"
        f"  D20 > D50 SMA | Price between SMAs\n"
        f"  Near Monthly CPR (0.5–1.5%)\n"
        f"  Matches: {len(results)} stocks\n"
        f"{'='*48}\n```"
    )
    if results:
        for r in results:
            send_discord_msg(DISCORD_WEBHOOK,
                f"**{r['symbol']}** — ₹{r['price']}\n"
                f"> CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)\n"
                f"> D20: ₹{r['sma20']} | D50: ₹{r['sma50']}\n"
                f"> Volume: {r['volume']:,}\n"
                f"> 📊 {tv_discord(r['symbol'])}\n"
            )
    else:
        send_discord_msg(DISCORD_WEBHOOK, "_No stocks matched Setup 1 today_")
    send_discord_msg(DISCORD_WEBHOOK,
        f"```\nNext Scan: Tomorrow 5:00 PM IST\n{'='*48}\n```")

    lines = [
        "📌 *Setup 1 — Monthly CPR Magnet*",
        "🔍 *KRATOS SCREENER*", f"📅 {now_str}",
        f"💰 ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}",
        f"Total: *{len(results)} stocks*\n" + "─"*20
    ]
    for r in results[:25]:
        lines += [
            f"*{r['symbol']}* — ₹{r['price']}",
            f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
            f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}",
            f"Vol: {r['volume']:,}",
            f"📊 {tv_telegram(r['symbol'])}\n"
        ]
    if not results: lines.append("No stocks matched today")
    lines.append("⏰ Next: Tomorrow 5 PM IST")
    send_telegram_msg(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, "\n".join(lines))


def main():
    now = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"SETUP 1 — Monthly CPR Magnet")
    print(f"Started: {now.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*50}\n")

    symbols    = get_all_nse_symbols()
    all_data   = download_all_data(symbols, period="1y")

    results = []
    for symbol, daily in all_data.items():
        try:
            r = check(symbol, daily)
            if r: results.append(r)
        except: continue

    results.sort(key=lambda x: x["volume"], reverse=True)
    print(f"\nMatched: {len(results)} stocks")

    send_alerts(results, now)
    print("✅ Alerts sent!")

if __name__ == "__main__":
    main()
