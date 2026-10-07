# Java/Spring — 예외 처리

## 기본 원칙
- 비즈니스 예외는 **CustomException(런타임 예외)** 으로 던지고, 전역 `@RestControllerAdvice`에서 응답으로 변환한다.
- **JDK 범용 예외 직접 던지기 지양**: 검증·비즈니스 실패에 `IllegalArgumentException`/`IllegalStateException` 등을 직접 던지지 않는다. 프로젝트 표준 CustomException(ErrorCode) 사용 — 예: backoffice는 `KarechatException(ErrorCode.INVALID_INPUT_VALUE, "메시지")`. (사용자 지시, 2026-09-07)
- **generic `RuntimeException` 재래핑 금지**: `catch (Exception e) { throw new RuntimeException(..., e) }`는 ErrorCode/HTTP 매핑을 소실시킨다. 표준 CustomException(ErrorCode.INTERNAL_SERVER_ERROR, e)으로 변환하고, 이미 표준 예외면 그대로 재전파한다.
- 예외를 삼키지 않는다: `catch (Exception e) {}` 금지. 잡았으면 로깅 후 재던지거나 의미 있게 처리한다.
- `checked exception`을 무의미하게 throws로 전파하지 않는다(`throws Exception` 광범위 선언 지양). 경계에서 표준 CustomException으로 변환한다.
- 컨트롤러에 개별 try/catch로 에러 응답을 조립하지 않는다 — 전역 핸들러에 위임하고, 응답에 `e.getMessage()` 원문을 노출하지 않는다.

## ErrorCode 패턴 (karechat)
에러는 `ErrorCode` enum으로 코드·메시지·HTTP 상태를 한곳에 정의하고, `{도메인}ErrorGenerator`로 예외를 생성한다.

```java
public enum ErrorCode {
    INVALID_REQUEST(HttpStatus.BAD_REQUEST, "C001", "잘못된 요청입니다."),
    HSP_NOT_FOUND(HttpStatus.NOT_FOUND, "H001", "병원 정보를 찾을 수 없습니다.");

    private final HttpStatus status;
    private final String code;
    private final String message;
    // 생성자 + getter (Lombok @Getter @AllArgsConstructor 가능)
}
```

- 새 에러는 임의 메시지 문자열을 흩지 말고 `ErrorCode`에 항목을 추가한다.
- 도메인별 `ErrorGenerator`가 있으면 그 패턴을 따른다 (예: `ChatbotErrorGenerator`).

## 전역 처리
- `@RestControllerAdvice` + `@ExceptionHandler`로 CustomException → 표준 에러 응답 변환.
- `@Valid` 검증 실패(`MethodArgumentNotValidException`)도 전역 핸들러에서 일관된 포맷으로 변환.
- 예상치 못한 `Exception`은 500으로 매핑하되 스택트레이스를 클라이언트에 노출하지 않는다.

## 검증
- 입력 검증은 DTO + `@Valid`로 선언적으로. Service에서는 비즈니스 규칙(존재 여부·상태·권한)을 검증.
- "조회 후 없으면 예외"는 `findById(...).orElseThrow(() -> ...ErrorGenerator...)` 형태로.
