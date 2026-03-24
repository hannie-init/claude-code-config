---
name: add-feature
description: API 설계서와 화면 흐름 문서를 기반으로 Spring Boot 기능을 개발한다. feature-developer → test-writer → validator → code-reviewer 순서로 실행한다.
---

아래 API 설계서와 화면 흐름 문서를 기반으로 기능을 개발해줘.

입력: $ARGUMENTS (예: docs/features/certificate-status/api-spec.md docs/features/certificate-status/screen-flow.md)

다음 순서로 진행해:

## 1단계: 기능 구현
[feature-developer 서브에이전트 호출]
- $ARGUMENTS로 전달된 api-spec.md, screen-flow.md를 읽고 구현
- Entity → Repository → Service → Controller → CustomException 순서로 작성

### 중계서버 인터페이스 호출 규칙 (api-spec.md에 `## 중계서버 인터페이스` 섹션이 있는 경우 적용)

api-spec.md에 `## 중계서버 인터페이스` 섹션이 있으면 아래 규칙을 따라 외부 호출 코드를 추가해:

1. **`PackInterfaceService` 파일을 먼저 읽어서 기존 패턴을 파악한다.**
   - 경로: `src/main/java/com/kakaohealthcare/dfd/skillserver/service/PackInterfaceService.java`
   - 기존 메서드 중 구조가 비슷한 것을 참고해서 동일한 패턴으로 작성

2. **`PackInterfaceService`에 새 메서드를 추가한다.**
   - 메서드명: 기능명을 반영한 camelCase (예: `getCertificateStatus`)
   - `step` 값: api-spec.md의 인터페이스 번호 (예: `H_103`)
   - `bodyMap`에 인터페이스 Request 필드를 담아 `monoWebClient.createPackageWebClient()` 호출
   - 응답은 `interfaceDtoConverter.convertToDto()` 로 변환
   - 기존 메서드 주석 형식 유지: `/** * H-XXX {인터페이스명} */`

3. **Service 레이어에서 `PackInterfaceService`를 주입받아 사용한다.**
   - `PackInterfaceService`는 `@RequiredArgsConstructor`로 주입
   - `baseUrl`, `hspCd`, `hspId` 등 공통 파라미터는 `ChatbotRequestContextHolder` 또는 기존 패턴에서 가져옴

4. **인터페이스 Request/Response DTO가 없으면 새로 생성한다.**
   - 위치: `src/main/java/com/kakaohealthcare/dfd/skillserver/dto/interfaceDto/`
   - 기존 DTO 파일 구조(Lombok, `@JsonProperty` 등) 참고

- 완료 후 아래 정보를 반드시 출력 (2단계로 전달됨):
  - 생성/수정된 파일 경로 목록 (전체 경로)
  - 구현한 비즈니스 규칙 요약 (screen-flow.md 기준)
  - 특이사항 또는 설계 문서 기준으로 결정한 사항

## 2단계: 테스트 코드 작성
[test-writer 서브에이전트 호출]
- 입력: 1단계 feature-developer가 출력한 **생성/수정 파일 경로 목록** + $ARGUMENTS의 screen-flow.md 경로
- 위 파일들을 직접 읽어 테스트 대상 파악
- Service 단위 테스트(@ExtendWith(MockitoExtension.class))
- Controller 슬라이스 테스트(@WebMvcTest)
- 정상/예외/경계값 케이스 포함
- 완료 후 아래 정보를 반드시 출력 (3단계로 전달됨):
  - 작성된 테스트 파일 경로 목록 (전체 경로)
  - 총 테스트 케이스 수 및 커버한 시나리오 요약

## 3단계: 빌드 및 테스트 검증
[validator 서브에이전트 호출]
- ./gradlew clean compileJava 실행
- ./gradlew test 실행
- **성공 시**: 다음 단계 진행
- **실패 시**: 아래 유형별로 분기한다. 컴파일 에러 카운터 / 테스트 실패 카운터는 서로 독립적으로 관리한다.

### 컴파일 에러 시 (최대 4회, 위치에 따라 담당 에이전트 분기)

**에러 발생 위치가 `src/main/java/` 인 경우**
[feature-developer 서브에이전트 호출]
- 입력: validator가 출력한 에러 메시지 전문 (파일명, 라인번호 포함)
- 해당 파일을 수정하여 컴파일 에러 해소
- 완료 후 수정된 파일 목록 출력
→ **컴파일 에러 카운터 +1** → validator 재실행

**에러 발생 위치가 `src/test/java/` 인 경우**
[test-writer 서브에이전트 호출]
- 입력: validator가 출력한 에러 메시지 전문 (파일명, 라인번호 포함)
- 테스트 코드의 컴파일 에러 수정
- 완료 후 수정된 파일 목록 출력
→ **컴파일 에러 카운터 +1** → validator 재실행

**컴파일 에러 카운터 4회 초과 시** 아래 메시지를 출력하고 중단:
```
⛔ 컴파일 에러 자동 수정 한계 도달 (4회 시도)

반복되는 컴파일 에러는 설계 문서와 구현 코드 간 구조적 불일치이거나,
프로젝트 빌드 환경 문제일 수 있습니다.
아래 파일을 직접 확인 후 수정해 주세요:

{최종 에러 메시지 전문 - 파일명, 라인번호 포함}
```

### 테스트 실패 시 (최대 2회)
[test-writer 서브에이전트 호출]
- 입력: validator가 출력한 실패 테스트명, 에러 메시지 전문
- 실패 원인 분석 후 아래 두 가지 중 하나로 처리:
  - **테스트 코드 문제** (잘못된 Mock 설정, 잘못된 기댓값 등): 테스트 코드 수정 후 수정 파일 목록 출력
  - **구현 로직 문제** (Service/Controller 버그, 비즈니스 규칙 누락 등): 코드를 수정하지 않고 아래 형식으로 출력
    ```
    [ESCALATE] 구현 로직 문제로 판단됨
    - 실패 테스트: {테스트명}
    - 원인 분석: {분석 내용}
    - 수정 필요 파일: {파일 경로}
    ```
→ **테스트 실패 카운터 +1** → validator 재실행

**test-writer가 [ESCALATE]를 출력한 경우**, 오케스트레이터(Claude)가 아래를 수행한다:
[feature-developer 서브에이전트 호출]
- 입력: test-writer가 출력한 ESCALATE 내용 전문
- 지정된 파일의 구현 로직 수정
- 완료 후 수정된 파일 목록 출력
→ validator 재실행 (이 경우에도 **테스트 실패 카운터 +1**)

**테스트 실패 카운터 2회 초과 시** 에러 리포트를 출력하고 중단:
```
⛔ 테스트 자동 수정 한계 도달 (2회 시도)

{최종 실패 테스트명 및 에러 메시지 전문}
```

> **카운터 요약**
> | 카운터 | 증가 조건 | 최대 횟수 |
> |--------|----------|----------|
> | 컴파일 에러 | main 또는 test 코드 컴파일 에러로 에이전트 수정 시도 1회 | 4회 |
> | 테스트 실패 | test-writer 직접 수정 또는 feature-developer escalate 1회 | 2회 |

## 4단계: 코드 리뷰
[code-reviewer 서브에이전트 호출]
- 입력: 1단계 생성/수정 파일 목록 + 2단계 테스트 파일 목록
- 위 파일들을 직접 읽어 리뷰 수행
- Critical / Warning / Suggestion 심각도별 분류 리포트 출력
