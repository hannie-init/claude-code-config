#!/bin/zsh
# 매일 실행: transcript 수집(순수 Python, LLM 없음, 비용 0)
set -euo pipefail
DATA="$HOME/.claude/harness-tuner-data"
LOG="$DATA/logs/collect-$(date +%F).log"
mkdir -p "$DATA/logs"
{
  echo "===== collect $(date '+%F %T') ====="
  /usr/bin/python3 "$HOME/.claude/skills/harness-tuner/extract.py"
} >> "$LOG" 2>&1
