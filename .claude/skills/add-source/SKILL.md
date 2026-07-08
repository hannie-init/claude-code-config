---
name: add-source
description: 사용자가 자유롭게 말한 내용을 sources/ 아래 구조화된 마크다운 파일로 정리해서 저장한다. 트리거: "기록해줘", "메모해줘", "노트로 남겨줘", 회의·장애·아티클 내용을 sources에 저장하고 싶을 때.
---

# add-source

사용자 입력을 `templates/source-template.md` 구조에 맞게 정리해 sources/ 에 저장한다.

## 기본 경로

모든 파일은 `~/karechat-knowledge/` 아래에 저장한다.
- sources: `~/karechat-knowledge/sources/<카테고리>/`
- templates: `~/karechat-knowledge/templates/source-template.md`

## 카테고리 분류

| 폴더 | 대상 |
|------|------|
| `sources/notes/` | 개인 메모, 생각 정리, 학습 내용 |
| `sources/meetings/` | 회의록, 미팅 요약 |
| `sources/articles/` | 외부 아티클, 문서 요약 |
| `sources/incidents/` | 장애, 이슈, 트러블슈팅 |

`$ARGUMENTS`로 카테고리가 명시된 경우 우선 적용한다.

## 실행 흐름

1. **인터뷰** — 핵심 내용이 이미 있으면 재질문하지 않는다. 날짜·출처·태그가 없을 때만 최소한으로 묻는다.
2. **파일명 결정** — `YYYY-MM-DD-주제요약.md` (kebab-case, 3~5 단어). 날짜 없으면 오늘 날짜 사용.
3. **파일 생성** — 처리 상태는 항상 `미처리`. 추론이 필요한 내용은 `(추정) ...` 형식으로 `## 메모`에만 기록.
4. **중복 확인** — 같은 날짜·주제 파일이 있으면 덮어쓰지 않고 사용자에게 확인한다.
5. **결과 보고** — 저장 경로와 핵심 내용을 한 줄로 알린다.

## 주의사항

- sources 파일은 사용자가 말하지 않은 내용을 추가하지 않는다.
- `처리 상태`는 항상 `미처리`로 설정한다. wiki 반영은 `update-knowledge` 스킬이 담당한다.

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-09 | 변경 이력 섹션 추가 |
