---
name: figma-web-compare
model: opus
description: >
  Figma 선택 노드와 Chrome에 열린 웹페이지의 텍스트를 자동 비교한다.
  Chrome을 --remote-debugging-port=9222로 실행하고 대상 페이지를 열어두면
  Figma Desktop MCP + Playwright CDP로 텍스트를 각각 추출해
  오탈자·내용 차이를 표 형식으로 리포트한다.
  트리거: "figma 비교", "텍스트 비교해줘", "디자인 확인해줘", "/figma-web-compare"
---

## 개요

- **Figma 텍스트**: `mcp__figma-desktop__get_design_context` 로 추출
- **웹 텍스트**: `scripts/capture_page.py` 가 Chrome CDP에 연결해 `page.inner_text('body')` 로 추출
- Claude가 두 텍스트를 시맨틱 diff하여 차이점을 리포트

## 사전 조건

### 초기 설치 (최초 1회)
```bash
bash ~/.claude/skills/figma-web-compare/scripts/setup.sh
```

### Chrome 디버그 모드 실행 (비교 전 매번)

> ⚠️ **Chrome 136 버전부터 보안상 기본 프로필(default profile)에서는 `--remote-debugging-port`가 무시된다.**
> Chrome은 실행되지만 9222 포트를 절대 바인딩하지 않는다. 반드시 별도 `--user-data-dir`을 지정해야 한다.
> 또한 `open -a` 방식은 최신 Chrome에서 플래그 전달이 불안정하므로 **바이너리를 직접 실행**한다.

```bash
pkill -9 "Google Chrome"; sleep 1
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  "--remote-allow-origins=*" \
  --user-data-dir="$HOME/chrome-debug-profile" &
```

> **zsh 주의**: `--remote-allow-origins=*` 의 `*` 는 zsh가 glob으로 해석하므로 반드시 따옴표로 감싼다.
> **별도 프로필 주의**: `--user-data-dir` 는 기존 로그인 세션이 없는 새 프로필이다. 비교할 사이트에 **다시 로그인**해야 한다.
> 단, 같은 디렉토리(`chrome-debug-profile`)를 계속 재사용하면 로그인이 유지되어 다음부터는 재로그인 불필요하다.

alias 등록 권장 (`~/.zshrc`):
```bash
alias chrome-debug='/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 "--remote-allow-origins=*" --user-data-dir="$HOME/chrome-debug-profile" &'
```

실행 후 연결 확인:
```bash
curl -s http://localhost:9222/json
```

그 후 비교할 페이지를 열고 (필요시 로그인) Step 1 진행

## 워크플로우

### Step 1 — Chrome 연결 및 텍스트 추출

```bash
python ~/.claude/skills/figma-web-compare/scripts/capture_page.py \
  [--port 9222] \
  [--output /tmp/figma_compare_content.json] \
  [--page-url <URL에_포함된_패턴>]
```

- **성공**: stdout에 `{"success": true, "url": ..., "title": ..., "available_pages": N}` 출력
- **연결 실패**: 에러 메시지와 함께 Chrome 재시작 안내 출력 → 사용자에게 안내 후 중단
- `--page-url` 생략 시 가장 최근에 열린 탭 자동 선택

### Step 2 — Figma 텍스트 추출

`mcp__figma-desktop__get_design_context` 호출 (nodeId 미전달 시 현재 선택 노드 자동 사용)

응답 코드에서 모든 텍스트 노드(`<p>`, `<span>` 등) 내용 수집

### Step 3 — 텍스트 비교

`/tmp/figma_compare_content.json` 파일의 `text_content` 필드와 Figma 텍스트를 비교:

- 항목별로 매칭 (번호, 제목, 본문 순서 기준)
- 오탈자, 누락 문장, 추가 문장, 기호/부호 차이 모두 검출
- 공백·줄바꿈 차이는 무시, 실질적 텍스트 내용 차이만 리포트

#### 동적 데이터 처리 (필수)

데이터 바인딩 영역(환자명, 금액, 병실명, 날짜 등)은 **오탈자/내용 차이와 반드시 분리**해서 리포트한다. `❌ 차이 발견` 표에 섞지 않는다.

- **동적 데이터 판별 기준**: Figma 쪽이 플레이스홀더 형태(`홍길동`, `{1인실}`, `nnn,nnn`, `nnn,nnn (원/일)`, `YYYY.MM.DD` 등 더미 값)이고, 웹은 실제 값(`1,080,000원`, 빈칸 등)인 경우
- 이런 항목은 `⚠️ 동적 데이터 (실제 값 vs 플레이스홀더 — 오류 아님)` 섹션에 별도 표로 정리
- 단, **노출 포맷 자체가 다르면**(예: `nnn,nnn (원/일)` ↔ `1,080,000원`처럼 단위·표기 형식 불일치) 해당 행에 "포맷 확인 권장" 메모를 남긴다
- 스크롤 상태/접근성 요소(`아래로 스크롤` ↔ `동의 후 제출`, `본문 바로가기` 등)도 오류가 아니므로 `ℹ️ 상태/스크롤 차이` 섹션으로 분리

### Step 4 — 리포트 출력

```
## Figma ↔ 웹 비교 결과

**페이지**: {url}
**Figma 노드**: {nodeId} / {name}
**비교 시각**: {datetime}

### ❌ 차이 발견 ({n}건)
| # | 위치 | Figma 내용 | 웹 내용 |
|---|------|-----------|--------|
| 1 | 약정 내용 8번 번호 | `8.` | `8` |
| 2 | 6번 인용부호 | `⌜보증인...⌟` | `「보증인...」` |

### ⚠️ 동적 데이터 (실제 값 vs 플레이스홀더 — 오류 아님)
| 위치 | Figma (디자인 예시) | 웹 (실제 데이터) |
|------|------|--------|
| 상급병실차액 | `nnn,nnn (원/일)` | `1,080,000원` (포맷 확인 권장) |

### ℹ️ 상태/스크롤 차이 (콘텐츠 오류 아님)
- 하단 버튼: Figma `동의 후 제출` ↔ 웹 `아래로 스크롤` (스크롤 상태 차이)

### ✅ 일치 항목
차이 없음 (또는 주요 섹션 요약)
```

## 명령어 형식

```
/figma-web-compare [nodeId] [--port 9222] [--page-url <패턴>]
```

| 인수 | 기본값 | 설명 |
|------|--------|------|
| `nodeId` | 현재 Figma 선택 노드 | 비교할 Figma 프레임 ID (예: `25295:82666`) |
| `--port` | `9222` | Chrome remote debugging port |
| `--page-url` | (없음, 마지막 탭) | URL 패턴으로 탭 특정 |

## 오류 대응

| 오류 | 원인 | 해결 |
|------|------|------|
| `Chrome에 연결할 수 없습니다` (포트 안 열림) | Chrome 136+ 기본 프로필은 디버그 포트 무시 | `--user-data-dir` 지정해 바이너리 직접 실행 |
| `403 Forbidden` | `--remote-allow-origins` 미설정 | Chrome을 `"--remote-allow-origins=*"` 플래그로 재시작 (스크립트는 `suppress_origin`으로 우회) |
| `no matches found: --remote-allow-origins=*` | zsh가 `*`를 glob으로 해석 | 플래그를 따옴표로 감싸기 |
| `playwright 패키지가 설치되지 않았습니다` | 초기 설치 미완료 | `setup.sh` 실행 |
| `열린 탭이 없습니다` | Chrome 열었지만 탭이 없음 | 비교할 페이지 탭 열기 |
| `URL에 '...'이 포함된 탭을 찾을 수 없습니다` | `--page-url` 패턴 불일치 | 탭 목록 확인 후 패턴 수정 |

## 주의사항

- `capture_page.py` 는 Playwright 연결을 끊을 뿐 Chrome 프로세스를 종료하지 않음 (안전)
- User-Agent 설정은 Chrome 재시작 후 DevTools에서 다시 설정 필요
- Figma Desktop 앱이 열려 있고 해당 파일이 활성화된 상태여야 MCP 호출 가능

## 변경 이력

- 2026-06-11: 동적 데이터 처리 규칙 추가 — 데이터 바인딩 영역(환자명·금액·병실명 등)은 `⚠️ 동적 데이터` 섹션, 스크롤/접근성 차이는 `ℹ️ 상태/스크롤 차이` 섹션으로 분리해 `❌ 차이 발견`과 섞지 않도록 명시
- 2026-06-11: frontmatter에 `model: opus` 추가 — 스킬 실행 시 Opus 모델 사용 명시
- 2026-06-11: Chrome 136+ 기본 프로필 디버그 포트 무시 이슈 대응 — `--user-data-dir` 지정 + 바이너리 직접 실행 방식으로 변경, zsh glob 따옴표 안내 추가, `capture_page.py`에 `suppress_origin=True` 적용(403 우회), 오류 표 보강
- 2026-06-11: `finally` 문법 오류 수정, `--remote-allow-origins=*` 플래그 추가, 403 에러 힌트 개선
- 2026-06-10: 최초 생성 — Figma Desktop MCP + Chrome CDP 텍스트 비교 스킬
