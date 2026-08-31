#!/usr/bin/env bash
# install.sh — harness-architect 를 대상 프로젝트에 배치한다.
#
# 사용법:
#   bash install.sh <대상_디렉터리> [--harness claude|codex|opencode] [--force] [--no-merge]
#
# 하는 일은 파일 복사뿐이다(생성·컴파일 없음):
#   core/                     → <대상>/<하네스 디렉터리>/skills/harness-architect/
#   <하네스>/<하네스 디렉터리>/ → <대상>/<하네스 디렉터리>/            (역할 정의·훅 배선)
#
# 이미 있는 설정 파일(settings.json / hooks.json / opencode.json)은 **덮어쓰지 않고
# 우리 항목만 추가한다** (scripts/merge-config.py). 기존 훅은 그대로 두고, 우리 훅이
# 이미 있으면 정의만 갱신한다. 바꾸기 전에 .bak-<타임스탬프> 를 남긴다.
# 깨진 JSON 은 손대지 않고 붙일 내용을 출력한다 — 추측으로 고치지 않는다.
# --no-merge 를 주면 기존 파일을 건드리지 않고 출력만 한다.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET=""
HARNESS=""
FORCE=0
NO_MERGE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --harness)  HARNESS="${2:-}"; shift 2 ;;
        --force)    FORCE=1; shift ;;
        --no-merge) NO_MERGE=1; shift ;;
        -h|--help) sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
        *)         TARGET="$1"; shift ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "install: 대상 디렉터리가 필요합니다. 사용법: install.sh <대상> [--harness <h>]" >&2
    exit 2
fi
if [[ ! -d "$TARGET" ]]; then
    echo "install: '$TARGET' 는 디렉터리가 아닙니다." >&2
    exit 2
fi

if [[ -z "$HARNESS" ]]; then
    HARNESS="$(bash "$HERE/core/scripts/detect-harness.sh" --field harness 2>/dev/null || echo "")"
fi
if [[ -z "$HARNESS" ]]; then
    echo "install: 하네스를 판정할 수 없습니다. --harness claude|codex|opencode 를 지정하십시오." >&2
    exit 2
fi

case "$HARNESS" in
    claude)   DOT=".claude";   SRC="$HERE/claude/.claude" ;;
    codex)    DOT=".codex";    SRC="$HERE/codex/.codex" ;;
    opencode) DOT=".opencode"; SRC="$HERE/opencode/.opencode" ;;
    *) echo "install: 알 수 없는 하네스 '$HARNESS' (claude|codex|opencode)" >&2; exit 2 ;;
esac

DEST="$TARGET/$DOT"
SKILL_DEST="$DEST/skills/harness-architect"

echo "install: [$HARNESS] $TARGET 에 배치합니다."

# ── 1) 코어 ────────────────────────────────────────────────────────────────
# 코어는 통째로 교체한다. 사용자가 손댈 파일이 아니고, 부분 복사는 버전이 섞인
# 설치본을 만든다.
if [[ -d "$SKILL_DEST" && "$FORCE" -eq 0 ]]; then
    echo "  코어: 기존 설치본을 갱신합니다 ($SKILL_DEST)"
fi
mkdir -p "$SKILL_DEST"
rm -rf "${SKILL_DEST:?}/references" "${SKILL_DEST:?}/schemas" \
       "${SKILL_DEST:?}/examples" "${SKILL_DEST:?}/scripts" "${SKILL_DEST:?}/roles"
cp -R "$HERE/core/." "$SKILL_DEST/"
chmod +x "$SKILL_DEST"/scripts/*.sh 2>/dev/null
echo "  코어:     $SKILL_DEST"

# ── 2) 어댑터 ──────────────────────────────────────────────────────────────
# 설정 파일은 병합 대상이므로 따로 다룬다.
CONFIG_FILES=("settings.json" "hooks.json" "opencode.json")

pending_merge=()
while IFS= read -r -d '' src; do
    rel="${src#"$SRC"/}"
    dst="$DEST/$rel"
    base="$(basename "$rel")"

    is_config=0
    for c in "${CONFIG_FILES[@]}"; do [[ "$base" == "$c" ]] && is_config=1; done

    if [[ "$is_config" -eq 1 && -f "$dst" && "$FORCE" -eq 0 ]]; then
        pending_merge+=("$rel")
        continue
    fi
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
done < <(find "$SRC" -type f -print0)

echo "  어댑터:   $DEST (역할 $(find "$SRC" -type f \( -name '*.md' -o -name '*.toml' \) | wc -l)종 + 배선)"

# ── 3) 이미 있는 설정 파일에 우리 항목만 추가한다 ──────────────────────────
MERGE="python3 $SKILL_DEST/scripts/merge-config.py"

for rel in "${pending_merge[@]}"; do
    dst="$DEST/$rel"
    if [[ "$NO_MERGE" -eq 1 ]]; then
        echo ""
        echo "  ⚠ --no-merge: $dst 를 건드리지 않았습니다. 아래를 손으로 합치십시오:"
        sed 's/^/    /' "$SRC/$rel"
        continue
    fi

    $MERGE --hooks "$dst" "$SRC/$rel"
    case $? in
        0|1) echo "  설정:     $dst (기존 항목 보존)" ;;
        *)   echo ""
             echo "  ⚠ $dst 를 자동 병합하지 못했습니다. 아래를 손으로 합치십시오:"
             sed 's/^/    /' "$SRC/$rel" ;;
    esac
done

# OpenCode 는 프로젝트의 opencode.json 에 플러그인을 등록해야 가드가 산다.
# 파일이 없으면 만들지 않는다 — 프로젝트 설정 파일을 새로 만드는 것은 모델 해석 등
# 다른 동작에 영향을 줄 수 있어서, 있는 파일에 더하기만 한다.
if [[ "$HARNESS" == "opencode" && "$NO_MERGE" -eq 0 && -f "$TARGET/opencode.json" ]]; then
    $MERGE --opencode-plugin "$TARGET/opencode.json" "./.opencode/plugin/harness-guard.js"
fi

# ── 4) 하네스별 후속 조치 ──────────────────────────────────────────────────
echo ""
echo "install: 배치 완료. 남은 확인 사항:"
case "$HARNESS" in
    claude)
        cat <<'NEXT'
  1. superpowers 설치 확인:
       bash .claude/skills/harness-architect/scripts/check-superpowers.sh
     없으면 Claude Code 에서 직접: /plugin install superpowers@claude-plugins-official
  2. 가드 훅이 걸렸는지 확인 (deny JSON 이 나와야 합니다):
       echo '{"agent_type":"reviewer","tool_name":"Write","tool_input":{"file_path":"src/x.ts"}}' \
         | python3 .claude/skills/harness-architect/scripts/guard-readonly.py
NEXT
        ;;
    codex)
        cat <<'NEXT'
  1. ~/.codex/config.toml 에 아래가 필요합니다:
       [features]
       hooks = true
       multi_agent = true
  2. **훅 신뢰 등록 — 이 단계 없이는 가드가 동작하지 않습니다.**
     등록되지 않은 프로젝트 훅은 신뢰된 경로에서도 조용히 무시됩니다.
     아래 블록을 ~/.codex/config.toml 끝에 붙여 넣으십시오:
NEXT
        python3 "$SKILL_DEST/scripts/codex-hook-trust.py" "$DEST/hooks.json" 2>/dev/null \
            | sed 's/^/       /' \
            || echo "       (codex-hook-trust.py 실행 실패 — 어댑터 문서의 guard 절 참고)"
        cat <<'NEXT'
  3. superpowers 설치 확인:
       bash .codex/skills/harness-architect/scripts/check-superpowers.sh --harness codex
NEXT
        ;;
    opencode)
        cat <<'NEXT'
  1. opencode.json 의 plugin 배열에 로컬 플러그인이 등록돼야 가드가 삽니다.
     opencode.json 이 이미 있으면 위에서 자동으로 추가했습니다. 없으면 만드십시오:
       { "$schema": "https://opencode.ai/config.json",
         "plugin": ["./.opencode/plugin/harness-guard.js"] }
     등록하지 않으면 1차 경계(역할 파일의 tools/permission)만 남습니다.
  2. 역할 7종이 보이는지 확인:
       opencode agent
  3. superpowers 설치 확인:
       bash .opencode/skills/harness-architect/scripts/check-superpowers.sh --harness opencode
NEXT
        ;;
esac
echo ""
echo "  공통: bash $DOT/skills/harness-architect/scripts/init-workspace.sh 로 게이트를 감지합니다."
