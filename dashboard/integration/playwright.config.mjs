import path from "node:path";
import { fileURLToPath } from "node:url";

const integrationRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(integrationRoot, "../..");
const projectRoot = process.env.DASHBOARD_PROJECT_ROOT
  ? path.resolve(process.env.DASHBOARD_PROJECT_ROOT)
  : repoRoot;
const python = process.env.DASHBOARD_PYTHON;
if (!python) {
  throw new Error("DASHBOARD_PYTHON must point to Python 3.11 or newer");
}

export default {
  testDir: path.join(integrationRoot, "tests", "browser"),
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { outputFolder: path.join(integrationRoot, "playwright-report"), open: "never" }]],
  outputDir: path.join(integrationRoot, "test-results"),
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "chrome",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `"${python}" -B -X utf8 dashboard/integration/launcher.py --project-root "${projectRoot}" --no-open`,
    cwd: repoRoot,
    url: "http://127.0.0.1:5173/api/v1/snapshot",
    reuseExistingServer: false,
    timeout: 90_000,
    stdout: "pipe",
    stderr: "pipe",
  },
};
