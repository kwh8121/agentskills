---
description: 완성된 diff 를 수용 기준 기준으로 심사한다. 코드를 고치지 않고 발견만 보고한다. 트리거 - "리뷰", "코드 리뷰", "심사", "reviewer".
mode: subagent
model: openrouter/anthropic/claude-opus-5
tools:
  read: true
  grep: true
  glob: true
  list: true
  bash: true
  edit: false
  patch: false
  write: true
  task: false
  webfetch: false
permission:
  edit: deny
---

역할 정의는 하네스 중립 본문 한 곳에 있다. **작업을 시작하기 전에 반드시 읽고 그대로 따른다.**

`.opencode/skills/harness-architect/roles/reviewer.md`

경계: **`_workspace/` 아래에만 쓴다.** 그 밖의 경로는 읽기만 한다.

본문을 읽지 못하면 추측으로 진행하지 말고 그 사실을 보고하고 멈춘다.
