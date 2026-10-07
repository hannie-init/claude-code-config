---
name: db-query
description: |
  로컬 어디서든 사용하는 글로벌 MySQL 조회/실행 스킬. 단일 .env에서 dev/stg/prod를
  접두어로 구분하며, dev/stg는 쓰기 허용, prod는 조회(SELECT/SHOW/DESC/EXPLAIN) 전용으로 강제한다.
  임의 테이블에 대한 읽기 전용 SELECT가 필요할 때 사용한다.

  다음 상황에서 사용:
  - "DB 조회해줘", "이 테이블 확인해줘", "쿼리 실행해줘"
  - 특정 스킬(hospital-admission-setup 등)이 다루지 않는 테이블 조회
  - stte_ccrc / usr_hsp_ccrc 등 임의 테이블 SELECT
---

# DB Query (global)

로컬 전역에서 쓰는 읽기 우선 DB 조회 스킬.
글로벌 CLAUDE.md의 "DB 접근은 전용 스킬 스크립트를 경유한다" 규칙을 따르는 공용 진입점이다.

> **DB 접속 정보 취급**: 스크립트가 `.env`를 스스로 로드한다. `.env`를 `Read`/`cat`/`grep`으로 열람하지 **말 것**. prod 여부가 필요하면 사용자에게 확인한다.

## 접속 설정 (.env)

`~/.claude/skills/db-query/.env` — 접두어로 환경 구분:
- `dev`: `DEV_DB_*` (없으면 무접두어 `DB_*` 폴백)
- `stg`: `STG_DB_*`
- `prod`: `PROD_DB_*`

`.env.example` 참고. (초기값은 hospital-guide-inserter의 .env를 복사해 사용)

## 안전 정책

| 환경 | 쓰기(INSERT/UPDATE/DELETE/DDL) | 조회 |
|------|-------------------------------|------|
| dev  | **사용자 승인 후** `--allow-write` 로만 실행 | 허용 |
| stg  | **사용자 승인 후** `--allow-write` 로만 실행 | 허용 |
| prod | **차단** (스크립트가 거부, `--allow-write` 무시) | 허용 |

- SELECT/SHOW/DESC/DESCRIBE/EXPLAIN/WITH 외 구문은 "쓰기"로 판정된다.
- **dev/stg 쓰기 워크플로우 (필수)**:
  1. `--allow-write` 없이 실행 → 스크립트가 쓰기를 감지하면 SQL을 출력하고 exit 3 으로 중단.
  2. 그 SQL을 **사용자에게 보여주고 명시적 승인**을 받는다.
  3. 승인받은 뒤에만 동일 명령에 `--allow-write` 를 붙여 실행한다.
- prod 쓰기는 `--allow-write` 를 붙여도 항상 차단된다. 필요하면 SQL만 생성해 사용자 승인을 받는다.

## 사용법

```bash
# 조회 (dev 기본)
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --sql "SELECT * FROM stte_ccrc WHERE grp_cd LIKE 'HSPTZ%' LIMIT 20"

# database 오버라이드 (member DB 등, 동일 host/계정일 때)
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --db <member_db_name> --sql "SELECT ..."

# 운영 조회 (쓰기 자동 차단)
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env prod --sql "SELECT ..."

# dev/stg 쓰기: 1) 먼저 승인 없이 실행 → SQL 확인용 출력 후 중단(exit 3)
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --sql "UPDATE ... WHERE ..."
#            2) 사용자 승인 후에만 --allow-write 붙여 재실행
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --allow-write --sql "UPDATE ... WHERE ..."
```

- `--sql`은 세미콜론으로 여러 구문을 넣을 수 있다(각 구문 결과를 순서대로 출력).
- 결과셋이 있으면 표로, 쓰기면 affected rows를 출력한다.
