# Polywatch 도메인 지식

## 1. 프로젝트 목적

Polymarket 예측시장에서 **인사이더/고래 베팅**을 실시간 감지.
핵심 전제: 불확실 구간(yes 0.2–0.7)에 대형 신규 포지션 진입 후 가격이 그 방향으로 이동 → 정보 우위 신호.

---

## 2. Polymarket API

### Gamma API (마켓 메타데이터)
```
GET https://gamma-api.polymarket.com/markets
  ?slug=btc-updown-5m-{unix_ts}     # 슬러그로 단일 마켓
  ?limit=100&order=volume&ascending=false   # 거래대금 top100
  ?limit=100&order=volume24hr&ascending=false&active=true
```
주요 필드: `conditionId`, `question`, `outcomePrices` (JSON 문자열 배열), `endDate`, `startDate`, `volume`, `volume24hr`, `slug`

`outcomePrices`: `'["0.73","0.27"]'` → Yes 가격, No 가격 (합 = 1)

### Data API (포지션/거래/활동)
```
GET https://data-api.polymarket.com/v1/market-positions
  ?market={conditionId}&sortBy=TOKENS&status=OPEN

GET https://data-api.polymarket.com/v1/positions
  ?user={wallet}&sizeThreshold=0.01&limit=500

GET https://data-api.polymarket.com/v1/activity
  ?user={wallet}&limit=500

GET https://data-api.polymarket.com/trades
  ?user={wallet}&limit=50
```

### CLOB API (실시간 호가)
```
GET https://clob.polymarket.com/markets/{conditionId}
```
`tokens[].outcome == "Yes"` → `tokens[].price` = 현재 yes 가격

### Binance Futures API (BTC 가격)
```
GET https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT
GET https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit=2
```

---

## 3. BTC 단기 마켓 슬러그 규칙

```
btc-updown-5m-{unix_ts}    # 5분봉 Up/Down
btc-updown-15m-{unix_ts}   # 15분봉 Up/Down
btc-updown-1h-{unix_ts}    # 1시간봉
```

`unix_ts`는 **마감 시각** (UTC, 초 단위).
5m 마켓: `ts = (now // 300) * 300` 기준으로 ±600초 탐색.
15m 마켓: `ts = (now // 900 + offset) * 900`.

현재 활성 마켓 찾는 법:
```python
base_ts = (int(now.timestamp()) // 300) * 300
for offset in range(-600, 601, 300):
    slug = f"btc-updown-5m-{base_ts + offset}"
    # 조회 후 startDate < now < endDate 확인
```

---

## 4. 포지션 응답 구조

`/market-positions` 응답: `list[{positions: list[pos]}]`
각 `pos` 필드:
- `proxyWallet` / `user` — 지갑 주소
- `name` — 닉네임 (없으면 지갑 주소)
- `outcome` — `"Yes"/"No"` or `"Up"/"Down"`
- `avgPrice` — 평균 진입가 (0~1)
- `currentValue` — 현재 포지션 달러 가치
- `size` — 토큰 수량
- `realizedPnl`, `cashPnl` — 실현 손익
- `totalBought` — 총 매수 금액

---

## 5. 인사이더 감지 로직

### 시그널 기준 (macro_monitor.py)
| 파라미터 | 값 | 의미 |
|---|---|---|
| `MIN_VAL` | $1,000 | 포지션 최소 규모 |
| `PRICE_ZONE` | 0.2–0.7 | 불확실 구간 (확신 없는 시장에서 진입) |
| `MIN_MOVE` | +0.08 | 진입 후 가격 이동 최소값 |

**EARLY_YES**: Yes 포지션 avg ∈ [0.2, 0.7] + 현재 yes_price - avg ≥ 0.08 + (신규 or 50% 증액)
**EARLY_NO**: No 포지션 avg ∈ [0.2, 0.7] (1-avg 기준) + No 가격 상승 ≥ 0.08 + (신규 or 50% 증액)

### 지갑 스코어링 (market_scanner.py)

**Type A (신규, <14일)**:
| 조건 | 점수 |
|---|---|
| age < 14일 | +4 |
| age < 3일 | +3 추가 |
| 포지션 ≥ max($100K, min_val×10) | +2 |
| avg ∈ (0.3, 0.7) | +1 |
| 마켓수 ≤ 3 | +2 |
| 48시간 내 청산 이력 | +2 |

**Type B (베테랑, 거래 ≥ 20회)**:
| 조건 | 점수 |
|---|---|
| win_rate > 0.70 | +5 |
| win_rate > 0.60 | +3 |
| total_pnl > $100K | +4 |
| total_pnl > $20K | +2 |
| 대형 포지션 | +2 |
| 48h 청산 | +2 |
| 마켓수 ≤ 10 | +1 |

**임계값**: score ≥ 4 → 인사이더 의심

동적 threshold: `min_val = max(500, min(10000, vol24 * 0.005))`

### SYNC 감지 (watch_insiders.py)
같은 사이클에서 ≥3개 포지션이 **동일한 % 변화** (±20% 이상) → 자동화 봇/조율 신호

---

## 6. 지갑 분류 (wallet_cache.py)

```
insider   : win_rate > 0.70, n_markets < 10, total_pnl > $20K
amm_bot   : bias_up ∈ [0.45, 0.55], total_trades > 100
arbitrager: avg_pos_val > 0.9, max_pos_val ≥ $1K
gambler   : win_rate < 0.20, total_trades > 100, total_pnl < -$10K
unknown   : 나머지
```

캐시: `eda/data/wallets.json` (dict, 키=지갑주소)
인사이더 감지 시 Telegram 즉시 발송.

---

## 7. 매크로 마켓 필터

### keyword-based (scanner.py)
포함 키워드: `election, president, federal reserve, fed, interest rate, gdp, inflation, nuclear, war, nato, sanctions, iran, russia, china, taiwan, ukraine, israel, trump, ...`
제외 키워드: `f1, formula, world cup, fifa, wimbledon, premier league, ...`

### LLM-based (market_scanner.py)
`ollama.generate(model="gemma4:e2b", ...)` — JSON 배열 인덱스 반환
fallback: 파싱 실패 시 전체 마켓 반환

---

## 8. 스포츠 마켓 필터 (market_scanner.py)

슬러그 prefix: `fifwc-, atp-, wta-, nba-, nfl-, mlb-, nhl-, wimbledon, ufc-, tennis-, golf-, soccer-, f1-, ...`
이벤트 슬러그 완전 일치: `world-cup-winner`, `2026-womens-wimbledon-winner`
질문 키워드: `" vs "`, `"win the 202"`, `"reach the 2026 fifa"`, ...

---

## 9. DB 스키마 (db.py → polymarket.db)

```sql
market_snapshots : condition_id, title, yes_price, captured_at
positions        : wallet, condition_id, outcome, avg_price, size, current_value, realized_pnl, captured_at
trades           : wallet, condition_id, tx_hash, side, outcome, price, size, ts
wallets          : wallet PK, name, classification, win_rate, n_markets, total_pnl
watched_markets  : condition_id PK, title, volume, yes_price, first_seen, last_seen, expires_at
```

`watched_markets.expires_at = last_seen + 43200` (12시간 TTL)

---

## 10. 프로세스 구성

| 프로세스 | 파일 | 주기 | 역할 |
|---|---|---|---|
| Scanner | `scanner.py` | 1시간 | top100 스캔 → macro 추출 → DB 갱신 → TG 신규 마켓 알림 |
| Alert Watch | `alert_watch.py` | 10분 | 4개 핵심 마켓 가격/포지션 이상 → TG 알림 |
| Macro Monitor | `macro_monitor.py` | 10분 | macro_top.json 전체 포지션 스냅샷 diff → 인사이더 시그널 |
| Market Scanner | `market_scanner.py` | 수동/N분 | top100 심층 분석, 병렬 지갑 스코어링 |
| Insider Watch | `scripts/watch_insiders.py` | 5초 | BTC 5m Up/Down 실시간 홀더 추적 |
| Collector | `macro_collector.py` | 수동 | macro_top.json 마켓 포지션 수집 + 지갑 프로파일링 |

Windows 실행: `alert_watch_silent.vbs` → PowerShell 창 없이 백그라운드 실행

---

## 11. Alert Watch 감시 마켓 (2025-06 기준)

| 키 | 마켓 | 가격 알림 | 최소 포지션 |
|---|---|---|---|
| 이란핵_2027 | Iran Nuke before 2027 | ±0.04 | $2K |
| 파나마운하 | US takes Panama Canal before 2027 | ±0.05 | $2K |
| 미국인플레3.8_June | Will annual inflation be 3.8% in June? | ±0.05 | $5K |
| 이란핵합의_Congress | Congress approves Iran deal in 2026 | ±0.05 | $1K |

---

## 12. 알려진 인사이더/고빈도 트레이더

**names** (watch_insiders.py):
`saintQ, Bigwwinn, std0, Bonereaper, AutomatedTrading, lll1111, PershingSquare, terterbobo, zhangfan151, JadonLeung, 0x50f7, Grailstrades, baloneigh`

**wallets**:
`0xb27bc932...`, `0x04b6D7E9...`, `0x368a83f2...`, `0x3FF45437`, `0x5fCf73bd...`, `0x5083a040...`

---

## 13. EDA 실험 결과 (eda/results.md)

데이터: 60분, 117 스냅샷, 372 지갑

| 가설 | 결과 |
|---|---|
| H1: 멀티프레임 SYNC (5m+15m 동방향) | 31명 중 15명 (48.4%) — 랜덤 수준 |
| H2: 진입 후 1~5분 가격 선행 | 14/42 = 33.3% — **베이스라인(50%) 하회**, 유의미한 선행 없음 |
| H3: 5m vs 15m 거래대금 | 5m/15m = 2.25x — 5m 압도적 우세 |
| H4: KNOWN_INSIDERS 활동 | 13명 중 7명 감지 (Bonereaper, terterbobo, std0 등) |

**결론**: 개별 진입 타이밍 선행 신호 약함. 대신 **알려진 지갑 추적 + 포지션 규모 급변 감지**가 더 효과적.

---

## 14. 환경 설정

```
.env 파일:
  TG_TOKEN=...   # Telegram Bot 토큰
  TG_CHAT=...    # 채팅 ID
```

런타임 상태 파일 (gitignore):
- `*.pkl` — 각 모니터 상태
- `polymarket.db` — SQLite DB
- `eda/data/wallets.json` — 지갑 캐시
- `macro_top.json` — 매크로 마켓 목록

의존성: `requests`, `ollama` (local), `sqlite3` (stdlib)
Python: `.python-version` 기준
