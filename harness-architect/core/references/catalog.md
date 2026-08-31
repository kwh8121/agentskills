# 카탈로그 — 에이전트 7종과 스킬 매핑

## 왜 카탈로그인가

작업마다 역할을 새로 설계하면 매번 역할 정의에 토큰을 쓰고 결과도 흔들린다.
**에이전트는 아래 7종에서 고르기만 한다. 새 역할을 만들지 않는다.**

새 역할이 필요해 보이면 먼저 이 판정을 통과해야 한다:

```
반복되는 Procedure 인가?            → Skill (아래 매핑표에서 주입)
독립적인 책임·판단·완료조건인가?     → Agent (7종 중에 없으면 사람에게 물어본다)
```

## 에이전트 7종

정의는 `roles/manifest.tsv` 한 곳에서 하고, 하네스별 역할 파일은 거기서 파생된다.
역할 본문은 `roles/<id>.md` 이며 하네스 어휘를 쓰지 않는다.
`scripts/check-adapters.py` 가 세 어댑터와 manifest 의 일치를 강제한다.

| id | tier | capabilities | 책임 | 도구 경계 근거 |
|---|---|---|---|---|
| `implementer` | standard | read, search, edit, write, bash | 일반 구현 | 소스 편집권을 가진 유일한 역할 |
| `reviewer` | deep | read, search, bash, write | 의미적 코드 리뷰 | **edit 없음** — 리뷰어가 고치면 독립 검증이 무너진다 |
| `dependency-mapper` | standard | read, search, bash | 영향·의존성 분석 | 조사 전용. 어떤 파일도 쓰지 않는다 |
| `baseline-tester` | standard | read, search, bash, write | 기존 동작 고정 | 테스트 파일만 write. 소스 수정 금지 |
| `integrator` | deep | read, search, edit, write, bash | 병렬 결과 통합 | 머지 충돌 해소를 위해 edit 필요 |
| `orchestrator` | deep | read, bash, write, dispatch | DAG·상태·재라우팅 | **edit 없음** — Orchestrator 는 코드를 쓰지 않는다 |
| `deployment-agent` | standard | read, bash, write | 배포·헬스체크·롤백 준비 | Human Gate 없이는 실행하지 않는다 |

`tier` → 실제 모델, `capabilities` → 그 하네스의 도구 이름은 **어댑터가 정한다**
(`references/adapters/<하네스>.md` 의 `tier_map`·`guard`). 이 표에 하네스 고유 이름을 쓰지 않는다.

### capabilities 가 실제로 막아주는 것과 막아주지 못하는 것

편집 능력을 빼면 **기존 파일을 고치는 정식 경로**가 사라진다. 그것이 전부다.
쓰기 능력은 새 파일을 만들 수 있고, 셸은 리다이렉션·`sed -i` 로 무엇이든 바꿀 수 있다.
`reviewer`·`orchestrator`(write+bash)와 `dependency-mapper`(bash)가 여기 해당한다.

그래서 `scripts/guard-readonly.py` 가 **쓰기 대상 경로**로 2차 판정을 한다 —
reviewer·orchestrator 는 `_workspace/` 아래만, dependency-mapper 는 아무 데도 쓰지 못한다
(허용 범위의 진실의 원천은 `roles/manifest.tsv` 의 `write_scope`).

**강제 수준은 하네스마다 다르다.** 못 막는 것을 막는다고 쓰지 않는다:

| 경계 | Claude Code | Codex | OpenCode |
|---|---|---|---|
| reviewer·orchestrator 가 편집·쓰기 도구로 소스 수정 | **역할 선언 + 훅이 차단** | **훅이 차단** (신뢰·승인 후) | **역할 선언이 차단** (`tools`/`permission`) |
| reviewer·orchestrator 가 셸로 소스 수정 (`sed -i`·리다이렉션·`rm`·`git commit` 등) | **훅이 차단** | **훅이 차단** (신뢰·승인 후) | **플러그인 훅이 차단** (`harness-guard.js` 등록 시) |
| dependency-mapper 가 어떤 경로로든 파일 생성 | **훅이 차단** | **훅이 차단** (신뢰·승인 후) | **역할 선언 + 플러그인 훅** |
| 위 역할이 **MCP 쓰기 도구**로 소스 수정 (`serena_replace_content` 등) | **훅이 차단** (이름 패턴 + 경로 판정) | **훅이 차단** (신뢰·승인 후) | **플러그인 훅이 차단** (등록 시) |
| 위 역할이 변수 확장·base64·인터프리터 파이프로 우회 | 미차단 | 미차단 | 미차단 |
| 이름에 write/edit/patch/replace… 가 없는 미지의 MCP 쓰기 도구 | 미차단 | 미차단 | 미차단 |

- Codex 는 역할별 도구 목록을 강제하지 않는다. 경계는 훅과 프롬프트 준수가 함께 지키며,
  **훅은 프로젝트 신뢰와 해시 승인 뒤에만 동작한다** — 승인 전에는 프롬프트 준수뿐이다.
- OpenCode 는 선언적 경계가 1차 방어선이고, 셸 우회는 플러그인을 등록해야 막힌다.
- **MCP 도구는 이름 패턴으로 판정한다.** 고정 목록만으로는 `serena_replace_content` 같은
  도구가 그대로 통과한다(실측으로 관측해 고쳤다). 이름에 write/edit/patch/replace/create/
  delete/insert/rename/move/append 가 들어가면 쓰기로 보고 경로를 검사하며, 경로를 못 찾으면
  거부한다. 그 어휘를 쓰지 않는 MCP 쓰기 도구는 여전히 통과한다.
- **어느 하네스에서도 샌드박스가 아니다.** 훅은 셸을 파싱하지 않고 쓰기 구문을 패턴으로
  찾으므로 변수 확장이나 인터프리터 경유는 잡지 못한다. 규율 장치이지 보안 경계가 아니다.

`implementer`·`integrator` 는 소스를 고치는 것이 일이라 가드 대상이 아니고,
`baseline-tester` 는 특성화 테스트를 레포의 테스트 디렉터리에 써야 해서 제외했다.

배선 방법은 어댑터의 `guard` 절과 `../../../README.md` 의 "설치" 참고. 훅을 걸지 않아도
스킬은 동작하지만, 그때 위 표의 "차단" 칸은 전부 "프롬프트 준수"로 내려간다.

### 카탈로그에 없는 것과 그 이유

- **security-reviewer 를 만들지 않는다.** `reviewer` + `security-review` 스킬 주입으로 처리한다.
  보안은 별도 책임이 아니라 같은 diff 를 보는 다른 렌즈다. 에이전트를 늘리면 diff 를 두 번 읽게 된다.
- **test-writer 를 만들지 않는다.** 테스트 작성은 `implementer` 의 일이고,
  방법은 `superpowers:test-driven-development` 가 규정한다.
- **planner 를 만들지 않는다.** `superpowers:writing-plans` 가 이미 그 절차다.
- **documentation-agent 를 만들지 않는다.** 문서는 구현의 일부다.

## superpowers 스킬 매핑

절차적 지식은 직접 쓰지 않고 아래로 위임한다. 활성 버전은 **superpowers 6.3.0**.

**두 종류를 섞지 않는다.** 워커에게는 `Agent` 도구가 없다 —
다른 에이전트를 부르는 스킬을 워커 프롬프트에 주입하면 실행되지 않는다.

- `controller_skills` — 하네스를 운전하는 쪽이 직접 호출한다.
  H0~H2 는 harness-architect 스킬 자신이, H3 은 `orchestrator` 가 소유한다.
- `agent_skills` — 워커 프롬프트에 주입한다. 자기 작업만 하는 스킬이어야 한다.

| 상황 | 위임 대상 | 소유 | 적용 레벨 |
|---|---|---|---|
| 목표·수용 기준이 불명확해 프로파일링 불가 | `superpowers:brainstorming` | controller | 전 레벨 (Phase 0) |
| 다단계 작업의 계획 수립 | `superpowers:writing-plans` | controller | H2, H3 |
| 계획을 서브에이전트로 실행 | `superpowers:subagent-driven-development` | controller | H2, H3 |
| 독립 조사 2건 이상을 동시에 | `superpowers:dispatching-parallel-agents` | controller | 전 레벨 |
| reviewer 호출 방법·심사 기준 | `superpowers:requesting-code-review` | controller | H1–H3 |
| 작업 공간 격리 | `superpowers:using-git-worktrees` | controller | H2, H3 (**필수**) |
| 완료 선언 직전 | `superpowers:verification-before-completion` | controller | **전 레벨 필수** |
| 브랜치 마무리 + 작업 공간 정리 | `superpowers:finishing-a-development-branch` | controller | H2·H3 **필수** / H1 은 브랜치 작업 시 |
| implementer 의 기본 작업 방식 | `superpowers:test-driven-development` | agent (implementer) | H1–H3 |
| 리뷰 피드백 수신·반영 | `superpowers:receiving-code-review` | agent (implementer) | H1–H3 |
| 게이트가 반복 실패, 원인 불명 | `superpowers:systematic-debugging` | 양쪽 | 전 레벨 |
| `risk: high` 인 diff 의 보안 심사 | 내장 `security-review` | agent (reviewer) | risk: high |

**표기 관례**: 산문에서 `**REQUIRED SUB-SKILL:** Use superpowers:<name>` 형태로 지시한다
(superpowers 자신의 관례를 그대로 따른다).

## H2/H3 는 superpowers 위임이 본체다

harness-architect 가 H2/H3 에서 직접 하는 일은 네 가지뿐이다:

1. 레벨 판정과 `HarnessSpec` 산출
2. 전문 역할 에이전트 배치 (`dependency-mapper` / `baseline-tester` / `integrator` / `orchestrator`)
3. 결정론적 게이트 실행 (`run-gates.sh`)
4. Human Gate

계획 수립과 태스크 루프는 `superpowers:writing-plans` → `superpowers:subagent-driven-development` 가
담당한다. SDD 의 워크스페이스·진행 원장·`scripts/{sdd-workspace,task-brief,review-package}` 를
**그대로 호출하고 재구현하지 않는다.**
