#!/usr/bin/env python3
"""codex-hook-trust.py — Codex 훅을 신뢰 등록하는 TOML 블록을 만든다.

사용법:
    python3 codex-hook-trust.py <hooks.json 경로> [--all]

    기본값은 **harness-architect 가 건 훅만** 출력한다. 같은 파일에 있는 사용자의 다른 훅까지
    신뢰 블록에 넣으면, 붙여 넣는 사람이 의도하지 않은 훅까지 신뢰하게 된다. `--all` 은
    파일 안의 모든 훅을 낸다.

왜 필요한가:
    Codex 는 `~/.codex/config.toml` 에 `[hooks.state."<경로>:<이벤트>:<i>:<j>"]` 항목이 있고
    그 `trusted_hash` 가 훅 정의와 일치할 때만 훅을 실행한다. **등록되지 않은 프로젝트 훅은
    신뢰된 프로젝트에서도 조용히 무시된다** (실측으로 확인했다). 그래서 설치 직후에는
    읽기 전용 가드가 동작하지 않는다.

해시 형식 (Codex 의 정규화 규칙):
    canonical = JSON.stringify({
        event_name: "<snake_case 이벤트>",
        hooks: [{ async, command, timeout, type }],   // 키 순서 고정
        matcher: <있으면 문자열, 없으면 생략>
    })
    trusted_hash = "sha256:" + sha256(canonical)

    `async`·`timeout` 은 Codex 가 채우는 기본값이 해시에 들어가므로, 이 스크립트가 읽는
    hooks.json 에도 **명시돼 있어야** 값이 어긋나지 않는다. 어댑터가 배포하는
    codex/.codex/hooks.json 은 그래서 두 값을 명시한다.

이 스크립트는 **출력만 한다.** config.toml 을 직접 고치지 않는다 — 훅 신뢰는 사용자가
명시적으로 내리는 결정이다.
"""
import hashlib
import json
import os
import sys

EXIT_OK, EXIT_USAGE = 0, 2

# Codex 가 쓰는 이벤트 키(스네이크)로 옮긴다.
EVENT_KEY = {
    "PreToolUse": "pre_tool_use",
    "PostToolUse": "post_tool_use",
    "SessionStart": "session_start",
    "UserPromptSubmit": "user_prompt_submit",
    "PreCompact": "pre_compact",
    "PostCompact": "post_compact",
    "Stop": "stop",
}

DEFAULT_ASYNC = False
DEFAULT_TIMEOUT = 600

# 우리 훅을 알아보는 표식. merge-config.py 의 MARKER 와 같아야 한다.
MARKER = "harness-architect/scripts/guard-readonly.py"


def identity_hash(event_key, hook, matcher):
    payload = {
        "event_name": event_key,
        "hooks": [{
            "async": bool(hook.get("async", DEFAULT_ASYNC)),
            "command": hook.get("command", ""),
            "timeout": int(hook.get("timeout", DEFAULT_TIMEOUT)),
            "type": hook.get("type", "command"),
        }],
    }
    if matcher is not None:
        payload["matcher"] = matcher
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return EXIT_USAGE

    only_ours = "--all" not in sys.argv[1:]
    path = os.path.abspath(sys.argv[1])
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"codex-hook-trust: {path} 를 읽을 수 없습니다: {e}", file=sys.stderr)
        return EXIT_USAGE

    lines = []
    for event, groups in (data.get("hooks") or {}).items():
        event_key = EVENT_KEY.get(event, event.lower())
        for gi, group in enumerate(groups or []):
            matcher = group.get("matcher")
            for hi, hook in enumerate(group.get("hooks") or []):
                if only_ours and MARKER not in str(hook.get("command", "")):
                    continue
                key = f"{path}:{event_key}:{gi}:{hi}"
                lines.append(f'[hooks.state."{key}"]')
                lines.append(f'trusted_hash = "{identity_hash(event_key, hook, matcher)}"')
                lines.append("enabled = true")
                lines.append("")

    if not lines:
        where = "harness-architect 훅이" if only_ours else "훅이"
        print(f"codex-hook-trust: {path} 에 등록할 {where} 없습니다.", file=sys.stderr)
        return EXIT_USAGE

    print("# ~/.codex/config.toml 끝에 붙여 넣으십시오. 붙이기 전까지 가드는 동작하지 않습니다.")
    print("\n".join(lines).rstrip())
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
