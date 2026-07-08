# 반드시 동작해야 할 규칙

- [ ] **다수결 기각 로직**: R2에서 2명 이상이 DISAGREE한 이슈는 R3의 `rejected_issue_ids`에 포함되어야 한다 (`is_security_veto`가 아닌 경우).
- [ ] **기각 이유 기록**: 기각된 이슈는 `rejection_reasons`에 기각 근거가 기록되어야 한다.
- [ ] **보안 이슈 비기각**: 보안 카테고리 이슈는 다수결과 관계없이 기각되지 않아야 한다.
- [ ] **R3 JSON 필드 완전성**: `accepted_issues`, `rejected_issue_ids`, `rejection_reasons`, `overall_verdict` 모두 JSON에 존재해야 한다.
- [ ] **R1 최소 3개 이슈**: 각 리뷰어가 독립적으로 3개 이상 이슈를 발견해야 한다.
