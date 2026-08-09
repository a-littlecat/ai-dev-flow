import { describe, expect, it, vi } from "vitest";
import { copyText } from "../src/ui/clipboard";

describe("copyText", () => {
  it("uses the Clipboard API when available", async () => {
    const writeText = vi.fn(async () => undefined);
    const fallbackCopy = vi.fn(() => true);

    await expect(copyText("value", { writeText, fallbackCopy })).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith("value");
    expect(fallbackCopy).not.toHaveBeenCalled();
  });

  it("falls back when Clipboard API is unavailable or rejects", async () => {
    const fallbackCopy = vi.fn(() => true);
    await expect(copyText("missing", { fallbackCopy })).resolves.toBe(true);
    expect(fallbackCopy).toHaveBeenCalledWith("missing");

    const writeText = vi.fn(async () => { throw new Error("denied"); });
    await expect(copyText("denied", { writeText, fallbackCopy })).resolves.toBe(true);
    expect(fallbackCopy).toHaveBeenCalledWith("denied");
  });
});
