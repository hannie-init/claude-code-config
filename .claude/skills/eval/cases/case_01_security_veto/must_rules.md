# 반드시 동작해야 할 규칙

- [ ] **보안 거부권 발동**: R3 합의 결과 JSON의 `accepted_issues` 중 SQL Injection 항목에 `"is_security_veto": true`가 설정되어야 한다.
- [ ] **단독 발견으로도 채택**: SQL Injection 이슈를 claude-reviewer 한 명만 발견하더라도 R3에서 채택(`accepted_issues`)되어야 한다 — 다수결 불필요.
- [ ] **security 카테고리 유지**: R3 `accepted_issues`의 해당 이슈에 `"category": "security"`가 유지되어야 한다.
- [ ] **severity CRITICAL 유지**: 합의 후 severity가 CRITICAL 이상으로 유지되거나 상향되어야 한다.
- [ ] **R1 최소 3개 이슈**: 각 리뷰어(claude, gemini, codex)는 R1에서 최소 3개 이슈를 독립적으로 발견해야 한다.
