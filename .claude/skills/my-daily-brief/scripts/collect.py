#!/usr/bin/env python3
"""로컬 Claude Code transcript(~/.claude/projects/*/*.jsonl)에서 특정 날짜(기본: 어제)에
한 작업의 원시 데이터를 추출한다. 요약(LLM)은 하지 않는다 — SKILL.md(Claude)가 담당.

추출 내용
  - 프로젝트(cwd)별 세션: 제목(ai-title), 시작/종료 시각(KST), 사용자 프롬프트 목록
  - 프로젝트가 git repo면 그날의 커밋 로그

원칙
  - 읽기 전용. transcript/repo를 수정하지 않는다.
  - 시크릿 마스킹 후 출력. 턴당 글자수 절단으로 토큰 폭발 방지.
  - 요청 날짜에 데이터가 없으면 그 이전 가장 최근 날짜로 폴백(fallback=true 표시).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

HOME = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(HOME, ".claude", "projects")

KST = timezone(timedelta(hours=9))
FALLBACK_DAYS = 14        # 요청일에 데이터 없을 때 거슬러 올라가는 최대 일수
PER_PROMPT_CHARS = 400    # 프롬프트당 절단
MAX_PROMPTS_PER_SESSION = 40

# 시크릿 마스킹 (feedback-loop/extract.py 패턴 재사용)
SECRET_RES = [
    re.compile(r'(sk-[A-Za-z0-9]{8,})'),
    re.compile(r'(ghp_[A-Za-z0-9]{20,})'),
    re.compile(r'(xox[baprs]-[A-Za-z0-9-]{10,})'),
    re.compile(r'(AKIA[0-9A-Z]{12,})'),
    re.compile(r'([Bb]earer\s+[A-Za-z0-9._\-]{16,})'),
    re.compile(r'((?:password|passwd|pwd|secret|token|api[_-]?key)["\']?\s*[:=]\s*["\']?)([^\s"\',}]{6,})', re.I),
    re.compile(r'\b([A-Fa-f0-9]{40,})\b'),
]


def redact(text: str) -> str:
    for rx in SECRET_RES:
        if rx.groups >= 2:
            text = rx.sub(lambda m: m.group(1) + "[REDACTED]", text)
        else:
            text = rx.sub("[REDACTED]", text)
    return text


def to_kst(ts: str) -> datetime | None:
    """'2026-09-17T06:46:19.268Z' -> KST datetime."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(KST)
    except (ValueError, AttributeError):
        return None


def resolve_requested(arg: str) -> date:
    today = datetime.now(KST).date()
    if arg == "today":
        return today
    if arg == "yesterday":
        return today - timedelta(days=1)
    return date.fromisoformat(arg)


COMMAND_RE = re.compile(r"<command-name>/?([\w:-]+)</command-name>")
SKIP_MARKERS = (
    "<local-command-stdout>", "<local-command-caveat>",
    "[Request interrupted", "Caveat: The messages below",
)


def clean_prompt(text: str) -> str | None:
    """실제 사용자 입력만 남긴다. 스킵 대상이면 None."""
    t = text.strip()
    if not t:
        return None
    m = COMMAND_RE.search(t)
    if m:
        return f"[/{m.group(1)}]"  # 슬래시 커맨드 실행 기록
    if any(mark in t for mark in SKIP_MARKERS):
        return None
    if t.startswith("<system-reminder>"):
        return None
    t = redact(t)
    if len(t) > PER_PROMPT_CHARS:
        t = t[:PER_PROMPT_CHARS] + " …(절단)"
    return t


def scan_transcripts(since: date) -> dict:
    """since(KST) 이후 활동 가능성이 있는 파일을 파싱해
    {local_date: {cwd: {session_id: session_dict}}} 로 버킷팅한다."""
    since_epoch = datetime.combine(since, datetime.min.time(), KST).timestamp()
    buckets: dict[date, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    titles: dict[str, str] = {}

    for path in glob.glob(os.path.join(PROJECTS_DIR, "*", "*.jsonl")):
        try:
            if os.path.getmtime(path) < since_epoch:
                continue
        except OSError:
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                typ = obj.get("type")
                if typ == "ai-title":
                    sid = obj.get("sessionId")
                    if sid and obj.get("aiTitle"):
                        titles[sid] = obj["aiTitle"]
                    continue
                if typ != "user" or obj.get("isSidechain"):
                    continue
                content = (obj.get("message") or {}).get("content")
                if not isinstance(content, str):
                    continue  # tool_result 등 리스트형은 사용자 입력이 아님
                dt = to_kst(obj.get("timestamp", ""))
                if dt is None or dt.date() < since:
                    continue
                prompt = clean_prompt(content)
                if prompt is None:
                    continue
                cwd = obj.get("cwd") or "(unknown)"
                sid = obj.get("sessionId") or os.path.basename(path).split(".")[0]
                sess = buckets[dt.date()][cwd].setdefault(sid, {
                    "session": sid[:8],
                    "start": dt.isoformat(timespec="minutes"),
                    "end": dt.isoformat(timespec="minutes"),
                    "prompts": [],
                    "git_branch": obj.get("gitBranch") or "",
                })
                sess["end"] = dt.isoformat(timespec="minutes")
                if len(sess["prompts"]) < MAX_PROMPTS_PER_SESSION:
                    sess["prompts"].append(f"{dt.strftime('%H:%M')} {prompt}")

    # 제목 매핑
    for day_map in buckets.values():
        for cwd_map in day_map.values():
            for sid, sess in cwd_map.items():
                if sid in titles:
                    sess["title"] = titles[sid]
    return buckets


def git_commits(cwd: str, day: date) -> list[dict]:
    """해당 repo의 그날(KST) 커밋. repo가 아니면 빈 목록."""
    if not os.path.isdir(cwd):
        return []
    since = day.isoformat() + " 00:00:00 +0900"
    until = (day + timedelta(days=1)).isoformat() + " 00:00:00 +0900"
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "log", "--all", f"--since={since}", f"--until={until}",
             "--pretty=format:%h|%ad|%an|%s", "--date=format-local:%H:%M"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "TZ": "Asia/Seoul"},
        )
    except (subprocess.TimeoutExpired, OSError):
        return []
    if proc.returncode != 0:
        return []
    out = []
    for ln in proc.stdout.splitlines():
        parts = ln.split("|", 3)
        if len(parts) == 4:
            out.append({"hash": parts[0], "time": parts[1], "author": parts[2],
                        "subject": redact(parts[3])})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Claude Code transcript 기반 일일 업무 원시 데이터 추출")
    ap.add_argument("--date", dest="date_", default="yesterday",
                    help="yesterday(기본) | today | YYYY-MM-DD")
    args = ap.parse_args()

    requested = resolve_requested(args.date_)
    buckets = scan_transcripts(requested - timedelta(days=FALLBACK_DAYS))

    actual, fallback = requested, False
    if requested not in buckets:
        earlier = sorted(d for d in buckets if d < requested)
        if not earlier:
            print(json.dumps({"requested_date": requested.isoformat(),
                              "date": None, "fallback": False, "projects": []},
                             ensure_ascii=False))
            return
        actual, fallback = earlier[-1], True

    projects = []
    seen_hashes: set[str] = set()
    for cwd, sess_map in sorted(buckets[actual].items()):
        sessions = sorted(sess_map.values(), key=lambda s: s["start"])
        commits = []
        for c in git_commits(cwd, actual):  # worktree끼리 중복 커밋 제거
            if c["hash"] not in seen_hashes:
                seen_hashes.add(c["hash"])
                commits.append(c)
        projects.append({"cwd": cwd.replace(HOME, "~"), "sessions": sessions,
                         "commits": commits})

    print(json.dumps({
        "requested_date": requested.isoformat(),
        "date": actual.isoformat(),
        "fallback": fallback,
        "projects": projects,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
