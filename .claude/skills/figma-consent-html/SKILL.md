---
name: figma-consent-html
description: Figma Desktop MCP로 입원동의서 UI를 분석하고, 사용자에게 백엔드 코드 정보를 질문한 뒤 mobile_template + pdf_template HTML을 생성한다. 트리거: "입원동의서 HTML 변환", "consent template 생성", "서류 HTML 만들어줘", "동의서 파일 만들어줘", "HTML 퍼블리싱"
---

# 입원동의서 HTML 템플릿 변환 스킬

## 개요

Figma에서 읽을 수 있는 것 vs 사용자에게 물어봐야 하는 것이 명확히 구분된다.

| 정보 출처 | 내용 |
|----------|------|
| **Figma** | 레이아웃, 약관 텍스트, 섹션 구조, 서명 영역 수/위치, 토글 항목 수/텍스트, 동적 필드 위치 |
| **사용자에게 질문** | 병원 CSS 클래스, content_code, 각 토글 항목의 content detail code, 조건부 섹션 코드 |

---

## 워크플로우

### Step 1: Figma 디자인 수집

Figma Desktop MCP로 현재 선택된 노드를 읽는다.

```
mcp__figma-desktop__get_screenshot()      → 전체 레이아웃 시각 확인
mcp__figma-desktop__get_design_context()  → 텍스트 내용 추출
```

스크린샷으로 파악할 것:
- 섹션 수와 각 섹션 제목
- 토글 버튼 항목 수와 텍스트 (동의/비동의 or 예/아니오)
- 서명 영역 수와 종류 (환자 서명 / 보호자 서명 / 조건부 서명)
- 조건부로 노출되는 섹션 (상급병실, 비급여 등)
- PDF 레이아웃의 테이블 구조, 수신인 텍스트, 로고 영역

---

### Step 2: 사용자에게 필수 정보 질문

Figma만으로는 알 수 없는 백엔드 코드를 질문한다.  
**모든 항목이 확정될 때까지 HTML 생성하지 않는다.**

#### 질문 1 — 병원 기본 정보

```
다음 정보를 알려주세요:
1. 병원명 (예: 한양대병원 서울)
2. hsp_id (예: 5)
3. content_code (예: P001)
4. PDF content-wrap 클래스 (아래 중 선택):
   - hallym       → 한림대병원 계열
   - hyumc        → 한양대병원 서울
   - hyumc-guri   → 한양대병원 구리
   - dsmc         → 계명대병원
```

#### 질문 2 — 토글/선택 항목의 content detail code

Figma에서 파악한 토글 항목을 나열하고 각 코드를 물어본다.

예시:
```
Figma에서 다음 [N]개의 동의 항목을 확인했습니다:
  1. "입원사실 정보공개 동의 여부" (동의/비동의)
  2. "주차요금에 대한 설명을 들었습니다" (동의/비동의)
  3. "건강보험 부정수급 방지 본인확인" (예/아니오)

각 항목의 content detail code를 알려주세요. (예: AP01-001, AP01-002, AP01-003)
비동의를 허용하지 않는 항목이 있으면 함께 알려주세요. (data-disagree-not-allowed)
```

#### 질문 3 — 조건부 섹션 (있는 경우만)

```
"상급병실사용확인서", "비급여행위 사용신청서" 등 조건부로 노출되는 섹션이 보입니다.
해당 섹션을 활성화하는 content detail code를 알려주세요.
(data-bind-required-code 값으로 사용됩니다. 예: AP01-004)
```

#### 질문 4 — 서명이 2개 이상인 경우

```
서명 영역이 [N]개 확인됩니다:
  - 메인 서명 (sign-all): 환자 서명 → 자동 처리
  - 보호자 서명 (caregiver-sign): 있으면 자동 처리
  - 조건부 서명: 몇 번째 서명이 어떤 조건(code)에 연결되나요?
    (예: 상급병실 섹션 활성 시 sign-004 / AP01-004)
```

---

### Step 3: HTML 생성 규칙

#### 3-1. 동적 데이터 name 속성 매핑표

Figma의 라벨 텍스트를 보고 아래 표를 참조해 `name` 속성을 결정한다.

**환자 정보**
| Figma 라벨 | name 속성 | 비고 |
|-----------|-----------|------|
| 환자성명, 환자명 | `usrNm` | |
| 등록번호 | `ptNo` | |
| 생년월일 | `usrBirthday` | |
| 나이 | `usrAge` | |
| 진료과 | `deptNm` | |
| 병동 | `hsptlzWard` | |
| 병실, 호실 | `hsptlzRoom` | |
| 입원일, 입원(예정)일 | `hsptlzDate` | `class="data-content"` 추가 |
| 담당의사 | `medrNm` | |
| 보험유형 | `insuranceType` | |
| 우편번호 | `postNo` | |
| 기본주소 | `bscAddr` | |
| 상세주소 | `dtlAddr` | |
| 전화번호 (복수) | `phoneNumberList` | `class="data-content"` 추가, 배열 |
| 상급병실 등급 | `roomGrade` | 조건부 섹션 내부 |
| 상급병실료 | `advancedRoomFee` | 조건부 섹션 내부, `class="data-content"` |
| 년 | `YYYY` | |
| 월 | `MM` | |
| 일 | `DD` | |
| 날짜 전체 (약정일 등) | `YYYYMMDD` | |

**보호자 정보**
| Figma 라벨 | name 속성 |
|-----------|-----------|
| 보호자 성명 | `caregiverName` |
| 보호자 생년월일 | `caregiverBirthDate` |
| 보호자 성별 | `caregiverSex` |
| 보호자 관계 | `caregiverRelationship` |
| 보호자 주소 | `caregiverAddress` |
| 보호자 상세주소 | `caregiverDetailAddress` |
| 보호자 실거주 주소 | `caregiverAcutalAddress` | ← 오타 그대로 유지 (시스템 키) |
| 보호자 전화번호 (복수) | `caregiverPhoneNumberList` | 배열 |

**서명**
| 서명 종류 | name 속성 | 추가 속성 |
|---------|-----------|---------|
| 환자 서명 (메인) | `sign-all` | `data-type="sign" data-error="Y" data-value="" data-status="N"` |
| 보호자 서명 | `caregiver-sign` | + `data-caregiver-sign="Y"` |
| 조건부 서명 N번째 | `sign-{N}` | + `data-code="{contentDetailCode}"` |

#### 3-2. mobile_template 골격

```html
<div class="mobile-temp-container btn-fixed">
  <div class="content-wrap">
    <div class="page-title-wrap">
      <h3 class="page-title">{서류명}</h3>
      <span class="page-desc">아래 내용을 읽고 동의해 주세요.</span>
    </div>

    <!-- 서명이 2개 이상일 때만 추가 -->
    <div class="btn-agree-all">
      <div>
        <span class="chk-type-01"></span>
        <span class="text">모두 동의하기</span>
      </div>
    </div>

    <div class="box-item-wrap">

      <!-- 섹션 반복 -->
      <div class="box-item">
        <h4 class="sub-title">{섹션명}</h4>
        <ul class="list-02">
          <li>
            <span class="num">1.</span>
            <p>{약관 텍스트}</p>
          </li>
          <!-- 토글 항목 (li 안에 바로) -->
          <li class="in-box-btn">
            <div
              class="box-btn-area-error"
              name="{contentDetailCode}"
              data-type="toggle"
              data-error="Y"
              data-value=""
              data-status=""
              data-disagree-not-allowed="Y"  <!-- 비동의 불허 시만 -->
            >
              <div class="box-btn-area">
                <button class="" data-value="동의" data-status="Y">
                  <span class="chk-type-01"></span>
                  <span class="text">동의</span>
                </button>
                <button class="" data-value="비동의" data-status="N">
                  <span class="chk-type-01"></span>
                  <span class="text">비동의</span>
                </button>
              </div>
              <div class="box-btn-area-error-text">
                <span>항목을 선택해 주세요.</span>
              </div>
            </div>
          </li>
        </ul>

        <!-- 섹션 하단 동의 문구 (있을 경우) -->
        <div class="agree-desc">
          <span>{동의 확인 문구}</span>
        </div>

        <!-- 환자 서명 -->
        <div class="sign-wrap" name="sign-all" data-type="sign"
             data-error="Y" data-value="" data-status="N">
          <div class="sign-requirement sign-requirement-error">
            <span class="sign-guide">환자 서명</span>
            <span class="sign-requirement-text">환자 서명이 필요해요.</span>
            <span class="patient-txt"></span>
            <button class="sign-preview"><img /></button>
            <button class="btn-sign"><span>서명하기</span></button>
            <button class="btn-clear"><span>삭제</span></button>
          </div>
          <div class="sign-requirement-error-text">
            <span>서명을 입력해 주세요.</span>
          </div>
        </div>
      </div>

      <!-- 조건부 섹션 (data-bind-required-code로 감쌈) -->
      <div class="box-item box-list" data-bind-required-code="{contentDetailCode}">
        <!-- 섹션 내용 -->
        <!-- 조건부 서명 -->
        <div class="sign-wrap" name="sign-{N}" data-code="{contentDetailCode}"
             data-type="sign" data-error="Y" data-value="" data-status="N">
          <!-- ... -->
        </div>
      </div>

      <!-- 보호자 정보 섹션 -->
      <div class="box-item">
        <h2 class="sub-title">보호자</h2>
        <ul class="list-info-01">
          <li>
            <span class="tit">성명</span>
            <span class="con"><span name="caregiverName"></span></span>
          </li>
          <!-- 기타 보호자 필드 -->
        </ul>
        <!-- 보호자 서명 -->
        <div class="sign-wrap" name="caregiver-sign" data-type="sign"
             data-error="Y" data-value="" data-status="N" data-caregiver-sign="Y">
          <!-- ... -->
        </div>
      </div>

    </div>
  </div>
  <OneBtnFooter text="아래로 스크롤" />
</div>
```

#### 3-3. pdf_template 골격

```html
<div class="pdf-temp-container">
  <div class="content-wrap {병원CSS클래스} form-{N}">
    <!-- form-N은 서류 복잡도에 따라 결정. 단순하면 생략, 복잡하면 form-1 -->
    <div class="pdf-page">

      <!-- 헤더 -->
      <div class="head-area">
        <h1>({체크마크용 span})  {서류명}</h1>
        <!-- 또는 단순: <h1>{서류명}</h1> -->
      </div>

      <!-- 환자 인적사항 테이블 -->
      <div class="info-box-area">
        <div class="sub-tit align-between">
          <span>◈ 환자 인적사항</span>
          <span>입원(예정)일 : <span class="data-content" name="hsptlzDate"></span></span>
        </div>
        <div class="table-area">
          <table><!-- 등록번호/진료과/병실/환자명/생년월일/주소/전화번호 --></table>
        </div>
      </div>

      <!-- 약정/동의 내용 -->
      <div class="info-box-area">
        <div class="sub-tit"><span>◈ {섹션명}</span></div>
        <ul class="list-02">
          <li>
            <span class="num">1.</span>
            <span class="con">{약관 텍스트}</span>
          </li>
          <!-- 인라인 토글 (PDF 스타일) -->
          <li>
            <span class="num">N.</span>
            <span class="con chk">
              <span>{항목 텍스트} :&nbsp;</span>
              <div class="box-item">
                <div class="box-btn-area" name="{contentDetailCode}">
                  <div>
                    <button data-status="Y">
                      <span class="chk-type-01"></span>
                      <span class="text">동의</span>
                    </button>
                    <span>/</span>
                    <button data-status="N">
                      <span class="chk-type-01"></span>
                      <span class="text">비동의</span>
                    </button>
                  </div>
                </div>
              </div>
            </span>
          </li>
        </ul>
      </div>

      <!-- 서명/날짜 영역 -->
      <div class="info-box-area">
        <div class="info-list">
          <ul style="justify-content: flex-end">
            <li style="flex: unset; margin-right: 20px">
              <span class="tit">약정일 : </span>
              <span name="YYYYMMDD"></span>
            </li>
            <li style="flex: unset">
              <span class="tit">약정인(환자/대리인) : </span>
              <span name="usrNm"></span>
            </li>
            <li style="flex: unset">
              <span class="tit" name="sign-all">(날인 또는 서명)</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- 조건부 섹션 -->
      <div data-bind-required-code="{contentDetailCode}">
        <!-- 조건부 내용 -->
      </div>

      <!-- 수신인 (병원별 상이) -->
      <div class="title-receiver-wrap">
        <p class="text">{병원 풀네임} 귀하</p>
      </div>

    </div>
  </div>
</div>
```

---

### Step 4: 출력 파일 저장

```
경로: .../HsptlzForm/MobileForm/ui/templates/{병원코드}.js

export const {서류명}_{병원약칭}_mobile = `...`;
export const {서류명}_{병원약칭}_pdf = `...`;
```

**파일명 규칙**
| 병원 (hsp_id) | 파일명 |
|--------------|--------|
| 한림대병원 춘천 (15) | `hallymChuncheon.js` |
| 한림대병원 평촌 | `hallymPyeongchon.js` |
| 한양대병원 서울 (5) | `hyumcSeoul.js` |
| 한양대병원 구리 (6) | `hyumcGuri.js` |
| 계명대병원 (13) | `dsmc.js` |

---

## § 5. 레퍼런스 예시

> 각 예시는 실제 생성 완료된 HTML에서 발췌한 핵심 패턴이다.
> 새 병원의 HTML을 생성할 때 같은 content_code 유형의 예시를 참조한다.

---

### § 5-1. 입원약정서 (한림대춘천성심병원) — AP01, 토글 4개

**서류 특성**
- content_code: `AP01`
- detail codes: AP01-001 (입원사실 정보공개 / 동의·비동의), AP01-002 (주차요금 / 동의·비동의), AP01-003 (건강보험 본인확인 / 예·아니오), AP01-004 (상급병실 조건부 섹션 trigger)
- 서명: sign-all (환자) + caregiver-sign (보호자) + 조건부 sign (AP01-004)
- CSS: `content-wrap hallym form-1`
- 파일: `templates/hallymChuncheon.js`

**mobile_template 핵심 패턴**
```html
<!-- 토글 (동의/비동의) -->
<li class="in-box-btn">
  <div class="box-btn-area-error" name="AP01-001" data-type="toggle"
       data-error="Y" data-value="N" data-disagree-not-allowed="Y" data-status="">
    <div class="box-btn-area">
      <button class="" data-value="동의" data-status="Y">
        <span class="chk-type-01"></span><span class="text">동의</span>
      </button>
      <button class="" data-value="비동의" data-status="N">
        <span class="chk-type-01"></span><span class="text">비동의</span>
      </button>
    </div>
    <div class="box-btn-area-error-text"><span>항목을 선택해 주세요.</span></div>
  </div>
</li>

<!-- 토글 (예/아니오) — AP01-003 -->
<button class="" data-value="예" data-status="Y">...</button>
<button class="" data-value="아니오" data-status="N">...</button>

<!-- 환자 서명 -->
<div class="sign-wrap" name="sign-all" data-type="sign" data-error="Y" data-value="" data-status="N">
  <div class="sign-requirement sign-requirement-error">
    <span class="sign-guide">환자 서명</span>
    <span class="sign-requirement-text">환자 서명이 필요해요.</span>
    <span class="patient-txt"></span>
    <button class="sign-preview"><img /></button>
    <button class="btn-sign"><span>서명하기</span></button>
    <button class="btn-clear"><span>삭제</span></button>
  </div>
  <div class="sign-requirement-error-text"><span>서명을 입력해 주세요.</span></div>
</div>

<!-- 보호자 서명 -->
<div class="sign-wrap" name="caregiver-sign" data-type="sign"
     data-error="Y" data-value="" data-status="N" data-caregiver-sign="Y">...</div>

<!-- 조건부 섹션 (AP01-004 선택 시 노출) -->
<div class="box-item box-list" data-bind-required-code="AP01-004">
  <h4 class="sub-title">상급병실사용확인서</h4>
  ...
</div>
```

**pdf_template 핵심 패턴**
```html
<div class="content-wrap hallym form-1">
  <div class="head-area"><h1>(<span></span>)입원약정서</h1></div>
  <!-- 인적사항 테이블 -->
  <table>
    <tr><th>등록번호</th><td><span name="ptNo"></span></td>
        <th>진료과</th><td><span name="deptNm"></span></td>
        <th>호실</th><td><span name="hsptlzRoom"></span></td></tr>
    <tr><th>환자명</th><td><span name="usrNm"></span></td>
        <th>생년월일</th><td><span name="usrBirthday"></span></td>
        ...
  </table>
  <!-- PDF 토글 (인라인) -->
  <li><span class="num">9.</span>
    <span class="con chk">
      <span>입원사실 정보공개 동의 여부 :&nbsp;</span>
      <div class="box-item">
        <div class="box-btn-area" name="AP01-001">
          <div>
            <button data-status="Y"><span class="chk-type-01"></span><span class="text">동의</span></button>
            <span>/</span>
            <button data-status="N"><span class="chk-type-01"></span><span class="text">비동의</span></button>
          </div>
        </div>
      </div>
    </span>
  </li>
  <!-- 보호자 서명 (PDF) -->
  <span class="tit" name="caregiver-sign" style="position: relative">(날인 또는 서명)</span>
  <!-- 조건부 섹션 (PDF) -->
  <div class="box-line" data-bind-required-code="AP01-004">...</div>
</div>
```

---

### § 5-2. 입원약정서 (계명대학교 동산병원) — HSPTLZ-001, 토글 3개

**서류 특성**
- content_code: `HSPTLZ-001`
- detail codes: 3개 (ETC_TYPE 동의여부 — 사용자가 코드 제공)
- 서명: sign-all + caregiver-sign
- CSS: `content-wrap dsmc`
- Figma nodeId: `14104:498505`

**mobile_template 핵심 패턴**
```html
<!-- 토글 (동의/비동의 방식 — 계명대 스타일) -->
<li class="in-box-btn">
  <div class="box-btn-area-error" name="{HSPTLZ-001-001}" data-type="toggle"
       data-error="Y" data-value="" data-status="">
    <div class="box-btn-area">
      <button class="" data-value="동의" data-status="Y">
        <span class="chk-type-01"></span><span class="text">동의</span>
      </button>
      <button class="" data-value="비동의" data-status="N">
        <span class="chk-type-01"></span><span class="text">비동의</span>
      </button>
    </div>
    <div class="box-btn-area-error-text"><span>항목을 선택해 주세요.</span></div>
  </div>
</li>

<!-- 신분증 확인 섹션 — 계명대 특유 섹션 -->
<div class="box-item">
  <h4 class="sub-title">신분증 확인</h4>
  ...
</div>
```

**pdf_template 핵심 패턴**
```html
<div class="content-wrap dsmc">
  <!-- form 클래스 없음 (단순 레이아웃) -->
  <div class="head-area"><h1>입원약정서</h1></div>
  ...
  <!-- 수신인 -->
  <div class="title-receiver-wrap">
    <p class="text">계명대학교 동산병원장 귀하</p>
  </div>
</div>
```

---

### § 5-3. 입원약정서 (한양대학교구리병원) — P001, 토글 1개

**서류 특성**
- content_code: `P001`
- detail codes: P001-001 (사생활 보호 신청 / 동의함·동의 안함)
- 서명: sign-all + caregiver-sign (보호자가 위 내용을 확인하였음 서명)
- CSS: `content-wrap hyumc-guri form-1`
- Figma nodeId: `16580:49502`

**mobile_template 핵심 패턴**
```html
<!-- 사생활 보호 신청 토글 — 버튼 텍스트가 "동의함"/"동의 안함" -->
<li class="in-box-btn">
  <div class="box-btn-area-error" name="P001-001" data-type="toggle"
       data-error="Y" data-value="" data-status="">
    <div class="box-btn-area">
      <button class="" data-value="동의함" data-status="Y">
        <span class="chk-type-01"></span><span class="text">동의함</span>
      </button>
      <button class="" data-value="동의 안함" data-status="N">
        <span class="chk-type-01"></span><span class="text">동의 안함</span>
      </button>
    </div>
    <div class="box-btn-area-error-text"><span>항목을 선택해 주세요.</span></div>
  </div>
</li>
```

> ⚠️ 한양대구리 P001은 버튼 텍스트가 **"동의함"/"동의 안함"**이다 (`data-value`도 동일하게 설정).

**pdf_template 핵심 패턴**
```html
<div class="content-wrap hyumc-guri form-1">
  ...
  <!-- 수신인 -->
  <div class="title-receiver-wrap">
    <p class="text">입원전담전문의 기관 한양대학교 병원장 귀하</p>
  </div>
</div>
```

---

### § 5-4. 입원약정서 (한양대학교병원 서울) — P001, 토글 없음

**서류 특성**
- content_code: `P001`
- detail codes: 없음 (DB 기준 hsptlz_cnte_form_dtl 레코드 0건)
- 서명: sign-all + caregiver-sign
- CSS: `content-wrap hyumc form-1`
- Figma nodeId: `16575:49186`

**mobile_template 핵심 패턴**
```html
<!-- 토글 없음 — btn-agree-all도 생략 가능 -->
<div class="mobile-temp-container btn-fixed">
  <div class="content-wrap">
    <div class="page-title-wrap">
      <h3 class="page-title">입원약정서</h3>
      <span class="page-desc">아래 내용을 읽고 동의해 주세요.</span>
    </div>
    <div class="box-item-wrap">
      <div class="box-item">
        <ul class="list-02">
          <!-- 항목 1~10, 토글 없음 -->
        </ul>
      </div>
      <!-- 환자 서명 -->
      <div class="sign-wrap" name="sign-all" ...>...</div>
      <!-- 보호자 서명 -->
      <div class="sign-wrap" name="caregiver-sign" ...>...</div>
    </div>
  </div>
</div>
```

**pdf_template 핵심 패턴**
```html
<div class="content-wrap hyumc form-1">...</div>
```

> ⚠️ DB에 한양대서울(hsp_id=5) P001의 `css_class`가 `hyumc-guri`로 잘못 입력된 버그가 있음. 실제 생성 시 반드시 `hyumc` 사용.

---

### § 5-5. 개인정보 수집·이용·제공 동의서 (한양대학교병원 서울) — P017, 토글 5개

**서류 특성**
- content_code: `P017`
- detail codes: 5개 (가~마 항목별 — 사용자가 코드 제공)
- 서명: sign-all (환자) + caregiver-sign (보호자)
- CSS: `content-wrap hyumc`
- Figma nodeId: `14104:499355`

**mobile_template 핵심 패턴**
```html
<!-- 가~마 각 섹션마다 토글 -->
<div class="box-item">
  <h4 class="sub-title">가. 개인정보 수집·이용 및 제3자 제공(필수항목)</h4>
  ...
  <li class="in-box-btn">
    <div class="box-btn-area-error" name="{P017-001}" data-type="toggle" ...>
      <div class="box-btn-area">
        <button class="" data-value="동의함" data-status="Y">
          <span class="chk-type-01"></span><span class="text">동의함</span>
        </button>
        <button class="" data-value="동의 안함" data-status="N">
          <span class="chk-type-01"></span><span class="text">동의 안함</span>
        </button>
      </div>
      ...
    </div>
  </li>
</div>
<!-- 총 5개 섹션 반복 -->
```

> ⚠️ P017 토글도 버튼 텍스트가 **"동의함"/"동의 안함"**이다.

---

| 병원 (hsp_id) | mobile content-wrap | pdf content-wrap | form 클래스 |
|--------------|---------------------|------------------|------------|
| 한림춘천 (15) | (없음) | `hallym` | `form-1`, `form-2` (서류별) |
| 한양대서울 (5) | (없음) | `hyumc` | `form-1` (긴 서류) |
| 한양대구리 (6) | (없음) | `hyumc-guri` | `form-1` (긴 서류) |
| 계명대 (13) | (없음) | `dsmc` | (없음) |

> ⚠️ 주의: 한양대서울(hsp_id=5) P001(입원약정서) DB에 `hyumc-guri` 오기입 버그 있음. 신규 생성 시 반드시 `hyumc` 사용.

---

## 체크리스트 (생성 후 검증)

- [ ] `name` 속성이 위 매핑표와 일치하는가
- [ ] 토글 항목의 `name`이 사용자 제공 contentDetailCode와 일치하는가
- [ ] `data-disagree-not-allowed="Y"` 항목이 올바르게 적용되었는가
- [ ] 조건부 섹션의 `data-bind-required-code`가 올바른 code와 연결되었는가
- [ ] pdf_template의 `content-wrap {병원CSS클래스}` 클래스가 올바른가
- [ ] 보호자 서명에 `data-caregiver-sign="Y"` 있는가
- [ ] `caregiverAcutalAddress` (오타) 그대로 사용했는가

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-06-09 | § 5. 레퍼런스 예시 추가 — 한림춘천 AP01 / 계명대 HSPTLZ-001 / 한양대구리·서울 P001 / 한양대서울 P017 |
| 2026-06-09 | 변경 이력 섹션 추가 (모든 스킬 공통 적용) |
