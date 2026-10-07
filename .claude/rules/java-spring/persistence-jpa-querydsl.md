# Java/Spring — 영속성 (JPA & QueryDSL)

## 트랜잭션
- Service 클래스 기본은 `@Transactional(readOnly = true)`. 데이터를 변경하는 메서드에만 `@Transactional`을 별도로 단다.
- 트랜잭션 경계는 Service 메서드 단위. Controller/Repository에 `@Transactional`을 두지 않는다.
- 외부 HTTP 호출·메일 발송 등 롤백 불가능한 작업은 트랜잭션 경계 밖으로 빼거나 커밋 후(`afterCommit`) 처리한다.

## 연관관계 & N+1
- 연관관계는 기본 `LAZY`. `EAGER` 금지.
- 목록 조회에서 연관 엔티티가 필요하면 **fetch join** 또는 QueryDSL로 한 번에 가져온다. 반복문 안에서 연관 객체를 조회하는 N+1을 만들지 않는다.
- 컬렉션 fetch join + 페이징 동시 사용 주의(메모리 페이징). 필요 시 `@BatchSize`/별도 조회로 분리.

## 쿼리 선택
- **단순/정적 조회** → Spring Data JPA 메서드 네이밍 쿼리 (`findByHspCdAndUseYn`).
- **동적 조건/조인/집계** → QueryDSL. `BooleanBuilder` 또는 `BooleanExpression` 동적 조건 메서드로 null-safe 하게 조립.
- 복잡한 정적 쿼리는 `@Query`(JPQL). 네이티브 쿼리는 꼭 필요할 때만.

## QueryDSL 규칙
- 커스텀 쿼리는 `{Entity}RepositoryCustom` 인터페이스 + `{Entity}RepositoryImpl` 구현으로 분리하고, `{Entity}Repository`가 함께 상속한다.
- 생성된 Q타입(`Q...`)은 `build/generated/querydsl`에 생성된다(빌드 산출물, 커밋하지 않음).
- 동적 조건은 `private BooleanExpression cond(...)` 메서드로 추출해 재사용·null 처리한다.

## 기타
- 조회 직후 같은 데이터를 다시 조회하지 않는다(불필요한 쿼리).
- `save`는 신규/병합 의미를 이해하고 사용. 더티체킹으로 충분하면 명시적 `save` 호출을 남발하지 않는다.
- 대량 처리(batch)는 `karechat-server-batch` 패턴을 따르고, 청크/페이징으로 메모리를 관리한다.
