/**
 * Shared test fixtures. Every synthetic payload is assembled from the
 * versioned contract fixtures and strictly validated through the same
 * `validateContract` path the runtime uses — tests never hand-maintain a
 * private wire model. The pure makers live in tests/makers.ts so the
 * Playwright Node side can reuse them without a JSON-module import.
 */
import type { DashboardSnapshot } from "../src/generated/contracts.types";
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
