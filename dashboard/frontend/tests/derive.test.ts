/**
 * Unit tests for the derived read-only projections and filters in
 * src/state/derive.ts. All snapshots are built from the versioned fixtures
 * and strictly validated (see tests/support.ts).
 */
import { describe, expect, it } from "vitest";
import {
  derive,
  emptyFilters,
  filterTasks,
  filtersActive,
  focusClosure,
  highlightCounts,
  highlightTasks,
  resolveSelectionAfterFilter,
  taskMatchesText,
} from "../src/state/derive";
import { layoutGraph, layeringFlow } from "../src/ui/graph/layout";
import type { RelationshipEdge } from "../src/generated/contracts.types";
import {
  makeAction,
  makeAssessment,
  makeDependsOn,
  makeDiagnostic,
  makePlainEdge,
  makeSnapshot,
  makeTask,
  sha,
} from "./support";

function baseSnapshot() {
  return makeSnapshot({
    tasks: [
      makeTask("TASK-A", { lifecycle: "In Progress", risk_flags: ["public_api"], module_locks: ["ui"] }),
      makeTask("TASK-B", { lifecycle: "Ready" }),
      makeTask("TASK-C", { lifecycle: "Review", review_status: "Passed", ua_status: "Pending", freshness: "stale" }),
    ],
    edges: [
      makeDependsOn(101, "TASK-A", "TASK-B", "unsatisfied"),
      makePlainEdge(102, "parent", "TASK-B", "TASK-C"),
      makePlainEdge(103, "conflicts_with", "TASK-A", "TASK-C"),
    ],
    actions: [
      // Matrix row 7: In Progress -> continue / needs_authority.
      makeAction(201, "TASK-A", { action_kind: "continue", reason_codes: ["CONTINUE_AUTHORITY_UNSUPPORTED"] }),
      // Matrix row 6: Ready + all dependencies satisfied -> execute / needs_authority.
      makeAction(202, "TASK-B"),
      // Matrix row 9: Review + Passed + UA pending -> user_decision / actionable.
      makeAction(203, "TASK-C", {
        action_kind: "user_decision",
        eligibility: "actionable",
        reason_codes: ["USER_DECISION_PENDING"],
        required_authority: "user_decision",
        authority_state: "not_required",
      }),
    ],
    parallel_assessments: [
      makeAssessment(301, "TASK-A", "TASK-B", "candidate", ["ALL_CHECKS_PASSED"]),
      makeAssessment(302, "TASK-A", "TASK-C", "must_serial", ["WRITE_SCOPE_OVERLAP"]),
      makeAssessment(303, "TASK-B", "TASK-C", "unknown", ["WORKTREE_EVIDENCE_UNKNOWN"]),
    ],
    diagnostics: [
      makeDiagnostic(401, "warning", ["TASK-A"]),
      makeDiagnostic(402, "error", ["TASK-A", "TASK-B"]),
      makeDiagnostic(403, "info", []),
    ],
  });
}

describe("derive", () => {
  it("indexes actions per task and picks the first wire-order action as primary", () => {
    const derived = derive(baseSnapshot());
    expect(derived.actionsByTask.get("TASK-A")?.length).toBe(1);
    expect(derived.primaryActionByTask.get("TASK-A")?.action_kind).toBe("continue");
    expect(derived.primaryActionByTask.get("TASK-B")?.action_kind).toBe("execute");
    expect(derived.primaryActionByTask.get("TASK-B")?.eligibility).toBe("needs_authority");
    expect(derived.primaryActionByTask.get("TASK-C")?.action_kind).toBe("user_decision");
  });

  it("never re-ranks multiple recommendations: primary follows server wire order", () => {
    // A merged task legally carries two recommendations (matrix rows 13a +
    // 13b): release first, then close. Even though close is actionable and
    // release is unknown, the frontend must not promote close.
    const mergedTask = makeTask("TASK-M", {
      lifecycle: "Accepted",
      commit_status: "Committed",
      merge_status: "Merged",
      close_authority: "User Authorized",
    });
    const release = makeAction(210, "TASK-M", {
      action_kind: "release",
      eligibility: "unknown",
      reason_codes: ["RELEASE_AXIS_UNSUPPORTED"],
      required_authority: "release",
      authority_state: "unsupported",
    });
    const close = makeAction(211, "TASK-M", {
      action_kind: "close",
      eligibility: "actionable",
      reason_codes: ["CLOSE_AUTHORITY_PRESENT"],
      required_authority: "close",
      authority_state: "present",
    });

    const canonical = derive(makeSnapshot({ tasks: [mergedTask], actions: [release, close] }));
    expect(canonical.actionsByTask.get("TASK-M")?.map((a) => a.action_kind)).toEqual(["release", "close"]);
    expect(canonical.primaryActionByTask.get("TASK-M")?.action_kind).toBe("release");

    // If the wire order were ever reversed, the frontend mirrors it as-is;
    // blocked / needs_authority / unknown are never re-sorted by the UI.
    const reversed = derive(makeSnapshot({ tasks: [mergedTask], actions: [close, release] }));
    expect(reversed.actionsByTask.get("TASK-M")?.map((a) => a.action_kind)).toEqual(["close", "release"]);
    expect(reversed.primaryActionByTask.get("TASK-M")?.action_kind).toBe("close");
  });

  it("indexes parallel assessments on both sides of the pair", () => {
    const derived = derive(baseSnapshot());
    expect(derived.assessmentsByTask.get("TASK-A")?.length).toBe(2);
    expect(derived.assessmentsByTask.get("TASK-B")?.length).toBe(2);
    expect(derived.assessmentsByTask.get("TASK-C")?.length).toBe(2);
    const results = (derived.assessmentsByTask.get("TASK-A") ?? []).map((a) => a.result).sort();
    expect(results).toEqual(["candidate", "must_serial"]);
  });

  it("merges diagnostics from task_ids and computes the worst severity", () => {
    const snapshot = baseSnapshot();
    // Also reference a diagnostic through task.diagnostic_ids to exercise the merge.
    const taskA = snapshot.tasks.find((t) => t.task_id === "TASK-A");
    expect(taskA).toBeDefined();
    (taskA?.diagnostic_ids as string[]).push(sha(403));
    const derived = derive(snapshot);
    const aDiags = derived.diagnosticsByTask.get("TASK-A") ?? [];
    expect(aDiags.map((d) => d.severity).sort()).toEqual(["error", "info", "warning"]);
    expect(derived.worstSeverityByTask.get("TASK-A")).toBe("error");
    expect(derived.worstSeverityByTask.get("TASK-B")).toBe("error");
    expect(derived.worstSeverityByTask.get("TASK-C")).toBeUndefined();
  });

  it("builds upstream/downstream with display direction and excludes conflicts_with", () => {
    const derived = derive(baseSnapshot());
    // depends_on TASK-A -> TASK-B displays as prerequisite(TASK-B) -> dependent(TASK-A).
    expect([...(derived.upstream.get("TASK-A") ?? [])]).toEqual(["TASK-B"]);
    expect([...(derived.downstream.get("TASK-B") ?? [])]).toEqual(["TASK-A"]);
    // parent TASK-B -> TASK-C displays as parent(TASK-C) -> child(TASK-B).
    expect([...(derived.upstream.get("TASK-B") ?? [])].sort()).toEqual(["TASK-C"]);
    // conflicts_with is symmetric: neither upstream nor downstream.
    expect(derived.upstream.get("TASK-C") ?? new Set()).not.toContain("TASK-A");
    expect(derived.downstream.get("TASK-C") ?? new Set()).not.toContain("TASK-A");
  });

  it("matches a task to its worktree only on a unique branch_hint match", () => {
    const worktree = {
      root: "D:/wt/task-a",
      head: sha(501),
      branch: "refs/heads/codex/task-a",
      detached: false,
      locked: false,
      prunable: false,
      dirty_state: "clean",
      dirty_paths: [],
      diagnostic_ids: [],
    };
    const snapshot = makeSnapshot({
      tasks: [makeTask("TASK-A", { branch_hint: "codex/task-a" }), makeTask("TASK-B", { branch_hint: "codex/missing" })],
      project: {
        root: "D:/fixture",
        branch: "main",
        head: sha(500),
        dirty: false,
        git_state: "ok",
        worktrees: [worktree],
      },
    });
    const derived = derive(snapshot);
    expect(derived.worktreeByTask.get("TASK-A")?.root).toBe("D:/wt/task-a");
    expect(derived.worktreeByTask.has("TASK-B")).toBe(false);
  });
});

describe("filterTasks", () => {
  it("empty filters keep every task and report inactive", () => {
    const snapshot = baseSnapshot();
    const derived = derive(snapshot);
    const filters = emptyFilters();
    expect(filtersActive(filters)).toBe(false);
    expect(filterTasks(snapshot, derived, filters).size).toBe(3);
  });

  it("filters by text, lifecycle, risk, class, module, worktree root and severity", () => {
    const snapshot = baseSnapshot();
    const derived = derive(snapshot);
    const base = emptyFilters();

    expect([...filterTasks(snapshot, derived, { ...base, text: "task-b" })]).toEqual(["TASK-B"]);
    expect([...filterTasks(snapshot, derived, { ...base, lifecycles: ["Ready"] })]).toEqual(["TASK-B"]);
    expect([...filterTasks(snapshot, derived, { ...base, riskFlags: ["public_api"] })]).toEqual(["TASK-A"]);
    expect([...filterTasks(snapshot, derived, { ...base, taskClasses: ["C"] })]).toHaveLength(3);
    expect([...filterTasks(snapshot, derived, { ...base, moduleLocks: ["ui"] })]).toEqual(["TASK-A"]);
    expect([...filterTasks(snapshot, derived, { ...base, severities: ["warning"] })]).toEqual(["TASK-A"]);
    expect(filterTasks(snapshot, derived, { ...base, worktreeRoots: ["D:/nowhere"] }).size).toBe(0);
    // AND across groups, OR within a group.
    expect(
      [...filterTasks(snapshot, derived, { ...base, lifecycles: ["Ready", "Accepted"], riskFlags: ["public_api"] })],
    ).toEqual([]);
    expect(filtersActive({ ...base, lifecycles: ["Ready"] })).toBe(true);
  });

  it("filters by action kind via derived actions", () => {
    const snapshot = baseSnapshot();
    const derived = derive(snapshot);
    const filters = { ...emptyFilters(), actionKinds: ["user_decision"] };
    expect([...filterTasks(snapshot, derived, filters)]).toEqual(["TASK-C"]);
  });
});

describe("highlight semantics", () => {
  it("candidates highlight matches only candidate pairs, never unknown or must_serial", () => {
    const snapshot = baseSnapshot();
    const derived = derive(snapshot);
    const candidates = highlightTasks(snapshot, derived, "candidates");
    expect([...candidates].sort()).toEqual(["TASK-A", "TASK-B"]);
    expect(candidates.has("TASK-C")).toBe(false);
    const counts = highlightCounts(snapshot, derived);
    expect(counts.candidates).toBe(2);
  });

  it("actionable highlight matches only actionable, non-none actions", () => {
    const snapshot = baseSnapshot();
    const derived = derive(snapshot);
    expect([...highlightTasks(snapshot, derived, "actionable")]).toEqual(["TASK-C"]);
  });

  it("decisions highlight matches user_decision actions and authority", () => {
    const snapshot = baseSnapshot();
    const derived = derive(snapshot);
    expect([...highlightTasks(snapshot, derived, "decisions")]).toEqual(["TASK-C"]);
  });
});

describe("focusClosure", () => {
  it("walks transitively and is cycle-safe", () => {
    const snapshot = makeSnapshot({
      tasks: [makeTask("CYCLE-A"), makeTask("CYCLE-B"), makeTask("CYCLE-C")],
      edges: [
        makeDependsOn(601, "CYCLE-A", "CYCLE-B"),
        makeDependsOn(602, "CYCLE-B", "CYCLE-C"),
        makeDependsOn(603, "CYCLE-C", "CYCLE-A"),
      ],
    });
    const derived = derive(snapshot);
    expect(focusClosure(derived, "CYCLE-A", "upstream").size).toBe(3);
    expect(focusClosure(derived, "CYCLE-A", "downstream").size).toBe(3);
  });
});

describe("graph layout", () => {
  it("maps every directional edge type target -> source, conflicts to null", () => {
    const depends = makeDependsOn(701, "A", "B") as unknown as RelationshipEdge;
    expect(layeringFlow(depends)).toEqual({ from: "B", to: "A" });
    const conflict = makePlainEdge(702, "conflicts_with", "A", "B") as unknown as RelationshipEdge;
    expect(layeringFlow(conflict)).toBeNull();
    const parent = makePlainEdge(703, "parent", "A", "B") as unknown as RelationshipEdge;
    expect(layeringFlow(parent)).toEqual({ from: "B", to: "A" });
  });

  it("lays out a DAG left to right along the display direction", () => {
    const snapshot = baseSnapshot();
    const layout = layoutGraph(
      snapshot.tasks.map((t) => t.task_id),
      snapshot.edges,
    );
    const a = layout.nodes.get("TASK-A");
    const b = layout.nodes.get("TASK-B");
    const c = layout.nodes.get("TASK-C");
    expect(a && b && c).toBeTruthy();
    // TASK-C is the parent of TASK-B, which is the prerequisite of TASK-A.
    expect(c!.layer).toBeLessThan(b!.layer);
    expect(b!.layer).toBeLessThan(a!.layer);
    expect(layout.cycleEdgeIds.size).toBe(0);
    expect(layout.width).toBeGreaterThan(0);
    expect(layout.height).toBeGreaterThan(0);
  });

  it("flags cycle edges instead of dropping them from the data", () => {
    const edges = [
      makeDependsOn(801, "CYCLE-A", "CYCLE-B") as unknown as RelationshipEdge,
      makeDependsOn(802, "CYCLE-B", "CYCLE-C") as unknown as RelationshipEdge,
      makeDependsOn(803, "CYCLE-C", "CYCLE-A") as unknown as RelationshipEdge,
    ];
    const layout = layoutGraph(["CYCLE-A", "CYCLE-B", "CYCLE-C"], edges);
    expect(layout.cycleEdgeIds.size).toBe(1);
    // Exactly one of the cycle edges is flagged as the DFS back edge; which
    // one depends on traversal order, but it must be one of the three.
    const edgeIds = edges.map((edge) => edge.edge_id);
    expect(edgeIds).toContain([...layout.cycleEdgeIds][0]);
    expect(layout.nodes.size).toBe(3);
  });
});

describe("taskMatchesText", () => {
  const task = makeSnapshot({
    tasks: [makeTask("TASK-GAMMA", { title: "Graph Rendering Polish" })],
  }).tasks[0]!;

  it("matches case-insensitively on task id and title", () => {
    expect(taskMatchesText(task, "gamma")).toBe(true);
    expect(taskMatchesText(task, "GAMMA")).toBe(true);
    expect(taskMatchesText(task, "task-gam")).toBe(true);
    expect(taskMatchesText(task, "rendering")).toBe(true);
    expect(taskMatchesText(task, "POLISH")).toBe(true);
  });

  it("trims the needle and treats a blank needle as match-all", () => {
    expect(taskMatchesText(task, "  gamma  ")).toBe(true);
    expect(taskMatchesText(task, "")).toBe(true);
    expect(taskMatchesText(task, "   ")).toBe(true);
  });

  it("rejects needles present in neither id nor title", () => {
    expect(taskMatchesText(task, "alpha")).toBe(false);
    expect(taskMatchesText(task, "graphx")).toBe(false);
  });

  it("is the exact predicate filterTasks uses for its text filter", () => {
    const snapshot = makeSnapshot({
      tasks: [makeTask("TASK-GAMMA", { title: "Graph Rendering Polish" }), makeTask("TASK-BETA", { title: "Other" })],
    });
    const derived = derive(snapshot);
    const visible = filterTasks(snapshot, derived, { ...emptyFilters(), text: " gamma " });
    expect([...visible]).toEqual(["TASK-GAMMA"]);
  });
});

describe("resolveSelectionAfterFilter", () => {
  it("returns undefined when nothing is selected (never auto-selects)", () => {
    expect(resolveSelectionAfterFilter(new Set(["TASK-A"]), null)).toBeUndefined();
  });

  it("returns undefined when the selection is still visible", () => {
    expect(resolveSelectionAfterFilter(new Set(["TASK-A", "TASK-B"]), "TASK-A")).toBeUndefined();
  });

  it("switches to the single remaining task when the selection left the visible set", () => {
    expect(resolveSelectionAfterFilter(new Set(["TASK-GAMMA"]), "TASK-ALPHA")).toBe("TASK-GAMMA");
  });

  it("clears the selection when zero or multiple tasks remain", () => {
    expect(resolveSelectionAfterFilter(new Set(), "TASK-ALPHA")).toBeNull();
    expect(resolveSelectionAfterFilter(new Set(["TASK-B", "TASK-C"]), "TASK-ALPHA")).toBeNull();
  });
});
