# harness-architect

> 개발 업무를 자연어로 받아 **작업 복잡도에 맞는 최소 하네스를 매번 새로 고르는** Claude Code 스킬.
> 버튼 색상 변경에 5인 팀을 붙이지 않고, 인증 마이그레이션을 단일 에이전트로 밀지 않는다.

```
Task ──▶ harness-architect Skill ──▶ HarnessSpec ─┬→ Agent Catalog (7종)
        (분석 + 판정 + 구성안)     (실행 계약)     ├→ superpowers Skills (위임)
                                                   └→ Deterministic Gates (exit code)
```

**Harness Architect 자체는 Agent 가 아니라 Skill 이다.** 분석·판정·구성안 생성은 Skill 이 하고,
실제 작업 수행은 카탈로그의 Agent 가 한다. `orchestrator` 는 가장 복잡한 레벨(H3)로
판정된 경우에만 활성화된다.

## 설치

이 폴더(`.claude/`)를 프로젝트 루트에 그대로 복사한다. 절대 경로 하드코딩이 없어
통째로 복사하면 그대로 동작한다.

```bash
cp -r harness-architect/.claude /path/to/your-project/
```

`.claude/settings.json` 은 덮어쓰지 말고 병합한다. 대상 프로젝트에 이미
`hooks.PreToolUse` 가 있으면 아래 항목을 배열에 **추가**한다(교체 아님).

```json
{
  "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/skills/harness-architect/scripts/guard-readonly.py\"",
      "timeout": 10
    }
  ]
}
```

### 사전 요건

| 요건 | 없으면 무엇이 끊기는가 |
|---|---|
| Claude Code (스킬·서브에이전트·훅 지원 버전) | 스킬 자체가 로드되지 않는다 |
| Bash, POSIX `awk`/`grep` | `detect-stack.sh`·`run-gates.sh`·`gate-summary.sh` |
| Python 3 | `validate-spec.py`, `guard-readonly.py` |
| **PyYAML** (`pip install pyyaml`) — 선택 | 없으면 `validate-spec.py` 가 exit 2 로 "검증 불가"를 알린다. 하네스는 계속 동작하지만 아래 "승인 게이트 확인" 항목을 사람이 대신 봐야 한다 |
| [superpowers 플러그인](https://github.com/obra/superpowers) (6.3.0 기준) | H0 도 `verification-before-completion` 이 필수라 완전히 끊긴다. **Phase 1 이 감지해 exit 4 로 중단하고 설치 명령(`/plugin install superpowers@claude-plugins-official`)을 제시한다.** 매핑표는 `references/catalog.md` |
| Linear MCP — 선택 | `tracking.provider: linear` 를 쓸 수 없다. `none` 으로 두면 그대로 동작한다 |

### 설치 확인

```bash
# superpowers preflight — 필수 스킬 11종이 있는지 확인 (없으면 목록을 알려준다)
bash .claude/skills/harness-architect/scripts/check-superpowers.sh

# 스택 감지 — 대상 프로젝트의 실제 검증 명령을 찾아내는지 확인
# (superpowers 가 없으면 골격을 만들지 않고 exit 4 로 중단한다)
bash .claude/skills/harness-architect/scripts/init-workspace.sh

# HarnessSpec 예제 4종이 계약 검증기를 통과하는지 확인 (PyYAML 필요)
for f in .claude/skills/harness-architect/examples/*.yaml; do
  python3 .claude/skills/harness-architect/scripts/validate-spec.py "$f"
done

# 읽기 전용 가드가 실제로 걸리는지 확인
echo '{"hook_event_name":"PreToolUse","agent_type":"reviewer","agent_id":"s1",
       "tool_name":"Write","tool_input":{"file_path":"src/x.ts","content":"y"}}' \
  | python3 .claude/skills/harness-architect/scripts/guard-readonly.py
```

마지막 명령은 `"permissionDecision": "deny"` 가 포함된 JSON 을 내야 한다. 아무 출력도 없으면
`.claude/settings.json` 에 훅이 등록되지 않은 것이다.

## 하네스 레벨 4종

| 레벨 | 패턴 | 역할 수 | 적용 |
|---|---|---|---|
| **H0** | Single | 0 | 단일 영역, 동작 변화 없음. 게이트가 회귀를 전부 잡는 경우 |
| **H1** | Pipeline | 2 | 일반적인 기능 개발. implementer → 게이트 → reviewer |
| **H2** | Fan-out / Fan-in | ≤5 | 진짜 독립적인 작업 단위가 2개 이상일 때만 |
| **H3** | Orchestrator + DAG | ≤7 | 의존 + 실패 원인별 재라우팅이 필요할 때만 |

판정은 6축 프로파일링(scope / coupling / parallelism / uncertainty / risk / side_effect) 뒤
5스텝 판정 트리로 이루어진다(`references/routing.md`). **한 단계 아래가 왜 안 되는지 쓸 수
없으면 아래 레벨이 맞다.**

## 구성

- `.claude/skills/harness-architect/SKILL.md` — Phase 0~5 오케스트레이터
- `.claude/skills/harness-architect/references/` — 판정 기준 5종
  (profiling / routing / catalog / context-budget / linear-tracking)
- `.claude/skills/harness-architect/schemas/harness-spec.yaml` — 실행 계약 스키마
- `.claude/skills/harness-architect/examples/` — H0~H3 판정 사례 4종
- `.claude/skills/harness-architect/scripts/` —
  `detect-stack.sh` / `run-gates.sh` / `init-workspace.sh` / `gate-summary.sh` /
  `check-superpowers.sh` / `harness-paths.sh`(source 전용) (셸) +
  `validate-spec.py` / `guard-readonly.py` (파이썬)
- `.claude/agents/` × 7 — implementer / reviewer / dependency-mapper / baseline-tester /
  integrator / orchestrator / deployment-agent
- `.claude/settings.json` — 읽기 전용 가드 훅 등록

## 토큰을 아끼는 세 가지 장치

1. **결정론적 게이트 분리** — 포맷·린트·타입·테스트·빌드는 `run-gates.sh` 의 exit code 가
   판정한다. AI 리뷰어에게 "린트 문제 찾아봐"라고 시키지 않는다.
2. **컨텍스트 예산** — 에이전트마다 `required`/`optional`/`forbidden` 을 명시한다
   (`references/context-budget.md`). 모든 에이전트의 `forbidden` 에
   `full_repository_dump` 가 들어간다. 보고서는 본문이 아니라 경로로 넘긴다.
3. **고정 카탈로그** — 역할 정의를 매번 새로 생성하지 않는다. 7종에서 고르기만 한다.

## 도구 경계는 frontmatter + 훅으로 강제한다

frontmatter 의 `tools` 가 1차 경계다 — `reviewer`·`orchestrator` 에 `Edit` 이 없고,
`dependency-mapper` 에 `Write` 가 없다. 하지만 `Edit` 을 빼도 `Write` 로 새 파일을,
`Bash` 로 `sed -i`·리다이렉션을 쓸 수 있다. `guard-readonly.py` 를 `PreToolUse` 훅으로
걸어 **쓰기 대상 경로**로 2차 판정한다.

| 역할 | 쓰기 허용 범위 |
|---|---|
| `reviewer` · `orchestrator` | `_workspace/` 아래만 |
| `dependency-mapper` | 없음 (조사 전용) |
| `implementer` · `integrator` · `baseline-tester` · `deployment-agent` | 가드 대상 아님 |

훅은 셸을 파싱하지 않고 쓰기 구문을 패턴으로 찾는다. **샌드박스가 아니라 규율 장치다.**

## HarnessSpec 은 실행 전에 기계가 검증한다

Phase 3 은 승인을 요청하기 전에 `validate-spec.py` 를 돌린다. exit 1 이면 승인을 요청하지 않는다.

```bash
python3 .claude/skills/harness-architect/scripts/validate-spec.py \
  _workspace/harness/spec.yaml --gates _workspace/harness/gates.tsv
```

카탈로그 밖 에이전트, `model`/숫자 필드 타입 오류, 축 모순(`coupling: high` +
`parallelism ≠ none`), 레벨별 에이전트 불변식, controller 스킬의 워커 오배정,
**수용 기준에 대응하는 게이트 부재**, Human Gate 누락, H3 재라우팅 계약(`escalation`) 누락,
`full_repository_dump` 금지 누락, 루프·워커 상한 초과를 거부한다.
`yaml.safe_load` 성공은 "문법이 YAML 이다" 만 말해 준다는 것이 이 검증기를 만든 이유다.

## 진행 상황은 Linear 에 남길 수 있다

`tracking.provider: linear` 로 승인하면 진행 상황이 Linear 에 남는다 — 목적은 사용자가
터미널을 보지 않고도 진행과 검증 근거를 파악하는 것이다.

| 하네스 | Linear |
|---|---|
| H1 작업 | Issue 1건 (작업 단위가 1개다) |
| H2/H3 작업 | Project + 단위별 Issue |
| H3 DAG 의 `depends_on` | `blockedBy`/`blocks` — Linear 가 의존을 네이티브로 표현한다 |
| Phase 3 승인 대기 | 상태 `Triage` |
| 구현 중 / 리뷰 중 / 완료 | `In Progress` / `In Review` / `Done` |
| 게이트 결과 | 코멘트 — 명령 + exit code + 로그 경로 (**전문은 붙이지 않는다**) |
| Human Gate | `In Review` + 증거 코멘트 (로그 경로·diff 통계·롤백 절차) |

**H0 은 추적하지 않는다.** 단일 파일 변경까지 이슈로 만들면 백로그가 오탈자 수정으로 찬다.
**쓰기는 컨트롤러만 한다** — 워커·orchestrator 는 Linear 를 건드리지 않고 상태 토큰만
반환한다. 추적 실패는 하네스를 멈추지 않는다. 상세 매핑은 `references/linear-tracking.md`.

## 작업 공간은 만든 하네스가 정리한다

H2·H3 은 `superpowers:using-git-worktrees` 로 격리된 worktree 에서 작업하고, Phase 5 에서
`superpowers:finishing-a-development-branch` 로 정리한다. **두 스킬은 쌍이며
`validate-spec.py` 가 그 짝을 강제한다** (`E-SKILL-WORKTREE`).

정리 시점을 정하는 것은 **통합 결과**다 — 로컬 머지 완료면 제거, PR 생성이나 유지면 보존.
**Linear 상태는 정리를 트리거하지 않는다.** `Canceled` 는 폐기뿐 아니라 강등(H2→H1, 작업은
계속된다)을 포함하고, `Done` 은 최종 게이트 통과 시점이라 브랜치 통합보다 먼저 찍히기
때문이다. Linear 는 반대 방향으로만 쓴다: `In Progress` 면 경고하고, `Canceled` 면 폐기
메뉴를 제시만 한다.

게이트 로그·조사 보고서는 `scripts/harness-paths.sh` 가 `_workspace/` 를 **메인 워크트리
루트**에 고정하므로 worktree 를 제거해도 남는다. 게이트 *명령*은 그대로 현재 트리에서
실행된다 — 검증 대상은 worktree 의 코드다.

## 승인 게이트 확인

Phase 3 에서 승인을 요청받으면 다음을 확인한다.

- [ ] 승인을 요청받기 전에 에이전트가 스폰되지 않았다
- [ ] 요약에 레벨·근거·에이전트와 모델·게이트·`max_loops`·Human Gate 가 전부 있다
- [ ] **한 단계 아래 레벨이 왜 안 되는지** 근거가 있다. 없으면 그 아래가 맞다
- [ ] `risk: high` 가 레벨 승격 근거로 쓰이지 않았다 (risk 는 reviewer·`max_loops` 만 바꾼다)
- [ ] **수용 기준마다 그것을 확인하는 게이트가 있다** — 게이트로 확인 불가능한 항목은
      `verification.manual` 에 있는가? 어느 쪽에도 없는 수용 기준은 검증되지 않은 채
      완료 선언된다
- [ ] (Linear 추적 시) 추적 대상이 만들어졌고 상태가 `Triage` 다
- [ ] (H2·H3) `controller_skills` 에 `using-git-worktrees` 와
      `finishing-a-development-branch` 가 **둘 다** 있다 — 격리를 만들었으면 해제도 절차에 있어야 한다

## 알려진 한계

- 읽기 전용 가드 훅은 셸을 파싱하지 않아 변수 확장·인터프리터 경유 우회가 가능하다
  (규율 장치이지 샌드박스가 아니다)
- Linear API(`get_issue`/`get_project`)가 `blockedBy`·진행률(%)을 응답 필드로 노출하지
  않아 해당 항목은 자동 검증 대신 사용자 육안 확인에 의존한다
- H2 경로(Fan-out/Fan-in)와 Phase 4 의 실제 에이전트 dispatch 는 다양한 실전 사례로
  검증이 누적되는 중이다

