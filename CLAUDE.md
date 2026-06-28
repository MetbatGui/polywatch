# Polywatch — 개발 워크플로우

## 브랜치 전략

브랜치 단위 = 유닛 개발 1개 (단일 도메인 객체 or 단일 기능).
브랜치당 커밋 수: TDD 3단계 × stub 수 → 보통 3~9커밋.

메이저 변경 시:
1. `master`에서 브랜치 분기
2. 통합개발 사이클 진행
3. 코드리뷰 통과
4. 브랜치 push
5. `git merge --no-ff` → master 병합 + 종합 변경점 커밋

## 통합개발 사이클

1. **통합 테스트 작성** — stub으로 전부 pass하는 상태
2. **유닛 개발 사이클** — 각 stub 실구현 (아래 참조)
3. **Regression** — 통합 테스트 전체 실행
4. 실패 시 보완 → 3번 반복
5. 전체 통과 → 사이클 종료

## 유닛 개발 사이클

각 stub 구현 시:
1. **TDD** — red → green → refactor
2. `uvx ty check <diff>` — 타입 체크
3. `uvx ruff check <diff>` — 린트

## 커밋 주기

TDD 각 단계마다 커밋:
1. 실패 테스트 작성 → 실패 확인 → **커밋**
2. 구현 → 전체 통과 → lint → **커밋**
3. 리팩토링 → lint → **커밋**

## 커밋 컨벤션

형식: `{gitmoji} {type}: {subject}`

본문 항상 작성. WHY 중심 — 설계 결정, 제약, 비자명한 이유.

```
🧪 test: WalletClassifier insider 분류 실패 테스트

insider 기준 낮게 설정 (win_rate>0.6).
탐색 모드 — 재현율 우선.
```

| 단계 | gitmoji | type |
|---|---|---|
| 실패 테스트 | 🧪 | test |
| 구현 | ✨ | feat |
| 버그 수정 | 🐛 | fix |
| 리팩토링 | ♻️ | refactor |
| 문서 | 📝 | docs |
| 설정/의존성 | 🔧 | chore |

## 프로젝트 구조

DDD 레이어 기준 (`docs/agents/ddd_architecture.md` 참조):

```
src/
  domain/        # Entity, VO, Domain Service — 외부 의존 없음
  application/   # Application Service, Port 인터페이스
  infrastructure/# Port 구현체 (HTTP, DB, Telegram)
tests/
  unit/          # domain/ 테스트 — 순수 로직
  integration/   # application/ 테스트 — VCR fixture
  fixtures/      # 실제 API 응답 캡처본
docs/
  agents/        # AI 에이전트용 참조 문서
```

## 테스트 전략

- **테스트 프레임워크**: pytest
- **유닛 테스트**: 도메인 로직만, 외부 의존 없음
- **통합 테스트**: VCR 패턴 — `tests/fixtures/`에 실제 API 응답 캡처 후 재생
- **코드리뷰**: `/code-review` 스킬 사용 (브랜치 merge 전)
