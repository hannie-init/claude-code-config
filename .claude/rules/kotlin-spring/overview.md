# Kotlin/Spring — 개요 및 적용 기준

Kotlin + Spring Boot 서버(예: `karechat-partners-center/server`) 작업 시 적용하는 규칙이다.
레이어 책임·예외 철학·영속성 원칙 등 **언어 중립 규칙은 [java-spring](../java-spring/)을 그대로 따르고**, 이 디렉터리는 Kotlin 고유 규칙과 차이점만 다룬다.

## 적용 기준 (스택 감지)
- `build.gradle.kts` + `src/main/kotlin` 이 있으면 Kotlin/Spring 프로젝트 → 이 규칙 적용.
- `build.gradle` + `src/main/java` 면 기존 [java-spring](../java-spring/) 규칙 적용.
- Kotlin 프로젝트에서는 java-spring의 **Lombok 규칙·record 분기·Mockito 테스트 규칙을 적용하지 않는다** (각각 언어 기능·Kotest/MockK로 대체).

## 기준 스택 (partners-center 기준)
- **언어/빌드**: Kotlin 2.x, Gradle Kotlin DSL(`build.gradle.kts`), ktlint(`org.jlleitschuh.gradle.ktlint`)
- **프레임워크**: Spring Boot 4.x (web / data-jpa / security / validation), `kotlin("plugin.spring")`(all-open) + `kotlin("plugin.jpa")`(no-arg) 적용 전제
- **테스트**: Kotest(runner-junit5, assertions-core) + MockK, 통합 테스트는 JUnit5 + `@SpringBootTest` + Testcontainers(MySQL)
- **base 패키지**: `com.kakaohealthcare.partners`

## 패키지 구조 — 도메인 우선
java-spring의 레이어 우선(`controller/service/...`)과 달리 **도메인으로 먼저 묶고 그 아래 레이어**를 둔다.

```
com.kakaohealthcare.partners/
  {domain}/              # account, auth, audit, statistics ...
    model/               # 엔티티·enum·값 객체 (java-spring의 domain)
    application/         # 서비스·정책(Policy)·유스케이스
    infrastructure/      # Repository, 외부 연동 (EmailSender 등)
    presentation/        # Controller, presentation/dto/ 에 Request/Response
  common/
    error/               # ErrorCode, KarechatException, GlobalExceptionHandler
    response/            # FrontResponse (성공 응답 표준 래퍼)
    security/ config/ util/
```

- 의존 방향: `presentation → application → model`, infrastructure는 application이 사용.
- 공통 코드(에러·응답 래퍼·util)는 `common/` 아래에 둔다.

## 핵심 패턴 (repo 현행)
- **성공 응답**: `FrontResponse.ok(dto)` — data에는 DTO만, `@Entity` 직접 노출 금지.
- **에러**: `ErrorCode` enum(이름 형식 `{DOMAIN}_{REASON}`, status+기본 메시지의 단일 소스) + `KarechatException(errorCode)` → `GlobalExceptionHandler`가 변환.
- **엔티티 ↔ DTO 변환**: 확장 함수 `fun Xxx.toResponse(): XxxResponse` (DTO 파일 또는 사용처 인접).
- **Controller**: 얇게, expression body 적극 사용, 인가는 SecurityConfig 매트릭스에 위임(개별 컨트롤러에 흩지 않음).

## 상세 규칙
| 파일 | 내용 |
|---|---|
| [conventions.md](conventions.md) | Kotlin 코딩 스타일 — null 처리, 불변성, 클래스 설계, 스코프 함수, 코루틴 등 |
| [testing.md](testing.md) | Kotest + MockK 테스트 규칙, 통합 테스트, ktlintCheck |

## 변경 이력
- 2026-10-06: 최초 작성. partners-center 실제 패턴 + 사용자 제공 Kotlin 스타일 가이드 기반.
