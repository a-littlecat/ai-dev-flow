import { describe, expect, it } from "vitest";
import { derive } from "../src/state/derive";
import { deriveOverview } from "../src/state/overview";
import { makeAction, makeAssessment, makeSnapshot, makeTask } from "./support";

describe("deriveOverview", () => {
  it("projects only explicit action, candidate, in-progress and waiting facts", () => {
    const tasks = [
      makeTask("DECISION", { lifecycle: "Review" }),
      makeTask("CANDIDATE"),
      makeTask("PAIR"),
      makeTask("ACTIVE", { lifecycle: "In Progress" }),
      makeTask("BLOCKED", { lifecycle: "Blocked" }),
      makeTask("BLOCKER", { lifecycle: "In Progress" }),
      makeTask("UNKNOWN"),
    ];
    const actions = [
      makeAction(2, "DECISION", {
        action_kind: "user_decision",
        eligibility: "needs_authority",
        required_authority: "user_decision",
        authority_state: "missing",
        reason_codes: ["USER_DECISION_PENDING"],
      }),
      makeAction(1, "ACTIVE", { eligibility: "actionable", required_authority: "none", authority_state: "not_required" }),
      makeAction(3, "BLOCKED", {
        eligibility: "blocked",
        reason_codes: ["DEPENDENCY_UNSATISFIED"],
        blocking_task_ids: ["BLOCKER"],
      }),
    ];
    const parallelAssessments = [
      makeAssessment(10, "DECISION", "CANDIDATE", "candidate", ["ALL_CHECKS_PASSED"]),
      makeAssessment(11, "DECISION", "UNKNOWN", "unknown", ["WORKTREE_EVIDENCE_UNKNOWN"]),
    ];
    const snapshot = makeSnapshot({ tasks, actions, parallel_assessments: parallelAssessments, edges: [], diagnostics: [] });

    const overview = deriveOverview(snapshot, derive(snapshot));

    expect(overview.current?.task.task_id).toBe("DECISION");
    expect(overview.parallelSuggestions.map((item) => item.task.task_id)).toEqual(["CANDIDATE"]);
    expect(overview.parallelSuggestions[0]?.counterpart.task_id).toBe("DECISION");
    expect(overview.activeTasks.map((item) => item.task.task_id)).toEqual(["ACTIVE", "BLOCKER"]);
    expect(overview.waiting.map((item) => item.task.task_id)).toEqual(["BLOCKED"]);
    expect(overview.waiting[0]?.counterpart?.task_id).toBe("BLOCKER");
    expect(overview.hiddenTaskCount).toBe(2);
  });

  it("preserves backend wire order when choosing the current action", () => {
    const tasks = [makeTask("FIRST"), makeTask("LATER", { lifecycle: "Review" })];
    const snapshot = makeSnapshot({
      tasks,
      actions: [
        makeAction(1, "FIRST"),
        makeAction(2, "LATER", {
          action_kind: "user_decision",
          eligibility: "actionable",
          required_authority: "user_decision",
          authority_state: "not_required",
          reason_codes: ["USER_DECISION_PENDING"],
        }),
      ],
      parallel_assessments: [],
      edges: [],
      diagnostics: [],
    });

    expect(deriveOverview(snapshot, derive(snapshot)).current?.task.task_id).toBe("FIRST");
    const reversed = { ...snapshot, actions: [...snapshot.actions].reverse() };
    expect(deriveOverview(reversed, derive(reversed)).current?.task.task_id).toBe("LATER");
  });

  it("keeps unknown assessments out of parallel suggestions", () => {
    const tasks = [makeTask("A"), makeTask("B")];
    const snapshot = makeSnapshot({
      tasks,
      actions: [makeAction(1, "A")],
      parallel_assessments: [makeAssessment(2, "A", "B", "unknown", ["WORKTREE_EVIDENCE_UNKNOWN"])],
      edges: [],
      diagnostics: [],
    });

    const overview = deriveOverview(snapshot, derive(snapshot));

    expect(overview.parallelSuggestions).toEqual([]);
    expect(overview.hiddenTaskCount).toBe(1);
  });

  it("does not invent a blocking task for an authority-blocked action", () => {
    const tasks = [makeTask("CURRENT", { lifecycle: "Review" }), makeTask("DENIED", { lifecycle: "Accepted" })];
    const snapshot = makeSnapshot({
      tasks,
      actions: [
        makeAction(1, "CURRENT", {
          action_kind: "user_decision",
          eligibility: "actionable",
          required_authority: "user_decision",
          authority_state: "not_required",
          reason_codes: ["USER_DECISION_PENDING"],
        }),
        makeAction(1, "DENIED", {
          action_kind: "merge",
          eligibility: "blocked",
          required_authority: "merge",
          authority_state: "denied",
          reason_codes: ["MERGE_AUTHORITY_DENIED"],
          blocking_task_ids: [],
        }),
      ],
      parallel_assessments: [],
      edges: [],
      diagnostics: [],
    });

    const overview = deriveOverview(snapshot, derive(snapshot));

    expect(overview.waiting).toHaveLength(1);
    expect(overview.waiting[0]?.kind).toBe("action_blocked");
    expect(overview.waiting[0]?.counterpart).toBeNull();
    expect(overview.waiting[0]?.action?.reason_codes).toEqual(["MERGE_AUTHORITY_DENIED"]);
  });
});
