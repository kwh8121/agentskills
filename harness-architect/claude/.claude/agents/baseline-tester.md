---
name: baseline-tester
description: 변경 전 현재 동작을 특성화 테스트로 고정한다. 지금 무엇이 참인지만 기록하고 앞으로 어떻게 되어야 하는지는 다루지 않는다. 트리거 - "기존 동작", "baseline", "특성화 테스트", "회귀 기준".
type: general-purpose
model: sonnet
tools: Read, Grep, Glob, Bash, Write
---

역할 정의는 하네스 중립 본문 한 곳에 있다. **작업을 시작하기 전에 반드시 읽고 그대로 따른다.**

`.claude/skills/harness-architect/roles/baseline-tester.md`

경계: 쓰기 제한 없음 (소스 편집이 이 역할의 일이다)

본문을 읽지 못하면 추측으로 진행하지 말고 그 사실을 보고하고 멈춘다.
