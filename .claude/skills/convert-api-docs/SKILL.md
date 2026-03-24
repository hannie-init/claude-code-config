---
name: convert-api-docs
description: 엑셀 단위서비스 명세 텍스트를 api-spec.md와 screen-flow.md로 변환한다. 트리거 키워드: '단위서비스 명세 변환', 'api-spec 생성', '명세 변환'
---

단위서비스 명세를 api-spec.md와 screen-flow.md로 변환해줘.

입력: $ARGUMENTS

아래 순서대로 사용자에게 단계별로 입력을 받아서 진행해. 각 단계는 순차적으로 진행하고, 사용자의 응답을 받은 후에 다음 단계로 넘어가.

---

## Step 0: 기능명 입력

$ARGUMENTS에 기능명이 이미 포함되어 있으면 이 단계는 건너뛰어.
그렇지 않으면 사용자에게 아래와 같이 질문해:

> "docs/features/{feature-name}/ 에 저장할게요. feature-name을 입력해주세요. (예: user-login, order-create)"

사용자가 입력한 feature-name을 이후 단계에서 사용해.

---

## Step 1: 프론트 API 명세 입력

사용자에게 아래와 같이 요청해:

> "프론트 API 명세를 입력해주세요. (엑셀에서 복사한 탭 구분 텍스트 또는 파일 경로)"

사용자가 입력한 API 명세를 저장해둬.

---

## Step 2: 중계서버 호출 여부 확인

사용자에게 아래와 같이 질문해:

> "이 기능에서 병원 중계서버(외부 인터페이스) 호출이 필요한가요? (y/n)"

- **n** 이면 Step 3, 4를 건너뛰고 Step 5로 이동
- **y** 이면 Step 3으로 이동

---

## Step 3: 인터페이스 설계 명세 입력 (중계서버 호출 시에만)

사용자에게 아래와 같이 요청해:

> "인터페이스 설계 명세를 입력해주세요. (엑셀에서 복사한 Request/Response 명세 텍스트)"

사용자가 입력한 인터페이스 명세를 저장해둬.

---

## Step 4: 인터페이스 번호 입력 (중계서버 호출 시에만)

사용자에게 아래와 같이 요청해:

> "인터페이스 번호를 입력해주세요. (예: 103 또는 H-103)"

- `103` 또는 `H-103` 형태 모두 허용
- 내부적으로 `H_103` 포맷으로 정규화해서 저장 (H 뒤에 언더스코어, 숫자는 0 패딩 없이)

---

## Step 5: api-spec.md / screen-flow.md 생성

[doc-converter 서브에이전트 호출]
- Step 0에서 입력받은 feature-name으로 `docs/features/{feature-name}/` 디렉토리 하위에 파일 생성
- Step 1 프론트 API 명세를 기반으로 api-spec.md 작성
- 중계서버 호출이 있는 경우 (Step 2가 y) api-spec.md에 아래 섹션을 추가:
  - `## 중계서버 인터페이스` 섹션에 Step 3 명세와 Step 4 번호 포함
- 완료 후 생성된 파일 경로 목록 출력

---

## api-spec.md 템플릿

```markdown
# {기능명} API

## {HTTP_METHOD} {endpoint}

### Request
- Path:
- Header:
- Query:
- Body:

### Response
- 200:
- 400:
- 403:
- 404:

### 비즈니스 규칙
-

## 중계서버 인터페이스 (중계서버 호출이 있는 경우에만 포함)

### {인터페이스 번호} {인터페이스명}
- 인터페이스 번호: H_XXX (예: H_103)
- step 값: H_XXX (PackInterfaceService에서 사용하는 step 키)

#### Request
- (인터페이스 설계 명세의 Request 필드)

#### Response
- (인터페이스 설계 명세의 Response 필드)
```

---

## screen-flow.md 템플릿

```markdown
# {기능명} 화면 흐름

## 정상 플로우
1.

## 예외 케이스
-
```
