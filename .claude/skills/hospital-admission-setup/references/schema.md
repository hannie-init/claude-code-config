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
