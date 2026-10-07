# Java/Spring — 네이밍

## 클래스
- **Controller**: `{도메인}Controller` (예: `ChatBotController`)
- **Service**: `{도메인}Service`. 구현이 여럿일 때만 인터페이스 + `{도메인}ServiceImpl`. 단일 구현이면 인터페이스 만들지 않는다.
- **Repository**: `{Entity}Repository`. QueryDSL 커스텀은 `{Entity}RepositoryCustom` + `{Entity}RepositoryImpl`.
- **Entity**: 도메인 명사 (예: `HspMst`, `SkillAuditEntity`). 기존 테이블 약어 네이밍(`HspMst`, `Mst`/`Dtl` 접미사)을 그대로 따른다.
- **DTO**: `{용도}RequestDto` / `{용도}ResponseDto` (예: `ChatbotRequestDto`, `ValidResponseDto`).
- **Enum**: 의미 있는 단수 명사 (예: `HspType`, `SkillTemplate`, `DeputyGb`).
- **예외/에러**: `{도메인}ErrorGenerator`, `ErrorCode` (enum) — [exception-handling.md](exception-handling.md) 참고.

## 메서드
- camelCase, 동사로 시작: `findById`, `createReservation`, `validateRequest`.
- Repository 쿼리 메서드는 Spring Data JPA 네이밍 규칙을 따른다: `findByHspCdAndUseYn`, `existsByMbrId`.
- boolean 반환은 `is`/`has`/`exists` 접두사.

## 변수·상수
- 변수/필드: camelCase. 약어는 도메인 관례(`hspCd`, `mbrId`)를 따른다.
- 상수: `static final` + UPPER_SNAKE_CASE.
- 의미 없는 약어 신규 도입 금지(기존 도메인 약어는 예외).

## 패키지
- 소문자, 단수. 레이어 기준: `controller`, `service`, `repository`, `domain`(entity), `dto`, `exception`, `config`, `aop`, `utility`, `components`.
- DTO는 용도별 하위 패키지로 묶는다 (예: `dto/chatBotDto/chatbotRequestDto`).
- 신규 코드는 [v2-modern.md](v2-modern.md)의 `application/domain/presentation/common` 구조 권장.
