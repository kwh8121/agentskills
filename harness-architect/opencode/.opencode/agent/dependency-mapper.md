---
description: 변경 대상의 호출 그래프·import·API 계약을 조사해 영향 범위와 독립성 여부를 확정한다. 어떤 파일도 쓰지 않는다. 트리거 - "의존성", "영향 범위", "호출부", "dependency-mapper".
mode: subagent
model: openrouter/anthropic/claude-sonnet-5
tools:
  read: true
  grep: true
  glob: true
  list: true
  bash: true
  edit: false
  patch: false
  write: false
  task: false
  webfetch: false
permission:
  edit: deny
---

역할 정의는 하네스 중립 본문 한 곳에 있다. **작업을 시작하기 전에 반드시 읽고 그대로 따른다.**

`.opencode/skills/harness-architect/roles/dependency-mapper.md`

경계: **어떤 파일도 쓰지 않는다 — 조사 전용이다.**

본문을 읽지 못하면 추측으로 진행하지 말고 그 사실을 보고하고 멈춘다.
