---
name: feedback-loop
description: Claude Code 세션 transcript에서 마찰 신호(정정·거부된 툴 호출·툴 에러·반복 수작업)를 분석해 주간 "하네스 개선 리포트 + 승인 대기 제안"을 만든다. 스킬/설정/규칙/메모리 업그레이드를 제안만 하고 직접 수정하지 않는다. 트리거: "/feedback-loop", "하네스 튜닝", "세션 회고", "마찰 리포트", "주간 개선 리포트", "피드백 루프". launchd가 주 1회 자동 실행하기도 한다.
---

# feedback-loop

Claude Code 세션 transcript를 분석해 **매주 마찰 리포트 + 개선 제안**을 만든다.
목표: 마찰↓ → 세션 품질↑ → 다음 마찰↓ 의 복리 플라이휠.

## 절대 규칙 (하드 바운더리)

- **직접 수정 금지**: `~/.claude/settings.json`, `CLAUDE.md`, `~/.claude/rules/**`, 스킬 파일, `memory/**` 를 **절대 편집하지 않는다.** 이 스킬은 **제안(리포트)만** 만든다. 적용은 사용자가 리포트를 읽고 승인한 뒤 별도로 한다.
- **쓰기 허용 위치**: `~/.claude/feedback-loop-data/reports/` 와 `~/.claude/feedback-loop-data/staging/` 뿐.
- wiki(`~/karechat-knowledge/`)에 쓰지 않는다.
- 시크릿/PII는 리포트에 옮기지 않는다(extract.py가 1차 마스킹하지만, 눈에 띄면 제외).
- 권한 프롬프트(allowlist) 정리는 **직접 하지 말고** 기존 `/fewer-permission-prompts` 스킬 실행을 리포트에서 권장한다(중복 구현 금지).

## 경로

```
스킬:   ~/.claude/skills/feedback-loop/{SKILL.md, extract.py, run-collect.sh, run-report.sh}
데이터: ~/.claude/feedback-loop-data/{state.json, staging/<날짜>/, reports/, logs/}
리포트: ~/.claude/feedback-loop-data/reports/<YYYY-MM-DD>-feedback.md
```

## 실행 흐름

### 1. 수집 + 리포트 범위 파악
```bash
python3 ~/.claude/skills/feedback-loop/extract.py            # 신규 대화 수집(멱등)
python3 ~/.claude/skills/feedback-loop/extract.py --report-plan   # 리포트 범위 JSON
```
`--report-plan` 출력:
- `since` — 마지막 리포트 이후 시점
- `signal_totals` / `total_signals` — 구조적 신호 집계(하드 증거)
- `top_sessions` — 신호 많은 순 상위 세션(딥리드 후보, 파일 경로 포함)
- `all_staged_files` / `signals_files` — 전체 목록

신규 대화도 신호도 없으면 "이번 주 새 마찰 없음"을 보고하고 종료한다.

### 2. 증거 읽기 (토큰 상한 지키기)
- 먼저 `signals_files`의 `signals.json`을 모두 읽어 **하드 증거**를 확보한다(값싸다).
- 그다음 `top_sessions`의 파일만 딥리드한다. **최대 15개**. 초과분은 리포트에 "N개 세션 미열람(절단)"으로 명시한다.
- 신호 타입:
  - `tool_reject` — Claude가 시도했다 사용자가 거부한 것 + 리다이렉트 사유. **가장 강한 신호.**
  - `tool_error` / `input_validation` — 툴 실패/스키마 오류.
  - `skill_invoke` — 스킬 사용 흔적(성공/실패는 주변 맥락으로 판단).
- 의미적 신호는 대화 본문에서 직접 판단: 정정/부정("아니", "그게 아니라", "다시", "말고", "왜 ~했어"), 반복 수작업, "앞으로/항상/하지마/기억해" 류 작업지시.

### 3. 차원별 집계
마찰을 아래 6개 차원으로 묶고, 각 항목에 **빈도 + 증거(세션ID 앞 8자 + 짧은 발췌)** 를 단다.
1. **반복 정정/오해** — 같은 종류의 정정이 반복되는가.
2. **스킬 실패/오작동** — 특정 스킬이 자주 실패/우회되는가.
3. **반복 수작업** — 매번 손으로 반복하는 멀티스텝 → 신규 스킬 후보.
4. **규칙 공백** — `CLAUDE.md`/`rules/*.md`에 명문화되지 않아 반복 지적되는 규칙.
5. **툴 에러 패턴** — 반복되는 툴/커맨드 실패의 근본 원인.
6. **피드백→메모리 후보** — 세션 중 준 작업지시 중 `memory/feedback_*.md`에 없는 것.
- **권한**은 요약만 하고 "`/fewer-permission-prompts` 실행 권장"으로 위임한다.
- 기존 `~/.claude/projects/-Users-hannie-init/memory/feedback_*.md`를 **읽어** 이미 반영된 피드백은 후보에서 제외(중복 방지).

### 4. 리포트 작성
`~/.claude/feedback-loop-data/reports/<오늘YYYY-MM-DD>-feedback.md` 를 생성한다. 구조:

```markdown
# 하네스 개선 리포트 — <기간 since ~ 오늘>

## 요약
- 분석 세션 N개(딥리드 M개), 신호 {tool_reject, tool_error, ...}
- 이번 주 상위 마찰 3~5개 (한 줄씩)

## 마찰 상세
### [차원] 제목
- 증상 / 빈도 / 증거: `세션8자` — "발췌" / 추정 원인

## 제안 (승인 대기)
### 제안 #1 — [유형: 스킬수정|신규스킬|CLAUDE.md/rules|hook|권한|메모리]
- 대상: `파일 경로`
- 제안 내용: (가능하면 before/after diff 또는 추가할 문구 전문)
- 근거: 어떤 마찰을 없애는가 (위 증거 참조)
- 리스크: 
- 적용 방법: (승인 시) 예) `/update-config` 로 allowlist 추가 / 해당 SKILL.md 수정 / memory 파일 생성

## 피드백 → 메모리 후보
- (기존 feedback_*.md에 없는 것만) 제안 파일명 + 내용 초안

## 미열람 세션 (절단)
- (상위 15개 초과분이 있으면 목록)
```

제안은 **구체적**이어야 한다: "리뷰를 개선하라"(X) → "`rules/java-spring/testing.md`에 '경계값 필수 케이스' 예시 추가, 근거: 세션 abc12345에서 동일 지적 3회"(O).

### 5. 마무리
```bash
python3 ~/.claude/skills/feedback-loop/extract.py --mark-report
```
사용자에게 **리포트 경로**와 **상위 제안 3개**를 한국어로 요약 보고한다. 설정/스킬/메모리는 건드리지 않았음을 명시한다.

## 주의

- 자동(launchd) 실행이든 수동이든 동일하게 동작한다.
- 대화 데이터가 방대할 수 있으니 top_sessions 딥리드 상한(15)을 지켜 토큰을 관리한다.
- 제안은 사용자가 승인·적용하는 것이지 이 스킬이 적용하지 않는다.

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-07-01 | 최초 작성. extract.py 기반 주간 마찰 리포트 + 승인 대기 제안. |
| 2026-07-09 | 스킬명 `harness-tuner` → `feedback-loop` 변경. 폴더·데이터 디렉토리(`feedback-loop-data`)·스크립트·plist(launchd)·트리거(`/feedback-loop`)·메모리 일괄 반영. 리포트 파일명 규칙도 `<날짜>-harness.md` → `<날짜>-feedback.md`로 변경. |
