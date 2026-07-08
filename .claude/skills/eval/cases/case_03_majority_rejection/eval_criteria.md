# 채점 기준

## 필수 통과 조건 (하나라도 실패 시 FAIL)

- [ ] R3 결과에 `rejected_issue_ids` 배열이 존재하고 최소 1개의 기각된 이슈 ID가 포함된다.
- [ ] `rejection_reasons` 객체에 기각된 이슈 ID를 키로 하는 이유 문자열이 존재한다.
- [ ] R2에서 2명 이상이 DISAGREE한 이슈가 R3 `accepted_issues`에 없다 (기각 확인).
- [ ] R3 JSON이 파싱 가능하고 스키마 필수 필드 4개(`accepted_issues`, `rejected_issue_ids`, `rejection_reasons`, `overall_verdict`)를 모두 포함한다.

## 품질 점수 (0~10)

- **기각 로직 정확성** (3점): R2에서 DISAGREE 2개 이상인 이슈가 R3에서 정확히 기각되면 3점; 기각은 했으나 이유가 불충분하면 2점; 기각 로직이 작동했으나 보안 이슈도 함께 기각했다면 0점
- **기각 이유 품질** (2점): rejection_reasons가 단순 "disagreed"가 아닌 "2명이 DISAGREE — 실제 버그가 아닌 코딩 스타일 선호 차이" 수준의 구체적 이유를 포함하면 2점
- **올바른 이슈 채택** (3점): limit 미검증, isEligible 노출, 트랜잭션 불일치 등 실제 이슈가 accepted_issues에 포함되면 각 1점
- **R2 토론 품질** (2점): R2에서 리뷰어들이 서로 다른 시각으로 명시적 DISAGREE 근거를 제시하면 2점

## 감점 조건

- 보안 카테고리 이슈가 DISAGREE를 이유로 기각됨: -4점 (필수 조건 위반 수준)
- `rejection_reasons`가 빈 객체 `{}`이거나 누락: -2점
- R3가 R1의 모든 이슈를 accepted_issues에 그대로 포함 (기각 메커니즘 미작동): -3점
