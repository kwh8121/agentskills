# agentskills

에이전트 하네스용 스킬 모음. 각 최상위 폴더가 **독립적으로 설치 가능한 스킬 하나**다.
설치는 파일 복사이며 빌드 단계가 없다.

| 스킬 | 무엇을 하는가 | 동작 하네스 |
|---|---|---|
| [`harness-architect`](./harness-architect) | 개발 업무를 6축으로 프로파일링해 **최소 하네스(H0~H3)** 를 판정하고, 실행 계약(HarnessSpec)을 산출해 승인받은 뒤 그 구조대로 실행한다. 도구 경계를 역할 선언 + 훅으로 이중 강제하고 진행 상황을 Linear 에 남길 수 있다. | Claude Code · Codex · OpenCode |

---

## 설치

```bash
# 클론과 설치는 한 줄로 잇는다 — 클론이 실패하면 install.sh 도 돌지 않게.
# 대상 경로는 인자로 넘긴다(cd 불필요). 임시 디렉터리는 재실행 대비 먼저 지운다
# (git clone 은 비어있지 않은 대상에 exit 128 로 실패한다).
rm -rf /tmp/agentskills && \
git clone --depth 1 https://github.com/kwh8121/agentskills.git /tmp/agentskills && \
bash /tmp/agentskills/harness-architect/install.sh /path/to/your-project              # 하네스 자동 감지

#   ... install.sh /path/to/your-project --harness codex      # 하네스 명시
#   ... install.sh /path/to/your-project --no-merge           # 기존 설정을 건드리지 않음
```

`install.sh` 는 소스 트리가 온전한지(부분 클론 방지) 먼저 확인하고, 배치가 끝나면
**기대 산출물이 실제로 생겼는지 검증한 뒤에** 성공을 알린다. 어느 쪽이든 실패하면
non-zero 로 종료하므로 위처럼 `&&` 로 이어도 안전하다.

기존 설정 파일은 **덮어쓰지 않고 우리 항목만 추가**한다. 백업(`.bak-<타임스탬프>`)을 남기고,
재실행해도 중복되지 않으며, 깨진 JSON 은 손대지 않고 붙일 내용을 출력한다.
`.claude/` · `.codex/` · `.opencode/` 디렉터리가 **이미 있어도 안전하다** — 기존 역할 파일·
플러그인·설정은 보존되고, 배치 경로(아래 표)는 현재 설치본의 정식 출력이다.

배치되는 것과 **하네스별로 반드시 해야 하는 후속 조치**:

<table>
<tr><th>하네스</th><th>배치 경로</th><th>후속 조치 (안 하면 가드가 동작하지 않는다)</th></tr>
<tr>
<td><b>Claude Code</b></td>
<td><code>.claude/skills/harness-architect/</code><br><code>.claude/agents/*.md</code><br><code>.claude/settings.json</code></td>
<td>없음. <code>settings.json</code> 이 이미 있으면 install.sh 가 <b>덮어쓰지 않고 우리 훅만 추가</b>한다(백업 후 병합, 재실행해도 중복 없음).</td>
</tr>
<tr>
<td><b>Codex</b></td>
<td><code>.codex/skills/harness-architect/</code><br><code>.codex/agents/*.toml</code><br><code>.codex/hooks.json</code></td>
<td>
① <code>~/.codex/config.toml</code> 에 <code>[features] hooks = true</code>, <code>multi_agent = true</code><br>
② <b>훅 신뢰 등록</b> — install.sh 가 출력하는 <code>[hooks.state.…]</code> 블록을 <code>~/.codex/config.toml</code> 끝에 붙인다. <b>등록되지 않은 프로젝트 훅은 신뢰된 경로에서도 조용히 무시된다.</b> <code>hooks.json</code> 은 이미 있으면 자동 병합되고, 신뢰 블록도 병합 결과 기준으로 다시 계산된다.
</td>
</tr>
<tr>
<td><b>OpenCode</b></td>
<td><code>.opencode/skills/harness-architect/</code><br><code>.opencode/agent/*.md</code><br><code>.opencode/plugin/harness-guard.js</code><br><code>opencode.json</code></td>
<td>없음. install.sh 가 <code>opencode.json</code> 의 <code>plugin</code> 배열에 <code>harness-guard.js</code> 를 등록한다 — <b>있으면 병합, 없으면 최소 파일(<code>$schema</code>+<code>plugin</code>) 생성</b>. OpenCode 는 플러그인을 자동 로드하지 않아 등록이 없으면 2차 가드(셸·MCP 우회 차단)가 죽는다. <code>--no-merge</code> 면 생성을 생략하므로 직접 등록해야 한다.</td>
</tr>
</table>

### 공통 사전 요건

| 요건 | 없으면 |
|---|---|
| Bash + POSIX `awk`/`grep`, Python 3 | 스크립트가 돌지 않는다 |
| **superpowers** (필수 스킬 11종) | H0 도 `verification-before-completion` 이 필수라 **완전히 끊긴다.** Phase 1 이 감지해 exit 4 로 중단하며 그 하네스의 설치 명령을 알려준다 |
| PyYAML (`pip install pyyaml`) — 선택 | `validate-spec.py` 가 exit 2. 승인 게이트를 사람이 대신 확인 |
| Linear MCP — 선택 | `tracking.provider: linear` 불가 (`none` 이면 정상) |

superpowers 설치: Claude Code `/plugin install superpowers@claude-plugins-official` ·
Codex `codex plugin add superpowers` ·
OpenCode `opencode.json` 의 `plugin` 에 `superpowers@git+https://github.com/obra/superpowers.git`

---

## 설치 확인

`<skill_dir>` 은 `.claude/skills/harness-architect` · `.codex/…` · `.opencode/…` 중 해당 하네스 경로다.
첫 명령이 알려준다.

```bash
bash <skill_dir>/scripts/detect-harness.sh          # harness / skill_dir / adapter 출력
bash <skill_dir>/scripts/check-superpowers.sh       # 필수 스킬 11종 (exit 1 이면 설치 명령을 알려준다)
bash <skill_dir>/scripts/init-workspace.sh          # 게이트 감지 → _workspace/harness/gates.tsv

# 읽기 전용 가드가 실제로 거부하는가 — "permissionDecision":"deny" 가 나와야 한다
echo '{"agent_type":"reviewer","tool_name":"Write","tool_input":{"file_path":"src/x.ts"}}' \
  | python3 <skill_dir>/scripts/guard-readonly.py
```

`init-workspace.sh` 의 종료 코드: **0** 게이트 감지 성공 / **3** 스택 미감지(사용자에게 물어야 함) /
**4** superpowers 미설치(진행 불가).

---

## 사용법

설치한 프로젝트에서 하네스를 열고 **개발 업무를 자연어로** 맡기면 된다
("이 저장소에 파일 업로드 기능 추가해줘", "인증 모듈 리팩터링해줘").
코드 변경이 없는 질문·조사에는 쓰지 않는다 — 하네스는 실행 계약이지 대화 도구가 아니다.

진행 흐름과 사용자가 개입하는 지점:

| Phase | 하는 일 | 사용자 |
|---|---|---|
| −2 | 하네스 판정, 어댑터 로드 | — |
| −1 | 이전 세션 재개 판정 | Phase 3 이상·불일치·하네스 변경이면 **재개/재판정/폐기 선택** |
| 0 | task 6필드 정규화 | 레벨·Human Gate 가 뒤집히는 질문에만 답 |
| 1 | 결정론적 게이트 탐지 | 스택 미감지 시 **검증 명령을 알려준다** (스킬은 지어내지 않는다) |
| 2 | 6축 프로파일링 → H0~H3 판정 | — |
| 3 | HarnessSpec 산출 + 기계 검증 | **한 화면 요약을 보고 승인** ← 여기 전에는 에이전트가 뜨지 않는다 |
| 4 | 레벨별 실행 (구현 → 게이트 → 리뷰) | — |
| 5 | 최종 게이트 → 완료 검증 → Human Gate | 되돌릴 수 없는 변경이면 **증거를 보고 최종 승인** |

승인 시 확인할 항목은 [harness-architect/README.md 의 "승인 게이트 확인"](./harness-architect#승인-게이트-확인).

---

## 테스트

새 프로젝트에서 제대로 도는지 보려면:

1. 위 **설치 확인** 4개 명령이 전부 통과하는지 본다.
2. 작은 실제 작업(오타 수정 + 테스트 1건 같은 H0/H1 급)을 맡기고 아래를 확인한다.

| 확인할 것 | 정상 |
|---|---|
| 스킬이 트리거되는가 | Phase −2 의 `detect-harness.sh` 가 먼저 돈다 |
| 승인 전 스폰 | Phase 3 승인 **전에 에이전트가 뜨면 버그** |
| 게이트 판정 | 린트·테스트 통과 여부를 AI 가 아니라 `run-gates.sh` 의 exit code 가 정한다 |
| 게이트 미감지 | 명령을 지어내지 않고 사용자에게 묻는다 |
| 역할 경계 | reviewer 에게 소스 수정을 시키면 거부된다 |
| 진행 기록 | `_workspace/harness/state.json` 에 phase·harness 가 남는다 |
| 역할 7종 로드 (OpenCode) | `opencode agent` 목록에 7종이 보인다 |

저장소를 수정했다면 커밋 전에 `harness-architect/` 에서:

```bash
python3 core/scripts/check-adapters.py     # 세 하네스 어댑터의 파리티
for f in core/examples/*.yaml; do python3 core/scripts/validate-spec.py "$f"; done
```

---

## 알아둘 한계

- 가드는 **샌드박스가 아니라 규율 장치다.** 셸을 파싱하지 않고 쓰기 구문을 패턴으로 찾으므로
  변수 확장·base64·인터프리터 경유는 잡지 못한다.
- **강제 수준은 하네스마다 다르다.** Codex 는 훅 신뢰 등록 전까지, OpenCode 는 가드 플러그인
  등록 전까지 셸·MCP 우회를 막지 못한다. 하네스별 표는
  [`core/references/catalog.md`](./harness-architect/core/references/catalog.md).
- MCP 쓰기 도구는 **이름 패턴**(write/edit/patch/replace/…)으로 판정한다. 그 어휘를 쓰지 않는
  MCP 쓰기 도구는 통과한다.
- 어댑터의 `tier_map` 모델 이름은 설치 환경의 모델 허용 목록에 따라 다르다. 거부되면
  어댑터 문서와 역할 파일을 함께 고치면 되고, 어긋나면 `check-adapters.py` 가 잡는다.

자세한 설계·판정 기준·Linear 연동은 [harness-architect/README.md](./harness-architect),
저장소 규약과 불변식은 [CLAUDE.md](./CLAUDE.md).
