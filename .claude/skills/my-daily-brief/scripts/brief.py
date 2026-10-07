#!/usr/bin/env python3
"""hermes-kb(private)에서 특정 사람의 데일리 브리핑 + 미완료 태스크를 뽑아 한국어로 출력한다.

데이터는 gh api 온디맨드로 읽는다(로컬 클론 불필요). 철저히 읽기 전용이다.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta

REPO = os.getenv("HERMES_KB_REPO", "khc-dt/hermes-kb")
DEFAULT_PERSON = os.getenv("HERMES_ME", "hannie.init")


def _fail(msg: str) -> "None":
    print(f"[오류] {msg}", file=sys.stderr)
    sys.exit(1)


def gh_api(path: str, raw: bool = False) -> str:
    """gh api 호출. raw=True면 파일 원문(base64 아님)을 그대로 받는다."""
    cmd = ["gh", "api", f"repos/{REPO}/{path}"]
    if raw:
        cmd += ["-H", "Accept: application/vnd.github.raw"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        _fail("gh CLI가 설치되어 있지 않습니다. `brew install gh` 후 `gh auth login` 하세요.")
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if "404" in err:
            _fail(f"경로를 찾을 수 없습니다: {path} (repo={REPO})\n{err}")
        if "401" in err or "auth" in err.lower():
            _fail(f"gh 인증이 필요합니다. `gh auth login` 후 다시 시도하세요.\n{err}")
        _fail(f"gh api 실패: {path}\n{err}")
    return proc.stdout


def list_daily_dates() -> list[str]:
    """tasks/daily/ 에 있는 YYYY-MM-DD 목록(오름차순)."""
    entries = json.loads(gh_api("contents/tasks/daily"))
    dates = []
    for e in entries:
        name = e.get("name", "")
        if name.endswith(".json"):
            dates.append(name[: -len(".json")])
    return sorted(dates)


def resolve_date(requested: str | None, available: list[str]) -> tuple[str, bool]:
    """요청 날짜를 가용 목록에 맞춰 해석한다. (해석된 날짜, 폴백여부) 반환."""
    if not available:
        _fail("tasks/daily 에 브리핑 파일이 없습니다.")
    if requested in (None, "latest"):
        return available[-1], False
    if requested == "today":
        target = date.today().isoformat()
    elif requested == "yesterday":
        target = (date.today() - timedelta(days=1)).isoformat()
    else:
        target = requested
    if target in available:
        return target, False
    # target 이하 가장 최신 날짜로 폴백
    below = [d for d in available if d <= target]
    if below:
        return below[-1], True
    return available[0], True


def alias_key(name: str | None) -> str:
    """'hannie.init(김한나)' -> 'hannie.init'."""
    if not name:
        return ""
    return name.split("(", 1)[0].strip()


def load_json_file(path: str) -> dict:
    return json.loads(gh_api(f"contents/{path}", raw=True))


def pick_person_brief(daily: dict, person: str) -> dict | None:
    for p in daily.get("team_member_focus", []):
        if alias_key(p.get("name")) == person:
            return p
    return None


def my_open_tasks(open_tasks: dict, person: str) -> list[dict]:
    out = []
    for t in open_tasks.get("tasks", []):
        if alias_key(t.get("owner")) != person:
            continue
        if (t.get("status") or "").lower() == "done":
            continue
        out.append(t)
    # 마감일 있는 것 먼저, 그다음 우선순위
    prio = {"high": 0, "상": 0, "medium": 1, "중": 1, "low": 2, "하": 2}
    out.sort(key=lambda t: (t.get("due_date") is None, t.get("due_date") or "",
                            prio.get((t.get("priority") or "").lower(), 3)))
    return out


def _item_fields(item) -> tuple[str, str, str]:
    """action/done 항목이 문자열이든 객체든 (importance, title, source)로 정규화."""
    if isinstance(item, str):
        return "", item, ""
    if isinstance(item, dict):
        return ((item.get("importance") or "").strip(),
                item.get("title", ""),
                item.get("source", ""))
    return "", str(item), ""


def render(person_name: str, brief_date: str, fallback: bool,
           brief: dict | None, tasks: list[dict]) -> str:
    lines = []
    title_name = person_name
    lines.append(f"📋 {title_name} 데일리 브리핑 — {brief_date}")
    if fallback:
        lines.append(f"   (요청 날짜에 브리핑이 없어 {brief_date} 로 대체)")
    lines.append("")

    if brief is None:
        lines.append("🔵 진행/예정")
        lines.append("   - (해당 날짜 브리핑에 이 사람 항목 없음)")
        lines.append("")
    else:
        action = brief.get("action_items", [])
        done = brief.get("done_items", [])
        blockers = brief.get("blockers", [])

        lines.append("🔵 진행/예정")
        if action:
            for it in action:
                imp, title, src = _item_fields(it)
                imp_s = f"[{imp}] " if imp else "[ ] "
                src_s = f"  ({src})" if src else ""
                lines.append(f"   - {imp_s}{title}{src_s}")
        else:
            lines.append("   - (없음)")
        lines.append("")

        lines.append("✅ 완료")
        if done:
            for it in done:
                _, title, src = _item_fields(it)
                src_s = f"  ({src})" if src else ""
                lines.append(f"   - {title}{src_s}")
        else:
            lines.append("   - (없음)")
        lines.append("")

        lines.append("⚠️ 블로커")
        if blockers:
            for it in blockers:
                text = it if isinstance(it, str) else it.get("title", str(it))
                lines.append(f"   - {text}")
        else:
            lines.append("   - (없음)")
        lines.append("")

    lines.append(f"📌 미완료 태스크 ({len(tasks)}건)")
    if tasks:
        for t in tasks:
            status = t.get("status", "?")
            due = t.get("due_date") or "-"
            url = t.get("source_url") or t.get("source_id") or ""
            lines.append(f"   - [{status}] {t.get('title', '')}  | 마감: {due}  | {url}")
    else:
        lines.append("   - (없음)")
    lines.append("")

    if brief and brief.get("source_refs"):
        lines.append("출처: " + ", ".join(brief["source_refs"]))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="hermes-kb 내 데일리 브리핑")
    ap.add_argument("--date", dest="date_", default="latest",
                    help="latest(기본) | today | yesterday | YYYY-MM-DD")
    ap.add_argument("--person", default=DEFAULT_PERSON,
                    help=f"영문 alias (기본 {DEFAULT_PERSON}). 예: kane.cho")
    ap.add_argument("--json", action="store_true", help="필터된 원본 JSON 출력")
    args = ap.parse_args()

    person = alias_key(args.person)  # 'hannie.init(김한나)' 로 줘도 처리
    available = list_daily_dates()
    brief_date, fallback = resolve_date(args.date_, available)

    daily = load_json_file(f"tasks/daily/{brief_date}.json")
    brief = pick_person_brief(daily, person)
    open_tasks = load_json_file("tasks/open-tasks.json")
    tasks = my_open_tasks(open_tasks, person)

    # 표시용 이름: 브리핑에 있으면 그 표기(한글 포함), 없으면 태스크 owner, 없으면 alias
    display = person
    if brief and brief.get("name"):
        display = brief["name"]
    elif tasks:
        display = tasks[0].get("owner") or person

    if args.json:
        print(json.dumps({
            "date": brief_date,
            "fallback": fallback,
            "person": display,
            "brief": brief,
            "open_tasks": tasks,
        }, ensure_ascii=False, indent=2))
        return

    print(render(display, brief_date, fallback, brief, tasks))


if __name__ == "__main__":
    main()
