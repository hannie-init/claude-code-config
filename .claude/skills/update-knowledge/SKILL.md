---
name: update-knowledge
description: sources/ 폴더에서 미처리 파일을 읽어 wiki를 생성하거나 갱신한다. 트리거: "wiki 업데이트해줘", "지식 반영해줘", "sources 처리해줘", 특정 파일을 wiki에 반영하고 싶을 때.
---

# update-knowledge

sources/ 파일을 읽고 wiki/ 문서를 생성하거나 병합(merge)한다. 덮어쓰지 않는다.

## 기본 경로

모든 파일은 `~/karechat-knowledge/` 아래에서 읽고 쓴다.
- sources: `~/karechat-knowledge/sources/`
- wiki: `~/karechat-knowledge/wiki/`
- templates: `~/karechat-knowledge/templates/`
- CHANGELOG: `~/karechat-knowledge/CHANGELOG.md`

## 처리 대상 결정

- `$ARGUMENTS`가 있으면 해당 파일만 처리한다.
- 없으면 sources/ 전체에서 `처리 상태: 미처리`인 파일을 날짜 최신 순으로 처리한다.

## wiki 범주

| 디렉토리 | 대상 |
|----------|------|
| `wiki/features/` | 담당 기능 상세, 비즈니스 로직, 플로우, QA |
| `wiki/api/` | API 스펙, 요청/응답 형식, 연동 정보 |
| `wiki/architecture/` | 시스템 구조, 컴포넌트 관계, 데이터 흐름 |
| `wiki/development/` | GCP, Git, Spring, Java, 인프라, 개발 환경 |

## 실행 흐름

1. **추출** — 핵심 사실, 결정사항, TODO, Open Questions 후보를 식별한다.
2. **매핑** — 위 범주 중 가장 적합한 wiki 경로를 결정한다.
3. **wiki 갱신**
   - 기존 파일 있음 → 읽고 내용 병합. 덮어쓰기 금지.
   - 기존 파일 없음 → `templates/wiki-page-template.md` 구조로 신규 생성.
4. **표기 규칙**
   - 추론·유추한 내용: `> **Inference:** ...`
   - 불확실한 내용: `Open Questions` 섹션에 추가.
   - `Related Sources`에 참조 파일 링크.
   - `Last Updated`를 오늘 날짜로 갱신.
5. **CHANGELOG 기록** — `CHANGELOG.md` 최상단에 날짜·변경 파일·변경 유형·한 줄 요약·참조 sources 추가.
6. **결과 보고** — 처리한 파일 목록과 변경 내용을 요약한다.

## 주의사항

- sources 파일은 절대 수정하지 않는다.
- wiki 섹션 순서(Overview → Key Concepts → Decisions → Open Questions → Related Sources → Related Wiki Pages → Last Updated)를 유지한다.

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-09 | 변경 이력 섹션 추가 |
