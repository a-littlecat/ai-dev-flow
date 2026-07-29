/**
 * Playwright configuration for DASHBOARD-FE-001 phase 2 browser verification.
 *
 * - Uses the locally installed Google Chrome via `channel: "chrome"`; no
 *   browser binaries are downloaded.
 * - Starts the Vite dev server with DASHBOARD_MOCK_BACKEND=1 so /api/v1/* is
 *   served by the schema-validating mock middleware in vite.config.ts (no
 *   dependency on the not-yet-integrated backend service).
 * - Serial workers: the mock backend holds single global state per server.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  outputDir: "test-results",
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "chrome",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 10_000,
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    timeout: 60_000,
    env: { DASHBOARD_MOCK_BACKEND: "1" },
    stdout: "pipe",
    stderr: "pipe",
  },
});
