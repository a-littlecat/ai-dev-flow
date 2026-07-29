/**
 * Pure fixture makers shared by unit tests (tests/support.ts) and browser
 * tests (tests/browser/*). No schema imports here so Playwright's loader can
 * resolve this module without JSON import attributes; validation lives in
 * the callers (src/api/schema for the app/vitest, tests/browser/validate.ts
 * for the Playwright Node side).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const FIXTURES_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../contracts/fixtures/v1",
);

export function readFixtureText(name: string): string {
  return readFileSync(path.join(FIXTURES_DIR, name), "utf-8");
}

export function readFixtureJson(name: string): unknown {
  return JSON.parse(readFixtureText(name));
}

/** Deterministic Sha256-shaped id for synthetic payloads. */
export function sha(seed: number): string {
  return seed.toString(16).padStart(64, "0").slice(-64);
}

export function makeTask(taskId: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    task_id: taskId,
    title: `任务 ${taskId}`,
    source_path: `docs/tasks/${taskId}.md`,
    task_type: "code",
    task_class: "C",
    lifecycle: "Ready",
    review_status: "Pending",
    ua_level: "UA4",
    ua_status: "Pending",
    acceptance_authority: "None",
    commit_status: "Uncommitted",
    merge_status: "Unmerged",
    merge_authority: "None",
    close_authority: "None",
    unsupported_axes: [],
    scheduling_state: "canonical",
    priority: "high",
    risk_flags: [],
    write_scope: [],
    module_locks: [],
    parallel_intent: "consider",
    worktree_requirement: "required",
    branch_hint: null,
    freshness: "fresh",
    diagnostic_ids: [],
    provenance: [],
    ...overrides,
  };
}

export function makeDependsOn(
  edgeSeed: number,
  dependent: string,
  prerequisite: string,
  evaluation: "satisfied" | "unsatisfied" | "unknown" = "satisfied",
): Record<string, unknown> {
  return {
    edge_id: sha(edgeSeed),
    type: "depends_on",
    source_task_id: dependent,
    target_task_id: prerequisite,
    condition: {
      axis: "lifecycle",
      operator: "eq",
      expected: "Accepted",
      actual: evaluation === "satisfied" ? "Accepted" : null,
      evaluation,
    },
    storage_direction: "dependent_to_prerequisite",
    display_direction: "prerequisite_to_dependent",
    directional: true,
    origin: "canonical",
    provenance: [],
  };
}

export function makePlainEdge(
  edgeSeed: number,
  type: "parent" | "replaces" | "discovered_from" | "conflicts_with",
  source: string,
  target: string,
): Record<string, unknown> {
  const direction = {
    parent: ["child_to_parent", "parent_to_child"],
    replaces: ["replacement_to_replaced", "replaced_to_replacement"],
    discovered_from: ["discovered_to_origin", "origin_to_discovered"],
    conflicts_with: ["symmetric", "symmetric"],
  }[type];
  return {
    edge_id: sha(edgeSeed),
    type,
    source_task_id: source,
    target_task_id: target,
    condition: null,
    storage_direction: direction[0],
    display_direction: direction[1],
    directional: type !== "conflicts_with",
    origin: "canonical",
    provenance: [],
  };
}

export function makeAction(
  actionSeed: number,
  taskId: string,
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  // Default matches the frozen action matrix row 6 (Ready + all dependencies
  // satisfied): execute is never `actionable` without a trusted authority
  // receipt, and matrix rows carry their single canonical reason code.
  return {
    action_id: sha(actionSeed),
    task_id: taskId,
    action_kind: "execute",
    eligibility: "needs_authority",
    reason_codes: ["EXECUTION_AUTHORITY_UNSUPPORTED"],
    blocking_task_ids: [],
    blocking_condition_ids: [],
    related_diagnostic_ids: [],
    required_authority: "execution",
    authority_state: "unsupported",
    evidence: [],
    ...overrides,
  };
}

export function makeAssessment(
  assessmentSeed: number,
  left: string,
  right: string,
  result: "candidate" | "must_serial" | "unknown",
  reasonCodes: string[] = [],
): Record<string, unknown> {
  return {
    assessment_id: sha(assessmentSeed),
    left_task_id: left,
    right_task_id: right,
    result,
    reason_codes: reasonCodes,
    hard_conflicts: [],
    projection_conflicts: [],
    worktree_evidence: [],
    requires_user_confirmation: true,
  };
}

export function makeDiagnostic(
  diagnosticSeed: number,
  severity: "error" | "violation" | "warning" | "info",
  taskIds: string[] = [],
): Record<string, unknown> {
  return {
    diagnostic_id: sha(diagnosticSeed),
    code: `DIAG-${diagnosticSeed}`,
    severity,
    message: `诊断 ${diagnosticSeed}`,
    task_ids: taskIds,
    provenance: [],
  };
}
