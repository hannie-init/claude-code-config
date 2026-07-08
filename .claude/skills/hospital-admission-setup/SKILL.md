---
name: hospital-admission-setup
description: |
  병원 "입원 기본 스펙" 오픈 시 필요한 skill DB + member DB 기본 세팅을 자동화한다.
  hsp_prop, dtl_mst 테이블에 기능 활성화 데이터를 INSERT하거나 현황을 조회한다.
  member DB의 svc_hsp_mst 테이블 조회/수정도 지원한다.

  다음 상황에서 사용:
  - "입원 기본 스펙 세팅", "입원 DB 세팅", "병원 기본 세팅"
  - "오늘의 일정 세팅", "주치의 정보 세팅", "퇴원 안내 활성화"
  - "입원 사전 안내 URL 등록", "주차 안내 URL 등록"
  - "입원 기능 DB 추가", "입원 세팅 조회"
  - "입원 확인 세팅", "member DB 세팅"
---

# Hospital Admission Setup

병원 입원 기본 스펙 오픈 시 skill DB + member DB 기본 세팅 자동화 스킬.
스키마 상세는 `references/schema.md` 참고.

> **DB 접속 정보 취급**: 스크립트가 `.env`를 스스로 로드한다. Claude는 `.env`를 `Read`/`grep`/`cat`으로 열람하지 **말 것**(권한상 거부되며 불필요). 이 스킬은 `.env`가 가리키는 단일 DB로 연결하므로, prod 여부 확정이 필요하면 사용자에게 확인한다.

> 콘텐츠 카드(입원 생활 안내 / 편의시설 / 안전생활 / 퇴원 안내 카드)는 `hospital-guide-inserter` 스킬 사용.

## 세팅 기능 목록

| 기능 코드 | 기능명 | 테이블 |
|----------|--------|--------|
| `HSP_MST_INFO` | 입원생활 안내 활성화 | `hsp_mst` (UPDATE, skill DB) |
| `TODAY_SCHEDULE` | 오늘의 일정 | `hsp_prop` (skill DB) |
| `DOCTOR_INFO` | 주치의 정보보기 | `dtl_mst` (skill DB) |
| `DISCHARGE_ACTIVATE` | 퇴원 안내 활성화 | `dtl_mst` (skill DB) |
| `PRE_GUIDE_URL` | 입원 사전 안내 URL | `hsp_prop` (skill DB, URL 입력 필요) |
| `PARK_URL` | 주차 안내 URL | `hsp_prop` (skill DB, URL 입력 필요) |
| `MEMBER_EXPD` | 입원 확인 활성화 | `svc_hsp_mst.hsptlz_expd_use_yn` (UPDATE, member DB) |
| `MEMBER_LVG` | 입원생활 안내 활성화 | `svc_hsp_mst.hsptlz_lvng_use_yn` (UPDATE, member DB) |

---

## 시작 시 작업 유형 확인 (필수)

스킬이 트리거되면 **반드시 먼저** 사용자에게 작업 유형을 물어본다:

> "어떤 작업을 하시겠어요?
> 1. **기능 세팅** — DB에 기능 활성화 데이터 INSERT
> 2. **현황 조회** — 특정 병원의 현재 세팅 상태 확인"

- **1 선택 → 세팅 워크플로우** 진행
- **2 선택 → 현황 조회** 진행

---

## 세팅 워크플로우 (Claude 지침)

```
진행 상황:
- [ ] 1. hsp_id 입력 받기
- [ ] 2. 세팅할 기능 확인 (URL 필요 여부 확인)
- [ ] 3. --dry-run SQL 확인 & 사용자 승인
- [ ] 4. 실제 INSERT 실행
- [ ] 5. --query로 결과 검증 & 사용자 확인
```

### 1. hsp_id & 세팅 기능 선택

사용자에게 hsp_id를 받은 뒤, **기능 선택**과 **필수 URL 입력**을 순서대로 받는다.

**① 기능 선택** — 병원마다 사용하지 않는 기능이 있을 수 있으므로 반드시 확인:
```
세팅할 기능을 선택해주세요 (사용하지 않는 기능은 제외):
[ ] HSP_MST_INFO       — 입원생활 안내 활성화 (hsp_mst.hsptz_info = 'Y')
[ ] TODAY_SCHEDULE     — 오늘의 일정
[ ] DOCTOR_INFO        — 주치의 정보보기
[ ] DISCHARGE_ACTIVATE — 퇴원 안내 활성화
[ ] MEMBER_EXPD        — 입원 확인 활성화 (svc_hsp_mst.hsptlz_expd_use_yn = 'Y')
[ ] MEMBER_LVG         — 입원생활 안내 활성화 (svc_hsp_mst.hsptlz_lvng_use_yn = 'Y')
```

**② 필수 DB 값 입력** — 기능 선택과 무관하게 항상 필요한 값:
```
- 입원 사전 안내 URL (HOSPITALIZATION_PRE_GUIDE_URL): https://...
- 주차 안내 URL (PARK_GUIDE_URL): https://...
```
URL이 이미 세팅되어 있으면 생략 가능 (중복 시 SKIP 처리됨).

선택한 기능 코드와 URL 여부에 따라 `--features` 파라미터를 구성한다.

### 2-3. dry-run으로 SQL 미리보기

```bash
python3 ~/.claude/skills/hospital-admission-setup/scripts/setup_admission.py \
  --hsp-id <ID> \
  [--features TODAY_SCHEDULE,DOCTOR_INFO,DISCHARGE_ACTIVATE,PRE_GUIDE_URL,PARK_URL] \
  [--pre-guide-url "https://..."] \
  [--park-url "https://..."] \
  --dry-run
```

SQL 결과를 사용자에게 보여주고 확인 요청.

### 4. 실제 INSERT

사용자 확인 후 `--dry-run` 제거:
```bash
python3 ~/.claude/skills/hospital-admission-setup/scripts/setup_admission.py \
  --hsp-id <ID> \
  [--features ...] \
  [--pre-guide-url "https://..."] \
  [--park-url "https://..."]
```

### 5. INSERT 후 검증 (피드백 루프)

INSERT 완료 즉시 `--query`로 DB 결과 조회:
```bash
python3 ~/.claude/skills/hospital-admission-setup/scripts/setup_admission.py \
  --query --hsp-id <ID>
```

Claude가 결과를 마크다운 표로 변환 후 사용자에게 확인 요청.
문제 발견 시 롤백 후 재시도:
```sql
-- DataGrip에서 실행 (skill DB)
UPDATE hsp_mst SET hsptz_info = NULL WHERE hsp_id = <ID>;
DELETE FROM hsp_prop WHERE hsp_id = <ID>
  AND code IN ('HSPTLZ_TODAY_SCHEDULE_MENU_YN', 'HOSPITALIZATION_PRE_GUIDE_URL', 'PARK_GUIDE_URL');
DELETE FROM dtl_mst WHERE hsp_id = <ID>
  AND grp_cd IN ('HSPTZ_LIVING_MYDOCTOR', 'HSPTZ_LIVING_DISCHARGE');

-- member DB
UPDATE svc_hsp_mst SET hsptlz_expd_use_yn = NULL WHERE hsp_id = <ID>;
UPDATE svc_hsp_mst SET hsptlz_lvng_use_yn = NULL WHERE hsp_id = <ID>;
```

삭제 확인 후 3단계(dry-run)부터 재실행.

---

## 현황 조회

```bash
python3 ~/.claude/skills/hospital-admission-setup/scripts/setup_admission.py \
  --query --hsp-id <ID>
```

스크립트 실행 후, Claude는 결과를 **마크다운 표** 두 개로 변환하여 보여준다.

### 기능 활성화 현황
| 기능 | 상태 |
|------|------|
| 입원 확인 | ✅ Y / ❌ 미설정 (svc_hsp_mst, member DB) |
| [입원생활 안내] | |
| ㄴ 입원생활 안내 활성화 (skill DB) | ✅ Y / ❌ 미설정 (hsp_mst) |
| ㄴ 입원생활 안내 활성화 (member DB) | ✅ Y / ❌ 미설정 (svc_hsp_mst) |
| ㄴ 오늘의 일정 | ✅ 활성화 / ❌ 미설정 |
| ㄴ 주치의 정보보기 | ✅ 활성화 / ❌ 미설정 |
| ㄴ 입원생활 안내보기 (콘텐츠) | ✅ 활성화 (카드 N장) / ❌ 미설정 |
| ㄴ 편의시설 확인 (콘텐츠) | ✅ 활성화 (카드 N장) / ❌ 미설정 |
| ㄴ 안전생활 안내보기 (콘텐츠) | ✅ 활성화 (카드 N장) / ❌ 미설정 |
| 퇴원 안내 활성화 | ✅ 활성화 / ❌ 미설정 |
| 퇴원 안내 (콘텐츠) | ✅ 활성화 (카드 N장) / ❌ 미설정 |

### 필수 DB 값
| 항목 | 값 |
|------|-----|
| 입원 사전 안내 URL | https://... 또는 (미설정) |
| 주차 안내 URL | https://... 또는 (미설정) |

- 콘텐츠 (입원생활 안내보기/편의시설/안전생활/퇴원 안내) 는 `hospital-guide-inserter` 스킬로 등록

---

## 오류 케이스

| 오류 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| `⚠️ 기존 데이터 발견` | 동일 hsp_id+code 이미 존재 | DataGrip에서 해당 행 삭제 후 재실행 |
| `--pre-guide-url 값이 필요` | URL 파라미터 누락 | `--pre-guide-url "https://..."` 추가 |
| `DB 연결 실패` | .env 미설정 또는 VPN 미연결 | .env 확인 후 VPN 접속 |
| `member DB 연결 실패` | MEMBER_DB_NAME 미설정 또는 VPN 미연결 | .env에 MEMBER_DB_NAME 추가 후 VPN 접속 |

---

## 초기 설정 (최초 1회)

```bash
cp ~/.claude/skills/hospital-admission-setup/.env.example \
   ~/.claude/skills/hospital-admission-setup/.env
# .env에 DB 접속 정보 입력 (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, MEMBER_DB_NAME)

pip install pymysql python-dotenv
```

---

## 주요 규칙

- `use_yn = Y`, `fsr_id = lst_mdf_id = 0`, `fsr_dtm = lst_mdf_dtm = NOW()`
- 중복 데이터(동일 hsp_id+code 또는 hsp_id+grp_cd+dtl_cd) 있으면 SKIP
- member DB(`svc_hsp_mst`) 조회/수정 지원: `MEMBER_DB_NAME` env 설정 필요 (동일 서버, 다른 DB명)

상세 스키마 → `references/schema.md`

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-09 | 변경 이력 섹션 추가 |
| 2026-07-03 | `.env` 직접 열람 금지 안내 추가 — 스크립트가 `.env`를 로드하므로 Claude가 `.env`를 Read/grep하지 않고, prod 여부는 사용자에게 확인(권한 거부 루프 제거) |
