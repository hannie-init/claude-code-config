# Java/Spring — 테스트

JUnit5 + Mockito 기반. `/code` 스킬의 2단계(테스트)가 이 규칙을 따른다.

## 공통
- `@DisplayName`은 **한국어**로, 무엇을 검증하는지 명확히.
- `given / when / then` 주석으로 구조를 명시한다.
- 테스트 파일 위치는 `src/test/java/`에 프로덕션과 동일한 패키지 경로.
- 한 테스트는 한 가지를 검증. 단언은 AssertJ(`assertThat`) 권장.

## Service 단위 테스트
- `@ExtendWith(MockitoExtension.class)`, 대상은 `@InjectMocks`, 의존성은 `@Mock`.
- DB·외부 호출은 모두 Mock으로 대체. 비즈니스 규칙과 분기를 검증한다.

```java
@ExtendWith(MockitoExtension.class)
class FooServiceTest {
    @InjectMocks private FooService fooService;
    @Mock private FooRepository fooRepository;

    @Test
    @DisplayName("존재하지 않는 병원이면 예외를 던진다")
    void create_throws_when_hsp_not_found() {
        // given
        given(fooRepository.findById(anyLong())).willReturn(Optional.empty());
        // when & then
        assertThatThrownBy(() -> fooService.create(request))
            .isInstanceOf(CustomException.class);
    }
}
```

## Controller 슬라이스 테스트
- `@WebMvcTest({Controller}.class)`, `MockMvc` 주입, Service는 `@MockBean`.
- 요청/응답 JSON, 상태 코드, `@Valid` 검증 실패 응답을 검증한다.

## 필수 케이스
- **정상**: 기본 성공 시나리오.
- **예외**: 정의된 모든 비즈니스 예외(ErrorCode) 분기.
- **경계값**: null, 빈 문자열, 최대/최소, 권한 없음 등.
