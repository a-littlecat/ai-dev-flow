/**
 * Strict schema validation of every versioned contract fixture and the SSE
 * transcript. These tests guard against frontend/schema drift in both
 * directions: fixtures must pass, and any undocumented mutation must fail.
 */
import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import type { DashboardSnapshot, ErrorEnvelope, SnapshotEvent } from "../src/generated/contracts.types";
import { SchemaViolationError, tryParseErrorEnvelope, validateContract } from "../src/api/schema";
import { FIXTURES_DIR, readFixtureJson, readFixtureText } from "./support";

const SNAPSHOT_FIXTURE_STATES: Record<string, "fresh" | "stale" | "partial"> = {
  "fresh.json": "fresh",
  "stale.json": "stale",
  "partial.json": "partial",
  "parse-error.json": "partial",
  "dependency-cycle.json": "partial",
  "git-degraded.json": "fresh",
  "parallel-unknown.json": "fresh",
};

describe("versioned JSON fixtures", () => {
  it("fixture directory contains exactly the fixtures under test", () => {
    const jsonFiles = readdirSync(FIXTURES_DIR).filter((name) => name.endsWith(".json")).sort();
    expect(jsonFiles).toEqual([...Object.keys(SNAPSHOT_FIXTURE_STATES), "task-detail-error.json"].sort());
    const sseFiles = readdirSync(FIXTURES_DIR).filter((name) => name.endsWith(".sse"));
    expect(sseFiles).toEqual(["events.sse"]);
  });

  for (const [name, expectedState] of Object.entries(SNAPSHOT_FIXTURE_STATES)) {
    it(`${name} passes strict DashboardSnapshot validation`, () => {
      const snapshot = validateContract<DashboardSnapshot>("DashboardSnapshot", readFixtureJson(name));
      expect(snapshot.schema_version).toBe("ai-dev-flow/dashboard-snapshot/v1");
      expect(snapshot.state).toBe(expectedState);
    });
  }

  it("task-detail-error.json passes strict ErrorEnvelope validation", () => {
    const envelope = validateContract<ErrorEnvelope>("ErrorEnvelope", readFixtureJson("task-detail-error.json"));
    expect(envelope.schema_version).toBe("ai-dev-flow/dashboard-error/v1");
    expect(envelope.error.code).toBe("TASK_NOT_FOUND");
  });

  it("task-detail-error.json is rejected as a DashboardSnapshot", () => {
    expect(() => validateContract("DashboardSnapshot", readFixtureJson("task-detail-error.json"))).toThrow(
      SchemaViolationError,
    );
  });
});

describe("SSE transcript (events.sse)", () => {
  interface SseFrame {
    event: string | null;
    id: string | null;
    data: string;
  }

  function parseTranscript(text: string): { retryMs: number | null; frames: SseFrame[] } {
    let retryMs: number | null = null;
    const frames: SseFrame[] = [];
    let current: { event: string | null; id: string | null; data: string[] } | null = null;
    for (const line of text.split(/\r?\n/)) {
      if (line.startsWith("retry:")) {
        retryMs = Number(line.slice("retry:".length).trim());
        continue;
      }
      if (line === "") {
        if (current && current.data.length > 0) {
          frames.push({ event: current.event, id: current.id, data: current.data.join("\n") });
        }
        current = null;
        continue;
      }
      current ??= { event: null, id: null, data: [] };
      if (line.startsWith("event:")) {
        current.event = line.slice("event:".length).trim();
      } else if (line.startsWith("id:")) {
        current.id = line.slice("id:".length).trim();
      } else if (line.startsWith("data:")) {
        current.data.push(line.slice("data:".length).trim());
      }
    }
    return { retryMs, frames };
  }

  it("declares a reconnect retry directive", () => {
    const { retryMs } = parseTranscript(readFixtureText("events.sse"));
    expect(retryMs).toBe(2000);
  });

  it("every snapshot frame passes strict SnapshotEvent validation", () => {
    const { frames } = parseTranscript(readFixtureText("events.sse"));
    expect(frames.length).toBeGreaterThan(0);
    for (const frame of frames) {
      expect(frame.event).toBe("snapshot");
      expect(frame.id).toMatch(/^[0-9a-f]{64}$/);
      const event = validateContract<SnapshotEvent>("SnapshotEvent", JSON.parse(frame.data));
      expect(event.schema_version).toBe("ai-dev-flow/dashboard-event/v1");
      expect(["fresh", "stale", "partial"]).toContain(event.state);
      expect(typeof event.reset_required).toBe("boolean");
    }
  });

  it("the transcript contains a reset_required frame", () => {
    const { frames } = parseTranscript(readFixtureText("events.sse"));
    const events = frames.map((frame) =>
      validateContract<SnapshotEvent>("SnapshotEvent", JSON.parse(frame.data)),
    );
    expect(events.some((event) => event.reset_required)).toBe(true);
  });
});

describe("strict drift rejection", () => {
  function freshClone(): Record<string, unknown> {
    return JSON.parse(readFixtureText("fresh.json")) as Record<string, unknown>;
  }

  it("rejects an undocumented top-level property (additionalProperties: false)", () => {
    const drifted = { ...freshClone(), frontend_extra_field: true };
    expect(() => validateContract("DashboardSnapshot", drifted)).toThrow(SchemaViolationError);
  });

  it("rejects a missing required property", () => {
    const drifted = freshClone();
    delete drifted.revision;
    expect(() => validateContract("DashboardSnapshot", drifted)).toThrow(SchemaViolationError);
  });

  it("rejects an enum value outside the contract", () => {
    const drifted = { ...freshClone(), state: "mostly-fresh" };
    expect(() => validateContract("DashboardSnapshot", drifted)).toThrow(SchemaViolationError);
  });

  it("rejects a changed disclaimer const", () => {
    const drifted = { ...freshClone(), disclaimer: "改写后的免责声明" };
    expect(() => validateContract("DashboardSnapshot", drifted)).toThrow(SchemaViolationError);
  });

  it("rejects a malformed sha256 revision", () => {
    const drifted = { ...freshClone(), revision: "not-a-sha" };
    expect(() => validateContract("DashboardSnapshot", drifted)).toThrow(SchemaViolationError);
  });

  it("SchemaViolationError names the contract kind and issues", () => {
    try {
      validateContract("DashboardSnapshot", { ...freshClone(), state: "nope" });
      expect.unreachable("validation must fail");
    } catch (error) {
      expect(error).toBeInstanceOf(SchemaViolationError);
      const violation = error as SchemaViolationError;
      expect(violation.kind).toBe("DashboardSnapshot");
      expect(violation.issues.length).toBeGreaterThan(0);
      expect(violation.message).toContain("DashboardSnapshot");
    }
  });

  it("tryParseErrorEnvelope returns null for non-envelope payloads", () => {
    expect(tryParseErrorEnvelope(readFixtureJson("fresh.json"))).toBeNull();
    expect(tryParseErrorEnvelope(null)).toBeNull();
    expect(tryParseErrorEnvelope("oops")).toBeNull();
    expect(tryParseErrorEnvelope(readFixtureJson("task-detail-error.json"))?.error.code).toBe("TASK_NOT_FOUND");
  });
});

describe("schema identity", () => {
  it("the versioned schema file declares the expected contract id", () => {
    const schemaPath = path.resolve(FIXTURES_DIR, "../../dashboard-contracts-v1.schema.json");
    const schema = JSON.parse(readFileSync(schemaPath, "utf-8")) as Record<string, unknown>;
    expect(schema.$id).toBe("ai-dev-flow/dashboard-contracts/v1");
    expect(schema.$schema).toBe("https://json-schema.org/draft/2020-12/schema");
  });
});
