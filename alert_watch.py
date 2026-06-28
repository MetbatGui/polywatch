"""4개 핵심 마켓 가격 이상징후 감시 + TG 알림
10분마다 yes_price 변화 추적 → 급변 or 대형 신규 포지션 시 TG 발송
"""
import json, requests, time, pickle, sys, os, traceback
from datetime import datetime
from pathlib import Path

# Windows 에러 다이얼로그 억제
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x8007)

# 작업 디렉토리 고정 (VBS/스케줄러 실행 시 경로 보장)
os.chdir(Path(__file__).parent)
sys.path.insert(0, 'eda')
from wallet_cache import tg_send

DATA = "https://data-api.polymarket.com/v1"
GAMMA = "https://gamma-api.polymarket.com/markets"
STATE_FILE = Path("alert_watch_state.pkl")
LOG_FILE = Path("alert_watch.log")

MARKETS = {
    "이란핵_2027": {
        "cid": "0x8bdeac60c92d3bc494792fd334ca181b0cf70355f23dca4098d558280b554c81",
        "q": "Iran Nuke before 2027",
        "price_alert": 0.04,   # 4센트 이상 이동 시 알림
        "min_position": 2000,  # $2K+ 신규 포지션 알림
    },
    "파나마운하": {
        "cid": "0x0686076be591223c6da6a594c12b4a47083fbd77a37ddc96f484eba3b13e3669",
        "q": "US takes Panama Canal before 2027",
        "price_alert": 0.05,
        "min_position": 2000,
    },
    "미국인플레3.8_June": {
        "cid": "0x1a64843d427607b164ea18493a30066de60f10abbbdc559066be494528378886",
        "q": "Will annual inflation be 3.8% in June?",
        "price_alert": 0.05,
        "min_position": 5000,
    },
    "이란핵합의_Congress": {
        "cid": "0x0665610d8a06655edb83376e45fd8d2dd78889d2b3a1b2668efe398514cf87ae",
        "q": "Congress approves Iran deal in 2026",
        "price_alert": 0.05,
        "min_position": 1000,
    },
}

CYCLE_MIN = 10


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


CLOB = "https://clob.polymarket.com"

def get_yes_price(cid):
    r = requests.get(f"{CLOB}/markets/{cid}", timeout=8)
    r.raise_for_status()
    tokens = r.json().get("tokens", [])
    for t in tokens:
        if t.get("outcome") == "Yes":
            return float(t["price"])
    return None


def get_positions(cid):
    r = requests.get(f"{DATA}/market-positions",
                     params={"market": cid, "sortBy": "TOKENS", "status": "OPEN"},
                     timeout=8)
    data = r.json()
    positions = {}
    for item in (data if isinstance(data, list) else [data]):
        for pos in item.get("positions", []):
            wallet = pos.get("proxyWallet") or pos.get("user", "")
            positions[wallet] = pos
    return positions


def run_cycle(state, cycle):
    alerts = []

    for key, cfg in MARKETS.items():
        cid = cfg["cid"]
        q_short = cfg["q"][:40]

        # 현재 yes 가격
        try:
            yes_now = get_yes_price(cid)
        except Exception as e:
            log(f"  price err {key}: {e}")
            continue

        if yes_now is None:
            continue

        prev_yes = state.get(f"{key}_yes")

        # 가격 이상징후
        if prev_yes is not None:
            move = yes_now - prev_yes
            if abs(move) >= cfg["price_alert"]:
                direction = "↑" if move > 0 else "↓"
                alerts.append(
                    f"📈 가격 급변 [{key}]\n"
                    f"{q_short}\n"
                    f"yes: {prev_yes:.3f} → {yes_now:.3f} ({move:+.3f}) {direction}\n"
                    f"시각: {datetime.now().strftime('%H:%M KST')}"
                )
                log(f"  PRICE ALERT {key}: {prev_yes:.3f} → {yes_now:.3f} ({move:+.3f})")

        state[f"{key}_yes"] = yes_now

        # 포지션 이상징후 (신규 대형 진입)
        try:
            positions = get_positions(cid)
        except Exception as e:
            log(f"  pos err {key}: {e}")
            continue

        prev_pos = state.get(f"{key}_pos", {})

        for wallet, pos in positions.items():
            val = float(pos.get("currentValue") or 0)
            avg = float(pos.get("avgPrice") or 0)
            outcome = pos.get("outcome", "")
            name = pos.get("name", "") or wallet[:16]

            if val < cfg["min_position"]:
                continue

            is_new = wallet not in prev_pos
            prev_val = float((prev_pos.get(wallet) or {}).get("currentValue") or 0)
            big_increase = val > prev_val * 1.5 and val - prev_val > cfg["min_position"] * 0.5

            # 불확실 구간 진입 (Yes avg 0.2-0.7)
            in_uncertain = 0.2 <= avg <= 0.7 if outcome == "Yes" else 0.2 <= (1 - avg) <= 0.7

            if (is_new or big_increase) and in_uncertain and cycle > 1:
                tag = "신규" if is_new else "증액"
                alerts.append(
                    f"🚨 의심 포지션 [{key}][{tag}]\n"
                    f"{q_short}\n"
                    f"{name} [{outcome}] avg={avg:.3f} val=${val:,.0f}\n"
                    f"시각: {datetime.now().strftime('%H:%M KST')}"
                )
                log(f"  POS ALERT {key}: {name} [{outcome}] avg={avg:.3f} val=${val:,.0f} [{tag}]")

        state[f"{key}_pos"] = positions
        log(f"  {key}: yes={yes_now:.4f} pos={len(positions)}개")

    return alerts, state


def main():
    log("=== alert_watch 시작 ===")
    log(f"감시 마켓: {list(MARKETS.keys())}")
    log(f"주기: {CYCLE_MIN}분")

    if STATE_FILE.exists():
        with open(STATE_FILE, "rb") as f:
            state = pickle.load(f)
        log("이전 상태 로드")
    else:
        state = {}

    cycle = 0
    while True:
        cycle += 1
        t0 = time.time()
        log(f"\n--- 사이클 #{cycle} ---")

        try:
            alerts, state = run_cycle(state, cycle)
        except Exception as e:
            log(f"사이클 오류: {e}")
            alerts = []

        with open(STATE_FILE, "wb") as f:
            pickle.dump(state, f)

        if alerts:
            for alert in alerts:
                log(f"TG 발송: {alert[:60]}")
                tg_send(alert)
        else:
            log("이상징후 없음")

        elapsed = time.time() - t0
        sleep_time = max(0, CYCLE_MIN * 60 - elapsed)
        log(f"다음 사이클: {CYCLE_MIN}분 후 ({elapsed:.1f}s 소요)")
        time.sleep(sleep_time)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception:
            err = traceback.format_exc()
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] FATAL CRASH — 60초 후 재시작\n{err}\n")
            time.sleep(60)
