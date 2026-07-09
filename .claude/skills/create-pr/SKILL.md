---
name: create-pr
description: >
  변경사항을 커밋하고 push한 뒤 GitHub Pull Request를 생성한다. base 브랜치는 기본 develop.
  트리거: "PR 생성", "PR 만들어", "PR 올려", "커밋하고 PR", "풀리퀘스트 생성",
  "create a pull request", "pr-create", "/create-pr". Jira 티켓(khc.atlassian.net)을 자동 연동한다.
metadata:
  author: hannie-init
---

# Create PR Workflow

현재 변경사항을 커밋·push하고 GitHub PR을 생성한다. base 브랜치는 **기본 `develop`**. Jira 티켓을 찾으면 PR 본문에 링크하고 PR URL을 티켓 코멘트로 남긴다(티켓이 없으면 생략).

## 참고 레퍼런스
- 사내 `khc-vc-fe` create-pr (PR 템플릿 `.github` 탐지, Jira 도메인 `khc.atlassian.net` 명시)
- 사내 create-pr v1.2 (draft PR, Jira 연동, worktree 지원)

---

## 1. 정보 수집 및 분석

필수 정보가 없으면 확인한다.

- **Base 브랜치**: PR 대상. **기본값 `develop`.** 원격에 `develop`이 없으면(`git ls-remote --heads origin develop`가 비면) repo 기본 브랜치(`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`)로 대체하고 사용자에게 알린다.
- **티켓 키**: `[A-Z]+-\d+` 패턴(예: `DPT-10557`, `DPPM-135`, `KHCQA-343`). **브랜치명·커밋 메시지에서 자동 추출**하고, 여러 개면 쉼표로. 못 찾으면 티켓 없이 진행한다(에러 아님).

변경사항을 분석한다.

```bash
git status --short --branch
git diff --staged
git diff {base_branch}...HEAD
git log {base_branch}..HEAD --oneline
git remote get-url origin
git worktree list
```

이미 커밋이 끝나 staged diff가 비어도 브랜치 diff·커밋 히스토리로 PR 내용을 작성한다.

---

## 2. 커밋 생성 (필요 시)

커밋 안 된 변경이 있으면 스테이징 후 커밋한다. **커밋 컨벤션은 사용자 글로벌 규칙(`~/.gitmessage.txt` / `korean-commit`)을 따른다** — scope·버전태그는 쓰지 않는다.

- **타입**: `feat` | `fix` | `docs` | `refactor` | `revert` | `test`
- **형식**(Subject 한글):

```text
{타입}: {한글 요약}

- {주요 변경사항}

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

- `git add -A` 대신 관련 파일만 선택 스테이징. 민감/불필요 파일(`.env*`, `settings.local.json`, `.idea/`, `build/`, `.DS_Store` 등) 제외.
- 이미 적절한 커밋이 있으면 이 단계를 건너뛴다.
- **현재 브랜치가 base 브랜치이면** PR용 브랜치 생성 여부를 먼저 확인한다(base에 직접 커밋 금지).

---

## 3. PR 템플릿 결정

리포지토리의 `.github`를 먼저 확인하고, 없으면 아래 기본 템플릿을 쓴다.

**탐지 순서**(먼저 존재하는 것 사용):
1. `.github/PULL_REQUEST_TEMPLATE.md`
2. `.github/pull_request_template.md`
3. `PULL_REQUEST_TEMPLATE.md` (루트) / `docs/PULL_REQUEST_TEMPLATE.md`
4. `.github/PULL_REQUEST_TEMPLATE/*.md` (여러 개면 사용자에게 선택)

```bash
ls .github/PULL_REQUEST_TEMPLATE.md .github/pull_request_template.md PULL_REQUEST_TEMPLATE.md docs/PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/*.md 2>/dev/null
```

- 레포 템플릿이 있으면 **그 형식을 그대로 사용**하고, 예시/플레이스홀더(`ex. ...`)를 실제 내용으로 채운다.
- 없으면 아래 **기본 템플릿(상세형)** 사용:

```markdown
# 🔗 티켓 링크

- [{티켓키}](https://khc.atlassian.net/browse/{티켓키})
<!-- 티켓 없으면 이 섹션 생략 -->

# 📋 작업 내용

- {변경사항 요약}

## 🧐 주요 검토 필요 사항

- {검토 포인트}

# ✅ 체크리스트

- [x] 셀프 리뷰 완료
- [x] 테스트 완료
- [x] 변경 사이즈 적절
```

> **Jira 링크 규격(필수)**: 도메인은 반드시 `https://khc.atlassian.net/browse/{티켓키}`. 사용자 이메일 등에서 다른 도메인을 추측하지 않는다. 티켓이 없으면 티켓 링크 섹션을 통째로 뺀다.

---

## 4. Push 및 PR 생성

현재 브랜치를 push한다.

```bash
git push -u origin $(git rev-parse --abbrev-ref HEAD)
```

**PR 내용을 사용자에게 보여주고 승인**을 받은 뒤 **draft PR**을 생성한다.

- **제목**: `[{티켓키}] {타입}: {한글 요약}` — 콜론 뒤 요약은 **한글**. 티켓 없으면 `{타입}: {한글 요약}`.
- **본문**: 3단계에서 정한 템플릿을 채운 전체.

```bash
gh pr create \
  --base {base_branch} \
  --draft \
  --assignee @me \
  --title "[{티켓키}] {타입}: {한글 요약}" \
  --body "{PR_BODY}"
```

---

## 5. PR 생성 후 검증

결과를 추측하지 말고 CLI로 확인한다.

```bash
gh pr view --json number,url,headRefName,baseRefName,title,isDraft
git remote get-url origin
```

- remote의 org/repo와 `gh pr view` 결과가 일치하는지 확인한다.
- 성공: 실제 PR 번호·URL을 전달하고 6단계(Jira)로 진행한다.
- 실패: 사용자가 직접 실행할 `gh pr create ...` 명령을 제공한다.

---

## 6. Jira 연동 (링크 + PR URL 코멘트)

PR 검증 성공 후 실행한다. **티켓이 없으면 조용히 건너뛴다(에러 아님).**

- 도구: **Atlassian MCP** (`mcp__atlassian__*`). `cloudId`는 `khc.atlassian.net`(hostname)을 우선 사용하고, 실패 시 `getAccessibleAtlassianResources`로 조회.
- 티켓 키 추출: PR **title** `[A-Z]+-\d+` + PR **body**의 `# 🔗 티켓 링크` 섹션(다음 `#` 헤딩 전까지)에서 추출 → 중복 제거.

각 티켓에 대해:
1. `getJiraIssue`로 **존재 확인**(없거나 조회 실패면 그 티켓만 건너뜀).
2. `addCommentToJiraIssue`로 PR URL 코멘트 작성:
   ```
   PR #{PR번호} 생성: {PR_URL}
   ```

- **상태 전이(transition)는 하지 않는다** — 링크와 코멘트만.
- 개별 티켓 실패 시 `"⚠️ {티켓키} Jira 코멘트 실패 — {사유}"` 경고만 출력하고 **PR 플로우는 중단하지 않는다**.
- Atlassian MCP를 못 쓰는 환경이면 건너뛰고 이유를 보고한다.
- 완료 후 `"✅ Jira: {성공}건 코멘트, {스킵}건"` 요약.

---

## 7. Worktree 및 특이사항

- Worktree 환경이면 해당 경로 컨텍스트를 유지하고 모든 명령을 같은 repo에서 실행한다.
- 현재 브랜치가 base 브랜치이면 PR용 브랜치 생성을 먼저 확인한다.
- push가 reject되면 `git pull --rebase origin {branch}` 제안/실행. 충돌 시 충돌 파일과 수동 후속 명령을 안내한다.
- co-author 생략을 원하거나 repo 정책상 금지면 생략한다.

---

## 변경 이력

| 날짜 | 변경 내용 |
|---|---|
| 2026-07-09 | 최초 작성. base 기본 develop / draft PR / .github 템플릿 탐지+기본 상세 템플릿 / Jira 링크+PR URL 코멘트(상태전이 없음, 없으면 생략) / 커밋은 글로벌 컨벤션. |
