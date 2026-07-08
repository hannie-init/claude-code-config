---
name: code
description: Spring Boot(케어챗 서버) 기능을 경량 파이프라인으로 구현한다 — 구현 → 테스트 → 검증을 서브에이전트로 순차 실행한다. 트리거 키워드 '/code', '기능 구현', '코딩해줘'. 자연어 요구사항을 입력으로 받는다(설계 문서 경로 불필요).
---

# /code — 경량 코딩 파이프라인

자연어 요구사항을 받아 **구현 → 테스트 → 검증** 순서로 진행한다. 각 단계는 범용 서브에이전트로 실행하고, 모든 단계는 `~/.claude/rules/java-spring/`의 코딩 규칙과 **기존 코드 패턴**을 따른다.

입력: `$ARGUMENTS` (구현할 기능에 대한 자연어 설명)

> 시작 전: `$ARGUMENTS`가 비어 있거나 모호하면, 구현 대상·대상 모듈·핵심 비즈니스 규칙을 1~2개 질문으로 먼저 확인한다.

## 공통 규칙 (모든 단계)
- 코딩 규칙은 `~/.claude/rules/java-spring/`를 따른다. 규칙과 기존 코드가 충돌하면 **해당 파일의 현행 패턴 우선**.
- 서브에이전트는 메인 컨텍스트를 공유하지 않으므로, 각 단계 프롬프트에 **rules 경로와 직전 단계 산출물(파일 목록)을 명시**해서 전달한다.
- 작업 대상 모듈에 프로젝트 `CLAUDE.md`나 `.claude/skills/`가 있으면 그 규칙을 함께 따른다.
  - 예: `karechat-server-skill`에서 중계서버(`H_xxx`) 인터페이스 호출이 필요하면 프로젝트 전용 **`pack-interface`** 스킬 규칙을 적용한다.

## 1단계: 구현
범용 서브에이전트를 띄워 아래를 수행시킨다:
- 요구사항(`$ARGUMENTS`)을 분석하고, 유사 도메인의 **기존 코드 패턴을 먼저 탐색**한다(Entity 구조, 예외 처리, Response 포맷, Repository/Service 패턴).
- `~/.claude/rules/java-spring/`의 `layered-architecture.md`, `di-and-lombok.md`, `exception-handling.md`, `persistence-jpa-querydsl.md`, (신규 모듈이면) `v2-modern.md`를 적용한다.
- 구현 순서: **Entity → Repository → Service → Controller → CustomException(ErrorCode)**.
- 완료 후 반드시 출력: 생성/수정 파일 경로 목록, 구현한 비즈니스 규칙 요약, 설계상 결정사항.

## 2단계: 테스트
범용 서브에이전트를 띄워 아래를 수행시킨다:
- 입력: 1단계가 출력한 생성/수정 파일 경로 목록.
- 규칙: `~/.claude/rules/java-spring/testing.md` (한국어 `@DisplayName`, given/when/then, Service는 `@ExtendWith(MockitoExtension.class)`, Controller는 `@WebMvcTest`).
- 정상 / 예외(정의된 모든 ErrorCode 분기) / 경계값 케이스를 포함한다.
- 완료 후 반드시 출력: 작성된 테스트 파일 경로 목록, 총 케이스 수 및 커버 시나리오 요약.

## 3단계: 검증
- 대상 모듈에서 빌드/테스트를 실행한다: `./gradlew compileJava` → `./gradlew test`.
- **성공 시**: 변경 파일 목록과 핵심 변경점, 테스트 결과를 요약 보고하고 종료한다.
- **실패 시**: 에러 메시지 전문을 근거로 **최대 1회** 수정 루프를 돈다.
  - 에러 위치가 `src/main/java/`면 1단계 에이전트 패턴으로, `src/test/java/`면 2단계 에이전트 패턴으로 수정 후 재검증한다.
  - 1회 수정 후에도 실패하면 더 시도하지 말고, 실패한 에러 전문과 추정 원인을 사용자에게 보고하고 판단을 요청한다.

## 변경 이력
- 2026-06-29: 최초 작성. 삭제된 add-feature 스킬을 대체하는 경량 파이프라인. 설계 문서 경로 입력 제거, 중계서버 규칙은 프로젝트 전용 pack-interface 스킬로 분리.
