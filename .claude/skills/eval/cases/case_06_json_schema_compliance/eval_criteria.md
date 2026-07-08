# 채점 기준

## 필수 통과 조건 (하나라도 실패 시 FAIL)

- [ ] R1 (claude, gemini, codex 세 결과 모두) JSON 파싱 성공.
- [ ] R2 (claude, gemini, codex 세 결과 모두) JSON 파싱 성공.
- [ ] R3 JSON 파싱 성공.
- [ ] R4 (claude, gemini, codex 세 결과 모두) JSON 파싱 성공.
- [ ] R1 각 이슈 객체에 `id`, `title`, `description`, `severity`, `category`, `line_start`, `line_end`, `suggestion` 8개 필드 모두 존재.
- [ ] R3 각 accepted_issue 객체에 `issue_id`, `title`, `severity`, `category`, `agreement_count`, `is_security_veto`, `final_suggestion`, `rationale` 8개 필드 모두 존재.
- [ ] R4 각 issue_verdict 객체에 `issue_id`, `resolved`, `confidence`, `note` 4개 필드 모두 존재.
- [ ] `severity` 값이 `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` 중 하나.
- [ ] `stance` 값이 `AGREE`, `DISAGREE`, `PARTIAL` 중 하나.
- [ ] `overall_verdict` 값이 `PASS`, `PARTIAL`, `FAIL` 중 하나.
- [ ] R3 `accepted_issues`에 `is_security_veto: true`인 항목이 1개 이상 존재.

## 품질 점수 (0~10)

- **R1 이슈 발견 완전성** (3점): MUST 이슈 6개 중 발견 개수에 비례 (1~2개=1점, 3~4개=2점, 5~6개=3점)
- **심각도 정확성** (2점): 하드코딩 키=CRITICAL, Optional.get()/예외삼킴=HIGH, 중복 검사=MEDIUM, 매직넘버=LOW가 모두 정확하면 2점; 1~2개 오류면 1점
- **R2 응답 완전성** (2점): R2에서 각 리뷰어가 R1의 모든 이슈(다른 리뷰어 것 포함)에 AGREE/DISAGREE/PARTIAL 응답을 달면 2점
- **R4 `confidence` 범위** (2점): 모든 `confidence` 값이 0.0~1.0 범위이고, 수정된 이슈는 0.7 이상, 미수정은 0.5 이하로 설정되면 2점
- **R3 rationale 품질** (1점): 각 accepted_issue의 `rationale`이 2문장 이하이면서 채택 근거를 명확히 설명하면 1점

## 감점 조건

- JSON에 마크다운 코드 펜스(```json) 포함: 라운드당 -2점
- JSON 파싱 실패: 라운드당 -3점 (필수 조건 실패)
- 필수 필드 누락: 필드 1개당 -0.5점
- 열거형 외 값 사용 (예: severity="IMPORTANT"): -1점
