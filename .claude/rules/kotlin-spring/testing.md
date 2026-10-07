# Kotlin/Spring — 테스트

Kotest + MockK 기반 (Mockito·AssertJ를 쓰지 않는다). partners-center 현행 패턴 기준.

## 공통
- 테스트 이름·시나리오 설명은 **한국어**로, 무엇을 검증하는지 명확히.
- 테스트 파일 위치는 `src/test/kotlin/`에 프로덕션과 동일한 패키지 경로.
- 한 테스트는 한 가지를 검증한다.
- 공용 픽스처·테스트 더블은 `support/` 패키지에 둔다 (예: `AccountFixture`, `CapturingEmailSender`).
- 작업 후 `./gradlew ktlintCheck test`로 검증한다.

## 단위 테스트 — Kotest + MockK
- 스펙 스타일은 **BehaviorSpec**(Given/When/Then, 한국어 문자열)을 기본으로 하되, 같은 패키지의 기존 스펙 스타일이 있으면 그것을 따른다.
- 의존성은 `mockk<T>()`로 대체하고 `every { } returns`, `verify { }`, `slot()`을 쓴다. 부수 효과만 있는 협력자는 `mockk(relaxed = true)` 허용(이유를 주석으로).
- 단언은 Kotest matcher(`shouldBe`, `shouldBeInstanceOf<T>()` 등).
- 시간이 로직에 개입하면 `Clock.fixed(...)`를 주입해 고정한다.

```kotlin
class EmailOtpServiceTest :
    BehaviorSpec({
        val clock = Clock.fixed(Instant.parse("2026-09-09T00:00:00Z"), ZoneOffset.UTC)

        Given("사용자가 누른 재전송") {
            val otpRepo = mockk<AuthOtpRepository>(relaxed = true)
            every { otpRepo.save(any()) } answers { firstArg() }

            Then("is_resend=true 로 적재된다") {
                // when
                val result = service.send(accountId, resend = true)
                // then
                result.shouldBeInstanceOf<SendResult.Sent>()
                verify { otpRepo.save(match { it.isResend }) }
            }
        }
    })
```

- 스프링 빈 목이 필요한 슬라이스 테스트는 springmockk의 `@MockkBean`을 쓴다(Mockito `@MockBean` 금지).

## 통합 테스트 — JUnit5 + Testcontainers
필터 순서·세션·DB 제약처럼 mock 층에서 드러나지 않는 것은 실 DB + 실 HTTP로 검증한다.

- `@SpringBootTest(webEnvironment = RANDOM_PORT)` + `@Testcontainers` + MySQL 컨테이너.
- 테스트 함수는 JUnit `@Test` + 백틱 한국어 함수명: ``fun `존재하지 않는 사용자 조회 시 예외가 발생한다`()``.
- 의존성 주입은 `@Autowired lateinit var` 허용(테스트 한정).
- 실 HTTP 경유 시 트랜잭션 롤백에 의존하지 않는다(서버 스레드가 별도 트랜잭션) — 격리는 테스트별 고유 데이터(고유 이메일 등)로 한다.
- 왜 통합 테스트여야 하는지(단위로 못 잡는 이유)를 클래스 KDoc에 한 줄 남긴다.

## 필수 케이스
- **정상**: 기본 성공 시나리오.
- **예외**: 정의된 모든 비즈니스 예외(ErrorCode) 분기. sealed result라면 모든 하위 타입.
- **경계값**: null, 빈 문자열, 최대/최소, 권한 없음, 만료/횟수 초과 등.

## 변경 이력
- 2026-10-06: 최초 작성. partners-center 테스트 구조(Kotest BehaviorSpec 단위 + JUnit5/Testcontainers 통합) 기준.
