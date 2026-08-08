/**
 * Read-only API client. The frontend only ever issues same-origin GET
 * requests plus the SSE stream; it never reads the file system, never runs
 * Git and never writes anything back.
 */
import type { DashboardSnapshot, ErrorEnvelope, Health, ProjectConsole, TaskDetail } from "../generated/contracts.types";
import { SchemaViolationError, tryParseErrorEnvelope, validateContract } from "./schema";

export type ApiFailure =
  | { kind: "network"; message: string }
  | { kind: "http"; status: number; error: ErrorEnvelope | null }
  | { kind: "schema"; error: SchemaViolationError };

export type ApiResult<T> = { ok: true; value: T } | { ok: false; failure: ApiFailure };

async function getJson(
  url: string,
  etag?: string,
): Promise<(ApiResult<unknown> & { etag?: string | null }) | "not-modified"> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: etag ? { "If-None-Match": etag } : {},
      credentials: "same-origin",
    });
  } catch (error) {
    return {
      ok: false,
      failure: { kind: "network", message: error instanceof Error ? error.message : String(error) },
    };
  }
  if (response.status === 304) {
    return "not-modified";
  }
  let payload: unknown = null;
  let text: string;
  try {
    // Headers may arrive before the connection drops: a failing body read is
    // a network failure, not a silent success.
    text = await response.text();
  } catch (error) {
    return {
      ok: false,
      failure: { kind: "network", message: error instanceof Error ? error.message : String(error) },
    };
  }
  if (text.length > 0) {
    try {
      payload = JSON.parse(text);
    } catch {
      return { ok: false, failure: { kind: "http", status: response.status, error: null } };
    }
  }
  if (!response.ok) {
    return { ok: false, failure: { kind: "http", status: response.status, error: tryParseErrorEnvelope(payload) } };
  }
  return { ok: true, value: payload, etag: response.headers.get("etag") };
}

export interface SnapshotReply {
  snapshot: DashboardSnapshot;
  etag: string | null;
}

export interface ConsoleReply {
  console: ProjectConsole;
  etag: string | null;
}

export async function fetchConsole(etag?: string): Promise<ApiResult<ConsoleReply | null>> {
  const result = await getJson("/api/v1/console", etag);
  if (result === "not-modified") {
    return { ok: true, value: null };
  }
  if (!result.ok) {
    return result;
  }
  try {
    const console = validateContract<ProjectConsole>("ProjectConsole", result.value);
    return { ok: true, value: { console, etag: result.etag ?? null } };
  } catch (error) {
    return { ok: false, failure: { kind: "schema", error: error as SchemaViolationError } };
  }
}

export async function fetchSnapshot(etag?: string): Promise<ApiResult<SnapshotReply | null>> {
  const result = await getJson("/api/v1/snapshot", etag);
  if (result === "not-modified") {
    return { ok: true, value: null };
  }
  if (!result.ok) {
    return result;
  }
  try {
    const snapshot = validateContract<DashboardSnapshot>("DashboardSnapshot", result.value);
    return { ok: true, value: { snapshot, etag: result.etag ?? null } };
  } catch (error) {
    return { ok: false, failure: { kind: "schema", error: error as SchemaViolationError } };
  }
}

export async function fetchTaskDetail(taskId: string): Promise<ApiResult<TaskDetail>> {
  const result = await getJson(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
  if (result === "not-modified") {
    // Task detail requests never send If-None-Match; a 304 here is a server bug.
    return { ok: false, failure: { kind: "http", status: 304, error: null } };
  }
  if (!result.ok) {
    return result;
  }
  try {
    return { ok: true, value: validateContract<TaskDetail>("TaskDetail", result.value) };
  } catch (error) {
    return { ok: false, failure: { kind: "schema", error: error as SchemaViolationError } };
  }
}

export async function fetchHealth(): Promise<ApiResult<Health>> {
  const result = await getJson("/api/v1/health");
  if (result === "not-modified") {
    // Health requests never send If-None-Match; a 304 here is a server bug.
    return { ok: false, failure: { kind: "http", status: 304, error: null } };
  }
  if (!result.ok) {
    return result;
  }
  try {
    return { ok: true, value: validateContract<Health>("Health", result.value) };
  } catch (error) {
    return { ok: false, failure: { kind: "schema", error: error as SchemaViolationError } };
  }
}

/** Fixture mode (development/tests): load a versioned fixture, strictly validated. */
export async function fetchFixtureSnapshot(name: string): Promise<ApiResult<SnapshotReply>> {
  let payload: unknown;
  try {
    const response = await fetch(`/fixtures/v1/${encodeURIComponent(name)}.json`, { credentials: "same-origin" });
    if (!response.ok) {
      return { ok: false, failure: { kind: "http", status: response.status, error: null } };
    }
    payload = await response.json();
  } catch (error) {
    return {
      ok: false,
      failure: { kind: "network", message: error instanceof Error ? error.message : String(error) },
    };
  }
  try {
    const snapshot = validateContract<DashboardSnapshot>("DashboardSnapshot", payload);
    return { ok: true, value: { snapshot, etag: null } };
  } catch (error) {
    return { ok: false, failure: { kind: "schema", error: error as SchemaViolationError } };
  }
}
