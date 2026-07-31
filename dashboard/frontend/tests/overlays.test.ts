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
      const store = new AppStore();
      store.setSnapshot(
        makeSnapshot({
          diagnostics: [diagnostic],
        }),
        null,
        null,
      );
      const overlays = new Overlays(() => undefined);

      overlays.update(store.get());

      const notice = overlays.root.querySelector(".task-ingestion-notice");
      expect(notice?.textContent).toContain(
        `关系图当前显示 ${store.get().snapshot?.summary.task_total} 个已解析任务`,
      );
      expect(notice?.textContent).toContain("部分任务可能未纳入");
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
