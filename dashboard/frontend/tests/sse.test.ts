/**
 * Unit tests for the SSE subscription wrapper: strict validation of every
 * snapshot frame (including the versioned transcript payload), visible
 * protocol-error reporting for malformed frames and connection status
 * reporting.
 */
import { describe, expect, it } from "vitest";
import { SnapshotEventStream } from "../src/api/sse";
import type { SnapshotEvent } from "../src/generated/contracts.types";
import { readFixtureText } from "./support";

type Listener = (event: unknown) => void;

class FakeEventSource {
  static readonly CLOSED = 2;
  readyState = 0;
  readonly url: string;
  private listeners = new Map<string, Listener[]>();
  closed = false;

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, listener: Listener): void {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  }

  removeEventListener(type: string, listener: Listener): void {
    const list = this.listeners.get(type) ?? [];
    this.listeners.set(type, list.filter((item) => item !== listener));
  }

  close(): void {
    this.readyState = FakeEventSource.CLOSED;
    this.closed = true;
  }

  emit(type: string, event: unknown): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

// The wrapper references EventSource.CLOSED in its error handler.
(globalThis as { EventSource?: unknown }).EventSource = FakeEventSource;

function transcriptPayload(): string {
  const text = readFixtureText("events.sse");
  const dataLine = text.split(/\r?\n/).find((line) => line.startsWith("data:"));
  if (!dataLine) {
    throw new Error("events.sse transcript has no data line");
  }
  return dataLine.slice("data:".length).trim();
}

describe("SnapshotEventStream", () => {
  function setup() {
    const events: SnapshotEvent[] = [];
    const statuses: string[] = [];
    const protocolErrors: string[] = [];
    const sources: FakeEventSource[] = [];
    const stream = new SnapshotEventStream(
      {
        onEvent: (event) => events.push(event),
        onStatus: (status) => statuses.push(status),
        onProtocolError: (detail) => protocolErrors.push(detail),
      },
      (url) => {
        const source = new FakeEventSource(url);
        sources.push(source);
        return source as unknown as EventSource;
      },
    );
    return { events, statuses, protocolErrors, sources, stream };
  }

  it("connects to the same-origin events endpoint and reports status", () => {
    const { sources, statuses, stream } = setup();
    stream.start();
    expect(sources[0]?.url).toBe("/api/v1/events");
    expect(statuses).toEqual(["connecting"]);
    sources[0]?.emit("open", {});
    expect(statuses).toEqual(["connecting", "connected"]);
  });

  it("delivers a strictly validated transcript frame", () => {
    const { events, sources, stream } = setup();
    stream.start();
    sources[0]?.emit("snapshot", { data: transcriptPayload() });
    expect(events.length).toBe(1);
    expect(events[0]?.schema_version).toBe("ai-dev-flow/dashboard-event/v1");
    expect(events[0]?.reset_required).toBe(true);
    expect(events[0]?.changed_task_ids).toEqual(["DASHBOARD-BE-001"]);
  });

  it("reports malformed JSON frames as protocol errors instead of ignoring them", () => {
    const { events, protocolErrors, sources, stream } = setup();
    stream.start();
    sources[0]?.emit("snapshot", { data: "{not json" });
    sources[0]?.emit("snapshot", { data: 42 });
    expect(events.length).toBe(0);
    expect(protocolErrors.length).toBe(2);
    expect(protocolErrors[0]).toContain("JSON");
  });

  it("reports schema-drift frames as protocol errors without corrupting state", () => {
    const { events, protocolErrors, sources, stream } = setup();
    stream.start();
    const valid = JSON.parse(transcriptPayload()) as Record<string, unknown>;
    sources[0]?.emit("snapshot", { data: JSON.stringify({ ...valid, state: "half-fresh" }) });
    sources[0]?.emit("snapshot", { data: JSON.stringify({ ...valid, extra: true }) });
    const missingField = { ...valid } as Record<string, unknown>;
    delete missingField.reset_required;
    sources[0]?.emit("snapshot", { data: JSON.stringify(missingField) });
    expect(events.length).toBe(0);
    expect(protocolErrors.length).toBe(3);
    expect(protocolErrors[0]).toContain("SnapshotEvent");
  });

  it("recovers after a protocol error: the next valid frame is delivered", () => {
    const { events, protocolErrors, sources, stream } = setup();
    stream.start();
    sources[0]?.emit("snapshot", { data: "{broken" });
    expect(protocolErrors.length).toBe(1);
    sources[0]?.emit("snapshot", { data: transcriptPayload() });
    expect(events.length).toBe(1);
    expect(events[0]?.schema_version).toBe("ai-dev-flow/dashboard-event/v1");
  });

  it("start is idempotent and stop closes the source", () => {
    const { sources, stream } = setup();
    stream.start();
    stream.start();
    expect(sources.length).toBe(1);
    stream.stop();
    expect(sources[0]?.closed).toBe(true);
  });
});
