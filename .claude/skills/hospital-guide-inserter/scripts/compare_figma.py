#!/usr/bin/env python3
"""Figma 디자인 링크 ↔ 병원 톡채널 DB 대조 / UPDATE SQL 생성.

병원안내(hsp_guid_mst_dtl) · 진료안내(hsp_med_guid_mst_dtl) 두 블록의
웹링크(W)를 다룬다. Figma 노드 읽기는 Claude(figma-desktop MCP)가 수행하고,
이 스크립트는 DB 조회와 SQL 생성이라는 결정적 작업만 담당한다.

사용 흐름:
  1) --dump-links  : 현재 DB의 W 링크를 구조화 출력 → Claude가 Figma 값과 대조
  2) --build-sql   : {키: 새 URL} JSON을 받아 UPDATE SQL 생성 (실행 안 함)
                     키는 "카드::버튼"(권장) 또는 "버튼" 단독. 버튼ID가 여러
                     카드에 중복되면(예: 모든 카드 BUTTON_1) 카드까지 WHERE에
                     넣어 정확히 1행만 수정한다.

환경:
  --env dev|prod (기본 dev). dump-links는 prod 조회 허용(읽기). SQL은 텍스트만 생성.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import pymysql
except ImportError as e:
    print(f"[오류] 필수 라이브러리 없음: {e}\n설치: pip install pymysql python-dotenv")
    sys.exit(1)

# 같은 scripts/ 디렉터리의 insert_guide.load_db_config 재사용 (dev/prod .env 로딩 일원화)
sys.path.insert(0, str(Path(__file__).parent))
from insert_guide import load_db_config  # noqa: E402


# 블록별 테이블/컬럼 매핑 ─────────────────────────────────────────────────────
BLOCKS = {
    "hsp_guide": {
        "label": "병원안내",
        "table": "hsp_guid_mst_dtl",
        "card_col": "guid_cd",
        "dtl_col": "guid_dtl_cd",
        "nm_col": "guid_dtl_nm",
        "tp_col": "guid_dtl_link_tp",
        "link_col": "guid_dtl_link",
        "seq_col": "guid_dtl_mak_seq",
        "has_grp": True,
        "default_grp": "HSP_GUIDE",
    },
    "med_guide": {
        "label": "진료안내",
        "table": "hsp_med_guid_mst_dtl",
        "card_col": "med_guid_cd",
        "dtl_col": "med_guid_dtl_cd",
        "nm_col": "med_guid_dtl_nm",
        "tp_col": "med_guid_dtl_link_tp",
        "link_col": "med_guid_dtl_link",
        "seq_col": "med_guid_dtl_mak_seq",
        "has_grp": False,
        "default_grp": None,
    },
}


def fetch_links(cfg, b, hsp_id, grp_cd):
    where = [f"hsp_id = {int(hsp_id)}", f"{b['tp_col']} = 'W'", "use_yn = 'Y'"]
    if b["has_grp"]:
        where.append(f"grp_cd = '{grp_cd}'")
    sql = (
        f"SELECT {b['card_col']} AS card, {b['dtl_col']} AS dtl, {b['nm_col']} AS nm, "
        f"{b['link_col']} AS link FROM {b['table']} "
        f"WHERE {' AND '.join(where)} ORDER BY {b['card_col']}, {b['seq_col']}"
    )
    conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def cmd_dump(args, b):
    cfg = load_db_config(args.env)
    grp = args.grp_cd or b["default_grp"]
    rows = fetch_links(cfg, b, args.hsp_id, grp)
    print(f"[{b['label']}/{b['table']}] hsp_id={args.hsp_id} env={args.env}"
          + (f" grp_cd={grp}" if b["has_grp"] else "") + f" — W 링크 {len(rows)}건\n")
    for r in rows:
        print(f"  {r['card']:<30} {r['dtl']:<12} {str(r['nm']):<18} {r['link']}")
    print("\n[안내] 위 값을 Figma 노드의 버튼별 URL과 대조한 뒤, 변경분을 --build-sql 로 SQL 생성하세요.")
    if rows:
        ex = f"{rows[0]['card']}::{rows[0]['dtl']}"
        print(f"       키는 \"카드::버튼\" 형태 권장. 예: --build-sql '{{\"{ex}\":\"https://...\"}}'")


def cmd_build(args, b):
    try:
        updates = json.loads(args.build_sql)
    except json.JSONDecodeError as e:
        print(f"[오류] --build-sql JSON 파싱 실패: {e}")
        print('  형식 예: \'{"BCARD_03::BUTTON_1":"https://...","BCARD_11::BUTTON_1":"https://..."}\'')
        sys.exit(1)
    if not isinstance(updates, dict) or not updates:
        print("[오류] --build-sql 은 {키: 새 URL} 형태의 비어있지 않은 JSON 이어야 합니다.")
        sys.exit(1)

    grp = args.grp_cd or b["default_grp"]

    # 키를 (카드, 버튼)으로 해석한다. guid_dtl_cd 가 카드마다 중복될 수 있어
    # (예: 모든 카드 BUTTON_1) 카드(card_col)까지 WHERE 에 넣어야 1행만 수정된다.
    # 모호하거나 존재하지 않는 키는 잘못된 SQL 대신 에러로 막는다.
    cfg = load_db_config(args.env)
    rows = fetch_links(cfg, b, args.hsp_id, grp)

    resolved = []   # (card, dtl, url)
    errors = []
    for key, url in updates.items():
        if "::" in key:
            card, dtl = key.split("::", 1)
        else:
            card, dtl = None, key
        matches = [r for r in rows if r["dtl"] == dtl and (card is None or r["card"] == card)]
        cards = sorted({r["card"] for r in matches})
        if not matches:
            errors.append(
                f"  키 '{key}' 에 해당하는 W 링크 행이 없습니다 "
                f"(hsp_id={args.hsp_id}" + (f", grp_cd={grp}" if b["has_grp"] else "") + ")."
            )
            continue
        if card is None and len(cards) > 1:
            errors.append(
                f"  '{dtl}' 가 {len(cards)}개 카드에 중복됩니다 → {', '.join(cards)}\n"
                f"      카드를 지정하세요: \"<카드>::{dtl}\" (예: \"{cards[0]}::{dtl}\")"
            )
            continue
        resolved.append((cards[0], dtl, url))

    if errors:
        print("[오류] --build-sql 키를 해석할 수 없습니다:")
        for e in errors:
            print(e)
        print("\n  현재 W 링크 목록은 --dump-links 로 확인하세요.")
        sys.exit(1)

    note = f" / grp_cd='{grp}'" if b["has_grp"] else ""
    print("-- =========================================================")
    print(f"-- {b['label']} ({b['table']}) 웹링크 UPDATE  — hsp_id={args.hsp_id}{note}")
    print(f"-- 대상 환경: {args.env}  / 변경 {len(resolved)}건")
    if args.note:
        print(f"-- ⚠️ {args.note}")
    print("-- 이 스크립트는 SQL만 생성합니다. 실행은 DataGrip 등에서 직접 수행하세요.")
    print("-- =========================================================")
    print("START TRANSACTION;\n")
    for card, dtl, url in resolved:
        safe_url = str(url).replace("'", "''")
        cond = [f"hsp_id = {int(args.hsp_id)}"]
        if b["has_grp"]:
            cond.append(f"grp_cd = '{grp}'")
        cond.append(f"{b['card_col']} = '{card}'")
        cond.append(f"{b['dtl_col']} = '{dtl}'")
        cond.append(f"{b['tp_col']} = 'W'")
        print(f"UPDATE {b['table']}")
        print(f"SET {b['link_col']} = '{safe_url}',")
        print("    lst_mdf_dtm = NOW()")
        print(f"WHERE {' AND '.join(cond)};\n")

    sel_where = [f"hsp_id = {int(args.hsp_id)}", f"{b['tp_col']} = 'W'"]
    if b["has_grp"]:
        sel_where.append(f"grp_cd = '{grp}'")
    print("-- 검증")
    print(f"SELECT {b['card_col']}, {b['dtl_col']}, {b['nm_col']}, {b['link_col']}")
    print(f"FROM {b['table']} WHERE {' AND '.join(sel_where)} ORDER BY {b['card_col']}, {b['seq_col']};")
    print("\n-- 이상 없으면 COMMIT, 아니면 ROLLBACK")
    print("-- COMMIT;\n-- ROLLBACK;")


def main():
    p = argparse.ArgumentParser(description="Figma 링크 ↔ 병원 톡채널 DB 대조/UPDATE SQL 생성")
    p.add_argument("--block", required=True, choices=list(BLOCKS.keys()),
                   help="대상 블록: hsp_guide(병원안내) | med_guide(진료안내)")
    p.add_argument("--hsp-id", type=int, required=True, help="병원 DB ID")
    p.add_argument("--env", default="dev", choices=["dev", "prod"], help="대상 환경 (기본 dev)")
    p.add_argument("--grp-cd", help="hsp_guide 전용 grp_cd (기본값 HSP_GUIDE)")
    p.add_argument("--dump-links", action="store_true", help="현재 DB W 링크 출력")
    p.add_argument("--build-sql", metavar="JSON",
                   help='{"카드::버튼": 새 URL} JSON → UPDATE SQL 생성 (버튼 단독 키도 가능, 중복 시 카드 필수)')
    p.add_argument("--note", help="생성 SQL 상단에 넣을 주의 메모 (예: 2026-07-01 개편과 동시 반영)")
    args = p.parse_args()

    b = BLOCKS[args.block]
    if args.dump_links:
        cmd_dump(args, b)
    elif args.build_sql:
        cmd_build(args, b)
    else:
        print("[오류] --dump-links 또는 --build-sql 중 하나가 필요합니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
