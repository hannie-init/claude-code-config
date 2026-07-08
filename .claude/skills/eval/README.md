# Harness Eval 실행 가이드

멀티 에이전트 코드 리뷰 Harness(Claude + Gemini + Codex)의 동작을 Golden Dataset으로 검증하는 평가 프레임워크입니다.

## 디렉토리 구조

```
evals/
├── cases/                          # Golden Dataset
│   ├── case_01_security_veto/      # 보안 거부권 검증
│   ├── case_02_persona_specialization/  # 페르소나 전문성 검증
│   ├── case_03_majority_rejection/ # 다수결 기각 검증
│   ├── case_04_regression_detection/   # R4 회귀 감지 검증
│   ├── case_05_no_false_praise/    # 심각도 인플레이션 방지 검증
│   └── case_06_json_schema_compliance/ # JSON 스키마 준수 검증
├── results/                        # 실행 결과 저장 (자동 생성)
├── run_eval.md                     # /eval 슬래시 커맨드 정의
├── judge_prompt.md                 # Judge LLM 프롬프트 템플릿
└── README.md                       # 이 파일
```

각 케이스 디렉토리 구조:
```
{case_id}/
├── input.java          # 리뷰 대상 Java 코드
├── expected_issues.md  # 반드시 발견해야 할 이슈 목록
├── must_rules.md       # 반드시 동작해야 할 오케스트레이션 규칙
└── eval_criteria.md    # Judge LLM 채점 기준
```

---

## 실행 방법

### 전체 케이스 실행

```
/eval --all
```

### 특정 케이스만 실행

```
/eval case_01_security_veto
/eval case_02_persona_specialization
/eval case_03_majority_rejection
/eval case_04_regression_detection
/eval case_05_no_false_praise
/eval case_06_json_schema_compliance
```

### 결과 확인

실행 완료 후 `evals/results/` 디렉토리에 결과 파일이 생성됩니다:

```
evals/results/{case_id}_{yyyyMMdd_HHmmss}_result.md
```

---

## 케이스별 검증 목적

| 케이스 | 목적 | 핵심 검증 포인트 |
|---|---|---|
| case_01_security_veto | 보안 거부권 | 한 명만 발견해도 R3 채택, `is_security_veto: true` |
| case_02_persona_specialization | 페르소나 전문성 | Gemini→N+1, Claude→SRP, 다른 우선순위 |
| case_03_majority_rejection | 다수결 기각 | 2명 DISAGREE → R3 `rejected_issue_ids` 기재 |
| case_04_regression_detection | R4 회귀 감지 | 수정 후 `new_issues`에 새 버그 등장 |
| case_05_no_false_praise | 억지 이슈 금지 | 잘 짜인 코드에 CRITICAL 없음, 허위 이슈 없음 |
| case_06_json_schema_compliance | JSON 스키마 준수 | R1~R4 전 라운드 JSON 파싱 성공, 필수 필드 완전 |

---

## 케이스 추가 방법

1. `evals/cases/` 하위에 새 디렉토리 생성 (예: `case_07_your_case/`)
2. 아래 4개 파일을 작성합니다:
   - `input.java` — 리뷰할 Spring Boot Java 코드 (50~100줄 권장)
   - `expected_issues.md` — MUST/SHOULD 이슈 목록
   - `must_rules.md` — 오케스트레이션 동작 요구사항
   - `eval_criteria.md` — 필수 통과 조건 + 품질 점수 기준 + 감점 조건
3. `run_eval.md`의 CASES 목록에 새 케이스 ID를 추가합니다.

### eval_criteria.md 작성 팁

- **필수 통과 조건**: `passed: true/false`로 명확히 판정 가능한 객관적 조건만 작성
- **품질 점수**: 항목 합계가 10점이 되도록 배점 설계
- **감점 조건**: 점수 인플레이션을 막는 페널티 조건 포함

---

## 평가 아키텍처

```
/eval {case_id}
    │
    ├── input.java 읽기
    │
    ├── /review 호출 (4라운드 실행)
    │       ├── R1: claude + gemini + codex 병렬 독립 리뷰
    │       ├── R2: 상호 토론 (AGREE/DISAGREE/PARTIAL)
    │       ├── R3: r3-moderator 합의 (보안 거부권 + 다수결)
    │       └── R4: 수정 후 재검증 (회귀 감지)
    │
    ├── _workspace/{exec_id}/ 에서 결과 수집
    │
    ├── judge_prompt.md + eval_criteria.md → Judge LLM 호출
    │
    └── 결과 저장 → evals/results/{case_id}_{run_id}_result.md
```
