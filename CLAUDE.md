# Polywatch — 개발 워크플로우

## 브랜치 전략

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

## 테스트 전략

- **유닛 테스트**: 도메인 로직만, API 레이어 완전 제거
- **통합 테스트**: VCR 패턴 — 실제 API 응답을 `tests/fixtures/`에 캡처 후 재생. 결정적 + 현실적.
- **코드리뷰**: `/code-review` 스킬 사용 (브랜치 merge 전)
