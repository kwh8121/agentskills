# agentskills

Claude Code 스킬 모음. 각 하위 폴더가 독립적으로 설치 가능한 스킬 하나다 —
`<skill>/.claude/` 를 프로젝트 루트에 복사하면 그대로 동작한다.

## 스킬 목록

| 스킬 | 설명 |
|---|---|
| [`harness-architect`](./harness-architect) | 개발 업무를 6축으로 프로파일링해 최소 하네스(H0~H3)를 판정하고, 실행 계약(HarnessSpec)을 산출해 승인받은 뒤 그 구조대로 실행하는 라우터 스킬. 도구 경계를 frontmatter + 훅으로 이중 강제하고, 진행 상황을 Linear에 남길 수 있다. |
