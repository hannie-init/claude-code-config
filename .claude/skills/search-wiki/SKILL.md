---
name: search-wiki
description: ~/karechat-knowledge/wiki/ 에서 키워드·주제로 정제된 지식을 검색해 출처와 함께 답한다. 트리거: "wiki 검색", "위키에서 찾아줘", "wiki에 ~ 있어?", "~에 대해 wiki에서 알려줘", "지식 검색해줘".
---

# search-wiki

`~/karechat-knowledge/wiki/` 하위의 정제된 지식을 **읽기 전용**으로 검색해 사용자 질문에 출처와 함께 답한다.
수집(`add-source`) → 정제(`update-knowledge`) 파이프라인의 마지막 소비(검색) 단계를 담당한다.

## 기본 경로

검색 대상은 `~/karechat-knowledge/wiki/` 하위 전체다.

| 디렉토리 | 다루는 주제 |
|----------|------------|
| `wiki/features/` | 담당 기능 상세, 비즈니스 로직, 플로우, QA |
| `wiki/api/` | API 스펙, 요청/응답 형식, 연동 정보 |
| `wiki/architecture/` | 시스템 구조, 컴포넌트 관계, 데이터 흐름 |
| `wiki/development/` | GCP, Git, Spring, Java, 인프라, 개발 환경 |
| `wiki/hospital/` | 병원 세팅·관리 관련 지식 |

`sources/`, `CHANGELOG.md`, `templates/` 는 검색 범위에서 **제외**한다 (정제된 wiki만 대상).

## 검색 흐름

Grep / Glob / Read 도구만 사용한다.

1. **질의 파싱** — 사용자 질문에서 핵심 키워드를 추출한다. 한국어·영문 표기와 약어를 함께 고려한다 (예: `hsp_policy` ↔ "병원 정책", "정책 데이터"). `$ARGUMENTS`가 있으면 그것을 질의로 사용한다.
2. **1차 탐색** — `Glob`으로 `~/karechat-knowledge/wiki/**/*.md` 목록을 확보한 뒤, `Grep`(`-i`, output_mode `files_with_matches`)으로 키워드 매칭 파일을 찾는다. 매칭 파일에 대해 `content` 모드로 다시 검색해 매칭 위치를 본다.
3. **랭킹** — 제목(`#`)·`## Overview`·`## Key Concepts` 매칭을 본문 매칭보다 우선한다. 매칭 파일이 0건이면 키워드를 완화(동의어·상위어)해 재시도한다.
4. **정독** — 상위 후보 파일을 `Read`로 읽어 질문에 직접 답하는 섹션(특히 `Key Concepts`, `Decisions`)을 확인한다.
5. **답변 합성** — 핵심 답을 먼저 제시하고, 근거를 파일 경로·섹션명과 함께 인용한다. `Related Wiki Pages` 링크를 따라 연관 문서도 안내한다.

## 출력 형식

- **답변**: 질문에 대한 직접적인 결론 (한국어).
- **근거**: `wiki/<범주>/<파일>.md › 섹션명` 형식의 출처 목록.
- **관련 문서**: `Related Wiki Pages` 기반 추가 참고 링크.
- **미확인**: 해당 문서의 `Open Questions`에 걸려 있거나 wiki에 없는 내용은 추측하지 말고 "wiki에 없음/미확정"으로 명시.

## 주의사항

- **읽기 전용** — wiki/sources 어떤 파일도 수정·생성하지 않는다. 기록·반영은 `add-source` / `update-knowledge` 담당이다.
- wiki에 없는 내용을 지어내지 않는다. 없으면 "wiki에 기록 없음"이라 답하고, 필요 시 `/add-source` → `/update-knowledge`로 기록을 제안한다.
- `> **Inference:**` 로 표시된 내용은 추론임을 밝혀 인용하고, `Open Questions` 항목은 미확정으로 안내한다.
- 검색 범위는 `wiki/` 하위만이다. sources/, CHANGELOG.md, templates/ 는 제외한다.

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-18 | 스킬 신규 생성 |
