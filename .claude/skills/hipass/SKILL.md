---
name: hipass
description: Use when working on HiPass (진료비 자동결제) feature — chatbot blocks, frontend webview APIs, 11pay SDK integration, Kocess token expiry, or card register/detail/expire flows in karechat-server-skill
---

# Karechat HiPass (진료비 하이패스)

## 목적

하이패스(진료비 자동결제) 기능의 아키텍처, 엔드포인트, 데이터 흐름, 컨텍스트 의존성, 외부 연동 구조를 정의한다.
신규 개발/수정 시 이 문서를 기준으로 레이어 역할과 컨텍스트 사용 규칙을 따른다.

## 레이어 구조

```
Presentation (컨트롤러 4개)
├── HiPassChatbotController     — 챗봇 스킬 블록 (/cht/)
├── HiPassFrontEndController    — 프론트엔드 웹뷰 API (/few/)
├── SkPayRestController         — 11pay REST API (/skpay/)
└── SkPayMvcController          — 11pay MVC(SDK 화면 + 콜백) (/skpay/)

Application (서비스/컴포넌트 3개)
├── HiPassBlockComponent        — 챗봇 말풍선 블록 조립
├── HipassService               — 프론트엔드 비즈니스 로직
└── SkpayService                — 11pay SDK/토큰/콜백/해지 처리
```

## 엔드포인트 전체 맵

### 챗봇 (`HiPassChatbotController`)

| 경로 | 메서드 | 기능 | 응답 |
|------|--------|------|------|
| `/dfd/api/hsp/cht/v1/hipass/register` | POST | 하이패스 관리하기 블록 | `ChatbotResponseDto` |
| `/dfd/api/hsp/cht/v1/hipass/guide` | POST | 하이패스 이용안내 블록 | `ChatbotResponseDto` |

### 프론트엔드 (`HiPassFrontEndController`)

| 경로 | 메서드 | 기능 | 응답 |
|------|--------|------|------|
| `/dfd/api/hsp/few/v1/hipass/sms/{hspId}/{mpiKey}` | GET | SMS 수신정보 입력 화면 | `HiPassSmsResponse` |
| `/dfd/api/hsp/few/v1/hipass/result/{result}/{hspId}/{mpiKey}` | GET | 카드 등록 결과 페이지 | `HipassPayMethod` |
| `/dfd/api/hsp/few/v1/hipass/detail/{hspId}/{mpiKey}/{hipassId}` | GET | 카드관리 상세 | `HipassPayMethod` |
| `/dfd/api/hsp/few/v1/hipass/available/{hspId}` | GET | 사용 가능 여부(메뉴 노출: `hipass_use` AND `submall_id`) | `Map<"available", Boolean>` |
| `/dfd/api/hsp/few/v1/hipass/sms/modify` | POST | SMS 수신정보 수정 | `HiPassSmsModifyResponse` |

### 11pay / SkPay (`SkPayRestController` + `SkPayMvcController`)

| 경로 | 메서드 | 타입 | 기능 | 응답 |
|------|--------|------|------|------|
| `/dfd/api/skpay/{hspId}/{mpiKey}` | GET | MVC | 11pay SDK 카드등록 화면 | Thymeleaf `11pay-card-register` |
| `/dfd/api/skpay/grant/{hspId}/{mpiKey}` | POST | REST | 11pay 인증 토큰 요청 | `SkpayAuthGrantResponse` |
| `/dfd/api/skpay/callback/{hspId}/{mpiKey}` | POST | MVC | 11pay 콜백 처리 | Thymeleaf `callback-redirect` |
| `/dfd/api/skpay/expire/{hspId}/{mpiKey}` | POST | REST | 하이패스 카드 해지 | `HipassExpireRes` |

## 핵심 플로우

### 1. 카드 등록 플로우

```
챗봇 "하이패스 관리하기"
  → CCRC 동의 확인 (CcrcIntegrationService.isAgreed)
  → [미동의] 동의 페이지 webLink 제공
  → [동의] 카드 목록 조회 (H_89: getHiPassAllPayMethod)
  → 프론트엔드 SMS 입력 화면 (/few/.../sms)
  → 11pay SDK 호출 (/skpay/{hspId}/{mpiKey})
  → 11pay 인증 토큰 발급 (/skpay/grant)
  → 사용자 카드 입력 (11pay SDK UI)
  → 11pay 콜백 (/skpay/callback)
    → [성공] encData 복호화 → 병원 등록 전달 (registerHiPass)
      → [병원 실패] 카드 목록 재확인 → [미반영] 토큰 즉시 만료
    → [실패] 실패 결과 페이지 리다이렉트
  → 결과 페이지 (/few/.../result)
```

### 2. 카드 상세 조회 / 관리

```
챗봇 carousel "관리하기" 버튼 클릭
  → 프론트엔드 상세 페이지 (/few/.../detail)
  → 동의 여부 재확인
  → 카드 상세 조회 (H_90: getHiPassPayMethod)
  → 병원별 안내사항 조회 (DtlMst: HIPASS_GUIDE)
```

### 3. 카드 해지 플로우

```
프론트엔드 해지 요청 (/skpay/expire)
  → 환자번호 미입력 시 환자 정보 조회 (getPatientInfo)
  → 코세스(Kocess) 소켓 통신으로 토큰 만료
    → [이미 해지] "이미 해지된 카드에요" 응답
    → [성공] 병원에 해지 전달 (expireHiPass)
    → [실패] 에러 응답 + 원무창구 안내
```

## 하이패스 노출/진입 판정 (`hipass_use` 컬럼)

하이패스 "사용여부"는 전용 컬럼 **`payment_hsp_mst.hipass_use`** (`tinyint(1)`, `1`=사용/노출, `0`=미사용)로 판단한다.
(2026-10 전용 컬럼 분리 — 이전엔 `submall_id` null 여부로 간접 판정해 가맹등록과 오픈이 분리되지 않았음)

| 판정 | 메서드 | 조건 | 용도 |
|------|--------|------|------|
| **메뉴/진입점 노출** | `HipassService.isHipassAvailable()` | `hipass_use=1` AND `submall_id` 존재 | `/available` API → common·third-party 서버의 챗봇 시작/부가서비스 카드 노출 |
| **발화 직접 진입** | `HipassService.isHipassEntryAllowed()` | `submall_id`(가맹) 존재 (`hipass_use` 무관) | 챗봇 "하이패스 관리하기" 발화 진입 (`HiPassBlockComponent`) |

- **발화 진입은 가맹(`submall_id`)만 있으면 허용**된다. 대부분 병원이 개발환경 없이 운영에만 연결돼 있어, **운영 오픈 전(`hipass_use=0`)에도 "하이패스 관리하기" 발화로 테스트**할 수 있게 하기 위함이다.
- 가맹이 없으면(`submall_id` 없음) 발화해도 빈 블록(`emptyContentsBlock`) — 11pay가 동작 불가하므로 차단.
- **운영 오픈 = `hipass_use`를 `1`로 설정**(메뉴 노출). `submall_id`는 가맹 등록 시점에 바로 넣어도 된다(발화 테스트 가능).

## 컨텍스트 의존성

### ThreadLocal 컨텍스트

모든 하이패스 로직은 ThreadLocal 기반 컨텍스트에 의존한다. request body 재파싱 없이 유틸로 접근한다.

| 유틸 | 용도 |
|------|------|
| `CurrentContext.currentHspId()` | 병원 ID |
| `CurrentContext.currentHspMst()` | 병원 마스터 (채널 ID, 인터페이스 URL 등) |
| `CurrentContext.currentMpiKey()` | MPI 키 |
| `CurrentContext.currentUsrId()` | 사용자 ID |
| `CurrentContext.currentUsrInfo()` | 사용자 정보 (CI키, 전화번호 등) |
| `CurrentContext.currentUsrNm()` | 사용자 이름 |
| `CurrentContext.currentHspName()` | 병원명 |
| `CurrentContext.currentBaseUrl()` | 인터페이스 서버 URL |
| `CurrentContext.currentInterfaceSeverHspCd()` | 인터페이스 서버 병원 코드 |
| `PayHspMstContextHolder.currentPayHspMst()` | 결제 설정 (submallId, hipassUse, cardMaxCount, installmentAmount, telUseType) |

### 컨텍스트 초기화 경로

- **챗봇 경로** (`/cht/`): `ChatbotRequestBodyAdvice` → `RequestContextHolder` + `PayHspMstContextHolder`
- **프론트엔드 경로** (`/few/`): `NonChatbotInterceptor` → path variable(`hspId`, `mpiKey`)로 `RequestContext` 수동 설정
- **SkPay 경로** (`/skpay/`): `NonChatbotInterceptor` 동일

## 외부 연동

### 병원 인터페이스 (`HspInterfaceCommonService`)

| 메서드 | 용도 | 비고 |
|--------|------|------|
| `getHiPassAllPayMethod()` | 전체 카드 목록 조회 (H_89) | `CommonConvertRequest` 사용 |
| `getHiPassPayMethod()` | 카드 상세 조회 (H_90) | `HiPassDetailRequest` 사용 |
| `registerHiPass()` | 카드 등록 병원 전달 | `HiPassRegisterRequest` 사용 |
| `expireHiPass()` | 카드 해지 병원 전달 | `HipassExpireRequest` 사용 |
| `modifyHiPass()` | SMS 수신정보 수정 | `HipassModifyRequest` 사용 |
| `getPatientInfo()` | 환자 정보 조회 | 해지 시 ptNo 미입력 보충 |

### 11pay (SK Pay)

- **인증 토큰**: `SkPay.serverUrl` + `authorizationsGrantPath`로 REST 호출
- **인증 키**: 환경변수 `SK_AUTHORIZATION_{hspId}`에서 병원별 키 조회
- **SDK 화면**: `SkPaySdkRequest`로 Thymeleaf 템플릿(`11pay-card-register`) 렌더링
- **콜백**: `SkPayCallBack` → Base64 디코드(`HiPassUtil.decryptResult`) → AES256 복호화(`Security.decryptForSkAes256`)

### 코세스 (Kocess) — 토큰 만료

- **프로토콜**: TCP 소켓 통신 (EUC-KR 인코딩)
- **설정**: `HiPassProperties.Kocess` (host, port, 전문 헤더)
- **요청**: `HipassTokenExpireReq.convertToByte()` → 2321 byte 전문
- **응답**: `KocessTokenExpireRes` (ansCode `0000` = 성공, skCode `20002020` = 이미 해지)
- **타임아웃**: 20초

### CCRC (동의 서비스)

- `CcrcIntegrationService.isAgreed(hspId, usrId, CcrcIntegrationEnum.HIPASS)` — 스킬/공통 양쪽 동의 확인
- 미동의 시: `urlBuilder.integrationCcrcUrl(...)` → 동의 페이지 URL 생성 후 앱스킴 리다이렉트

## 주요 DTO/응답 구조

### HipassPayMethod (카드 정보 — 프론트엔드 + 챗봇 공용)

```
hipassId, paymentToken, cardName, cardNum, cardAcquirerCode
mainCardYn, cardHolderName, applyStartDate, applyEndDate
smsYn, smsPhoneNum, regDate, installmentMonth
applicantName, applicantPhoneNum, applicantBrdyDt, relationWithPt
result, confirmScheme, retryLink (프론트엔드 전용)
guideContents (병원별 안내사항, 프론트엔드 전용)
```

### HiPassSmsResponse (SMS 입력 화면 응답)

```
result ("0"=성공, "1"=실패/최대초과, "2"=미동의)
defaultPhoneNum, registerScheme, ccrcUrl
installmentAmount, telUseType
```

## 통계 이벤트

`FunctionalStatisticsDto`를 `ApplicationEventPublisher`로 발행한다.

| detailFunctionType | 발생 시점 |
|---|---|
| `MANAGING_BLOCK` | 챗봇 카드 목록 조회 성공 |
| `REGISTER` | 카드 등록 완료 (성공/실패) |
| `EXPIRE` | 카드 해지 완료 (성공/실패) |

## 참고 코드 위치

| 역할 | 경로 |
|------|------|
| 챗봇 컨트롤러 | `src/.../v2/presentation/chatbot/hipass/HiPassChatbotController.java` |
| 프론트엔드 컨트롤러 | `src/.../v2/presentation/frontend/HiPassFrontEndController.java` |
| SkPay REST 컨트롤러 | `src/.../v2/presentation/thirdparty/skPay/SkPayRestController.java` |
| SkPay MVC 컨트롤러 | `src/.../v2/presentation/thirdparty/skPay/SkPayMvcController.java` |
| 챗봇 블록 컴포넌트 | `src/.../v2/application/hipass/HiPassBlockComponent.java` |
| 프론트엔드 서비스 | `src/.../v2/application/hipass/HipassService.java` |
| SkPay 서비스 | `src/.../v2/application/hipass/SkpayService.java` |
| 프론트엔드 응답 | `src/.../v2/presentation/frontend/response/HiPassSmsResponse.java` |
| 프론트엔드 요청 | `src/.../v2/infrastructure/frontend/HipassFrontReq.java` |
| 병원 요청 DTO | `src/.../v2/infrastructure/hospitalinterface/request/hipass/HipassRequest.java` |
| 병원 응답 DTO | `src/.../v2/infrastructure/hospitalinterface/response/hipass/HiPass*Response.java` |
| SkPay 콜백 | `src/.../v2/domain/thirdparty/skPay/SkPayCallBack.java` |
| 코세스 토큰 요청 | `src/.../v2/domain/thirdparty/kocess/HipassTokenExpireReq.java` |
| 설정 | `src/.../config/properties/HiPassProperties.java` |
| 유틸 | `src/.../utility/HiPassUtil.java` |
| CCRC 동의 서비스 | `src/.../v2/application/CcrcIntegrationService.java` |

## 작업 체크리스트

하이패스 관련 작업 완료 시 해당 항목을 확인한다.

- [ ] 챗봇 블록 변경 → `ChatbotResponseDto` 반환 계약 유지, Kakao 말풍선 필수 필드 확인
- [ ] 프론트엔드 API 변경 → `NonChatbotInterceptor` 경로에서 `RequestContext` 초기화 커버 확인
- [ ] SkPay 경로 변경 → `NonChatbotInterceptor` 컨텍스트 초기화 + `PayHspMstContextHolder` 초기화 확인
- [ ] 카드 등록 로직 변경 → 콜백 성공/실패 분기, 병원 전달 실패 시 재확인 + 토큰 만료 후처리 흐름 유지
- [ ] 카드 해지 로직 변경 → 코세스 소켓 통신 → 병원 전달 순서 유지, 이미 해지 케이스 처리
- [ ] 동의 흐름 변경 → `CcrcIntegrationEnum.HIPASS` 기준 동의 확인 로직 유지
- [ ] 결제 설정 참조 → `currentPayHspMst()` 사용 (submallId, cardMaxCount, installmentAmount)
- [ ] 통계 이벤트 → `FunctionalStatisticsDto` 발행 누락 없음 (MANAGING_BLOCK, REGISTER, EXPIRE)

## 병원 하이패스 연동 가이드

신규 병원에 하이패스 기능을 연동할 때 아래 절차를 따른다.
사용자가 병원 ID(`hspId`)를 제공하지 않으면 반드시 먼저 물어본다.

### 입력 데이터 형식

사용자가 아래 형태로 정보를 붙여넣는다:

```
MXID : hp-xxxxx
가맹점명 : OO병원 | 123-45-67890
VAN : NICE

<상용>
MCT_Auth_key : ...
Basic_Auth_key : ...
Basic_Auth_key_BASE64 : ...

<개발stg>
CT_Auth_key : ...
Basic_Auth_key : ...
Basic_Auth_key_BASE64 : ...
```

### 사전 준비: DB 접근은 `db-query` 스킬을 경유한다

> **이 머신의 실제 DB 접근 방식**: 로컬 DB 작업은 mysql CLI가 아니라 **`db-query` 스킬(Python pymysql + 스킬 로컬 `.env`)** 로 한다. mysql-client는 설치돼 있지 않으며 설치할 필요도 없다. 비밀번호는 `~/.zshrc`가 아니라 `db-query` 스킬의 `.env`에 있고, 스크립트가 스스로 로드한다. **`.env`를 `Read`/`cat`/`grep`으로 열람하지 않는다.**

#### 1. dev DB 연결 확인

```bash
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --sql "SELECT hsp_id, submall_id, submall_business_num FROM payment_hsp_mst WHERE hsp_id = {hspId}"
```

- 정상 연결 시 `[연결] env=dev host=10.50.32.5 db=dfdskill` 로그와 결과가 출력된다.
- 연결 실패 시 사용자에게 VPN 연결 및 `db-query` 스킬 `.env` 설정을 확인하도록 안내한다.

#### 2. dev 쓰기 워크플로우 (INSERT/UPDATE)

`db-query`는 dev 쓰기를 2단계로 보호한다.

```bash
# 1) --allow-write 없이 실행 → 쓰기 감지 시 SQL을 출력하고 exit 3 으로 중단(미리보기)
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --sql "UPDATE payment_hsp_mst SET ... WHERE hsp_id={hspId}"

# 2) 사용자 승인 후에만 --allow-write 를 붙여 재실행
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --allow-write --sql "UPDATE payment_hsp_mst SET ... WHERE hsp_id={hspId}"
```

- member DB 등 같은 host의 다른 DB는 `--db {db_name}` 로 오버라이드한다.
- 여러 구문은 `--sql`에 세미콜론으로 이어서 넣을 수 있다.

> **⚡ 성능 — DB write는 반드시 배치로 실행한다.**
> `query.py`는 호출마다 python 인터프리터 기동 + pymysql 커넥션 수립 + VPN 왕복 비용이 든다. 단계마다 따로 실행하면 이 비용이 배로 늘어 전체 세팅이 느려진다.
> 따라서 개발 DB에 반영할 SQL(Step 2 ~ 2-4 중 값이 확보된 것)은 **가능한 한 세미콜론으로 이어붙여 한 번에** 실행한다. 미리보기 1회 + 승인 후 실행 1회로 끝내는 것이 원칙이다.

#### 3. 상용(prod) DB 쓰기 — `db-query` 로는 차단됨

`db-query` 스킬은 **prod 쓰기를 항상 차단**한다(`--allow-write` 무시). 따라서 상용 DB에 반영이 필요한 단계(`submall_id` 운영 오픈, `hsp_prop`/`stte_ccrc`/`dtl_mst` 상용 등록)는 아래 중 하나로 처리한다.

- **조회만** 필요하면: `--env prod` 로 SELECT (읽기 전용 허용).
- **쓰기**가 필요하면: SQL을 **생성만** 하여 사용자에게 전달하고, 사용자가 QueryPie 등 승인된 경로로 직접 실행한다. (팀 룰: prod 쓰기는 SQL 생성 + 사용자 승인/직접 실행)

### Step 1: 입력 데이터 파싱

| 항목 | 추출 규칙 |
|------|-----------|
| `submall_id` | MXID 값 그대로 (예: `hp-snubh`) |
| `submall_business_num` | 가맹점명의 사업자번호에서 하이픈 제거 (예: `129-82-06989` → `1298206989`) |
| 개발 `SK_AUTHORIZATION` | `"Basic " + 개발stg Basic_Auth_key_BASE64` |
| 개발 `SK_SECRETKEY` | 개발stg `CT_Auth_key` |
| 상용 `SK_AUTHORIZATION` | `"Basic " + 상용 Basic_Auth_key_BASE64` |
| 상용 `SK_SECRETKEY` | 상용 `MCT_Auth_key` |

### Step 1-1: 파싱 결과 확인 및 일괄 실행

Step 1 파싱 후 **아래 3가지를 한 번에 실행**한다 (사용자 확인 후):

1. **개발 DB** — `payment_hsp_mst` UPDATE (`submall_id`, `submall_business_num`)
2. **Secret Manager** — 개발 + 상용 프로젝트에 `SK_AUTHORIZATION_{hspId}`, `SK_SECRETKEY_{hspId}` 생성
3. **Cloud Run** — 개발 + 상용 서비스에 보안비밀 환경변수 연동

#### 실행 전 확인 절차

파싱 결과를 아래 형식으로 사용자에게 보여주고, **"진행할까요?"** 를 물어본 뒤 승인을 받고 실행한다.

```
## hspId={hspId} 일괄 등록 요약

### 1. 개발 DB (payment_hsp_mst)
- submall_id: {submall_id}
- submall_business_num: {submall_business_num}

### 2. Secret Manager
| 환경 | 시크릿 키 | 값 (앞 10자) |
|------|-----------|-------------|
| 개발 | SK_AUTHORIZATION_{hspId} | Basic {앞10자}... |
| 개발 | SK_SECRETKEY_{hspId} | {앞10자}... |
| 상용 | SK_AUTHORIZATION_{hspId} | Basic {앞10자}... |
| 상용 | SK_SECRETKEY_{hspId} | {앞10자}... |

### 3. Cloud Run 환경변수 연동
- 개발: run-dev-dfd-hsp-api-skill (dev-dfd-393200)
- 상용: run-prd-dfd-hsp-api-skill (prd-dfd)

### 4. IntelliJ 환경변수 (개발용)
위 작업이 진행되는 동안 IntelliJ Run/Debug Configuration > Environment variables에 아래 값을 등록하세요:
- `SK_AUTHORIZATION_{hspId}` = `Basic {개발stg_Basic_Auth_key_BASE64}`
- `SK_SECRETKEY_{hspId}` = `{개발stg_CT_Auth_key}`

위 내용으로 진행할까요?
```

#### 실행 순서

사용자가 승인하면 아래 순서로 실행한다. **DB 등록과 Secret Manager 등록은 독립적이므로 병렬 실행**한다.

1. **병렬 실행**:
   - 개발 DB `payment_hsp_mst` UPDATE
   - 개발 Secret Manager `SK_AUTHORIZATION_{hspId}` 생성
   - 개발 Secret Manager `SK_SECRETKEY_{hspId}` 생성
   - 상용 Secret Manager `SK_AUTHORIZATION_{hspId}` 생성
   - 상용 Secret Manager `SK_SECRETKEY_{hspId}` 생성
2. **순차 실행** (Secret Manager 완료 후):
   - 개발 Cloud Run `--update-secrets` 연동 → **`run_in_background: true`로 백그라운드 실행**
   - 상용 Cloud Run `--update-secrets` 연동 → **`run_in_background: true`로 백그라운드 실행**
3. **Cloud Run 배포를 기다리지 않고** 바로 다음 단계(Step 2-1 이후)의 사용자 입력 요청을 안내한다.
4. 백그라운드 Cloud Run 배포 완료 알림이 오면 결과를 요약하고, 사용자가 직접 확인할 수 있도록 GCP 콘솔 링크를 함께 제공한다:

```
✅ Cloud Run 배포 완료

### Secret Manager 확인
- 개발: https://console.cloud.google.com/security/secret-manager/secret/SK_AUTHORIZATION_{hspId}/versions?project=dev-dfd-393200
- 개발: https://console.cloud.google.com/security/secret-manager/secret/SK_SECRETKEY_{hspId}/versions?project=dev-dfd-393200
- 상용: https://console.cloud.google.com/security/secret-manager/secret/SK_AUTHORIZATION_{hspId}/versions?project=prd-dfd
- 상용: https://console.cloud.google.com/security/secret-manager/secret/SK_SECRETKEY_{hspId}/versions?project=prd-dfd

### Cloud Run 리비전 확인
- 개발: https://console.cloud.google.com/run/detail/asia-northeast3/run-dev-dfd-hsp-api-skill/revisions?project=dev-dfd-393200
- 상용: https://console.cloud.google.com/run/detail/asia-northeast3/run-prd-dfd-hsp-api-skill/revisions?project=prd-dfd
```

> **gcloud 인증 만료 시**: Secret Manager/Cloud Run 명령어가 인증 오류를 반환하면, 사용자에게 `! gcloud auth login`을 실행하도록 안내하고, 로그인 완료 후 실패한 명령어만 재실행한다.

> **Secret Manager에 이미 시크릿이 존재하면**: `create` 대신 `versions add`로 새 버전을 추가한다.

### Step 2: DB 등록 — `payment_hsp_mst` 테이블

> **⚡ Step 2 ~ 2-4는 한 번에 실행한다.** 아래 Step 2 ~ 2-4는 모두 **같은 개발 DB(dfdskill)** 에 대한 write다. 값이 확보된 SQL을 단계별로 따로 돌리지 말고, **세미콜론으로 이어붙여 미리보기 1회 → 승인 → 실행 1회**로 처리한다. (호출 횟수 = 속도. 배치 원칙은 사전 준비 §2 참고)
>
> 예: `payment_hsp_mst` UPDATE(Step 2 + 2-1 + 2-1-1은 같은 테이블이므로 하나의 UPDATE로 합칠 수 있으면 합친다) + `hsp_prop` INSERT(2-2) + `stte_ccrc`/`stte_ccrc_cnte` INSERT(2-3) + `dtl_mst`(`CCRC_ITEM_MGMT`) INSERT(2-3-1) + `dtl_mst`(`HIPASS_GUIDE`) INSERT(2-4)를 하나의 `--sql`에 이어붙인다.
> ```bash
> # 미리보기 (쓰기 감지 시 exit 3)
> python3 ~/.claude/skills/db-query/scripts/query.py --env dev \
>   --sql "UPDATE payment_hsp_mst SET ... WHERE hsp_id={hspId}; INSERT INTO hsp_prop ...; INSERT INTO stte_ccrc ...; INSERT INTO stte_ccrc_cnte ...; INSERT INTO dtl_mst ...;"
> # 사용자 승인 후 실행 (--allow-write)
> python3 ~/.claude/skills/db-query/scripts/query.py --env dev --allow-write \
>   --sql "UPDATE payment_hsp_mst SET ... WHERE hsp_id={hspId}; INSERT INTO hsp_prop ...; INSERT INTO stte_ccrc ...; INSERT INTO stte_ccrc_cnte ...; INSERT INTO dtl_mst ...;"
> ```
> 아직 값이 없는 단계(예: 피그마 확인 대기)는 빼고, 확보된 것만 묶으면 된다. 상용(prod)은 배치와 별개로 SQL만 생성해 전달한다.

개발 DB (`db-query` 스킬 `--env dev` → host `10.50.32.5`, db `dfdskill`)에 반영한다.

```sql
UPDATE payment_hsp_mst
SET submall_id = '{MXID}',
    submall_business_num = '{사업자번호_하이픈제거}'
WHERE hsp_id = {hspId};
```

실행 방법 (미리보기 → 승인 → 실행):
```bash
# 미리보기 (쓰기 감지 시 exit 3)
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --sql "UPDATE payment_hsp_mst SET submall_id='{MXID}', submall_business_num='{사업자번호}' WHERE hsp_id={hspId}"
# 사용자 승인 후 실행
python3 ~/.claude/skills/db-query/scripts/query.py \
  --env dev --allow-write --sql "UPDATE payment_hsp_mst SET submall_id='{MXID}', submall_business_num='{사업자번호}' WHERE hsp_id={hspId}"
```

> **상용 DB 반영**: `db-query`는 prod 쓰기를 차단한다. 상용은 위 UPDATE **SQL만 생성**해 사용자에게 전달하고, 사용자가 QueryPie 등 승인된 경로로 직접 실행한다. 상용 조회가 필요하면 `--env prod` 로 SELECT(읽기 전용)만 사용한다.

> **중요 — 운영 "메뉴 노출"은 `submall_id`가 아니라 `hipass_use` 컬럼으로 제어합니다 (2026-10 변경).**
> - `submall_id`/`submall_business_num`(가맹 정보)은 개발·상용 모두 **연동 시점에 바로 등록**해도 됩니다. 가맹만 등록되면 운영에서 "하이패스 관리하기" **발화로 테스트** 가능합니다(`isHipassEntryAllowed`).
> - **운영 메뉴 노출은 `hipass_use=1`** 을 **운영 오픈 일정에 맞춰** 설정하는 것으로 제어합니다(Step 2-1-1 참고). 신규 연동은 `hipass_use=0`(기본, 미노출)으로 둡니다.

### Step 2-1: 매입사 코드 등록 — `payment_hsp_mst` 테이블

사용자가 매입사 코드를 제공하면 동일 테이블에 업데이트한다. 여러 코드가 콤마로 구분된 경우 그대로 저장한다.

| 입력 키 | 컬럼명 | 예시 |
|---------|--------|------|
| BC | `bc` | `01` |
| KB | `kb` | `02` |
| 하나 | `hana` | `03,29` |
| 삼성 | `samsung` | `06` |
| 신한 | `shinhan` | `05,07` |
| 현대 | `hyundai` | `08` |
| 롯데 | `lotte` | `33,38` |
| 우리 | `woori` | `17` |
| NH | `nh` | `11` |

```sql
UPDATE payment_hsp_mst
SET bc = '{BC}',
    kb = '{KB}',
    hana = '{하나}',
    samsung = '{삼성}',
    shinhan = '{신한}',
    hyundai = '{현대}',
    lotte = '{롯데}',
    woori = '{우리}',
    nh = '{NH}'
WHERE hsp_id = {hspId};
```

> **참고**: 매입사 코드는 Step 2의 DB 등록과 동일한 접속 정보를 사용한다. 사용자가 제공하지 않은 카드사는 UPDATE에 포함하지 않는다.

### Step 2-1-1: 하이패스 설정 등록 — `payment_hsp_mst` 추가 컬럼

아래 피그마 정책서 링크를 사용자에게 안내하고, 해당 병원의 정책 항목을 확인하여 값을 알려달라고 요청한다.

> **피그마 정책서**: https://www.figma.com/design/xXnxQ7zvJVN2IktpRPpMCC/DFD-%25ED%2595%2598%25EC%259D%25B4%25ED%258C%25A8%25EC%258A%25A4-%25EC%259E%2590%25EB%258F%2599%25EA%25B2%25B0%25EC%25A0%259C-?node-id=4050-7952&t=sfbEVkhOR5T1uh7V-0

#### 피그마 정책서에서 확인할 항목

| 피그마 정책서 항목 | 컬럼 | 값 매핑 |
|-------------------|------|---------|
| 카드 최대 등록 갯수 | `card_max_count` | 숫자 그대로 (예: `3`) |
| 하이패스 알림 설정 필수 여부 | `tel_use_type` | 필수→`REQUIRED`, 선택→`OPTIONAL`, 미사용→`DISABLED` |
| 하이패스 관리 시 연락처 수정 가능 여부 | `tel_modify_use` | Y→`1`, N→`0` |
| 할부 제공 기준 금액 | `installment_amount` | 금액 숫자 (예: `50000`), 미사용→`NULL` |
| 하이패스 메뉴 노출 여부(오픈 계획) | `hipass_use` | 노출→`1`, 미노출→`0`. **신규 연동은 `0`(기본), 운영 오픈 시 `1`** |

```sql
UPDATE payment_hsp_mst
SET card_max_count = {카드최대갯수},
    tel_use_type = '{REQUIRED|OPTIONAL|DISABLED}',
    tel_modify_use = {1|0},
    installment_amount = {금액|NULL},
    hipass_use = {1|0}
WHERE hsp_id = {hspId};
```

> **참고**: `installment_amount`는 할부 개월 수가 있는 경우에만 금액을 설정하고, 할부가 없는 병원은 `NULL`로 둔다.
> **`hipass_use` (메뉴 노출 스위치)**: `tinyint(1) NOT NULL DEFAULT 0` 컬럼(2026-10 추가). **신규 연동은 `0`(미노출)으로 두고, 운영 오픈 시점에 `1`로 변경**해 메뉴를 노출한다. 가맹(`submall_id`)만 등록돼 있으면 `hipass_use=0`이어도 **발화로 진입·테스트**가 가능하다. (개발 DB에서 메뉴까지 확인하려면 `1`로 설정)

### Step 2-2: 하이패스 이용안내 병원 링크 등록 — `hsp_prop` 테이블

사용자가 병원 하이패스 안내 페이지 URL을 제공하면, `hsp_prop` 테이블에 `HIPASS_GUIDE_LINK` 코드로 등록한다.
이 링크는 챗봇 이용안내 블록(`HiPassBlockComponent.guideDefaultTextCard()`)에서 "병원 하이패스 안내사항" 버튼에 사용된다.

**개발 DB와 상용 DB 모두에 등록한다.**

```sql
INSERT INTO hsp_prop (hsp_id, code, value, description, use_yn)
VALUES ({hspId}, 'HIPASS_GUIDE_LINK', '{URL}', '하이패스 이용안내 병원 링크', 'Y');
```

이미 존재하는 경우 업데이트:
```sql
UPDATE hsp_prop
SET value = '{URL}'
WHERE hsp_id = {hspId} AND code = 'HIPASS_GUIDE_LINK';
```

기존 등록 예시:

| hsp_id | value | 병원 |
|--------|-------|------|
| 13 | `https://dongsan.dsmc.or.kr:49870/content/05use/02_0106.php` | 동산병원 |
| 5 | `https://seoul.hyumc.com/seoul/customer/question.do?...` | 한양대서울 |
| 7 | `https://www.snubh.org/medical/out/clinic09.do` | 분당서울대 |

### Step 2-3: CCRC 동의 데이터 등록 — `stte_ccrc` / `stte_ccrc_cnte` 테이블

하이패스 카드 등록 시 CCRC 동의 화면에 표시되는 데이터를 등록한다.
**개발 DB와 상용 DB 모두에 등록한다.**

> **상용 DB 작업 전 QueryPie가 실행 중인지 확인하세요.**

#### stte_ccrc (동의 헤더)

병원별로 1건 등록한다. `stte_ccrc_hdr`에 병원명이 포함된다.

**실제 테이블 컬럼:**
`stte_ccrc_id(PK)`, `hsp_id(PK)`, `grp_cd`, `dtl_cd`, `essn_yn`, `ccrc_scrn`, `stte_ccrc_title`, `stte_ccrc_hdr`, `stte_ccrc_footer`, `ccrc_dsp_yn`, `ccrc_dtl_yn`, `ver_no(PK)`, `use_yn`, `use_str_dt`, `use_end_dt`, `fsr_dtm`, `fsr_id`, `lst_mdf_dtm`, `lst_mdf_id`

```sql
INSERT INTO stte_ccrc (
  stte_ccrc_id, hsp_id, grp_cd, dtl_cd, essn_yn, ccrc_scrn,
  stte_ccrc_title, stte_ccrc_hdr, stte_ccrc_footer,
  ccrc_dsp_yn, ccrc_dtl_yn, ver_no, use_yn, use_str_dt, use_end_dt,
  fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id
) VALUES (
  82, {hspId}, 'HIPASS', 'HIPASS_01', 'Y', 'PTCFM',
  '개인정보 제3자 제공 동의',
  '{병원명}은 (주)카카오헬스케어에서 제공하는 서비스 이용을 위한 목적으로만 개인정보를 제공하며, 본래의 목적 범위를 초과하여 제3자에게 제공 및 처리하지 않습니다.',
  '본 동의는 거부할 수 있으며, 거부 시 서비스 이용이 제한될 수 있습니다.',
  'Y', 'Y', '1.0', 'Y', CURDATE(), '2099-12-31',
  CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0
);
```

> **병원명 확인**: `stte_ccrc_hdr`의 `{병원명}` 부분만 변경한다. 나머지 문구는 고정이다.

#### stte_ccrc_cnte (동의 항목 — 8건)

병원별로 8건 등록한다 (4개 항목 × 2개 화면 CCRC/PTCFM).

**실제 테이블 컬럼:**
`stte_ccrc_id(PK)`, `hsp_id(PK)`, `stte_ccrc_cnte_cd(PK)`, `ccrc_scrn(PK)`, `cnte_mak_seq`, `cnte_key`, `cnte_value`, `ver_no`, `use_yn`, `use_str_dt`, `use_end_dt`, `fsr_dtm`, `fsr_id`, `lst_mdf_dtm`, `lst_mdf_id`

```sql
INSERT INTO stte_ccrc_cnte (stte_ccrc_id, hsp_id, stte_ccrc_cnte_cd, ccrc_scrn, cnte_mak_seq, cnte_key, cnte_value, ver_no, use_yn, use_str_dt, use_end_dt, fsr_dtm, fsr_id, lst_mdf_dtm, lst_mdf_id)
VALUES
  -- HIPASS_01_01: 동의 목적(CCRC) / 제공 받는 자(PTCFM)
  (82, {hspId}, 'HIPASS_01_01', 'CCRC',  1, '동의 목적', '케어챗을 통해 병원 시스템에 등록된 진료비 자동결제(하이패스 서비스) 수단 관리', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),
  (82, {hspId}, 'HIPASS_01_01', 'PTCFM', 1, '제공 받는 자', '(주)카카오헬스케어', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),

  -- HIPASS_01_02: 제공 받는 자(CCRC) / 제공받는 자의 이용 목적(PTCFM)
  (82, {hspId}, 'HIPASS_01_02', 'CCRC',  2, '제공 받는 자', '카카오헬스케어', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),
  (82, {hspId}, 'HIPASS_01_02', 'PTCFM', 2, '제공받는 자의 이용 목적', '케어챗을 통해 병원 시스템에 등록된 진료비 자동결제(하이패스 서비스) 수단 관리', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),

  -- HIPASS_01_03: 개인정보 항목(CCRC) / 제공 항목(PTCFM) — ⚠️ 병원마다 다름
  (82, {hspId}, 'HIPASS_01_03', 'CCRC',  3, '개인정보 항목', '{개인정보_항목}', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),
  (82, {hspId}, 'HIPASS_01_03', 'PTCFM', 3, '제공 항목', '{개인정보_항목}', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),

  -- HIPASS_01_04: 보유 및 이용 기간(CCRC & PTCFM)
  (82, {hspId}, 'HIPASS_01_04', 'CCRC',  4, '제공받는 자의 보유 및 이용 기간', '케어챗 서비스 내 게시 후 즉시 파기', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0),
  (82, {hspId}, 'HIPASS_01_04', 'PTCFM', 4, '제공받는 자의 보유 및 이용 기간', '케어챗 서비스 내 게시 후 즉시 파기', '1.0', 'Y', CURDATE(), '2099-12-01', CURRENT_TIMESTAMP(), 0, CURRENT_TIMESTAMP(), 0);
```

#### ⚠️ 개인정보 항목 (`HIPASS_01_03`) — 병원별 상이

`HIPASS_01_03`의 `cnte_value` 값은 병원마다 다르다.
아래 피그마 정책서 링크를 사용자에게 안내하고, 해당 병원의 **"병원 → 케어챗 3자 제공 개인정보 항목"** 값을 확인하여 알려달라고 요청한다.

> **피그마 정책서**: https://www.figma.com/design/xXnxQ7zvJVN2IktpRPpMCC/DFD-%25ED%2595%2598%25EC%259D%25B4%25ED%258C%25A8%25EC%258A%25A4-%25EC%259E%2590%25EB%258F%2599%25EA%25B2%25B0%25EC%25A0%259C-?node-id=4050-7952&t=sfbEVkhOR5T1uh7V-0

기존 등록 예시:

| hsp_id | 병원 | 개인정보 항목 |
|--------|------|---------------|
| 5 | 한양대서울 | `자동결제 수단 정보(카드사, 소유자명, 8자리 숫자 부분 삭제된 카드번호, 유효기간), 휴대전화번호, 환자번호, 신청자명, 신청자 생년월일, 환자와의 관계, 신청자 휴대전화번호` |
| 6 | 한양대구리 | `자동결제 수단 정보(카드사, 소유자명, 8자리 숫자 부분 삭제된 카드번호, 유효기간), 휴대전화번호` |
| 7 | 분당서울대 | `자동결제 수단 정보(카드사, 소유자명, 8자리 숫자 부분 삭제된 카드번호, 유효기간), 휴대전화번호, 환자명(성명)` |
| 13 | 동산병원 | `자동결제 수단 정보(카드사, 소유자명, 8자리 숫자 부분 삭제된 카드번호, 유효기간), 휴대전화번호` |

> **참고**: 대부분 병원은 동일하지만, 병원마다 추가 항목이 있는 경우가 있으므로 반드시 피그마 정책서를 확인한다.

### Step 2-3-1: 마이메뉴 동의항목 노출 등록 — `dtl_mst` (`CCRC_ITEM_MGMT`) 테이블

> **⚠️ 누락 주의 — 이 단계가 빠지면 마이메뉴에 하이패스 동의항목이 안 보인다.**
> Step 2-3의 `stte_ccrc`/`stte_ccrc_cnte`만 넣고 이 단계를 빼먹기 쉽다. 그 경우 하이패스 등록/해지는 되지만, **앱 "마이메뉴 > 병원별 동의항목"에 하이패스가 노출되지 않는다.**

**개발 DB와 상용 DB 모두에 등록한다.**

#### 왜 필요한가 (노출 구조)

마이메뉴 동의 내역 조회(`CommonController.selectHspCcrcInfo` → `CommonService.selectHspCcrcInfo`)는 `stte_ccrc`(HIPASS)를 직접 도는 게 아니라, **`dtl_mst`의 `grp_cd='CCRC_ITEM_MGMT'` 목록을 기준(driver)으로 루프**를 돈다. 각 항목의 `dtl_cd`로 `stte_ccrc`를 매칭(`findByHspIdAndDtlCd`)해 화면에 표시한다.
→ 따라서 `CCRC_ITEM_MGMT`에 `HIPASS_01` 행이 없으면 `stte_ccrc`가 아무리 있어도 마이메뉴에 안 뜬다.

#### INSERT SQL 템플릿

```sql
INSERT INTO dtl_mst (hsp_id, grp_cd, dtl_cd, dtl_cd_nm, dtl_expl, dtl_cd_seq, use_yn, fsr_id, lst_mdf_id, fsr_dtm, lst_mdf_dtm)
VALUES
  ({hspId}, 'CCRC_ITEM_MGMT', 'HIPASS_01', '개인정보 제3자 제공 동의', '하이패스', {seq}, 'Y', 0, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());
```

- `dtl_cd` = `'HIPASS_01'` — **Step 2-3의 `stte_ccrc.dtl_cd`와 반드시 동일**해야 매칭된다.
- `dtl_cd_nm` = `'개인정보 제3자 제공 동의'`, `dtl_expl` = `'하이패스'` (고정).
- `{seq}` = 해당 병원의 기존 `CCRC_ITEM_MGMT` 항목 다음 순번. 등록 전 아래로 현재 최대 seq를 확인한다.

```bash
python3 ~/.claude/skills/db-query/scripts/query.py --env dev \
  --sql "SELECT dtl_cd, dtl_cd_seq FROM dtl_mst WHERE grp_cd='CCRC_ITEM_MGMT' AND hsp_id={hspId} ORDER BY dtl_cd_seq"
```

> **중복 방지**: 이미 `HIPASS_01`이 있으면 INSERT하지 말고 `use_yn='Y'`인지만 확인한다.

기존 등록 예시:

| hsp_id | 병원 | dtl_cd | seq |
|--------|------|--------|-----|
| 13 | 동산병원 | `HIPASS_01` | 7 |
| 41 | 대전선병원 | `HIPASS_01` | 4 |
| 42 | 유성선병원 | `HIPASS_01` | 4 |

### Step 2-4: 하이패스 안내 사항 등록 — `dtl_mst` 테이블

프론트엔드 카드 상세 화면에서 표시되는 하이패스 안내 사항 데이터를 등록한다.
**개발 DB와 상용 DB 모두에 등록한다.**

> **상용 DB 작업 전 QueryPie가 실행 중인지 확인하세요.**

#### 데이터 추출 방법

아래 피그마 정책서 안내 이미지 링크를 사용자에게 안내하고, 해당 병원의 하이패스 안내 사항 Bold/Medium 텍스트를 확인하여 알려달라고 요청한다.

> **피그마 정책서 (안내 사항)**: https://www.figma.com/design/xXnxQ7zvJVN2IktpRPpMCC/DFD-%ED%95%98%EC%9D%B4%ED%8C%A8%EC%8A%A4-%EC%9E%90%EB%8F%99%EA%B2%B0%EC%A0%9C-?node-id=4050-7951&m=dev

**피그마 → DB 매핑 규칙:**
- **Bold 텍스트** → `dtl_cd_nm` (제목)
- **Medium 텍스트** → `dtl_expl` (설명)
- `dtl_cd_nm`과 `dtl_expl` 중 하나만 있을 수 있다 (없는 쪽은 `NULL`)
- 피그마 디자인의 위에서 아래 순서대로 `dtl_cd_seq` = 1, 2, 3, ... 으로 매긴다
- `dtl_cd`는 `HIPASS_GUIDE_01`, `HIPASS_GUIDE_02`, ... 형식 (`dtl_cd_seq`에 맞춰 0-패딩 2자리)

#### INSERT SQL 템플릿

```sql
INSERT INTO dtl_mst (hsp_id, grp_cd, dtl_cd, dtl_cd_nm, dtl_expl, dtl_cd_seq, use_yn, fsr_id, lst_mdf_id, fsr_dtm, lst_mdf_dtm)
VALUES
  ({hspId}, 'HIPASS_GUIDE', 'HIPASS_GUIDE_01', '{Bold텍스트|NULL}', '{Medium텍스트|NULL}', 1, 'Y', 0, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
  ({hspId}, 'HIPASS_GUIDE', 'HIPASS_GUIDE_02', '{Bold텍스트|NULL}', '{Medium텍스트|NULL}', 2, 'Y', 0, 0, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
  -- ... 피그마 디자인 순서대로 계속
  ;
```

> **항목 수와 내용은 전부 병원마다 다르다.** 반드시 피그마 정책서를 확인하고 추출한다.

#### 기존 등록 예시 (hsp_id별 항목 수)

| hsp_id | 병원 | 총 항목 수 |
|--------|------|-----------|
| 5 | 한양대서울 | 5 |
| 6 | 한양대구리 | 5 |
| 7 | 분당서울대 | 5 |
| 13 | 동산병원 | 6 |

### Step 3: GCP Secret Manager 등록

#### 개발 (dev-dfd-393200)

```bash
# SK_AUTHORIZATION_{hspId}
echo -n 'Basic {개발stg_Basic_Auth_key_BASE64}' | \
  gcloud secrets create SK_AUTHORIZATION_{hspId} \
    --project=dev-dfd-393200 \
    --data-file=- \
    --replication-policy=automatic

# SK_SECRETKEY_{hspId}
echo -n '{개발stg_CT_Auth_key}' | \
  gcloud secrets create SK_SECRETKEY_{hspId} \
    --project=dev-dfd-393200 \
    --data-file=- \
    --replication-policy=automatic
```

> 이미 시크릿이 존재하면 `create` 대신 새 버전 추가:
> ```bash
> echo -n '값' | gcloud secrets versions add SK_AUTHORIZATION_{hspId} --project=dev-dfd-393200 --data-file=-
> ```

#### 상용 (prd-dfd)

```bash
# SK_AUTHORIZATION_{hspId}
echo -n 'Basic {상용_Basic_Auth_key_BASE64}' | \
  gcloud secrets create SK_AUTHORIZATION_{hspId} \
    --project=prd-dfd \
    --data-file=- \
    --replication-policy=automatic

# SK_SECRETKEY_{hspId}
echo -n '{상용_MCT_Auth_key}' | \
  gcloud secrets create SK_SECRETKEY_{hspId} \
    --project=prd-dfd \
    --data-file=- \
    --replication-policy=automatic
```

### Step 4: Cloud Run 환경변수에 보안비밀 연동

Secret Manager에 등록한 시크릿을 Cloud Run 서비스의 환경변수로 연결한다.

#### Cloud Run 서비스 정보

| 환경 | 서비스명 | 프로젝트 | 리전 |
|------|----------|----------|------|
| 개발 | `run-dev-dfd-hsp-api-skill` | `dev-dfd-393200` | `asia-northeast3` |
| 상용 | `run-prd-dfd-hsp-api-skill` | `prd-dfd` | `asia-northeast3` |

#### 개발

```bash
gcloud run services update run-dev-dfd-hsp-api-skill \
  --region=asia-northeast3 \
  --project=dev-dfd-393200 \
  --update-secrets="SK_AUTHORIZATION_{hspId}=SK_AUTHORIZATION_{hspId}:latest,SK_SECRETKEY_{hspId}=SK_SECRETKEY_{hspId}:latest"
```

#### 상용

```bash
gcloud run services update run-prd-dfd-hsp-api-skill \
  --region=asia-northeast3 \
  --project=prd-dfd \
  --update-secrets="SK_AUTHORIZATION_{hspId}=SK_AUTHORIZATION_{hspId}:latest,SK_SECRETKEY_{hspId}=SK_SECRETKEY_{hspId}:latest"
```

#### Cloud Run 콘솔 확인 URL

| 환경 | URL |
|------|-----|
| 개발 | `https://console.cloud.google.com/run/detail/asia-northeast3/run-dev-dfd-hsp-api-skill/revisions?project=dev-dfd-393200` |
| 상용 | `https://console.cloud.google.com/run/detail/asia-northeast3/run-prd-dfd-hsp-api-skill/revisions?project=prd-dfd` |

> **참고**: `--update-secrets`는 기존 환경변수/보안비밀을 유지하면서 새 시크릿만 추가한다. 서비스가 새 리비전으로 배포되므로, 콘솔에서 최신 리비전의 환경변수 탭에서 시크릿 연동을 확인한다.

### Secret Manager 콘솔 확인 URL

| 환경 | URL |
|------|-----|
| 개발 | `https://console.cloud.google.com/security/secret-manager/secrets?project=dev-dfd-393200` |
| 상용 | `https://console.cloud.google.com/security/secret-manager/secrets?project=prd-dfd` |

### Step 5: IntelliJ 환경변수 등록

Secret Manager / Cloud Run 환경변수 연동이 완료되면, 로컬 개발을 위해 IntelliJ의 Run/Debug Configuration에 환경변수를 등록한다.

#### 설정 방법

1. IntelliJ 상단 메뉴 → **Run** → **Edit Configurations...**
2. 사용 중인 Spring Boot 실행 설정 선택
3. **Environment variables** 필드에 아래 키-값 추가

| 환경변수 키 | 값 (개발 기준) |
|-------------|----------------|
| `SK_AUTHORIZATION_{hspId}` | `Basic {개발stg_Basic_Auth_key_BASE64}` |
| `SK_SECRETKEY_{hspId}` | `{개발stg_CT_Auth_key}` |

> **값은 Step 1에서 파싱한 개발stg 키를 사용한다.** `SK_AUTHORIZATION`은 `"Basic "` 접두사 포함, `SK_SECRETKEY`는 `CT_Auth_key` 값 그대로 입력한다.

### 최종 확인: H_90 응답 데이터 정합성 검증 (sms_yn / sms_phone_num)

연동 마무리 단계에서 **병원이 H_90(카드 상세 조회) 응답을 정책대로 보내는지** 중계서버 로그로 검증한다.
H_90 응답은 병원별 정책항목의 "알림 연락처" 정책과 연동되는 데이터다.

#### 검증 규칙

| sms_yn | sms_phone_num | 판정 |
|--------|---------------|------|
| `Y` | 값 있음 | ✅ 정상 |
| `Y` | 비어 있음 | ❌ 병원 오송신 — 수신번호 누락 |
| `N` | 비어 있음 | ✅ 정상 |
| `N` | **값 있음** | ❌ 병원 오송신 — 미사용인데 번호가 담겨 옴 |

- 특히 **알림 연락처 미사용 병원(`tel_use_type = DISABLED`)** 은 항상 `sms_yn=N` + `sms_phone_num` 빈 값이어야 한다. 위반 시 병원 측 인터페이스 수정 요청 대상이다.

#### 확인 방법 — grafana-log 스킬(중계서버 Loki 로그)

`grafana-log` 스킬로 해당 병원 job의 H_90 응답 로그를 조회해 `sms_yn`/`sms_phone_num` 값을 눈으로 대조한다.

```logql
{job="{병원job}", env="dev"} |~ "H_90" |~ "sms"
```

- 로그 라인 형식: `... GET API Response: H_90, {"succeed":"true", ..., "sms_yn":"N","sms_phone_num":"..."}`
- 위반 발견 시: 병원 담당자에게 **"sms_yn=N이면 sms_phone_num을 빈 값으로 보내야 한다"** 고 수정 요청하고, 수정 전까지는 케어챗 화면에 잘못된 번호가 노출될 수 있음을 사용자에게 알린다.

> 실제 사례 (2026-09-28): 대전선(41)·유성선(42)은 `tel_use_type=DISABLED`(알림 연락처 미사용)인데, dev 중계서버(`job="sunhospital"`) H_90 응답에 `"sms_yn":"N"` + `"sms_phone_num":"010...."`가 담겨 수신됨 → 병원 측 오송신으로 확인, 수정 요청 대상.

### 연동 완료 체크리스트

- [ ] `hspId` 확인
- [ ] `payment_hsp_mst` 테이블에 `submall_id`, `submall_business_num` 등록
- [ ] `payment_hsp_mst.hipass_use` 설정 (신규 연동 기본 `0`=미노출; 발화 테스트는 가맹만으로 가능, **운영 메뉴 노출은 오픈 시 `1`**)
- [ ] `stte_ccrc` 동의 헤더 등록 (병원명 확인)
- [ ] `stte_ccrc_cnte` 동의 항목 8건 등록 (개인정보 항목은 피그마 정책서 확인)
- [ ] `dtl_mst`(`CCRC_ITEM_MGMT`)에 `HIPASS_01` 등록 (⚠️ 누락 시 마이메뉴에 하이패스 동의항목 안 보임)
- [ ] `dtl_mst`(`HIPASS_GUIDE`) 하이패스 안내 사항 등록 (피그마 정책서에서 Bold/Medium 텍스트 추출)
- [ ] 개발 Secret Manager에 `SK_AUTHORIZATION_{hspId}`, `SK_SECRETKEY_{hspId}` 등록
- [ ] 상용 Secret Manager에 `SK_AUTHORIZATION_{hspId}`, `SK_SECRETKEY_{hspId}` 등록
- [ ] 개발 Cloud Run (`run-dev-dfd-hsp-api-skill`) 보안비밀 환경변수 연동
- [ ] 상용 Cloud Run (`run-prd-dfd-hsp-api-skill`) 보안비밀 환경변수 연동
- [ ] Cloud Run 콘솔에서 최신 리비전 환경변수 탭에서 시크릿 연동 확인
- [ ] IntelliJ Edit Configurations에 `SK_AUTHORIZATION_{hspId}`, `SK_SECRETKEY_{hspId}` 환경변수 등록
- [ ] **H_90 응답 정합성 검증** — 중계서버 로그(grafana-log)에서 `sms_yn`/`sms_phone_num` 대조 (`sms_yn=N`이면 `sms_phone_num` 빈 값, `Y`면 값 필수. 위반 시 병원에 수정 요청)

### 연동 완료 후 안내

모든 단계가 완료되면 사용자에게 아래 내용을 안내한다:

> 위 작업은 **통합 스킬 서버** 기준으로 등록되었습니다.
> - 개발: `run-dev-dfd-hsp-api-skill` (`dev-dfd-393200`, `asia-northeast3`)
> - 상용: `run-prd-dfd-hsp-api-skill` (`prd-dfd`, `asia-northeast3`)
>
> 해당 병원이 별도 서버(병원 전용 Cloud Run 서비스)를 사용하는 경우:
> 1. 해당 서버에도 동일하게 Secret Manager 보안비밀 환경변수 연동이 필요합니다.
> 2. `application-{병원프로필}.yml` 파일의 `hi-pass.sk-pay.redirect-url`에 해당 병원 스킬 서버 도메인을 지정해야 합니다.
>
> 예시:
> - 통합 서버: `https://karechat-skill-api-dev.kakaohealthcare.com/dfd/api/skpay/callback`
> - 병원 전용 서버: `https://karechat-hsp-{병원코드}-dev.kakaohealthcare.com/dfd/api/skpay/callback`
>
> 설정 위치: `src/main/resources/application-{병원프로필}-{env}.yml`
> ```yaml
> hi-pass:
>   sk-pay:
>     redirect-url: https://karechat-hsp-{병원코드}-{env}.kakaohealthcare.com/dfd/api/skpay/callback
> ```

## 로컬 테스트 가이드

로컬에서 11pay SDK 카드관리창을 실행하고 콜백을 로컬로 받아 테스트하는 방법이다.

### Step 1: redirect-url을 localhost로 변경

`src/main/resources/application-skill-dev.yml` 파일의 `hi-pass.sk-pay.redirect-url` 도메인을 localhost로 변경한다.

```yaml
hi-pass:
  sk-pay:
    redirect-url: http://localhost:8081/dfd/api/skpay/callback
```

> **⚠️ 이 변경은 절대 커밋하지 않는다.** 테스트 완료 후 반드시 원복한다.
> 원본: `https://karechat-skill-api-dev.kakaohealthcare.com/dfd/api/skpay/callback`

### Step 2: 로컬 서버 실행 후 크롬에서 SDK 호출

사용자에게 아래 정보를 요청한다:

| 항목 | 필수 | 설명 |
|------|------|------|
| `hspId` | Y | 병원 ID |
| `mpiKey` | Y | MPI 키 |
| `smsYn` | Y | SMS 수신 여부 (`Y` 또는 `N`) |
| `smsPhoneNum` | `smsYn=Y`일 때만 | 휴대전화번호 (예: `01012345678`) |
| `installmentMonth` | N | 할부 개월 수 (일시불이면 `0`, 할부 없으면 파라미터 자체를 생략) |

정보를 받으면 아래 패턴으로 URL을 생성하여 크롬 주소창에 붙여넣으라고 안내한다.

**smsYn=Y + 할부 있는 경우:**
```
http://localhost:8081/dfd/api/skpay/{hspId}/{mpiKey}?smsYn=Y&smsPhoneNum={전화번호}&installmentMonth={할부개월수}
```

**smsYn=Y + 일시불인 경우:**
```
http://localhost:8081/dfd/api/skpay/{hspId}/{mpiKey}?smsYn=Y&smsPhoneNum={전화번호}&installmentMonth=0
```

**smsYn=N인 경우:**
```
http://localhost:8081/dfd/api/skpay/{hspId}/{mpiKey}?smsYn=N
```

> `installmentMonth`는 일시불일 때 `0`을 넣고, 할부 자체가 없는 병원이면 파라미터를 생략한다.

### Step 3: 테스트 완료 후 원복

`application-skill-dev.yml`의 `redirect-url`을 원래 값으로 되돌린다. **커밋 전 반드시 확인한다.**

## FAQ

### Q. 해지를 했는데 11pay 카드 내역에 계속 노출돼요

하이패스 해지는 **병원에 등록된 자동결제 토큰만 만료**시키는 것이지, 11pay에 등록된 카드 자체를 삭제하는 게 아니다.

구조를 정리하면:
1. **11pay** = 간편결제 수단 (네이버페이, 카카오페이와 같은 역할). 여기에 카드를 등록한다.
2. **하이패스 등록** = 11pay에 등록된 카드를 병원 자동결제 수단으로 연동하고, 이때 결제 토큰이 발행된다.
3. **하이패스 해지** = 발행된 결제 토큰만 만료. 11pay 카드 내역은 그대로 유지된다.

따라서 해지 후에도 11pay 화면에 카드가 보이는 것은 정상이다.

### Q. 토큰 해지가 실패해요. 어떻게 확인해야 하나요?

하이패스 해지는 3단계로 진행된다. 어느 단계에서 실패했는지 로그를 확인해야 한다.

#### 해지 플로우 (`SkpayService.expireHiPass()`)

```
1. 코세스(Kocess) 소켓 통신 → 결제 토큰 만료 요청
2. 코세스 응답 확인
3. 병원 시스템에 해지 전달
```

#### 단계별 실패 원인

**1단계: 코세스 소켓 연결 실패**
- 증상: `ansCode = "9999"`, `skCode = "KOCESS 연결 실패"` 로그
- 원인: 코세스 서버 접속 불가 (host/port 설정 오류, 네트워크 차단, 코세스 서버 다운)
- 확인: `application-{병원프로필}-{env}.yml`의 `hi-pass.kocess.host`, `port` 설정 확인
- 참고: 소켓 타임아웃은 20초

**2단계: 코세스 응답 에러**
- `ansCode = "0000"` → 성공
- `skCode = "20002020"` 또는 `skMessage`에 `"존재하지않는토큰입니다"` → 이미 해지된 토큰. 사용자에게 "이미 해지된 카드에요" 응답
- 그 외 코드 → SK 결제 게이트웨이 오류. `skCode`와 `skMessage`를 로그에서 확인

**3단계: 병원 시스템 전달 실패**
- 코세스 해지는 성공했지만 병원 연동(`expireHiPass`)에서 실패
- 사용자에게 "병원 연결에 문제가 있어요. 원무 창구에서 해지해 주세요." + 병원 전화번호 응답

#### 로그 확인 및 재시도 방법

**1. GCP 콘솔에서 로그 확인**

사용자에게 환경(개발/상용)과 병원 ID를 물어본다. GCP Cloud Run 로그에서 직접 검색해줄 수도 있다. (`/gcp-cloudrun-log` 스킬 활용)

GCP 콘솔 로그 탐색기에서 아래 키워드로 검색:
```
Start of request SkPayRestController.expireHipassCard
```

검색 결과에서:
1. 중첩된 필드 펼치기
2. 복사 → **JSON으로 복사**
3. `hipassTokenExpireReq` 객체의 값을 추출

**2. curl로 해지 재시도**

추출한 값으로 아래 curl을 구성하여 **Postman에 붙여넣기** 후 실행한다:

```bash
curl --location --globoff 'https://{스킬서버도메인}/dfd/api/skpay/expire/{hspId}/{mpiKey}' \
--header 'Content-Type: application/json' \
--data '{
    "hspId": {hspId},
    "mpiKey": "{mpiKey}",
    "hipassId": "{hipassId}",
    "paymentToken": "{paymentToken}",
    "applyStartDate": "{applyStartDate}"
}'
```

스킬서버 도메인:
- 개발 (통합): `karechat-skill-api-dev.kakaohealthcare.com`
- 상용 (통합): `karechat-skill-api.kakaohealthcare.com`
- 병원 전용 서버가 있는 경우: `karechat-hsp-{병원코드}-{env}.kakaohealthcare.com`

### Q. 코세스/11pay에서는 이미 해지됐는데 병원에만 데이터가 남아있어요

코세스 토큰은 이미 만료되었지만 병원 시스템에 해지 전달이 실패한 케이스다.
로컬에서 코세스 통신을 건너뛰고 **병원에만 해지 요청**을 보내면 된다.

#### 방법: 코세스 호출 주석 처리 후 로컬에서 실행

`SkpayService.java`의 `expireHiPass()` 메서드 (line 270~)에서 코세스 관련 코드를 주석 처리한다:

```java
public HipassExpireRes expireHiPass(HipassTokenExpireReq hipassTokenExpireReq) throws Exception {
    try {
      if (StringUtils.isBlank(hipassTokenExpireReq.getPtNo())) {
        CommonConvertRequest convertRequest = new CommonConvertRequest(currentInterfaceSeverHspCd(), currentMpiKey());
        PtInfo ptInfo = hspInterfaceCommonService(currentHspId()).getPatientInfo(currentBaseUrl(), currentHspId(), convertRequest);
        hipassTokenExpireReq.setPtNo(ptInfo.getPtNo());
      }

      // ⬇️ 아래 코세스 통신 부분을 주석 처리
      // KocessTokenExpireRes kocessTokenExpireRes = this.expireHipassToKocess(hipassTokenExpireReq);
      // if (kocessTokenExpireRes.alreadyExpiredToken())
      //   return new HipassExpireRes(Result.FAIL.getCode(), "이미 해지된 카드에요.");
      // if (!kocessTokenExpireRes.resultSuccess()) {
      //   return this.expireFailed(kocessTokenExpireRes);
      // }

      // 병원에 해지 전달 (이 부분만 실행)
      HipassExpireRes expireRes = this.expireHspRes(hipassTokenExpireReq);
      this.publishStatisticsEvent("EXPIRE");
      return expireRes;
    } catch (Exception e) {
      return new HipassExpireRes(Result.FAIL.getCode(), "하이패스 해지에 실패했어요.\n" + "원무 창구에서 해지해 주세요.\n" + currentHspMst().getRprnTelNo());
    }
  }
```

파일 위치: `src/.../v2/application/hipass/SkpayService.java`

#### 실행 순서

1. 위 코드 주석 처리
2. 로컬 서버 실행
3. FAQ 2번의 curl 템플릿으로 Postman에서 해지 요청 실행
4. 병원 응답 확인 후 **주석 반드시 원복** (커밋 금지)

### Q. 토큰 해지가 에러 응답으로 실패될 때 이메일 어떻게 보내야 하나요?

코세스/11pay 측 장애로 토큰 해지가 지속 실패할 경우, 아래 담당자에게 이메일로 문의한다.

#### 수신자 목록

```
받는사람/참조:
- 박소영 <11st.sy.park@partner.sk.com>
- 유원상(Wonsang Yoo) <yoows@sk.com>
- ksk3197@koces.com
- 박종휘 <pjh6755@koces.com>
- 백한별(Hanbyeol Baek) <hbbaek@sk.com>
- 이옥재(OckJae Lee) <ockjae.lee@sk.com>
```

#### 이메일 작성 시 필수 포함 사항

- **가맹 ID** (예: `hp-snubh`) — 반드시 명시
- **환경** (스테이징 / 운영) — 반드시 명시
- 대상 거래 정보: `apprVer`, `svcType`, `trdType`
- 발생 기간 (KST)
- 발생 건수
- 건별 내역: 요청시각, 응답코드, 환자식별번호, 카드 토큰

#### 이메일 템플릿 예시

```
제목: [하이패스] 토큰 해지 에러 문의 - {가맹ID} ({환경})

안녕하세요 카카오헬스케어 {발신자명}입니다.

현재 {병원명}({가맹ID}) {환경} 채널에서 하이패스 결제수단 테스트 중에,
{발생기간} 요청한 결제수단 해지가 "{에러메시지}" 라는 메시지로 실패되고 있어 문의드립니다.

  - 대상 거래   : 토큰 해지 (apprVer=A1 / svcType=SK / trdType=SD)
  - 대상 환경   : 11pay 및 코세스 {환경}환경
  - 발생 기간   : {시작시각} ~ {종료시각} (KST)
  - 발생 건수   : 총 {N}건 (해당 기간 내 토큰 해지 시도 전량 실패)


■ 발생 내역 요약
  ------------------------------------------------------------------------------------
  No  요청시각(KST)           응답코드    환자식별번호    카드 토큰(payment_token)
  ------------------------------------------------------------------------------------
  1   {시각}                  {코드}      {환자번호}      {토큰}
  2   ...
  ------------------------------------------------------------------------------------

  상기 기간 동안 토큰 해지 요청에 대해 응답코드 {코드}({에러설명})이 지속 반환되고 있습니다.
  확인 부탁드립니다.

감사합니다.
```

> **내역 데이터 수집**: GCP 콘솔 로그에서 `Start of request SkPayRestController.expireHipassCard`로 검색하여 해당 기간의 요청/응답을 추출한다. 사용자에게 환경과 병원 ID를 물어보고 `/gcp-cloudrun-log` 스킬로 직접 조회해줄 수도 있다.

### Q. 해지 실패 사유가 "VAN과관계되지않은서브몰에대한요청입니다." 일 때

이 에러는 **11pay 가맹 등록이 아직 완료되지 않은 상태**에서 발생한다. 토큰 등록은 되지만 코세스 쪽 해지 전문에서 거절되는 케이스다.

#### 조치

11pay 담당 매니저에게 직접 문의한다:
- **유원상(Wonsang Yoo)** <yoows@sk.com>
- **박소영** <11st.sy.park@partner.sk.com>

#### 이메일 템플릿

```
제목: [하이패스] 가맹 등록 확인 요청 - {가맹ID} ({환경})

안녕하세요 카카오헬스케어 {발신자명}입니다.

금일 {병원명}({가맹ID}) 가맹으로 11Pay {환경}, 코세스 {환경}환경으로
토큰 등록 및 해지를 진행하였는데, 토큰 등록은 정상 발급되나
코세스에 토큰 해지 전문 요청 시
"SKP 기관인증거절" 해지사유: "VAN과관계되지않은서브몰에대한요청입니다."
응답으로 토큰 해지가 실패되었습니다.

아직 가맹 등록 절차가 마무리되지 않은 것 같아
11pay 쪽에서 확인이 필요할 것 같은데 이 부분 확인 후 처리 부탁드리겠습니다.

감사합니다.
```

> **가맹 ID** (예: `hp-snubh`)와 **환경** (스테이징/운영)은 반드시 명시한다.

### Q. 특정 병원에 등록된 토큰을 모두 삭제하고 싶어요

병원 요청 등으로 11pay에 등록된 특정 가맹의 **모든 결제 토큰을 일괄 삭제**해야 할 때, 11pay 담당자에게 이메일로 요청한다.

#### 수신자

- **유원상(Wonsang Yoo)** <yoows@sk.com>
- **박소영** <11st.sy.park@partner.sk.com>

#### 이메일 템플릿

```
제목: [하이패스] 결제 토큰 일괄 삭제 요청 - {가맹ID} ({환경})

안녕하세요. 카카오헬스케어 {발신자명}입니다.

병원 요청사항으로 11pay {환경} 환경에 등록된
{병원명}({가맹ID}) 가맹의 모든 결제 토큰을 전부 삭제 부탁드리려고 합니다.
일괄 삭제 후에 회신 부탁드리겠습니다.

감사합니다.
```

> **가맹 ID** (예: `hp-snubh`)와 **환경** (stg/운영)은 반드시 명시한다.

## 변경 이력

- 2026-09-21: DB 접근 방식을 mysql CLI(`/opt/homebrew/opt/mysql-client/bin/mysql`) + `~/.zshrc` 환경변수(`SKILL_DB_PASSWORD_DEV`/`SKILL_DB_PASSWORD_PROD`)에서 **`db-query` 스킬(pymysql + 스킬 로컬 `.env`) 경유**로 교체. 이 머신에는 mysql-client가 설치돼 있지 않고 zshrc에 해당 환경변수도 없으며, 기존 DB 스킬(db-query/hospital-admission-setup)이 전부 pymysql+`.env`를 쓰는 실제 환경에 맞춤. dev는 `--allow-write`(미리보기→승인→실행), prod 쓰기는 `db-query`가 차단하므로 SQL 생성 후 사용자 직접 실행으로 정리. (사전 준비 섹션 + Step 2)
- 2026-09-28: 연동 최종 확인 절차에 **H_90 응답 sms_yn/sms_phone_num 정합성 검증** 추가. `sms_yn=N`이면 `sms_phone_num`이 비어 있어야 하고 `Y`면 값이 있어야 한다는 규칙 + grafana-log(중계서버 Loki) 확인 방법 + 체크리스트 항목 추가. 대전선(41)·유성선(42) dev에서 `sms_yn=N`인데 번호가 담겨 오는 병원 오송신 사례 확인이 계기.
