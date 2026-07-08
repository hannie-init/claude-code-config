---
name: sync-claude-config
description: |
  ~/claude-code-config/.claude/ (git 관리)와 ~/.claude/ (Claude 실제 사용 경로) 사이의
  skills와 agents 파일을 동기화한다.
  트리거 키워드: 'config 동기화', 'skill 동기화', 'agent 동기화', 'sync claude config',
  'git과 로컬 동기화', 'claude 설정 동기화', '.claude 동기화'
---

# Claude Config 동기화

## 개요

두 경로 사이의 skills/agents를 동기화한다.

| 경로 | 설명 |
|---|---|
| `~/claude-code-config/.claude/` | Git으로 관리하는 원본 |
| `~/.claude/` | Claude Code가 실제로 읽는 경로 |

## 동기화 방향 선택

사용자가 명시하지 않으면 어느 방향으로 동기화할지 먼저 물어본다.

- **git → live** (`--from-git`): git 레포 내용을 `~/.claude/`에 반영. git pull 후 사용.
- **live → git** (`--to-git`): `~/.claude/`에서 직접 수정한 내용을 git 레포에 반영. 커밋 전 사용.

## 사용법

```bash
# 차이점 확인 (변경 없음)
bash ~/.claude/skills/sync-claude-config/scripts/sync.sh --status

# git → ~/.claude/ 동기화
bash ~/.claude/skills/sync-claude-config/scripts/sync.sh --from-git

# ~/.claude/ → git 동기화
bash ~/.claude/skills/sync-claude-config/scripts/sync.sh --to-git
```

## 워크플로우

### git에서 수정 후 live 반영
```
git pull (또는 git 레포에서 직접 편집)
→ sync.sh --status 로 차이 확인
→ sync.sh --from-git 으로 ~/.claude/에 반영
```

### live에서 수정 후 git 반영
```
~/.claude/skills 또는 ~/.claude/agents 직접 편집
→ sync.sh --to-git 으로 git 레포에 반영
→ cd ~/claude-code-config && git add -A && git commit
```

## 주의사항

- 동기화 시 상대방에만 있는 파일은 삭제하지 않음 (안전 우선)
- `--to-git` 후 반드시 git commit 필요
- `.git/` 디렉토리는 동기화에서 제외됨
- 이 스킬 자체는 git에 포함하지 않음 (`~/.claude/`에만 위치)

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-09 | 변경 이력 섹션 추가 |
