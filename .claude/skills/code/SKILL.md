---
name: code
description: Spring Boot(케어챗 서버) 기능을 경량 파이프라인으로 구현한다 — 구현 → 테스트 → 검증을 서브에이전트로 순차 실행한다. 트리거 키워드 '/code', '기능 구현', '구현', '구현해줘', '기능 만들어줘', '코딩해줘'. Java 또는 Kotlin의 Spring 기능을 만들거나 구현해달라는 자연어 요청이면 이 스킬로 라우팅한다(단, '진행해줘'처럼 대상이 모호한 말은 코딩인지 먼저 확인). JVM/Spring 프로젝트가 아니면 이 스킬을 사용하지 않는다(0단계 가드에서 중단). 자연어 요구사항을 입력으로 받는다(설계 문서 경로 불필요).
---

# /code — 경량 코딩 파이프라인

자연어 요구사항을 받아 **구현 → 테스트 → 검증** 순서로 진행한다. 1·2단계는 전용 **`spring-developer` 에이전트**로 실행하고(규칙 내장), 3단계 검증은 이 스킬이 오케스트레이션한다. 모든 단계는 0단계에서 감지한 스택의 코딩 규칙(`~/.claude/rules/java-spring/` 또는 `~/.claude/rules/kotlin-spring/`)과 **기존 코드 패턴**을 따른다.

입력: `$ARGUMENTS` (구현할 기능에 대한 자연어 설명)

> 시작 전: `$ARGUMENTS`가 비어 있거나 모호하면, 구현 대상·대상 모듈·핵심 비즈니스 규칙을 1~2개 질문으로 먼저 확인한다.

## 0단계: 스택 감지 (가드)
대상 프로젝트(또는 대상 모듈)의 루트를 확인해 스택 프로파일을 결정한다:
- `build.gradle.kts` + `src/main/kotlin` 존재 → **`kotlin-spring`** (규칙: `~/.claude/rules/kotlin-spring/`)
- `build.gradle`(또는 `.kts`) + `src/main/java` 존재 → **`java-spring`** (규칙: `~/.claude/rules/java-spring/`)
- 혼재 시(멀티모듈에 양쪽 존재) 실제 작업 대상 모듈 기준으로 판단하고, 모호하면 사용자에게 확인한다.
- **둘 다 아니면(gradlew 없음, JVM/Spring 아님)**: 이 스킬을 즉시 중단하고 "JVM/Spring 프로젝트가 아니라 /code 파이프라인을 적용하지 않고 일반 구현으로 진행한다"고 사용자에게 알린 뒤, 스킬 밖에서 해당 프로젝트의 컨벤션에 맞춰 구현한다.

결정된 스택 프로파일은 1·2·3단계 모든 에이전트 프롬프트에 명시해 전달한다.

## 공통 규칙 (모든 단계)
- 코딩 규칙은 감지된 스택의 rules 디렉터리를 따른다. 규칙과 기존 코드가 충돌하면 **해당 파일의 현행 패턴 우선**. (1·2단계 `spring-developer` 에이전트는 스택별 규칙 로드를 내장한다.)
- 서브에이전트는 메인 컨텍스트를 공유하지 않으므로, 각 단계 프롬프트에 **스택 프로파일·요구사항·대상 모듈·직전 단계 산출물(파일 목록)을 명시**해서 전달한다.
- 작업 대상 모듈에 프로젝트 `CLAUDE.md`나 `.claude/skills/`가 있으면 그 규칙을 함께 따른다.
  - 예: `karechat-server-skill`에서 중계서버(`H_xxx`) 인터페이스 호출이 필요하면 프로젝트 전용 **`pack-interface`** 스킬 규칙을 적용한다.

## 1단계: 구현
**`spring-developer` 에이전트**를 띄워 아래를 수행시킨다(규칙은 에이전트가 내장·자체 로드하므로, 프롬프트에는 스택 프로파일·요구사항·대상 모듈·제약을 명확히 전달한다):
- 요구사항(`$ARGUMENTS`)을 분석하고, 유사 도메인의 **기존 코드 패턴을 먼저 탐색**한다(Entity 구조, 예외 처리, Response 포맷, Repository/Service 패턴).
- 구현 순서: **Entity → Repository → Service → Controller → CustomException(ErrorCode)**. (kotlin-spring은 도메인 우선 패키지 `{domain}/model|application|infrastructure|presentation` 기준으로 동일 순서.)
- 완료 후 반드시 출력: 생성/수정 파일 경로 목록, 구현한 비즈니스 규칙 요약, 설계상 결정사항.

## 2단계: 테스트
**`spring-developer` 에이전트**를 띄워 아래를 수행시킨다:
- 입력: 스택 프로파일 + 1단계가 출력한 생성/수정 파일 경로 목록.
- 규칙 — 에이전트가 내장:
  - `java-spring`: `rules/java-spring/testing.md` (한국어 `@DisplayName`, given/when/then, Service는 `@ExtendWith(MockitoExtension.class)`, Controller는 `@WebMvcTest`)
  - `kotlin-spring`: `rules/kotlin-spring/testing.md` (Kotest BehaviorSpec 한국어 Given/Then + MockK, 통합은 JUnit5+Testcontainers)
- 정상 / 예외(정의된 모든 ErrorCode 분기) / 경계값 케이스를 포함한다.
- 완료 후 반드시 출력: 작성된 테스트 파일 경로 목록, 총 케이스 수 및 커버 시나리오 요약.

## 3단계: 검증
- 대상 모듈에서 빌드/테스트를 실행한다:
  - `java-spring`: `./gradlew compileJava` → `./gradlew test`
  - `kotlin-spring`: `./gradlew compileKotlin` → `./gradlew ktlintCheck test`
- **성공 시**: 변경 파일 목록과 핵심 변경점, 테스트 결과를 요약 보고하고 종료한다.
- **실패 시**: 에러 메시지 전문을 근거로 **최대 1회** 수정 루프를 돈다.
  - 에러 위치가 프로덕션(`src/main/`)이든 테스트(`src/test/`)든 **`spring-developer` 에이전트**에게 에러 전문과 수정 대상을 넘겨 수정시킨 후 재검증한다.
  - 1회 수정 후에도 실패하면 더 시도하지 말고, 실패한 에러 전문과 추정 원인을 사용자에게 보고하고 판단을 요청한다.

## 변경 이력
- 2026-10-06: Kotlin 지원 추가 — 0단계 스택 감지(가드) 도입(java-spring/kotlin-spring 프로파일, 비 JVM 프로젝트는 스킬 중단), 2단계 테스트 규칙·3단계 검증 명령 스택별 분기, description에 Kotlin 명시.
- 2026-08-14: 1·2단계를 범용 서브에이전트 → 전용 `spring-developer` 에이전트 호출로 전환. 3단계 수정 루프도 spring-developer에 위임.
- 2026-08-14: 트리거 description 확장('구현', '구현해줘', '기능 만들어줘' 추가). 자연어 구현 요청 라우팅 신뢰도 개선. '진행해줘'처럼 모호한 말은 트리거 제외(선확인).
- 2026-06-29: 최초 작성. 삭제된 add-feature 스킬을 대체하는 경량 파이프라인. 설계 문서 경로 입력 제거, 중계서버 규칙은 프로젝트 전용 pack-interface 스킬로 분리.
