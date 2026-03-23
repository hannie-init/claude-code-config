---
name: korean-commit
description: "한국어로 커밋 메시지를 작성하는 git commit 스킬. commit-commands 플러그인의 커스텀 버전으로, 지정된 Subject/Body/Footer 템플릿 구조와 커밋 타입(feat/fix/docs/refactor/revert/test)을 사용한다. 모든 안내 메시지와 커밋 메시지는 한국어로 작성한다. 트리거 키워드: 커밋, 커밋해줘, 변경사항 커밋, commit kr, /commit-kr, /korean-commit"
---

## 커밋 타입 가이드

| 타입 | 설명 |
|------|------|
| `feat` | 새로운 기능 개발 시 |
| `fix` | 버그를 수정했을 시 |
| `docs` | 문서작업 |
| `refactor` | 리팩토링 작업 |
| `revert` | 작업을 되돌렸을 시 |
| `test` | 테스트 코드 관련 작업을 했을 시 또는 테스트를 위해 머지 했을 때 |

## 커밋 메시지 형식

```
<Type>: <Subject>

Body 내용 (선택사항)

Footer 내용 (선택사항)
```

- **Subject**: `<Type>: <한국어 요약>` — 변경 내용을 간결하게 요약 (50자 이내 권장)
- **Body**: 변경 이유 및 상세 설명 (생략 가능)
- **Footer**: 관련 이슈 번호, Breaking Change 등 (생략 가능)

## 실행 절차

1. `git status`로 변경 파일 목록 확인
2. `git diff HEAD`로 변경 내용 파악
3. 변경 내용에 맞는 타입 선택
4. 한국어로 Subject 작성
5. 필요 시 Body, Footer 작성
6. 변경 파일 스테이징 후 커밋 실행
7. 커밋 완료 후 **push 여부를 사용자에게 확인**
   - "push도 진행할까요?" 라고 물어본다
   - 승인 시 `git push` 실행

## 커밋 명령어 형식

Body/Footer 포함 시:
```bash
git commit -m "$(cat <<'EOF'
<Type>: <Subject>

<Body>

<Footer>
EOF
)"
```

Subject만 있을 때:
```bash
git commit -m "<Type>: <Subject>"
```

## Push 명령어 형식

원격 브랜치가 설정되어 있을 때:
```bash
git push
```

처음 push하거나 upstream이 없을 때:
```bash
git push -u origin <브랜치명>
```

## 주의사항

- 모든 안내 메시지와 커밋 메시지 Subject는 **한국어**로 작성
- `git add -A` 대신 관련 파일만 선택적으로 스테이징
- 현재 브랜치 및 최근 커밋 이력을 확인 후 작업

## 절대 커밋하면 안 되는 파일

스테이징 전 아래 파일이 포함되지 않았는지 반드시 확인한다.

### 민감 정보
- `.env`, `.env.*` — API 키, 비밀번호 등
- `application-local.yml` / `application-local.properties`
- `application-secret.yml` / `*secret*.yml`
- `**/credentials.*`, `**/secrets.*`

### Claude Code 로컬 설정
- `.claude/settings.local.json` — 개인 권한 설정 (머신마다 다름)

### IntelliJ IDE
- `.idea/` 디렉토리 전체
- `*.iml`, `*.iws`, `*.ipr`

### macOS
- `.DS_Store`, `.AppleDouble`

### Java / Spring / Gradle 빌드 산출물
- `.gradle/`, `build/`, `out/`, `target/`
- `*.class`, `*.jar`, `*.war`, `*.log`

> **참고**: 위 파일들이 `.gitignore`에 등록되어 있지 않으면 git이 추적할 수 있다.
> Claude를 통해 커밋할 때는 이 스킬이 스테이징을 막지만, 직접 `git add .` 사용 시에는 보호되지 않으므로 `.gitignore` 설정을 권장한다.
