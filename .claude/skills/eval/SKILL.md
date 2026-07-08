---
name: eval
description: Golden Dataset으로 멀티 에이전트 코드 리뷰 Harness를 검증합니다. /eval [case_id|--all]
argument-hint: "[case_id | --all]"
allowed_tools:
  - Bash
  - Read
  - Write
  - Agent
---

# Harness Eval Runner

인수: $ARGUMENTS

---

## Step 1 — 케이스 목록 결정

`$ARGUMENTS`를 파싱합니다.

- `--all` 또는 인수 없음 → 아래 6개 전체 실행:
  ```
  case_01_security_veto
  case_02_persona_specialization
  case_03_majority_rejection
  case_04_regression_detection
  case_05_no_false_praise
  case_06_json_schema_compliance
  ```
- 특정 case_id → 해당 케이스 1개만 실행

---

## Step 2 — 케이스별 실행

각 케이스에 대해 아래 2-1 ~ 2-7을 순서대로 수행합니다.

### 2-1. 경로 설정

```
CASE_DIR = .claude/skills/eval/cases/{case_id}
INPUT    = {CASE_DIR}/input.java
CRITERIA = {CASE_DIR}/eval_criteria.md
```

`{CASE_DIR}/input.java` 파일이 존재하는지 Bash로 확인합니다. 없으면 해당 케이스를 `ERROR (파일 없음)`으로 표시하고 다음 케이스로 넘어갑니다.

### 2-2. /review 실행

`{INPUT}` 경로를 인수로 `/review` 스킬을 실행합니다.

```
/review {INPUT}
```

`/review` 완료 후 출력된 마지막 요약 블록에서 `Run ID` 값을 읽습니다.

```
Run ID   : {run_id}
```

### 2-3. 결과 파일 수집

Read 도구로 아래 파일을 읽습니다. 파일이 없으면 `"결과 없음"` 문자열로 대체합니다.

```
R1 = _workspace/01_reviews/{run_id}_result.json
R2 = _workspace/02_debates/{run_id}_result.json
R3 = _workspace/03_consensus/{run_id}_result.json
R4 = _workspace/05_verify/{run_id}_result.json
```

### 2-4. eval_criteria.md 읽기

Read 도구로 `{CRITERIA}` 파일을 읽어 EVAL_CRITERIA 변수에 저장합니다.

### 2-5. Judge LLM 호출

`.claude/skills/eval/judge_prompt.md` 파일을 읽어 프롬프트 템플릿을 가져옵니다.

아래 변수를 치환합니다:

| 변수 | 값 |
|---|---|
| `{case_id}` | 현재 case_id |
| `{eval_criteria}` | EVAL_CRITERIA 내용 |
| `{r1_result}` | R1 파일 내용 |
| `{r2_result}` | R2 파일 내용 |
| `{r3_result}` | R3 파일 내용 |
| `{r4_result}` | R4 파일 내용 |

변수 치환된 프롬프트로 **claude-reviewer 에이전트**를 호출합니다:

```
Agent(
  subagent_type: "claude-reviewer",
  prompt: {치환된 judge_prompt 전문}
)
```

반환된 JSON을 JUDGE_RESULT 변수에 저장합니다.

JSON 파싱 실패 시 재시도 1회. 재시도도 실패하면 해당 케이스를 `ERROR (Judge 응답 파싱 실패)`로 처리합니다.

### 2-6. 필수 조건 집계

JUDGE_RESULT의 `mandatory_checks` 배열에서:

```
total_checks  = mandatory_checks.length
passed_checks = mandatory_checks.filter(c => c.passed == true).length
failed_checks = mandatory_checks.filter(c => c.passed == false)
verdict       = JUDGE_RESULT.verdict  ("PASS" | "FAIL")
quality_score = JUDGE_RESULT.quality_score
```

### 2-7. 결과 저장

Bash로 `.claude/skills/eval/results/` 디렉토리를 생성합니다:

```bash
mkdir -p .claude/skills/eval/results
```

Write 도구로 아래 경로에 결과 파일을 저장합니다:

```
.claude/skills/eval/results/{case_id}_{run_id}_result.md
```

파일 내용:

```markdown
# Eval Result: {case_id}
Run ID: {run_id}

## 종합 판정: {PASS|FAIL}

## 필수 통과 조건

| 조건 | 결과 | 근거 |
|---|---|---|
| {condition} | ✅ PASS / ❌ FAIL | {reason} |
...

## 품질 점수: {quality_score}/10

| 항목 | 점수 |
|---|---|
| {항목} | {점수} |
...

## 감점

{deductions 목록 (없으면 "없음")}

## 종합 평가

{JUDGE_RESULT.summary}
```

### 2-8. 콘솔 출력

```
================================================================
EVAL: {case_id}
================================================================
필수 조건   : {passed_checks}/{total_checks} {PASS|FAIL}
품질 점수   : {quality_score}/10
종합 판정   : {verdict}

실패 조건:
  - {failed_checks[0].condition}
  - {failed_checks[1].condition}
  ... (실패 없으면 이 줄 생략)

상세 리포트: .claude/skills/eval/results/{case_id}_{run_id}_result.md
================================================================
```

---

## Step 3 — --all 최종 요약 (전체 실행 시만)

모든 케이스 완료 후:

```
================================================================
EVAL SUMMARY
================================================================
{case_id}  {PASS|FAIL}  {score}/10  {실패 이유 (FAIL인 경우만)}
...
----------------------------------------------------------------
전체       {pass_count}/{total_count} PASS
평균 점수  {avg_score}/10
================================================================
```

`.claude/skills/eval/results/summary_{run_timestamp}.md` 파일로도 저장합니다.
