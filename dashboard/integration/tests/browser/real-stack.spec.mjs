import playwright from "../../../frontend/node_modules/@playwright/test/index.js";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { test, expect } = playwright;
test.skip(
  process.env.DASHBOARD_STATE_MATRIX === "1",
  "the state-matrix run uses its own isolated real project",
);
const integrationRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const screenshotRoot = path.join(integrationRoot, "artifacts", "screenshots");
const viewports = [
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
];

for (const viewport of viewports) {
  test(`real backend and frontend render the current project at ${viewport.width}x${viewport.height}`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize(viewport);
    const api = await request.get("/api/v1/snapshot");
    expect(api.status()).toBe(200);
    expect(api.headers()["access-control-allow-origin"]).toBeUndefined();
    const snapshot = await api.json();
    expect(snapshot.schema_version).toBe("ai-dev-flow/dashboard-snapshot/v1");
    expect(snapshot.tasks.length).toBeGreaterThan(0);
    expect(snapshot.parallel_assessments.length).toBeGreaterThan(50);

    await page.goto("/");
    await expect(page).toHaveTitle("任务关系仪表盘 · ai-dev-flow");
    await expect(page.getByRole("banner", { name: "全局状态栏" })).toContainText("只读");
    await expect(page.getByRole("region", { name: "任务关系图区域" })).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "实时连接" }).first()).toBeVisible();
    await expect(page.locator("#parallel-assessment-list")).toBeHidden();
    await expect(page.locator("body")).not.toContainText("HOST_NOT_ALLOWED");

    mkdirSync(screenshotRoot, { recursive: true });
    await page.screenshot({
      path: path.join(screenshotRoot, `real-stack-${viewport.width}x${viewport.height}.png`),
      fullPage: true,
    });
  });
}
