/**
 * DASHBOARD-FE-UA4-001-P1-002 after-evidence screenshots: the frozen
 * 1440×900 / 1024×768 / 390×844 viewports across the default graph, an active
 * search + highlight combination, the expanded filter panel, an open task
 * detail, the stale / partial fixtures and the expanded diagnostics drawer.
 * Every shot is visually inspected after generation (see task receipts).
 */
import { expect, test, type Page } from "@playwright/test";
import { buildGraphSnapshot, mockReset, mockSetSnapshot, shot } from "./helpers";

async function openGraph(page: Page): Promise<void> {
  await mockReset();
  await mockSetSnapshot(buildGraphSnapshot());
  await page.goto("/?view=network");
  await expect(page.locator(".node")).toHaveCount(5);
}

test.describe("after-evidence screenshots", () => {
  test("1440×900: default, search+highlight, filters, detail, drawer", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openGraph(page);
    await shot(page, "after/default-1440");

    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("gamma");
    await expect(page.locator(".search-status")).toContainText("匹配 1");
    await page.getByRole("button", { name: /需要决定（2）/ }).click();
    await expect(page.locator(`.node[data-task-id="TASK-GAMMA"]`)).toHaveClass(/node-match/);
    await shot(page, "after/search-gamma-highlight-1440");
    await search.fill("");
    await page.getByRole("button", { name: /需要决定（2）/ }).click();

    await page.locator(".toolbar-filter-toggle").click();
    await expect(page.locator("#filter-lifecycles-Ready")).toBeVisible();
    await shot(page, "after/filter-panel-1440");
    await page.locator(".toolbar-filter-toggle").click();

    await page.locator(`.node[data-task-id="TASK-ALPHA"]`).click();
    await expect(page.locator(".detail-title")).toContainText("TASK-ALPHA");
    await shot(page, "after/detail-alpha-1440");

    await page.locator(".diag-drawer-toggle").click();
    await expect(page.locator(".diag-drawer-list")).toBeVisible();
    await shot(page, "after/diag-drawer-open-1440");
  });

  test("1440×900: stale and partial fixtures", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/?fixture=stale&view=network");
    await expect(page.locator(".stale-strip-stale")).toBeVisible();
    await shot(page, "after/stale-1440");

    await page.goto("/?fixture=partial&view=network");
    await expect(page.locator(".stale-strip-partial")).toBeVisible();
    await shot(page, "after/partial-1440");
  });

  test("1440×900 dark theme: default graph and search (reproducible)", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ colorScheme: "dark" });
    await openGraph(page);
    await shot(page, "after/dark-default-1440");

    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("gamma");
    await expect(page.locator(`.node[data-task-id="TASK-GAMMA"]`)).toHaveClass(/node-match/);
    await expect(page.locator(".search-status")).toContainText("匹配 1");
    await shot(page, "after/dark-search-gamma-1440");
  });

  test("1024×768 and 390×844: default graph", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await openGraph(page);
    await shot(page, "after/default-1024");

    await page.setViewportSize({ width: 390, height: 844 });
    await openGraph(page);
    await shot(page, "after/default-390");
  });
});
