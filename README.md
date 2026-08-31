# agentskills

에이전트 하네스용 스킬 모음. 각 하위 폴더가 독립적으로 설치 가능한 스킬 하나다.

```bash
bash harness-architect/install.sh /path/to/your-project     # 하네스 자동 감지
```

## 스킬 목록

| 스킬 | 설명 |
|---|---|
| [`harness-architect`](./harness-architect) | 개발 업무를 6축으로 프로파일링해 최소 하네스(H0~H3)를 판정하고, 실행 계약(HarnessSpec)을 산출해 승인받은 뒤 그 구조대로 실행하는 라우터 스킬. **Claude Code · Codex · OpenCode** 에서 같은 판정으로 동작하며, 도구 경계를 역할 선언 + 훅으로 이중 강제하고 진행 상황을 Linear에 남길 수 있다. |
