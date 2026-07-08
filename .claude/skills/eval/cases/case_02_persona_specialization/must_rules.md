# 반드시 동작해야 할 규칙

- [ ] **gemini-reviewer 전문성**: gemini-reviewer의 R1 결과에 N+1 쿼리 이슈가 `severity: HIGH` 이상으로 포함되어야 한다 (performance 전문 페르소나).
- [ ] **claude-reviewer 전문성**: claude-reviewer의 R1 결과에 SRP 위반 이슈가 포함되어야 한다 (design 전문 페르소나).
- [ ] **페르소나 차별화**: R1에서 세 리뷰어가 동일한 이슈 목록을 내지 않아야 한다 — 각 리뷰어의 primary axis에 해당하는 이슈가 서로 다른 우선순위로 나타나야 한다.
- [ ] **R3 합의 채택**: N+1 이슈와 SRP 이슈 모두 R3 `accepted_issues`에 포함되어야 한다 (두 이슈 모두 명백히 존재하므로 다수결 통과 예상).
- [ ] **R1 최소 3개 이슈**: 각 리뷰어가 독립적으로 3개 이상 이슈를 발견해야 한다.
