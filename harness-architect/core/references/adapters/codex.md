# 어댑터 — Codex CLI

검증 기준: `codex-cli 0.149.1`.

## skill_dir

```
.codex/skills/harness-architect
```

```bash
python3 .codex/skills/harness-architect/scripts/resume-check.py
bash    .codex/skills/harness-architect/scripts/init-workspace.sh
```

역할 본문은 `.codex/skills/harness-architect/roles/<id>.md`,
역할 정의 파일(어댑터)은 `.codex/agents/<id>.toml` 다.

## dispatch

`spawn_agent` 로 띄우고 `wait_agent` 로 받는다. **`~/.codex/config.toml` 에
`[features] multi_agent = true` 가 필요하다** — 없으면 도구 자체가 없다.

```
spawn_agent { agent_type: "implementer", model: "gpt-5.5",
              reasoning_effort: "medium", fork_turns: "none" }
```

- `fork_turns: "none"` 을 쓴다. 기본값 `"all"` 은 전체 대화를 자식에게 복사해
  컨텍스트 예산(`references/context-budget.md`)을 무너뜨린다.
- **`model` 과 `reasoning_effort` 를 항상 함께 명시한다.** `model` 만 주면 추론 강도가
  그 모델의 기본값으로 조용히 되돌아간다.
- 재작업 라운드는 `followup_task` 로 **같은 자식을 재개한다.** 새 구현자를 다시 띄우지 않는다.
- 대기: `wait_agent` 는 폴링이 아니라 이벤트 구독이다. 할 일이 남았으면 기다리지 말고,
  정말 유휴일 때만 `timeout_ms` 300000~600000 로 길게 한 번 기다린다.
- 목록·정리: `list_agents`. V2 에는 `close_agent` 가 없다(자동 축출).
- 모델 이름은 세션의 spawn 허용 목록에 있는 것만 쓴다. 표에서 베껴 넣지 않는다.

## tier_map

| tier | model | reasoning_effort |
|---|---|---|
| `fast` | `gpt-5.4-mini` | `low` |
| `standard` | `gpt-5.5` | `medium` |
| `deep` | `gpt-5.5` | `high` |

허용 목록은 모델 프리셋마다 다르다. `spawn_agent` 가 모델을 거부하면 **이 표만 고친다** —
역할 정의(`.codex/agents/*.toml`)의 `model`/`model_reasoning_effort` 도 함께 맞춘다.

기계 수준 backstop 을 `~/.codex/config.toml` 에 두면 누락된 spawn 도 안전한 티어로 떨어진다:

```toml
[agents]
default_subagent_model = "gpt-5.5"
default_subagent_reasoning_effort = "medium"
```

## skill_call

스킬은 `.codex/skills/<name>/SKILL.md` 에서 로드된다. 산문으로 지시한다:

```
**REQUIRED SUB-SKILL:** `.codex/skills/brainstorming/SKILL.md` 를 읽고 그대로 따른다.
```

`$name` 워크플로 호출 규약을 쓰는 설치본에서는 `$brainstorming` 형태도 동작한다 —
**둘 중 이 프로젝트에 실제로 설치된 형태를 확인하고 쓴다.**

## superpowers_roots

탐지 경로:

```
${CODEX_HOME:-$HOME/.codex}/skills
.codex/skills
```

미설치 시 제시할 명령 (**사용자가 직접 실행한다**):

```
codex plugin add superpowers        # 또는 저장소의 .codex-plugin/ 을 스킬 경로에 배치
```

superpowers 저장소는 `.codex-plugin/plugin.json` 에 `"skills": "./skills/"` 를 선언하므로
Codex 플러그인으로 설치하면 필수 11종이 그대로 들어온다.

> 이 머신 기준으로 Codex 에는 **필수 11종이 설치돼 있지 않다.** `init-workspace.sh` 가
> exit 4 로 중단하는 것이 정상 동작이다 — 절차를 내장해 우회하지 않는다.

## guard

`.codex/hooks.json` 에 등록한다. **이벤트 이름과 JSON 구조가 Claude Code 와 같다.**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .codex/skills/harness-architect/scripts/guard-readonly.py --harness codex"
          }
        ]
      }
    ]
  }
}
```

- 페이로드: `tool_name` / `tool_input` / `hook_event_name` (Claude 와 동일).
  역할 식별자는 `agent_role` · `agentRole` · `agent_type` · `agentType` 중 하나거나,
  `source.subagent.thread_spawn.*` 에 중첩돼 온다 — 가드가 네 자리를 전부 본다.
- 거부 출력: `hookSpecificOutput.permissionDecision = "deny"` + `permissionDecisionReason`
  (Claude 와 동일).
- 전제: `~/.codex/config.toml` 에 `[features] hooks = true`.

### 훅 신뢰 등록 (이 단계 없이는 가드가 동작하지 않는다)

**등록되지 않은 프로젝트 훅은 신뢰된 프로젝트 경로에서도 조용히 무시된다** — 실측으로 확인했다.
`~/.codex/config.toml` 에 아래 형식의 항목이 있어야 실행된다:

```toml
[hooks.state."<프로젝트>/.codex/hooks.json:pre_tool_use:0:0"]
trusted_hash = "sha256:..."
enabled = true
```

`trusted_hash` 는 훅 정의를 정규화한 JSON 의 sha256 이다:

```
sha256( JSON.stringify({ event_name, hooks:[{async, command, timeout, type}], matcher }) )
```

`scripts/codex-hook-trust.py <hooks.json>` 가 이 블록을 만들어 준다 (기존에 동작 중인 실제
항목을 바이트 단위로 재현하는 것을 확인했다). **스크립트는 출력만 하고 config.toml 을 고치지
않는다** — 훅 신뢰는 사용자가 명시적으로 내리는 결정이다.

`async`·`timeout` 기본값이 해시에 들어가므로 배포되는 `hooks.json` 은 두 값을 명시한다.
값을 바꾸면 해시가 달라져 블록을 다시 만들어야 한다.

**강제 수준: 조건부.** 위 등록 전까지 읽기 전용 경계는 역할 프롬프트 준수에만 의존한다 —
Codex 는 역할별 도구 목록도 강제하지 않기 때문이다.

## worktree

가능하다. 다만 Codex App/샌드박스 환경에서는 이미 외부 관리 worktree 안이거나 detached HEAD 일
수 있다. `superpowers:using-git-worktrees` 를 부르기 전에 읽기 전용으로 확인한다:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
BRANCH=$(git branch --show-current)
```

`GIT_DIR != GIT_COMMON` 이면 이미 linked worktree 다(생성하지 않는다).
`BRANCH` 가 비었으면 detached HEAD — 브랜치·푸시·PR 을 만들 수 없으므로 커밋까지만 하고
사람에게 넘긴다.
