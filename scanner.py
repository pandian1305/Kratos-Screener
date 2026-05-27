"""
SETUP 1 — Monthly CPR Magnet
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Strategy: Price is sandwiched between Daily 20 SMA
and Daily 50 SMA (20 must be > 50), AND price is
within 0.5%–1.5% of Monthly CPR (BC, Pivot, or TC).
This signals price is in a CPR "magnet zone" with
bullish SMA structure — high probability reversal.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import os, time
import pandas as pd
from datetime import datetime
import pytz
from common import (get_all_nse_symbols, fetch_daily, resample_monthly,
                    calc_cpr, tv_discord, tv_telegram,
                    send_discord_msg, send_telegram_msg, parallel_scan)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DISCORD_WEBHOOK  = os.environ["DISCORD_WEBHOOK"]

MIN_PRICE       = 30
MAX_PRICE       = 600
MIN_VOLUME      = 100000
CPR_BUFFER_LOW  = 0.005
CPR_BUFFER_HIGH = 0.015
IST = pytz.timezone("Asia/Kolkata")

def scan(symbol):
    try:
        daily = fetch_daily(symbol, days=400)
        if daily is None or len(daily) < 55: return None

        close  = daily["Close"].iloc[-1]
        volume = int(daily["Volume"].iloc[-1])
        if not (MIN_PRICE <= close <= MAX_PRICE): return None
        if volume < MIN_VOLUME: return None

        sma20 = daily["Close"].rolling(20).mean().iloc[-1]
        sma50 = daily["Close"].rolling(50).mean().iloc[-1]
        if pd.isna(sma20) or pd.isna(sma50): return None
        if sma20 <= sma50: return None
        if not (min(sma20, sma50) <= close <= max(sma20, sma50)): return None

        monthly = resample_monthly(daily)
        if monthly is None or len(monthly) < 3: return None

        pm  = monthly.iloc[-2]
        cpr = calc_cpr(pm["High"], pm["Low"], pm["Close"])

        nearest, name, min_dist = None, None, float("inf")
        for n, lv in {"BC": cpr["bc"], "Pivot": cpr["pivot"], "TC": cpr["tc"]}.items():
            d = abs(close - lv) / lv
            if CPR_BUFFER_LOW <= d <= CPR_BUFFER_HIGH and d < min_dist:
                min_dist, nearest, name = d, lv, n
        if nearest is None: return None

        return {
            "symbol": symbol, "price": round(close, 2),
            "sma20": round(sma20, 2), "sma50": round(sma50, 2),
            "cpr_level": name, "cpr_value": round(nearest, 2),
            "cpr_dist": round(min_dist * 100, 2), "volume": volume
        }
    except: return None

def send_alerts(results, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")

    # Discord
    send_discord_msg(DISCORD_WEBHOOK,
        f"```\n{'='*48}\n"
        f"  📌 SETUP 1 — Monthly CPR Magnet\n"
        f"  🔍 KRATOS SCREENER | {now_str}\n"
        f"  Price ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}\n"
        f"  D20 > D50 SMA | Price between SMAs\n"
        f"  Price within 0.5–1.5% of Monthly CPR\n"
        f"  Matches: {len(results)} stocks\n"
        f"{'='*48}\n```"
    )
    if results:
        for r in results:
            send_discord_msg(DISCORD_WEBHOOK,
                f"**{r['symbol']}** — ₹{r['price']}\n"
                f"> CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)\n"
                f"> D20 SMA: ₹{r['sma20']} | D50 SMA: ₹{r['sma50']}\n"
                f"> Volume: {r['volume']:,}\n"
                f"> 📊 {tv_discord(r['symbol'])}\n"
            )
    else:
        send_discord_msg(DISCORD_WEBHOOK, "_No stocks matched Setup 1 today_")
    send_discord_msg(DISCORD_WEBHOOK,
        f"```\nNext Scan: Tomorrow 5:00 PM IST\n{'='*48}\n```")

    # Telegram
    lines = [
        "📌 *Setup 1 — Monthly CPR Magnet*",
        "🔍 *KRATOS SCREENER*", f"📅 {now_str}",
        f"💰 ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}",
        f"Total: *{len(results)} stocks*\n" + "─"*20
    ]
    if results:
        for r in results[:25]:
            lines += [
                f"*{r['symbol']}* — ₹{r['price']}",
                f"CPR {r['cpr_level']}: ₹{r['cpr_value']} ({r['cpr_dist']}% away)",
                f"D20: ₹{r['sma20']} | D50: ₹{r['sma50']}",
                f"Vol: {r['volume']:,}",
                f"📊 {tv_telegram(r['symbol'])}\n"
            ]
    else:
        lines.append("No stocks matched today")
    lines.append("⏰ Next: Tomorrow 5 PM IST")
    send_telegram_msg(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, "\n".join(lines))

def main():
    now = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"SETUP 1 — Monthly CPR Magnet")
    print(f"Scans ALL NSE stocks | ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol>{MIN_VOLUME:,}")
    print(f"Started: {now.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*50}\n")

    symbols = get_all_nse_symbols()
    print(f"Total symbols to scan: {len(symbols)}\n")

    results, scanned, skipped = parallel_scan(symbols, scan, max_workers=10)
    results.sort(key=lambda x: x["volume"], reverse=True)

    print(f"\n{'='*50}")
    print(f"Scanned:{scanned} | Skipped:{skipped} | Matched:{len(results)}")
    print(f"{'='*50}\n")

    send_alerts(results, now)
    print("Alerts sent ✅")

if __name__ == "__main__":
    main()
