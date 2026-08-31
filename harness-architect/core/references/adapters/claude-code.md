# 어댑터 — Claude Code

기준 하네스다. 나머지 두 하네스는 이 문서의 대응물을 각자의 방식으로 채운다.

## skill_dir

```
.claude/skills/harness-architect
```

스크립트 호출은 전부 이 접두사를 붙인다.

```bash
python3 .claude/skills/harness-architect/scripts/resume-check.py
bash    .claude/skills/harness-architect/scripts/init-workspace.sh
```

역할 본문은 `.claude/skills/harness-architect/roles/<id>.md`,
역할 정의 파일(어댑터)은 `.claude/agents/<id>.md` 다.

## dispatch

`Agent` 도구로 부른다. `subagent_type` 은 `.claude/agents/<id>.md` 의 `name` 과 같다.

```
Agent(subagent_type="implementer", model="sonnet", prompt="<브리핑>")
```

- **모델을 항상 명시한다.** 생략하면 세션의 가장 비싼 모델을 상속한다.
- 동시 실행: 한 응답에 여러 `Agent` 호출을 넣으면 병렬로 돈다.
  **파일을 쓰는 워커는 동시에 띄우지 않는다** (조사 역할만 허용).
- 결과 회수: 서브에이전트의 최종 응답이 그대로 돌아온다. 보고서는 본문이 아니라
  **경로로** 넘기게 프롬프트에 지시한다.

## tier_map

| tier | model |
|---|---|
| `fast` | `haiku` |
| `standard` | `sonnet` |
| `deep` | `opus` |

## skill_call

`Skill` 도구 또는 산문 지시.

```
Skill(skill="superpowers:brainstorming")
```

산문 표기 관례: `**REQUIRED SUB-SKILL:** Use superpowers:<name>`

## superpowers_roots

탐지 경로 (`scripts/check-superpowers.sh` 가 이 순서로 본다):

```
$CLAUDE_PLUGIN_ROOT
${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins
.claude/plugins
```

미설치 시 제시할 명령 (**사용자가 직접 입력한다 — 스킬이 대신 실행할 수 없다**):

```
/plugin install superpowers@claude-plugins-official
```

재시작은 필요 없다.

## guard

`.claude/settings.json` 의 `hooks.PreToolUse` 에 등록한다.

```json
{
  "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash|mcp__.*",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/skills/harness-architect/scripts/guard-readonly.py\"",
      "timeout": 10
    }
  ]
}
```

- 페이로드: `agent_type` / `tool_name` / `tool_input` (stdin JSON)
- 거부 출력: `hookSpecificOutput.permissionDecision = "deny"` + `permissionDecisionReason`

매처에 `mcp__.*` 가 반드시 들어간다 — 빠지면 MCP 쓰기 도구(`mcp__serena__replace_content` 등)가
훅에 도달조차 하지 않는다.

**강제 수준: 완전.** 역할 식별자가 페이로드에 있고 훅이 도구 실행 전에 거부할 수 있다.
`tools` frontmatter 가 1차 경계, 이 훅이 경로 기준 2차 판정이다.

## worktree

제약 없다. `superpowers:using-git-worktrees` 를 그대로 쓴다.
`_workspace/` 는 `scripts/harness-paths.sh` 가 메인 워크트리 루트에 고정한다.
