---
name: convert-api-docs
description: 엑셀 단위서비스 명세 텍스트를 api-spec.md와 screen-flow.md로 변환한다. 트리거 키워드: '단위서비스 명세 변환', 'api-spec 생성', '명세 변환'
---

단위서비스 명세 텍스트를 api-spec.md와 screen-flow.md로 변환해줘.

입력: $ARGUMENTS
- 엑셀에서 복사한 단위서비스 명세 텍스트 (여러 개 한 번에 가능)
- 또는 파일 경로

[doc-converter 서브에이전트 호출]
- 입력된 명세를 파싱하여 docs/features/{feature-name}/ 하위에 파일 생성
- 명세가 여러 개인 경우 각각 별도 디렉토리에 생성
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
