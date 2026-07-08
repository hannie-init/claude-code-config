#!/usr/bin/env bash
# Claude Config Sync Script
# Syncs skills and agents between ~/claude-code-config/.claude/ and ~/.claude/
#
# Usage:
#   sync.sh --from-git   : git repo -> ~/.claude (git is source of truth)
#   sync.sh --to-git     : ~/.claude -> git repo (local is source of truth)
#   sync.sh --status     : show differences without syncing

set -euo pipefail

GIT_DIR="$HOME/claude-code-config/.claude"
LIVE_DIR="$HOME/.claude"
TARGETS=("skills" "agents")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_status() {
    echo -e "${BLUE}=== Claude Config Sync Status ===${NC}"
    local has_diff=0

    for target in "${TARGETS[@]}"; do
        local git_path="$GIT_DIR/$target"
        local live_path="$LIVE_DIR/$target"

        echo ""
        echo -e "${YELLOW}[$target]${NC}"

        if [ ! -d "$git_path" ]; then
            echo -e "  ${RED}Git 경로 없음:${NC} $git_path"
            continue
        fi
        if [ ! -d "$live_path" ]; then
            echo -e "  ${RED}Live 경로 없음:${NC} $live_path"
            continue
        fi

        local only_in_git=()
        local only_in_live=()
        local both=()

        while IFS= read -r item; do
            name=$(basename "$item")
            if [ -e "$live_path/$name" ]; then
                both+=("$name")
            else
                only_in_git+=("$name")
            fi
        done < <(find "$git_path" -maxdepth 1 -mindepth 1 2>/dev/null)

        while IFS= read -r item; do
            name=$(basename "$item")
            if [ ! -e "$git_path/$name" ]; then
                only_in_live+=("$name")
            fi
        done < <(find "$live_path" -maxdepth 1 -mindepth 1 2>/dev/null)

        if [ ${#only_in_git[@]} -gt 0 ]; then
            echo -e "  ${GREEN}Git에만 있음 (live에 없음):${NC}"
            for item in "${only_in_git[@]}"; do
                echo "    + $item"
            done
            has_diff=1
        fi

        if [ ${#only_in_live[@]} -gt 0 ]; then
            echo -e "  ${RED}Live에만 있음 (git에 없음):${NC}"
            for item in "${only_in_live[@]}"; do
                echo "    - $item"
            done
            has_diff=1
        fi

        if [ ${#both[@]} -gt 0 ]; then
            echo -e "  ${BLUE}공통 항목:${NC}"
            for item in "${both[@]}"; do
                echo "    = $item"
            done
        fi
    done

    echo ""
    if [ $has_diff -eq 0 ]; then
        echo -e "${GREEN}두 위치가 동기화되어 있습니다.${NC}"
    else
        echo -e "${YELLOW}동기화가 필요합니다. --from-git 또는 --to-git 옵션을 사용하세요.${NC}"
    fi
}

sync_from_git() {
    echo -e "${BLUE}=== Git → Live 동기화 ===${NC}"
    echo -e "출처: ${GIT_DIR}"
    echo -e "대상: ${LIVE_DIR}"
    echo ""

    for target in "${TARGETS[@]}"; do
        local git_path="$GIT_DIR/$target"
        local live_path="$LIVE_DIR/$target"

        echo -e "${YELLOW}[$target] 동기화 중...${NC}"

        if [ ! -d "$git_path" ]; then
            echo -e "  ${RED}건너뜀: $git_path 없음${NC}"
            continue
        fi

        mkdir -p "$live_path"
        rsync -av --update "$git_path/" "$live_path/" 2>&1 | sed 's/^/  /'
        echo -e "  ${GREEN}완료${NC}"
    done

    echo ""
    echo -e "${GREEN}Git → Live 동기화 완료!${NC}"
    echo -e "${YELLOW}참고: Live에만 있는 항목은 유지됩니다. --status로 확인하세요.${NC}"
}

sync_to_git() {
    echo -e "${BLUE}=== Live → Git 동기화 ===${NC}"
    echo -e "출처: ${LIVE_DIR}"
    echo -e "대상: ${GIT_DIR}"
    echo ""

    for target in "${TARGETS[@]}"; do
        local git_path="$GIT_DIR/$target"
        local live_path="$LIVE_DIR/$target"

        echo -e "${YELLOW}[$target] 동기화 중...${NC}"

        if [ ! -d "$live_path" ]; then
            echo -e "  ${RED}건너뜀: $live_path 없음${NC}"
            continue
        fi

        mkdir -p "$git_path"
        rsync -av --update --exclude='.git/' "$live_path/" "$git_path/" 2>&1 | sed 's/^/  /'
        echo -e "  ${GREEN}완료${NC}"
    done

    echo ""
    echo -e "${GREEN}Live → Git 동기화 완료!${NC}"
    echo -e "${YELLOW}참고: Git 레포에서 커밋을 잊지 마세요: cd ~/claude-code-config && git add -A && git commit${NC}"
}

case "${1:-}" in
    --from-git)
        sync_from_git
        ;;
    --to-git)
        sync_to_git
        ;;
    --status)
        show_status
        ;;
    *)
        echo "Usage: sync.sh [--from-git | --to-git | --status]"
        echo ""
        echo "  --from-git  : git repo → ~/.claude/ 동기화"
        echo "  --to-git    : ~/.claude/ → git repo 동기화"
        echo "  --status    : 차이점 확인 (변경 없음)"
        exit 1
        ;;
esac
