# Java/Spring — v2 모던 구조 (신규 코드 권장)

karechat-server는 `v2/` 패키지에서 레이어드 → 헥사고날/DDD풍 구조로 마이그레이션 중이다.
**신규 기능·모듈**은 이 구조를 권장한다. 단, 같은 도메인의 기존 v2 코드가 있으면 그 패턴을 우선 따른다.

## 패키지 구조
```
v2/
  application/   # 유스케이스 = 애플리케이션 서비스 (도메인 조합, 트랜잭션 경계)
  domain/        # 엔티티, 값 객체, enum, 도메인 서비스, 리포지토리 인터페이스
  presentation/  # 컨트롤러, 요청/응답 모델 (외부 노출 계층)
  common/        # util, 공통 컨텍스트(CurrentContext 등), 공유 타입
```

도메인별로 다시 묶는다. 예: `v2/application/checkup/...`, `v2/presentation/chatbot/checkup/...`.

## 의존 방향
- `presentation → application → domain`. domain은 바깥(스프링/인프라)을 모르게 유지한다.
- 리포지토리 **인터페이스는 domain**, 구현(JPA/QueryDSL)은 인프라 계층에 둔다.
- 외부 시스템 호출은 포트(인터페이스)로 추상화하고 application에서 조합한다.

## 모던 코드 스타일
- **DTO는 record**로 작성하고 검증 어노테이션을 함께 둔다.
  ```java
  public record CreateReservationRequest(
      @NotNull Long hspId,
      @NotBlank String mbrId
  ) {}
  ```
- 변환은 record의 정적 팩토리(`from`/`of`)로. 별도 매퍼가 있으면 그 패턴을 따른다.
- 불변성 우선: 도메인 객체는 setter 없이 의미 있는 메서드로 상태를 바꾼다.
- `Optional`을 반환 타입에 적절히 사용하되 필드/파라미터에는 쓰지 않는다.
- 컴포넌트는 단일 책임으로 잘게 나눈다(`...Component`, `...Service`).

> 빌드는 여전히 Java 11이다. record는 Java 16+ 정식 문법이므로, 사용 전 해당 모듈의 `sourceCompatibility`를 확인한다. 11이면 record 대신 Lombok `@Getter @Builder` 불변 DTO를 쓰고, 모듈이 16+로 올라가면 record로 전환한다.
