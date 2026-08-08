import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { whyNowLabel } from "../src/ui/projectConsole";

describe("whyNowLabel", () => {
  it("maps machine codes to user-readable copy", () => {
    expect(whyNowLabel("DEPENDENCY_UNSATISFIED")).toBe("仍有前置依赖未满足");
    expect(whyNowLabel("USER_DECISION_PENDING")).toBe("正在等待用户决策");
  });

  it("does not expose an unknown machine code as explanatory copy", () => {
    expect(whyNowLabel("FUTURE_MACHINE_CODE")).toBe("存在未识别的治理条件，请查看诊断码");
  });

  it("maps every fixed reason code emitted directly by ConsoleBuilder", () => {
    const builder = readFileSync(
      new URL("../../backend/src/ai_dev_flow_dashboard/console/builder.py", import.meta.url),
      "utf8",
    );
    const fixedCodes = [...builder.matchAll(/"([A-Z][A-Z0-9_]+)"/g)].map((match) => match[1]!);

    expect(fixedCodes).toContain("ACTIVE_RUNTIME_SESSION");
    expect(new Set(fixedCodes).size).toBe(7);
    for (const code of new Set(fixedCodes)) {
      expect(whyNowLabel(code), code).not.toContain("未识别");
    }
  });
});
