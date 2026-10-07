# Kotlin/Spring — 코딩 스타일

자바 스타일을 그대로 옮기지 말고 **관용적인 Kotlin**으로 작성한다.
포맷팅(들여쓰기, import 순서 등)은 ktlint 결과를 따르고, 아래는 그 외의 설계·작성 규칙이다.
기존 코드 패턴과 충돌하면 해당 프로젝트의 현행 패턴이 우선한다.

## Null 처리
- `!!` 사용 금지. 테스트 코드에서만 예외적으로 허용한다.
- null이 될 수 없는 값은 non-null 타입으로 선언한다. "일단 `?`"로 선언하지 않는다.
- 조회 결과가 없으면 엘비스 연산자로 의미 있는 예외를 던진다.
  - 예: `repository.findByIdOrNull(id) ?: throw KarechatException(ErrorCode.ACCOUNT_NOT_FOUND)`
- 반환 타입에 `Optional`을 쓰지 않고 `T?`를 쓴다. Spring Data는 `findById` 대신 `findByIdOrNull`을 쓴다.
- 자바 API(서블릿, 자바 라이브러리 등)에서 받은 값은 변수 타입을 명시해 플랫폼 타입을 경계에서 끊는다.
  - 예: `val traceId: String? = request.getHeader("X-Trace-Id")`

## 변수와 불변성
- 기본은 `val`. 재할당이 필요한 경우에만 `var`를 쓴다.
- 외부에 노출하는 컬렉션은 `List`/`Set`/`Map`(읽기 전용) 타입으로 공개한다.
  - 내부 변경이 필요하면 `private val _items = mutableListOf<T>()` + `val items: List<T> get() = _items` 패턴.
- `var`와 가변 컬렉션을 함께 쓰지 않는다 (`var list: MutableList<T>` 금지).
- `lateinit`은 테스트의 `@Autowired`/`@BeforeEach` 초기화 등 프레임워크가 주입 후 초기화하는 경우에만 쓴다.

## 클래스 설계
- DTO, 요청/응답 객체는 `data class`로 작성한다. 요청 DTO에는 `jakarta.validation` 제약을 함께 둔다.
- **JPA 엔티티는 `data class`로 만들지 않는다.** 일반 `class`로 작성하고, 필요하면 `equals`/`hashCode`를 id 기반으로 직접 구현한다. `toString`에 연관관계 필드를 넣지 않는다.
  - 현행 패턴(partners-center): 컬럼은 주 생성자 프로퍼티(`var` 허용 — JPA 더티체킹), `id`는 본문에 `var id: Long? = null`, 생성/수정 시각은 `@CreationTimestamp`/`@UpdateTimestamp` + `Instant`.
- 엔티티 ↔ DTO 변환은 확장 함수로 작성한다 (예: `fun Account.toResponse() = AccountSummaryResponse(...)`).
- 오버로딩이나 빌더 패턴 대신 기본 인자와 이름 있는 인자를 쓴다.
- 결과 상태가 여러 개인 경우 `sealed class`/`sealed interface` + `when`으로 표현하고, `when`에 불필요한 `else`를 두지 않아 컴파일러가 누락을 잡게 한다. (예: `EmailOtpService.SendResult`/`VerifyResult`)
- getter/setter 메서드를 직접 만들지 않는다. 프로퍼티를 쓰고, 외부 수정이 불필요하면 `private set`을 쓴다.

## Spring
- 의존성은 생성자 주입 + `private val`로 받는다. 필드 `@Autowired`와 `lateinit var` 주입은 쓰지 않는다(테스트 제외).
- `kotlin-spring`(all-open), `kotlin-jpa`(no-arg) 플러그인이 적용돼 있다는 전제로 작성한다. 클래스에 수동으로 `open`을 붙이지 않는다.
- JSON 직렬화는 `jackson-module-kotlin` 기준으로 동작한다. 요청 DTO의 선택 필드는 nullable 또는 기본값으로 표현한다.
- 트랜잭션 경계·readOnly 원칙은 [java-spring/persistence-jpa-querydsl.md](../java-spring/persistence-jpa-querydsl.md)를 따른다.
- 로깅은 현행 패턴인 `private val log = LoggerFactory.getLogger(javaClass)` (SLF4J)를 기본으로 쓴다. 프로젝트에 `kotlin-logging` 의존성이 있으면 `KotlinLogging.logger {}` 패턴을 따른다. 플레이스홀더(`log.info("id={}", id)`) 사용, 민감정보 로깅 금지.

## 스코프 함수
- 스코프 함수(`let`, `run`, `apply`, `also`, `with`)를 2단계 이상 중첩하지 않는다.
- 중첩 람다에서 `it`을 겹쳐 쓰지 않는다. 바깥 람다 파라미터에는 이름을 붙인다.
- 단순 null 체크는 `?.let` 대신 `if (x != null)` 또는 엘비스 + early return(`?: return`)을 우선한다.
- 용도 기준 — `apply`: 객체 초기화/설정, `also`: 로깅 등 부수 효과, `let`: nullable 값 변환.

## 확장 함수
- `Any`, `String`, `Long` 등 범용 타입에 도메인 의미를 가진 확장 함수를 만들지 않는다.
- 외부 의존성(클라이언트, 리포지토리)이 필요한 비즈니스 로직은 확장 함수가 아니라 서비스 클래스 메서드로 작성한다.
- 정적 유틸 클래스(`object XxxUtils`) 대신 최상위 함수나 확장 함수를 쓴다.

## 예외 처리
- 비즈니스 예외는 프로젝트 공통 예외(`KarechatException(ErrorCode)`)로 던진다. 새 에러는 `ErrorCode` enum에 항목을 추가한다(`{DOMAIN}_{REASON}`, status + 기본 메시지).
- `runCatching { }.getOrNull()`처럼 실패 원인을 버리는 코드를 쓰지 않는다. 실패를 무시하는 경우에도 `onFailure`로 로그를 남긴다.
- `catch (e: Throwable)`을 쓰지 않는다.
- 전역 처리 원칙(컨트롤러 개별 try/catch 금지 등)은 [java-spring/exception-handling.md](../java-spring/exception-handling.md)를 따른다.

## 코루틴 (사용하는 모듈에 한함)
- 기본은 동기(Spring MVC) 코드다. 요청받지 않은 상태에서 기존 동기 코드를 `suspend`로 바꾸지 않는다.
- `GlobalScope` 사용 금지.
- 요청 처리 경로(컨트롤러, 서비스)에서 `runBlocking` 사용 금지. `main`, 테스트, 배치 진입점에서만 허용한다.
- `suspend` 함수 안에서 JPA/JDBC 등 블로킹 호출은 `withContext(Dispatchers.IO)`로 감싼다.
- 병렬 호출은 `coroutineScope { }` 안에서 `async`/`await`로 작성한다.
- 코루틴 안에서 `runCatching`이나 `catch (e: Exception)`을 쓸 때 `CancellationException`은 다시 던진다.

## 컬렉션과 함수형
- 컬렉션 처리에 `.stream()`/`Collectors`를 쓰지 않고 Kotlin 컬렉션 함수(`map`, `filter`, `associateBy`, `groupBy` 등)를 쓴다.
- 대용량이거나 연산이 긴 체인은 `asSequence()`를 고려한다.
- 체인이 길어지면 중간 결과에 이름 있는 변수를 둔다.

## 변경 이력
- 2026-10-06: 최초 작성. 사용자 제공 Kotlin 스타일 가이드를 기반으로 partners-center 현행 패턴(로깅 SLF4J, 엔티티 구조, ErrorCode)을 반영.
