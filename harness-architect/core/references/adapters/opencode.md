# 어댑터 — OpenCode

검증 기준: `opencode 1.18.23`.

## skill_dir

```
.opencode/skills/harness-architect
```

```bash
python3 .opencode/skills/harness-architect/scripts/resume-check.py
bash    .opencode/skills/harness-architect/scripts/init-workspace.sh
```

역할 본문은 `.opencode/skills/harness-architect/roles/<id>.md`,
역할 정의 파일(어댑터)은 `.opencode/agent/<id>.md` 다 (`agent`, 단수).

## dispatch

`task` 도구로 부른다. 대상은 `.opencode/agent/<id>.md` 의 파일명이며 그 파일의
frontmatter 가 `mode: subagent` 여야 서브에이전트로 노출된다.

```
task(subagent_type="implementer", description="<한 줄>", prompt="<브리핑>")
```

- **모델은 역할 파일의 `model` 이 결정한다.** 호출부에서 tier 를 바꿔야 하면 역할 파일을
  고치지 말고 `opencode.json` 의 `agent.<id>.model` 로 덮어쓴다.
- 동시 실행: 한 응답에 여러 `task` 를 넣으면 병렬로 돈다. 파일을 쓰는 워커는 동시에 띄우지 않는다.
- 결과 회수: 서브에이전트의 최종 응답이 돌아온다. 보고서는 경로로 넘긴다.
- 설치 확인: `opencode agent` 로 7종이 보이는지 본다.

## tier_map

| tier | model |
|---|---|
| `fast` | `openai/gpt-5.4-mini` |
| `standard` | `openrouter/anthropic/claude-sonnet-5` |
| `deep` | `openrouter/anthropic/claude-opus-5` |

`provider/model` 문자열은 그 설치본이 인증한 프로바이더에 따라 다르다. 모델을 못 찾으면
**이 표와 역할 파일의 `model` 을 함께 고친다.** `opencode models` 로 실제 목록을 본다.

## skill_call

스킬은 `.opencode/skills/<name>/SKILL.md` 에서 로드된다. 산문으로 지시한다:

```
**REQUIRED SUB-SKILL:** `.opencode/skills/brainstorming/SKILL.md` 를 읽고 그대로 따른다.
```

superpowers 를 플러그인으로 설치한 경우 스킬 경로가 플러그인 쪽으로 등록되므로
(`config` 훅이 `skills.paths` 에 추가한다) 이름만으로도 로드된다.

## superpowers_roots

탐지 경로:

```
${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}/skills
$HOME/.opencode/skills
.opencode/skills
${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}/node_modules/superpowers/skills
node_modules/superpowers/skills
```

미설치 시 제시할 방법 (**사용자가 직접 편집·실행한다**): `opencode.json` 의 `plugin` 배열에 추가.

```json
{ "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"] }
```

## guard

두 겹이다.

**1차 — 선언적 경계 (역할 파일 frontmatter).** 이것이 주 방어선이다.

```yaml
tools:
  edit: false
  patch: false
  write: false
permission:
  edit: deny
```

`core/roles/manifest.tsv` 의 `capabilities` 가 이 맵을 결정한다.

**2차 — 플러그인 훅 (`.opencode/plugin/harness-guard.js`).** 경로 기준 판정을 더한다.

- `chat.params` / `chat.headers` 훅이 `{sessionID, agent}` 를 주므로 여기서
  세션→역할 맵을 만든다.
- `tool.execute.before` 는 `{tool, sessionID, callID}` + `output.args` 를 받는다.
  세션으로 역할을 찾아 `scripts/guard-readonly.py --harness opencode` 에 넘기고,
  거부되면 **throw 해서 도구 실행을 막는다.**

**MCP 도구 주의.** `tools`/`permission` 의 불리언 맵은 **MCP 도구를 덮지 않는다** —
`serena_replace_content` 로 reviewer 가 소스를 고치는 것을 실제로 관측했다. 그 경로는
2차 훅(가드의 이름 패턴 판정)만 막는다. 플러그인을 등록하지 않으면 MCP 쓰기가 열려 있다.

**강제 수준: 부분적.**
`tools`/`permission` 은 `edit`·`write` 계열을 확실히 막지만, `bash` 를 허용한 역할이
`sed -i`·리다이렉션으로 우회하는 것은 2차 훅을 설치해야 막힌다. 플러그인을 설치하지 않으면
`references/catalog.md` 강제 수준 표의 "훅이 차단" 행은 전부 "프롬프트 준수"로 내려간다.

## worktree

제약 없다. `superpowers:using-git-worktrees` 를 그대로 쓴다.
`_workspace/` 는 `scripts/harness-paths.sh` 가 메인 워크트리 루트에 고정한다.
