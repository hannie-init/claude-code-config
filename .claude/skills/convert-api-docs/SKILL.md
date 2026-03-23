---
name: convert-api-docs
description: 엑셀 단위서비스 명세 텍스트를 api-spec.md와 screen-flow.md로 변환한다. 트리거 키워드: '단위서비스 명세 변환', 'api-spec 생성', '명세 변환'
---

단위서비스 명세 텍스트를 api-spec.md와 screen-flow.md로 변환해줘.

입력: $ARGUMENTS
- 엑셀에서 복사한 단위서비스 명세 텍스트 (여러 개 한 번에 가능)
- 또는 파일 경로

명세 변환 전에 사용자에게 feature-name을 물어봐.
- "docs/features/{feature-name}/ 에 저장할게요. feature-name을 입력해주세요. (예: user-login, order-create)" 라고 질문
- 명세가 여러 개인 경우 각각의 feature-name을 모두 물어봐
- 사용자가 입력한 feature-name으로 디렉토리 생성

[doc-converter 서브에이전트 호출]
- 사용자가 입력한 feature-name으로 docs/features/{feature-name}/ 하위에 파일 생성
- 아래 템플릿 구조를 기반으로 파일 생성
- 완료 후 생성된 파일 경로 목록 출력

## api-spec.md 템플릿

```markdown
# {기능명} API

## {HTTP_METHOD} {endpoint}

### Request
- Path:
- Header:
- Body:

### Response
- 200:
- 400:
- 403:
- 404:

### 비즈니스 규칙
-
```

## screen-flow.md 템플릿

```markdown
# {기능명} 화면 흐름

## 정상 플로우
1.

## 예외 케이스
-
```
