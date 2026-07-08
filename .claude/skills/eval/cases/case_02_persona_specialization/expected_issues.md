# 반드시 발견해야 할 이슈

## MUST (필수 발견)

- [ ] **N+1 쿼리 — generateMonthlySummary (line 28)**: `orders` 루프 안에서 매 반복마다 `orderItemRepository.findByOrderId(order.getId())`를 호출한다. 주문 100건이면 쿼리 101개가 발생한다. `JOIN FETCH` 또는 `@EntityGraph`로 일괄 조회해야 한다.
- [ ] **N+1 쿼리 — getPendingOrdersSummary (line 48)**: `generateMonthlySummary`와 동일 패턴이 반복된다. N+1이 두 곳에서 중복으로 발생하며, 공통 조회 로직이 분리되지 않아 수정 시 누락 위험이 있다.
- [ ] **SRP 위반 — generateMonthlySummary (line 36-37)**: 요약 계산 메서드가 PDF 생성(`pdfExportService`)과 이메일 발송(`emailService`)을 직접 수행한다. 리포팅 서비스가 배달 채널 결정까지 담당하게 되어, 이메일 로직 변경 시 summary 로직을 건드려야 한다.

## SHOULD (발견하면 좋음)

- [ ] **total 계산 로직 중복**: `generateMonthlySummary`, `getOrderDetail`, `getPendingOrdersSummary` 세 곳에서 동일한 `unitPrice * quantity` 합산 로직이 반복된다. `OrderSummaryDto` 생성자나 별도 헬퍼로 추출해야 한다.
- [ ] **@Transactional 범위 과도**: 이메일 발송이 `@Transactional` 범위 안에 포함되어 이메일 SMTP 오류가 트랜잭션 롤백을 유발한다. 이메일 발송은 트랜잭션 커밋 후 이벤트 발행 방식으로 분리해야 한다.
