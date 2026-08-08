/**
 * Shared helpers for the phase-2 browser tests.
 *
 * Every synthetic payload is assembled from the versioned contract fixtures
 * (via tests/support.ts makers, which clone fresh.json) and strictly
 * validated through the same `validateContract` path the runtime uses. The
 * mock backend middleware re-validates server-side; nothing here maintains a
 * private wire model.
 */
import type { Page } from "@playwright/test";
import type {
  DashboardSnapshot,
  ProjectConsole,
  ConsoleItem,
  ErrorEnvelope,
  Provenance,
  SnapshotEvent,
  TaskDetail,
  WorktreeSnapshot,
} from "../../src/generated/contracts.types";
import { validateContract } from "./validate";
import {
  makeAction,
  makeAssessment,
  makeDependsOn,
  makeDiagnostic,
  makePlainEdge,
  makeTask,
  readFixtureJson,
  readFixtureText,
  sha,
} from "../makers";

/** Clone the versioned `fresh` fixture, apply overrides, strictly validate. */
function makeSnapshot(overrides: Record<string, unknown> = {}): DashboardSnapshot {
  const base = JSON.parse(readFixtureText("fresh.json")) as Record<string, unknown>;
  return validateContract<DashboardSnapshot>("DashboardSnapshot", { ...base, ...overrides });
}

export const BASE = "http://127.0.0.1:5173";

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`mock control ${path} failed: HTTP ${response.status} ${await response.text()}`);
  }
}

export function mockReset(): Promise<void> {
  return post("/__mock__/reset", {});
}

export function mockSetSnapshot(snapshot: DashboardSnapshot): Promise<void> {
  return post("/__mock__/snapshot", { snapshot });
}

export function mockSetConsole(console: ProjectConsole): Promise<void> {
  return post("/__mock__/console", { console });
}

export function makeConsoleItem(overrides: Partial<ConsoleItem> = {}): ConsoleItem {
  return {
    task_id: "TASK-ALPHA",
    title: "示例任务",
    queue: "ready_queue",
    actor: "agent",
    session_id: null,
    harness_id: null,
    phase: null,
    next_step: "继续执行任务",
    status_summary: "任务已 Ready，可按授权边界继续",
    why_now_codes: ["DEPENDENCIES_SATISFIED"],
    blocking_task_ids: [],
    unblocks_count: 0,
    priority: "medium",
    last_activity_at: null,
    freshness: "fresh",
    source_kinds: ["task", "git"],
    branch: null,
    worktree: null,
    action_kind: "execute",
    action_eligibility: "actionable",
    action_kinds: ["execute"],
    action_eligibilities: ["actionable"],
    ...overrides,
  };
}

export function makeProjectConsole(
  snapshot: DashboardSnapshot,
  overrides: Partial<ProjectConsole> = {},
): ProjectConsole {
  const base: ProjectConsole = {
    schema_version: "adf/project-console/v1",
    revision: snapshot.revision,
    snapshot_revision: snapshot.revision,
    generated_at: new Date().toISOString(),
    state: "fresh",
    freshness: {
      task_facts_at: new Date(Date.now() - 8_000).toISOString(),
      git_facts_at: new Date(Date.now() - 3_000).toISOString(),
      runtime_facts_at: new Date(Date.now() - 12_000).toISOString(),
    },
    counts: { active_work: 0, human_attention: 0, ready_queue: 0, blocked: 0, stale_sessions: 0 },
    active_work: [],
    human_attention: [],
    ready_queue: [],
    blocked: [],
    stale_sessions: [],
    recent_changes: [],
    ambiguity: { has_unique_primary: false, candidate_count: 0, message: "当前没有唯一主任务" },
    disclaimer: "Project Console 是只读投影。",
  };
  const result = { ...base, ...overrides };
  result.counts = {
    active_work: result.active_work.length,
    human_attention: result.human_attention.length,
    ready_queue: result.ready_queue.length,
    blocked: result.blocked.length,
    stale_sessions: result.stale_sessions.length,
  };
  return validateContract<ProjectConsole>("ProjectConsole", result);
}

export function mockSendEvent(event: SnapshotEvent): Promise<void> {
  return post("/__mock__/event", { event });
}

export function mockSetSseDown(down: boolean): Promise<void> {
  return post("/__mock__/sse", { down });
}

export function mockSetTaskError(envelope: ErrorEnvelope | null): Promise<void> {
  return post("/__mock__/task-error", { envelope });
}

/** Test-only hook: inject an unvalidated raw SSE frame (protocol-error path). */
export function mockSendRawEvent(frame: string): Promise<void> {
  return post("/__mock__/raw-event", { frame });
}

/** Test-only hook: the next snapshot 200 reply drops the connection mid-body. */
export function mockTruncateSnapshot(): Promise<void> {
  return post("/__mock__/truncate", {});
}

/** Strictly validated synthetic TaskDetail for route-fulfilled race tests. */
export function makeTaskDetail(
  snapshot: DashboardSnapshot,
  taskId: string,
  taskOverrides: Record<string, unknown> = {},
): TaskDetail {
  const task = snapshot.tasks.find((item) => item.task_id === taskId);
  if (!task) {
    throw new Error(`snapshot has no task ${taskId}`);
  }
  return validateContract<TaskDetail>("TaskDetail", {
    schema_version: "ai-dev-flow/dashboard-task-detail/v1",
    revision: snapshot.revision,
    task: { ...task, ...taskOverrides },
    edges: snapshot.edges.filter((e) => e.source_task_id === taskId || e.target_task_id === taskId),
    actions: snapshot.actions.filter((a) => a.task_id === taskId),
    parallel_assessments: snapshot.parallel_assessments.filter(
      (a) => a.left_task_id === taskId || a.right_task_id === taskId,
    ),
    diagnostics: snapshot.diagnostics.filter((d) => d.task_ids.includes(taskId)),
  });
}

/** Strictly validated synthetic SSE event. */
export function makeEvent(revision: string, state: "fresh" | "stale" | "partial", resetRequired: boolean): SnapshotEvent {
  return validateContract<SnapshotEvent>("SnapshotEvent", {
    schema_version: "ai-dev-flow/dashboard-event/v1",
    revision,
    state,
    changed_task_ids: [],
    reset_required: resetRequired,
  });
}

/** Distinct Sha256-shaped revision for revision-change assertions. */
export function rev(char: string): string {
  return char.repeat(64);
}

/** Versioned task-detail error envelope fixture, strictly validated. */
export function taskDetailErrorEnvelope(): ErrorEnvelope {
  return validateContract<ErrorEnvelope>("ErrorEnvelope", readFixtureJson("task-detail-error.json"));
}

export function makeProvenance(seed: number, sourcePath: string): Provenance {
  return {
    source_path: sourcePath,
    heading: `第 ${seed} 节`,
    field: "lifecycle",
    line: seed,
    raw_value: "Ready",
    source_type: "canonical",
  };
}

export function makeWorktree(root: string, branch: string | null, headSeed: number): WorktreeSnapshot {
  return {
    root,
    head: sha(headSeed),
    branch,
    detached: false,
    locked: false,
    prunable: false,
    dirty_state: "clean",
    dirty_paths: [],
    diagnostic_ids: [],
  };
}

export const GRAPH_TASKS = ["TASK-ALPHA", "TASK-BETA", "TASK-GAMMA", "TASK-DELTA", "TASK-EPSILON"] as const;

/**
 * Rich synthetic graph snapshot cloned from the versioned fresh fixture and
 * strictly validated. Five tasks, one edge of every relationship type, one
 * candidate and one must_serial assessment, actions covering the frozen
 * action matrix (blocked / needs_authority / actionable / plan), diagnostics,
 * provenance and worktree evidence. Every action is a matrix-legal
 * kind/eligibility/authority/reason combination — the frontend never sees
 * synthetic states the backend could not emit.
 */
export function buildGraphSnapshot(revisionSeed = 900): DashboardSnapshot {
  const alpha = makeTask("TASK-ALPHA", {
    contract_schema_version: "adf/v0.10.0",
    review_requirement: "Not Required",
    review_state: "Not Run",
    lifecycle: "Ready",
    task_class: "A",
    module_locks: ["core"],
    write_scope: ["src/core"],
    branch_hint: "feat/alpha",
    provenance: [makeProvenance(7, "docs/tasks/TASK-ALPHA.md")],
  });
  const beta = makeTask("TASK-BETA", {
    lifecycle: "Ready",
    task_class: "B",
    module_locks: ["core"],
    write_scope: ["src/core"],
  });
  const gamma = makeTask("TASK-GAMMA", { lifecycle: "Review", task_class: "C" });
  const delta = makeTask("TASK-DELTA", { lifecycle: "Review", review_status: "Passed", ua_status: "Pending", task_class: "C" });
  const epsilon = makeTask("TASK-EPSILON", {
    lifecycle: "Draft",
    task_class: null,
    freshness: "stale",
    risk_flags: ["high-risk"],
  });

  const edges = [
    makeDependsOn(101, "TASK-BETA", "TASK-ALPHA", "unsatisfied"),
    makeDependsOn(102, "TASK-GAMMA", "TASK-ALPHA", "satisfied"),
    makePlainEdge(103, "parent", "TASK-DELTA", "TASK-ALPHA"),
    makePlainEdge(104, "discovered_from", "TASK-EPSILON", "TASK-DELTA"),
    makePlainEdge(105, "conflicts_with", "TASK-BETA", "TASK-EPSILON"),
    makePlainEdge(106, "replaces", "TASK-GAMMA", "TASK-DELTA"),
  ];

  const actions = [
    // Matrix row 9: Review + Passed + UA pending — first in wire order.
    makeAction(304, "TASK-DELTA", {
      action_kind: "user_decision",
      eligibility: "actionable",
      reason_codes: ["USER_DECISION_PENDING"],
      required_authority: "user_decision",
      authority_state: "not_required",
    }),
    // Matrix row 6: Ready + all dependencies satisfied.
    makeAction(301, "TASK-ALPHA", {
      evidence: [makeProvenance(9, "docs/tasks/TASK-ALPHA.md")],
    }),
    // Matrix row 5: Ready + an unsatisfied dependency.
    makeAction(302, "TASK-BETA", {
      eligibility: "blocked",
      reason_codes: ["DEPENDENCY_UNSATISFIED"],
      blocking_task_ids: ["TASK-ALPHA"],
      blocking_condition_ids: [sha(101)],
    }),
    // Matrix row 8: Review + review pending.
    makeAction(303, "TASK-GAMMA", {
      action_kind: "review",
      reason_codes: ["REVIEW_AUTHORITY_UNSUPPORTED"],
      required_authority: "review",
    }),
    // Matrix row 3: Draft.
    makeAction(305, "TASK-EPSILON", {
      action_kind: "plan",
      reason_codes: ["PLANNING_DECISION_REQUIRED"],
      required_authority: "user_decision",
      authority_state: "missing",
    }),
  ];

  const alphaWorktree = makeWorktree("D:/fixture-wt-alpha", "refs/heads/feat/alpha", 500);
  const assessments = [
    makeAssessment(201, "TASK-ALPHA", "TASK-DELTA", "candidate", ["ALL_CHECKS_PASSED"]),
    makeAssessment(202, "TASK-BETA", "TASK-GAMMA", "must_serial", ["WRITE_SCOPE_OVERLAP", "MODULE_LOCK_OVERLAP"]),
  ];
  (assessments[0] as Record<string, unknown>).worktree_evidence = [alphaWorktree];

  const diagnostics = [
    makeDiagnostic(401, "error", ["TASK-EPSILON"]),
    makeDiagnostic(402, "warning", ["TASK-BETA"]),
  ];

  const zeroLifecycle = {
    Accepted: 0,
    Blocked: 0,
    Cancelled: 0,
    Closed: 0,
    Deferred: 0,
    Draft: 0,
    "In Progress": 0,
    "Needs Fix": 0,
    Ready: 0,
    Review: 0,
  };
  const snapshot = makeSnapshot({
    revision: sha(revisionSeed),
    state: "fresh",
    tasks: [alpha, beta, gamma, delta, epsilon],
    edges,
    actions,
    parallel_assessments: assessments,
    diagnostics,
    stale_sources: [],
    project: {
      root: "D:/fixture",
      branch: "codex/dashboard-fe-001",
      head: sha(600),
      dirty: false,
      git_state: "ok",
      worktrees: [alphaWorktree],
    },
    summary: {
      task_total: 5,
      edge_total: edges.length,
      action_total: actions.length,
      counts_by_lifecycle: { ...zeroLifecycle, Ready: 2, Review: 2, Draft: 1 },
      counts_by_action: {
        plan: 1,
        execute: 2,
        continue: 0,
        review: 1,
        repair: 0,
        user_decision: 1,
        commit: 0,
        merge: 0,
        release: 0,
        close: 0,
        none: 0,
      },
      counts_by_relation: { depends_on: 2, parent: 1, replaces: 1, discovered_from: 1, conflicts_with: 1 },
      counts_by_severity: { error: 1, violation: 0, warning: 1, info: 0 },
    },
  });
  return snapshot;
}

/** Clone the graph snapshot under a new revision (strictly re-validated). */
export function reviseSnapshot(base: DashboardSnapshot, revision: string): DashboardSnapshot {
  return validateContract<DashboardSnapshot>("DashboardSnapshot", {
    ...JSON.parse(JSON.stringify(base)),
    revision,
  });
}

/** Persist a screenshot under artifacts/screenshots/ (git-ignored evidence). */
export async function shot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `artifacts/screenshots/${name}.png`, fullPage: false });
}
