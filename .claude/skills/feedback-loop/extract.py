#!/usr/bin/env python3
"""
feedback-loop / extract.py

Claude Code transcript(~/.claude/projects/*/*.jsonl)에서
- 대화 텍스트(user/assistant)를 트림해 staging에 저장하고
- 구조적 마찰 신호(툴 거부/툴 에러/InputValidationError/스킬 호출)를 채굴한다.

LLM은 쓰지 않는다. 판단/리포트 작성은 SKILL.md(Claude)가 담당한다.

모드
  (기본)            : 마지막 수집 이후 변경된 세션의 신규 턴만 수집 → staging/<오늘>/ 에 기록, 신호 누적
  --dry-run         : 아무것도 쓰지 않고 요약만 출력
  --report-plan     : 마지막 리포트 이후의 staging 범위/신호/상위 세션 목록을 JSON으로 출력(상태 불변)
  --mark-report     : last_report_at 을 현재로 갱신
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
DATA = os.path.join(HOME, ".claude", "feedback-loop-data")
STAGING = os.path.join(DATA, "staging")
STATE_PATH = os.path.join(DATA, "state.json")

LOOKBACK_DAYS = 8          # 맥이 며칠 꺼져 있어도 최대 8일치 캐치업 (첫 실행 폭발 방지)
PER_TURN_CHARS = 4000      # 턴당 절단
TOP_SESSIONS = 15          # 리포트에서 딥리드할 상위 세션 수

REJECT_MARK = "doesn't want to proceed with this tool use"

# --- 시크릿 마스킹 -----------------------------------------------------------
SECRET_RES = [
    re.compile(r'(sk-[A-Za-z0-9]{8,})'),
    re.compile(r'(ghp_[A-Za-z0-9]{20,})'),
    re.compile(r'(xox[baprs]-[A-Za-z0-9-]{10,})'),
    re.compile(r'(AKIA[0-9A-Z]{12,})'),
    re.compile(r'([Bb]earer\s+[A-Za-z0-9._\-]{16,})'),
    re.compile(r'((?:password|passwd|pwd|secret|token|api[_-]?key)["\']?\s*[:=]\s*["\']?)([^\s"\',}]{6,})', re.I),
    re.compile(r'\b([A-Fa-f0-9]{40,})\b'),  # long hex
]

def redact(text):
    if not text:
        return text
    for rx in SECRET_RES:
        if rx.groups >= 2:
            text = rx.sub(lambda m: m.group(1) + "***REDACTED***", text)
        else:
            text = rx.sub("***REDACTED***", text)
    return text

# --- 상태 --------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": {}, "last_collect_at": None, "last_report_at": None}

def save_state(state):
    os.makedirs(DATA, exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)

def now_iso():
    return datetime.now().astimezone().isoformat()

def parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

# --- 프로젝트/파일 -----------------------------------------------------------
def project_slug(path):
    # ~/.claude/projects/<encoded>/<uuid>.jsonl -> <encoded>
    return os.path.basename(os.path.dirname(path))

def short_proj(slug):
    # 표시용 축약: 앞 -Users-hannie-init 제거, 남은 걸 사용
    s = slug
    for pre in ("-Users-hannie-init-", "-Users-hannie-init"):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    return s.strip("-") or "home"

def target_files():
    # 직속 *.jsonl 만 (subagents/·tool-results/ 는 더 깊어서 자동 제외)
    return sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")))

# --- 파싱 --------------------------------------------------------------------
def block_text(content):
    """message.content -> (표시 텍스트, tool_use[list of names], tool_results[list of dict])"""
    if isinstance(content, str):
        return content, [], []
    texts, tools, results = [], [], []
    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                texts.append(b.get("text", ""))
            elif t == "tool_use":
                tools.append({"id": b.get("id"), "name": b.get("name"), "input": b.get("input")})
            elif t == "tool_result":
                results.append(b)
            # thinking / image 등은 무시
    return "\n".join(texts).strip(), tools, results

def result_text(b):
    c = b.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for x in c:
            if isinstance(x, dict) and x.get("type") == "text":
                out.append(x.get("text", ""))
            elif isinstance(x, str):
                out.append(x)
        return "\n".join(out)
    return json.dumps(c, ensure_ascii=False) if c is not None else ""

def is_noise_user(text):
    """시스템 리마인더/커맨드 노이즈 사용자 턴 걸러내기"""
    if not text:
        return True
    t = text.strip()
    if t.startswith("<") and ("system-reminder" in t[:80] or "command-" in t[:80]):
        return True
    if t.startswith("Caveat:") or t.startswith("[Request interrupted"):
        return True
    return False

# --- 세션 처리 ---------------------------------------------------------------
def process_file(path, state, dry):
    sid = os.path.basename(path)[:-6]  # strip .jsonl
    slug = project_slug(path)
    size = os.path.getsize(path)
    prev = state["sessions"].get(sid, {})
    offset = prev.get("offset", 0)
    if offset > size:  # 파일이 줄었으면(로테이션) 처음부터
        offset = 0
    if offset == size:
        return None  # 신규 없음

    turns = []          # (role, text)
    signals = []        # dict
    tool_names = {}     # tool_use_id -> name (세션 전체에서 매핑 필요 → 처음부터 훑어 맵 구성)

    # tool_use id->name 맵은 offset 이전 것도 참조될 수 있으므로 파일 전체를 한 번 훑어 맵만 만든다
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                c = msg.get("content")
                if isinstance(c, list):
                    for b in c:
                        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id"):
                            tool_names[b["id"]] = b.get("name")
    except Exception:
        pass

    # 이제 offset 이후 신규 라인만 추출
    new_chars = 0
    with open(path, "r", errors="replace") as f:
        f.seek(offset)
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            msg = o.get("message")
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            text, tools, results = block_text(msg.get("content"))

            # 신호: tool_result (에러/거부)
            for r in results:
                if r.get("is_error"):
                    rt = result_text(r)
                    tname = tool_names.get(r.get("tool_use_id")) or "?"
                    if REJECT_MARK in rt:
                        # 거부 + 사용자 리다이렉트
                        redir = ""
                        idx = rt.find("the user said:")
                        if idx != -1:
                            redir = rt[idx + len("the user said:"):].strip()
                        signals.append({
                            "type": "tool_reject", "session": sid, "project": slug,
                            "tool": tname, "snippet": redact(redir[:400] or rt[:400]),
                        })
                    else:
                        subtype = "input_validation" if "InputValidationError" in rt else "tool_error"
                        signals.append({
                            "type": subtype, "session": sid, "project": slug,
                            "tool": tname, "snippet": redact(rt[:300]),
                        })

            # 신호: 스킬 호출
            for tu in tools:
                if tu.get("name") == "Skill":
                    inp = tu.get("input") or {}
                    signals.append({
                        "type": "skill_invoke", "session": sid, "project": slug,
                        "tool": inp.get("skill", "?"),
                        "snippet": redact(str(inp.get("args", ""))[:200]),
                    })

            # 대화 텍스트
            if role == "user":
                if not is_noise_user(text):
                    tt = redact(text[:PER_TURN_CHARS])
                    if tt:
                        turns.append(("user", tt))
                        new_chars += len(tt)
            elif role == "assistant":
                disp = text
                if tools:
                    disp = (disp + "  " if disp else "") + " ".join("[tool:%s]" % (t.get("name")) for t in tools)
                disp = disp.strip()
                if disp:
                    tt = redact(disp[:PER_TURN_CHARS])
                    turns.append(("assistant", tt))
                    new_chars += len(tt)

    return {
        "sid": sid, "slug": slug, "size": size, "prev_offset": offset,
        "turns": turns, "signals": signals, "new_chars": new_chars,
    }

def write_staging(day_dir, res, first_prompt):
    os.makedirs(day_dir, exist_ok=True)
    fname = "%s__%s.md" % (short_proj(res["slug"])[:40], res["sid"][:8])
    fpath = os.path.join(day_dir, fname)
    new_file = not os.path.exists(fpath)
    with open(fpath, "a", encoding="utf-8") as f:
        if new_file:
            f.write("# 세션 %s\n\n" % res["sid"])
            f.write("- 프로젝트: `%s`\n" % res["slug"])
            f.write("- 세션ID: %s\n" % res["sid"])
            if first_prompt:
                f.write("- 첫 질문: %s\n" % first_prompt[:160].replace("\n", " "))
            f.write("\n---\n")
        else:
            f.write("\n\n--- (이어붙임) ---\n")
        for role, txt in res["turns"]:
            f.write("\n**%s:** %s\n" % ("나" if role == "user" else "Claude", txt))
    return fpath

def append_signals(day_dir, sigs):
    os.makedirs(day_dir, exist_ok=True)
    sp = os.path.join(day_dir, "signals.json")
    existing = []
    if os.path.exists(sp):
        try:
            with open(sp) as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.extend(sigs)
    tmp = sp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    os.replace(tmp, sp)
    return sp

# --- 커맨드 ------------------------------------------------------------------
def cmd_collect(state, dry):
    now = datetime.now().astimezone()
    last = parse_iso(state.get("last_collect_at")) if state.get("last_collect_at") else None
    if last:
        cutoff = max(last, now - timedelta(days=LOOKBACK_DAYS))
    else:
        cutoff = now - timedelta(days=1)  # 첫 실행: 오늘만
    cutoff_ts = cutoff.timestamp()

    files = target_files()
    candidates = [p for p in files if os.path.getmtime(p) >= cutoff_ts]

    day_dir = os.path.join(STAGING, now.strftime("%Y-%m-%d"))
    total_new_sessions = 0
    total_chars = 0
    sig_counter = {}
    for p in candidates:
        res = process_file(p, state, dry)
        if not res or not (res["turns"] or res["signals"]):
            # 상태만 갱신(신규 있었으나 노이즈뿐일 수 있음)
            if res and not dry:
                state["sessions"][res["sid"]] = {"offset": res["size"], "mtime": os.path.getmtime(p)}
            continue
        total_new_sessions += 1
        total_chars += res["new_chars"]
        for s in res["signals"]:
            sig_counter[s["type"]] = sig_counter.get(s["type"], 0) + 1
        if not dry:
            first_prompt = next((t for r, t in res["turns"] if r == "user"), "")
            write_staging(day_dir, res, first_prompt)
            if res["signals"]:
                append_signals(day_dir, res["signals"])
            state["sessions"][res["sid"]] = {"offset": res["size"], "mtime": os.path.getmtime(p)}

    if not dry:
        state["last_collect_at"] = now_iso()
        save_state(state)

    print(json.dumps({
        "mode": "dry-run" if dry else "collect",
        "cutoff": cutoff.isoformat(),
        "candidate_files": len(candidates),
        "new_sessions": total_new_sessions,
        "new_chars": total_chars,
        "signals": sig_counter,
        "staging_dir": day_dir if not dry else None,
    }, ensure_ascii=False, indent=2))

def cmd_report_plan(state):
    now = datetime.now().astimezone()
    last_rep = parse_iso(state.get("last_report_at")) if state.get("last_report_at") else None
    since = last_rep or (now - timedelta(days=7))
    # since 날짜 이후의 staging 일자 폴더
    dirs = []
    if os.path.isdir(STAGING):
        for d in sorted(glob.glob(os.path.join(STAGING, "*"))):
            base = os.path.basename(d)
            try:
                dd = datetime.strptime(base, "%Y-%m-%d").date()
            except ValueError:
                continue
            if dd >= since.date():
                dirs.append(d)

    # 신호 집계 + 세션별 신호 카운트
    all_signals = []
    session_sig = {}
    session_file = {}
    for d in dirs:
        sp = os.path.join(d, "signals.json")
        if os.path.exists(sp):
            try:
                with open(sp) as f:
                    sigs = json.load(f)
                all_signals.extend(sigs)
                for s in sigs:
                    session_sig[s["session"]] = session_sig.get(s["session"], 0) + 1
            except Exception:
                pass
        for mf in glob.glob(os.path.join(d, "*.md")):
            sid8 = os.path.basename(mf).split("__")[-1].replace(".md", "")
            session_file.setdefault(sid8, mf)

    sig_by_type = {}
    for s in all_signals:
        sig_by_type[s["type"]] = sig_by_type.get(s["type"], 0) + 1

    # 상위 세션(신호 많은 순) → 딥리드 후보
    ranked = sorted(session_sig.items(), key=lambda kv: kv[1], reverse=True)
    top = []
    for sid, cnt in ranked[:TOP_SESSIONS]:
        f = session_file.get(sid[:8])
        top.append({"session": sid, "signal_count": cnt, "file": f})

    all_md = []
    for d in dirs:
        all_md.extend(sorted(glob.glob(os.path.join(d, "*.md"))))

    print(json.dumps({
        "since": since.isoformat(),
        "staging_dirs": dirs,
        "signal_totals": sig_by_type,
        "total_signals": len(all_signals),
        "total_staged_files": len(all_md),
        "top_sessions": top,
        "all_staged_files": all_md,
        "signals_files": [os.path.join(d, "signals.json") for d in dirs if os.path.exists(os.path.join(d, "signals.json"))],
    }, ensure_ascii=False, indent=2))

def cmd_mark_report(state):
    state["last_report_at"] = now_iso()
    save_state(state)
    print(json.dumps({"last_report_at": state["last_report_at"]}, ensure_ascii=False))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report-plan", action="store_true")
    ap.add_argument("--mark-report", action="store_true")
    args = ap.parse_args()

    state = load_state()
    if args.report_plan:
        cmd_report_plan(state)
    elif args.mark_report:
        cmd_mark_report(state)
    else:
        cmd_collect(state, args.dry_run)

if __name__ == "__main__":
    main()
