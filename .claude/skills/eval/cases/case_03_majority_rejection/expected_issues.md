# 반드시 발견해야 할 이슈

## MUST (필수 발견)

- [ ] **getRecentLogs limit 파라미터 미검증 (line 44)**: `limit`에 음수나 극단적으로 큰 값이 전달되면 예상치 못한 동작이 발생할 수 있다. 외부 입력이라면 1~100 범위 검증이 필요하다.
- [ ] **isEligible이 public API에서 제외되지 않음 (line 48)**: `// Visible for testing` 주석이 붙은 메서드가 `package-private`으로 노출된다. 테스트를 위한 내부 메서드는 인터페이스 계약 밖에 있어야 하며, `@VisibleForTesting` 애노테이션 또는 별도 전략으로 처리하는 것이 낫다.
- [ ] **NotificationSender.send() 실패 시 트랜잭션 부분 커밋 (line 37)**: `@Transactional` 범위 안에서 외부 시스템 호출(notificationSender)이 실패해도 이미 저장된 성공 로그가 롤백되지 않는다. 외부 호출 후 DB 기록이 불일치 상태가 될 수 있다.

## 의도적 논쟁 대상 이슈 (다수결 기각 검증용)

- [ ] **`@Autowired` 필드 주입 사용**: 필드 주입이 아닌 생성자 주입을 권장한다는 LOW 지적이 나올 수 있다. 그러나 이 코드는 Spring Boot 표준 패턴을 따른 것이며, 생성자 주입은 선호의 차이이지 버그가 아니다. 두 리뷰어가 DISAGREE하면 R3에서 기각되어야 한다.

## SHOULD (발견하면 좋음)

- [ ] **dispatch 메서드가 너무 많은 일을 함**: 필터링 + 발송 + 로깅을 한 메서드가 담당한다. 그러나 50줄 미만이고 명확하므로 필수 수준은 아니다.
