/**
 * Shared test fixtures. Every synthetic payload is assembled from the
 * versioned contract fixtures and strictly validated through the same
 * `validateContract` path the runtime uses — tests never hand-maintain a
 * private wire model. The pure makers live in tests/makers.ts so the
 * Playwright Node side can reuse them without a JSON-module import.
 */
import type { DashboardSnapshot, ProjectConsole } from "../src/generated/contracts.types";
import { validateContract } from "../src/api/schema";
import { readFixtureText } from "./makers";

export {
  FIXTURES_DIR,
  makeAction,
  makeAssessment,
  makeDependsOn,
  makeDiagnostic,
  makePlainEdge,
  makeTask,
  readFixtureJson,
  readFixtureText,
  sha,
} from "./makers";

/**
 * Clone the versioned `fresh` fixture, apply overrides and strictly validate
 * the result. A test payload that drifts from the contract fails here, not in
 * the assertion under test.
 */
export function makeSnapshot(overrides: Record<string, unknown> = {}): DashboardSnapshot {
  const base = JSON.parse(readFixtureText("fresh.json")) as Record<string, unknown>;
  return validateContract<DashboardSnapshot>("DashboardSnapshot", { ...base, ...overrides });
}

export function makeProjectConsole(snapshotRevision: string, overrides: Partial<ProjectConsole> = {}): ProjectConsole {
  const generatedAt = "2026-08-08T12:00:00Z";
  return validateContract<ProjectConsole>("ProjectConsole", {
    schema_version: "adf/project-console/v1",
    revision: snapshotRevision,
    snapshot_revision: snapshotRevision,
    generated_at: generatedAt,
    state: "fresh",
    freshness: { task_facts_at: generatedAt, git_facts_at: generatedAt, runtime_facts_at: generatedAt },
    counts: { active_work: 0, human_attention: 0, ready_queue: 0, blocked: 0, stale_sessions: 0 },
    active_work: [],
    human_attention: [],
    ready_queue: [],
    blocked: [],
    stale_sessions: [],
    recent_changes: [],
    ambiguity: { has_unique_primary: false, candidate_count: 0, message: "当前没有唯一主任务" },
    disclaimer: "只读投影",
    ...overrides,
  });
}
