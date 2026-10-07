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
    # 입원/퇴원 동의 데이터 (stte_ccrc + stte_ccrc_cnte + dtl_mst)
    "CONSENT_HSPTLZ",
    # 입원 확인 상세
    "DETAIL_INFO",
    # 기타 기능 플래그
    "DIET", "REMOTE_CONSULT", "CERTIFICATES",
    "MEMBER_ARRIVAL", "MEMBER_HOPE_ROOM", "MEMBER_CONSENT_FORM",
]

# ── 입원/퇴원 동의 데이터 상수 ──────────────────────────────────────────
# stte_ccrc_id=81 은 HSPTZ_LVNG_CCRC_ITEM(개인정보 제3자 제공 동의-입원/퇴원)의
# 고정 상수다(전 병원 공통). 예시값이 아니다.
CONSENT_STTE_CCRC_ID = 81
CONSENT_GRP_CD = "HSPTZ_LVNG_CCRC_ITEM"
CONSENT_DTL_CD = "HSPTZ_LVNG_CCRC_ITEM_01"
CONSENT_TITLE = "개인정보 제3자 제공 동의"
CONSENT_HDR_TMPL = ("{hsp_nm}은 (주)카카오헬스케어에서 제공하는 서비스 이용을 위한 목적으로만 "
                    "개인정보를 제공하며, 본래의 목적 범위를 초과하여 제3자에게 제공 및 처리하지 않습니다.")
CONSENT_FOOTER = "본 동의는 거부할 수 있으며, 거부 시 서비스 이용이 제한될 수 있습니다."
# CCRC_FOOTER_INFO('동의 전문 보기') 링크 — 기존 병원 행에서 복사, 없으면 이 기본값(dev) 사용
DEFAULT_CCRC_DTL_URL = ("https://karechat-common-dev.kakaohealthcare.com"
                        "/myMenu/myInfo/ccrcManagement/privacyInfo/ccrcDtl")

# 동의 상세 내용 8행: (cnte_cd, ccrc_scrn, cnte_mak_seq, cnte_key, cnte_value)
_V_PURPOSE = "케어챗을 통한 입∙퇴원 정보 조회, 편의 서비스 제공"
_V_PROVIDER = "(주)카카오헬스케어"
_V_ITEMS = "이름, 휴대전화번호, 입원일시, 진료과, 주치의, 병동/병실, 입원비, 식단"
_V_PERIOD = "서비스 내 게시 직후 파기"
CONSENT_CNTE = [
    (f"{CONSENT_DTL_CD}_01", "CCRC", 1, "동의 목적", _V_PURPOSE),
    (f"{CONSENT_DTL_CD}_02", "CCRC", 2, "제공 받는 자", _V_PROVIDER),
    (f"{CONSENT_DTL_CD}_03", "CCRC", 3, "개인정보 항목", _V_ITEMS),
    (f"{CONSENT_DTL_CD}_04", "CCRC", 4, "제공받는 자의 보유 및 이용 기간", _V_PERIOD),
    (f"{CONSENT_DTL_CD}_01", "PTCFM", 1, "제공 받는 자", _V_PROVIDER),
    (f"{CONSENT_DTL_CD}_02", "PTCFM", 2, "제공 항목", _V_ITEMS),
    (f"{CONSENT_DTL_CD}_03", "PTCFM", 3, "제공받는 자의 이용 목적", _V_PURPOSE),
    (f"{CONSENT_DTL_CD}_04", "PTCFM", 4, "제공받는 자의 보유 및 이용 기간", _V_PERIOD),
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


def _dtl_mst_row(hsp_id: int, grp_cd: str, dtl_cd: str, dtl_cd_nm: str,
                 dtl_expl: str = None, seq: int = 1):
    sql = (
        "INSERT INTO dtl_mst"
        " (hsp_id, grp_cd, dtl_cd, dtl_cd_nm, dtl_expl, dtl_cd_seq, use_yn, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id)\n"
        "VALUES (%s, %s, %s, %s, %s, %s, 'Y', NOW(), 0, NOW(), 0)"
    )
    return sql, (hsp_id, grp_cd, dtl_cd, dtl_cd_nm, dtl_expl, seq)


def _hsp_mst_update(hsp_id: int, cols: dict):
    """hsp_mst 의 여러 컬럼을 한 번에 UPDATE. cols = {컬럼명: 값}"""
    set_clause = ", ".join(f"{c} = %s" for c in cols)
    sql = f"UPDATE hsp_mst SET {set_clause} WHERE hsp_id = %s"
    return sql, (*cols.values(), hsp_id)


def _svc_hsp_mst_update(hsp_id: int, col: str):
    sql = f"UPDATE svc_hsp_mst SET {col} = 'Y' WHERE hsp_id = %s"
    return sql, (hsp_id,)


def _stte_ccrc_row(hsp_id: int, hdr: str):
    sql = (
        "INSERT INTO stte_ccrc"
        " (stte_ccrc_id, hsp_id, grp_cd, dtl_cd, essn_yn, ccrc_scrn, stte_ccrc_title,"
        " stte_ccrc_hdr, stte_ccrc_footer, ccrc_dsp_yn, ccrc_dtl_yn, ver_no, use_yn,"
        " use_str_dt, use_end_dt, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id)\n"
        "VALUES (%s, %s, %s, %s, 'Y', 'PTCFM', %s, %s, %s, 'Y', 'Y', '1.0', 'Y',"
        " CURDATE(), '2099-12-01', NOW(), 0, NOW(), 0)"
    )
    return sql, (CONSENT_STTE_CCRC_ID, hsp_id, CONSENT_GRP_CD, CONSENT_DTL_CD,
                 CONSENT_TITLE, hdr, CONSENT_FOOTER)


def _stte_ccrc_cnte_row(hsp_id: int, cnte_cd: str, scrn: str, seq: int, key: str, value: str):
    sql = (
        "INSERT INTO stte_ccrc_cnte"
        " (stte_ccrc_id, hsp_id, stte_ccrc_cnte_cd, ccrc_scrn, cnte_mak_seq, cnte_key,"
        " cnte_value, ver_no, use_yn, use_str_dt, use_end_dt, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id)\n"
        "VALUES (%s, %s, %s, %s, %s, %s, %s, '1.0', 'Y', CURDATE(), '2099-12-01', NOW(), 0, NOW(), 0)"
    )
    return sql, (CONSENT_STTE_CCRC_ID, hsp_id, cnte_cd, scrn, seq, key, value)


def _consent_items(hsp_id: int, conn, args) -> list:
    """입원/퇴원 동의 데이터 11행(stte_ccrc 1 + stte_ccrc_cnte 8 + dtl_mst 2)을 item 리스트로 생성."""
    items = []

    # 병원명 (stte_ccrc_hdr 치환용)
    with conn.cursor() as cur:
        cur.execute("SELECT hsp_nm FROM hsp_mst WHERE hsp_id=%s", (hsp_id,))
        row = cur.fetchone()
    if not row:
        print(f"❌ hsp_id={hsp_id} 병원을 hsp_mst 에서 찾을 수 없습니다.")
        sys.exit(1)
    hsp_nm = row[0]
    hdr = CONSENT_HDR_TMPL.format(hsp_nm=hsp_nm)

    # '동의 전문 보기' URL: 기존 병원 CCRC_FOOTER_INFO 행에서 복사 → args → 기본값(dev)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT dtl_expl FROM dtl_mst"
            " WHERE hsp_id=%s AND grp_cd='CCRC_FOOTER_INFO' AND dtl_expl LIKE 'http%%' LIMIT 1",
            (hsp_id,),
        )
        r = cur.fetchone()
    footer_url = (r[0] if r else None) or getattr(args, "ccrc_dtl_url", None) or DEFAULT_CCRC_DTL_URL
    if not r and not getattr(args, "ccrc_dtl_url", None):
        print(f"⚠️  기존 CCRC_FOOTER_INFO URL을 찾지 못해 기본값(dev)을 사용합니다. 운영 반영 시 --ccrc-dtl-url 로 지정하세요.\n    → {footer_url}")

    # CCRC_ITEM_MGMT 목록 seq: 기존 항목 최대 seq + 1 (없으면 3 = SELF_01/02 다음)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(dtl_cd_seq), 2) + 1 FROM dtl_mst"
            " WHERE hsp_id=%s AND grp_cd='CCRC_ITEM_MGMT'",
            (hsp_id,),
        )
        mgmt_seq = cur.fetchone()[0]

    # 1) stte_ccrc (정의)
    sql, params = _stte_ccrc_row(hsp_id, hdr)
    items.append({"label": "동의 정의 (stte_ccrc)", "sql": sql, "params": params,
                  "ck": ("stte_ccrc", hsp_id), "conn_type": "skill"})

    # 2) stte_ccrc_cnte (상세 내용 8행)
    for cnte_cd, scrn, seq, key, value in CONSENT_CNTE:
        sql, params = _stte_ccrc_cnte_row(hsp_id, cnte_cd, scrn, seq, key, value)
        items.append({"label": f"동의 내용 {scrn}/{seq} ({key})", "sql": sql, "params": params,
                      "ck": ("stte_ccrc_cnte", hsp_id, cnte_cd, scrn), "conn_type": "skill"})

    # 3) dtl_mst — 목록 노출용
    sql, params = _dtl_mst_row(hsp_id, "CCRC_ITEM_MGMT", CONSENT_DTL_CD,
                               CONSENT_TITLE, "입원/퇴원", mgmt_seq)
    items.append({"label": "동의 목록노출 (dtl_mst/CCRC_ITEM_MGMT)", "sql": sql, "params": params,
                  "ck": ("dtl_mst", hsp_id, "CCRC_ITEM_MGMT", CONSENT_DTL_CD), "conn_type": "skill"})

    # 4) dtl_mst — '동의 전문 보기' 링크
    sql, params = _dtl_mst_row(hsp_id, "CCRC_FOOTER_INFO", CONSENT_DTL_CD,
                               "동의 전문 보기", footer_url, 1)
    items.append({"label": "동의 전문보기 (dtl_mst/CCRC_FOOTER_INFO)", "sql": sql, "params": params,
                  "ck": ("dtl_mst", hsp_id, "CCRC_FOOTER_INFO", CONSENT_DTL_CD), "conn_type": "skill"})

    return items


def build_items(hsp_id: int, args, conn) -> list:
    items = []

    if "HSP_MST_INFO" in args.features:
        sql, params = _hsp_mst_update(hsp_id, {"hsptz_info": "Y"})
        items.append({"label": "입원생활 안내 활성화 (hsp_mst)", "sql": sql, "params": params,
                      "ck": ("hsp_mst", hsp_id, "hsptz_info"), "conn_type": "skill"})

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

    # ── A. 입원/퇴원 동의 데이터 ──
    if "CONSENT_HSPTLZ" in args.features:
        items.extend(_consent_items(hsp_id, conn, args))

    # ── B. 입원 정보 상세 확인 (hsptlz_detail_info_yn + bed_tp='DAY') ──
    if "DETAIL_INFO" in args.features:
        sql, params = _hsp_mst_update(hsp_id, {"hsptlz_detail_info_yn": "Y", "bed_tp": "DAY"})
        items.append({"label": "입원 정보 상세 확인 (hsp_mst: detail_info + bed_tp=DAY)", "sql": sql, "params": params,
                      "ck": ("hsp_mst", hsp_id, "hsptlz_detail_info_yn"), "conn_type": "skill"})

    # ── C. 기타 기능 플래그 ──
    if "DIET" in args.features:
        sql, params = _hsp_mst_update(hsp_id, {"diet_use_yn": "Y"})
        items.append({"label": "식단 관리 (hsp_mst.diet_use_yn)", "sql": sql, "params": params,
                      "ck": ("hsp_mst", hsp_id, "diet_use_yn"), "conn_type": "skill"})

    if "REMOTE_CONSULT" in args.features:
        sql, params = _hsp_mst_update(hsp_id, {"remote_consultation_use_yn": "Y"})
        items.append({"label": "화상 상담 (hsp_mst.remote_consultation_use_yn)", "sql": sql, "params": params,
                      "ck": ("hsp_mst", hsp_id, "remote_consultation_use_yn"), "conn_type": "skill"})

    if "CERTIFICATES" in args.features:
        sql, params = _hsp_prop_row(hsp_id, "CERTIFICATES_USE_YN", "Y", "제증명 발급 신청 기능 사용 여부")
        items.append({"label": "제증명 발급 신청 (hsp_prop.CERTIFICATES_USE_YN)", "sql": sql, "params": params,
                      "ck": ("hsp_prop", hsp_id, "CERTIFICATES_USE_YN"), "conn_type": "skill"})

    if "MEMBER_ARRIVAL" in args.features:
        sql, params = _svc_hsp_mst_update(hsp_id, "hsptlz_arrival_use_yn")
        items.append({"label": "입원 도착 확인/체크인 (member DB)", "sql": sql, "params": params,
                      "ck": ("svc_hsp_mst", hsp_id, "hsptlz_arrival_use_yn"), "conn_type": "member"})

    if "MEMBER_HOPE_ROOM" in args.features:
        sql, params = _svc_hsp_mst_update(hsp_id, "hsptlz_hope_room_use_yn")
        items.append({"label": "희망병실 배정 (member DB)", "sql": sql, "params": params,
                      "ck": ("svc_hsp_mst", hsp_id, "hsptlz_hope_room_use_yn"), "conn_type": "member"})

    if "MEMBER_CONSENT_FORM" in args.features:
        sql, params = _svc_hsp_mst_update(hsp_id, "hsptlz_consent_form_use_yn")
        items.append({"label": "입원 동의서 (member DB)", "sql": sql, "params": params,
                      "ck": ("svc_hsp_mst", hsp_id, "hsptlz_consent_form_use_yn"), "conn_type": "member"})

    return items


def is_existing(conn, ck: tuple) -> bool:
    with conn.cursor() as cur:
        if ck[0] == "hsp_prop":
            cur.execute("SELECT 1 FROM hsp_prop WHERE hsp_id=%s AND code=%s", (ck[1], ck[2]))
        elif ck[0] == "hsp_mst":
            col = ck[2]
            cur.execute(f"SELECT {col} FROM hsp_mst WHERE hsp_id=%s", (ck[1],))
            row = cur.fetchone()
            return row is not None and row[0] == "Y"
        elif ck[0] == "svc_hsp_mst":
            col = ck[2]
            cur.execute(f"SELECT {col} FROM svc_hsp_mst WHERE hsp_id=%s", (ck[1],))
            row = cur.fetchone()
            return row is not None and row[0] == "Y"
        elif ck[0] == "stte_ccrc":
            cur.execute(
                "SELECT 1 FROM stte_ccrc WHERE hsp_id=%s AND stte_ccrc_id=%s AND dtl_cd=%s",
                (ck[1], CONSENT_STTE_CCRC_ID, CONSENT_DTL_CD),
            )
        elif ck[0] == "stte_ccrc_cnte":
            cur.execute(
                "SELECT 1 FROM stte_ccrc_cnte"
                " WHERE hsp_id=%s AND stte_ccrc_id=%s AND stte_ccrc_cnte_cd=%s AND ccrc_scrn=%s",
                (ck[1], CONSENT_STTE_CCRC_ID, ck[2], ck[3]),
            )
        else:  # dtl_mst
            cur.execute(
                "SELECT 1 FROM dtl_mst WHERE hsp_id=%s AND grp_cd=%s AND dtl_cd=%s",
                (ck[1], ck[2], ck[3]),
            )
        return cur.fetchone() is not None


def query_hospital(conn, hsp_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT code, value, use_yn FROM hsp_prop"
            " WHERE hsp_id=%s AND code IN (%s,%s,%s,%s) ORDER BY code",
            (hsp_id, "HSPTLZ_TODAY_SCHEDULE_MENU_YN", "HOSPITALIZATION_PRE_GUIDE_URL",
             "PARK_GUIDE_URL", "CERTIFICATES_USE_YN"),
        )
        props = cur.fetchall()

        cur.execute(
            "SELECT grp_cd, dtl_cd, dtl_cd_nm, use_yn FROM dtl_mst"
            " WHERE hsp_id=%s AND grp_cd IN (%s,%s,%s,%s) ORDER BY grp_cd",
            (hsp_id, "HSPTZ_LIVING_MYDOCTOR", "HSPTZ_LIVING_DISCHARGE",
             "CCRC_ITEM_MGMT", "CCRC_FOOTER_INFO"),
        )
        dtls = cur.fetchall()

        cur.execute(
            "SELECT grp_cd, COUNT(*) FROM hsp_guid_mst"
            " WHERE hsp_id=%s AND use_yn='Y' AND grp_cd IN (%s,%s,%s,%s) GROUP BY grp_cd",
            (hsp_id, "HSPTLZ_LIVING_GUIDE", "CONVENIENCE_UTILITY", "HSPTZ_LIVING_SAFETY_MANAGEMENT", "DISCHARGE_GUIDE"),
        )
        cards = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute(
            "SELECT hsptz_info, hsptlz_detail_info_yn, bed_tp, diet_use_yn, remote_consultation_use_yn"
            " FROM hsp_mst WHERE hsp_id=%s",
            (hsp_id,),
        )
        hsp_mst_row = cur.fetchone()

        # 동의 데이터 완전성
        cur.execute("SELECT COUNT(*) FROM stte_ccrc WHERE hsp_id=%s AND stte_ccrc_id=%s AND dtl_cd=%s",
                    (hsp_id, CONSENT_STTE_CCRC_ID, CONSENT_DTL_CD))
        n_stte = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM stte_ccrc_cnte WHERE hsp_id=%s AND stte_ccrc_id=%s",
                    (hsp_id, CONSENT_STTE_CCRC_ID))
        n_cnte = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM dtl_mst WHERE hsp_id=%s AND dtl_cd=%s AND grp_cd IN ('CCRC_ITEM_MGMT','CCRC_FOOTER_INFO')",
            (hsp_id, CONSENT_DTL_CD))
        n_dtl = cur.fetchone()[0]
        consent = (n_stte, n_cnte, n_dtl)

    return props, dtls, cards, hsp_mst_row, consent


def query_member(member_conn, hsp_id: int):
    with member_conn.cursor() as cur:
        cur.execute(
            "SELECT hsptlz_expd_use_yn, hsptlz_lvng_use_yn, hsptlz_arrival_use_yn,"
            " hsptlz_hope_room_use_yn, hsptlz_consent_form_use_yn FROM svc_hsp_mst WHERE hsp_id=%s",
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
    parser.add_argument("--ccrc-dtl-url", help="동의 전문 보기 URL (CONSENT_HSPTLZ, 미지정 시 기존 병원 행에서 복사)")
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
            props, dtls, cards, hsp_mst_row, consent = query_hospital(conn, args.hsp_id)
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
            detail_val = hsp_mst_row[1] if hsp_mst_row else None
            bed_tp_val = hsp_mst_row[2] if hsp_mst_row else None
            diet_val = hsp_mst_row[3] if hsp_mst_row else None
            remote_val = hsp_mst_row[4] if hsp_mst_row else None

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
            detail_status = "✅ Y" if detail_val == "Y" else f"❌ {detail_val or '미설정'}"
            print(f"{'  입원 정보 상세 확인 (hsp_mst)':<{W}} {detail_status}")
            print(f"{'  ㄴ bed_tp (DAY 필요)':<{W}} {bed_tp_val or '미설정'}")
            print("─" * 60)

            # 입원/퇴원 동의 데이터
            n_stte, n_cnte, n_dtl = consent
            consent_ok = (n_stte >= 1 and n_cnte >= 8 and n_dtl >= 2)
            consent_status = (f"✅ 완비 (stte_ccrc {n_stte}/1, cnte {n_cnte}/8, dtl_mst {n_dtl}/2)"
                              if consent_ok else
                              f"❌ 불완전 (stte_ccrc {n_stte}/1, cnte {n_cnte}/8, dtl_mst {n_dtl}/2)")
            print(f"{'입원/퇴원 동의 데이터':<{W}} {consent_status}")
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
            print("─" * 60)

            # 기타 기능
            print(f"{'식단 관리 (hsp_mst)':<{W}} {'✅ Y' if diet_val == 'Y' else '❌ ' + (diet_val or '미설정')}")
            print(f"{'화상 상담 (hsp_mst)':<{W}} {'✅ Y' if remote_val == 'Y' else '❌ ' + (remote_val or '미설정')}")
            print(f"{'제증명 발급 신청 (hsp_prop)':<{W}} {'✅ Y' if _prop_active('CERTIFICATES_USE_YN') else '❌ 미설정'}")
            if member_row is not None:
                print(f"{'입원 도착/체크인 (member DB)':<{W}} {_yn_status(member_row[2])}")
                print(f"{'희망병실 배정 (member DB)':<{W}} {_yn_status(member_row[3])}")
                print(f"{'입원 동의서 (member DB)':<{W}} {_yn_status(member_row[4])}")

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

        items = build_items(args.hsp_id, args, conn)
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
