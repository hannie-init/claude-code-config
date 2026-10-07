# Java/Spring — 의존성 주입 & Lombok

## 의존성 주입
- **생성자 주입만 사용**한다. 필드는 `private final`, 클래스에 `@RequiredArgsConstructor`.
- `@Autowired` 필드 주입 금지. setter 주입 금지.
- 의존성이 너무 많으면(대략 5개 이상) 책임 분리를 검토한다.

```java
@Service
@RequiredArgsConstructor
public class FooService {
    private final FooRepository fooRepository;
    private final BarClient barClient;
}
```

## Lombok 사용 규칙
허용·권장:
- `@RequiredArgsConstructor` — DI용 생성자.
- `@Getter` — DTO/Entity 조회용.
- `@Builder` — 생성자 인자가 많은 객체 생성.
- `@Slf4j` — 로깅. `log.info/debug/warn/error` 사용, `System.out` 금지.
- `@NoArgsConstructor(access = AccessLevel.PROTECTED)` — JPA Entity 기본 생성자.

지양:
- Entity에 `@Setter`, `@Data`, `@AllArgsConstructor`(전체 공개 생성자) — 불변성·캡슐화 깨짐.
- `@SneakyThrows` — 예외를 숨긴다. 명시적으로 처리하거나 던진다.
- 무분별한 `@EqualsAndHashCode`(특히 JPA Entity의 연관 필드 포함) — 순환/성능 문제.

## 로깅
- `@Slf4j`로 선언하고 SLF4J 플레이스홀더(`log.info("id={}", id)`)를 쓴다. 문자열 `+` 연결 금지.
- 민감정보(개인정보·토큰)는 로그에 남기지 않는다.
- 예외 로깅 시 메시지와 함께 예외 객체를 넘긴다: `log.error("처리 실패", e)`.
