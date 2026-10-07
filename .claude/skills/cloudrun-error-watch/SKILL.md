---
name: cloudrun-error-watch
description: >
  GCP Cloud Run 서비스의 ERROR 로그를 주기적으로 폴링해 장애를 감지하고,
  신규 에러를 요약 표 + trace별 Logs Explorer 딥링크 + 데스크톱/모바일 푸시 알림으로 리포트하는 스킬.
  skill / member / common 서버(및 임의 Cloud Run 서비스)를 여러 개 동시에 감시할 수 있다.
  사용자가 "에러 감시", "장애 감시 설정", "주기 에러 감시", "서버 감시해줘", "장애나면 알려줘",
  "prod 서버 모니터링해서 알려줘", "/cloudrun-error-watch" 등을 말할 때 사용한다.
  단, "실시간 로그", "tail", "스트리밍"처럼 실시간 스트림 의도면 gcp-cloudrun-tail 스킬을,
  단발성 로그 조회면 gcp-cloudrun-log 스킬을 쓴다(이 스킬은 '주기 폴링 + 장애 리포트' 전용).
---

# Cloud Run 에러 감시 & 알림 스킬

GCP Cloud Run 서비스의 ERROR 로그를 **주기적으로 폴링**해 신규 장애를 감지하고 알림을 보낸다.
결정적 조회·파싱·링크 생성은 `scripts/check_errors.py`(조회 전용)가 담당하고,
워터마크 관리·푸시 알림·주기 실행(`/loop`)은 이 스킬(Claude)이 오케스트레이션한다.

- 관련 스킬 구분: **실시간 tail** → `gcp-cloudrun-tail`, **단발 조회** → `gcp-cloudrun-log`, **주기 감시+알림** → (이 스킬).
- **prod는 조회 전용.** 이 스킬은 `gcloud logging read` 외 어떤 쓰기도 하지 않는다.

## 사전 확인
1. gcloud 설치: `gcloud version` (없으면 설치 안내).
2. 인증: `gcloud auth list --filter=status:ACTIVE --format="value(account)"` (없으면 `gcloud auth login` 안내).
   - gcloud가 Python 3.9로 크래시하면 스크립트가 `CLOUDSDK_PYTHON`을 3.10+로 자동 지정한다(별도 조치 불필요).

## 1회 점검
한 사이클만 돌려 현재 상태를 본다:
```bash
python3 ~/.claude/skills/cloudrun-error-watch/scripts/check_errors.py \
  --env prod --target skill --target member --target common
```
스크립트는 대상 서비스별 리포트(표 + trace 링크 + 배치 링크)를 출력하고,
마지막 줄에 `RESULT {json}`(대상별 new_count·max_ts, total_new, push_text)을 낸다.

## 주기 감시 시작
사용자가 감시 대상·env·주기를 말하면 아래 절차로 감시 루프를 건다.

1. **대상 확정**: `--target skill/member/common` 또는 `--service <서비스명>`. 여러 개 지정 가능.
2. **기준 워터마크 초기화**: 스크립트를 한 번 실행해 나온 각 서비스 `max_ts`를 워터마크 맵으로 삼는다
   (또는 "지금부터" 원하면 현재 시각). 워터마크 맵은 대화 컨텍스트에 유지한다.
3. **`/loop {interval}` 로 재귀 실행.** 매 사이클마다:
   - `check_errors.py` 를 `--since-json '{"서비스명":"워터마크",...}'` 로 실행.
   - 출력의 마지막 `RESULT {json}` 을 파싱한다.
   - `total_new > 0` 이면:
     - 스크립트가 출력한 대상별 리포트(표 + trace 링크 + 배치 링크)를 세션에 그대로 보여준다.
     - `ToolSearch` 로 `select:PushNotification` 로드 후, `RESULT.push_text` 를 메시지로 푸시 알림을 보낸다.
     - 각 서비스의 워터마크를 `RESULT.services[svc].max_ts` 로 갱신한다(new_count>0인 서비스만).
   - `total_new == 0` 이면 `정상 (신규 ERROR 없음, HH:MM)` 한 줄만 남기고 푸시/링크는 생략한다.
4. **중단**: 사용자가 멈추라고 하면 `/loop`(cron) 작업을 `CronDelete` 로 취소한다.

> `/loop 10m` 처럼 60분 미만 고정 주기는 세션 한정 cron으로 동작한다(세션 종료 시 중단).
> 세션이 없어도 감시하려면 웹훅/launchd 기반이 필요하다(이 스킬 범위 밖).

## 대상 레지스트리 (env별 실측 서비스명)
| target | prod | dev | stg |
|---|---|---|---|
| `skill` | `run-prd-dfd-hsp-api-skill` | `run-dev-dfd-hsp-api-skill` | `stg-dfd-hsp-api` |
| `member` | `dfd-mem-api` | `dev-dfd-mem-api` | `stg-dfd-mem-api` |
| `common` | `dfd-com-api` | `dev-dfd-com-api` | `stg-dfd-com-api` |

- 프로젝트: dev=`dev-dfd-393200`, stg=`stg-dfd`, prod=`prd-dfd`. 리전 `asia-northeast3` 고정.
- 그 외 서비스(hsp-api-{병원}, gw, noti-api, interface-api 등)는 `--service <서비스명>` 으로 직접 지정.
  - 예: 특정 병원 hsp-api → `--service run-prd-dfd-hsp-api-hallym`

## 스크립트 인자
| 인자 | 기본값 | 설명 |
|---|---|---|
| `--env {dev,stg,prod}` | (필수) | 프로젝트 매핑 |
| `--target {skill,member,common}` | — | 레지스트리 대상(반복 가능) |
| `--service NAME` | — | 임의 Cloud Run 서비스(반복 가능). `--target`와 최소 하나 필수 |
| `--severity` | `ERROR` | `severity>=` 조건 |
| `--freshness` | `11m` | 조회 기간(주기보다 살짝 크게) |
| `--limit` | `100` | 대상당 최대 건수 |
| `--since-json` | — | 대상별 워터마크 `{"서비스명":"RFC3339"}`. 초과분만 신규 |
| `--exclude REGEX` | — | 제외할 메시지 정규식(반복 가능). 노이즈 검증 에러 등 |
| `--window-pad` | `5` | 링크 timeRange 앞뒤 분 |
| `--link-traces` | `5` | trace 링크 최대 개수 |
| `--region` | `asia-northeast3` | 리전 |

## 링크 규칙 (중요)
- 과거 로그가 보이도록 링크 시간범위는 **절대범위 `timeRange={start}%2F{end}`** 를 쓴다.
  `cursorTimestamp+duration` 은 "지금 기준 상대범위"로 해석돼 과거 로그가 안 보인다.
- **trace 링크**는 severity 필터 없이 `trace="projects/{proj}/traces/{id}"` 로 걸어 요청 하나의 전체 흐름
  (요청 → 응답 → 에러 → 컨트롤러 캐치)을 한 화면에서 본다.

## 예시
```bash
# prod skill+member+common 통합 점검
python3 ~/.claude/skills/cloudrun-error-watch/scripts/check_errors.py --env prod --target skill --target member --target common

# 노이즈성 검증 에러 제외하고 감시
... --env prod --target skill --exclude "유효하지 않습니다" --exclude "RuntimeException: 2000"

# dev 특정 병원 hsp-api 감시
... --env dev --service run-dev-dfd-hsp-api-edge
```
사용 흐름 예: 사용자가 "prod skill·member·common 10분마다 감시해줘" → 1회 점검으로 워터마크 초기화 →
`/loop 10m` 로 위 "주기 감시 시작" 절차 수행.

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-07-09 | 최초 작성. 다중 Cloud Run 서비스(skill/member/common + 임의 서비스) 주기 에러 감시, 워터마크 기반 신규 판정, trace별 절대범위 Logs Explorer 딥링크, 세션 푸시 알림. `scripts/check_errors.py` 조회 전용 코어. |
