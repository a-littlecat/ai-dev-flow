/**
 * Unit tests for the read-only API client: a connection that drops after the
 * headers (rejecting body read) maps to a network failure — never a silent
 * success — so callers surface a visible error and enter health-check/retry.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchConsole, fetchSnapshot, fetchTaskDetail } from "../src/api/client";
import { makeProjectConsole } from "./support";
import { sha } from "./makers";

function stubBodyReadFailure(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      status: 200,
      ok: true,
      headers: new Headers({ ETag: '"sha256-x"' }),
      text: async () => {
        throw new Error("terminated");
      },
    })) as unknown as typeof fetch,
  );
}

describe("API client body-read failures", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps a rejecting snapshot body read to a network failure", async () => {
    stubBodyReadFailure();
    const result = await fetchSnapshot();
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.kind).toBe("network");
      if (result.failure.kind === "network") {
        expect(result.failure.message).toContain("terminated");
      }
    }
  });

  it("maps a rejecting task-detail body read to a network failure", async () => {
    stubBodyReadFailure();
    const result = await fetchTaskDetail("TASK-A");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.kind).toBe("network");
    }
  });

  it("still maps a fetch-level rejection to a network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("connection refused");
      }) as unknown as typeof fetch,
    );
    const result = await fetchSnapshot();
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.kind).toBe("network");
    }
  });

  it("sends the console ETag and maps 304 to retained local data", async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => ({
      status: 304,
      ok: false,
      headers: new Headers(),
      text: async () => "",
      requestHeaders: init.headers,
    }));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    const result = await fetchConsole('"sha256-old"');
    expect(result).toEqual({ ok: true, value: null });
    expect(fetchMock.mock.calls[0]?.[1]?.headers).toEqual({ "If-None-Match": '"sha256-old"' });
  });

  it("strictly validates a Project Console response", async () => {
    const payload = makeProjectConsole(sha(700));
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        status: 200,
        ok: true,
        headers: new Headers({ ETag: '"sha256-console"' }),
        text: async () => JSON.stringify(payload),
      })) as unknown as typeof fetch,
    );
    const result = await fetchConsole();
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value?.console.snapshot_revision).toBe(sha(700));
  });
});
