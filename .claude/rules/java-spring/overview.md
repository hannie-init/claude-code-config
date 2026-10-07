# Java/Spring — 개요 및 적용 기준

## 스택
- **언어/빌드**: Java 11, Gradle 멀티모듈
- **프레임워크**: Spring Boot (web / webflux / data-jpa / data-redis / validation / aop / actuator)
- **라이브러리**: Lombok 1.18.x, QueryDSL 5.0.0, MySQL connector 8.0.x, Thymeleaf
- **API 문서**: Swagger (`@Api`, `@ApiOperation`)
- **base 패키지**: `com.kakaohealthcare.dfd.{module}` (예: `com.kakaohealthcare.dfd.skillserver`)

## 모듈 구조
karechat-server는 멀티모듈 모노레포다. 새 코드는 **목적에 맞는 모듈**에 둔다.
- `karechat-server-skill` — 챗봇 스킬 서버 (핵심 비즈니스)
- `karechat-server-member` — 회원 도메인
- `karechat-server-interface` — 외부 인터페이스
- `karechat-server-common` — 공통 코드 (여러 모듈에서 재사용)
- `karechat-server-gateway`, `karechat-server-batch` 등

> 공통으로 쓰일 유틸/상수/예외는 개별 모듈이 아니라 `karechat-server-common`에 둔다.

## 레거시 vs v2 — 적용 기준
코드베이스가 전통적 레이어드 구조에서 `v2/` 패키지의 모던 구조로 마이그레이션 중이다.

- **기존(레거시) 파일을 수정**할 때 → 그 파일이 속한 패키지의 **현행 패턴을 그대로 유지**한다. 일관성이 최우선이며, 한 파일만 새 스타일로 바꾸지 않는다.
- **신규 기능/모듈을 작성**할 때 → 가능하면 `v2/` 모던 구조를 따른다. 자세한 내용은 [v2-modern.md](v2-modern.md).
- 어느 쪽인지 모호하면, 같은 도메인의 인접 코드를 먼저 읽고 다수 패턴을 따른다.

## 공통 원칙
- 한 클래스 = 한 책임. Controller는 얇게, 비즈니스 로직은 Service로.
- Entity를 Controller 레이어에 직접 노출하지 않는다 (요청/응답은 DTO).
- 사람이 읽는 메시지·주석·로그 설명은 한국어로 작성한다.
