"""신규 거액 지갑 정보 조회 + JSON 캐싱 + 자동 분류
ponytail: 지갑 수백 개면 JSON dict 충분. 수만 개 넘으면 sqlite로.
"""
import json, requests, time, os
from pathlib import Path

DATA = "https://data-api.polymarket.com/v1"
CACHE = Path(__file__).parent / "data" / "wallets.json"
CACHE.parent.mkdir(exist_ok=True)

# 텔레그램: .env에서 TG_TOKEN, TG_CHAT 로드 (없으면 알림 skip)
ENV = Path(__file__).parent.parent / ".env"
_tg = {}
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("TG_TOKEN="):
            _tg["token"] = line.split("=", 1)[1].strip()
        elif line.startswith("TG_CHAT="):
            _tg["chat"] = line.split("=", 1)[1].strip()


def tg_send(text: str):
    if not _tg.get("token") or not _tg.get("chat"):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{_tg['token']}/sendMessage",
                      json={"chat_id": _tg["chat"], "text": text}, timeout=5)
    except Exception:
        pass


def _load() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def _save(d: dict):
    CACHE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


_cache = _load()


def is_cached(wallet: str) -> bool:
    return wallet in _cache


def fetch_profile(wallet: str) -> dict:
    """지갑 통계: PnL, win_rate, 마켓수, bias, 생성일"""
    out = {"total_trades": 0, "total_pnl": 0.0, "win_rate": 0.0,
           "max_pos_val": 0.0, "avg_pos_val": 0.0, "n_markets": 0,
           "bias_up": 0.5, "profile_age_days": 999}
    try:
        r = requests.get(f"{DATA}/positions",
                         params={"user": wallet, "sizeThreshold": "0.01", "limit": 500}, timeout=8)
        d = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
        pnls = [float(x.get("cashPnl") or 0) + float(x.get("realizedPnl") or 0) for x in d]
        vals = [float(x.get("currentValue") or 0) for x in d]
        ups = sum(1 for x in d if x.get("outcome") == "Up")
        n = len(pnls)
        out["n_markets"] = n
        out["total_pnl"] = round(sum(pnls), 2)
        out["win_rate"] = round(sum(1 for p in pnls if p > 0) / n, 3) if n else 0
        out["max_pos_val"] = round(max(vals), 2) if vals else 0
        out["avg_pos_val"] = round(sum(vals) / len(vals), 2) if vals else 0
        out["bias_up"] = round(ups / n, 3) if n else 0.5
    except Exception:
        pass
    try:
        r = requests.get(f"{DATA}/activity", params={"user": wallet, "limit": 500}, timeout=5)
        acts = r.json()
        ts = [float(a["timestamp"]) for a in acts if a.get("timestamp")]
        out["total_trades"] = len(acts)
        if ts:
            out["profile_age_days"] = round((time.time() - min(ts)) / 86400)
    except Exception:
        pass
    return out


def classify(p: dict) -> str:
    bias, trades = p["bias_up"], p["total_trades"]
    avg, mx = p["avg_pos_val"], p["max_pos_val"]
    wr, n, pnl = p["win_rate"], p["n_markets"], p["total_pnl"]
    if 0.45 <= bias <= 0.55 and trades > 100:
        return "amm_bot"
    if avg > 0.9 and mx >= 1000:
        return "arbitrager"
    if wr > 0.7 and n < 10 and pnl > 20000:
        return "insider"
    if wr < 0.2 and trades > 100 and pnl < -10000:
        return "gambler"
    return "unknown"


def cache_wallet(wallet: str, name: str = None) -> dict:
    """미캐싱이면 조회+분류+저장. 캐싱돼 있으면 기존 반환."""
    if wallet in _cache:
        return _cache[wallet]
    p = fetch_profile(wallet)
    now = time.time()
    rec = {"wallet": wallet, "name": name, "first_seen": now,
           "classification": classify(p), "last_updated": now, **p}
    _cache[wallet] = rec
    _save(_cache)
    if rec["classification"] == "insider":
        tg_send(f"🚨 INSIDER 의심\n{name or wallet}\nWR:{p['win_rate']*100:.0f}% "
                f"{p['n_markets']}mkt PnL:${p['total_pnl']:+,.0f} age:{p['profile_age_days']}d")
    return rec


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = cache_wallet(sys.argv[1])
        print({k: r[k] for k in ("name", "classification", "win_rate", "n_markets",
                                 "total_pnl", "profile_age_days", "max_pos_val")})
    else:
        print(f"캐시: {CACHE} ({len(_cache)}개)")
