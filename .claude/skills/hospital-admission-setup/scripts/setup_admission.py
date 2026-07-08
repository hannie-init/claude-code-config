#!/usr/bin/env python3
"""병원 입원 기본 기능 DB 세팅 스크립트 (skill DB + member DB)"""

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

load_dotenv(Path(__file__).parent.parent / ".env")

_DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "autocommit": True,
}

_MEMBER_DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("MEMBER_DB_NAME"),
    "charset": "utf8mb4",
    "autocommit": True,
}

ALL_FEATURES = [
    "HSP_MST_INFO", "TODAY_SCHEDULE", "DOCTOR_INFO", "DISCHARGE_ACTIVATE",
    "PRE_GUIDE_URL", "PARK_URL", "MEMBER_EXPD", "MEMBER_LVG",
]


def connect():
    try:
        return pymysql.connect(**_DB)
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}\n.env 설정 및 VPN 연결 확인")
        sys.exit(1)


def connect_member():
    if not _MEMBER_DB.get("database"):
        print("⚠️  MEMBER_DB_NAME 미설정 — member DB 항목은 조회/수정 불가")
        return None
    try:
        return pymysql.connect(**_MEMBER_DB)
    except Exception as e:
        print(f"⚠️  member DB 연결 실패: {e}")
        return None


def _fmt_sql(sql: str, params: tuple) -> str:
    result = sql
    for p in params:
        val = "NULL" if p is None else f"'{p}'" if isinstance(p, str) else str(p)
        result = result.replace("%s", val, 1)
    return result


def _hsp_prop_row(hsp_id: int, code: str, value: str, description: str, category: str = "입원"):
    sql = (
        "INSERT INTO hsp_prop"
        " (hsp_id, code, value, description, category, use_yn, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id)\n"
        "VALUES (%s, %s, %s, %s, %s, 'Y', NOW(), 0, NOW(), 0)"
    )
    return sql, (hsp_id, code, value, description, category)


def _dtl_mst_row(hsp_id: int, grp_cd: str, dtl_cd: str, dtl_cd_nm: str):
    sql = (
        "INSERT INTO dtl_mst"
        " (hsp_id, grp_cd, dtl_cd, dtl_cd_nm, dtl_cd_seq, use_yn, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id)\n"
        "VALUES (%s, %s, %s, %s, 1, 'Y', NOW(), 0, NOW(), 0)"
    )
    return sql, (hsp_id, grp_cd, dtl_cd, dtl_cd_nm)


def _hsp_mst_update(hsp_id: int):
    sql = "UPDATE hsp_mst SET hsptz_info = 'Y' WHERE hsp_id = %s"
    return sql, (hsp_id,)


def _svc_hsp_mst_update(hsp_id: int, col: str):
    sql = f"UPDATE svc_hsp_mst SET {col} = 'Y' WHERE hsp_id = %s"
    return sql, (hsp_id,)


def build_items(hsp_id: int, args) -> list[dict]:
    items = []

    if "HSP_MST_INFO" in args.features:
        sql, params = _hsp_mst_update(hsp_id)
        items.append({"label": "입원생활 안내 활성화 (hsp_mst)", "sql": sql, "params": params,
                      "ck": ("hsp_mst", hsp_id), "conn_type": "skill"})

    if "TODAY_SCHEDULE" in args.features:
        sql, params = _hsp_prop_row(hsp_id, "HSPTLZ_TODAY_SCHEDULE_MENU_YN", "Y", "오늘의 일정 메뉴 사용 여부")
        items.append({"label": "오늘의 일정", "sql": sql, "params": params,
                      "ck": ("hsp_prop", hsp_id, "HSPTLZ_TODAY_SCHEDULE_MENU_YN"), "conn_type": "skill"})

    if "DOCTOR_INFO" in args.features:
        sql, params = _dtl_mst_row(hsp_id, "HSPTZ_LIVING_MYDOCTOR", "HSPTZ_LIVING_MYDOCTOR_INFO", "주치의 정보 보기")
        items.append({"label": "주치의 정보보기", "sql": sql, "params": params,
                      "ck": ("dtl_mst", hsp_id, "HSPTZ_LIVING_MYDOCTOR", "HSPTZ_LIVING_MYDOCTOR_INFO"), "conn_type": "skill"})

    if "DISCHARGE_ACTIVATE" in args.features:
        sql, params = _dtl_mst_row(hsp_id, "HSPTZ_LIVING_DISCHARGE", "HSPTZ_LIVING_DISCHARGE_INFO", "퇴원 안내 정보")
        items.append({"label": "퇴원 안내 활성화", "sql": sql, "params": params,
                      "ck": ("dtl_mst", hsp_id, "HSPTZ_LIVING_DISCHARGE", "HSPTZ_LIVING_DISCHARGE_INFO"), "conn_type": "skill"})

    if "PRE_GUIDE_URL" in args.features:
        if not args.pre_guide_url:
            print("❌ PRE_GUIDE_URL 세팅에 --pre-guide-url 값이 필요합니다.")
            sys.exit(1)
        sql, params = _hsp_prop_row(hsp_id, "HOSPITALIZATION_PRE_GUIDE_URL", args.pre_guide_url, "입원 사전 안내 URL")
        items.append({"label": "입원 사전 안내 URL", "sql": sql, "params": params,
                      "ck": ("hsp_prop", hsp_id, "HOSPITALIZATION_PRE_GUIDE_URL"), "conn_type": "skill"})

    if "PARK_URL" in args.features:
        if not args.park_url:
            print("❌ PARK_URL 세팅에 --park-url 값이 필요합니다.")
            sys.exit(1)
        sql, params = _hsp_prop_row(hsp_id, "PARK_GUIDE_URL", args.park_url, "주차 안내 URL")
        items.append({"label": "주차 안내 URL", "sql": sql, "params": params,
                      "ck": ("hsp_prop", hsp_id, "PARK_GUIDE_URL"), "conn_type": "skill"})

    if "MEMBER_EXPD" in args.features:
        sql, params = _svc_hsp_mst_update(hsp_id, "hsptlz_expd_use_yn")
        items.append({"label": "입원 확인 (member DB)", "sql": sql, "params": params,
                      "ck": ("svc_hsp_mst", hsp_id, "hsptlz_expd_use_yn"), "conn_type": "member"})

    if "MEMBER_LVG" in args.features:
        sql, params = _svc_hsp_mst_update(hsp_id, "hsptlz_lvng_use_yn")
        items.append({"label": "입원생활 안내 활성화 (member DB)", "sql": sql, "params": params,
                      "ck": ("svc_hsp_mst", hsp_id, "hsptlz_lvng_use_yn"), "conn_type": "member"})

    return items


def is_existing(conn, ck: tuple) -> bool:
    with conn.cursor() as cur:
        if ck[0] == "hsp_prop":
            cur.execute("SELECT 1 FROM hsp_prop WHERE hsp_id=%s AND code=%s", (ck[1], ck[2]))
        elif ck[0] == "hsp_mst":
            cur.execute("SELECT hsptz_info FROM hsp_mst WHERE hsp_id=%s", (ck[1],))
            row = cur.fetchone()
            return row is not None and row[0] == "Y"
        elif ck[0] == "svc_hsp_mst":
            col = ck[2]
            cur.execute(f"SELECT {col} FROM svc_hsp_mst WHERE hsp_id=%s", (ck[1],))
            row = cur.fetchone()
            return row is not None and row[0] == "Y"
        else:
            cur.execute(
                "SELECT 1 FROM dtl_mst WHERE hsp_id=%s AND grp_cd=%s AND dtl_cd=%s",
                (ck[1], ck[2], ck[3]),
            )
        return cur.fetchone() is not None


def query_hospital(conn, hsp_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT code, value, use_yn FROM hsp_prop"
            " WHERE hsp_id=%s AND code IN (%s,%s,%s) ORDER BY code",
            (hsp_id, "HSPTLZ_TODAY_SCHEDULE_MENU_YN", "HOSPITALIZATION_PRE_GUIDE_URL", "PARK_GUIDE_URL"),
        )
        props = cur.fetchall()

        cur.execute(
            "SELECT grp_cd, dtl_cd, dtl_cd_nm, use_yn FROM dtl_mst"
            " WHERE hsp_id=%s AND grp_cd IN (%s,%s) ORDER BY grp_cd",
            (hsp_id, "HSPTZ_LIVING_MYDOCTOR", "HSPTZ_LIVING_DISCHARGE"),
        )
        dtls = cur.fetchall()

        cur.execute(
            "SELECT grp_cd, COUNT(*) FROM hsp_guid_mst"
            " WHERE hsp_id=%s AND use_yn='Y' AND grp_cd IN (%s,%s,%s,%s) GROUP BY grp_cd",
            (hsp_id, "HSPTLZ_LIVING_GUIDE", "CONVENIENCE_UTILITY", "HSPTZ_LIVING_SAFETY_MANAGEMENT", "DISCHARGE_GUIDE"),
        )
        cards = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT hsptz_info FROM hsp_mst WHERE hsp_id=%s", (hsp_id,))
        hsp_mst_row = cur.fetchone()

    return props, dtls, cards, hsp_mst_row


def query_member(member_conn, hsp_id: int):
    with member_conn.cursor() as cur:
        cur.execute(
            "SELECT hsptlz_expd_use_yn, hsptlz_lvng_use_yn FROM svc_hsp_mst WHERE hsp_id=%s",
            (hsp_id,),
        )
        return cur.fetchone()


def _yn_status(val, label_prefix=""):
    if val is None:
        return "❌ 미설정"
    return "✅ Y" if val == "Y" else f"❌ {val}"


def main():
    parser = argparse.ArgumentParser(description="병원 입원 기본 기능 DB 세팅")
    parser.add_argument("--hsp-id", type=int, help="병원 ID")
    parser.add_argument(
        "--features",
        default=",".join(ALL_FEATURES),
        help=f"세팅할 기능 코드 (콤마 구분). 선택값: {', '.join(ALL_FEATURES)}",
    )
    parser.add_argument("--pre-guide-url", help="입원 사전 안내 URL (PRE_GUIDE_URL 포함 시 필수)")
    parser.add_argument("--park-url", help="주차 안내 URL (PARK_URL 포함 시 필수)")
    parser.add_argument("--dry-run", action="store_true", help="SQL 출력만, 실행 안 함")
    parser.add_argument("--query", action="store_true", help="현재 DB 세팅 상태 조회")
    args = parser.parse_args()
    args.features = [f.strip() for f in args.features.split(",") if f.strip()]

    if not args.hsp_id:
        print("❌ --hsp-id 필요")
        sys.exit(1)

    conn = connect()
    try:
        if args.query:
            props, dtls, cards, hsp_mst_row = query_hospital(conn, args.hsp_id)
            prop_map = {row[0]: row for row in props}
            dtl_map = {(row[0], row[1]): row for row in dtls}

            member_conn = connect_member()
            member_row = None
            if member_conn:
                try:
                    member_row = query_member(member_conn, args.hsp_id)
                finally:
                    member_conn.close()

            def _prop_active(code):
                r = prop_map.get(code)
                return r is not None and r[2] == "Y"

            def _dtl_active(grp, dtl):
                r = dtl_map.get((grp, dtl))
                return r is not None and r[3] == "Y"

            def _card_status(grp_cd):
                n = cards.get(grp_cd, 0)
                return f"✅ 활성화 (카드 {n}장)" if n > 0 else "❌ 미설정"

            hsptz_info_val = hsp_mst_row[0] if hsp_mst_row else None
            hsptz_info_active = hsptz_info_val == "Y"

            W = 36
            print(f"\n[hsp_id={args.hsp_id}] 현재 세팅 상태\n")
            print("### 기능 활성화 현황")
            print(f"{'기능':<{W}} 상태")
            print("─" * 60)

            # 입원 확인 (member DB)
            if member_row is None and member_conn is None:
                expd_status = "⚠️  member DB 연결 실패"
            elif member_row is None:
                expd_status = "❌ 데이터 없음 (svc_hsp_mst)"
            else:
                expd_status = _yn_status(member_row[0])
            print(f"{'입원 확인':<{W}} {expd_status}")
            print("─" * 60)

            # 입원생활 안내
            if member_row is None and member_conn is None:
                lvg_status = "⚠️  member DB 연결 실패"
            elif member_row is None:
                lvg_status = "❌ 데이터 없음 (svc_hsp_mst)"
            else:
                lvg_status = _yn_status(member_row[1])
            print(f"{'[입원생활 안내]':<{W}} {lvg_status}")
            hsptz_status = "✅ Y" if hsptz_info_active else f"❌ {hsptz_info_val or '미설정'} (hsp_mst)"
            print(f"{'  입원생활 안내 활성화 (skill DB)':<{W}} {hsptz_status}")
            print(f"{'  입원생활 안내 활성화 (member DB)':<{W}} {lvg_status}")

            rows = [
                ("  오늘의 일정",               _prop_active("HSPTLZ_TODAY_SCHEDULE_MENU_YN")),
                ("  주치의 정보보기",             _dtl_active("HSPTZ_LIVING_MYDOCTOR", "HSPTZ_LIVING_MYDOCTOR_INFO")),
            ]
            for name, active in rows:
                status = "✅ 활성화" if active else "❌ 미설정"
                print(f"{name:<{W}} {status}")
            content_rows = [
                ("  입원생활 안내보기 (콘텐츠)", "HSPTLZ_LIVING_GUIDE"),
                ("  편의시설 확인 (콘텐츠)",     "CONVENIENCE_UTILITY"),
                ("  안전생활 안내보기 (콘텐츠)", "HSPTZ_LIVING_SAFETY_MANAGEMENT"),
            ]
            for name, grp_cd in content_rows:
                print(f"{name:<{W}} {_card_status(grp_cd)}")
            print("─" * 60)

            discharge_active = _dtl_active("HSPTZ_LIVING_DISCHARGE", "HSPTZ_LIVING_DISCHARGE_INFO")
            print(f"{'퇴원 안내 활성화':<{W}} {'✅ 활성화' if discharge_active else '❌ 미설정'}")
            print(f"{'퇴원 안내 (콘텐츠)':<{W}} {_card_status('DISCHARGE_GUIDE')}")

            URL_ITEMS = [
                ("입원 사전 안내 URL", "HOSPITALIZATION_PRE_GUIDE_URL"),
                ("주차 안내 URL",      "PARK_GUIDE_URL"),
            ]
            print("\n### 필수 DB 값")
            print(f"{'항목':<22} 값")
            print("─" * 80)
            for label, code in URL_ITEMS:
                row = prop_map.get(code)
                value = row[1] if row else "(미설정)"
                print(f"{label:<22} {value}")
            return

        items = build_items(args.hsp_id, args)
        if not items:
            print("세팅할 항목이 없습니다.")
            return

        # member DB 항목이 있으면 member_conn 준비
        needs_member = any(item["conn_type"] == "member" for item in items)
        member_conn = connect_member() if needs_member else None
        if needs_member and member_conn is None:
            print("❌ member DB 연결이 필요하지만 실패했습니다. .env의 MEMBER_DB_NAME 및 VPN 연결 확인")
            sys.exit(1)

        try:
            def _get_conn(conn_type):
                return member_conn if conn_type == "member" else conn

            existing = {
                item["label"]
                for item in items
                if is_existing(_get_conn(item["conn_type"]), item["ck"])
            }
            if existing:
                print(f"\n⚠️  기존 데이터 발견: {', '.join(existing)} → SKIP 처리됩니다.\n")

            print(f"\n[hsp_id={args.hsp_id}] 세팅 항목 {len(items)}개\n")
            for item in items:
                is_dup = item["label"] in existing
                if is_dup:
                    op = "SKIP (중복)"
                elif args.dry_run:
                    op = "DRY-RUN"
                elif item["ck"][0] in ("hsp_mst", "svc_hsp_mst"):
                    op = "UPDATE"
                else:
                    op = "INSERT"
                print(f"{'─' * 60}")
                print(f"[{op}] {item['label']}")
                print(_fmt_sql(item["sql"], item["params"]) + ";")

            if args.dry_run:
                print("\n" + "─" * 60)
                print("dry-run 완료. 실제 실행: --dry-run 제거 후 재실행")
                return

            inserted = skipped = 0
            for item in items:
                if item["label"] in existing:
                    skipped += 1
                    continue
                c = _get_conn(item["conn_type"])
                with c.cursor() as cur:
                    cur.execute(item["sql"], item["params"])
                inserted += 1

            print(f"\n✅ 세팅 완료 {inserted}건, SKIP {skipped}건")

        finally:
            if member_conn:
                member_conn.close()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
