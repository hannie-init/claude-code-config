#!/usr/bin/env python3
"""Cloud Run 에러 감시 1-사이클 코어.

여러 대상 서비스(skill/member/common 또는 임의 서비스명)의 최근 ERROR 로그를
gcloud logging read(조회 전용)로 가져와 파싱하고, 신규 에러(워터마크 초과분)를
message/trace로 그룹핑해 사람용 리포트 + 기계용 RESULT json 라인을 출력한다.

워터마크 관리·푸시 알림·주기 실행(/loop)은 호출하는 쪽(스킬/Claude)이 담당한다.
prod는 조회 전용 — 이 스크립트는 gcloud logging read 외에 어떤 쓰기도 하지 않는다.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from collections import Counter, defaultdict

# --- 고정 매핑 -------------------------------------------------------------
PROJECTS = {
    "dev": "dev-dfd-393200",
    "stg": "stg-dfd",
    "prod": "prd-dfd",
}

# target 이름 -> env별 Cloud Run 서비스명 (실측값)
TARGETS = {
    "skill": {
        "prod": "run-prd-dfd-hsp-api-skill",
        "dev": "run-dev-dfd-hsp-api-skill",
        "stg": "stg-dfd-hsp-api",
    },
    "member": {
        "prod": "dfd-mem-api",
        "dev": "dev-dfd-mem-api",
        "stg": "stg-dfd-mem-api",
    },
    "common": {
        "prod": "dfd-com-api",
        "dev": "dev-dfd-com-api",
        "stg": "stg-dfd-com-api",
    },
}

CONSOLE_BASE = "https://console.cloud.google.com/logs/query"


def find_gcloud_python():
    """gcloud가 3.9로 크래시하는 문제 회피용 python3.10+ 경로 탐색."""
    env_val = os.environ.get("CLOUDSDK_PYTHON")
    if env_val and os.path.exists(env_val):
        return env_val
    candidates = [
        os.path.expanduser("~/.local/bin/python3.10"),
        "/opt/homebrew/bin/python3.12",
        "/opt/homebrew/bin/python3.11",
        "/opt/homebrew/bin/python3.10",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    for name in ("python3.13", "python3.12", "python3.11", "python3.10"):
        found = shutil.which(name)
        if found:
            return found
    return None


def run_gcloud_read(project, service, region, severity, freshness, limit):
    """gcloud logging read 실행 → 로그 엔트리 리스트(JSON) 반환."""
    query = (
        'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{service}" '
        f'AND resource.labels.location="{region}" '
        'AND NOT (jsonPayload.requestUri=~"/prometheus" '
        'OR httpRequest.requestUrl=~"/prometheus") '
        f"AND severity>={severity}"
    )
    cmd = [
        "gcloud", "logging", "read", query,
        f"--project={project}",
        f"--freshness={freshness}",
        f"--limit={limit}",
        "--order=desc",
        "--format=json",
    ]
    env = dict(os.environ)
    gpy = find_gcloud_python()
    if gpy:
        env["CLOUDSDK_PYTHON"] = gpy
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"gcloud logging read 실패 (service={service}): "
            f"{proc.stderr.strip()[:500]}"
        )
    out = proc.stdout.strip()
    if not out:
        return []
    return json.loads(out)


def message_of(entry):
    """엔트리에서 사람이 읽는 대표 메시지 추출."""
    jp = entry.get("jsonPayload") or {}
    msg = ""
    if isinstance(jp, dict):
        msg = jp.get("message") or ""
    if not msg:
        msg = entry.get("textPayload") or ""
    return msg.strip()


def message_label(entry):
    """집계용 라벨(대표 패턴으로 정규화)."""
    msg = message_of(entry)
    if "EXTERNAL_SERVICE_ERROR" in msg:
        return "[WebClient] EXTERNAL_SERVICE_ERROR"
    if "WebClientException" in msg:
        return "WebClientException: 외부 서비스 통신 실패"
    if not msg:
        url = (entry.get("httpRequest") or {}).get("requestUrl", "")
        path = re.sub(r"^https?://[^/]+", "", url)
        return f"(HTTP 요청 에러) {path[:50]}" if path else "(빈 메시지)"
    return msg.splitlines()[0][:60]


def path_of(entry):
    url = (entry.get("httpRequest") or {}).get("requestUrl", "")
    return re.sub(r"^https?://[^/]+", "", url)


def encode_query(lines):
    return urllib.parse.quote("\n".join(lines), safe="")


def time_range_param(start_ts, end_ts):
    return urllib.parse.quote(f"{start_ts}/{end_ts}", safe="")


def pad_ts(ts, minutes, direction):
    """RFC3339 timestamp를 분 단위로 앞뒤 확장. 간단히 초 단위 파싱 없이 문자열 재조립."""
    # ts 예: 2026-07-09T05:28:17.777659Z → datetime 파싱
    from datetime import datetime, timedelta, timezone
    clean = ts.replace("Z", "+00:00")
    # 마이크로초 자리 정규화
    try:
        dt = datetime.fromisoformat(clean)
    except ValueError:
        # 소수점 이하 자릿수 과다 시 잘라내기
        m = re.match(r"(.*\.\d{6})\d*(\+00:00)", clean)
        if m:
            dt = datetime.fromisoformat(m.group(1) + m.group(2))
        else:
            raise
    dt = dt.astimezone(timezone.utc)
    delta = timedelta(minutes=minutes)
    dt = dt - delta if direction == "start" else dt + delta
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def trace_link(service, trace_id, start_ts, end_ts, project):
    q = encode_query([
        f'trace="projects/{project}/traces/{trace_id}"',
        f'resource.labels.service_name="{service}"',
    ])
    tr = time_range_param(start_ts, end_ts)
    return f"{CONSOLE_BASE};query={q};timeRange={tr}?project={project}"


def batch_link(service, region, severity, start_ts, end_ts, project):
    q = encode_query([
        'resource.type="cloud_run_revision"',
        f'resource.labels.service_name="{service}"',
        f'resource.labels.location="{region}"',
        f"severity>={severity}",
    ])
    tr = time_range_param(start_ts, end_ts)
    return f"{CONSOLE_BASE};query={q};timeRange={tr}?project={project}"


def resolve_targets(env, targets, services):
    """(라벨, 서비스명) 리스트 생성. 라벨은 사람이 읽는 이름."""
    resolved = []
    for t in targets:
        if t not in TARGETS:
            raise SystemExit(
                f"알 수 없는 target '{t}'. 사용 가능: {', '.join(TARGETS)} "
                f"(그 외 서비스는 --service 로 직접 지정)"
            )
        svc = TARGETS[t].get(env)
        if not svc:
            raise SystemExit(f"target '{t}'는 env '{env}'에 매핑이 없습니다.")
        resolved.append((t, svc))
    for s in services:
        resolved.append((s, s))
    # 서비스명 기준 중복 제거(순서 유지)
    seen = set()
    uniq = []
    for label, svc in resolved:
        if svc in seen:
            continue
        seen.add(svc)
        uniq.append((label, svc))
    return uniq


def analyze_service(label, service, entries, since, excludes,
                    region, severity, window_pad, link_traces, project):
    """한 서비스의 신규 에러 분석 + 리포트 문자열 + 요약 dict 반환."""
    exclude_res = [re.compile(p) for p in excludes]

    def excluded(entry):
        msg = message_of(entry)
        return any(r.search(msg) for r in exclude_res)

    new = []
    for e in entries:
        ts = e.get("timestamp", "")
        if since and ts <= since:
            continue
        if excluded(e):
            continue
        new.append(e)

    if not new:
        return (f"### {label} (`{service}`)\n정상 — 신규 ERROR 없음\n",
                {"service": service, "new_count": 0, "max_ts": since or None,
                 "top_message": None})

    timestamps = sorted(e.get("timestamp", "") for e in new)
    min_ts, max_ts = timestamps[0], timestamps[-1]
    start_ts = pad_ts(min_ts, window_pad, "start")
    end_ts = pad_ts(max_ts, window_pad, "end")

    msg_counts = Counter(message_label(e) for e in new)

    # trace 그룹핑
    trace_entries = defaultdict(list)
    for e in new:
        tr = e.get("trace", "")
        if tr:
            trace_entries[tr].append(e)
    top_traces = sorted(trace_entries.items(),
                        key=lambda kv: len(kv[1]), reverse=True)[:link_traces]

    lines = [f"### {label} (`{service}`) — 신규 ERROR {len(new)}건"]
    lines.append(f"구간: {min_ts} ~ {max_ts} (UTC)")
    lines.append("")
    lines.append("| 건수 | 메시지 |")
    lines.append("|---|---|")
    for m, n in msg_counts.most_common():
        lines.append(f"| {n} | {m} |")
    lines.append("")
    if top_traces:
        lines.append(f"**trace별 전체 흐름 링크 (상위 {len(top_traces)})**")
        for tr, es in top_traces:
            tid = tr.split("/")[-1]
            lines.append(f"- `{tid[:12]}…` ({len(es)}건): "
                        f"{trace_link(service, tid, start_ts, end_ts, project)}")
        lines.append("")
    lines.append(f"**배치 전체(severity>={severity}) 링크**: "
                f"{batch_link(service, region, severity, start_ts, end_ts, project)}")
    lines.append("")

    top_message = msg_counts.most_common(1)[0][0]
    return ("\n".join(lines),
            {"service": service, "new_count": len(new), "max_ts": max_ts,
             "top_message": top_message})


def main():
    ap = argparse.ArgumentParser(
        description="Cloud Run 에러 감시 1-사이클 (조회 전용)")
    ap.add_argument("--env", required=True, choices=list(PROJECTS))
    ap.add_argument("--target", action="append", default=[],
                    help="skill|member|common (반복 가능)")
    ap.add_argument("--service", action="append", default=[],
                    help="임의 Cloud Run 서비스명 (반복 가능)")
    ap.add_argument("--severity", default="ERROR")
    ap.add_argument("--freshness", default="11m")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--since-json", default="",
                    help='대상별 워터마크 {"서비스명":"RFC3339"}')
    ap.add_argument("--exclude", action="append", default=[],
                    help="제외할 메시지 정규식 (반복 가능)")
    ap.add_argument("--window-pad", type=int, default=5,
                    help="링크 timeRange 앞뒤 분")
    ap.add_argument("--link-traces", type=int, default=5)
    ap.add_argument("--region", default="asia-northeast3")
    args = ap.parse_args()

    if not args.target and not args.service:
        ap.error("--target 또는 --service 중 최소 하나는 필요합니다.")

    project = PROJECTS[args.env]
    since_map = {}
    if args.since_json:
        try:
            since_map = json.loads(args.since_json)
        except json.JSONDecodeError as ex:
            ap.error(f"--since-json 파싱 실패: {ex}")

    targets = resolve_targets(args.env, args.target, args.service)

    report_sections = []
    services_result = {}
    header = (f"## Cloud Run 에러 감시 [{args.env}] "
              f"(severity>={args.severity}, freshness={args.freshness})")
    report_sections.append(header)

    for label, service in targets:
        try:
            entries = run_gcloud_read(project, service, args.region,
                                    args.severity, args.freshness, args.limit)
        except RuntimeError as ex:
            report_sections.append(f"### {label} (`{service}`)\n⚠️ 조회 실패: {ex}\n")
            services_result[service] = {"error": str(ex), "new_count": 0}
            continue
        section, summary = analyze_service(
            label, service, entries, since_map.get(service), args.exclude,
            args.region, args.severity, args.window_pad, args.link_traces, project)
        report_sections.append(section)
        services_result[service] = {
            "new_count": summary["new_count"],
            "max_ts": summary["max_ts"],
            "top_message": summary["top_message"],
        }

    # 통합 요약 / push 문구
    total_new = sum(v.get("new_count", 0) for v in services_result.values())
    parts = []
    for label, service in targets:
        v = services_result.get(service, {})
        n = v.get("new_count", 0)
        if n:
            parts.append(f"{label} {n}")
    push_text = ""
    if total_new:
        push_text = f"[{args.env}] 신규 ERROR — " + " / ".join(parts)
        top = None
        for label, service in targets:
            tm = services_result.get(service, {}).get("top_message")
            if tm:
                top = tm
                break
        if top:
            push_text += f" (대표: {top[:50]})"

    result = {
        "env": args.env,
        "services": services_result,
        "total_new": total_new,
        "push_text": push_text,
    }

    print("\n".join(report_sections))
    print("RESULT " + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
