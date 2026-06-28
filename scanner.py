"""1시간마다 top100 스캔 → 매크로 마켓 추출 → watched_markets 갱신"""
import json, requests, time, sys, os, traceback
from datetime import datetime
from pathlib import Path

os.chdir(Path(__file__).parent)
sys.path.insert(0, 'eda')
from wallet_cache import tg_send
import db

GAMMA = "https://gamma-api.polymarket.com/markets"
LOG = Path("scanner.log")
SCAN_INTERVAL = 3600  # 1시간

MACRO_INCLUDE = {
    "election", "president", "prime minister", "chancellor", "senate",
    "congress", "parliament", "governor", "federal reserve", "fed ",
    "interest rate", "gdp", "inflation", "recession", "ipo ",
    "nuclear", "nuke", "war", "peace", "nato", "sanctions",
    "iran", "russia", "china", "taiwan", "ukraine", "israel",
    "biden", "trump", "harris", "macron", "modi", "erdogan",
    "zelensky", "zelenskyy", "canal", "gulf", "geopolit",
    "referendum", "vote", "ballot", "primary", "runoff",
    "nominee", "leadership", "cabinet", "ceasefire", "treaty",
}

EXCLUDE = {
    "f1 ", "formula", "grand prix", "world cup", "fifa", "wimbledon",
    "fastest lap", "premier league", "bundesliga", "serie a", "la liga",
    "champions league", "tour de", "pga", "t20", "cricket", "rugby",
    "temperature", "weather", "total kills", "odd/even", "score:",
    "shots ", "spread:", "both teams", "clean sheet", "song on",
    "fdv above", "market cap be between", "post 200+",
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_macro(q: str) -> bool:
    q = q.lower()
    if any(kw in q for kw in EXCLUDE):
        return False
    return any(kw in q for kw in MACRO_INCLUDE)


def fetch_top(limit=100) -> list:
    all_markets = []
    for offset in range(0, limit, 100):
        r = requests.get(GAMMA, params={
            "limit": 100, "order": "volume", "ascending": "false", "offset": offset
        }, timeout=10)
        data = r.json()
        if not data:
            break
        all_markets.extend(data)
        if len(data) < 100:
            break
    return all_markets[:limit]


def get_yes_price(m: dict) -> float:
    op = m.get("outcomePrices", '["0.5"]')
    if isinstance(op, str):
        op = json.loads(op)
    return float(op[0]) if op else 0.5


def scan():
    log("스캔 시작")
    markets = fetch_top(100)
    macro = [m for m in markets if is_macro(m.get("question", ""))]
    log(f"top100 중 매크로: {len(macro)}개")

    # 만료된 항목 정리
    expired = db.expire_watched()
    if expired:
        log(f"만료 제거: {expired}개")

    active = {r["condition_id"] for r in db.get_active_watched()}
    new_count = 0

    for m in macro:
        cid = m.get("conditionId", "")
        title = m.get("question", "")
        vol = float(m.get("volume") or 0)
        yes = get_yes_price(m)

        is_new = cid not in active
        db.upsert_watched(cid, title, vol, yes)
        db.insert_snapshot(cid, title, yes)

        if is_new:
            new_count += 1
            log(f"  NEW: {title[:60]} yes={yes:.3f} vol=${vol:,.0f}")
            tg_send(f"🆕 신규 매크로 마켓 감시 추가\n{title[:70]}\nyes={yes:.3f} vol=${vol:,.0f}")

    log(f"신규: {new_count}개 | 총 감시: {len(db.get_active_watched())}개")


def main():
    db.init_db()
    log("=== scanner 시작 (1시간 주기) ===")
    while True:
        try:
            scan()
        except Exception:
            log(f"오류:\n{traceback.format_exc()}")
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"FATAL: {traceback.format_exc()}\n")
            time.sleep(60)
