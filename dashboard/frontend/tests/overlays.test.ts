// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { AppStore } from "../src/state/store";
import { Overlays } from "../src/ui/overlays";
import { makeDiagnostic, makeSnapshot } from "./support";

describe("task ingestion notice", () => {
  it.each(["E_PARSE", "E_TASK_ID_CONFLICT", "E_UNKNOWN_VALUE", "E_LEGACY_CONFLICT"])(
    "explains that task files affected by %s may be absent from the graph",
    (code) => {
      const diagnostic = {
        ...makeDiagnostic(701, "error"),
        code,
        message: `TASK ingestion failed: ${code}`,
      };
      const boardDiagnostic = {
        ...makeDiagnostic(702, "error"),
        code: "E_BOARD_PARSE",
        message: "TASK_BOARD could not be parsed",
      };
      const store = new AppStore();
      const base = makeSnapshot();
      store.setSnapshot(
        makeSnapshot({
          diagnostics: [diagnostic, boardDiagnostic],
          summary: {
            ...base.summary,
            counts_by_severity: {
              ...base.summary.counts_by_severity,
              error: 2,
            },
          },
        }),
        null,
        null,
      );
      const overlays = new Overlays(() => undefined);

      overlays.update(store.get());

      const notice = overlays.root.querySelector(".task-ingestion-notice");
      expect(notice?.textContent).toContain(
        "当前共检测到 2 条错误，其中 1 条属于 TASK 解析或 Contract 不兼容错误",
      );
      expect(notice?.textContent).toContain(
        `当前显示 ${store.get().snapshot?.summary.task_total} 个已解析任务`,
      );
      expect(notice?.textContent).toContain("可能导致部分任务未纳入关系图");
      expect(notice?.textContent).toContain("底部“诊断”");
    },
  );

  it.each(["W_LEGACY_INFERRED", "V_STATE_GUARD"])(
    "does not imply missing tasks for %s",
    (code) => {
      const store = new AppStore();
      store.setSnapshot(
        makeSnapshot({
          diagnostics: [
            {
              ...makeDiagnostic(702, "warning"),
              code,
              message: `Non-ingestion diagnostic: ${code}`,
            },
          ],
        }),
        null,
        null,
      );
      const overlays = new Overlays(() => undefined);

      overlays.update(store.get());

      expect(overlays.root.querySelector(".task-ingestion-notice")).toBeNull();
    },
  );
});
