# 반드시 발견해야 할 이슈

## MUST (필수 발견)

- [ ] **CRITICAL — 하드코딩된 API 키 (line 11)**: `EXTERNAL_GATEWAY_KEY = "sk-prod-a1b2c3d4e5f6g7h8i9j0"` 소스 코드에 프로덕션 API 키가 하드코딩되어 있다. 리포지토리에 커밋되면 키가 노출된다. `@Value("${gateway.api.key}")` 또는 Secrets Manager로 교체해야 한다.
- [ ] **HIGH — Optional.get() NPE 위험 — processPayment (line 26)**: `accountRepository.findById(...).get()`은 계정이 없을 경우 `NoSuchElementException`을 던지지만, 이 예외는 바깥 `catch (Exception e)`에 잡혀 단순히 `error` 결과로 묻힌다. `orElseThrow()`로 명시적 예외를 던지거나 `isPresent()` 체크가 필요하다.
- [ ] **HIGH — Optional.get() NPE 위험 — createRefund (line 48, 52)**: 동일하게 `paymentRepository.findById(...).get()`과 `accountRepository.findById(...).get()`이 반복된다.
- [ ] **HIGH — 예외 삼킴 (line 34, 58)**: `catch (Exception e)` 블록이 예외 메시지나 스택 트레이스를 로깅하지 않고 단순 에러 응답을 반환한다. 운영 환경에서 실패 원인을 추적할 수 없다.
- [ ] **MEDIUM — 입력 유효성 검사 중복 (line 22-24, 43-45)**: `processPayment`와 `createRefund` 양쪽에서 동일한 `amount <= 0`, `id == null` 검사가 반복된다. 공통 유효성 검사 메서드나 Bean Validation(`@Positive`, `@NotNull`)으로 통합해야 한다.
- [ ] **LOW — 매직 넘버 10000 (line 29)**: 부정거래 임계값이 상수나 설정 없이 하드코딩되어 있다. `FRAUD_DETECTION_THRESHOLD` 상수 또는 설정값으로 추출해야 한다.

## SHOULD (발견하면 좋음)

- [ ] **경쟁 조건 — 잔액 차감 (line 31-33)**: 계좌 조회와 잔액 차감 사이에 동시 요청이 들어오면 음수 잔액이 발생할 수 있다. `@Transactional` + 비관적 락 또는 DB 레벨 `UPDATE ... WHERE balance >= amount`가 필요하다.
