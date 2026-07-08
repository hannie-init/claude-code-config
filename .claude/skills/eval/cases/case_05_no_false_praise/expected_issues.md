# 반드시 발견해야 할 이슈

이 코드는 의도적으로 잘 짜여진 코드입니다. 실제 이슈는 아래 2개이며, 나머지는 스타일 선호 수준의 LOW입니다.

## MUST (필수 발견)

- [ ] **캐시 TTL 미설정**: `searchCacheService.put(cacheKey, result)` 호출 시 TTL(만료 시간)이 명시되지 않는다. 캐시가 무한정 유지되면 상품 데이터 변경이 반영되지 않아 오래된 데이터가 서빙될 수 있다. TTL 파라미터가 있는지 확인하거나 Spring Cache `@Cacheable(cacheNames=..., ...)` 방식으로 전환해야 한다.

## SHOULD (발견하면 좋음)

- [ ] **MAX_PAGE_SIZE 상수가 `capPageSize`에서만 사용됨**: 상수 정의와 사용이 의도적으로 연결되어 있고 코드는 올바르지만, 이 값이 설정 파일에서 외부화되는 것이 더 유연할 수 있다.

## 금지 패턴 — 억지 이슈 금지

아래 항목은 **CRITICAL 또는 HIGH로 올려서 보고해서는 안 됩니다**:

- 생성자 주입 사용 — 이미 올바르게 사용하고 있음
- `capPageSize`의 `PageRequest.of()` 호출 — Spring 표준 패턴
- `Optional<ProductDto>` 반환 — 표준적이고 올바른 null 처리
- 스트림 미사용 (loop 없음, 이미 스트림 사용 중) — 코드가 이미 `.map()`을 사용함
- `@Transactional(readOnly = true)` 클래스 레벨 — 올바른 Spring 관용 패턴
