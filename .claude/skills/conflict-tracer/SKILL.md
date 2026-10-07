---
name: conflict-tracer
description: |
  머지/리베이스 충돌 시 "어떤 feature 브랜치와 충돌났는지"를 추적해 리포트하는 글로벌 스킬.
  충돌을 직접 해결하지 않는다(탐지·추적·리포트 전용). 진행 중인 머지가 develop/main 위에 있으면
  git merge --abort로 중단시켜 팀 룰(개발/운영 브랜치에서 직접 해결 금지)을 지킨다.

  다음 상황에서 사용:
  - "충돌 났어", "conflict 확인", "merge conflict", "어느 브랜치랑 충돌났어?"
  - PR에 conflict가 떠서 원인 브랜치를 알고 싶을 때
  - "/conflict-tracer"
---

# conflict-tracer

머지 충돌의 **상대편 코드가 어느 feature 브랜치에서 왔는지**를 추적해 리포트한다.
팀 룰(충돌은 feature 브랜치끼리, develop/main에서 직접 해결 금지)에 따라 동작한다.

> 상세 팀 룰: `~/.claude/CLAUDE.md`의 "머지 충돌 해결 전략" 참고.

## 🚫 이 스킬이 하지 않는 것 (중요)
- **충돌 해결을 하지 않는다.** 충돌 마커(`<<<<<<<`/`=======`/`>>>>>>>`) 편집, ours/theirs 선택, 해결본 저장, `git add`로 마킹, 머지 커밋 생성 — **전부 하지 않는다.**
- 해결은 **항상 사용자가 직접** 한다. 이 스킬은 "무엇과 왜 충돌났는지"만 밝힌다.
- 유일하게 허용되는 상태 변경: **develop/main 위 진행 중 머지의 `git merge --abort`** (아래 2단계).

## 워크플로우

### 0. 충돌/머지 상태 감지
```bash
git branch --show-current
git status -s
git diff --name-only --diff-filter=U        # 충돌(unmerged) 파일
ls .git/MERGE_HEAD 2>/dev/null && echo "머지 진행 중"
ls .git/rebase-merge .git/rebase-apply 2>/dev/null && echo "리베이스 진행 중"
```
- 충돌 파일도 없고 진행 중 머지/리베이스도 없으면 → "현재 충돌 없음"을 알리고, 필요하면 **사전 예측 모드**(4-B)로 안내 후 종료.

### 1. 진행 중 머지의 양쪽 브랜치 식별
```bash
# ours = 현재 체크아웃 브랜치(HEAD), theirs = 유입 브랜치
cat .git/MERGE_HEAD 2>/dev/null                       # 유입 커밋 해시
git name-rev --name-only $(cat .git/MERGE_HEAD 2>/dev/null) 2>/dev/null
```
- 충돌 파일별 충돌 구간을 읽어 **HEAD 측 / 유입 측 코드 조각**을 각각 확보한다(추적용).

### 2. develop/main 위에서 진행 중이면 → 즉시 abort 하여 중단
현재 브랜치가 `develop` 또는 `main`(운영/개발 통합 브랜치)이고 머지가 진행 중이면:
1. 먼저 1단계에서 **충돌 파일·양쪽 코드 조각을 캡처**해 둔다(abort 후엔 마커가 사라짐).
2. 중단:
   ```bash
   git merge --abort   # (리베이스면 git rebase --abort)
   ```
   - `MERGE_HEAD`가 없어 abort가 실패하면(비정상 인덱스 상태) 사용자에게 상황을 알리고 **임의로 reset 하지 않는다**. 판단을 요청한다.
3. "팀 룰상 develop/main에서 직접 해결하지 않으므로 머지를 중단했다"고 명확히 알린다.
4. abort 후에도 3단계 추적은 **캡처해 둔 코드 조각**과 두 브랜치를 대상으로 계속 진행한다.

> 현재 브랜치가 **feature 브랜치**면 abort 하지 않는다(거기서 해결하는 게 맞으므로). 추적·리포트만 하고 사용자가 해결하도록 둔다.

### 3. 충돌 상대 feature 브랜치 추적
충돌 구간에서 뽑은 **상대편(대개 develop/main 유입 측) 코드 조각**으로 출처를 특정한다. 파일·조각마다:
```bash
# 그 코드를 추가한 커밋 (유입 브랜치 히스토리 기준)
git log <유입브랜치> -S'<코드조각>' --oneline -- <파일경로> | head

COMMIT=<위에서 찾은 해시>
git show -s --format="commit %H%nauthor %an <%ae>%ndate %ad%nsubject %s" $COMMIT

# 그 커밋을 포함하는 브랜치(= 원본 feature 브랜치)
git branch -a --contains $COMMIT | grep -v 'develop\|main\|HEAD'
```
- 커밋 메시지의 `DTDEV-###` 티켓 키도 함께 추출해 리포트한다.
- 코드 조각이 애매하면 `git blame <파일> -L <시작>,<끝>`으로 라인 단위 커밋을 특정한다.

### 4-A. 리포트 (표준 출력 형식)
```
🔀 충돌 리포트
- 진행 중 머지: <ours 브랜치> ← <theirs 브랜치>   (develop/main이면: ⚠️ abort로 중단함)
- 충돌 파일: <파일 목록>

충돌 상대 브랜치:
- 파일 <경로> (라인 X~Y)
  · 상대 코드: <조각>
  · 출처: <feature/DTDEV-###>  (커밋 <해시>, <작성자>, "<subject>")
```

### 4-B. base 판정 — 사용자에게 질문 (자동 결정 금지)
충돌한 두 feature 브랜치를 제시하고, **먼저 main에 머지되어 운영 배포가 일어나는 브랜치**가 어느 쪽인지 `AskUserQuestion`으로 묻는다. (자동 추론하지 않는다.)
- 답을 받으면 그 브랜치를 base로 삼는 해결 **방향만 안내**한다:
  ```
  권장 해결 방향(직접 수행): 
    1) 본인 feature 브랜치 체크아웃
    2) git merge <먼저 배포되는 base 브랜치>
    3) 충돌 해결(직접) 후 커밋 → PR 반영
  ```
- **명령 실행은 사용자 몫.** 이 스킬은 여기서 멈춘다(해결·머지 대행 금지).

## 종료 조건
- 충돌 상대 브랜치·커밋·작성자·티켓을 리포트했고,
- develop/main 진행 머지가 있었다면 abort로 중단했으며,
- base 방향은 사용자에게 물어 안내만 했다면 완료.
