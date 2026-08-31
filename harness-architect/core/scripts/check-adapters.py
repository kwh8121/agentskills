#!/usr/bin/env python3
"""check-adapters.py — 하네스 어댑터 3종이 같은 계약을 선언하는지 검사한다.

사용법:
    python3 check-adapters.py [저장소_루트]     (기본값: core/ 의 부모)

종료코드:
    0  통과 (검사 대상이 없을 때도 0 — 설치본에는 어댑터 트리가 없다)
    1  파리티 위반 — 하네스마다 다르게 동작하게 된다
    2  검사기를 돌릴 수 없다 (manifest 없음 등)

왜 필요한가:
    역할 7종·도구 경계·모델 등급은 core/roles/manifest.tsv 한 곳에서 정하고,
    세 어댑터 트리가 그것을 각자의 문법으로 다시 쓴다. 다시 쓰는 순간 드리프트가
    시작되므로(Claude 만 고치고 Codex 를 빼먹는 식) 기계가 일치를 강제한다.

    tier→모델 매핑의 진실의 원천은 references/adapters/<하네스>.md 의 tier_map 표다.
    이 검사기는 역할 파일의 모델이 그 표와 같은지 본다 — 문서가 코드를 따라가는 것이
    아니라 코드가 문서를 따라간다.
"""
import os
import re
import sys

EXIT_OK, EXIT_INVALID, EXIT_CANNOT_RUN = 0, 1, 2

# references/adapters/README.md 의 "필수 키 7종" 과 같아야 한다.
REQUIRED_KEYS = ["skill_dir", "dispatch", "tier_map", "skill_call",
                 "superpowers_roots", "guard", "worktree"]

HARNESSES = {
    "claude":   {"doc": "claude-code.md", "tree": "claude/.claude/agents",   "ext": ".md"},
    "codex":    {"doc": "codex.md",       "tree": "codex/.codex/agents",     "ext": ".toml"},
    "opencode": {"doc": "opencode.md",    "tree": "opencode/.opencode/agent", "ext": ".md"},
}

CAP_TOOLS = {
    "claude": {"read": ["Read"], "search": ["Grep", "Glob"], "edit": ["Edit"],
               "write": ["Write"], "bash": ["Bash"], "dispatch": ["Agent"]},
    "opencode": {"read": ["read"], "search": ["grep", "glob", "list"],
                 "edit": ["edit", "patch"], "write": ["write"], "bash": ["bash"],
                 "dispatch": ["task"]},
}
OPENCODE_ALL_TOOLS = ["read", "grep", "glob", "list", "bash", "edit", "patch",
                      "write", "task", "webfetch"]

errors, warnings = [], []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def load_manifest(core):
    """roles/manifest.tsv → [(id, tier, capabilities, write_scope)]"""
    text = read(os.path.join(core, "roles", "manifest.tsv"))
    if text is None:
        return None
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            err("manifest.tsv", f"열이 4개가 아닙니다: {line!r}")
            continue
        rows.append((parts[0].strip(), parts[1].strip(),
                     [c for c in parts[2].split(",") if c], parts[3].strip()))
    return rows


def parse_tier_map(doc_text, doc_name):
    """어댑터 문서의 `## tier_map` 표에서 tier → (모델, 추론강도) 를 뽑는다."""
    section = re.search(r"^##\s+tier_map\s*$(.*?)(?=^##\s|\Z)", doc_text, re.M | re.S)
    if not section:
        err(doc_name, "## tier_map 절이 없습니다")
        return {}
    out = {}
    for row in re.finditer(r"^\|\s*`([a-z]+)`\s*\|([^|]*)\|(.*)$", section.group(1), re.M):
        tier = row.group(1)
        model = row.group(2).strip().strip("`| ")
        rest = [c.strip().strip("`") for c in row.group(3).split("|") if c.strip()]
        effort = rest[0] if rest else None
        out[tier] = (model, effort)
    return out


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def check_claude(path, rid, tier, caps, tiers, where):
    text = read(path)
    if text is None:
        err(where, "파일이 없습니다")
        return
    fm = frontmatter(text)
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    if not name or name.group(1) != rid:
        err(where, f"frontmatter 의 name 이 '{rid}' 가 아닙니다")
    model = re.search(r"^model:\s*(\S+)", fm, re.M)
    want = tiers.get(tier, (None, None))[0]
    if not model:
        err(where, "model 이 없습니다")
    elif want and model.group(1) != want:
        err(where, f"model '{model.group(1)}' 이 tier_map[{tier}]='{want}' 와 다릅니다")
    tools_line = re.search(r"^tools:\s*(.+)$", fm, re.M)
    if not tools_line:
        err(where, "tools 가 없습니다")
    else:
        got = {t.strip() for t in tools_line.group(1).split(",") if t.strip()}
        expect = {t for c in caps for t in CAP_TOOLS["claude"].get(c, [])}
        if got != expect:
            err(where, f"tools {sorted(got)} 가 capabilities {caps} → {sorted(expect)} 와 다릅니다")
    if f"roles/{rid}.md" not in text:
        err(where, f"역할 본문(roles/{rid}.md)을 가리키지 않습니다")


def check_codex(path, rid, tier, caps, tiers, where):
    text = read(path)
    if text is None:
        err(where, "파일이 없습니다")
        return
    name = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
    if not name or name.group(1) != rid:
        err(where, f"name 이 '{rid}' 가 아닙니다")
    model = re.search(r'^model\s*=\s*"([^"]+)"', text, re.M)
    effort = re.search(r'^model_reasoning_effort\s*=\s*"([^"]+)"', text, re.M)
    want_model, want_effort = tiers.get(tier, (None, None))
    if not model:
        err(where, "model 이 없습니다")
    elif want_model and model.group(1) != want_model:
        err(where, f"model '{model.group(1)}' 이 tier_map[{tier}]='{want_model}' 와 다릅니다")
    if not effort:
        err(where, "model_reasoning_effort 가 없습니다 — model 만 주면 추론 강도가 조용히 기본값으로 돌아갑니다")
    elif want_effort and effort.group(1) != want_effort:
        err(where, f"reasoning_effort '{effort.group(1)}' 가 tier_map[{tier}]='{want_effort}' 와 다릅니다")
    if f"roles/{rid}.md" not in text:
        err(where, f"역할 본문(roles/{rid}.md)을 가리키지 않습니다")
    # Codex 는 도구 목록을 강제하지 않으므로 경계가 산문으로라도 적혀 있어야 한다.
    if "쓰기 경계" not in text:
        err(where, "쓰기 경계가 developer_instructions 에 적혀 있지 않습니다")


def check_opencode(path, rid, tier, caps, tiers, where):
    text = read(path)
    if text is None:
        err(where, "파일이 없습니다")
        return
    fm = frontmatter(text)
    model = re.search(r"^model:\s*(\S+)", fm, re.M)
    want = tiers.get(tier, (None, None))[0]
    if not model:
        err(where, "model 이 없습니다")
    elif want and model.group(1) != want:
        err(where, f"model '{model.group(1)}' 이 tier_map[{tier}]='{want}' 와 다릅니다")
    if not re.search(r"^mode:\s*subagent\s*$", fm, re.M):
        err(where, "mode: subagent 가 없습니다 — 서브에이전트로 노출되지 않습니다")

    allowed = {t for c in caps for t in CAP_TOOLS["opencode"].get(c, [])}
    for tool in OPENCODE_ALL_TOOLS:
        m = re.search(rf"^\s+{tool}:\s*(true|false)\s*$", fm, re.M)
        if not m:
            err(where, f"tools.{tool} 선언이 없습니다 (선언적 경계가 이 하네스의 1차 방어선입니다)")
            continue
        want_bool = "true" if tool in allowed else "false"
        if m.group(1) != want_bool:
            err(where, f"tools.{tool}={m.group(1)} 이 capabilities {caps} 와 다릅니다 (기대: {want_bool})")

    # tools: 블록에도 edit 키가 있으므로 permission: 이후만 본다.
    perm_block = fm.split("permission:", 1)[1] if "permission:" in fm else ""
    edit_perm = re.search(r"^\s+edit:\s*(\S+)\s*$", perm_block, re.M)
    want_perm = "allow" if "edit" in caps else "deny"
    if not edit_perm:
        err(where, "permission.edit 이 없습니다")
    elif edit_perm.group(1) != want_perm:
        err(where, f"permission.edit={edit_perm.group(1)} (기대: {want_perm})")
    if f"roles/{rid}.md" not in text:
        err(where, f"역할 본문(roles/{rid}.md)을 가리키지 않습니다")


def main():
    core = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(core)

    rows = load_manifest(core)
    if rows is None:
        print("check-adapters: roles/manifest.tsv 를 읽을 수 없습니다.", file=sys.stderr)
        return EXIT_CANNOT_RUN
    if not rows:
        print("check-adapters: manifest 가 비어 있습니다.", file=sys.stderr)
        return EXIT_CANNOT_RUN

    # 역할 본문이 전부 있는가 — 어댑터가 가리키는 대상이다.
    for rid, *_ in rows:
        if not os.path.isfile(os.path.join(core, "roles", f"{rid}.md")):
            err("core/roles", f"{rid}.md 본문이 없습니다")

    present = [h for h, c in HARNESSES.items() if os.path.isdir(os.path.join(root, c["tree"]))]
    if not present:
        print(f"check-adapters: {root} 아래에 어댑터 트리가 없습니다 — "
              f"설치본에서는 검사할 것이 없습니다. (통과)")
        return EXIT_OK

    for harness, cfg in HARNESSES.items():
        doc_path = os.path.join(core, "references", "adapters", cfg["doc"])
        doc = read(doc_path)
        if doc is None:
            err(f"adapters/{cfg['doc']}", "어댑터 문서가 없습니다")
            continue
        for key in REQUIRED_KEYS:
            if not re.search(rf"^##\s+{re.escape(key)}\s*$", doc, re.M):
                err(f"adapters/{cfg['doc']}", f"필수 키 '## {key}' 절이 없습니다")

        tiers = parse_tier_map(doc, f"adapters/{cfg['doc']}")
        for t in ("fast", "standard", "deep"):
            if t not in tiers:
                err(f"adapters/{cfg['doc']}", f"tier_map 에 '{t}' 가 없습니다")

        tree = os.path.join(root, cfg["tree"])
        if harness not in present:
            warn(harness, f"어댑터 트리({cfg['tree']})가 없어 역할 검사를 건너뜁니다")
            continue

        declared = {f[: -len(cfg["ext"])] for f in os.listdir(tree) if f.endswith(cfg["ext"])}
        expected = {rid for rid, *_ in rows}
        for extra in sorted(declared - expected):
            err(f"{cfg['tree']}", f"manifest 에 없는 역할 '{extra}' 가 선언돼 있습니다")
        for missing in sorted(expected - declared):
            err(f"{cfg['tree']}", f"역할 '{missing}' 이 없습니다")

        for rid, tier, caps, _scope in rows:
            path = os.path.join(tree, rid + cfg["ext"])
            where = f"{cfg['tree']}/{rid}{cfg['ext']}"
            if harness == "claude":
                check_claude(path, rid, tier, caps, tiers, where)
            elif harness == "codex":
                check_codex(path, rid, tier, caps, tiers, where)
            else:
                check_opencode(path, rid, tier, caps, tiers, where)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    if errors:
        print(f"\ncheck-adapters: 파리티 위반 {len(errors)}건 — "
              f"하네스마다 다르게 동작하게 됩니다.")
        return EXIT_INVALID
    print(f"check-adapters: 하네스 {len(present)}종 · 역할 {len(rows)}종 파리티 통과 "
          f"(경고 {len(warnings)}건)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
