import { describe, expect, it } from "vitest";
import {
  CONSOLE_HIDDEN_POLL_MS,
  CONSOLE_MAX_BACKOFF_MS,
  CONSOLE_VISIBLE_POLL_MS,
  consolePollDelay,
} from "../src/state/consolePolling";

describe("consolePollDelay", () => {
  it("uses a 2s visible interval and a 10s hidden interval", () => {
    expect(consolePollDelay("visible", 0)).toBe(CONSOLE_VISIBLE_POLL_MS);
    expect(consolePollDelay("hidden", 0)).toBe(CONSOLE_HIDDEN_POLL_MS);
  });

  it("backs off exponentially after failures and caps the delay", () => {
    expect(consolePollDelay("visible", 1)).toBe(4_000);
    expect(consolePollDelay("visible", 2)).toBe(8_000);
    expect(consolePollDelay("hidden", 1)).toBe(20_000);
    expect(consolePollDelay("hidden", 20)).toBe(CONSOLE_MAX_BACKOFF_MS);
  });
});
