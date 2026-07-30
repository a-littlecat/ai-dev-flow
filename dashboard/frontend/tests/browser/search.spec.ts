/**
 * DASHBOARD-FE-UA4-001-P1-001 oracle: a non-empty text search must produce a
 * clear, consistent, observable result under every quick-highlight / focus
 * combination — matches are never dimmed together with non-matches, the
 * result count (and an explicit no-result state) is announced, and the detail
 * panel never keeps showing a task the search just filtered out.
 */
import { expect, test, type Page } from "@playwright/test";
import { buildGraphSnapshot, mockReset, mockSetSnapshot, shot } from "./helpers";

async function openGraph(page: Page): Promise<void> {
  await mockReset();
  await mockSetSnapshot(buildGraphSnapshot());
  await page.goto("/");
  await expect(page.locator(".node")).toHaveCount(5);
}

function node(page: Page, taskId: string) {
  return page.locator(`.node[data-task-id="${taskId}"]`);
}

const OTHERS = ["TASK-ALPHA", "TASK-BETA", "TASK-DELTA", "TASK-EPSILON"] as const;

async function opacityOf(page: Page, taskId: string): Promise<number> {
  return Number.parseFloat(await node(page, taskId).evaluate((el) => getComputedStyle(el).opacity));
}

/** Assert the full search-result contract for the unique match TASK-GAMMA. */
async function expectGammaIsTheOnlyMatch(page: Page): Promise<void> {
  await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-match/);
  await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-dimmed/);
  expect(await opacityOf(page, "TASK-GAMMA")).toBe(1);
  // The non-colour badge: symbol + text, never colour alone.
  await expect(node(page, "TASK-GAMMA").locator(".node-match-tag")).toHaveText("◈ 搜索匹配");
  await expect(node(page, "TASK-GAMMA")).toHaveAttribute("aria-label", /搜索匹配/);
  for (const other of OTHERS) {
    await expect(node(page, other)).toHaveClass(/node-dimmed/);
    await expect(node(page, other)).not.toHaveClass(/node-match/);
    expect(await opacityOf(page, other), `${other} must not compete for visual attention`).toBeLessThan(0.5);
  }
  await expect(page.locator(".search-status")).toContainText("匹配 1");
}

const HIGHLIGHTS: { name: RegExp; label: string }[] = [
  { name: /下一动作（1）/, label: "actionable" },
  { name: /并行候选（2）/, label: "candidates" },
  { name: /需要决定（2）/, label: "decisions" },
];

test.describe("search feedback (UA4-001-P1-001)", () => {
  test("search alone marks the match and dims everything else", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openGraph(page);
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("gamma");
    await expect(search).toHaveValue("gamma");
    await expectGammaIsTheOnlyMatch(page);
    await expect(page.locator(".search-status")).toHaveText("匹配 1 / 共 5 个任务");
    await shot(page, "search/gamma-no-highlight");
  });

  for (const { name, label } of HIGHLIGHTS) {
    test(`search x highlight=${label}: the match is never dimmed with the rest`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await openGraph(page);
      // Activate the highlight first, then type the search (the UA4 repro).
      await page.getByRole("button", { name }).click();
      const search = page.getByPlaceholder("搜索任务 ID / 标题…");
      await search.click();
      await page.keyboard.type("gamma");
      await expectGammaIsTheOnlyMatch(page);
      // The highlight itself stays active underneath the search.
      await expect(page.getByRole("button", { name })).toHaveAttribute("aria-pressed", "true");
      await shot(page, `search/gamma-highlight-${label}`);

      // Clearing the search restores the pure highlight semantics: only
      // non-highlighted nodes are dimmed, no match badges remain.
      await search.fill("");
      await expect(page.locator(".node-match")).toHaveCount(0);
      await expect(page.locator(".search-status")).toHaveCount(0);
      await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-match/);
      // Deactivate the highlight before the next combination.
      await page.getByRole("button", { name }).click();
      await expect(page.locator(".node-dimmed")).toHaveCount(0);
    });
  }

  for (const focusCase of [
    {
      direction: "upstream",
      buttonName: "只高亮选中节点的上游链",
      banner: "聚焦上游：TASK-BETA",
      selected: "TASK-BETA",
      query: "beta",
      context: ["TASK-ALPHA"],
      dimmed: ["TASK-GAMMA", "TASK-DELTA", "TASK-EPSILON"],
      lifecycle: null,
    },
    {
      direction: "downstream",
      buttonName: "只高亮选中节点的下游链",
      banner: "聚焦下游：TASK-DELTA",
      selected: "TASK-DELTA",
      query: "delta",
      context: ["TASK-GAMMA"],
      dimmed: ["TASK-ALPHA", "TASK-BETA", "TASK-EPSILON"],
      lifecycle: "Review",
    },
  ] as const) {
    test(`search x ${focusCase.direction} focus keeps the full focus chain visible`, async ({ page }) => {
      await openGraph(page);
      if (focusCase.lifecycle !== null) {
        await page.locator(".toolbar-filter-toggle").click();
        await page.locator(`#filter-lifecycles-${focusCase.lifecycle}`).check();
      }
      const search = page.getByPlaceholder("搜索任务 ID / 标题…");
      await search.fill(focusCase.query);
      await node(page, focusCase.selected).click();
      await page.getByRole("button", { name: focusCase.buttonName }).click();
      await expect(page.locator(".focus-banner")).toContainText(focusCase.banner);

      await expect(node(page, focusCase.selected)).toHaveClass(/node-match/);
      await expect(node(page, focusCase.selected)).not.toHaveClass(/node-dimmed/);
      for (const taskId of focusCase.context) {
        await expect(node(page, taskId)).not.toHaveClass(/node-dimmed/);
      }
      for (const taskId of focusCase.dimmed) {
        await expect(node(page, taskId)).toHaveClass(/node-dimmed/);
      }
      await shot(page, `search/${focusCase.direction}-focus-with-search`);
    });
  }

  test("changing search clears a focus anchored to the previous selection", async ({ page }) => {
    await openGraph(page);
    await node(page, "TASK-BETA").click();
    await page.getByRole("button", { name: "只高亮选中节点的上游链" }).click();
    await expect(page.locator(".focus-banner")).toContainText("聚焦上游：TASK-BETA");

    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.fill("gamma");
    await expect(page.locator(".focus-banner")).toHaveCount(0);
    await expectGammaIsTheOnlyMatch(page);

    await search.fill("");
    await node(page, "TASK-BETA").click();
    await page.getByRole("button", { name: "只高亮选中节点的上游链" }).click();
    await search.fill("zzzzz");
    await expect(page.locator(".focus-banner")).toHaveCount(0);
    await expect(page.locator(".graph-empty-text")).toHaveText("没有匹配「zzzzz」的任务");
    await expect(page.locator(".node-dimmed")).toHaveCount(5);
  });

  test("zero results show the count, an in-graph empty state and clear the detail", async ({ page }) => {
    await openGraph(page);
    // Select a task first: its detail must not survive a search it fails.
    await node(page, "TASK-ALPHA").click();
    await expect(page.locator(".detail-title")).toContainText("TASK-ALPHA");

    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("zzzzz");
    await expect(page.locator(".search-status")).toHaveText("无匹配结果");
    await expect(page.locator(".search-status")).toHaveClass(/search-status-empty/);
    await expect(page.locator(".graph-empty-text")).toHaveText("没有匹配「zzzzz」的任务");
    await expect(page.locator(".node-dimmed")).toHaveCount(5);
    // The selection was filtered out: the detail panel is cleared, not stale.
    await expect(page.locator(".detail-title")).toHaveText("任务详情");
    await expect(page.locator(".detail-hint").first()).toContainText("在关系图中选择一个节点");
    await shot(page, "search/no-results");
  });

  test("detail follows a unique match and clears on an ambiguous filter", async ({ page }) => {
    await openGraph(page);
    await node(page, "TASK-ALPHA").click();
    await expect(page.locator(".detail-title")).toContainText("TASK-ALPHA");

    // Unique match: the detail switches from the filtered-out task to it.
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("gamma");
    await expect(page.locator(".detail-title")).toContainText("TASK-GAMMA");
    await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-selected/);
    await shot(page, "search/detail-follows-unique-match");

    // Multiple results while the old selection is hidden: detail clears.
    await search.fill("");
    await expect(page.locator(".detail-title")).toContainText("TASK-GAMMA");
    await page.locator(".toolbar-filter-toggle").click();
    await page.locator("#filter-lifecycles-Ready").check();
    // TASK-GAMMA (Review) left the visible set; two Ready tasks remain — no
    // unambiguous switch, so the selection and the detail are cleared.
    await expect(page.locator(".detail-title")).toHaveText("任务详情");
    await expect(page.locator(".node-selected")).toHaveCount(0);
    await page.locator(".toolbar-reset").click();
  });

  test("clearing the search restores every node to full opacity", async ({ page }) => {
    await openGraph(page);
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("gamma");
    await expect(page.locator(".node-match")).toHaveCount(1);

    await search.fill("");
    await expect(page.locator(".node-match")).toHaveCount(0);
    await expect(page.locator(".node-dimmed")).toHaveCount(0);
    await expect(page.locator(".search-status")).toHaveCount(0);
    for (const id of ["TASK-GAMMA", ...OTHERS]) {
      expect(await opacityOf(page, id)).toBe(1);
    }
  });
});

test.describe("search x structural filters: AND semantics (UA4-RVW-004-P1-001)", () => {
  // Each of these structural options excludes TASK-GAMMA from the combined
  // result set even though the text predicate matches it.
  const EXCLUDING_FILTERS: { id: string; label: string }[] = [
    { id: "#filter-lifecycles-Ready", label: "lifecycle=Ready" },
    { id: "#filter-riskFlags-high-risk", label: "risk=high-risk" },
    { id: "#filter-severities-error", label: "severity=error" },
    { id: "#filter-worktreeRoots-D_fixture-wt-alpha", label: "worktree root" },
  ];

  for (const { id, label } of EXCLUDING_FILTERS) {
    test(`search gamma + ${label}: the text match is filtered out, counted out and dimmed`, async ({ page }) => {
      await openGraph(page);
      const search = page.getByPlaceholder("搜索任务 ID / 标题…");
      await search.click();
      await page.keyboard.type("gamma");
      await expect(page.locator(".search-status")).toHaveText("匹配 1 / 共 5 个任务");

      await page.locator(".toolbar-filter-toggle").click();
      await page.locator(id).check();

      // Combined set (structure AND text) is empty: explicit zero-result
      // state everywhere, and the text-matching node must not stay lit.
      await expect(page.locator(".search-status")).toHaveText("无匹配结果");
      await expect(page.locator(".search-status")).toHaveClass(/search-status-empty/);
      await expect(page.locator(".graph-empty-text")).toHaveText("没有匹配「gamma」的任务");
      await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-match/);
      await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-dimmed/);
      await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-filtered/);
      expect(await opacityOf(page, "TASK-GAMMA")).toBeLessThan(0.5);
      await expect(page.locator(".node-match")).toHaveCount(0);
      await expect(page.locator(".node-dimmed")).toHaveCount(5);

      // Unchecking restores the pure text-search result.
      await page.locator(id).uncheck();
      await expect(page.locator(".search-status")).toHaveText("匹配 1 / 共 5 个任务");
      await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-match/);
      await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-dimmed/);
      expect(await opacityOf(page, "TASK-GAMMA")).toBe(1);
      await page.locator(".toolbar-reset").click();
    });
  }

  test("non-empty combination: text match narrowed by structure counts the intersection", async ({ page }) => {
    await openGraph(page);
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("task");
    await expect(page.locator(".search-status")).toHaveText("匹配 5 / 共 5 个任务");

    await page.locator(".toolbar-filter-toggle").click();
    await page.locator("#filter-lifecycles-Ready").check();
    // 5 text matches AND lifecycle=Ready -> exactly ALPHA and BETA.
    await expect(page.locator(".search-status")).toHaveText("匹配 2 / 共 5 个任务");
    for (const id of ["TASK-ALPHA", "TASK-BETA"] as const) {
      await expect(node(page, id)).toHaveClass(/node-match/);
      await expect(node(page, id)).not.toHaveClass(/node-dimmed/);
      expect(await opacityOf(page, id)).toBe(1);
    }
    for (const id of ["TASK-GAMMA", "TASK-DELTA", "TASK-EPSILON"] as const) {
      await expect(node(page, id)).not.toHaveClass(/node-match/);
      await expect(node(page, id)).toHaveClass(/node-dimmed/);
      expect(await opacityOf(page, id)).toBeLessThan(0.5);
    }
    await shot(page, "search/and-intersection");
  });

  test("detail clears when the selected match is excluded by a structural filter", async ({ page }) => {
    await openGraph(page);
    await node(page, "TASK-GAMMA").click();
    await expect(page.locator(".detail-title")).toContainText("TASK-GAMMA");
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();
    await page.keyboard.type("gamma");
    await expect(page.locator(".detail-title")).toContainText("TASK-GAMMA");

    await page.locator(".toolbar-filter-toggle").click();
    await page.locator("#filter-lifecycles-Ready").check();
    // The combined set is empty: the detail must not keep showing GAMMA.
    await expect(page.locator(".detail-title")).toHaveText("任务详情");
    await expect(page.locator(".node-selected")).toHaveCount(0);

    await page.locator("#filter-lifecycles-Ready").uncheck();
    // Selection is not resurrected from scratch; the match itself is back.
    await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-match/);
    await page.locator(".toolbar-reset").click();
  });
});
