/**
 * harness-guard — 읽기 전용 역할이 소스를 쓰는 것을 OpenCode 에서 막는다.
 *
 * 왜 플러그인이 필요한가:
 *   1차 경계는 역할 파일(.opencode/agent/*.md)의 tools/permission 이다. 그것으로
 *   edit·write 계열은 막히지만, bash 를 가진 역할이 `sed -i`·리다이렉션으로 우회하는
 *   것은 못 막는다. 그 간극을 경로 기준 판정으로 메운다.
 *
 * 어떻게 역할을 아는가:
 *   tool.execute.before 는 {tool, sessionID, callID} 만 준다 — 역할이 없다.
 *   chat.params / chat.headers 가 {sessionID, agent} 를 주므로 거기서 세션→역할 맵을
 *   만들어 두고 조회한다. (references/adapters/opencode.md 의 guard 절)
 *
 * 판정은 하지 않는다:
 *   허용/거부 판정은 세 하네스가 공유하는 scripts/guard-readonly.py 하나가 한다.
 *   이 파일은 페이로드를 정규화해 넘기고 결과를 throw 로 옮기기만 한다.
 *
 * 한계:
 *   python3 가 없거나 스크립트를 못 부르면 **통과시킨다**. 깨진 가드가 모든 도구를
 *   막는 쪽이 더 나쁘다. 샌드박스가 아니라 규율 장치다.
 */
import { spawn } from "node:child_process";
import path from "node:path";

const GUARD_REL = ".opencode/skills/harness-architect/scripts/guard-readonly.py";

export const HarnessGuardPlugin = async ({ directory }) => {
  const guardPath = path.join(directory ?? process.cwd(), GUARD_REL);
  const sessionAgent = new Map();

  const askGuard = (payload) =>
    new Promise((resolve) => {
      let child;
      try {
        child = spawn("python3", [guardPath, "--harness", "opencode"], {
          stdio: ["pipe", "pipe", "ignore"],
        });
      } catch {
        return resolve(null);
      }
      let out = "";
      child.stdout.on("data", (chunk) => {
        out += chunk;
      });
      child.on("error", () => resolve(null));
      child.on("close", () => {
        if (!out.trim()) return resolve(null); // 출력 없음 = 허용
        try {
          resolve(JSON.parse(out));
        } catch {
          resolve(null);
        }
      });
      child.stdin.on("error", () => {});
      child.stdin.end(JSON.stringify(payload));
    });

  const remember = async (input) => {
    if (input?.sessionID && input?.agent) sessionAgent.set(input.sessionID, input.agent);
  };

  return {
    "chat.params": remember,
    "chat.headers": remember,

    "tool.execute.before": async (input, output) => {
      const agent = sessionAgent.get(input?.sessionID);
      if (!agent) return; // 역할을 모르면 판단 근거가 없다 — 메인 세션도 여기로 온다

      const verdict = await askGuard({
        agent,
        tool: input.tool,
        args: output?.args ?? {},
      });

      const decision = verdict?.hookSpecificOutput;
      if (decision?.permissionDecision === "deny") {
        throw new Error(decision.permissionDecisionReason);
      }
    },
  };
};

export default HarnessGuardPlugin;
