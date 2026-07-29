/**
 * Fixture-state coverage: every versioned contract fixture drives the real UI
 * in `?fixture=<name>` mode (loading / empty / fresh / stale / partial /
 * parse-error / dependency-cycle / parallel-unknown / git-degraded), plus the
 * task-detail error envelope against the schema-validating mock backend.
 */
import { expect, test } from "@playwright/test";
import {
  buildGraphSnapshot,
  mockReset,
  mockSetSnapshot,
  mockSetTaskError,
  shot,
  taskDetailErrorEnvelope,
} from "./helpers";

const STATUS_BAR = ".status-bar";

test.describe("versioned fixture states", () => {
  test("loading overlay appears while the snapshot fetch is in flight", async ({ page }) => {
    await page.route("**/fixtures/v1/fresh.json", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      await route.continue();
    });
    await page.goto("/?fixture=fresh");
    const overlay = page.locator(".overlay-loading");
    await expect(overlay).toBeVisible();
    await expect(overlay).toHaveText("正在加载本地任务快照…");
    await shot(page, "fixtures/loading");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜", { timeout: 15_000 });
  });

  test("fresh fixture: empty graph hint, fixture badge and fresh status", async ({ page }) => {
    await page.goto("/?fixture=fresh");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜");
    await expect(page.locator(STATUS_BAR)).toContainText("fixture：fresh");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：fixture 模式（无 SSE）");
    await expect(page.locator(STATUS_BAR)).toContainText("项目：D:/fixture");
    await expect(page.locator(STATUS_BAR)).toContainText("Git 正常");
    await expect(page.locator(".graph-empty-text")).toHaveText("当前快照中没有任何任务。");
    await expect(page.locator(".graph-svg")).toBeVisible();
    await shot(page, "fixtures/empty-fresh");
  });

  test("stale fixture: stale strip, stale source list, degraded git and diagnostics", async ({ page }) => {
    await page.goto("/?fixture=stale");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：过期");
    await expect(page.locator(STATUS_BAR)).toContainText("Git 降级");
    const strip = page.locator(".stale-strip-stale");
    await expect(strip).toContainText("当前为过期快照");
    await expect(strip).toContainText("docs/tasks/STALE-001.md");
    await expect(strip).toContainText("SOURCE_STALE");
    const drawer = page.locator(".diag-drawer-toggle");
    await expect(drawer).toHaveText("▸ 诊断（1）");
    await drawer.click();
    await expect(page.locator(".diag-drawer-list")).toContainText("SOURCE_STALE");
    await shot(page, "fixtures/stale");
  });

  test("partial fixture: partial strip and unavailable git", async ({ page }) => {
    await page.goto("/?fixture=partial");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：不完整");
    await expect(page.locator(STATUS_BAR)).toContainText("Git 不可用");
    const strip = page.locator(".stale-strip-partial");
    await expect(strip).toContainText("当前为不完整快照");
    await expect(strip).toContainText("SOURCE_UNAVAILABLE");
    await shot(page, "fixtures/partial");
  });

  test("parse-error fixture: parse diagnostic surfaces in strip and drawer", async ({ page }) => {
    await page.goto("/?fixture=parse-error");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：不完整");
    const strip = page.locator(".stale-strip-partial");
    await expect(strip).toContainText("SCHEDULING_PARSE_ERROR");
    await page.locator(".diag-drawer-toggle").click();
    await expect(page.locator(".diag-drawer-list")).toContainText("SCHEDULING_PARSE_ERROR");
    await expect(page.locator(".diag-drawer-list")).toContainText("Scheduling contains a non-canonical line");
    await shot(page, "fixtures/parse-error");
  });

  test("dependency-cycle fixture: cycle diagnostic is visible, not hidden", async ({ page }) => {
    await page.goto("/?fixture=dependency-cycle");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：不完整");
    await expect(page.locator(".stale-strip-partial")).toContainText("DEPENDENCY_CYCLE");
    await page.locator(".diag-drawer-toggle").click();
    await expect(page.locator(".diag-drawer-list")).toContainText("depends_on cycle detected");
    await shot(page, "fixtures/dependency-cycle");
  });

  test("parallel-unknown fixture: unknown assessment listed with non-authorisation notice", async ({ page }) => {
    await page.goto("/?fixture=parallel-unknown");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜");
    await expect(page.locator(".pair-list-title")).toHaveText("并行评估（候选 ≠ 授权，均需用户确认）");
    await expect(page.locator(".pair-item.pair-unknown .pair-button")).toContainText("PAIR-A × PAIR-B：并行未知");
    await shot(page, "fixtures/parallel-unknown");
  });

  test("git-degraded fixture: fresh snapshot with degraded git warning", async ({ page }) => {
    await page.goto("/?fixture=git-degraded");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜");
    await expect(page.locator(STATUS_BAR)).toContainText("Git 降级");
    await expect(page.locator(".overlay-strip")).toHaveCount(0);
    await page.locator(".diag-drawer-toggle").click();
    await expect(page.locator(".diag-drawer-list")).toContainText("GIT_CAPABILITY_UNSUPPORTED");
    await shot(page, "fixtures/git-degraded");
  });

  test("task-detail error envelope renders as a detail error", async ({ page }) => {
    await mockReset();
    await mockSetSnapshot(buildGraphSnapshot());
    await mockSetTaskError(taskDetailErrorEnvelope());
    await page.goto("/");
    await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜");
    await page.locator('.node[data-task-id="TASK-ALPHA"]').click();
    await expect(page.locator(".detail-error")).toContainText("错误 TASK_NOT_FOUND：任务不存在");
    await shot(page, "fixtures/task-detail-error");
    await mockSetTaskError(null);
  });
});
