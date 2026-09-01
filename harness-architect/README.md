# harness-architect

> 개발 업무를 자연어로 받아 **작업 복잡도에 맞는 최소 하네스를 매번 새로 고르는** 스킬.
> 버튼 색상 변경에 5인 팀을 붙이지 않고, 인증 마이그레이션을 단일 에이전트로 밀지 않는다.
> **Claude Code · Codex · OpenCode 세 하네스에서 같은 판정·같은 계약으로 동작한다.**

```
Task ──▶ harness-architect Skill ──▶ HarnessSpec ─┬→ Agent Catalog (7종)
        (분석 + 판정 + 구성안)     (실행 계약)     ├→ superpowers Skills (위임)
                                                   └→ Deterministic Gates (exit code)
```

**Harness Architect 자체는 Agent 가 아니라 Skill 이다.** 분석·판정·구성안 생성은 Skill 이 하고,
실제 작업 수행은 카탈로그의 Agent 가 한다. `orchestrator` 는 가장 복잡한 레벨(H3)로
판정된 경우에만 활성화된다.

## 설치

```bash
bash install.sh /path/to/your-project                      # 하네스 자동 감지
bash install.sh /path/to/your-project --harness codex      # 명시
```

`install.sh` 는 파일 복사만 한다(생성·컴파일 없음). 배치되는 것:

| 하네스 | 코어(스킬 본체) | 어댑터 |
|---|---|---|
| Claude Code | `.claude/skills/harness-architect/` | `.claude/agents/*.md` · `.claude/settings.json` |
| Codex | `.codex/skills/harness-architect/` | `.codex/agents/*.toml` · `.codex/hooks.json` |
| OpenCode | `.opencode/skills/harness-architect/` | `.opencode/agent/*.md` · `.opencode/plugin/harness-guard.js` |

**이미 있는 설정 파일(`settings.json`·`hooks.json`·`opencode.json`)은 덮어쓰지 않고
우리 항목만 추가한다** (`scripts/merge-config.py`). 대상 프로젝트의 기존 훅을 지우는 것이
설치 스크립트가 할 수 있는 최악의 일이므로, 병합 규칙을 좁게 잡았다:

| 상황 | 동작 |
|---|---|
| 기존 훅이 있다 | 그대로 두고 우리 그룹을 **뒤에 추가**한다 |
| 우리 훅이 이미 있다 | 중복 추가하지 않는다. 정의가 바뀌었으면 **그 항목만 갱신**한다 |
| 바꾸기 전 | `<파일>.bak-<타임스탬프>` 로 백업한다 |
| 대상이 깨진 JSON 이다 | **손대지 않고** 붙일 내용을 출력한다 — 추측으로 고치지 않는다 |
| `--no-merge` | 기존 파일을 건드리지 않고 출력만 한다 |

`opencode.json` 은 **있을 때만** `plugin` 배열에 더한다. 없으면 만들지 않는다 —
프로젝트 설정 파일을 새로 만들면 모델 해석 등 다른 동작에 영향을 줄 수 있다.

`install.sh` 는 복사 전에 **소스 트리가 온전한지** 확인하고(`core/`·어댑터 트리가 없으면
exit 2 — 부분 클론·`/tmp` 정리로 잘린 체크아웃을 조용히 배치하지 않는다), 복사 후에는
**기대 산출물이 실제로 생겼는지 검증한 뒤에** 성공을 알린다(빠지면 목록을 찍고 exit 1).
`set -e` 없이 병합 exit code 를 직접 다루므로, 이 두 관문이 "조용한 부분 배치"를 막는다.

### 사전 요건

| 요건 | 없으면 무엇이 끊기는가 |
|---|---|
| Bash, POSIX `awk`/`grep` | `detect-stack.sh`·`run-gates.sh`·`gate-summary.sh`·`detect-harness.sh` |
| Python 3 | `validate-spec.py`, `guard-readonly.py`, `checkpoint.py`, `resume-check.py` |
| **PyYAML** (`pip install pyyaml`) — 선택 | 없으면 `validate-spec.py` 가 exit 2 로 "검증 불가"를 알린다. 하네스는 계속 동작하지만 아래 "승인 게이트 확인" 항목을 사람이 대신 봐야 한다 |
| [superpowers](https://github.com/obra/superpowers) (필수 스킬 11종) | H0 도 `verification-before-completion` 이 필수라 완전히 끊긴다. **Phase 1 이 감지해 exit 4 로 중단하고 그 하네스의 설치 명령을 제시한다.** 매핑표는 `core/references/catalog.md` |
| Linear MCP — 선택 | `tracking.provider: linear` 를 쓸 수 없다. `none` 으로 두면 그대로 동작한다 |

하네스별 추가 요건:

| 하네스 | 추가로 필요한 것 |
|---|---|
| Claude Code | 스킬·서브에이전트·훅을 지원하는 버전 |
| Codex | `~/.codex/config.toml` 에 `[features] hooks = true`, `multi_agent = true`. **훅은 프로젝트 신뢰와 해시 승인 뒤에만 동작한다** |
| OpenCode | `opencode.json` 의 `plugin` 배열에 `"./.opencode/plugin/harness-guard.js"` 등록 (없으면 선언적 경계만 남는다) |

### 설치 확인

```bash
# 어댑터 3종이 같은 계약을 선언하는가 (저장소에서만 의미 있음)
python3 core/scripts/check-adapters.py

# 아래는 설치된 프로젝트에서. <skill_dir> 은 detect-harness.sh 가 알려준다
bash <skill_dir>/scripts/detect-harness.sh
bash <skill_dir>/scripts/check-superpowers.sh        # 필수 스킬 11종 확인
bash <skill_dir>/scripts/init-workspace.sh           # 스택 감지 (exit 4 = superpowers 미설치)

for f in <skill_dir>/examples/*.yaml; do
  python3 <skill_dir>/scripts/validate-spec.py "$f"
done

echo '{"agent_type":"reviewer","tool_name":"Write","tool_input":{"file_path":"src/x.ts"}}' \
  | python3 <skill_dir>/scripts/guard-readonly.py
```

마지막 명령은 `"permissionDecision": "deny"` 가 포함된 JSON 을 내야 한다. 아무 출력도 없으면
가드가 배선되지 않은 것이다 (하네스별 배선은 `core/references/adapters/<하네스>.md` 의 `guard`).

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

```
core/                          # 하네스와 무관한 한 벌
  SKILL.md                     # Phase −2~5 오케스트레이터
  references/                  # 판정 기준 (profiling / routing / catalog / context-budget / linear-tracking)
  references/adapters/         # 하네스 계약서 3종 + 키 목록 README
  roles/                       # 역할 본문 7종 + manifest.tsv (진실의 원천)
  schemas/harness-spec.yaml    # 실행 계약 스키마
  examples/                    # H0~H3 판정 사례 4종
  scripts/                     # detect-harness / detect-stack / init-workspace / run-gates /
                               # gate-summary / check-superpowers / harness-paths (셸)
                               # validate-spec / guard-readonly / checkpoint / resume-check /
                               # check-adapters (파이썬)
claude/.claude/   codex/.codex/   opencode/.opencode/   # 어댑터 트리 3종
install.sh                     # 하네스 감지 + 배치
```

**역할 정의의 진실의 원천은 `core/roles/manifest.tsv` 하나다.** 세 어댑터 트리의 역할 파일은
거기서 파생되고, `scripts/check-adapters.py` 가 tier·도구 경계·본문 참조의 일치를 강제한다.

## 토큰을 아끼는 세 가지 장치

1. **결정론적 게이트 분리** — 포맷·린트·타입·테스트·빌드는 `run-gates.sh` 의 exit code 가
   판정한다. AI 리뷰어에게 "린트 문제 찾아봐"라고 시키지 않는다.
2. **컨텍스트 예산** — 에이전트마다 `required`/`optional`/`forbidden` 을 명시한다
   (`references/context-budget.md`). 모든 에이전트의 `forbidden` 에
   `full_repository_dump` 가 들어간다. 보고서는 본문이 아니라 경로로 넘긴다.
3. **고정 카탈로그** — 역할 정의를 매번 새로 생성하지 않는다. 7종에서 고르기만 한다.

## 도구 경계는 역할 선언 + 훅으로 강제한다

역할 선언(`capabilities`)이 1차 경계다 — `reviewer`·`orchestrator` 에 편집 능력이 없고,
`dependency-mapper` 에 쓰기 능력이 없다. 하지만 편집을 빼도 쓰기로 새 파일을, 셸로
`sed -i`·리다이렉션을 쓸 수 있다. `guard-readonly.py` 가 **쓰기 대상 경로**로 2차 판정한다.

| 역할 | 쓰기 허용 범위 (`roles/manifest.tsv` 의 `write_scope`) |
|---|---|
| `reviewer` · `orchestrator` | `_workspace/` 아래만 |
| `dependency-mapper` | 없음 (조사 전용) |
| `implementer` · `integrator` · `baseline-tester` · `deployment-agent` | 가드 대상 아님 |

**강제 수준은 하네스마다 다르다** — Codex 는 훅 승인 전까지, OpenCode 는 플러그인 등록 전까지
셸 우회를 막지 못한다. 하네스별 표는 `core/references/catalog.md`.
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

## 중단하면 재개한다

Phase 전환·역할 완료마다 `checkpoint.py` 가 `_workspace/harness/state.json` 에 진행을 기록하고,
다음 세션의 Phase −1 이 `resume-check.py` 로 판정한다.

| exit | 뜻 | 스킬이 하는 일 |
|---|---|---|
| 0 | 재개할 것 없음 | Phase 0 으로 간다 |
| 10 | 자동 재개 후보 (Phase ≤ 2, 불일치 없음) | 브리핑의 `작업:` 이 지금 요청과 같은지 확인하고 이어간다 |
| 11 | **사람 판단** — Phase 3 이상 / 불일치 / state 손상 / **하네스 변경** | 브리핑을 제시하고 멈춘다. 재개·재판정·폐기 중 사용자가 고른다 |
| 12 | 완료된 이전 작업이 남아 있음 | 새 작업을 시작할지 묻고 `--archive` 로 보존한다 |

불일치로 보는 것: HEAD·브랜치 변경, worktree 제거, 작업 트리 변경, **승인된 spec.yaml 변조**,
그리고 **state 에 기록된 하네스와 지금 하네스가 다른 경우**.

**승인은 세션을 넘어 상속되지 않는다.** Phase 3 이상에서 재개하면 `approved: true` 가 남아
있어도 새로 승인받는다 — 기록은 사실이지 실행 권한이 아니다. 하네스가 바뀌면 dispatch 문법·
모델·가드 강제 수준이 전부 달라지므로 같은 이유로 다시 승인받는다.

**손상된 state 는 추측으로 복구하지 않는다.** `resume-check.py` 는 exit 11 로, `checkpoint.py` 는
exit 3 으로 멈추고 원본을 보존한다.

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
- **Codex**: 등록되지 않은 프로젝트 훅은 신뢰된 경로에서도 조용히 무시된다(실측 확인).
  `scripts/codex-hook-trust.py` 가 `~/.codex/config.toml` 에 붙일 신뢰 블록을 만들어 주지만,
  **붙이기 전까지는 읽기 전용 경계가 프롬프트 준수에만 의존한다** (Codex 는 역할별 도구 목록도
  강제하지 않는다). 신뢰 블록을 붙인 뒤 훅이 실제로 발화하는지는 아직 실측하지 않았다
- **MCP 쓰기 도구**: 가드는 도구 *이름 패턴*(write/edit/patch/replace/…)으로 MCP 쓰기를
  판정한다. 실제로 `serena_replace_content` 가 이 경로로 새어 파일이 수정되는 것을 관측해
  고쳤다. **그 어휘를 쓰지 않는 MCP 쓰기 도구는 여전히 통과한다**
- **OpenCode**: `tool.execute.before` 에 역할 정보가 없어 플러그인이 `chat.params` 로
  세션→역할 맵을 만들어 조회한다. 그 훅이 먼저 돌지 않은 도구 호출은 가드를 통과한다
- 어댑터의 `tier_map` 모델 이름은 설치 환경의 모델 허용 목록에 따라 달라진다.
  거부되면 어댑터 표와 역할 파일을 함께 고친다 (`check-adapters.py` 가 불일치를 잡는다)
- Linear API(`get_issue`/`get_project`)가 `blockedBy`·진행률(%)을 응답 필드로 노출하지
  않아 해당 항목은 자동 검증 대신 사용자 육안 확인에 의존한다
- H2 경로(Fan-out/Fan-in)와 Phase 4 의 실제 에이전트 dispatch 는 다양한 실전 사례로
  검증이 누적되는 중이다

