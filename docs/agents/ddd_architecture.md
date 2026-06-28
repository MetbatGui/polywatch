# DDD 실전 압축 가이드

## 핵심 원칙

비즈니스 문제를 코드 구조로 직접 표현한다.
기술(DB, API, 프레임워크)이 도메인을 오염시키지 않는다.

---

## 레이어 구조

```
┌─────────────────────────────┐
│      Infrastructure         │  DB, HTTP, Telegram, 파일 I/O
├─────────────────────────────┤
│       Application           │  유스케이스 조율, 트랜잭션 경계
├─────────────────────────────┤
│         Domain              │  비즈니스 규칙, 순수 로직
└─────────────────────────────┘
```

**의존 방향**: Infrastructure → Application → Domain
Domain은 아무것도 import하지 않는다 (stdlib 제외).

---

## 빌딩 블록

### Entity
- **식별자**로 구별. 상태 변경 가능.
- 언제: 동일한 것이 시간에 따라 변할 수 있을 때.
- 예: `Market(condition_id=...)` — 가격이 바뀌어도 같은 마켓

### Value Object
- **값**으로 구별. 불변. 교체하지 변경 안 함.
- 언제: 두 객체의 모든 속성이 같으면 동일한 것일 때.
- 예: `Price(value=0.73)`, `WalletAddress("0xabc...")`

### Aggregate
- Entity + Value Object 묶음. **일관성 경계**.
- 외부는 Aggregate Root만 접근.
- 언제: 함께 변경되어야 하는 객체 그룹.
- 예: `Market` aggregate → `Position` 리스트 포함

### Domain Service
- 특정 Entity/VO에 속하지 않는 **도메인 로직**.
- 상태 없음 (stateless). 순수 함수처럼.
- 언제: "이 로직이 어느 객체에 있어야 하는지 모호할 때."
- 예: `WalletClassifier.classify(profile)`, `SignalDetector.check(prev, curr)`

### Repository (Port)
- Aggregate를 저장/조회하는 **인터페이스**.
- Domain에는 인터페이스만, 구현은 Infrastructure.
- 예: `MarketRepository` → `SqliteMarketRepository` (infra)

### Port & Adapter (Hexagonal)
- **Port**: 도메인이 외부에 요구하는 인터페이스 (Protocol/ABC)
- **Adapter**: Port 구현체 (실제 HTTP, DB, TG 호출)
- 테스트 시 Adapter를 fixture/fake로 교체.

```
Domain defines:  AlertPort.send(msg: str) -> None
Infra implements: TelegramAdapter.send(msg: str) -> None
Test uses:       FakeAlertAdapter (list에 append)
```

---

## Ubiquitous Language

도메인 전문가와 개발자가 **같은 단어**를 쓴다.
코드의 클래스명·메서드명 = 도메인 용어.

❌ `process_data()`, `handle_item()`
✅ `detect_signals()`, `classify_wallet()`

---

## 식별 체크리스트

| 질문 | 답 → 타입 |
|---|---|
| 식별자로 구별하나? | Entity |
| 값이 같으면 동일한가? | Value Object |
| 함께 변경되어야 하나? | Aggregate로 묶기 |
| 어느 객체에도 안 어울리는 로직? | Domain Service |
| 외부 시스템 호출? | Port (인터페이스) + Adapter (구현) |
| 유스케이스 조율? | Application Service |

---

## 이 프로젝트 적용

### Bounded Context
`polywatch` 단일 컨텍스트 (규모상 분리 불필요).

### Domain 빌딩 블록

```
Entity
  Market         - condition_id, question, yes_price, end_date
  Wallet         - address, name, classification, profile
  Signal         - id, type, market_id, wallet, score, detected_at

Value Object
  Price          - value: float (0~1)
  WalletProfile  - win_rate, n_markets, total_pnl, age_days, bias_up

Domain Service
  MarketFilter      - is_macro(question) → bool
  WalletClassifier  - classify(profile) → Classification
  SignalDetector    - detect(prev_snap, curr_snap, config) → list[Signal]

Aggregate
  MarketSnapshot    - Market + list[Position] (특정 시점 스냅샷)
```

### Ports

```
PolymarketPort   - fetch_top_markets(), fetch_positions(market_id)
                   fetch_wallet_profile(address)
AlertPort        - send(message: str)
MarketRepo       - save_watched(market), get_active_watched()
WalletRepo       - save(wallet), get(address)
```

### Application Services

```
MarketScanService    - top100 조회 → 매크로 필터 → watched_markets 갱신 (1h)
PositionMonitor      - 감시 마켓 포지션 스냅샷 → 시그널 감지 → 알림 (5min)
WalletProfiler       - 신규 대형 지갑 → 프로파일 조회 → 분류 → 저장
```

---

## 테스트 전략 (DDD 관점)

- **Domain 테스트**: 외부 의존 없음. 순수 로직만. 빠름.
- **Application 테스트**: Port를 Fake로 교체. VCR fixture 사용.
- **Infrastructure 테스트**: 실제 DB/HTTP. 최소화.

```python
# Domain 테스트 예시 — 아무것도 import 안 함
def test_classify_insider():
    profile = WalletProfile(win_rate=0.75, n_markets=5, total_pnl=30000, ...)
    assert WalletClassifier.classify(profile) == Classification.INSIDER
```
