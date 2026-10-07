# DB 스키마 및 필드 매핑 규칙

## 목차
- [테이블 DDL](#테이블-ddl)
- [grp_cd 값 목록](#grpcd-값-목록)
- [고정값 매핑](#고정값-매핑)
- [guid_cd 네이밍 규칙](#guidcd-네이밍-규칙)
- [guid_dtl_link_tp 코드 값](#guiddtllinkt-코드-값)
- [엑셀 → DB 행 구조 (3행 블록)](#엑셀--db-행-구조-3행-블록)

---

## 테이블 DDL

### hsp_guid_mst
```sql
create table hsp_guid_mst
(
    hsp_id          int                          not null comment '병원 ID',
    guid_cd         varchar(50) charset utf8mb3  not null comment '안내 코드',
    grp_cd          varchar(30)                  not null comment '그룹핑 코드',
    guid_tile       varchar(500)                 null comment '안내 타이틀',
    guid_desc       varchar(1000)                null comment '안내 설명',
    guid_mak_seq    int                          null comment '안내 표시 순서',
    guid_img_path   varchar(500) charset utf8mb3 null comment '안내 이미지 경로',
    hsp_loc_guid_yn varchar(1)                   null comment '병원 위치 안내 가능 여부',
    sub_card_yn     varchar(1)                   null comment '하위 카드 구성 여부',
    use_yn          varchar(1) charset utf8mb3   null comment '사용 여부',
    fsr_dtm         datetime                     null comment '최초등록일시',
    fsr_id          bigint                       null comment '최초등록자ID',
    lst_mdf_dtm     datetime                     null comment '최종수정일시',
    lst_mdf_id      bigint                       null comment '최종수정자ID',
    primary key (hsp_id, guid_cd)
);
```

### hsp_guid_mst_dtl
```sql
create table hsp_guid_mst_dtl
(
    hsp_id           int                          not null comment '병원 ID',
    guid_cd          varchar(50) charset utf8mb3  not null comment '안내 코드',
    guid_dtl_cd      varchar(20) charset utf8mb3  not null comment '안내 상세 코드',
    grp_cd           varchar(30)                  not null comment '그룹핑 코드',
    guid_dtl_nm      varchar(100) charset utf8mb3 null comment '안내 상세 이름',
    guid_dtl_mak_seq int                          null comment '안내 상세 표시 순번',
    guid_dtl_link_tp varchar(1) charset utf8mb3   null comment '안내 상세 링크 타입',
    guid_dtl_link    varchar(500) charset utf8mb3 null comment '안내 상세 링크',
    use_yn           varchar(1) charset utf8mb3   null comment '사용 여부',
    fsr_dtm          datetime                     null comment '최초등록일시',
    fsr_id           bigint                       null comment '최초등록자ID',
    lst_mdf_dtm      datetime                     null comment '최종수정일시',
    lst_mdf_id       bigint                       null comment '최종수정자ID',
    primary key (hsp_id, guid_cd, guid_dtl_cd)
);
```

### 진료안내 테이블 (Figma 대조 모드 전용)

병원안내(`hsp_guid_*`)와 별개로 **진료 안내 블록**은 아래 테이블에서 관리된다.
구조는 `hsp_guid_*`와 유사하나 컬럼 접두어가 `med_guid_`이고 **`grp_cd` 컬럼이 없다.**

| 테이블 | PK | 링크 컬럼 |
|---|---|---|
| `hsp_med_guid_mst` | `(hsp_id, med_guid_cd)` | — (카드 마스터: med_guid_tile/desc/img_path) |
| `hsp_med_guid_mst_dtl` | `(hsp_id, med_guid_cd, med_guid_dtl_cd)` | `med_guid_dtl_link` (`med_guid_dtl_link_tp`=W/B/M) |

`compare_figma.py --block med_guide` 가 이 테이블을 대상으로 한다.

---

## grp_cd 값 목록

| grp_cd | 콘텐츠 | --grp-cd 옵션값 |
|--------|--------|----------------|
| `DISCHARGE_GUIDE` | 퇴원 안내 | `DISCHARGE_GUIDE` |
| `HSPTLZ_LIVING_GUIDE` | 입원 생활 안내 | `HSPTLZ_LIVING_GUIDE` |
| `CONVENIENCE_UTILITY` | 편의 시설 확인 | `CONVENIENCE_UTILITY` |
| `HSPTZ_LIVING_SAFETY_MANAGEMENT` | 안전 생활 알아보기 | `HSPTZ_LIVING_SAFETY_MANAGEMENT` |
| `HSP_GUIDE` | 병원안내 | (insert 미지원, `compare_figma.py --block hsp_guide` 대조 전용) |

---

## 고정값 매핑

| 필드 | 값 | 비고 |
|------|-----|------|
| `grp_cd` | `--grp-cd` 파라미터 값 | 콘텐츠 타입에 따라 다름 |
| `use_yn` | `Y` | 항상 고정 |
| `fsr_id` | `0` | 항상 고정 |
| `lst_mdf_id` | `0` | 항상 고정 |
| `fsr_dtm` | `NOW()` | INSERT 시각 |
| `lst_mdf_dtm` | `NOW()` | INSERT 시각 |
| `guid_tile` | `NULL` | 미사용 |
| `guid_img_path` | `NULL` | 미사용 |
| `hsp_loc_guid_yn` | `NULL` | 미사용 |
| `sub_card_yn` | `NULL` | 미사용 |
| `guid_dtl_cd` | `BUTTON_1` | 버튼은 항상 1개 |
| `guid_dtl_mak_seq` | `1` | 항상 고정 |

---

## guid_cd 네이밍 규칙
- 형식: `{GRP_CD}_BCARD_{순서}` (2자리 zero-padding)
- 예(퇴원 안내): `DISCHARGE_GUIDE_BCARD_01`, `DISCHARGE_GUIDE_BCARD_02`
- 예(입원 생활): `HSPTLZ_LIVING_GUIDE_BCARD_01`, `HSPTLZ_LIVING_GUIDE_BCARD_02`
- 순서는 엑셀 C열부터 시작 (C=01, D=02, E=03, F=04, G=05, H=06, ...)
- 빈 셀은 건너뜀 (순서 유지)

---

## guid_dtl_link_tp 코드 값

| 코드 | 의미 | guid_dtl_link 값 |
|------|------|-----------------|
| `W` | 웹 링크 | URL (http/https로 시작) |
| `B` | 블록 호출 | 블록 ID (사용자 입력 필요) |
| `M` | 사용자 발화 메세지 | 발화 텍스트 (문자열) |
| `T` | 미사용 | - |
| `C` | 미사용 | - |

---

## 엑셀 → DB 행 구조 (3행 블록)

각 병원 데이터는 3행씩 묶음(내용행/버튼행/글자수행). **컬럼 구조는 콘텐츠(grp_cd)에 따라 다르다.**

### ⬇️ 입원생활 · 편의시설 · 안전생활 (HSPTLZ_LIVING_GUIDE / CONVENIENCE_UTILITY / HSPTZ_LIVING_SAFETY_MANAGEMENT)

| 컬럼 | 내용행(1) | 버튼행(2) | 저장 위치 |
|---|---|---|---|
| A | 병원명 | (빈칸) | 병원 매칭용(미저장) |
| **B** | 인사말(무시) | **버튼1 "상세 내용 보기" URL** | `dtl_mst` (`*_DETAIL_CONTENT_LINK`) |
| **C** | (빈칸) | **버튼2 "안내 영상 보기" URL** | `dtl_mst` (`*_YOUTUBE_LINK`) |
| **D~** | 카드 본문(guid_desc) | 카드별 버튼 | `hsp_guid_mst(_dtl)` |

> **카드는 D열부터.** B·C의 헤더 버튼(상세/영상)은 **카드가 아니라 `dtl_mst`** 에 들어간다 → `insert_guide.py --insert-links`.
> 카드 본문/카드버튼만 `hsp_guid_mst(_dtl)` INSERT 대상(엑셀 INSERT 워크플로우).

### ⬇️ 퇴원 안내 (DISCHARGE_GUIDE)

| 컬럼 | 내용행(1) | 버튼행(2) | 저장 위치 |
|---|---|---|---|
| A | 병원명 | (빈칸) | 병원 매칭용(미저장) |
| **B** | 인사말(무시) | **버튼1 URL** | `dtl_mst` |
| **C~** | 카드 본문 | 카드별 버튼 | `hsp_guid_mst(_dtl)` |

- **행 3 (글자수행)**: 숫자만 있음 → 무시
- 헤더 행(A열="병원") 및 기획안 행은 건너뜀.
- 카드는 캐러셀 10장 × outputs 3 = **최대 30장** (파서가 D/C열부터 최대 30장 파싱).

### 인사말(헤더) 버튼 → `dtl_mst` 매핑

URL은 **`dtl_cd_nm`** 에 저장(라벨은 앱이 dtl_cd로 렌더링). `dtl_expl=''`, `dtl_cd_seq=1`, `use_yn='Y'`. PK=(grp_cd, dtl_cd, hsp_id).

| grp_cd | 상세 보기 dtl_cd | 안내 영상 보기 dtl_cd |
|---|---|---|
| HSPTLZ_LIVING_GUIDE | `GUIDE_INFO_DETAIL_CONTENT_LINK` | `GUIDE_INFO_YOUTUBE_LINK` |
| HSPTZ_LIVING_SAFETY_MANAGEMENT | `SAFETY_MANAGEMENT_DETAIL_CONTENT_LINK` | `SAFETY_MANAGEMENT_YOUTUBE_LINK` |
| CONVENIENCE_UTILITY | `CONVENIENCE_UTILITY_DETAIL_CONTENT_LINK` | `CONVENIENCE_UTILITY_YOUTUBE_LINK` |

> ⚠️ **퇴원 안내(DISCHARGE_GUIDE)는 규칙이 다르다.** 헤더 버튼(예: 퇴원 안내 영상 신청)은
> - grp_cd = **`HSPTZ_LIVING_DISCHARGE`** (카드 grp_cd `DISCHARGE_GUIDE`와 다름!), dtl_cd = **`HSPTZ_LIVING_DISCHARGE_INFO`**
> - URL은 **`dtl_expl`** 에 저장 (다른 기능은 `dtl_cd_nm`).
> - 이 행은 **퇴원 안내 활성화(hospital-admission-setup의 DISCHARGE_ACTIVATE)** 가 이미 만든 행과 동일 → INSERT 아닌 **UPDATE**.
> - `insert_guide.py --update-dtl --hsp-id <ID> --dtl-grp HSPTZ_LIVING_DISCHARGE --dtl-code HSPTZ_LIVING_DISCHARGE_INFO --dtl-expl "https://..."`

조회/삽입:
```bash
# 헤더 버튼 조회
insert_guide.py --query-links --hsp-id <ID> [--grp-cd <G>]
# 헤더 버튼 INSERT (dtl_mst)
insert_guide.py --insert-links --hsp-id <ID> --grp-cd <G> \
  --detail-url "https://..." [--youtube-url "https://..."]
# 잘못 들어간 카드 버튼 삭제 (hsp_guid_mst_dtl)
insert_guide.py --delete-button --hsp-id <ID> --grp-cd <G> --guid-cd <GUID_CD> [--dtl-cd BUTTON_1]
```

### 버튼 파싱 규칙
```
셀 값이 '-' 또는 빈 값 → 버튼 없음, hsp_guid_mst_dtl INSERT 안 함
셀 값에 '[버튼명]' + 줄바꿈 + 'http' → W 타입
셀 값에 '[버튼명]' + 줄바꿈 + '블록 호출' or 'block' → B 타입 (블록 ID 별도 입력)
```
