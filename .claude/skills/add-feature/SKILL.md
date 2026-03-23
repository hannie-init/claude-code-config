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
- **실패 시**: 실패 원인(파일명, 라인번호, 에러 메시지 전문)을 feature-developer 서브에이전트에게 전달하여 수정 요청 → 3단계 재실행
  - **최대 2회 재시도**. 2회 연속 실패 시 에러 리포트를 사용자에게 출력하고 중단.
- **성공 시**: 다음 단계 진행

## 4단계: 코드 리뷰
[code-reviewer 서브에이전트 호출]
- 입력: 1단계 생성/수정 파일 목록 + 2단계 테스트 파일 목록
- 위 파일들을 직접 읽어 리뷰 수행
- Critical / Warning / Suggestion 심각도별 분류 리포트 출력
