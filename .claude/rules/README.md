# 코딩 규칙 (rules)

`~/.claude/CLAUDE.md`에서 참조하는 글로벌 코딩 규칙 모음. 기존 코드 스타일과 충돌하면 **해당 프로젝트의 기존 패턴이 우선**한다.

## Java / Spring
karechat 서버(Gradle 멀티모듈, Java 11, Spring Boot, Lombok, JPA, QueryDSL 5.0) 기준으로 작성된 규칙이다.
레거시 코드는 **현행 패턴을 유지**하고, 신규 코드는 **v2 모던 구조를 권장**하는 듀얼 가이드다.

| 파일 | 내용 |
|---|---|
| [java-spring/overview.md](java-spring/overview.md) | 스택·모듈·패키지 구조, 레거시 vs v2 적용 기준 |
| [java-spring/naming.md](java-spring/naming.md) | 클래스·메서드·변수·패키지 네이밍 |
| [java-spring/layered-architecture.md](java-spring/layered-architecture.md) | Controller / Service / Repository / DTO / Entity 레이어 규칙 |
| [java-spring/di-and-lombok.md](java-spring/di-and-lombok.md) | 의존성 주입, Lombok 사용 규칙 |
| [java-spring/exception-handling.md](java-spring/exception-handling.md) | 예외 처리, ErrorCode 패턴 |
| [java-spring/persistence-jpa-querydsl.md](java-spring/persistence-jpa-querydsl.md) | JPA·QueryDSL, 트랜잭션, N+1 방지 |
| [java-spring/testing.md](java-spring/testing.md) | JUnit5 + Mockito 테스트 규칙 |
| [java-spring/v2-modern.md](java-spring/v2-modern.md) | 신규 코드용 v2 (application/domain/presentation) 구조 권장 |

## Kotlin / Spring
Kotlin + Spring Boot 서버(예: `karechat-partners-center/server`) 기준 규칙이다.
레이어 책임·예외 철학 등 언어 중립 규칙은 java-spring을 공유하고, Kotlin 고유 규칙과 차이점만 다룬다.
스택 감지: `build.gradle.kts` + `src/main/kotlin` → kotlin-spring, `build.gradle` + `src/main/java` → java-spring.

| 파일 | 내용 |
|---|---|
| [kotlin-spring/overview.md](kotlin-spring/overview.md) | 적용 기준(스택 감지)·기준 스택·도메인 우선 패키지 구조·핵심 패턴 |
| [kotlin-spring/conventions.md](kotlin-spring/conventions.md) | Kotlin 코딩 스타일 — null 처리, 불변성, 클래스 설계, 스코프 함수, 코루틴 |
| [kotlin-spring/testing.md](kotlin-spring/testing.md) | Kotest + MockK 단위 테스트, JUnit5 + Testcontainers 통합 테스트, ktlintCheck |

## 변경 이력
- 2026-10-06: Kotlin/Spring 규칙 3종 추가 (partners-center 패턴 + 사용자 Kotlin 스타일 가이드 기반).
- 2026-06-29: 최초 작성. Java/Spring 규칙 8종 추가.
