"""
SETUP 2 — Weekly S2 Watch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Price near (within 1%) or below Weekly S2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import os
import pandas as pd
from datetime import datetime
import pytz
from common import (
    get_all_nse_symbols, download_all_data,
    resample_weekly, calc_cpr,
    tv_discord, tv_telegram,
    send_discord_msg, send_telegram_msg
)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DISCORD_WEBHOOK  = os.environ["DISCORD_WEBHOOK"]

MIN_PRICE        = 30
MAX_PRICE        = 600
MIN_VOLUME       = 100000
WEEKLY_S2_BUFFER = 0.01
IST = pytz.timezone("Asia/Kolkata")


def check(symbol, daily):
    try:
        close  = daily["Close"].iloc[-1]
        volume = int(daily["Volume"].iloc[-1])
        if not (MIN_PRICE <= close <= MAX_PRICE): return None
        if volume < MIN_VOLUME: return None

        weekly = resample_weekly(daily)
        if weekly is None or len(weekly) < 4: return None

        cw  = weekly.iloc[-1]
        ws2 = calc_cpr(cw["High"], cw["Low"], cw["Close"])["s2"]

        s2_dist  = (close - ws2) / ws2
        near_s2  = abs(s2_dist) <= WEEKLY_S2_BUFFER
        below_s2 = close < ws2
        if not (near_s2 or below_s2): return None

        if below_s2 and not near_s2:
            trigger = f"Below W-S2 ({round(abs(s2_dist)*100,2)}% below)"
        elif near_s2 and not below_s2:
            trigger = f"Near W-S2 ({round(abs(s2_dist)*100,2)}% away)"
        else:
            trigger = "At W-S2"

        return {
            "symbol":symbol, "price":round(close,2),
            "weekly_s2":round(ws2,2), "trigger":trigger,
            "s2_dist":round(abs(s2_dist)*100,2), "volume":volume
        }
    except: return None


def send_alerts(results, now):
    now_str = now.strftime("%d %b %Y | %I:%M %p IST")
    send_discord_msg(DISCORD_WEBHOOK,
        f"```\n{'='*48}\n"
        f"  📌 SETUP 2 — Weekly S2 Watch\n"
        f"  🔍 KRATOS SCREENER | {now_str}\n"
        f"  Price ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}\n"
        f"  Price near (1%) or below Weekly S2\n"
        f"  Matches: {len(results)} stocks\n"
        f"{'='*48}\n```"
    )
    if results:
        for r in results:
            send_discord_msg(DISCORD_WEBHOOK,
                f"**{r['symbol']}** — ₹{r['price']}\n"
                f"> Trigger: {r['trigger']}\n"
                f"> Weekly S2: ₹{r['weekly_s2']} | Distance: {r['s2_dist']}%\n"
                f"> Volume: {r['volume']:,}\n"
                f"> 📊 {tv_discord(r['symbol'])}\n"
            )
    else:
        send_discord_msg(DISCORD_WEBHOOK, "_No stocks matched Setup 2 today_")
    send_discord_msg(DISCORD_WEBHOOK,
        f"```\nNext Scan: Tomorrow 5:00 PM IST\n{'='*48}\n```")

    lines = [
        "📌 *Setup 2 — Weekly S2 Watch*",
        "🔍 *KRATOS SCREENER*", f"📅 {now_str}",
        f"💰 ₹{MIN_PRICE}–₹{MAX_PRICE} | Vol > {MIN_VOLUME:,}",
        f"Total: *{len(results)} stocks*\n" + "─"*20
    ]
    for r in results[:25]:
        lines += [
            f"*{r['symbol']}* — ₹{r['price']}",
            f"Trigger: {r['trigger']}",
            f"Weekly S2: ₹{r['weekly_s2']} | Dist: {r['s2_dist']}%",
            f"Vol: {r['volume']:,}",
            f"📊 {tv_telegram(r['symbol'])}\n"
        ]
    if not results: lines.append("No stocks matched today")
    lines.append("⏰ Next: Tomorrow 5 PM IST")
    send_telegram_msg(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, "\n".join(lines))


def main():
    now = datetime.now(IST)
    print(f"\n{'='*50}")
    print(f"SETUP 2 — Weekly S2 Watch")
    print(f"Started: {now.strftime('%d %b %Y %I:%M %p IST')}")
    print(f"{'='*50}\n")

    symbols  = get_all_nse_symbols()
    all_data = download_all_data(symbols, period="1y")

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
