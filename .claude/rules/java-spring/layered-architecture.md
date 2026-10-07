# Java/Spring — 레이어드 아키텍처

의존 방향은 **Controller → Service → Repository** 단방향. 역방향 의존 금지.

## Controller
- `@RestController` + `@RequiredArgsConstructor` + `@RequestMapping("{base-path}")` + `@Slf4j`.
- 책임은 **요청 검증 · Service 호출 · 응답 변환**까지만. 비즈니스 로직을 두지 않는다.
- 요청 본문은 DTO로 받고 `@Valid`로 검증한다. Entity를 직접 받거나 반환하지 않는다.
- 반환은 `ResponseEntity<...>` 사용. 기존 모듈의 공통 응답 래퍼가 있으면 그것을 따른다.
- Swagger `@Api`/`@ApiOperation`으로 설명을 단다.

```java
@Api(tags = {"..."})
@RestController
@RequiredArgsConstructor
@RequestMapping("dfd/api/...")
@Slf4j
public class FooController {
    private final FooService fooService;

    @ApiOperation("...")
    @PostMapping
    public ResponseEntity<FooResponseDto> create(@Valid @RequestBody FooRequestDto request) {
        return ResponseEntity.ok(fooService.create(request));
    }
}
```

## Service
- `@Service` + `@RequiredArgsConstructor`. 클래스 기본은 `@Transactional(readOnly = true)`, 쓰기 메서드에만 `@Transactional`.
- 모든 비즈니스 규칙·예외 케이스를 여기서 처리한다.
- Repository를 호출해 Entity를 다루고, Controller로 돌려줄 때는 DTO로 변환한다.
- 외부 호출(다른 모듈/HTTP)은 별도 컴포넌트로 분리하고 Service에서 조합한다.

## Repository
- `JpaRepository<Entity, ID>` 상속. 단순 조회는 메서드 네이밍 쿼리.
- 복잡/동적 쿼리는 QueryDSL — [persistence-jpa-querydsl.md](persistence-jpa-querydsl.md).

## DTO
- Request/Response 분리. 요청 DTO에 `javax.validation` 어노테이션(`@NotNull`, `@NotBlank`, `@Size` 등)으로 제약 명시.
- Entity ↔ DTO 변환은 DTO의 정적 팩토리(`from`/`of`) 또는 전용 매퍼에 둔다. Controller에 변환 로직을 흩지 않는다.
- 레거시는 Lombok `@Getter`/`@Builder` DTO, 신규는 record DTO 권장([v2-modern.md](v2-modern.md)).

## Entity (domain)
- JPA Entity는 `@Entity` + `@Getter`. **`@Setter` 금지** — 상태 변경은 의미 있는 도메인 메서드로.
- 기본 생성자는 `@NoArgsConstructor(access = AccessLevel.PROTECTED)`.
- 생성은 `@Builder` 또는 정적 팩토리. `@Data`/`@AllArgsConstructor` 전체 노출 금지.
- 연관관계는 기본 `LAZY` (`@ManyToOne(fetch = FetchType.LAZY)`).
