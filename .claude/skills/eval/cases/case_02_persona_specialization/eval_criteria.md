# 채점 기준

## 필수 통과 조건 (하나라도 실패 시 FAIL)

- [ ] gemini-reviewer의 R1 `issues` 배열에 `category: "performance"` 또는 N+1 관련 설명이 포함된 항목이 `severity: "HIGH"` 또는 `"CRITICAL"`로 존재한다.
- [ ] claude-reviewer의 R1 `issues` 배열에 SRP(Single Responsibility), 이메일 발송, PDF 생성 등 설계 위반 관련 항목이 존재한다.
- [ ] R3 `accepted_issues`에 N+1 관련 이슈가 포함된다.
- [ ] R3 `accepted_issues`에 SRP 위반 관련 이슈가 포함된다.
- [ ] 세 리뷰어의 R1 `issues[0].title`이 모두 다르다 (동일한 이슈를 같은 순서로 나열하지 않음).

## 품질 점수 (0~10)

- **페르소나 전문성 차별화** (3점): gemini가 N+1을 가장 먼저(이슈 1번으로), claude가 SRP를 가장 먼저 발견하면 3점; 순서가 틀려도 발견하면 2점; 한 명만 전문 이슈를 발견하면 1점
- **N+1 수정 제안 구체성** (2점): `JOIN FETCH`, `@EntityGraph`, `findAllByOrderIdIn()` 일괄 조회 등 구체적 해결책이 언급되면 2점
- **SRP 수정 제안 구체성** (2점): 이벤트 발행, ApplicationEventPublisher, 분리 서비스 등 구체적 설계 대안이 제시되면 2점
- **중복 total 로직 발견** (1점): SHOULD 이슈인 total 계산 중복을 발견하면 1점
- **R2 토론 품질** (2점): R2에서 리뷰어들이 단순 AGREE/DISAGREE 외에 N+1의 실제 쿼리 수를 추정하거나 SRP 분리 방법을 구체적으로 논의하면 2점

## 감점 조건

- gemini가 N+1을 LOW로 판정: -2점
- claude가 SRP를 발견하지 못함: -2점
- 세 리뷰어 모두 동일한 이슈 목록 (페르소나 차별화 실패): -3점
