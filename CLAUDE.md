# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 언어 및 커뮤니케이션 규칙

- **기본 응답 언어**: 한국어
- **코드 주석 / 커밋 메시지 / 문서화**: 한국어
- **변수명 / 함수명 / 스킬 id / 에이전트 id / 필드명**: 영어 (코드·스키마 표준 준수)

## 저장소 성격

에이전트 하네스용 **스킬 모음**이다. 애플리케이션이 아니라 배포 산출물의 저장소다.

- 최상위 폴더 하나 = 독립적으로 설치 가능한 스킬 하나. 현재는 `harness-architect/` 뿐이다.
- 설치는 `bash harness-architect/install.sh <대상> [--harness claude|codex|opencode]` 다.
  하는 일은 **파일 복사 + 설정 파일 병합**뿐이고 **빌드 단계가 없다.**
  설정 병합은 `scripts/merge-config.py` 가 하며 덮어쓰지 않는다 (백업 후 추가, 멱등,
  깨진 JSON 은 손대지 않음, `--no-merge` 로 끌 수 있음). 유일한 예외로,
  프로젝트에 `opencode.json` 이 없으면 가드 플러그인만 담은 최소 파일을 생성한다
  (OpenCode 는 플러그인을 자동 로드하지 않아, 이게 없으면 2차 가드가 죽는다).
- **절대 경로 하드코딩 금지.** 모든 스크립트·문서·frontmatter 경로는 상대 경로여야
  통째로 복사했을 때 대상 저장소에서 그대로 동작한다. `$CLAUDE_PROJECT_DIR` 은 예외.
- 런타임: Bash + POSIX `awk`/`grep`, Python 3, 선택적 PyYAML. 패키지 매니저·의존성 파일 없음.
  (OpenCode 가드 플러그인만 Node 를 쓰는데, 이는 그 하네스가 이미 제공하는 런타임이다.)
- 원격 저장소 이름은 `agentskills` (README 의 표기), 로컬 디렉터리는 `agent-architect`.

## 검증 (이 저장소에는 테스트 러너가 없다 — 아래가 전부다)

스킬을 수정하면 `harness-architect/` 를 작업 디렉터리로 두고 다음을 돌린다:

```bash
cd harness-architect

# 0) 어댑터 파리티 — 세 하네스가 같은 역할·tier·경계를 선언하는가
#    (manifest.tsv 와 claude/·codex/·opencode/ 트리의 일치를 강제한다)
python3 core/scripts/check-adapters.py

# 1) HarnessSpec 예제 4종이 계약 검증기를 통과하는지 (PyYAML 필요, 없으면 exit 2)
for f in core/examples/*.yaml; do
  python3 core/scripts/validate-spec.py "$f"
done

# 2) 읽기 전용 가드가 세 하네스 페이로드를 전부 거부하는지 — "permissionDecision":"deny"
echo '{"agent_type":"reviewer","tool_name":"Write","tool_input":{"file_path":"src/x.ts"}}' \
  | python3 core/scripts/guard-readonly.py
echo '{"source":{"subagent":{"thread_spawn":{"agent_type":"orchestrator"}}},"tool_name":"Bash","tool_input":{"command":"sed -i s/a/b/ src/x.ts"}}' \
  | python3 core/scripts/guard-readonly.py --harness codex
echo '{"agent":"reviewer","tool":"write","args":{"filePath":"src/y.ts"}}' \
  | python3 core/scripts/guard-readonly.py --harness opencode

# 2-1) 허용 범위 안의 mkdir/touch/rm 은 통과해야 한다 (issue #1 회귀 — 출력 없어야 함)
echo '{"agent_type":"reviewer","tool_name":"Bash","tool_input":{"command":"mkdir -p _workspace/harness/review"}}' \
  | python3 core/scripts/guard-readonly.py

# 3) 세션 재개 판정이 동작하는지 — state 가 없는 새 저장소이므로 exit 0
python3 core/scripts/resume-check.py; echo "exit=$?"

# 4) 실제 배치 — 임시 프로젝트에 깔아 하네스별 경로가 성립하는지 본다
T=$(mktemp -d); (cd "$T" && git init -q)
bash install.sh "$T" --harness codex
test -f "$T/.codex/skills/harness-architect/SKILL.md" -a -f "$T/.codex/hooks.json"   # 산출물 검증
(cd "$T" && bash .codex/skills/harness-architect/scripts/detect-harness.sh)
(cd "$T" && bash .codex/skills/harness-architect/scripts/check-superpowers.sh --harness codex)
(cd "$T" && bash .codex/skills/harness-architect/scripts/init-workspace.sh)   # exit 0/3/4

# 4-1) 부분 클론 방어 — 소스 트리가 잘리면 install.sh 는 조용히 빈 배치를 하지 않고 멈춘다 (issue #2)
B=$(mktemp -d); mkdir -p "$B/harness-architect"; cp install.sh "$B/harness-architect/"
T2=$(mktemp -d); (cd "$T2" && git init -q)
bash "$B/harness-architect/install.sh" "$T2" --harness opencode; test "$?" -eq 2   # exit 2 여야 함
test ! -e "$T2/.opencode"   # 빈 디렉터리조차 남기지 않는다

# 4-2) OpenCode 가드 활성 — opencode.json 이 없어도 최소 파일을 만들어 플러그인을 등록한다 (issue #3)
T3=$(mktemp -d); (cd "$T3" && git init -q)
bash install.sh "$T3" --harness opencode | grep -q '가드: .*활성'   # 생성 + JSON 파싱으로 등록 확인
python3 -c "import json,sys; d=json.load(open('$T3/opencode.json')); sys.exit(0 if list(d)==['\$schema','plugin'] and d['plugin']==['./.opencode/plugin/harness-guard.js'] else 1)"
bash install.sh "$T3" --harness opencode | grep -q '이미 최신'      # 재실행 멱등
T4=$(mktemp -d); (cd "$T4" && git init -q)
bash install.sh "$T4" --harness opencode --no-merge 2>&1 | grep -q '⚠ 가드'   # --no-merge → 생성 안 함, 경고
test ! -e "$T4/opencode.json"
# 문자열만 있고 유효한 plugin 항목이 아니면 "활성" 으로 오판하지 않는다
T5=$(mktemp -d); (cd "$T5" && git init -q)
printf '{"plugin":[],"note":"not ./.opencode/plugin/harness-guard.js"}\n' > "$T5/opencode.json"
bash install.sh "$T5" --harness opencode --no-merge 2>&1 | grep -q '⚠ 가드'
```

단일 spec 검증: `python3 core/scripts/validate-spec.py _workspace/harness/spec.yaml --gates _workspace/harness/gates.tsv`

`_workspace/` 는 하네스 실행 산출물이 쌓이는 곳이며 커밋하지 않는다.

## harness-architect 아키텍처

### 무엇인가

개발 업무를 자연어로 받아 **작업 복잡도에 맞는 최소 하네스(H0~H3)를 매번 새로 판정**하는
라우터 **스킬**(Agent 가 아니다). 분석·판정·구성안 생성은 스킬이 하고, 실제 작업은
카탈로그의 Agent 7종이 한다. 절차적 지식은 직접 쓰지 않고 `superpowers` 스킬에 위임한다.

**Claude Code · Codex · OpenCode 세 하네스에서 동작한다.** 엔진은 한 벌(`core/`)이고,
하네스마다 다른 것은 어댑터에만 있다.

### 코어와 어댑터

```
core/         SKILL.md · references/ · roles/ · schemas/ · examples/ · scripts/   ← 하네스 무관
claude/.claude/    agents/*.md      settings.json          ← 어댑터
codex/.codex/      agents/*.toml    hooks.json             ← 어댑터
opencode/.opencode/ agent/*.md      plugin/harness-guard.js ← 어댑터
```

**코어는 하네스 고유 어휘를 쓰지 않는다.** 도구 이름·모델 이름·dispatch 문법·훅 경로는
전부 `core/references/adapters/<하네스>.md` 가 정의하고, `SKILL.md` 는 키 이름으로만 참조한다
(`skill_dir`, `dispatch`, `tier_map`, `skill_call`, `superpowers_roots`, `guard`, `worktree`).
코어를 고쳐야 새 하네스가 붙는다면 어댑터 경계가 새는 것이므로, 새는 부분을 먼저 키로 승격한다.

### 실행 흐름 (`SKILL.md` 의 Phase −2~5)

0. **Phase −2** — `detect-harness.sh` 로 하네스를 판정하고 `skill_dir`·어댑터 문서를 해석한다.
   판정 불가(exit 3)면 사용자에게 묻는다. 추측하지 않는다.
1. **Phase −1** — `resume-check.py` 로 세션 재개 판정. exit 0(재개 없음)·10(자동 재개 후보,
   Phase ≤ 2)·11(사람 판단 — Phase 3 이상·불일치·손상·**하네스 변경**)·12(완료된 이전 작업).
   승인은 세션을 넘어 상속되지 않는다 — Phase 3 이상에서 재개하면 새로 승인받는다.
2. **Phase 0** — `task` 6필드 정규화. 목표가 불명확하면 `superpowers:brainstorming` 으로 이탈.
3. **Phase 1** — `init-workspace.sh` 로 결정론적 게이트(`gates.tsv`) 탐지. 명령을 지어내지 않는다.
4. **Phase 2** — `references/profiling.md` 6축 판정 → `references/routing.md` 5스텝 판정 트리로 레벨 결정.
5. **Phase 3** — `schemas/harness-spec.yaml` 형식으로 `_workspace/harness/spec.yaml` 작성 →
   `validate-spec.py` (exit 1 이면 승인 요청 금지) → **한 화면 요약으로 사용자 승인**.
6. **Phase 4** — 레벨별 실행. **승인 전 에이전트 스폰 금지.**
7. **Phase 5** — 최종 게이트 → `superpowers:verification-before-completion` → Human Gate.

각 Phase 전환·역할 완료마다 `checkpoint.py` 가 `_workspace/harness/state.json` 에 진행을
원자적으로 기록한다 (`run-gates.sh`·`init-workspace.sh` 는 자동으로, 나머지는 SKILL.md 절차대로).
기록 실패는 하네스를 멈추지 않지만 stderr 로 알린다.

### 레벨 판정의 핵심

- 판정 트리의 갈림길은 **STEP 2**: "구현자 한 명이 한 번에 끝까지 들고 갈 수 있는가".
  `parallelism: none` 은 "단위가 1개"라는 뜻이 아니라 "동시에 못 돈다"는 뜻이다.
- 레벨을 올리려면 **한 단계 아래가 왜 안 되는지** 한 문장을 쓸 수 있어야 한다 (`harness.rationale`).
- `risk` 는 레벨을 바꾸지 않는다 — reviewer 유무와 `max_loops` 만 바꾼다.
- Human Gate 는 `risk` 가 아니라 STEP 5(`side_effect: irreversible` · `production` · 시크릿 · 삭제)가 정한다.

### 토큰 절약의 3대 장치

1. **결정론적 게이트 분리** — 포맷·린트·타입·테스트·빌드는 `run-gates.sh` 의 exit code 가 판정한다.
   AI 리뷰어에게 게이트 실패를 보내지 않는다.
2. **컨텍스트 예산** — 에이전트별 `required`/`optional`/`forbidden` (`references/context-budget.md`).
   모든 에이전트의 `forbidden` 에 `full_repository_dump` 가 들어간다. 보고서는 본문이 아니라 경로로 넘긴다.
3. **고정 카탈로그** — 역할 정의를 매번 새로 만들지 않고 7종에서 고른다.

### 도구 경계 이중 강제

역할 선언의 `capabilities`(→ 하네스별 도구 목록)가 1차 경계다
(`reviewer`·`orchestrator` 에 편집 능력 없음). `scripts/guard-readonly.py` 를 그 하네스의
pre-tool 훅으로 걸어 **쓰기 대상 경로**로 2차 판정한다 (`reviewer`·`orchestrator` 는
`_workspace/` 아래만, `dependency-mapper` 는 아무 데도 못 씀).
셸을 파싱하지 않으므로 샌드박스가 아니라 규율 장치다.

**강제 수준은 하네스마다 다르고, 그 차이를 문서가 숨기지 않는다** — Codex 는 훅 신뢰·승인
전까지, OpenCode 는 가드 플러그인 등록 전까지 셸 우회를 막지 못한다
(`references/catalog.md` 의 하네스별 표).

## 여러 파일에 걸친 불변식 (수정 시 전부 동기화)

harness-architect 는 "진실의 원천"이 코드·스키마·문서·테스트에 **중복 선언**되어 있고,
검증기가 그 일치를 강제한다. 하나를 바꾸면 나머지도 바꿔야 한다.

| 개념 | 정의 위치 (전부 일치해야 함) |
|---|---|
| 에이전트 7종 (`CATALOG`) | `core/roles/manifest.tsv` **(원천)** · `core/scripts/validate-spec.py` · `core/scripts/checkpoint.py` · `core/references/catalog.md` · 어댑터 트리 3종 |
| 역할별 tier·capabilities·write_scope | `core/roles/manifest.tsv` **(원천)** · `core/references/catalog.md` 표 · 어댑터 트리 3종 → `check-adapters.py` 가 강제 |
| tier→모델 매핑 (`fast`/`standard`/`deep`) | `core/references/adapters/<하네스>.md` 의 `tier_map` **(원천)** · 각 어댑터 트리의 역할 파일 `model` → `check-adapters.py` 가 강제 |
| 어댑터 필수 키 7종 | `core/references/adapters/README.md` · `core/scripts/check-adapters.py` 의 `REQUIRED_KEYS` · 어댑터 문서 3종의 `## <키>` 절 |
| 하네스 감지 규약 | `core/scripts/detect-harness.sh` **(원천)** · `core/scripts/checkpoint.py` 의 `detect_harness()` 가 이 스크립트를 호출 · `core/references/adapters/README.md` 표 |
| 자동 재개 상한 (`AUTO_MAX_PHASE = 2`) | `core/scripts/resume-check.py` · `core/SKILL.md` Phase −1 · README |
| 재개 판정 exit code (0 / 10 / 11 / 12) | `core/scripts/resume-check.py` · `core/SKILL.md` Phase −1 표 · README "중단하면 재개한다" 표 |
| state 스키마 버전 (`schema_version` / `SCHEMA_VERSION`, 현재 1) | `core/scripts/checkpoint.py` · `core/scripts/resume-check.py`. `harness` 는 **선택 필드**라 버전을 올리지 않았다 — 구버전 state(필드 없음)는 그대로 재개된다 |
| 허용 스킬 목록 (`ALLOWED_SKILLS` / `CONTROLLER_ONLY_SKILLS`) | `core/scripts/validate-spec.py` · `core/references/catalog.md` 매핑표 |
| 재라우팅 매핑 (`escalation`) | `core/scripts/validate-spec.py` · `core/references/routing.md` 표 · `core/schemas/harness-spec.yaml` · `core/roles/orchestrator.md` |
| 레벨↔패턴 / 레벨↔추적모드 / `max_loops` 상한 / `max_workers` 상한 | `core/scripts/validate-spec.py` · `core/schemas/harness-spec.yaml` · README |
| 레벨↔필수 controller 스킬 (`LEVEL_REQUIRED_CONTROLLER_SKILLS`) | `core/scripts/validate-spec.py` · `core/references/routing.md` H2/H3 절차 · `core/references/catalog.md` 매핑표 · `core/examples/h2-*.yaml`·`h3-*.yaml` |
| 게이트 tier 3종 (`fast`/`feature`/`final`) 과 스크립트 이름→tier 매핑 | `core/scripts/detect-stack.sh` · `core/scripts/run-gates.sh` · `core/scripts/validate-spec.py` 의 `TIERS` (에이전트 tier `TIERS_MODEL` 과 혼동 금지) |
| 읽기 전용 역할과 쓰기 허용 범위 | `core/roles/manifest.tsv` 의 `write_scope` **(원천)** · `core/scripts/guard-readonly.py` 가 이 파일을 읽는다(`DEFAULT_SCOPES` 는 폴백) · `core/references/catalog.md` 강제 수준 표 |
| 우리 훅을 알아보는 표식 (`MARKER` = `harness-architect/scripts/guard-readonly.py`) | `core/scripts/merge-config.py` · `core/scripts/codex-hook-trust.py` — 병합 멱등성과 신뢰 블록 필터가 같은 문자열에 의존한다 |
| 필수 superpowers 스킬 목록 (`REQUIRED_SKILLS`) | `core/scripts/check-superpowers.sh` · `core/scripts/validate-spec.py` 의 `ALLOWED_SKILLS`(내장 `security-review` 제외) · `core/references/catalog.md` 매핑표 |
| superpowers 탐지 경로·설치 명령 | `core/references/adapters/<하네스>.md` 의 `superpowers_roots` **(원천)** · `core/scripts/check-superpowers.sh` 의 `candidates` · `core/scripts/init-workspace.sh` 의 exit 4 안내 |

`validate-spec.py` 는 `yaml.safe_load` 성공("문법이 YAML")을 넘어 카탈로그 밖 에이전트,
`tier`/`model` 누락, 축 모순(`coupling: high` + `parallelism ≠ none`), **수용 기준에 대응하는 게이트 부재**,
Human Gate 누락, H3 `escalation` 계약 누락 등을 거부한다. 새 검사를 추가할 때 이 파일의
상단 상수(`CATALOG`, `ENUMS`, `TIERS_MODEL`, `ALLOWED_SKILLS` 등)부터 본다.

## 외부 의존성

| 의존 | 없으면 |
|---|---|
| `superpowers` (필수 스킬 11종) | H0 도 `verification-before-completion` 이 필수라 완전히 끊긴다. Phase 1 의 `check-superpowers.sh` 가 **하네스별 경로**를 보고, 없으면 `init-workspace.sh` 가 exit 4 로 즉시 중단하며 그 하네스의 설치 명령을 제시한다 (버전이 아니라 **필수 스킬 11종의 존재**로 판정한다 — 서로 다른 버전이 공존할 수 있다) |
| PyYAML (`pip install pyyaml`) | `validate-spec.py` 가 exit 2 — 승인 게이트를 사람이 대신 확인. 세션 재개(`checkpoint.py`·`resume-check.py`)는 표준 라이브러리 `json` 만 쓰므로 영향 없다 |
| Codex `[features] hooks`·`multi_agent` | 각각 가드 훅과 서브에이전트 dispatch 가 통째로 없어진다 |
| OpenCode 가드 플러그인 등록 | 셸 경유 우회를 막지 못한다. 선언적 경계(`tools`/`permission`)는 그대로 동작 |
| Linear MCP | `tracking.provider: linear` 불가. `none` 이면 정상 동작 |

## 불변 규칙 (스킬 로직을 건드릴 때)

- **최소 하네스 우선.** 승격에는 근거 문장이 필요하고, 강등(under-orchestration)도 똑같이 오답이다.
- **역할을 새로 만들지 않는다.** 반복 Procedure 는 Agent 가 아니라 Skill 이다.
- **코어에 하네스 고유 어휘를 쓰지 않는다.** 도구 이름·모델 이름·훅 경로가 필요해지면
  어댑터 키로 승격하고 `check-adapters.py` 에 검사를 추가한다.
- **역할을 세 벌 손으로 고치지 않는다.** `core/roles/manifest.tsv` 를 고치고 어댑터 트리를
  거기에 맞춘 뒤 `check-adapters.py` 로 확인한다.
- **게이트 명령을 지어내지 않는다.** 감지 실패 시 사용자에게 묻는다.
- **컨텍스트는 경로로 전달한다.** dispatch 시 tier→모델을 항상 명시한다.
- **자동 커밋 금지 / `_workspace/` 보존.** `core/scripts/harness-paths.sh` 가 `_workspace/` 를
  메인 워크트리 루트에 고정한다 (H2/H3 이 worktree 로 이동해도 산출물이 한곳에 남게).
  게이트 *명령*의 실행 디렉터리는 고정하지 않는다 — 검증 대상은 현재 트리의 코드다.
- **격리와 해제는 쌍이다.** worktree 를 만드는 레벨(H2·H3)은 정리 스킬까지 함께 선언한다.
  정리 시점은 **통합 결과**가 정하고 Linear 상태가 정하지 않는다 (`Canceled` 는 강등을
  포함하고 `Done` 은 통합보다 먼저 찍힌다).
- **진행을 기록한다.** Phase 전환·역할 완료마다 `checkpoint.py` 로 `state.json` 에 남긴다.
  기록 실패는 멈추지 않지만 조용히 넘기지도 않는다 (stderr 로 알린다).
- **승인은 세션을 넘어 상속되지 않는다.** Phase 3 이상에서 재개하면 `resume-check.py` 가
  exit 11 로 사람에게 넘긴다. **하네스가 바뀌어도 마찬가지다** — dispatch 규약과 가드
  강제 수준이 달라지므로 새 하네스 기준으로 다시 승인받는다.
- **손상된 state 는 추측으로 복구하지 않는다.** `resume-check.py` 는 exit 11 로,
  `checkpoint.py` 는 exit 3 으로 멈춘다 (원본 보존).
- **못 막는 것을 막는다고 쓰지 않는다.** 하네스별 강제 수준 표는 실제 동작을 그대로 적는다.
- **Linear 쓰기는 컨트롤러만.** 워커·orchestrator 는 상태 토큰만 반환한다. H0 은 추적하지 않는다.
