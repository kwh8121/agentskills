#!/usr/bin/env bash
# install.sh — harness-architect 를 대상 프로젝트에 배치한다.
#
# 사용법:
#   bash install.sh <대상_디렉터리> [--harness claude|codex|opencode] [--force] [--no-merge]
#
# 하는 일은 파일 복사와 설정 병합이다(컴파일·코드 생성 없음):
#   core/                     → <대상>/<하네스 디렉터리>/skills/harness-architect/
#   <하네스>/<하네스 디렉터리>/ → <대상>/<하네스 디렉터리>/            (역할 정의·훅 배선)
#
# 이미 있는 설정 파일(settings.json / hooks.json / opencode.json)은 **덮어쓰지 않고
# 우리 항목만 추가한다** (scripts/merge-config.py). 기존 훅은 그대로 두고, 우리 훅이
# 이미 있으면 정의만 갱신한다. 바꾸기 전에 .bak-<타임스탬프> 를 남긴다.
# 깨진 JSON 은 손대지 않고 붙일 내용을 출력한다 — 추측으로 고치지 않는다.
# opencode.json 이 없으면 가드 플러그인만 담은 최소 파일을 만든다 (OpenCode 는 플러그인을
# 자동 로드하지 않아, 등록이 없으면 2차 가드가 통째로 죽기 때문).
# --no-merge 를 주면 기존 파일을 건드리지 않고, opencode.json 도 만들지 않는다.
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
        -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
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

# ── 0) 소스 트리 온전성 ────────────────────────────────────────────────────
# set -e 를 쓰지 않으므로(아래 병합 exit code 를 직접 다룬다) 부분 클론·잘린
# 체크아웃이면 cp 가 조용히 실패하고도 "배치 완료"까지 흘러간다. 여기서 멈춘다.
for need in "$HERE/core/SKILL.md" "$HERE/core/scripts/detect-harness.sh" "$SRC"; do
    if [[ ! -e "$need" ]]; then
        echo "install: 소스 트리가 온전하지 않습니다 — '$need' 가 없습니다." >&2
        echo "install: 저장소를 다시 받으십시오 (부분 클론·잘린 체크아웃일 수 있습니다)." >&2
        exit 2
    fi
done

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

# OpenCode 는 프로젝트의 opencode.json 의 plugin 배열에 등록해야 가드가 산다.
# OpenCode 는 .opencode/plugin/*.js 를 자동 로드하지 않으므로, 등록이 없으면 2차 가드
# (bash 우회·MCP 쓰기 차단)가 통째로 죽는다. 있으면 병합하고, 없으면 가드 플러그인만
# 담은 최소 파일을 만든다 ($schema + plugin 두 키뿐이라 모델·프로바이더 해석에 영향 없음).
if [[ "$HARNESS" == "opencode" && "$NO_MERGE" -eq 0 ]]; then
    if [[ -f "$TARGET/opencode.json" ]]; then
        $MERGE --opencode-plugin "$TARGET/opencode.json" "./.opencode/plugin/harness-guard.js"
    else
        cat > "$TARGET/opencode.json" <<'JSON'
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "./.opencode/plugin/harness-guard.js"
  ]
}
JSON
        echo "  설정:     $TARGET/opencode.json 생성 (가드 플러그인 등록)"
    fi
fi

# ── 3.5) 배치 검증 ────────────────────────────────────────────────────────
# 복사가 부분 실패해도(디스크·권한·잘린 소스) set -e 가 없어 여기까지 온다.
# 조용한 부분 배치를 큰 실패로 바꾼다 — 기대 산출물이 실제로 있는지 본다.
missing=()
[[ -f "$SKILL_DEST/SKILL.md" ]]                  || missing+=("$SKILL_DEST/SKILL.md")
[[ -f "$SKILL_DEST/scripts/guard-readonly.py" ]] || missing+=("$SKILL_DEST/scripts/guard-readonly.py")

case "$HARNESS" in
    claude)   SRC_AGENT="$SRC/agents"; DST_AGENT="$DEST/agents"; WIRING="" ;;     # settings.json 은 있을 때만
    codex)    SRC_AGENT="$SRC/agents"; DST_AGENT="$DEST/agents"; WIRING="$DEST/hooks.json" ;;
    opencode) SRC_AGENT="$SRC/agent";  DST_AGENT="$DEST/agent";  WIRING="$DEST/plugin/harness-guard.js" ;;
esac
[[ -n "$WIRING" && ! -e "$WIRING" ]] && missing+=("$WIRING")

# 역할 파일은 소스 어댑터 트리의 basename 기준으로 대조한다 — 대상에 이미 있던 사용자
# 에이전트에 개수가 부풀지 않게. CATALOG 는 7종 고정(check-adapters.py 가 강제)이므로
# 소스가 7 미만이면 잘린 체크아웃, 도착이 소스 미만이면 복사 중단이다.
roles_src=0; roles_ok=0
while IFS= read -r -d '' rf; do
    roles_src=$((roles_src + 1))
    [[ -f "$DST_AGENT/$(basename "$rf")" ]] && roles_ok=$((roles_ok + 1))
done < <(find "$SRC_AGENT" -maxdepth 1 -type f \( -name '*.md' -o -name '*.toml' \) -print0 2>/dev/null)
[[ "$roles_src" -ne 7 || "$roles_ok" -ne "$roles_src" ]] \
    && missing+=("$DST_AGENT/ (역할 $roles_ok 종 도착 / 소스 $roles_src 종 / 기대 7종)")

if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "" >&2
    echo "install: 배치가 불완전합니다 — 다음 산출물이 없습니다:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    echo "install: 소스 트리·디스크 공간·권한을 확인하고 다시 실행하십시오." >&2
    exit 1
fi
echo "  검증:     핵심 산출물 · 역할 ${roles_ok}종 확인"

# OpenCode 2차 가드가 실제로 배선됐는지 — opencode.json 의 plugin 에 등록됐는가.
# 기본 경로에서는 위에서 만들거나 병합했으므로 통과한다. --no-merge 이거나 opencode.json
# 이 깨져 병합이 막힌 경우에만 경고가 뜬다 (선언적 1차 경계는 그대로 살아 있다).
if [[ "$HARNESS" == "opencode" ]]; then
    if [[ -f "$TARGET/opencode.json" ]] && grep -q "harness-guard.js" "$TARGET/opencode.json" 2>/dev/null; then
        echo "  가드:     opencode.json 에 플러그인 등록됨 (2차 경계 활성)"
    else
        echo "  ⚠ 가드:   opencode.json 에 플러그인이 등록되지 않았습니다 — 2차 경계(bash 우회·MCP 쓰기 차단)가 비활성입니다." >&2
        echo "            opencode.json 의 plugin 배열에 \"./.opencode/plugin/harness-guard.js\" 를 넣으십시오." >&2
    fi
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
  1. 가드 플러그인 등록 확인 — 위 "가드:" 줄이 "활성" 이어야 합니다.
     install.sh 가 opencode.json 을 병합(있던 경우)하거나 최소 파일로 생성(없던 경우)했습니다.
     --no-merge 로 깔았거나 경고가 떴으면 opencode.json 의 plugin 배열에 직접 넣으십시오:
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
