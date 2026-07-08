---
name: review
description: 4-라운드 멀티 에이전트 코드 리뷰 (Claude + Gemini + Codex). 코드 파일을 리뷰해달라는 요청 시 자동 실행됩니다. Java/Kotlin 파일은 karechat 도메인 특화 리뷰어(security-engineer 상시, database-engineer·breaking-change-detector 조건부)를 R1에 자동 편입한다.
argument-hint: "<file_path> [--language python|typescript|java|go|rust|...]"
allowed_tools:
  - Bash
  - Read
  - Write
  - Agent
---

# 4-Round Multi-Agent Code Review Orchestrator

인수: $ARGUMENTS

---

## 준비 단계

다음 단계를 순서대로 실행하세요:

**1. 인수 파싱**

`$ARGUMENTS`에서 파일 경로와 선택적 `--language` 플래그를 파싱합니다.
- `--language` 없으면 파일 확장자로 자동 감지:
  `.py`→python, `.ts`→typescript, `.js`→javascript, `.go`→go, `.rs`→rust,
  `.java`→java, `.kt`→kotlin, `.cs`→csharp, `.cpp`→cpp, `.c`→c,
  `.rb`→ruby, `.php`→php, `.swift`→swift

**2. 파일 읽기**

Read 도구로 대상 파일의 전체 내용을 읽습니다.

**3. 실행 ID 생성**

`date +%s | md5 | head -c 8` (또는 유사한 방법)으로 8자리 hex ID를 생성합니다.

**4. 리뷰 표준 읽기**

`.claude/rules/review-standards.md` 파일을 읽어 REVIEW_STANDARDS 변수에 저장합니다.

**5. 도메인 특화 리뷰어 판별 (Java/Kotlin 전용)**

언어가 `java` 또는 `kotlin`일 때만, 대상 파일의 **경로와 내용**을 스캔해 아래 특화 리뷰어를 추가로 활성화합니다(그 외 언어는 기존 3인 일반 리뷰어만 실행). 활성화된 리뷰어 목록을 SPECIALISTS 변수에 저장합니다.

| 특화 리뷰어 (subagent_type) | 활성화 조건 (파일명 또는 내용 매칭) | reviewer 값 |
|---|---|---|
| `security-engineer` | **Java/Kotlin이면 항상 활성화** | `security` |
| `database-engineer` | 파일명 `*Entity` / `*Repository`, 확장자 `.sql`, 내용에 `@Query` / `@Entity` / `QueryDSL`·`Q타입`(`QXxx`) / `JpaRepository` | `database` |
| `breaking-change-detector` | 파일명 `*Controller` / `*RequestDto` / `*ResponseDto` / `*Request` / `*Response`, 내용에 `@RestController` / `@RequestMapping` / `@GetMapping` 등 매핑 애노테이션 / `enum ` 정의 | `breaking-change` |

> 판별은 대상 파일 1개 기준. 해당 없으면 그 리뷰어는 건너뜁니다. security-engineer는 Java/Kotlin이면 조건 없이 포함합니다.

---

## Round 1: 독립 리뷰 (병렬)

**⚠️ 반드시 단일 메시지에서 Agent 도구를 동시에 호출해야 합니다. 순차 실행 금지.** 기본 3인(claude·gemini·codex)에 더해, 위에서 판별된 SPECIALISTS를 **같은 메시지에서 함께** 호출합니다(예: security-engineer만 활성화면 총 4개, 셋 다면 총 6개).

각 에이전트에 보낼 사용자 메시지를 구성합니다. 기본 3개 에이전트는 동일한 스키마이지만 persona가 다릅니다.

### Claude Reviewer 프롬프트 (subagent_type: claude-reviewer)

```
## Code to Review

Language: {language}

```{language}
{source_code}
```

Review this code according to your persona (Senior Software Architect) and the review standards below.

## Review Standards

{REVIEW_STANDARDS}

## Task
- Identify at least 3 distinct issues
- Include line numbers wherever possible
- Do NOT praise the code — focus entirely on problems and improvements
- Set reviewer field to "claude"

## Required Output Schema (output ONLY this JSON, no fences):
{
  "reviewer": "claude",
  "language": "{language}",
  "summary": "2-3 sentence overall assessment",
  "issues": [
    {
      "id": "R1-001",
      "title": "short one-line title",
      "description": "detailed explanation of the issue",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "security | performance | bug | design | test | style",
      "line_start": null,
      "line_end": null,
      "suggestion": "concrete fix or recommendation"
    }
  ]
}
Minimum 3 issues required in the issues array.
```

### Gemini Reviewer 프롬프트 (subagent_type: gemini-reviewer)

Gemini 에이전트에게 보낼 전체 프롬프트를 구성합니다 (CLI에 그대로 전달됨):

```
# Performance Engineer

You are a performance engineering specialist with deep expertise in runtime efficiency, resource management, and scalability. You have profiled and optimised systems handling millions of requests per second, and you can spot an O(n²) loop or a memory leak from a glance.

## Your Focus Areas

### 1. Algorithmic Complexity
- O(n²) or worse loops that could be O(n log n) or O(n) with a better data structure
- Unnecessary repeated computation inside loops (compute once, reuse)
- Missing memoization or caching where repeated calls with the same input are possible
- Sorting a collection multiple times instead of once

### 2. Memory Efficiency
- Unbounded collection growth (appending to a list/dict with no eviction)
- Loading entire datasets into memory when streaming would work
- Large intermediate objects created and discarded in hot paths
- Retained references that prevent garbage collection

### 3. I/O & Concurrency
- N+1 query patterns (fetching related data inside a loop)
- Missing batching or bulk operations
- Blocking calls inside async functions (sleep, file I/O, network without await)
- Shared mutable state accessed from multiple threads without locks

### 4. Resource Management
- Unclosed file handles, database connections, or sockets
- Missing `with` / context-manager usage
- Connections not returned to pool after use
- Thread or process pool exhaustion from unbounded task submission

## Review Style
- Quantify every performance claim: state the complexity class and a concrete worst-case scenario.
- Recommend the specific data structure or library call that fixes the problem.
- Do NOT flag performance concerns on code that runs once at startup — focus on hot paths.

---

## Review Standards

{REVIEW_STANDARDS}

---

## Code to Review

Language: {language}

```{language}
{source_code}
```

## Task
Review this code. Identify at least 3 distinct issues. Include line numbers wherever possible. Do not praise the code.
Set reviewer field to "gemini".

## Required Output (ONLY valid JSON, no fences, no prose):
{
  "reviewer": "gemini",
  "language": "{language}",
  "summary": "2-3 sentence overall assessment",
  "issues": [
    {
      "id": "R1-001",
      "title": "short one-line title",
      "description": "detailed explanation",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "security | performance | bug | design | test | style",
      "line_start": null,
      "line_end": null,
      "suggestion": "concrete fix"
    }
  ]
}
Minimum 3 issues required.
```

### Codex Reviewer 프롬프트 (subagent_type: codex-reviewer)

Codex 에이전트에게 보낼 전체 프롬프트를 구성합니다:

```
# Pragmatist Developer

You are a battle-hardened developer with a gift for finding the exact input or sequence of events that makes software blow up in production. You care about bugs that actually happen — not theoretical edge cases that require a PhD to trigger.

## Your Focus Areas

### 1. Bugs & Logic Errors
- Wrong operators: `=` vs `==`, `&` vs `and`, `|` vs `or`
- Off-by-one: `<` vs `<=`, `range(n)` vs `range(n+1)`
- Inverted conditions: `if not error` when `if error` was intended
- Incorrect handling of falsy values: 0, "", [], {}, None are all falsy in Python

### 2. Edge Cases
- Empty inputs: empty list, empty string, zero, null/None
- Single-element collections where multi-element logic is assumed
- Boundary values: first item, last item, maximum value, minimum value
- Unicode / encoding issues in string handling
- Float precision: `0.1 + 0.2 != 0.3`

### 3. Error Handling
- Bare `except:` or `except Exception:` that swallows all errors silently
- Missing `raise` after logging an exception
- Wrong exception type caught (catching `ValueError` when `KeyError` is possible)
- No error handling at I/O boundaries (file not found, network timeout)
- Functions that return `None` on failure but callers assume a value

### 4. Test Coverage Gaps
- Happy path tested but no negative-path tests
- No test for the empty / zero / None input
- Tests that only assert no exception was raised, not that the result is correct
- Hardcoded timestamps or random seeds that make tests non-deterministic

## Review Style
- For every bug: describe the triggering input or state → the wrong behaviour → the correct behaviour.
- Keep it practical: if you're not sure a path is reachable in context, say so but still report it.
- For test gaps: name the exact test case that's missing.

---

## Review Standards

{REVIEW_STANDARDS}

---

## Code to Review

Language: {language}

```{language}
{source_code}
```

## Task
Review this code. Identify at least 3 distinct issues. Include line numbers wherever possible. Do not praise the code.
Set reviewer field to "codex".

## Required Output (ONLY valid JSON, no fences, no prose):
{
  "reviewer": "codex",
  "language": "{language}",
  "summary": "2-3 sentence overall assessment",
  "issues": [
    {
      "id": "R1-001",
      "title": "short one-line title",
      "description": "detailed explanation",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "security | performance | bug | design | test | style",
      "line_start": null,
      "line_end": null,
      "suggestion": "concrete fix"
    }
  ]
}
Minimum 3 issues required.
```

### 도메인 특화 리뷰어 프롬프트 (SPECIALISTS, karechat 전용)

SPECIALISTS의 각 리뷰어(subagent_type: `security-engineer` / `database-engineer` / `breaking-change-detector`)에게 아래 공통 프롬프트를 보냅니다. 이들은 karechat 도메인 지식(PHI/PII·MySQL 8.0·QueryDSL·카카오 i 스킬 응답·하위호환)을 갖고 있으며, **자신의 전문 영역 이슈만** 찾습니다.

```
## Code to Review

Language: {language}

```{language}
{source_code}
```

너의 시스템 프롬프트에 정의된 karechat 전문 영역(보안/DB/Breaking change)에 한정해서만 리뷰하라.
일반 컨벤션·스타일 이슈는 다른 리뷰어가 담당하니 중복 지적하지 말 것.
`~/.claude/rules/java-spring/` 규칙과 충돌 시, 기존 코드의 현행 패턴 유지는 위반으로 보지 않는다.

## Review Standards

{REVIEW_STANDARDS}

## Task
- 전문 영역 이슈를 발견하는 대로 보고 (없으면 확인 내역 1건을 LOW로)
- 가능한 곳마다 line number 포함
- 칭찬 금지 — 문제와 개선점에만 집중
- reviewer 필드를 너의 전문 영역 값으로 설정: security-engineer→"security", database-engineer→"database", breaking-change-detector→"breaking-change"
- security-engineer의 경우 CRITICAL 보안 이슈는 반드시 severity를 CRITICAL로 (R3 보안 거부권 대상)

## Required Output Schema (output ONLY this JSON, no fences):
{
  "reviewer": "security | database | breaking-change",
  "language": "{language}",
  "summary": "2-3 sentence overall assessment (전문 영역 한정)",
  "issues": [
    {
      "id": "R1-001",
      "title": "short one-line title",
      "description": "왜 위험한가 + 영향 범위",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "security | performance | bug | design | test | style",
      "line_start": null,
      "line_end": null,
      "suggestion": "concrete fix or recommendation"
    }
  ]
}
```

**Agent 호출 후:** 기본 3인 결과를 r1_claude, r1_gemini, r1_codex에 저장하고, 활성화된 특화 리뷰어 결과는 r1_specialists 리스트(각 항목에 reviewer 값 포함)에 저장합니다. 이후 라운드에서 R1 이슈 풀 = r1_claude + r1_gemini + r1_codex + r1_specialists 로 취급합니다.

---

## Round 2: 교차 토론 (병렬)

**⚠️ 반드시 단일 메시지에서 Agent 도구를 3번 동시에 호출합니다.**

컨텍스트 압축 규칙:
- 타인 리뷰의 combined JSON 크기가 8,000자 초과 시 각 이슈의 description/suggestion을 200자로 truncate
- R3용은 항상 120자로 압축

R2 교차 토론은 **기본 3인(claude·gemini·codex)만** 수행합니다(특화 리뷰어는 R1 발견 전용). 단, 각 일반 리뷰어는 **다른 2명 + 활성화된 모든 특화 리뷰어의 R1 이슈**를 함께 검토 대상으로 받습니다. 특화 리뷰어의 도메인 이슈(보안·DB·Breaking change)를 일반 리뷰어가 교차 검증하게 하는 것이 목적입니다.

각 에이전트에게: (자신의 R1 리뷰) + (다른 2명 + 특화 리뷰어의 R1 리뷰) + 아래 태스크를 전달합니다.

### Claude Reviewer R2 프롬프트 (subagent_type: claude-reviewer)

```
## Your Own Round 1 Review

{r1_claude — formatted as text, not JSON}

## Other Reviewers' Findings

### GEMINI
{r1_gemini issues — formatted list, compressed if needed}

### CODEX
{r1_codex issues — formatted list, compressed if needed}

### SPECIALISTS (karechat 도메인 — 활성화된 것만)
{r1_specialists issues — reviewer(security/database/breaking-change)와 함께 formatted list, compressed if needed. 없으면 이 섹션 생략}

## Task (Round 2 — Cross-Debate)
For EVERY issue raised by the other reviewers (Gemini, Codex, and any active specialists), state one of:
- AGREE: you fully agree with the issue
- DISAGREE: you disagree and explain why
- PARTIAL: you partially agree and provide your amended version

Also add any issues that NONE of the three reviewers caught yet in missed_issues.

## Required Output (ONLY valid JSON, no fences):
{
  "reviewer": "claude",
  "responses": [
    {
      "issue_id": "R1-001",
      "stance": "AGREE | DISAGREE | PARTIAL",
      "reasoning": "concise reason for your stance",
      "amendment": "optional — provide if PARTIAL or DISAGREE"
    }
  ],
  "missed_issues": [
    {
      "id": "R1-NEW-001",
      "title": "...",
      "description": "...",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "security | performance | bug | design | test | style",
      "line_start": null,
      "line_end": null,
      "suggestion": "..."
    }
  ]
}
```

Gemini reviewer(subagent_type: gemini-reviewer)와 Codex reviewer(subagent_type: codex-reviewer)도 동일한 구조로 프롬프트를 구성합니다. 단, 각 리뷰어는 자신의 R1 리뷰를 own으로, **나머지 일반 리뷰어 2개 + 활성화된 특화 리뷰어 전부**를 others로 받습니다.

**3개 결과 수집:** r2_claude, r2_gemini, r2_codex에 저장합니다.

---

## Round 3: 합의 (Claude 단독, 순차 실행)

r3-moderator 에이전트(subagent_type: r3-moderator)를 단독으로 호출합니다.

프롬프트에 포함할 내용:

```
## Round 1 Reviews (compressed — description/suggestion truncated to 120 chars)

### CLAUDE: {r1_claude.summary[:120]}
{r1_claude issues — compact format: [id][severity/category] title | desc | fix: suggestion}

### GEMINI: {r1_gemini.summary[:120]}
{r1_gemini issues — same compact format}

### CODEX: {r1_codex.summary[:120]}
{r1_codex issues — same compact format}

### SPECIALISTS (karechat — 활성화된 것만): {각 reviewer=security/database/breaking-change}
{r1_specialists issues — same compact format, 각 이슈 앞에 reviewer 표기. security의 CRITICAL은 보안 거부권 후보로 인지. 없으면 생략}

## Round 2 Debates (compressed — reasoning truncated to 120 chars)

### CLAUDE
{r2_claude responses: [issue_id] STANCE: reasoning | amend: amendment}
{r2_claude missed_issues: [NEW][severity] title: description}

### GEMINI
{r2_gemini responses and missed_issues — same format}

### CODEX
{r2_codex responses and missed_issues — same format}

Apply your moderation rules to produce the final consensus.
Remember: security veto overrides majority rule.
Output ONLY the Round3Consensus JSON per your schema.
```

**결과 저장:** r3_consensus에 저장합니다.

---

## 코드 수정 적용 (Claude 직접)

r3_consensus.accepted_issues 목록을 기반으로 원본 코드에 수정을 적용합니다.

Bash 또는 Write 도구를 사용해 수정된 코드를 `/tmp/harness_{run_id}_modified.{ext}` 임시 파일에 저장합니다.

수정 시 지침:
- 합의된 이슈만 수정합니다 (accepted_issues 목록 기준)
- 원본 코드의 전체 구조를 유지합니다
- 수정 외 코드는 변경하지 않습니다
- 수정된 전체 소스 코드를 modified_code 변수에 저장합니다

---

## Round 4: 수정 검증 (병렬)

**⚠️ 반드시 단일 메시지에서 Agent 도구를 3번 동시에 호출합니다.**

각 에이전트에게 전달할 내용:

```
## Accepted Issues to Verify

{r3_consensus.accepted_issues — formatted list:
[issue_id] [severity][SECURITY VETO if applicable] title
  Fix applied: final_suggestion}

## Original Code

```{language}
{original_source_code}
```

## Modified Code

```{language}
{modified_code}
```

## Task (Round 4 — Verification ONLY)
Your ONLY goal is to verify whether each accepted fix was correctly applied and to detect regressions.
- Do NOT search for new issues unrelated to the applied fixes
- Do NOT re-report issues that existed before this round
- A new issue is reportable ONLY if it was directly caused by the edits made
- Assign confidence 0.0 (not fixed) to 1.0 (definitely fixed) for each issue

## Required Output (ONLY valid JSON, no fences):
{
  "reviewer": "claude | gemini | codex",
  "issue_verdicts": [
    {
      "issue_id": "R1-001",
      "resolved": true,
      "confidence": 0.9,
      "note": "brief explanation"
    }
  ],
  "new_issues": [
    {
      "id": "R4-NEW-001",
      "title": "...",
      "description": "...",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "category": "security | performance | bug | design | test | style",
      "line_start": null,
      "line_end": null,
      "suggestion": "..."
    }
  ],
  "overall_verdict": "PASS | PARTIAL | FAIL",
  "summary": "2-3 sentence assessment of the fixed code"
}
```

**결과 저장:** r4_claude, r4_gemini, r4_codex에 저장합니다.

---

## 결과물 저장

Write 도구로 각 라운드 결과를 저장합니다. 저장 전 Bash로 디렉토리를 생성합니다:

```bash
mkdir -p _workspace/01_reviews _workspace/02_debates _workspace/03_consensus \
         _workspace/04_modified _workspace/05_verify _workspace/reports
```

| 경로 | 내용 |
|---|---|
| `_workspace/01_reviews/{run_id}_result.json` | `[r1_claude, r1_gemini, r1_codex, ...r1_specialists]` JSON 배열 (활성화된 특화 리뷰어 포함) |
| `_workspace/02_debates/{run_id}_result.json` | `[r2_claude, r2_gemini, r2_codex]` JSON 배열 |
| `_workspace/03_consensus/{run_id}_result.json` | `r3_consensus` JSON |
| `_workspace/04_modified/{run_id}_modified_code.txt` | 수정된 소스 코드 (plain text) |
| `_workspace/05_verify/{run_id}_result.json` | `[r4_claude, r4_gemini, r4_codex]` JSON 배열 |

---

## 한국어 Markdown 리포트 생성

Write 도구로 `_workspace/reports/{run_id}_report.md` 파일을 직접 작성합니다.
아래 형식을 정확히 따르세요.

### 심각도 배지
- CRITICAL → 🔴
- HIGH → 🟠
- MEDIUM → 🟡
- LOW → 🟢

### 검증 결과 아이콘
- PASS → ✅ 통과
- PARTIAL → ⚠️ 부분 해결
- FAIL → ❌ 미해결

### 리뷰어 표기
- claude → Claude (시니어 아키텍트)
- gemini → Gemini (퍼포먼스 엔지니어)
- codex → Codex (실용주의 개발자)
- security → 🔒 Security Engineer (karechat 보안 특화)
- database → 🗄️ Database Engineer (karechat DB·JPA 특화)
- breaking-change → 📱 Breaking Change Detector (karechat 하위호환 특화)

### 리포트 구조

```markdown
# 코드 리뷰 하네스 리포트

| 항목 | 내용 |
|---|---|
| 실행 ID | `{run_id}` |
| 파일 | `{file_path}` |
| 언어 | `{language}` |
| 생성 시각 | {YYYY-MM-DD HH:MM} |

---

## 📋 요약

- **Round 1** 발견 이슈: **{R1 전체 이슈 합산}개** (일반 3인 + 활성 특화 리뷰어 합산){활성 특화 리뷰어가 있으면 " · 특화: " + 활성 리뷰어 표기 나열}
- **Round 3** 합의: 채택 **{accepted}개** / 기각 **{rejected}개**{보안 거부권이 있으면 " (보안 거부권 적용 **N개**)"}
- **Round 4** 검증: {verdict 분포 — 예: ✅ 통과 2명 / ⚠️ 부분 해결 1명}
  - 신규 발견: **{R4 new_issues 합산}개**

> {r3_consensus.overall_verdict}

---

## 🔍 Round 1 — 독립 리뷰 (병렬)

### {리뷰어 표기}

**종합 평가**: {summary}

**발견 이슈: {n}개**

- {심각도 배지} **[{id}]`L{line_start}` {title}**  
  {description}  
  → *{suggestion}*

(기본 3인 + 활성화된 특화 리뷰어 모두 같은 형식으로 출력. 특화 리뷰어는 "{리뷰어 표기}" 소제목 아래 도메인 이슈만 표시)

---

## 💬 Round 2 — 상호 토론

### {리뷰어 표기}

응답 {n}건 — 동의 **{agree}** / 부분동의 **{partial}** / 반대 **{disagree}**

{missed_issues가 있을 경우}
**추가 발견 ({n}개):**
- {심각도 배지} **{title}**: {description 120자}…

(3명 모두 출력)

---

## ⚖️ Round 3 — 합의 결과

**채택: {n}개** | **기각: {n}개**

#### 🔴 치명적 (CRITICAL)  ← 해당 severity별로 그룹화

**[{issue_id}] {title}**{보안 거부권이면 " 🛡️ *보안 거부권*"}  
- 동의: {agreement_count}/3명  
- 수정 방안: {final_suggestion}  
- 채택 근거: *{rationale}*

(채택 이슈 전체 출력 — CRITICAL→HIGH→MEDIUM→LOW 순)

{기각 이슈가 있을 경우}
### 기각된 이슈

- **{id}**: {rejection_reason}

---

## 🔧 수정된 코드

```{language}
{modified_code}
```

---

## ✅ Round 4 — 검증 결과

### {리뷰어 표기} — {검증 결과 아이콘}

{summary}

**이슈별 해결 여부:**

- {resolved이면 ✅, 아니면 ❌} `{issue_id}` (신뢰도 {confidence*100:.0f}%): {note}

{new_issues가 있을 경우}
**검증 중 신규 발견 ({n}개):**

- {심각도 배지} **[{id}] {title}**  
  {description}  
  → *{suggestion}*

*(해결: {resolved}/{total})*

(3명 모두 출력)

---

## 📌 최종 결론 및 권고사항

{CRITICAL 채택 이슈가 있으면}
### 🔴 즉시 수정 필요 (CRITICAL)
- **{title}**: {final_suggestion}

{HIGH 채택 이슈가 있으면}
### 🟠 머지 전 수정 권고 (HIGH)
- **{title}**: {final_suggestion}

{R4에서 미해결 이슈가 있으면}
### ⚠️ 미해결 이슈 ({n}개)
검증 라운드에서 해결 확인이 안 된 이슈입니다. 추가 수동 검토 권장:
- `{issue_id}`

{R4 new_issues가 있으면}
### 🆕 수정 과정에서 생긴 신규 이슈 ({n}개)
- {심각도 배지} **{title}**: {suggestion}

### 📊 머지 가능 여부

판단 기준:
- 모든 R4가 PASS이고 미해결 없음 → ✅ **머지 가능** — 모든 이슈가 해결되었습니다.
- CRITICAL 미해결 있음 → ❌ **머지 불가** — CRITICAL 이슈가 미해결 상태입니다.
- 그 외 → ⚠️ **조건부 머지 가능** — 미해결 이슈를 수동으로 확인한 후 머지하세요.
```

---

## 최종 콘솔 출력

리포트 저장 후 다음 요약을 출력합니다:

```
================================================================
Run ID   : {run_id}
Language : {language}

Round 1  : {total}개 이슈 발견 (일반 3인 + 특화 리뷰어 합산)
  특화   : {활성 특화 리뷰어 나열 — 없으면 "없음"}

Consensus: {overall_verdict}
  채택   : {n}개
  기각   : {n}개

  [CRITICAL] {title} ...
  [HIGH]     {title} ...

Verification:
  claude  {PASS|PARTIAL|FAIL}  resolved={n}/{total}  new={n}
  gemini  {PASS|PARTIAL|FAIL}  resolved={n}/{total}  new={n}
  codex   {PASS|PARTIAL|FAIL}  resolved={n}/{total}  new={n}
  → {pass_count}/3 reviewers gave PASS

리포트: _workspace/reports/{run_id}_report.md
================================================================
```
