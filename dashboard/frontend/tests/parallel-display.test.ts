// @vitest-environment jsdom
/**
 * Display-semantics tests for parallel assessments (candidate / must_serial /
 * unknown): evidence views must show all three states with text (never colour
 * alone), while the graph only reveals actionable assessment links on demand.
 */
import { beforeAll, describe, expect, it } from "vitest";
import { AppStore } from "../src/state/store";
import { Toolbar } from "../src/ui/toolbar";
import { GraphView } from "../src/ui/graph/graphView";
import { PARALLEL_RESULT_LABEL } from "../src/ui/labels";
import { makeAssessment, makeSnapshot, makeTask } from "./support";

beforeAll(() => {
  // jsdom has no matchMedia; GraphView only reads `.matches`.
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
});

function storeWithAssessments(): AppStore {
  const store = new AppStore();
  store.setSnapshot(
    makeSnapshot({
      tasks: [makeTask("CAND-A"), makeTask("CAND-B"), makeTask("SER-A"), makeTask("SER-B"), makeTask("UNK-A"), makeTask("UNK-B")],
      parallel_assessments: [
        makeAssessment(101, "CAND-A", "CAND-B", "candidate", ["ALL_CHECKS_PASSED"]),
        makeAssessment(102, "SER-A", "SER-B", "must_serial", ["WRITE_SCOPE_OVERLAP"]),
        makeAssessment(103, "UNK-A", "UNK-B", "unknown", ["WORKTREE_EVIDENCE_UNKNOWN"]),
      ],
    }),
    null,
    null,
  );
  return store;
}

describe("parallel assessment display semantics", () => {
  it("labels cover all three wire results", () => {
    expect(PARALLEL_RESULT_LABEL.candidate).toContain("非授权");
    expect(PARALLEL_RESULT_LABEL.must_serial).toBe("必须串行");
    expect(PARALLEL_RESULT_LABEL.unknown).toBe("并行未知");
  });

  it("pair list renders all three results with localized text and the non-authority warning", () => {
    const store = storeWithAssessments();
    const toolbar = new Toolbar(store);
    toolbar.update(store.get());
    const text = toolbar.root.textContent ?? "";
    expect(text).toContain("候选 ≠ 授权");
    expect(text).toContain("并行候选（需用户确认，非授权）");
    expect(text).toContain("必须串行");
    expect(text).toContain("并行未知");
    // Reason codes are localized, not raw wire values.
    expect(text).toContain("全部检查通过");
    expect(text).toContain("写范围重叠");
    expect(text).toContain("Worktree 证据未知");
    expect(text).not.toContain("ALL_CHECKS_PASSED");
  });

  it("candidate highlight chip counts only candidate-pair tasks", () => {
    const store = storeWithAssessments();
    const toolbar = new Toolbar(store);
    toolbar.update(store.get());
    const chips = [...toolbar.root.querySelectorAll("button")].map((b) => b.textContent ?? "");
    expect(chips.some((label) => label.startsWith("并行候选（2）"))).toBe(true);
  });

  it("keeps the task-source live region stable during viewport-only updates", () => {
    const store = storeWithAssessments();
    const toolbar = new Toolbar(store);
    toolbar.update(store.get());
    const source = toolbar.root.querySelector(".task-source-summary");
    expect(source).not.toBeNull();
    expect(source?.getAttribute("role")).toBe("status");

    store.setViewport({ x: 25, y: 40, k: 1.2 });
    toolbar.update(store.get());
    expect(toolbar.root.querySelector(".task-source-summary")).toBe(source);
  });

  it("graph marks candidate tasks with a non-authority tag and leaves unknown/must_serial tasks untagged", () => {
    const store = storeWithAssessments();
    const graph = new GraphView(store);
    graph.update(store.get());

    const tagged = [...graph.root.querySelectorAll(".node-candidate-tag")].map((node) =>
      node.closest(".node")?.getAttribute("data-task-id"),
    );
    expect(tagged.sort()).toEqual(["CAND-A", "CAND-B"]);
    for (const node of graph.root.querySelectorAll(".node-candidate-tag")) {
      expect(node.textContent).toContain("非授权");
    }

    const assessmentLabels = [...graph.root.querySelectorAll(".assessment-label")].map((node) => node.textContent ?? "");
    expect(assessmentLabels).toEqual([]);
    expect(graph.root.querySelector(".legend-note")?.textContent).toContain(
      "关系图已收起 3 条并行评估以避免遮挡",
    );
    expect(graph.root.querySelector(".legend-note")?.textContent).toContain(
      "“并行未知”仅在列表 / 详情中显示",
    );

    store.setHighlight("candidates");
    graph.update(store.get());
    let visibleAssessmentLabels = [...graph.root.querySelectorAll(".assessment-label")].map(
      (node) => node.textContent ?? "",
    );
    expect(visibleAssessmentLabels.some((text) => text.includes("并行候选"))).toBe(true);
    expect(visibleAssessmentLabels.some((text) => text.includes("必须串行"))).toBe(false);

    store.selectTask("SER-A");
    graph.update(store.get());
    visibleAssessmentLabels = [...graph.root.querySelectorAll(".assessment-label")].map(
      (node) => node.textContent ?? "",
    );
    expect(visibleAssessmentLabels.some((text) => text.includes("必须串行"))).toBe(true);
    expect(visibleAssessmentLabels.some((text) => text.includes("并行未知"))).toBe(false);
    expect(graph.root.querySelectorAll(".assessment-unknown")).toHaveLength(0);

    const titles = [...graph.root.querySelectorAll(".assessment-link title")].map(
      (node) => node.textContent ?? "",
    );
    expect(titles.length).toBeGreaterThan(0);
    expect(titles.every((text) => text.includes("requires_user_confirmation=true"))).toBe(true);
  });

  it("graph nodes always carry text state (lifecycle + next action), not colour alone", () => {
    const store = storeWithAssessments();
    const graph = new GraphView(store);
    graph.update(store.get());
    const nodes = [...graph.root.querySelectorAll(".node")];
    expect(nodes.length).toBe(6);
    for (const node of nodes) {
      const text = node.textContent ?? "";
      expect(text).toContain("状态：");
      expect(text).toContain("下一步：");
    }
  });

  it("resets the assessment legend when a later snapshot is empty", () => {
    const store = storeWithAssessments();
    const graph = new GraphView(store);
    graph.update(store.get());
    expect(graph.root.querySelector(".legend-note")?.textContent).toContain(
      "关系图已收起 3 条并行评估以避免遮挡",
    );

    store.setSnapshot(
      makeSnapshot({
        tasks: [],
        edges: [],
        actions: [],
        parallel_assessments: [],
        diagnostics: [],
      }),
      null,
      null,
    );
    graph.update(store.get());
    expect(graph.root.querySelector(".legend-note")?.textContent).toBe(
      "图中关系均带文字/符号；候选不代表已授权执行。",
    );
  });
});
