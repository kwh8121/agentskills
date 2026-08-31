---
description: 릴리스 아티팩트·백업·헬스체크·롤백 절차를 준비하고 검증한다. Human Gate 승인 없이는 배포를 실행하지 않는다. 트리거 - "배포", "릴리스", "롤백", "deploy".
mode: subagent
model: openrouter/anthropic/claude-sonnet-5
tools:
  read: true
  grep: false
  glob: false
  list: false
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

`.opencode/skills/harness-architect/roles/deployment-agent.md`

경계: 쓰기 제한 없음 (소스 편집이 이 역할의 일이다)

본문을 읽지 못하면 추측으로 진행하지 말고 그 사실을 보고하고 멈춘다.
