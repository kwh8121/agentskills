# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 언어 및 커뮤니케이션 규칙

- **기본 응답 언어**: 한국어
- **코드 주석 / 커밋 메시지 / 문서화**: 한국어
- **변수명 / 함수명 / 스킬 id / 에이전트 id / 필드명**: 영어 (코드·스키마 표준 준수)

## 저장소 성격

Claude Code **스킬 모음**이다. 애플리케이션이 아니라 배포 산출물의 저장소다.

- 최상위 폴더 하나 = 독립적으로 설치 가능한 스킬 하나. 현재는 `harness-architect/` 뿐이다.
- 설치는 복사다: `cp -r <skill>/.claude /path/to/target-project/`. 빌드 단계가 없다.
- **절대 경로 하드코딩 금지.** 모든 스크립트·문서·frontmatter 경로는 상대 경로여야
  통째로 복사했을 때 대상 저장소에서 그대로 동작한다. `$CLAUDE_PROJECT_DIR` 은 예외.
- 런타임: Bash + POSIX `awk`/`grep`, Python 3, 선택적 PyYAML. 패키지 매니저·의존성 파일 없음.
- 원격 저장소 이름은 `agentskills` (README 의 표기), 로컬 디렉터리는 `agent-architect`.

## 검증 (이 저장소에는 테스트 러너가 없다 — 아래가 전부다)

스킬을 수정하면 `harness-architect/` 를 작업 디렉터리로 두고 다음을 돌린다:

```bash
cd harness-architect

# 0) superpowers preflight — exit 1 이면 필수 스킬 목록과 함께 없는 것을 알려준다
bash .claude/skills/harness-architect/scripts/check-superpowers.sh

# 1) 스택 감지 — gates.tsv 생성. exit 3 이면 스택 미감지(정상일 수 있음)
#    exit 4 이면 superpowers 미설치 — 골격을 만들지 않고 즉시 중단한다
bash .claude/skills/harness-architect/scripts/init-workspace.sh

# 2) HarnessSpec 예제 4종이 계약 검증기를 통과하는지 (PyYAML 필요, 없으면 exit 2)
for f in .claude/skills/harness-architect/examples/*.yaml; do
  python3 .claude/skills/harness-architect/scripts/validate-spec.py "$f"
done

# 3) 읽기 전용 가드 훅이 실제로 거부하는지 — "permissionDecision":"deny" 가 나와야 함
echo '{"hook_event_name":"PreToolUse","agent_type":"reviewer","agent_id":"s1",
       "tool_name":"Write","tool_input":{"file_path":"src/x.ts","content":"y"}}' \
  | python3 .claude/skills/harness-architect/scripts/guard-readonly.py
```

단일 spec 검증: `python3 .../validate-spec.py _workspace/harness/spec.yaml --gates _workspace/harness/gates.tsv`

`_workspace/` 는 하네스 실행 산출물이 쌓이는 곳이며 커밋하지 않는다.

## harness-architect 아키텍처

### 무엇인가

개발 업무를 자연어로 받아 **작업 복잡도에 맞는 최소 하네스(H0~H3)를 매번 새로 판정**하는
라우터 **스킬**(Agent 가 아니다). 분석·판정·구성안 생성은 스킬이 하고, 실제 작업은
카탈로그의 Agent 7종이 한다. 절차적 지식은 직접 쓰지 않고 `superpowers` 플러그인 스킬에 위임한다.

### 실행 흐름 (`SKILL.md` 의 Phase 0~5)

1. **Phase 0** — `task` 6필드 정규화. 목표가 불명확하면 `superpowers:brainstorming` 으로 이탈.
2. **Phase 1** — `init-workspace.sh` 로 결정론적 게이트(`gates.tsv`) 탐지. 명령을 지어내지 않는다.
3. **Phase 2** — `references/profiling.md` 6축 판정 → `references/routing.md` 5스텝 판정 트리로 레벨 결정.
4. **Phase 3** — `schemas/harness-spec.yaml` 형식으로 `_workspace/harness/spec.yaml` 작성 →
   `validate-spec.py` (exit 1 이면 승인 요청 금지) → **한 화면 요약으로 사용자 승인**.
5. **Phase 4** — 레벨별 실행. **승인 전 에이전트 스폰 금지.**
6. **Phase 5** — 최종 게이트 → `superpowers:verification-before-completion` → Human Gate.

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

frontmatter 의 `tools` 가 1차 경계(`reviewer`·`orchestrator` 에 `Edit` 없음).
`scripts/guard-readonly.py` 를 `PreToolUse` 훅으로 걸어 **쓰기 대상 경로**로 2차 판정한다
(`reviewer`·`orchestrator` 는 `_workspace/` 아래만, `dependency-mapper` 는 아무 데도 못 씀).
셸을 파싱하지 않으므로 샌드박스가 아니라 규율 장치다.

## 여러 파일에 걸친 불변식 (수정 시 전부 동기화)

harness-architect 는 "진실의 원천"이 코드·스키마·문서·테스트에 **중복 선언**되어 있고,
검증기가 그 일치를 강제한다. 하나를 바꾸면 나머지도 바꿔야 한다.

| 개념 | 정의 위치 (전부 일치해야 함) |
|---|---|
| 에이전트 7종 (`CATALOG`) | `scripts/validate-spec.py` · `references/catalog.md` · `.claude/agents/*.md` |
| 허용 스킬 목록 (`ALLOWED_SKILLS` / `CONTROLLER_ONLY_SKILLS`) | `scripts/validate-spec.py` · `references/catalog.md` 매핑표 |
| 재라우팅 매핑 (`escalation`) | `scripts/validate-spec.py` · `references/routing.md` 표 · `schemas/harness-spec.yaml` · `agents/orchestrator.md` |
| 레벨↔패턴 / 레벨↔추적모드 / `max_loops` 상한 / `max_workers` 상한 | `scripts/validate-spec.py` · `schemas/harness-spec.yaml` · README |
| 레벨↔필수 controller 스킬 (`LEVEL_REQUIRED_CONTROLLER_SKILLS`) | `scripts/validate-spec.py` · `references/routing.md` H2/H3 절차 · `references/catalog.md` 매핑표 · `examples/h2-*.yaml`·`h3-*.yaml` |
| tier 3종 (`fast`/`feature`/`final`) 과 스크립트 이름→tier 매핑 | `scripts/detect-stack.sh` · `scripts/run-gates.sh` · `scripts/validate-spec.py` |
| 읽기 전용 역할과 쓰기 허용 범위 | `scripts/guard-readonly.py` (`READONLY_ROLES`) · `references/catalog.md` 강제 수준 표 |
| superpowers 버전 (현재 6.3.0) | `references/catalog.md` |
| 필수 superpowers 스킬 목록 (`REQUIRED_SKILLS`) | `scripts/check-superpowers.sh` · `scripts/validate-spec.py` 의 `ALLOWED_SKILLS`(내장 `security-review` 제외) · `references/catalog.md` 매핑표 |

`validate-spec.py` 는 `yaml.safe_load` 성공("문법이 YAML")을 넘어 카탈로그 밖 에이전트,
`model` 누락, 축 모순(`coupling: high` + `parallelism ≠ none`), **수용 기준에 대응하는 게이트 부재**,
Human Gate 누락, H3 `escalation` 계약 누락 등을 거부한다. 새 검사를 추가할 때 이 파일의
상단 상수(`CATALOG`, `ENUMS`, `ALLOWED_SKILLS` 등)부터 본다.

## 외부 의존성

| 의존 | 없으면 |
|---|---|
| `superpowers` 플러그인 (6.3.0) | H0 도 `verification-before-completion` 이 필수라 완전히 끊긴다. Phase 1 의 `check-superpowers.sh` 가 감지해 `init-workspace.sh` 가 exit 4 로 즉시 중단하고 설치 명령을 제시한다 (버전이 아니라 **필수 스킬 11종의 존재**로 판정한다 — 서로 다른 버전이 공존할 수 있다) |
| PyYAML (`pip install pyyaml`) | `validate-spec.py` 가 exit 2 — 승인 게이트를 사람이 대신 확인 |
| Linear MCP | `tracking.provider: linear` 불가. `none` 이면 정상 동작 |

## 불변 규칙 (스킬 로직을 건드릴 때)

- **최소 하네스 우선.** 승격에는 근거 문장이 필요하고, 강등(under-orchestration)도 똑같이 오답이다.
- **역할을 새로 만들지 않는다.** 반복 Procedure 는 Agent 가 아니라 Skill 이다.
- **게이트 명령을 지어내지 않는다.** 감지 실패 시 사용자에게 묻는다.
- **컨텍스트는 경로로 전달한다.** dispatch 시 `model` 을 항상 명시한다.
- **자동 커밋 금지 / `_workspace/` 보존.** `scripts/harness-paths.sh` 가 `_workspace/` 를
  메인 워크트리 루트에 고정한다 (H2/H3 이 worktree 로 이동해도 산출물이 한곳에 남게).
  게이트 *명령*의 실행 디렉터리는 고정하지 않는다 — 검증 대상은 현재 트리의 코드다.
- **격리와 해제는 쌍이다.** worktree 를 만드는 레벨(H2·H3)은 정리 스킬까지 함께 선언한다.
  정리 시점은 **통합 결과**가 정하고 Linear 상태가 정하지 않는다 (`Canceled` 는 강등을
  포함하고 `Done` 은 통합보다 먼저 찍힌다).
- **Linear 쓰기는 컨트롤러만.** 워커·orchestrator 는 상태 토큰만 반환한다. H0 은 추적하지 않는다.
