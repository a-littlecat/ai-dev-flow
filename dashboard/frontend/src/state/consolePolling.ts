export const CONSOLE_VISIBLE_POLL_MS = 2_000;
export const CONSOLE_HIDDEN_POLL_MS = 10_000;
export const CONSOLE_MAX_BACKOFF_MS = 60_000;

/**
 * Return the next one-shot polling delay. Consecutive transport/contract
 * failures back off exponentially; a successful response resets failures to
 * zero. The visibility-specific base interval remains the source of truth.
 */
export function consolePollDelay(visibility: DocumentVisibilityState, consecutiveFailures: number): number {
  const base = visibility === "visible" ? CONSOLE_VISIBLE_POLL_MS : CONSOLE_HIDDEN_POLL_MS;
  const exponent = Math.max(0, Math.min(10, consecutiveFailures));
  return Math.min(CONSOLE_MAX_BACKOFF_MS, base * (2 ** exponent));
}
