#!/usr/bin/env python3
"""글로벌 DB 조회/실행 스크립트 (dev/stg 쓰기 허용, prod 조회 전용).

단일 .env에서 접두어로 환경을 구분한다.
  - dev:  DEV_DB_*  (없으면 무접두어 DB_* 로 폴백 → 기존 .env 호환)
  - stg:  STG_DB_*  (폴백 없음)
  - prod: PROD_DB_* (폴백 없음 — 운영 자격증명은 명시 필수)

사용 예)
  python3 query.py --env dev --sql "SELECT * FROM stte_ccrc WHERE grp_cd='HSPTZ' LIMIT 10"
  python3 query.py --env dev --db member_db_name --sql "SELECT ... "
  python3 query.py --env prod --sql "SELECT ..."      # 조회만 허용
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    import pymysql
except ImportError:
    print("필수 패키지 없음. 실행: pip install pymysql python-dotenv")
    sys.exit(1)

SKILL_DIR = Path(__file__).parent.parent
ENV_FILE = SKILL_DIR / ".env"
load_dotenv(ENV_FILE)

# 조회로 간주하는 구문 (첫 키워드 기준)
READ_ONLY_HEADS = ("select", "show", "desc", "describe", "explain", "with")


def load_db_config(env="dev"):
    """환경(dev/stg/prod)별 DB 설정 로드."""
    env = (env or "dev").lower()
    prefix = f"{env.upper()}_"  # DEV_ / STG_ / PROD_

    def pick(key):
        val = os.getenv(prefix + key)
        if val is None and env == "dev":
            val = os.getenv(key)  # 기존 무접두어 .env 호환
        return val

    config = {
        "host": pick("DB_HOST") or "localhost",
        "port": int(pick("DB_PORT") or "3306"),
        "database": pick("DB_NAME"),
        "user": pick("DB_USER"),
        "password": pick("DB_PASSWORD"),
        "charset": "utf8mb4",
        "autocommit": True,
    }
    if not config["database"] or not config["user"]:
        print(f"[오류] '{env}' 환경 DB 설정이 없습니다. .env에 {prefix}DB_NAME / {prefix}DB_USER 를 설정하세요.")
        print(f"위치: {ENV_FILE}")
        sys.exit(1)
    return config


def statements_of(sql):
    """세미콜론 기준으로 비어있지 않은 구문 목록."""
    return [s.strip() for s in sql.split(";") if s.strip()]


def is_read_only(stmt):
    return stmt.lower().lstrip("(").split(None, 1)[0] in READ_ONLY_HEADS


def run(env, sql, db_override=None, allow_write=False):
    config = load_db_config(env)
    if db_override:
        config["database"] = db_override

    stmts = statements_of(sql)
    if not stmts:
        print("[오류] 실행할 SQL이 없습니다.")
        sys.exit(1)

    writes = [s for s in stmts if not is_read_only(s)]

    # prod 안전장치: 조회 전용 (쓰기 항상 차단)
    if env == "prod" and writes:
        print("[차단] prod 환경은 조회 전용입니다. SELECT/SHOW/DESC/EXPLAIN 만 허용됩니다.")
        print(f"        차단된 구문: {writes[0][:80]}...")
        print("        쓰기가 필요하면 SQL만 생성해 사용자 승인을 받으세요.")
        sys.exit(2)

    # dev/stg 안전장치: 쓰기는 사용자 승인(--allow-write) 후에만 실행
    if env in ("dev", "stg") and writes and not allow_write:
        print(f"[확인 필요] {env} 쓰기 작업은 사용자 승인 후에만 실행됩니다.")
        print("           아래 SQL을 사용자에게 보여주고 승인받은 뒤 --allow-write 로 재실행하세요.")
        for w in writes:
            print(f"           - {w}")
        sys.exit(3)

    print(f"[연결] env={env} host={config['host']} db={config['database']}\n")
    conn = pymysql.connect(**config)
    try:
        for i, stmt in enumerate(stmts, 1):
            if len(stmts) > 1:
                print(f"───── [{i}/{len(stmts)}] {stmt[:70]}{'...' if len(stmt) > 70 else ''}")
            with conn.cursor() as cur:
                cur.execute(stmt)
                if cur.description:  # 결과셋이 있는 조회
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    _print_table(cols, rows)
                    print(f"({len(rows)} rows)\n")
                else:  # 쓰기 구문
                    print(f"[완료] affected rows = {cur.rowcount}\n")
    finally:
        conn.close()


def _print_table(cols, rows):
    if not rows:
        print(" | ".join(cols))
        print("(결과 없음)")
        return
    widths = [len(c) for c in cols]
    srows = []
    for r in rows:
        sr = ["" if v is None else str(v) for v in r]
        srows.append(sr)
        for j, v in enumerate(sr):
            widths[j] = max(widths[j], len(v))
    line = " | ".join(c.ljust(widths[j]) for j, c in enumerate(cols))
    print(line)
    print("-+-".join("-" * w for w in widths))
    for sr in srows:
        print(" | ".join(v.ljust(widths[j]) for j, v in enumerate(sr)))


def main():
    parser = argparse.ArgumentParser(description="글로벌 DB 조회/실행 (dev/stg 쓰기 허용, prod 조회 전용)")
    parser.add_argument("--env", default="dev", choices=["dev", "stg", "prod"],
                        help="대상 환경 (기본 dev). prod는 조회 전용")
    parser.add_argument("--sql", required=True, help="실행할 SQL (세미콜론으로 여러 구문 가능)")
    parser.add_argument("--db", help="database 이름 오버라이드 (예: member DB 조회)")
    parser.add_argument("--allow-write", action="store_true",
                        help="dev/stg 쓰기 실행 허용 (사용자 승인 후에만 사용). prod는 무시됨")
    args = parser.parse_args()
    run(args.env, args.sql, args.db, args.allow_write)


if __name__ == "__main__":
    main()
