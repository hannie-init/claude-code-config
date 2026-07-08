# 채점 기준

## 필수 통과 조건 (하나라도 실패 시 FAIL)

- [ ] R3 `accepted_issues`에 `category: "security"` 이슈가 1개 이상 존재한다.
- [ ] 해당 보안 이슈의 `is_security_veto`가 `true`다.
- [ ] R3 `accepted_issues`에 포함된 보안 이슈의 `severity`가 `CRITICAL`이다.
- [ ] R1에서 세 리뷰어 중 최소 한 명이 `line_start`가 16~21 범위 내 SQL Injection을 발견했다.
- [ ] R3 최종 JSON이 파싱 가능하고 `accepted_issues`, `rejected_issue_ids`, `rejection_reasons`, `overall_verdict` 필드를 모두 포함한다.

## 품질 점수 (0~10)

- **보안 이슈 발견 완전성** (3점): 5개 SQL Injection 취약 메서드 중 발견 개수에 비례 (1개=1점, 3개=2점, 5개=3점)
- **수정 제안 구체성** (2점): `final_suggestion`이 PreparedStatement 또는 파라미터 바인딩 방법을 구체적으로 명시하면 2점, 막연하면 1점
- **R2 논의 깊이** (2점): 세 리뷰어가 R2에서 SQL Injection의 영향 범위(어느 메서드가 더 위험한지 등)를 추가로 논의하면 2점
- **R4 수정 검증** (2점): R4에서 SQL Injection 수정이 올바르게 검증되면 2점 (PreparedStatement 교체 확인)
- **R1 독립성** (1점): 세 리뷰어가 완전히 독립적인 시각으로 동일 이슈를 다른 표현으로 발견하면 1점

## 감점 조건

- SQL Injection을 LOW 또는 MEDIUM으로 판정: -3점
- `is_security_veto`를 `false`로 설정하거나 누락: -3점 (필수 조건 실패)
- 리뷰어가 서로 R1 결과를 복사한 흔적(동일한 description 문자열): -2점
