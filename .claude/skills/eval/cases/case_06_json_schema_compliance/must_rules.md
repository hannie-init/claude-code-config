# 반드시 동작해야 할 규칙

- [ ] **전 라운드 JSON 파싱 가능**: R1, R2, R3, R4 모든 라운드의 출력 JSON이 유효한 JSON이어야 한다 (마크다운 펜스, 설명 텍스트 없음).
- [ ] **R1 필수 필드 완전성**: 각 리뷰어의 R1 JSON이 `reviewer`, `language`, `summary`, `issues` 필드를 포함하고, 각 이슈에 `id`, `title`, `description`, `severity`, `category`, `line_start`, `line_end`, `suggestion` 필드가 모두 존재해야 한다.
- [ ] **R2 필수 필드 완전성**: 각 리뷰어의 R2 JSON이 `reviewer`, `responses`, `missed_issues` 필드를 포함하고, 각 response에 `issue_id`, `stance`, `reasoning` 필드가 존재해야 한다.
- [ ] **R3 필수 필드 완전성**: R3 JSON이 `accepted_issues`, `rejected_issue_ids`, `rejection_reasons`, `overall_verdict` 필드를 포함하고, 각 accepted_issue에 `issue_id`, `title`, `severity`, `category`, `agreement_count`, `is_security_veto`, `final_suggestion`, `rationale` 필드가 존재해야 한다.
- [ ] **R4 필수 필드 완전성**: 각 리뷰어의 R4 JSON이 `reviewer`, `issue_verdicts`, `new_issues`, `overall_verdict`, `summary` 필드를 포함하고, 각 verdict에 `issue_id`, `resolved`, `confidence`, `note` 필드가 존재해야 한다.
- [ ] **열거형 값 준수**: `severity`는 `CRITICAL|HIGH|MEDIUM|LOW`, `stance`는 `AGREE|DISAGREE|PARTIAL`, `overall_verdict`는 `PASS|PARTIAL|FAIL`만 허용.
- [ ] **보안 거부권**: CRITICAL 하드코딩 키 이슈가 R3에서 `is_security_veto: true`로 채택되어야 한다.
