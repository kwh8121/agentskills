#!/usr/bin/env bash
# detect-harness.sh — 지금 어떤 하네스에서 돌고 있는지 판정하고 경로를 해석한다.
#
# 사용법:
#   detect-harness.sh                 → harness / skill_dir / adapter 세 줄
#   detect-harness.sh --field harness → 값 하나만
#   eval "$(detect-harness.sh)"       → 셸 변수로 받기
#
# 종료코드: 0 = 판정됨 / 3 = 판정 불가(설치본도 못 찾음)
#
# 왜 필요한가:
#   SKILL.md 는 하네스 어휘를 쓰지 않는다. 스크립트 경로·어댑터 문서 위치는 하네스마다
#   다르므로, 그 해석을 한 곳에 모은다. 여기서 나온 skill_dir 을 다른 스크립트와
#   SKILL.md 가 그대로 쓴다.
#
# 판정 순서:
#   1) 환경변수 — 실행 중인 하네스가 남기는 고유 신호. 가장 믿을 수 있다.
#   2) 설치 디렉터리 — 환경변수가 없을 때(파이프·CI·수동 실행) 무엇이 깔려 있는지로 판단.
#   느슨한 접두사 매칭(CODEX_*)은 쓰지 않는다 — 다른 하네스가 컴패니언 플러그인으로
#   CODEX_COMPANION_SESSION_ID 같은 변수를 심어 두는 환경이 실제로 있다.
set -uo pipefail

FIELD=""
[[ "${1:-}" == "--field" ]] && FIELD="${2:-}"

skill_dir_for() {
    case "$1" in
        claude)   printf '.claude/skills/harness-architect\n' ;;
        codex)    printf '.codex/skills/harness-architect\n' ;;
        opencode) printf '.opencode/skills/harness-architect\n' ;;
    esac
}

adapter_for() {
    case "$1" in
        claude)   printf 'references/adapters/claude-code.md\n' ;;
        codex)    printf 'references/adapters/codex.md\n' ;;
        opencode) printf 'references/adapters/opencode.md\n' ;;
    esac
}

# --- 1) 환경변수 -----------------------------------------------------------
harness=""
if [[ -n "${CLAUDECODE:-}" || -n "${CLAUDE_PROJECT_DIR:-}" || -n "${CLAUDE_CODE_SESSION_ID:-}" ]]; then
    harness="claude"
elif [[ -n "${CODEX_SESSION_ID:-}" || -n "${CODEX_HOME:-}" || -n "${CODEX_HOOK_EVENT_NAMES:-}" ]]; then
    harness="codex"
elif [[ -n "${OPENCODE_CONFIG_DIR:-}" || -n "${OPENCODE_BIN_PATH:-}" || -n "${OPENCODE:-}" ]]; then
    harness="opencode"
fi

# --- 2) 설치 디렉터리 ------------------------------------------------------
installed=()
for h in claude codex opencode; do
    [[ -d "$(skill_dir_for "$h")" ]] && installed+=("$h")
done

if [[ -z "$harness" ]]; then
    if [[ "${#installed[@]}" -eq 1 ]]; then
        harness="${installed[0]}"
    elif [[ "${#installed[@]}" -gt 1 ]]; then
        echo "detect-harness: 하네스 환경변수가 없고 설치본이 여러 개입니다: ${installed[*]}" >&2
        echo "  --field 로 명시하거나 해당 하네스에서 실행하십시오." >&2
        exit 3
    else
        echo "detect-harness: 하네스를 판정할 수 없고 설치본도 없습니다." >&2
        echo "  확인한 위치: .claude/ .codex/ .opencode/ 아래 skills/harness-architect" >&2
        exit 3
    fi
fi

skill_dir="$(skill_dir_for "$harness")"

# 판정된 하네스의 설치본이 없는데 다른 하네스로 깔려 있으면 그쪽을 쓴다.
# (Claude 세션에서 codex 용 설치본만 있는 저장소를 열어보는 경우가 실제로 있다.)
if [[ ! -d "$skill_dir" && "${#installed[@]}" -ge 1 ]]; then
    echo "detect-harness: $harness 로 판정했으나 $skill_dir 가 없어 ${installed[0]} 설치본을 씁니다." >&2
    harness="${installed[0]}"
    skill_dir="$(skill_dir_for "$harness")"
fi

adapter="$skill_dir/$(adapter_for "$harness")"

case "$FIELD" in
    harness)   printf '%s\n' "$harness" ;;
    skill_dir) printf '%s\n' "$skill_dir" ;;
    adapter)   printf '%s\n' "$adapter" ;;
    "")        printf 'harness=%s\nskill_dir=%s\nadapter=%s\n' "$harness" "$skill_dir" "$adapter" ;;
    *)         echo "detect-harness: 알 수 없는 --field '$FIELD' (harness|skill_dir|adapter)" >&2; exit 3 ;;
esac
