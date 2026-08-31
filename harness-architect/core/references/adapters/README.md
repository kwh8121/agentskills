# 하네스 어댑터 — 계약서

`SKILL.md` 는 하네스 어휘를 쓰지 않는다. 하네스마다 다른 것은 전부 이 폴더의 문서가 정의하고,
스킬 본문은 **키 이름으로만** 참조한다(`skill_dir`, `dispatch`, `tier_map` …).

실행 중인 하네스는 `scripts/detect-harness.sh` 가 판정한다. 판정된 하네스의 문서 하나만 읽는다.

| 하네스 | 문서 | 감지 신호 |
|---|---|---|
| Claude Code | [`claude-code.md`](claude-code.md) | `CLAUDE_PROJECT_DIR` · `CLAUDE_CONFIG_DIR` · `.claude/` |
| Codex CLI | [`codex.md`](codex.md) | `CODEX_SESSION_ID` · `CODEX_HOME` · `.codex/` |
| OpenCode | [`opencode.md`](opencode.md) | `OPENCODE_CONFIG_DIR` · `.opencode/` |

## 필수 키 7종

세 문서가 **전부** 아래 키를 같은 제목으로 채운다. `scripts/check-adapters.py` 가 강제한다.

| 키 | 무엇을 정의하는가 |
|---|---|
| `skill_dir` | 스크립트·references·roles 를 부를 때의 경로 접두사 |
| `dispatch` | 서브에이전트 호출 문법, 동시 실행 규약, 결과 회수 방법 |
| `tier_map` | `fast`/`standard`/`deep` → 그 하네스의 실제 모델(+추론 강도) |
| `skill_call` | superpowers 스킬을 호출하는 문법 |
| `superpowers_roots` | 설치 탐지 경로와 그 하네스의 설치 명령 |
| `guard` | 읽기 전용 가드의 배선 방법과 **실제 강제 수준** |
| `worktree` | git worktree 사용 가능 여부와 제약 |

## 새 하네스를 추가하려면

1. 이 폴더에 `<harness>.md` 를 만들고 위 7종을 채운다.
2. 어댑터 트리(`<harness>/`)에 역할 7종을 `core/roles/manifest.tsv` 기준으로 만든다.
3. `scripts/detect-harness.sh` 에 감지 규칙을, `install.sh` 에 배치 규칙을 추가한다.
4. `scripts/check-adapters.py` 가 통과해야 끝이다.

**코어(`SKILL.md`·`references/`·`schemas/`·`scripts/`·`roles/`)는 건드리지 않는다.**
코어를 고쳐야 새 하네스가 붙는다면 그것은 어댑터 경계가 새는 것이므로, 새는 부분을
먼저 키로 승격한다.
