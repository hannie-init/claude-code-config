---
name: hospital-guide-inserter
description: |
  병원 안내 콘텐츠를 MySQL에 INSERT·조회하거나, Figma 디자인의 버튼 링크를
  DB와 대조해 UPDATE SQL을 생성한다. 세 개의 별개 기능(카테고리)으로 구성된다:
  ① 생활 안내(퇴원/입원/편의/안전, hsp_guid_mst(_dtl)) — INSERT·조회
  ② 병원안내(hsp_guid_mst(_dtl), grp_cd=HSP_GUIDE) — 조회·Figma 대조 (INSERT 미지원)
  ③ 진료안내(hsp_med_guid_mst(_dtl), 별도 테이블) — 조회·Figma 대조 (INSERT 미지원)
  ①②는 테이블이 같아도 grp_cd로 구분되는 다른 기능이니 섞지 말 것.

  다음 상황에서 사용:
  - "DB 넣기", "엑셀 업로드", "안내 콘텐츠 등록", "데이터 추가" → ① 생활 안내 INSERT
  - "현황 조회", "DB 확인" → 카테고리 확인 후 조회
  - "Figma 링크 대조", "링크 비교", "링크 UPDATE SQL", "병원안내/진료안내 링크 수정",
    "톡채널 링크 점검" → Figma 대조 & SQL 생성 (compare_figma.py, ②·③)
  - ① grp_cd: DISCHARGE_GUIDE(퇴원) / HSPTLZ_LIVING_GUIDE(입원) /
    CONVENIENCE_UTILITY(편의) / HSPTZ_LIVING_SAFETY_MANAGEMENT(안전)
  - 환경: --env dev|prod (prod는 조회 전용, 쓰기 차단)
---

# Hospital Guide Inserter

병원 안내 콘텐츠 → MySQL INSERT/조회 및 Figma 링크 대조 자동화 스킬.
스키마 상세는 `references/schema.md` 참고.

> **DB 접속 정보 취급**: 스크립트가 `.env`를 스스로 로드한다. Claude는 `.env`를 `Read`/`grep`/`cat`으로 열람하지 **말 것**(권한상 거부되며 불필요). 환경(dev/prod)은 `.env` 열람이 아니라 **`--env` 플래그와 스크립트 실행 출력**으로만 확정한다.

## 콘텐츠 카테고리 (3개 기능 — 먼저 구분할 것)

같은 테이블을 쓰더라도 **사용자 관점에서 별개 기능**이다. 작업 전 반드시 어느 카테고리인지 먼저 확정한다.

| # | 기능 | 테이블 | grp_cd | 지원 작업 |
|---|------|--------|--------|----------|
| ① | **생활 안내** (퇴원/입원/편의/안전) | `hsp_guid_mst(_dtl)` | 4종 (아래 표) | **INSERT · 조회** |
| ② | **병원안내** | `hsp_guid_mst(_dtl)` | `HSP_GUIDE` | **조회 · Figma 대조** (INSERT 미지원) |
| ③ | **진료안내** | `hsp_med_guid_mst(_dtl)` | 없음 (별도 테이블) | **조회 · Figma 대조** (INSERT 미지원) |

> ⚠️ ①과 ②는 테이블(`hsp_guid_*`)이 같지만 `grp_cd`로 분리되는 **다른 기능**이다. 절대 섞지 말 것.
> INSERT(엑셀 업로드)는 ①에서만 가능하다. ②·③는 조회 또는 Figma 링크 대조만 한다.

### ① 생활 안내 — grp_cd 선택 기준

| 콘텐츠 | --grp-cd 값 |
|--------|------------|
| 퇴원 안내 | `DISCHARGE_GUIDE` (기본값) |
| 입원 생활 안내 | `HSPTLZ_LIVING_GUIDE` |
| 편의 시설 확인 | `CONVENIENCE_UTILITY` |
| 안전 생활 알아보기 | `HSPTZ_LIVING_SAFETY_MANAGEMENT` |

### ② 병원안내 — `compare_figma.py --block hsp_guide` (grp_cd=HSP_GUIDE, 조회/대조 전용)
### ③ 진료안내 — `compare_figma.py --block med_guide` (별도 테이블, grp_cd 없음)

> ⚠️ `insert_guide.py --query --grp-cd`는 ① 4종만 받는다. **②·③ 조회는 `compare_figma.py --dump-links`** 로 한다.

## 데이터 입력 방식 (우선순위 순)

| 방식 | 방법 |
|------|------|
| **복사/붙여넣기** (기본) | 구글 시트 Ctrl+A → Ctrl+C → 채팅에 붙여넣기 |
| 로컬 엑셀 파일 | `.xlsx` 파일 경로를 인자로 전달 |
| 구글 시트 직접 연동 | `.env`의 `GOOGLE_SHEETS_URL` + gspread 인증 설정 |

## 시작 시 확인 (필수, 순서 준수)

스킬이 트리거되면 **반드시 아래 순서로** 사용자에게 물어본다.

**STEP 1 — 콘텐츠 카테고리 확정** (위 "콘텐츠 카테고리" 표 기준)

> "어떤 콘텐츠인가요?
> ① 생활 안내(퇴원/입원/편의/안전)  ② 병원안내  ③ 진료안내"

**STEP 2 — 작업 유형** (카테고리에 따라 선택지가 달라진다)

| 선택한 카테고리 | 가능한 작업 |
|---|---|
| ① 생활 안내 | **데이터 삽입(INSERT)** / **현황 조회** |
| ② 병원안내 | **현황 조회** / **Figma 링크 대조** (INSERT 불가) |
| ③ 진료안내 | **현황 조회(--dump-links)** / **Figma 링크 대조** (INSERT 불가) |

- **데이터 삽입 → INSERT 워크플로우** (① 전용)
- **현황 조회 → 현황 조회 섹션**
- **Figma 링크 대조 → Figma 대조 섹션** (②·③)

> ②·③에서 "데이터 넣기/INSERT" 요청이 오면, 해당 콘텐츠는 스크립트 INSERT를 지원하지 않음을 안내하고
> 조회 또는 Figma 대조로 안내한다 (신규 등록은 DataGrip 등에서 직접).

---

## INSERT 워크플로우 (Claude 지침) — ① 생활 안내 전용

> 이 워크플로우는 **① 생활 안내**(퇴원/입원/편의/안전)에서만 사용한다.
> ② 병원안내·③ 진료안내는 INSERT를 지원하지 않는다.

이 체크리스트를 복사하고 완료할 때마다 확인하세요:

```
진행 상황:
- [ ] 1. 콘텐츠 타입 확인 → --grp-cd 결정
- [ ] 2. 시트 Ctrl+A → Ctrl+C 후 붙여넣기
- [ ] 3. TSV 저장 & --list-hospitals 실행
- [ ] 4. hsp_id 확인 (B타입 버튼이면 블록ID도)
- [ ] 5. --dry-run SQL 확인 & 사용자 승인
- [ ] 6. 실제 INSERT 실행
- [ ] 7. --query로 결과 검증 & 사용자 확인
```

### 1. 콘텐츠 타입 & 시트 내용 확인
요청에서 콘텐츠 타입(퇴원/입원/편의/안전)을 파악해 `--grp-cd` 값을 결정한다.
사용자에게 구글 시트에서 **모든 내용을 Ctrl+A → Ctrl+C** 후 붙여넣기를 요청한다.

### 2-3. TSV 저장 & 병원 목록 확인
붙여넣은 내용을 `/tmp/hospital_guide.tsv`로 저장 후 병원 목록 확인:
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/insert_guide.py \
  /tmp/hospital_guide.tsv \
  --grp-cd <GRP_CD> \
  --list-hospitals
```

### 4. hsp_id 확인
```
[입원 생활 안내] 총 3개 병원:
  1. 해운대부민병원 - 카드 4장, 버튼 1개
  2. 일산병원 - 카드 5장, 버튼 3개 (B타입 버튼 1개 - 블록ID 필요)
```
사용자에게 처리할 병원 번호와 hsp_id를 확인. B타입 버튼이 있으면 블록 ID도 확인.

### 5. dry-run으로 SQL 미리보기
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/insert_guide.py \
  /tmp/hospital_guide.tsv \
  --grp-cd <GRP_CD> \
  --hospital-index <N> \
  --hsp-id <ID> \
  [--block-ids '{"C":"BLK_001"}'] \
  --dry-run
```
SQL 결과를 사용자에게 보여주고 확인 요청. `grp_cd`와 `guid_cd` 접두어가 올바른지 확인.

### 6. 실제 INSERT
사용자 확인 후 `--dry-run` 제거:
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/insert_guide.py \
  /tmp/hospital_guide.tsv \
  --grp-cd <GRP_CD> \
  --hospital-index <N> \
  --hsp-id <ID> \
  [--block-ids '{"C":"BLK_001"}']
```

### 7. INSERT 후 검증 (피드백 루프)
INSERT 완료 즉시 `--query`로 DB 결과를 조회해 원본 시트와 대조한다:
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/insert_guide.py \
  --query --grp-cd <GRP_CD> --hsp-id <ID>
```

스크립트 원본 출력을 그대로 보여준 후 사용자에게 확인 요청:
- **카드 수** 일치 여부 (엑셀 N장 → DB N행)
- **버튼 링크 타입(W/B/M)** 정확성
- **guid_desc 내용** 앞 20자로 원본과 대조

이상 없으면 완료. **문제 발견 시 롤백 후 재시도:**
```sql
-- DataGrip에서 실행 (dtl 먼저, mst 나중)
DELETE FROM hsp_guid_mst_dtl WHERE hsp_id = <ID> AND grp_cd = '<GRP_CD>';
DELETE FROM hsp_guid_mst     WHERE hsp_id = <ID> AND grp_cd = '<GRP_CD>';
```
삭제 확인 후 5단계(dry-run)부터 재실행.

---

## 현황 조회

카테고리별 조회 방법이 다르다. ⚠️ `insert_guide.py --query`는 **① 생활 안내(4종 grp_cd)만** 지원한다.
`HSP_GUIDE`는 `--grp-cd` 선택지에 없으므로 **② 병원안내는 `compare_figma.py --dump-links`로 조회**한다.

| 카테고리 | 조회 명령 |
|---|---|
| ① 생활 안내 | `insert_guide.py --query --grp-cd <4종 중 1> --hsp-id <ID>` |
| ② 병원안내 | `compare_figma.py --block hsp_guide --hsp-id <ID> --dump-links` |
| ③ 진료안내 | `compare_figma.py --block med_guide --hsp-id <ID> --dump-links` |

**① 생활 안내** — 특정 병원의 현재 DB 데이터 확인 (카드 본문 + 버튼 전체):
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/insert_guide.py \
  --query --grp-cd <GRP_CD> --hsp-id <ID> [--env dev|prod]
```

**② 병원안내 / ③ 진료안내** — 버튼 링크 덤프 (Figma 대조 섹션과 동일):
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/compare_figma.py \
  --block hsp_guide --hsp-id <ID> --env dev --dump-links   # 진료안내: --block med_guide
```
> 참고: `--dump-links`는 **버튼 링크가 있는 행만** 출력한다 (카드 본문 `guid_desc`는 미표시).

스크립트 실행 후, **스크립트 원본 출력을 그대로 사용자에게 보여준다.** (재렌더링 금지)

스크립트가 출력하는 컬럼 순서:
`guid_cd` | `seq` | `guid_desc` | `guid_dtl_nm` | `guid_dtl_link_tp` | `guid_dtl_link`

- `guid_cd`: `{GRP_CD}_` 접두어 제거된 `BCARD_XX` 형태
- `seq`: `hsp_guid_mst.guid_mak_seq` 실제 값
- `guid_desc`: 앞 20자 미리보기
- 버튼 없는 카드는 guid_dtl_nm / guid_dtl_link_tp / guid_dtl_link 빈 값
- 표 아래 요약: `총 N개 카드, 버튼 N개 (W:N, M:N, B:N)`

---

## Figma 대조 & 링크 UPDATE SQL 생성 (compare_figma.py)

Figma 디자인의 버튼 링크를 **병원 톡채널 DB와 대조**하고 정정용 UPDATE SQL을 만든다.
두 블록(테이블)을 지원한다:

| --block | 블록 | 테이블 | grp_cd |
|---|---|---|---|
| `hsp_guide` | 병원안내 | `hsp_guid_mst_dtl` | 필요 (기본 `HSP_GUIDE`) |
| `med_guide` | 진료안내 | `hsp_med_guid_mst_dtl` | 없음 |

**역할 분담**: Figma 노드 읽기/URL 추출은 **Claude가 figma-desktop MCP로** 수행하고,
이 스크립트는 **DB 조회 + SQL 생성**만 한다 (Figma 직접 접근 불가).

### 워크플로우

```
- [ ] 1. 사용자에게 Figma desktop에서 대상 화면(프레임) 선택 요청
- [ ] 2. mcp__figma-desktop__get_metadata 로 선택 노드 읽기 → 버튼별 URL 주석 추출
- [ ] 3. --dump-links 로 현재 DB 값 출력 → Figma 값과 1:1 대조표 작성
- [ ] 4. 차이나는 건만 {dtl_cd: 새 URL} JSON 구성
- [ ] 5. --build-sql 로 UPDATE SQL 생성 (실행 X, 사용자/DataGrip이 실행)
- [ ] 6. 반영 시점·범위 주의사항 함께 전달 (--note 활용)
```

### 1) 현재 DB 링크 덤프 (대조용)
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/compare_figma.py \
  --block hsp_guide --hsp-id <ID> --env dev --dump-links
# 진료안내: --block med_guide
```
출력 컬럼: `card | dtl_cd | 버튼명 | URL`. 이 값을 Figma 노드 주석의 버튼별 URL과 대조한다.

### 2) UPDATE SQL 생성
변경분만 `{"카드::버튼": 새 URL}` JSON으로 전달 (키 = `--dump-links`의 `card::dtl_cd`):
```bash
python3 ~/.claude/skills/hospital-guide-inserter/scripts/compare_figma.py \
  --block med_guide --hsp-id <ID> --env dev \
  --note "2026-07-01 개편과 동시 반영" \
  --build-sql '{"BCARD_4::BCARD_4_1":"https://seoul.hyumc.com/conts/102002008001000.do"}'
```
- **키 형식**: `"<card>::<dtl_cd>"` 권장 (각각 `--dump-links`의 1·2번째 컬럼). 버튼 단독키(`"BCARD_4_1"`)도 가능하나, 그 `dtl_cd`가 **여러 카드에 중복**되면(예: 입원 생활안내는 모든 카드가 `BUTTON_1`) 에러로 막히므로 카드를 명시해야 한다.
- WHERE 에 `card_col`(`guid_cd`/`med_guid_cd`)을 포함해 **카드별 정확히 1행만** 수정한다.
- `--build-sql`은 SQL 생성 전 DB를 **읽기 조회**해 키 존재·중복 여부를 검증한다 (없거나 모호하면 중단). → VPN/터널 필요.
- `START TRANSACTION` + 행별 UPDATE + 검증 SELECT + COMMIT/ROLLBACK 주석을 포함해 출력.
- **이 스크립트는 UPDATE/INSERT 를 실행하지 않는다** (검증용 SELECT만 수행). 실제 반영은 DataGrip 등에서 수행 (특히 운영).

### 주의
- **반영 시점**: Figma 주석에 "○월 ○일 개편과 동시 반영" 등 일정이 있으면 `--note`로 SQL에 명시하고, 그 전 실행을 금지한다.
- **적용 범위**: Figma가 URL 1개만 제시해도 DB엔 같은 옛 URL이 여러 카드에 깔려 있을 수 있다. 일괄/개별 여부를 **반드시 사용자에게 확인**한다.
- **prod**: `--dump-links`와 `--build-sql`은 읽기 조회만 하므로 prod 허용. 다만 운영 실제 반영(UPDATE)은 DataGrip에서.

---

## 오류 케이스 & 대응

| 오류 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| `⚠️ 기존 데이터 발견` | 동일 hsp_id+guid_cd 이미 존재 | DataGrip에서 해당 grp_cd 행 삭제 후 재실행 |
| `BLOCK_ID_REQUIRED` | B타입 버튼 블록ID 미입력 | `--block-ids '{"C":"BLK_001"}'` 추가 |
| `DB 연결 실패` | .env 미설정 또는 VPN 미연결 | .env 확인 후 VPN 접속 |
| `'prod' 환경 DB 설정이 없습니다` | PROD_DB_* 미설정 | .env에 `PROD_DB_*` 추가 |
| `[차단] prod 환경은 조회 전용` | prod에서 쓰기 시도 | `--query`만 사용, 쓰기는 DataGrip |
| `파일 없음` | TSV 경로 오류 | Write 도구로 재저장 후 경로 확인 |
| `병원 데이터를 찾을 수 없습니다` | 헤더행 파싱 실패 | 시트 첫 행 A열 값 확인 (병원명이어야 함) |

---

## 초기 설정 (최초 1회)

```bash
cp ~/.claude/skills/hospital-guide-inserter/.env.example \
   ~/.claude/skills/hospital-guide-inserter/.env
# .env에 DB 접속 정보 입력

pip install pymysql python-dotenv openpyxl
```

---

## 환경(dev/prod) 설정

단일 `.env`에서 **접두어**로 환경을 구분한다. `--env dev|prod` 로 선택 (기본값 `dev`).

```ini
# dev (DEV_ 접두어 없으면 무접두어 DB_* 로 폴백 — 기존 .env 호환)
DEV_DB_HOST=dev-db-host
DEV_DB_PORT=3306
DEV_DB_NAME=...
DEV_DB_USER=...
DEV_DB_PASSWORD=...

# prod (운영 — 폴백 없음, 명시 필수)
PROD_DB_HOST=prod-db-host
PROD_DB_PORT=3306
PROD_DB_NAME=...
PROD_DB_USER=...
PROD_DB_PASSWORD=...
```

**⚠️ prod 안전장치**: `--env prod` 는 **조회(`--query`) 전용**이다.
prod 환경에서 INSERT/UPDATE 등 쓰기 작업은 스크립트에서 차단된다 → 운영 DB 쓰기는 DataGrip 등에서 직접 수행.

```bash
# 운영 조회 — ① 생활 안내 (허용)
python3 .../insert_guide.py --query --grp-cd DISCHARGE_GUIDE --hsp-id 5 --env prod
# 운영 조회 — ② 병원안내 / ③ 진료안내 (허용)
python3 .../compare_figma.py --block hsp_guide --hsp-id 5 --env prod --dump-links
# 운영 쓰기 (차단됨)
python3 .../insert_guide.py /tmp/x.tsv --grp-cd ... --env prod   # → [차단] 메시지
```

---

## 주요 규칙 (요약)

- `guid_cd = {GRP_CD}_BCARD_01` ~ `0N` (카드 순서)
- `use_yn = Y`, `fsr_id = lst_mdf_id = 0`
- 카드 열: C~L (최대 10장), 3행 블록 구조 (내용행/버튼행/글자수행)
- 버튼 타입: `W`=웹 링크, `B`=블록 호출(블록ID 필요), `M`=사용자 발화
- 중복 데이터(동일 hsp_id+guid_cd) 있으면 INSERT 중단 및 경고

상세 필드 매핑 → `references/schema.md`

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-09 | 변경 이력 섹션 추가 |
| 2026-06-23 | dev/prod 환경 분리(`--env`, 단일 .env 접두어) 추가, prod 조회 전용 안전장치 적용 |
| 2026-06-23 | Figma 대조 모드(`compare_figma.py`) 추가 — 병원안내/진료안내 블록 DB 덤프 & UPDATE SQL 생성 |
| 2026-06-24 | 콘텐츠 3개 카테고리(① 생활 안내 / ② 병원안내 / ③ 진료안내)로 분리 — 병원안내(HSP_GUIDE)를 생활 안내 grp_cd 묶음에서 떼어내 별개 기능으로 명시, 시작 시 카테고리→작업 2단계 확인, 카테고리별 조회 방법 표 추가 |
| 2026-06-24 | 조회 명령 오류 정정 — `insert_guide.py --query --grp-cd`는 ① 4종만 지원(HSP_GUIDE 미지원). ② 병원안내·③ 진료안내 조회는 `compare_figma.py --dump-links`로 통일, prod 조회 예시도 정정 |
| 2026-06-24 | `compare_figma.py --build-sql` 카드 스코프 누락 버그 수정 — WHERE 에 `card_col`(`guid_cd`)을 포함해 카드별 1행만 수정. 키를 `"카드::버튼"` 복합키로 받고, 버튼ID가 여러 카드에 중복되면(예: 입원 생활안내 전 카드 `BUTTON_1`) DB 조회로 검증 후 에러 차단. `--dump-links`도 복합키 예시 출력 |
| 2026-06-29 | `.env.example` 갱신 — 스크립트가 실제로 읽는 `DEV_/STG_/PROD_` 접두어 스킴 반영. dev=무접두어 `DB_*`(폴백), stg=`STG_DB_*`(쓰기 허용), prod=`PROD_DB_*`(조회 전용) 키 예시 추가 |
| 2026-07-03 | `.env` 직접 열람 금지 안내 추가 — 스크립트가 `.env`를 로드하므로 Claude가 `.env`를 Read/grep하지 않고 환경은 `--env`·실행 출력으로 확정(권한 거부 루프 제거) |
