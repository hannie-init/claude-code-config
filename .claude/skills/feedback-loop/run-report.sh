#!/bin/zsh
# 주 1회 실행: 수집 후 feedback-loop 분석기(Claude)로 주간 리포트 생성
# 헤드리스 claude 는 cmux shim 이 아닌 영구 바이너리를 써야 한다.
set -euo pipefail
DATA="$HOME/.claude/feedback-loop-data"
LOG="$DATA/logs/report-$(date +%F).log"
mkdir -p "$DATA/logs"

CLAUDE_BIN="/opt/homebrew/bin/claude"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$(command -v claude || true)"

{
  echo "===== report $(date '+%F %T') ====="
  echo "claude: $CLAUDE_BIN"
  # 1) 수집
  /usr/bin/python3 "$HOME/.claude/skills/feedback-loop/extract.py"
  # 2) 분석기 실행 (리포트만 생성, 설정/스킬/메모리 미변경)
  "$CLAUDE_BIN" -p "/feedback-loop" \
    --permission-mode acceptEdits \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep"
} >> "$LOG" 2>&1
