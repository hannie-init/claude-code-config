# 반드시 발견해야 할 이슈

## MUST (필수 발견)

- [ ] **getAvailableStock가 예약 재고를 차감하지 않음 (line 25)**: 주석에도 명시되어 있듯, `total`에서 `reserved`를 빼지 않아 실제 가용 재고보다 많은 수량을 반환한다. `reserveStock`가 이 값을 기반으로 예약을 허용하므로 오버셀링이 발생한다.
- [ ] **reserveStock의 체크-후-행동(Check-Then-Act) 경쟁 조건 (line 35)**: `getAvailableStock()`와 `reservationRepository.save()` 사이에 다른 트랜잭션이 동일 재고를 예약할 수 있다. 비관적 락(`@Lock(PESSIMISTIC_WRITE)`) 또는 DB 레벨 락이 필요하다.

## R4 회귀 감지 대상 이슈 (수정 후 발생)

수정 시나리오: `getAvailableStock`에 `reservationRepository.countActiveByProductId(productId)`를 추가해 `total - reserved`를 반환하도록 수정한다.

- [ ] **수정 후 회귀 — 두 번의 별도 쿼리 사이 경쟁 조건**: `getTotalStock`과 `countActiveByProductId` 두 쿼리가 별개의 SELECT로 실행되므로, 그 사이에 새 예약이 생기면 `available`이 실제보다 높게 계산된다. 완전한 수정은 두 쿼리를 단일 DB 트랜잭션 또는 단일 쿼리로 통합해야 한다.
- [ ] **수정 후 회귀 — `@Transactional(readOnly = true)` 내 두 번의 쿼리**: readOnly 트랜잭션이라도 두 SELECT 사이에 다른 트랜잭션이 커밋되면 non-repeatable read가 발생한다. `SERIALIZABLE` 격리 수준 또는 SELECT FOR UPDATE가 필요하다.

## SHOULD (발견하면 좋음)

- [ ] **auditLogRepository.record 서명의 null 파라미터**: `releaseReservation`에서 `productId`가 `null`로 전달된다 (line 41). auditLog가 null productId를 처리하지 않으면 오류가 발생한다.
