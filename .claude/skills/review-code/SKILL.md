---
name: review-code
description: 지정한 파일 또는 디렉토리의 Spring Boot 코드를 리뷰한다. Critical / Warning / Suggestion 심각도별 분류 리포트를 출력한다. 트리거 키워드: '코드 리뷰', 'review'
---

지정한 코드를 리뷰해줘.

입력: $ARGUMENTS
- 파일 경로 (예: src/main/java/.../CertificateService.java)
- 디렉토리 경로 (예: src/main/java/.../certificates/)
- 미입력 시: 현재 브랜치에서 변경된 파일 전체 (git diff --name-only HEAD 기준)

## 사전 준비 (Claude가 직접 처리)
- $ARGUMENTS가 있으면 해당 경로를 그대로 사용
- $ARGUMENTS가 없으면 `git diff --name-only HEAD`로 변경 파일 목록을 먼저 파악

## 리뷰 실행
[code-reviewer 서브에이전트 호출]
- 입력: 위에서 확정된 파일/디렉토리 경로 목록 (전체 경로)
- 해당 파일들을 직접 읽어 리뷰 수행
- Critical / Warning / Suggestion 심각도별 분류 리포트 출력
