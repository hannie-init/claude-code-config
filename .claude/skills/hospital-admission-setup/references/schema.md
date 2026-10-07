# DB 스키마 및 필드 매핑 규칙

## 목차
- [테이블 DDL](#테이블-ddl)
- [고정값 매핑](#고정값-매핑)
- [기능별 INSERT/UPDATE 명세](#기능별-insertupdate-명세)

---

## 테이블 DDL

### hsp_prop
```sql
create table hsp_prop
(
    id          bigint auto_increment comment 'ID' primary key,
    hsp_id      int                    not null comment '병원 ID',
    code        varchar(100)           not null comment '설정 코드 값',
    value       varchar(255)           not null comment '설정 값',
    description varchar(300)           not null comment '설정에 대한 설명',
    category    varchar(10)            null comment '기능 카테고리',
    use_yn      varchar(1) default 'Y' null comment '사용 여부',
    fsr_dtm     datetime               null,
    fsr_id      bigint     default 0   null,
    lst_mdf_dtm datetime               null,
    lst_mdf_id  bigint     default 0   null
);
-- 중복 체크: (hsp_id, code) 조합
```

### dtl_mst
```sql
create table dtl_mst
(
    hsp_id      int          not null comment '병원ID',
    grp_cd      varchar(50)  not null comment '그룹 코드',
    dtl_cd      varchar(50)  not null comment '상세 코드',
    dtl_cd_nm   varchar(500) null comment '상세 이름',
    dtl_expl    varchar(4000) null comment '상세 설명',
    dtl_cd_seq  int          null comment '순번',
    use_yn      varchar(1) default 'Y' null,
    fsr_dtm     datetime     null,
    fsr_id      bigint default 0 null,
    lst_mdf_dtm datetime     null,
    lst_mdf_id  bigint default 0 null,
    primary key (grp_cd, dtl_cd, hsp_id)
);
-- 중복 체크: PRIMARY KEY (grp_cd, dtl_cd, hsp_id)
```

---

## 고정값 매핑

| 필드 | 값 | 비고 |
|------|-----|------|
| `use_yn` | `Y` | 항상 고정 |
| `fsr_id` | `0` | 항상 고정 |
| `lst_mdf_id` | `0` | 항상 고정 |
| `fsr_dtm` | `NOW()` | INSERT 시각 |
| `lst_mdf_dtm` | `NOW()` | INSERT 시각 |
| `dtl_cd_seq` | `1` | dtl_mst 항상 고정 |

---

### svc_hsp_mst (member DB)
```sql
-- member DB 테이블. 병원별 서비스 사용 여부 마스터
-- 행이 이미 존재하므로 INSERT가 아닌 UPDATE
-- 중복 체크: hsptlz_expd_use_yn / hsptlz_lvng_use_yn 이 이미 'Y'이면 SKIP
```

| 컬럼 | 설명 |
|------|------|
| `hsp_id` | 병원 ID (WHERE 조건) |
| `hsptlz_expd_use_yn` | 입원 확인 활성화 플래그 (`'Y'` / NULL) |
| `hsptlz_lvng_use_yn` | 입원생활 안내 활성화 플래그 (`'Y'` / NULL) |

- 롤백: `UPDATE svc_hsp_mst SET hsptlz_expd_use_yn = NULL WHERE hsp_id = <ID>;`
- 롤백: `UPDATE svc_hsp_mst SET hsptlz_lvng_use_yn = NULL WHERE hsp_id = <ID>;`

---

## 기능별 INSERT/UPDATE 명세

### 0. 입원생활 안내 활성화 (hsp_mst UPDATE)

> `hsp_mst`는 병원 마스터 테이블 — 행이 이미 존재하므로 INSERT가 아닌 UPDATE

```sql
UPDATE hsp_mst SET hsptz_info = 'Y' WHERE hsp_id = <ID>;
```

| 컬럼 | 값 | 비고 |
|------|-----|------|
| `hsp_id` | 병원 ID | WHERE 조건 |
| `hsptz_info` | `'Y'` | 입원생활안내 + 퇴원안내 활성화 플래그 |

- 이미 `'Y'`이면 SKIP (중복 처리)
- 롤백: `UPDATE hsp_mst SET hsptz_info = NULL WHERE hsp_id = <ID>;`
- member DB 항목은 `MEMBER_EXPD` / `MEMBER_LVG` 기능 코드로 별도 처리

### 1. 오늘의 일정 (hsp_prop)

| 컬럼 | 값 |
|------|-----|
| `hsp_id` | 병원 ID |
| `code` | `HSPTLZ_TODAY_SCHEDULE_MENU_YN` |
| `value` | `Y` |
| `description` | `오늘의 일정 메뉴 사용 여부` |
| `category` | `입원` |

### 2. 주치의 정보보기 (dtl_mst)

| 컬럼 | 값 |
|------|-----|
| `hsp_id` | 병원 ID |
| `grp_cd` | `HSPTZ_LIVING_MYDOCTOR` |
| `dtl_cd` | `HSPTZ_LIVING_MYDOCTOR_INFO` |
| `dtl_cd_nm` | `주치의 정보 보기` |

### 3. 퇴원 안내 활성화 (dtl_mst)

| 컬럼 | 값 |
|------|-----|
| `hsp_id` | 병원 ID |
| `grp_cd` | `HSPTZ_LIVING_DISCHARGE` |
| `dtl_cd` | `HSPTZ_LIVING_DISCHARGE_INFO` |
| `dtl_cd_nm` | `퇴원 안내 정보` |

### 4. 입원 사전 안내 URL (hsp_prop)

| 컬럼 | 값 |
|------|-----|
| `hsp_id` | 병원 ID |
| `code` | `HOSPITALIZATION_PRE_GUIDE_URL` |
| `value` | 사용자 입력 URL |
| `description` | `입원 사전 안내 URL` |
| `category` | `입원` |

### 5. 주차 안내 URL (hsp_prop)

| 컬럼 | 값 |
|------|-----|
| `hsp_id` | 병원 ID |
| `code` | `PARK_GUIDE_URL` |
| `value` | 사용자 입력 URL |
| `description` | `주차 안내 URL` |
| `category` | `입원` |

---

## 입원/퇴원 동의 데이터 (`CONSENT_HSPTLZ`) — 핵심

입원확인·입원생활 도입 시 **필수**. 「동의 관리」화면과 통합동의 화면이 이 데이터로 동작한다.
병원당 **3개 테이블 · 총 11행**: `stte_ccrc`(1) + `stte_ccrc_cnte`(8: CCRC 4 + PTCFM 4) + `dtl_mst`(2).

> **`stte_ccrc_id = 81`** 은 이 동의(`HSPTZ_LVNG_CCRC_ITEM` = 개인정보 제3자 제공 동의·입원/퇴원)의 **고정 상수**로, 전 병원 공통이다(예시값 아님). 확인: `SELECT stte_ccrc_id, COUNT(DISTINCT hsp_id) FROM stte_ccrc WHERE grp_cd='HSPTZ_LVNG_CCRC_ITEM' GROUP BY stte_ccrc_id;` → 81 단일.

> 3개 테이블 중 **하나라도 빠지면 증상이 다르다**: `dtl_mst` 목록행 누락 → 동의 관리 화면에 항목 자체가 안 뜸 / `CCRC_FOOTER_INFO` 누락 → '동의 전문 보기' 링크 깨짐 / `stte_ccrc`·`cnte` 누락 → 동의 화면·전문 내용 없음. 그래서 **행 단위로 개별 중복 체크**해야 한다(부분 누락 병원 존재).

### 테이블 DDL

```sql
-- stte_ccrc : 동의 정의 (PK: stte_ccrc_id, hsp_id)
-- stte_ccrc_cnte : 동의 상세 내용 (PK: stte_ccrc_id, hsp_id, stte_ccrc_cnte_cd, ccrc_scrn)
```

### A-1. stte_ccrc (1행)

| 컬럼 | 값 |
|------|-----|
| `stte_ccrc_id` | `81` (고정 상수) |
| `hsp_id` | 병원 ID |
| `grp_cd` | `HSPTZ_LVNG_CCRC_ITEM` |
| `dtl_cd` | `HSPTZ_LVNG_CCRC_ITEM_01` |
| `essn_yn` | `Y` |
| `ccrc_scrn` | `PTCFM` |
| `stte_ccrc_title` | `개인정보 제3자 제공 동의` |
| `stte_ccrc_hdr` | `{병원명}은 (주)카카오헬스케어에서 제공하는 서비스 이용을 위한 목적으로만 개인정보를 제공하며, 본래의 목적 범위를 초과하여 제3자에게 제공 및 처리하지 않습니다.` ← **병원명 치환** |
| `stte_ccrc_footer` | `본 동의는 거부할 수 있으며, 거부 시 서비스 이용이 제한될 수 있습니다.` |
| `ccrc_dsp_yn` / `ccrc_dtl_yn` | `Y` / `Y` |
| `ver_no` | `1.0` |
| `use_str_dt` / `use_end_dt` | `CURDATE()` / `2099-12-01` |

### A-2. stte_ccrc_cnte (8행 = CCRC 4 + PTCFM 4)

`stte_ccrc_id=81`, `ver_no='1.0'`, `use_str_dt=CURDATE()`, `use_end_dt='2099-12-01'` 공통. 내용은 **병원 공통**(치환 없음).

| stte_ccrc_cnte_cd | ccrc_scrn | cnte_mak_seq | cnte_key | cnte_value |
|---|---|---|---|---|
| HSPTZ_LVNG_CCRC_ITEM_01_01 | CCRC | 1 | 동의 목적 | 케어챗을 통한 입∙퇴원 정보 조회, 편의 서비스 제공 |
| HSPTZ_LVNG_CCRC_ITEM_01_02 | CCRC | 2 | 제공 받는 자 | (주)카카오헬스케어 |
| HSPTZ_LVNG_CCRC_ITEM_01_03 | CCRC | 3 | 개인정보 항목 | 이름, 휴대전화번호, 입원일시, 진료과, 주치의, 병동/병실, 입원비, 식단 |
| HSPTZ_LVNG_CCRC_ITEM_01_04 | CCRC | 4 | 제공받는 자의 보유 및 이용 기간 | 서비스 내 게시 직후 파기 |
| HSPTZ_LVNG_CCRC_ITEM_01_01 | PTCFM | 1 | 제공 받는 자 | (주)카카오헬스케어 |
| HSPTZ_LVNG_CCRC_ITEM_01_02 | PTCFM | 2 | 제공 항목 | 이름, 휴대전화번호, 입원일시, 진료과, 주치의, 병동/병실, 입원비, 식단 |
| HSPTZ_LVNG_CCRC_ITEM_01_03 | PTCFM | 3 | 제공받는 자의 이용 목적 | 케어챗을 통한 입∙퇴원 정보 조회, 편의 서비스 제공 |
| HSPTZ_LVNG_CCRC_ITEM_01_04 | PTCFM | 4 | 제공받는 자의 보유 및 이용 기간 | 서비스 내 게시 직후 파기 |

> `입∙퇴원`의 `∙`는 U+2219(BULLET OPERATOR) 특수문자다. 일반 가운뎃점(·)이 아니므로 원본 그대로 유지.

### A-3. dtl_mst (2행)

| grp_cd | dtl_cd | dtl_cd_nm | dtl_expl | dtl_cd_seq |
|---|---|---|---|---|
| `CCRC_ITEM_MGMT` | `HSPTZ_LVNG_CCRC_ITEM_01` | 개인정보 제3자 제공 동의 | 입원/퇴원 | 기존 최대 seq +1 (없으면 3) |
| `CCRC_FOOTER_INFO` | `HSPTZ_LVNG_CCRC_ITEM_01` | 동의 전문 보기 | (동의 전문 URL) | 1 |

- `CCRC_FOOTER_INFO`의 `dtl_expl`(URL)은 **환경별로 다름**. 스크립트는 같은 병원의 기존 `CCRC_FOOTER_INFO` 행에서 URL을 자동 복사하며, 없으면 `--ccrc-dtl-url`로 지정. (dev 기본값: `https://karechat-common-dev.kakaohealthcare.com/myMenu/myInfo/ccrcManagement/privacyInfo/ccrcDtl`)

---

## 입원 확인 상세 · 기타 기능 (B·C)

### 6. 입원 정보 상세 확인 (`DETAIL_INFO`, hsp_mst UPDATE)

```sql
UPDATE hsp_mst SET hsptlz_detail_info_yn = 'Y', bed_tp = 'DAY' WHERE hsp_id = <ID>;
```
- `bed_tp='DAY'`가 있어야 상세 확인이 정상 동작. ⚠️ 기존 `bed_tp` 값이 있으면 덮어쓰므로 확인 필요.
- 중복 체크: `hsptlz_detail_info_yn`이 이미 `'Y'`이면 SKIP.

### 7. 식단 관리 / 화상 상담 (hsp_mst UPDATE)

| 기능 코드 | 컬럼 |
|---|---|
| `DIET` | `hsp_mst.diet_use_yn = 'Y'` |
| `REMOTE_CONSULT` | `hsp_mst.remote_consultation_use_yn = 'Y'` |

### 8. 제증명 발급 신청 (`CERTIFICATES`, hsp_prop)

| 컬럼 | 값 |
|------|-----|
| `code` | `CERTIFICATES_USE_YN` |
| `value` | `Y` |
| `description` | `제증명 발급 신청 기능 사용 여부` |

> 제증명 전체 동작에는 URL/메시지 코드도 필요할 수 있다(값 입력 필요, 스크립트 미포함):
> `CERTIFICATES_ISSUE_REQUEST_WEB_URI`(발급 신청 URL), `ISSUE_CERTIFICATES_BLOCK_MESSAGE`, `CERTIFICATES_MESSAGE`.

### 9. member DB 추가 플래그 (svc_hsp_mst UPDATE)

| 기능 코드 | 컬럼 |
|---|---|
| `MEMBER_ARRIVAL` | `hsptlz_arrival_use_yn = 'Y'` (입원 도착 확인/체크인) |
| `MEMBER_HOPE_ROOM` | `hsptlz_hope_room_use_yn = 'Y'` (희망병실 배정) |
| `MEMBER_CONSENT_FORM` | `hsptlz_consent_form_use_yn = 'Y'` (입원 동의서) |
