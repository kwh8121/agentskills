#!/usr/bin/env bash
# check-superpowers.sh — harness-architect 가 위임하는 superpowers 스킬이 설치돼 있는지 확인한다.
#
# 사용법:  check-superpowers.sh [--quiet]
# 종료코드: 0 = 필수 스킬 전부 존재 / 1 = 하나 이상 없음
#
# 왜 버전이 아니라 "스킬의 존재"로 판정하는가:
#   같은 플러그인이 서로 다른 마켓플레이스에서 여러 벌 설치될 수 있다 — 실제로 5.1.0 과
#   6.3.0 이 공존하는 환경이 관측됐다. 그때 버전 문자열로 판정하면 엉뚱한 설치본을 보고
#   오판한다. 정작 알아야 하는 것은 "`REQUIRED SUB-SKILL` 호출이 성공하는가"이므로
#   스킬 디렉터리와 그 SKILL.md 의 존재로 직접 판정한다.
#
# 이 목록은 validate-spec.py 의 ALLOWED_SKILLS 에서 내장 `security-review` 를 뺀 것과
# 같아야 한다 (CLAUDE.md 의 불변식 표 참고).
set -uo pipefail

REQUIRED_SKILLS=(
    brainstorming
    writing-plans
    subagent-driven-development
    dispatching-parallel-agents
    using-git-worktrees
    requesting-code-review
    verification-before-completion
    finishing-a-development-branch
    test-driven-development
    receiving-code-review
    systematic-debugging
)

QUIET=0
HARNESS=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quiet)   QUIET=1; shift ;;
        --harness) HARNESS="${2:-}"; shift 2 ;;
        *)         shift ;;
    esac
done

# 하네스마다 스킬이 사는 곳이 다르다. 판정은 detect-harness.sh 한 곳에서만 한다.
if [[ -z "$HARNESS" ]]; then
    HARNESS="$(bash "$(dirname "${BASH_SOURCE[0]}")/detect-harness.sh" --field harness 2>/dev/null || echo "")"
fi

# 탐지 경로와 설치 명령은 references/adapters/<하네스>.md 의 superpowers_roots 와 같아야 한다.
candidates=()
install_hint=""
case "$HARNESS" in
    codex)
        candidates=("${CODEX_HOME:-$HOME/.codex}/skills" ".codex/skills")
        install_hint="codex plugin add superpowers   (또는 저장소의 .codex-plugin/ 을 스킬 경로에 배치)"
        ;;
    opencode)
        oc_cfg="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
        candidates=("$oc_cfg/skills" "$HOME/.opencode/skills" ".opencode/skills"
                    "$oc_cfg/node_modules/superpowers/skills" "node_modules/superpowers/skills")
        install_hint='opencode.json 의 plugin 배열에 "superpowers@git+https://github.com/obra/superpowers.git" 추가'
        ;;
    *)  # claude 및 판정 불가 — 기존 동작(플러그인 디렉터리 전수 탐색)을 유지한다.
        HARNESS="${HARNESS:-claude}"
        candidates=("${CLAUDE_PLUGIN_ROOT:-}" "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins" ".claude/plugins")
        install_hint="/plugin install superpowers@claude-plugins-official   (사용자가 직접 입력)"
        ;;
esac

roots=()
for c in "${candidates[@]}"; do
    [[ -n "$c" && -d "$c" ]] && roots+=("$c")
done

if [[ "${#roots[@]}" -eq 0 ]]; then
    [[ "$QUIET" -eq 1 ]] || {
        echo "check-superpowers: [$HARNESS] 스킬 디렉터리를 찾지 못했습니다." >&2
        echo "  확인한 위치: ${candidates[*]}" >&2
        echo "  설치: $install_hint" >&2
    }
    exit 1
fi

# 한 번의 find 로 설치된 스킬 이름을 전부 수집한다 (스킬마다 find 를 도는 것보다 훨씬 싸다).
# 관측된 레이아웃은 두 가지다:
#   <root>/cache/<marketplace>/<plugin>/<version>/skills/<name>/SKILL.md   (깊이 6)
#   <root>/marketplaces/<marketplace>/skills/<name>/SKILL.md               (깊이 4)
installed="$(find "${roots[@]}" -maxdepth 7 -type f -name SKILL.md -path '*/skills/*' 2>/dev/null \
             | awk -F/ '{ print $(NF-1) }' | sort -u)"

missing=()
for skill in "${REQUIRED_SKILLS[@]}"; do
    grep -qxF "$skill" <<< "$installed" || missing+=("$skill")
done

if [[ "${#missing[@]}" -eq 0 ]]; then
    [[ "$QUIET" -eq 1 ]] || \
        echo "check-superpowers: [$HARNESS] 필수 스킬 ${#REQUIRED_SKILLS[@]}종 전부 확인됨."
    exit 0
fi

[[ "$QUIET" -eq 1 ]] || {
    echo "check-superpowers: [$HARNESS] superpowers 필수 스킬 ${#missing[@]}종을 찾지 못했습니다." >&2
    for m in "${missing[@]}"; do echo "  - $m" >&2; done
    echo "  검색한 위치: ${roots[*]}" >&2
    echo "  설치: $install_hint" >&2
}
exit 1
