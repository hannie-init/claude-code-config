#!/usr/bin/env python3
"""
병원 안내 콘텐츠 엑셀 → MySQL INSERT 스크립트

Usage:
  # 구글 시트(.env의 GOOGLE_SHEETS_URL 사용)
  python insert_guide.py --grp-cd HSPTLZ_LIVING_GUIDE --list-hospitals
  python insert_guide.py --grp-cd DISCHARGE_GUIDE --hospital-index N --hsp-id ID [--block-ids '{"C":"BLK_001"}'] [--dry-run]

  # 로컬 엑셀/TSV 파일 사용
  python insert_guide.py <엑셀경로> --grp-cd CONVENIENCE_UTILITY --list-hospitals
  python insert_guide.py <엑셀경로> --grp-cd HSPTZ_LIVING_SAFETY_MANAGEMENT --hospital-index N --hsp-id ID [--dry-run]

  # DB 조회
  python insert_guide.py --query --grp-cd HSPTLZ_LIVING_GUIDE --hsp-id ID
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import pymysql
    from dotenv import load_dotenv
    import os
except ImportError as e:
    print(f"[오류] 필수 라이브러리 없음: {e}")
    print("설치: pip install pymysql python-dotenv")
    sys.exit(1)


SKILL_DIR = Path(__file__).parent.parent
ENV_FILE = SKILL_DIR / ".env"

load_dotenv(ENV_FILE)

GRP_CONFIGS = {
    "DISCHARGE_GUIDE":                "퇴원 안내",
    "HSPTLZ_LIVING_GUIDE":            "입원 생활 안내",
    "CONVENIENCE_UTILITY":            "편의 시설 확인",
    "HSPTZ_LIVING_SAFETY_MANAGEMENT": "안전 생활 알아보기",
}


# ── DB 설정 ─────────────────────────────────────────────────────────────────

def load_db_config(env="dev"):
    """환경(dev/prod)별 DB 설정 로드.

    단일 .env에서 접두어로 환경을 구분한다.
      - dev:  DEV_DB_*  (없으면 무접두어 DB_* 로 폴백 → 기존 .env 호환)
      - prod: PROD_DB_* (폴백 없음 — 운영 자격증명은 명시 필수)
    """
    env = (env or "dev").lower()
    prefix = f"{env.upper()}_"  # DEV_ / PROD_

    def pick(key):
        val = os.getenv(prefix + key)
        if val is None and env == "dev":
            val = os.getenv(key)  # 기존 무접두어 .env 호환
        return val

    config = {
        "host": pick("DB_HOST") or "localhost",
        "port": int(pick("DB_PORT") or "3306"),
        "db": pick("DB_NAME"),
        "user": pick("DB_USER"),
        "password": pick("DB_PASSWORD"),
        "charset": "utf8mb4",
    }
    if not config["db"] or not config["user"]:
        print(f"[오류] '{env}' 환경 DB 설정이 없습니다. .env에 {prefix}DB_NAME / {prefix}DB_USER 를 설정하세요.")
        print(f"위치: {ENV_FILE}")
        print(f".env.example을 참고해 .env 파일을 생성해 주세요.")
        sys.exit(1)
    return config


# ── 데이터 소스 로딩 ─────────────────────────────────────────────────────────

class _Cell:
    """gspread 값을 openpyxl Cell처럼 감싸는 래퍼."""
    def __init__(self, value):
        self.value = value


def load_from_tsv(path):
    """탭 구분 텍스트 파일(구글 시트 복사/붙여넣기) 파싱."""
    import csv
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            rows_raw = list(reader)
    except Exception as e:
        print(f"[오류] TSV 파일 읽기 실패: {e}")
        sys.exit(1)
    return [[_Cell(v) for v in row] for row in rows_raw]


def load_from_excel(path):
    try:
        import openpyxl
    except ImportError:
        print("[오류] openpyxl이 설치되지 않았습니다.")
        print("설치: pip install openpyxl")
        sys.exit(1)

    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
    except Exception as e:
        print(f"[오류] 엑셀 열기 실패: {e}")
        sys.exit(1)

    return list(ws.iter_rows())


def _open_google_sheet(spreadsheet_id, gid, credentials_path):
    """gspread 클라이언트로 워크시트를 열어 반환.

    인증 우선순위:
      1. gspread OAuth (Desktop App) — ~/.config/gspread/credentials.json
      2. Service Account JSON — GOOGLE_CREDENTIALS_PATH
    """
    try:
        import gspread
    except ImportError:
        print("[오류] gspread가 설치되지 않았습니다.")
        print("설치: pip install gspread google-auth")
        sys.exit(1)

    gc = None

    # 1순위: gspread OAuth Desktop App (~/.config/gspread/credentials.json)
    oauth_creds_path = Path.home() / ".config" / "gspread" / "credentials.json"
    if oauth_creds_path.exists():
        try:
            gc = gspread.oauth()
        except Exception as e:
            print(f"[경고] gspread OAuth 실패: {e}")

    # 2순위: Service Account JSON (GOOGLE_CREDENTIALS_PATH)
    if gc is None:
        if not credentials_path or not Path(credentials_path).exists():
            print("[오류] 구글 인증 정보가 없습니다.")
            print()
            print("  [권장] gspread OAuth Desktop App 방식:")
            print("  1. https://console.cloud.google.com/apis/credentials 접속")
            print("  2. 'Create Credentials' → 'OAuth client ID' → 'Desktop app' 선택")
            print("  3. JSON 다운로드 후 저장: ~/.config/gspread/credentials.json")
            print("  4. 스크립트 재실행 시 브라우저에서 구글 계정 로그인 (최초 1회)")
            print()
            print("  [대안] .env에 GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json 설정")
            sys.exit(1)
        try:
            from google.oauth2.service_account import Credentials
            sa_scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = Credentials.from_service_account_file(credentials_path, scopes=sa_scopes)
            gc = gspread.authorize(creds)
        except Exception as e:
            print(f"[오류] Service Account 인증 실패: {e}")
            sys.exit(1)

    try:
        sh = gc.open_by_key(spreadsheet_id)
        for sheet in sh.worksheets():
            if sheet.id == gid:
                return sheet
        return sh.sheet1
    except Exception as e:
        print(f"[오류] 구글 시트 열기 실패: {e}")
        sys.exit(1)


def load_from_google_sheets(url, credentials_path):
    m = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not m:
        print(f"[오류] 유효한 구글 스프레드시트 URL이 아닙니다: {url}")
        sys.exit(1)
    spreadsheet_id = m.group(1)
    gid_match = re.search(r"gid=(\d+)", url)
    gid = int(gid_match.group(1)) if gid_match else 0

    ws = _open_google_sheet(spreadsheet_id, gid, credentials_path)
    try:
        rows_raw = ws.get_all_values()
    except Exception as e:
        print(f"[오류] 구글 시트 읽기 실패: {e}")
        sys.exit(1)

    return [[_Cell(v) for v in row] for row in rows_raw]


def load_data_source(excel_path_arg):
    """파일 경로(xlsx/tsv/txt) 또는 .env의 GOOGLE_SHEETS_URL로 데이터 로딩."""
    if excel_path_arg:
        path = Path(excel_path_arg)
        if not path.exists():
            print(f"[오류] 파일 없음: {path}")
            sys.exit(1)
        if path.suffix.lower() in (".tsv", ".txt", ".tab"):
            return load_from_tsv(path)
        return load_from_excel(path)

    sheets_url = os.getenv("GOOGLE_SHEETS_URL")
    if sheets_url:
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        print(f"[정보] 구글 시트에서 데이터를 읽습니다...")
        return load_from_google_sheets(sheets_url, credentials_path)

    print("[오류] 파일 경로(.xlsx/.tsv)를 인자로 전달하거나 .env에 GOOGLE_SHEETS_URL을 설정해 주세요.")
    sys.exit(1)


# ── 엑셀 파싱 ────────────────────────────────────────────────────────────────

def cell_value(cell):
    v = cell.value
    if v is None:
        return ""
    return str(v).strip()


def parse_hospitals(rows):
    """워크시트 rows에서 병원 블록(3행씩) 목록을 파싱."""
    hospitals = []

    i = 0
    while i < len(rows):
        row = rows[i]
        hospital_name = cell_value(row[0]) if row else ""

        if hospital_name in ("", "병원", "기획안"):
            i += 1
            continue

        if i + 2 >= len(rows):
            i += 1
            continue

        content_row = rows[i]
        button_row = rows[i + 1]

        # C열(index 2)부터 L열(index 11)까지 카드 파싱 (최대 10장)
        cards = []
        col_letters = ["C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
        for col_idx, col_letter in enumerate(col_letters, start=2):
            if col_idx >= len(content_row):
                break
            content = cell_value(content_row[col_idx])
            if not content:
                continue

            button_cell = cell_value(button_row[col_idx]) if col_idx < len(button_row) else ""
            button_info = parse_button(button_cell, col_letter)

            cards.append({
                "col_letter": col_letter,
                "seq": len(cards) + 1,
                "guid_desc": content,
                "button": button_info,
            })

        if cards:
            hospitals.append({
                "name": hospital_name,
                "cards": cards,
                "row_start": i + 1,
            })

        i += 3

    return hospitals


def parse_button(cell_text, col_letter):
    """버튼 셀 텍스트를 파싱해 버튼 정보 딕셔너리 반환.

    타입:
      W = 웹 링크 (http로 시작)
      B = 블록 호출 ('블록 호출' 또는 'block' 포함)
      M = 사용자 발화 메세지 (나머지 텍스트)
    """
    if not cell_text or cell_text.strip() in ("-", ""):
        return None

    name_match = re.search(r'\[([^\]]+)\]', cell_text)
    btn_name = name_match.group(1) if name_match else cell_text.split("\n")[0].strip()

    lines = cell_text.split("\n")
    link_line = ""
    for line in lines[1:]:
        stripped = line.strip()
        if stripped:
            link_line = stripped
            break

    if link_line.startswith("http"):
        return {"name": btn_name, "type": "W", "link": link_line, "col": col_letter}
    elif "블록 호출" in link_line or "block" in link_line.lower():
        return {"name": btn_name, "type": "B", "link": None, "col": col_letter}
    elif link_line:
        return {"name": btn_name, "type": "M", "link": link_line, "col": col_letter}

    return None


# ── SQL 생성 및 INSERT ───────────────────────────────────────────────────────

def build_sqls(hsp_id, hospital, block_ids, grp_cd):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sqls = []
    warnings = []

    for card in hospital["cards"]:
        seq = card["seq"]
        guid_cd = f"{grp_cd}_BCARD_{seq:02d}"
        desc = card["guid_desc"].replace("'", "''")

        mst_sql = (
            f"INSERT INTO hsp_guid_mst "
            f"(hsp_id, guid_cd, grp_cd, guid_tile, guid_desc, guid_mak_seq, "
            f"guid_img_path, hsp_loc_guid_yn, sub_card_yn, use_yn, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id) "
            f"VALUES "
            f"({hsp_id}, '{guid_cd}', '{grp_cd}', NULL, '{desc}', {seq}, "
            f"NULL, NULL, NULL, 'Y', '{now}', 0, '{now}', 0);"
        )
        sqls.append(("mst", guid_cd, mst_sql))

        btn = card["button"]
        if btn:
            link_tp = btn["type"]
            link_val = btn["link"]

            if link_tp == "B":
                col = btn["col"]
                if block_ids and col in block_ids:
                    link_val = block_ids[col]
                else:
                    warnings.append(
                        f"  ⚠️  카드 {seq}({guid_cd}) 버튼이 B타입인데 블록 ID가 없습니다. "
                        f"--block-ids '{{\"{ col }\":\"블록ID\"}}' 로 지정해 주세요."
                    )
                    link_val = "BLOCK_ID_REQUIRED"

            link_val_escaped = (link_val or "").replace("'", "''")
            btn_name_escaped = btn["name"].replace("'", "''")

            dtl_sql = (
                f"INSERT INTO hsp_guid_mst_dtl "
                f"(hsp_id, guid_cd, guid_dtl_cd, grp_cd, guid_dtl_nm, guid_dtl_mak_seq, "
                f"guid_dtl_link_tp, guid_dtl_link, use_yn, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id) "
                f"VALUES "
                f"({hsp_id}, '{guid_cd}', 'BUTTON_1', '{grp_cd}', '{btn_name_escaped}', 1, "
                f"'{link_tp}', '{link_val_escaped}', 'Y', '{now}', 0, '{now}', 0);"
            )
            sqls.append(("dtl", guid_cd, dtl_sql))

    return sqls, warnings


def check_existing(conn, hsp_id, hospital, grp_cd):
    cursor = conn.cursor()
    existing = []
    for card in hospital["cards"]:
        guid_cd = f"{grp_cd}_BCARD_{card['seq']:02d}"
        cursor.execute(
            "SELECT COUNT(*) FROM hsp_guid_mst WHERE hsp_id = %s AND guid_cd = %s",
            (hsp_id, guid_cd)
        )
        count = cursor.fetchone()[0]
        if count > 0:
            existing.append(guid_cd)
    cursor.close()
    return existing


# ── 조회 기능 ────────────────────────────────────────────────────────────────

def query_hospital(conn, hsp_id, grp_cd):
    import unicodedata, re

    def dw(s):
        s = str(s)
        # 피부색 수정자(🏻-🏿), variation selector, ZWJ+다음글자 제거 후 폭 계산
        s = re.sub(r'[\U0001F3FB-\U0001F3FF\uFE00-\uFE0F]', '', s)
        s = re.sub(r'\u200D.', '', s)
        return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)

    def pad(s, width):
        s = str(s)
        return s + " " * max(0, width - dw(s))

    label = GRP_CONFIGS.get(grp_cd, grp_cd)

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.guid_cd, m.guid_desc, m.guid_mak_seq,
               d.guid_dtl_nm, d.guid_dtl_link_tp, d.guid_dtl_link
        FROM hsp_guid_mst m
        LEFT JOIN hsp_guid_mst_dtl d
               ON m.hsp_id = d.hsp_id AND m.guid_cd = d.guid_cd
        WHERE m.hsp_id = %s AND m.grp_cd = %s AND m.use_yn = 'Y'
        ORDER BY m.guid_mak_seq
        """,
        (hsp_id, grp_cd)
    )
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        print(f"\n[정보] hsp_id={hsp_id}의 {label} 데이터가 없습니다.\n")
        return

    headers = ["guid_cd", "seq", "guid_desc", "guid_dtl_nm", "guid_dtl_link_tp", "guid_dtl_link"]
    col_data = []
    type_counts = {"W": 0, "M": 0, "B": 0}

    for guid_cd, guid_desc, seq, btn_name, link_tp, link_val in rows:
        short_cd = (guid_cd or "").replace(f"{grp_cd}_", "")
        desc_str = (guid_desc or "").replace("\n", " ")
        desc_preview = desc_str[:20] + ("..." if len(desc_str) > 20 else "")
        col_data.append([
            short_cd,
            str(seq) if seq is not None else "",
            desc_preview,
            btn_name or "",
            link_tp or "",
            link_val or "",
        ])
        if link_tp in type_counts:
            type_counts[link_tp] += 1

    col_widths = [
        max(dw(h), max((dw(r[i]) for r in col_data), default=0))
        for i, h in enumerate(headers)
    ]

    def top():  return "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    def mid():  return "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    def bot():  return "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    def row(cells): return "│ " + " │ ".join(pad(c, w) for c, w in zip(cells, col_widths)) + " │"

    print(f"\n=== hsp_id={hsp_id} {label} 현황 ===\n")
    print(top())
    print(row(headers))
    for r_data in col_data:
        print(mid())
        print(row(r_data))
    print(bot())

    total_cards = len(rows)
    total_btns = sum(type_counts.values())
    print(f"\n총 {total_cards}개 카드, 버튼 {total_btns}개 "
          f"(W:{type_counts['W']}, M:{type_counts['M']}, B:{type_counts['B']})")
    print()


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="병원 안내 콘텐츠 엑셀 → MySQL INSERT")
    parser.add_argument("excel_path", nargs="?", help="엑셀 파일 경로 (생략 시 .env의 GOOGLE_SHEETS_URL 사용)")
    parser.add_argument(
        "--grp-cd",
        default="DISCHARGE_GUIDE",
        choices=list(GRP_CONFIGS.keys()),
        help="콘텐츠 그룹 코드 (기본값: DISCHARGE_GUIDE)",
    )
    parser.add_argument("--list-hospitals", action="store_true", help="병원 목록만 출력")
    parser.add_argument("--hospital-index", type=int, help="처리할 병원 번호 (1부터)")
    parser.add_argument("--hsp-id", type=int, help="병원 DB ID")
    parser.add_argument("--block-ids", type=str, help='B타입 버튼 블록 ID JSON. 예: \'{"C":"BLK_001"}\'')
    parser.add_argument("--dry-run", action="store_true", help="SQL만 출력, DB 미실행")
    parser.add_argument("--query", action="store_true", help="특정 hsp_id의 안내 현황 조회")
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "stg", "prod"],
        help="대상 환경 (기본값: dev). stg는 dev처럼 쓰기 허용, prod는 조회(--query) 전용 — 쓰기 작업 차단",
    )
    args = parser.parse_args()

    grp_cd = args.grp_cd
    label = GRP_CONFIGS[grp_cd]

    # 조회 모드 (엑셀 파싱 불필요)
    if args.query:
        if not args.hsp_id:
            print("[오류] --query 사용 시 --hsp-id가 필요합니다.")
            sys.exit(1)
        db_config = load_db_config(args.env)
        try:
            conn = pymysql.connect(**db_config)
        except Exception as e:
            print(f"[오류] DB 연결 실패: {e}")
            sys.exit(1)
        try:
            query_hospital(conn, args.hsp_id, grp_cd)
        finally:
            conn.close()
        return

    # prod 안전장치: 운영 환경은 조회(--query) 전용, 쓰기 작업 차단
    if args.env == "prod":
        print("[차단] prod 환경은 조회 전용입니다. (--query 만 허용)")
        print("       운영 DB INSERT/UPDATE는 DataGrip 등에서 직접 수행하세요.")
        sys.exit(1)

    # 데이터 소스 로딩 (엑셀 or 구글 시트)
    rows = load_data_source(args.excel_path)
    hospitals = parse_hospitals(rows)

    if not hospitals:
        print("[오류] 엑셀에서 병원 데이터를 찾을 수 없습니다.")
        sys.exit(1)

    # 병원 목록 출력 모드
    if args.list_hospitals:
        print(f"\n[{label}] 총 {len(hospitals)}개 병원:")
        for i, h in enumerate(hospitals, 1):
            card_count = len(h["cards"])
            btn_count = sum(1 for c in h["cards"] if c["button"])
            b_type = sum(1 for c in h["cards"] if c["button"] and c["button"]["type"] == "B")
            b_note = f" (B타입 버튼 {b_type}개 - 블록ID 필요)" if b_type else ""
            print(f"  {i}. {h['name']} - 카드 {card_count}장, 버튼 {btn_count}개{b_note}")
        print()
        return

    # INSERT 모드
    if not args.hospital_index or not args.hsp_id:
        print("[오류] --hospital-index 와 --hsp-id 가 필요합니다.")
        print("먼저 --list-hospitals 로 병원 목록을 확인하세요.")
        sys.exit(1)

    idx = args.hospital_index - 1
    if idx < 0 or idx >= len(hospitals):
        print(f"[오류] 병원 번호 {args.hospital_index}이 범위를 벗어납니다. (1~{len(hospitals)})")
        sys.exit(1)

    hospital = hospitals[idx]
    hsp_id = args.hsp_id

    try:
        block_ids = json.loads(args.block_ids) if args.block_ids else {}
    except json.JSONDecodeError as e:
        print(f"[오류] --block-ids JSON 파싱 실패: {e}")
        print(f"  입력값: {args.block_ids}")
        print(f"  올바른 형식 예: '{{\"C\":\"BLK_001\",\"D\":\"BLK_002\"}}'")
        sys.exit(1)

    print(f"\n[{label}] 대상 병원: {hospital['name']}")
    print(f"hsp_id: {hsp_id}")
    print(f"카드 수: {len(hospital['cards'])}장")
    print()

    sqls, warnings = build_sqls(hsp_id, hospital, block_ids, grp_cd)

    if warnings:
        print("=== 경고 ===")
        for w in warnings:
            print(w)
        print()

    print("=== 생성된 SQL ===")
    for _, guid_cd, sql in sqls:
        print(f"\n-- {guid_cd}")
        print(sql)
    print()

    if args.dry_run:
        print("[dry-run] SQL 미리보기만 출력했습니다. 실제 INSERT 없음.")
        return

    if any("BLOCK_ID_REQUIRED" in sql for _, _, sql in sqls):
        print("[오류] 블록 ID가 필요한 버튼이 있습니다. --block-ids 옵션으로 지정 후 재실행하세요.")
        sys.exit(1)

    db_config = load_db_config(args.env)
    try:
        conn = pymysql.connect(**db_config)
    except Exception as e:
        print(f"[오류] DB 연결 실패: {e}")
        sys.exit(1)

    try:
        existing = check_existing(conn, hsp_id, hospital, grp_cd)
        if existing:
            print(f"⚠️  기존 데이터 발견: hsp_id={hsp_id}, guid_cd={existing}")
            print("    중복 INSERT 시 Primary Key 오류가 발생합니다.")
            print("    기존 데이터를 삭제하려면 DataGrip에서 직접 삭제 후 재실행하세요.")
            sys.exit(1)

        cursor = conn.cursor()
        inserted = 0
        for _, guid_cd, sql in sqls:
            cursor.execute(sql)
            inserted += 1

        conn.commit()
        print(f"✅ INSERT 완료: {inserted}건")

    except Exception as e:
        conn.rollback()
        print(f"[오류] INSERT 실패 (롤백 완료): {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
