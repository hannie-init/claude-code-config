# claude-code-config

Claude Code 개인 설정 파일 모음입니다.
주로 Spring Boot 프로젝트 개발 환경에 맞게 구성되어 있습니다.

## 구조

```
.claude/
├── agents/          # 서브 에이전트 정의
│   ├── code-reviewer.md
│   ├── doc-converter.md
│   ├── feature-developer.md
│   ├── test-writer.md
│   └── validator.md
└── skills/          # 커스텀 스킬 정의
    ├── add-feature/
    ├── convert-api-docs/
    ├── korean-commit/
    └── review-code/
```

## Agents

서브 에이전트는 `.claude/agents/` 에 정의되며, 스킬에서 순차적으로 호출됩니다.

| 에이전트 | 역할 |
|---------|------|
| `feature-developer` | api-spec.md / screen-flow.md 기반으로 Entity, Repository, Service, Controller 구현 |
| `test-writer` | 구현된 코드의 Service 단위 테스트 및 Controller 슬라이스 테스트 작성 |
| `validator` | Gradle 빌드 및 테스트 실행 후 성공 여부 확인 |
| `code-reviewer` | 코드를 읽기 전용으로 분석하여 버그/보안/성능/품질 이슈 리포트 |
| `doc-converter` | 엑셀 단위서비스 명세를 api-spec.md / screen-flow.md 로 변환 |

## Skills

스킬은 `.claude/skills/` 에 정의되며, `/스킬명` 또는 트리거 키워드로 실행됩니다.

| 스킬 | 설명 | 트리거 |
|------|------|--------|
| `add-feature` | feature-developer → test-writer → validator → code-reviewer 순서로 Spring Boot 기능 개발 | `add-feature`, `기능 추가` |
| `convert-api-docs` | 엑셀 단위서비스 명세 텍스트를 api-spec.md / screen-flow.md 로 변환 | `단위서비스 명세 변환`, `api-spec 생성` |
| `korean-commit` | 한국어 커밋 메시지 작성 + push 옵션 제공 | `커밋해줘`, `/korean-commit` |
| `review-code` | Spring Boot 코드 리뷰 (Critical / Warning / Suggestion 분류) | `코드 리뷰`, `review` |

## 설치

```bash
git clone https://github.com/hannie-init/claude-code-config.git
cp -r claude-code-config/.claude/* ~/.claude/
```

## 주의

- `.claude/settings.local.json` 은 개인 권한 설정 파일로 git에서 제외됩니다.
- 민감 정보(`.env`, `application-local.yml` 등)는 절대 커밋하지 않습니다.
