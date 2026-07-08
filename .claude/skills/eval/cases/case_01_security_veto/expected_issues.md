# 반드시 발견해야 할 이슈

## MUST (필수 발견)

- [ ] **SQL Injection — searchByUsername (line 16)**: `username` 파라미터를 검증 없이 직접 SQL 문자열에 연결한다. 공격자가 `' OR '1'='1` 같은 입력으로 모든 레코드를 조회할 수 있다.
- [ ] **SQL Injection — searchByEmail (line 21)**: `email` 파라미터가 동일하게 문자열 연결로 삽입된다. WHERE 절 조건을 우회하거나 UNION 기반 데이터 추출이 가능하다.
- [ ] **SQL Injection — searchByRole (line 31)**: `role`과 `department` 두 파라미터 모두 직접 연결된다. 공격자가 두 파라미터 중 하나만 제어해도 전체 users + departments 테이블을 덤프할 수 있다.

## SHOULD (발견하면 좋음)

- [ ] **SQL Injection — findById (line 26)**: `Long` 타입이라 직접적 SQL Injection 위험은 낮으나, `toString()` 경로에서 예기치 않은 문자열이 삽입될 경우를 고려해 PreparedStatement로 통일할 것을 권고한다.
- [ ] **SQL Injection — existsByUsername (line 38)**: `searchByUsername`과 동일 패턴이 반복된다.
- [ ] **수정 권고 — PreparedStatement 파라미터 바인딩**: 모든 쿼리를 `JdbcTemplate.queryForList(sql, username)` 형태의 파라미터 바인딩으로 교체해야 한다.
