#!/usr/bin/env python3
"""merge-config.py — 대상 프로젝트의 기존 설정 파일에 하네스 배선을 **추가**한다.

사용법:
    merge-config.py --hooks <대상.json> <추가할.json>        # Claude settings.json / Codex hooks.json
    merge-config.py --opencode-plugin <opencode.json> <플러그인 경로>

종료코드:
    0  병합함 (무엇을 바꿨는지 stdout 에 한 줄)
    1  이미 최신이라 바꿀 것이 없음 (정상)
    2  손대지 않았다 — 대상이 깨진 JSON 이거나 구조가 예상과 다르다 (호출부가 안내를 출력해야 함)

원칙:
    - **덮어쓰지 않는다.** 기존 항목은 그대로 두고 우리 것만 더한다.
    - **멱등이다.** 우리 항목은 스크립트 경로(harness-architect/scripts/guard-readonly.py)로
      식별한다. 이미 있으면 정의만 갱신하고 새로 추가하지 않는다.
    - **깨진 파일은 건드리지 않는다.** 파싱에 실패하면 아무것도 쓰지 않고 exit 2 로 알린다.
      추측으로 고치는 것보다 사람에게 넘기는 쪽이 낫다.
    - **바꾸기 전에 백업한다.** <파일>.bak-<타임스탬프> 를 남긴다.

한계:
    JSON 을 다시 써내므로 원본의 들여쓰기·키 순서가 아니라 2칸 들여쓰기로 정규화된다.
    JSON 에는 주석이 없으므로 잃는 정보는 없다.
"""
import datetime
import json
import os
import shutil
import sys

EXIT_MERGED, EXIT_NOOP, EXIT_UNTOUCHED = 0, 1, 2

# 우리 훅을 알아보는 표식. 경로가 바뀌어도 이 부분은 유지된다.
MARKER = "harness-architect/scripts/guard-readonly.py"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def backup(path):
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    dst = f"{path}.bak-{stamp}"
    shutil.copy2(path, dst)
    return dst


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def is_ours(hook):
    return isinstance(hook, dict) and MARKER in str(hook.get("command", ""))


def merge_hooks(target_path, source_path):
    """hooks.PreToolUse 구조에 우리 그룹을 추가한다 (Claude·Codex 공통 형식)."""
    try:
        target = load(target_path)
        source = load(source_path)
    except (OSError, ValueError) as e:
        print(f"merge-config: {target_path} 를 병합할 수 없습니다: {e}", file=sys.stderr)
        return EXIT_UNTOUCHED

    if not isinstance(target, dict):
        print(f"merge-config: {target_path} 최상위가 객체가 아닙니다.", file=sys.stderr)
        return EXIT_UNTOUCHED

    hooks = target.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        print(f"merge-config: {target_path} 의 hooks 가 객체가 아닙니다.", file=sys.stderr)
        return EXIT_UNTOUCHED

    added, updated = [], []
    for event, groups in (source.get("hooks") or {}).items():
        existing = hooks.setdefault(event, [])
        if not isinstance(existing, list):
            print(f"merge-config: {target_path} 의 hooks.{event} 가 배열이 아닙니다.", file=sys.stderr)
            return EXIT_UNTOUCHED

        for group in groups or []:
            # 이미 우리 훅이 들어 있는 그룹을 찾는다.
            slot = None
            for g in existing:
                if isinstance(g, dict) and any(is_ours(h) for h in (g.get("hooks") or [])):
                    slot = g
                    break

            if slot is None:
                existing.append(group)
                added.append(event)
                continue

            # 정의가 달라졌으면(경로·타임아웃 변경 등) 우리 것만 갈아 끼운다.
            new_hooks = []
            changed = False
            for h in slot.get("hooks") or []:
                if is_ours(h):
                    replacement = next((x for x in (group.get("hooks") or []) if is_ours(x)), h)
                    if replacement != h:
                        changed = True
                    new_hooks.append(replacement)
                else:
                    new_hooks.append(h)          # 남의 훅은 손대지 않는다
            slot["hooks"] = new_hooks
            if group.get("matcher") != slot.get("matcher"):
                slot["matcher"] = group.get("matcher", slot.get("matcher"))
                changed = True
            if changed:
                updated.append(event)

    if not added and not updated:
        print(f"merge-config: {target_path} 은 이미 최신입니다.")
        return EXIT_NOOP

    bak = backup(target_path)
    save(target_path, target)
    what = []
    if added:
        what.append(f"추가 {', '.join(sorted(set(added)))}")
    if updated:
        what.append(f"갱신 {', '.join(sorted(set(updated)))}")
    print(f"merge-config: {target_path} 에 가드 훅을 {' · '.join(what)}했습니다 (백업 {bak})")
    return EXIT_MERGED


def merge_opencode_plugin(target_path, plugin_path):
    """opencode.json 의 plugin 배열에 로컬 플러그인 경로를 추가한다."""
    try:
        target = load(target_path)
    except (OSError, ValueError) as e:
        print(f"merge-config: {target_path} 를 병합할 수 없습니다: {e}", file=sys.stderr)
        return EXIT_UNTOUCHED

    if not isinstance(target, dict):
        print(f"merge-config: {target_path} 최상위가 객체가 아닙니다.", file=sys.stderr)
        return EXIT_UNTOUCHED

    plugins = target.setdefault("plugin", [])
    if not isinstance(plugins, list):
        print(f"merge-config: {target_path} 의 plugin 이 배열이 아닙니다.", file=sys.stderr)
        return EXIT_UNTOUCHED

    if plugin_path in plugins:
        print(f"merge-config: {target_path} 은 이미 최신입니다.")
        return EXIT_NOOP

    plugins.append(plugin_path)
    bak = backup(target_path)
    save(target_path, target)
    print(f"merge-config: {target_path} 의 plugin 에 {plugin_path} 를 추가했습니다 (백업 {bak})")
    return EXIT_MERGED


def main():
    if len(sys.argv) != 4:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return EXIT_UNTOUCHED
    mode, target, source = sys.argv[1], sys.argv[2], sys.argv[3]
    if mode == "--hooks":
        return merge_hooks(target, source)
    if mode == "--opencode-plugin":
        return merge_opencode_plugin(target, source)
    print(f"merge-config: 알 수 없는 모드 '{mode}'", file=sys.stderr)
    return EXIT_UNTOUCHED


if __name__ == "__main__":
    sys.exit(main())
