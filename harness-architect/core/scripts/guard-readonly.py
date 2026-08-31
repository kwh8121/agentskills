#!/usr/bin/env python3
"""guard-readonly.py — 읽기 전용 역할이 소스를 쓰는 것을 도구 실행 전에 막는다.

왜 필요한가:
    에이전트 정의에서 편집 능력을 빼면 *정식 편집 경로*만 사라진다. 쓰기 도구는 새 파일을,
    셸은 `sed -i`·리다이렉션으로 무엇이든 바꿀 수 있다. 그래서 "reviewer 는 코드를
    고치지 않는다", "orchestrator 는 코드를 쓰지 않는다" 는 프롬프트 준수에만 의존했다.
    이 훅이 그 간극을 메운다.

MCP 도구도 본다:
    고정된 도구 이름 목록만으로는 부족하다. `serena_replace_content`·`mcp__x__write_file`
    같은 MCP 도구가 그대로 통과해 읽기 전용 역할이 소스를 고치는 것을 실제로 관측했다.
    그래서 **이름 패턴**(write|edit|patch|replace|create|delete|…)으로도 쓰기 도구를 판정하고,
    경로 키도 `relative_path` 등 MCP 서버별 표기를 함께 본다. 쓰기 도구로 보이는데 대상
    경로를 못 찾으면 거부한다 — 무엇을 쓰는지 모르는 쓰기를 허용할 근거가 없다.

무엇을 막는가 (역할별 쓰기 허용 범위):
    ../roles/manifest.tsv 의 write_scope 열이 진실의 원천이다. 파일을 읽을 수 없으면
    아래 DEFAULT_SCOPES 로 물러난다.
        reviewer          _workspace/ 아래만        — 보고서는 써야 하므로
        orchestrator      _workspace/ 아래만        — dag.md·상태 파일
        dependency-mapper 아무 데도 못 쓴다          — 조사 전용
    그 밖의 역할과 메인 스레드는 건드리지 않는다.
    implementer·integrator 는 소스를 고치는 것이 일이고, baseline-tester 는 특성화
    테스트를 레포의 테스트 디렉터리에 써야 해서 가드 대상이 아니다.

하네스:
    Claude Code · Codex · OpenCode 세 하네스의 페이로드를 받는다. 차이는 입력 정규화뿐이고
    판정 로직은 하나다. `--harness <claude|codex|opencode>` 로 지정하거나 생략하면
    페이로드 키로 자동 판정한다. 배선 방법은 references/adapters/<하네스>.md 의 guard 절.

한계 — 이것은 샌드박스가 아니다:
    셸 검사는 셸을 파싱하지 않고 쓰기 구문을 패턴으로 찾는다. 변수 확장, base64,
    파이프로 넘긴 인터프리터 같은 우회는 잡지 못한다. 규율 장치이지 보안 경계가 아니다.
    막지 못한 경로는 여전히 프롬프트 준수에 의존한다.

계약:
    입력  stdin JSON — 역할 / 도구 이름 / 도구 인자
    출력  거부할 때만 JSON 한 덩어리. 허용은 출력 없이 exit 0.
          거부 형식은 Claude Code 와 Codex 가 동일하다
          (hookSpecificOutput.permissionDecision = "deny").
          OpenCode 플러그인은 같은 JSON 을 읽어 throw 로 옮긴다.
"""
import json
import os
import re
import sys

# manifest 를 읽지 못할 때의 최후 방어선. manifest.tsv 의 write_scope 와 같아야 한다.
DEFAULT_SCOPES = {
    "reviewer": ("_workspace/",),
    "orchestrator": ("_workspace/",),
    "dependency-mapper": (),
}

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "roles", "manifest.tsv")


def load_readonly_roles():
    """manifest.tsv 의 write_scope 에서 읽기 전용 역할을 만든다.

    '*'(제한 없음)은 가드 대상이 아니므로 건너뛴다. '-'는 전면 금지(빈 튜플)다.
    파일이 없거나 형식이 깨졌으면 DEFAULT_SCOPES 로 물러난다 — 가드가 죽어서 모든 도구를
    막는 쪽이 훨씬 나쁘다.
    """
    try:
        roles = {}
        with open(MANIFEST, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 4:
                    continue
                rid, scope = parts[0].strip(), parts[3].strip()
                if scope == "*":
                    continue
                roles[rid] = () if scope == "-" else tuple(
                    s.strip() for s in scope.split(",") if s.strip())
        return roles or DEFAULT_SCOPES
    except Exception:
        return DEFAULT_SCOPES


READONLY_ROLES = load_readonly_roles()

# 도구 이름은 하네스마다 다르다(Write/write/write_file, Bash/shell/exec, apply_patch …).
# 소문자로 접어 비교한다.
WRITE_TOOLS = {
    "write", "edit", "multiedit", "notebookedit", "patch",
    "apply_patch", "write_file", "str_replace_editor",
}
SHELL_TOOLS = {"bash", "shell", "exec", "local_shell", "run_command"}

# 이름으로 쓰기 도구를 알아내는 패턴. **MCP 도구 때문에 필요하다.**
# 고정 목록만 보면 `serena_replace_content`·`mcp__x__write_file` 같은 것이 그대로 통과한다
# (실측: reviewer 가 serena_replace_content 로 소스를 고치는 것을 관측했다).
WRITE_TOOL_PATTERN = re.compile(
    r"(write|edit|patch|replace|create|delete|remove|insert|rename|move|append|mkdir)",
    re.I)

# 위 패턴에 걸리지만 파일시스템을 건드리지 않는 것들. 읽기 전용 역할도 써야 한다.
WRITE_TOOL_EXEMPT = {
    "todowrite", "todoread", "todo_write", "todo_read", "todo",
    "update_plan", "write_todos", "exit_plan_mode",
}

# 인자에서 대상 경로를 찾을 때 볼 키들 (하네스별·MCP 서버별 표기 차이).
PATH_KEYS = (
    "file_path", "filePath", "notebook_path", "notebookPath", "path", "target_file",
    "relative_path", "relativePath", "filepath", "file", "target_path", "targetPath",
    "new_path", "newPath", "dest", "destination", "output_path", "outputPath",
)
PATH_LIST_KEYS = ("paths", "file_paths", "filePaths", "files")
COMMAND_KEYS = ("command", "cmd", "script")

# 패치 본문이 담기는 키. 경로가 인자가 아니라 본문 안에 있는 도구들이다.
# OpenCode 의 apply_patch 는 patchText, Codex 는 input 을 쓴다 (둘 다 실측).
PATCH_BODY_KEYS = ("patchText", "patch_text", "input", "patch", "content", "diff")

# 셸 안에서 파일을 바꾸는 구문들. 리다이렉션은 대상 경로를 따로 검사한다.
MUTATING_COMMANDS = [
    (re.compile(r"\bsed\b[^|;&]*\s-i\b"), "sed -i (제자리 편집)"),
    (re.compile(r"\bperl\b[^|;&]*\s-i\b"), "perl -i (제자리 편집)"),
    (re.compile(r"\b(rm|rmdir)\s"), "rm/rmdir (삭제)"),
    (re.compile(r"\b(mv|cp|install)\s"), "mv/cp/install (파일 생성·이동)"),
    (re.compile(r"\b(truncate|dd|shred)\s"), "truncate/dd/shred"),
    (re.compile(r"\b(chmod|chown|ln)\s"), "chmod/chown/ln"),
    (re.compile(r"\b(mkdir|touch)\s"), "mkdir/touch (파일·디렉터리 생성)"),
    (re.compile(r"\bgit\s+(commit|apply|checkout|reset|restore|stash|clean|rm|add)\b"),
     "git 쓰기 명령"),
    (re.compile(r"\bnpm\s+(i|install|ci)\b|\bpip\s+install\b"), "패키지 설치"),
    (re.compile(r"\btee\b"), "tee (파일 쓰기)"),
]

# `> path` / `>> path` — `2>&1`, `>&2` 같은 fd 복제는 제외한다.
REDIRECT = re.compile(r"(?<![0-9&])>>?\s*([^\s;|&()<>]+)")

ALWAYS_OK_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr"}

# apply_patch 본문에서 대상 파일을 뽑는다 (`*** Add File: path` 형식).
PATCH_FILE = re.compile(r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s*(.+)$", re.M)


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def allowed(path, prefixes):
    """path 가 허용 접두사 안에 있는가. 상위로 빠져나가는 경로는 거부한다."""
    p = str(path).strip().strip("\"'")
    if p in ALWAYS_OK_TARGETS:
        return True
    if p.startswith("/") or p.startswith("~"):
        return False          # 절대 경로는 작업 트리 밖 — 허용하지 않는다
    if ".." in p.split("/"):
        return False
    p = p[2:] if p.startswith("./") else p
    return any(p.startswith(pre) for pre in prefixes)


def scope_text(prefixes):
    return " 또는 ".join(prefixes) + " 아래" if prefixes else "어디에도 (조사 전용 역할)"


def _first(mapping, keys):
    for k in keys:
        v = mapping.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def normalize(data, harness):
    """하네스별 페이로드를 (역할, 도구, 인자) 로 정규화한다.

    도구 이름과 인자 키는 하네스마다 다르지만 의미는 같다. 역할 식별자만 위치가 크게 다르다:
        claude    agent_type
        codex     agent_role / agentRole / agent_type / agentType,
                  또는 source.subagent.thread_spawn.<같은 키>
        opencode  플러그인이 세션→역할 맵에서 찾아 agent 로 채워 준다
                  (tool.execute.before 자체에는 역할이 없다 — adapters/opencode.md 참고)
    """
    role = _first(data, ("agent_type", "agentType", "agent_role", "agentRole", "agent"))

    if not role and harness in ("codex", "auto"):
        source = data.get("source")
        if isinstance(source, dict):
            sub = source.get("subagent")
            spawn = sub.get("thread_spawn") if isinstance(sub, dict) else None
            if isinstance(spawn, dict):
                role = _first(spawn, ("agent_role", "agentRole", "agent_type", "agentType"))

    tool = _first(data, ("tool_name", "toolName", "tool"))
    args = data.get("tool_input")
    if not isinstance(args, dict):
        args = data.get("args") if isinstance(data.get("args"), dict) else {}

    return role.strip().lower(), tool.strip(), args


def main():
    harness = "auto"
    argv = sys.argv[1:]
    if "--harness" in argv:
        i = argv.index("--harness")
        if i + 1 < len(argv):
            harness = argv[i + 1].strip().lower()

    try:
        data = json.load(sys.stdin)
    except Exception:
        # 입력을 못 읽으면 판단할 근거가 없다. 조용히 통과시킨다 —
        # 깨진 가드가 모든 도구를 막는 쪽이 더 나쁘다.
        return 0
    if not isinstance(data, dict):
        return 0

    role, tool, args = normalize(data, harness)
    if role not in READONLY_ROLES:
        return 0                      # 메인 스레드이거나 가드 대상이 아닌 역할

    prefixes = READONLY_ROLES[role]
    tool_key = tool.lower()

    is_write = (tool_key in WRITE_TOOLS
                or (tool_key not in WRITE_TOOL_EXEMPT
                    and tool_key not in SHELL_TOOLS
                    and WRITE_TOOL_PATTERN.search(tool_key)))

    if is_write:
        targets = [args[k] for k in PATH_KEYS if isinstance(args.get(k), str) and args[k].strip()]
        for k in PATH_LIST_KEYS:
            v = args.get(k)
            if isinstance(v, list):
                targets += [x for x in v if isinstance(x, str) and x.strip()]

        # apply_patch 류는 경로가 본문 안에 있다. 키 이름은 하네스마다 다르다 —
        # OpenCode 는 patchText, Codex 는 input 을 쓴다 (실측).
        if not targets:
            body = ""
            for k in PATCH_BODY_KEYS:
                if isinstance(args.get(k), str):
                    body = args[k]
                    break
            targets = [m.strip() for m in PATCH_FILE.findall(body)]

        # 경로를 못 찾았는데 쓰기 도구를 부른 읽기 전용 역할은 거부한다.
        # 무엇을 쓰는지 알 수 없는 쓰기는 허용할 근거가 없다.
        if not targets:
            deny(f"[harness-architect] {role} 는 읽기 전용 역할입니다. "
                 f"'{tool}' 의 대상 경로를 확인할 수 없어 거부합니다 — "
                 f"쓰기 허용 범위: {scope_text(prefixes)}.")

        for path in targets:
            if not allowed(path, prefixes):
                deny(f"[harness-architect] {role} 는 읽기 전용 역할입니다. "
                     f"'{path}' 에 쓸 수 없습니다 — 쓰기 허용 범위: {scope_text(prefixes)}. "
                     f"발견 사항은 고치지 말고 보고서에 적으십시오. "
                     f"(references/catalog.md 의 도구 경계)")
        return 0

    if tool_key in SHELL_TOOLS:
        cmd = _first(args, COMMAND_KEYS)
        if not cmd:
            # Codex 는 배열 형태(argv)로 넘기기도 한다.
            for k in COMMAND_KEYS + ("argv",):
                v = args.get(k)
                if isinstance(v, list):
                    cmd = " ".join(str(x) for x in v)
                    break

        for pattern, label in MUTATING_COMMANDS:
            if pattern.search(cmd):
                deny(f"[harness-architect] {role} 는 읽기 전용 역할입니다. "
                     f"{label} 을(를) 쓸 수 없습니다 — 쓰기 허용 범위: {scope_text(prefixes)}. "
                     f"명령: {cmd[:160]}")

        for target in REDIRECT.findall(cmd):
            if target.startswith("&"):
                continue              # >&2 같은 fd 복제
            if not allowed(target, prefixes):
                deny(f"[harness-architect] {role} 는 읽기 전용 역할입니다. "
                     f"'{target}' 로 리다이렉션할 수 없습니다 — "
                     f"쓰기 허용 범위: {scope_text(prefixes)}. 명령: {cmd[:160]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
