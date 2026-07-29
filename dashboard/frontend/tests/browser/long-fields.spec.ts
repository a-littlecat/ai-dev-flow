/**
 * DASHBOARD-FE-UA4-RVW-004-P1-003 oracle (Round 3, strengthened): the
 * contract puts no length cap on task IDs, titles, source paths or worktree
 * roots. A schema-valid snapshot carrying extreme values must never cause
 * horizontal overflow, clipped text or overlapping regions at the three
 * frozen viewports — across the default view, an active search, the expanded
 * filter panel, an open long detail, the expanded diagnostics drawer, and
 * genuinely stale / partial snapshots built from the SAME long-field data
 * (not the short tasks=0 fixtures).
 *
 * Every payload is derived from the versioned-fixture-based graph snapshot
 * (stale_sources / state-specific diagnostics are cloned from the versioned
 * stale / partial fixtures) and strictly re-validated against the versioned
 * schema in-test; the mock backend re-validates on injection.
 */
import { expect, test, type Page } from "@playwright/test";
import type { DashboardSnapshot } from "../../src/generated/contracts.types";
import { buildGraphSnapshot, mockReset, mockSetSnapshot, shot } from "./helpers";
import { readFixtureJson } from "../makers";
import { validateContract } from "./validate";

/** Longest legal task id shape: word characters joined by dashes. */
const LONG_ID = `TASK-${"LONG".repeat(30)}`;
/** SVG node inner width: NODE_WIDTH 244 minus 12px padding on both sides. */
const NODE_TEXT_MAX_WIDTH = 220;

function buildLongFieldSnapshot(): DashboardSnapshot {
  const replaced = JSON.parse(
    JSON.stringify(buildGraphSnapshot()).replaceAll('"TASK-ALPHA"', JSON.stringify(LONG_ID)),
  ) as Record<string, unknown>;
  const tasks = replaced.tasks as Record<string, unknown>[];
  const alpha = tasks.find((task) => task.task_id === LONG_ID);
  if (!alpha) {
    throw new Error("long id replacement failed");
  }
  alpha.title = `超长标题：${"关系图仪表盘视觉品质验收与长字段溢出回归".repeat(6)}`;
  alpha.source_path = `docs/tasks/${"very-long-segment/".repeat(12)}${LONG_ID}.md`;
  alpha.branch_hint = `feat/${"alpha-long-branch-segment-".repeat(6)}`;
  const project = replaced.project as { worktrees: Record<string, unknown>[] };
  const worktree = project.worktrees[0];
  if (!worktree) {
    throw new Error("graph snapshot has no worktree");
  }
  worktree.root = `D:/${"very-long-worktree-root-".repeat(8)}`;
  worktree.branch = `refs/heads/${String(alpha.branch_hint)}`;
  return validateContract<DashboardSnapshot>("DashboardSnapshot", replaced);
}

/**
 * The same extreme-length payload as a stale or partial snapshot: the strip
 * state comes from real long-field data, not from the short tasks=0
 * fixtures. State-specific parts (stale_sources, the SOURCE_STALE /
 * SOURCE_UNAVAILABLE diagnostics) are cloned from the versioned fixtures.
 */
function buildLongFieldStateSnapshot(state: "stale" | "partial"): DashboardSnapshot {
  const base = JSON.parse(JSON.stringify(buildLongFieldSnapshot())) as Record<string, unknown>;
  const fixture = readFixtureJson(state === "stale" ? "stale.json" : "partial.json") as {
    stale_sources: unknown[];
    diagnostics: Record<string, unknown>[];
  };
  const code = state === "stale" ? "SOURCE_STALE" : "SOURCE_UNAVAILABLE";
  const stateDiagnostic = fixture.diagnostics.find((item) => item.code === code);
  if (!stateDiagnostic) {
    throw new Error(`versioned ${state} fixture has no ${code} diagnostic`);
  }
  base.state = state;
  base.stale_sources = state === "stale" ? fixture.stale_sources : [];
  base.diagnostics = [...(base.diagnostics as unknown[]), stateDiagnostic];
  const summary = base.summary as { counts_by_severity: Record<string, number> };
  summary.counts_by_severity[stateDiagnostic.severity as string] =
    (summary.counts_by_severity[stateDiagnostic.severity as string] ?? 0) + 1;
  return validateContract<DashboardSnapshot>("DashboardSnapshot", base);
}

async function inject(page: Page, snapshot: DashboardSnapshot): Promise<void> {
  await mockReset();
  await mockSetSnapshot(snapshot);
  await page.goto("/");
  await expect(page.locator(".node")).toHaveCount(5);
}

interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

function intersects(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

/** Document-level chrome: no horizontal overflow, bars inside the viewport. */
async function expectNoHorizontalOverflow(page: Page, width: number): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
  for (const selector of [".status-bar", ".toolbar"]) {
    const box = await page.locator(selector).boundingBox();
    expect(box, `${selector} must be laid out`).not.toBeNull();
    expect(box!.x + box!.width, `${selector} escapes the ${width}px viewport`).toBeLessThanOrEqual(width + 1);
  }
}

/**
 * Element-level clipping oracle: no rendered text element may be silently
 * clipped — its content box must fit its own box (no hidden overflow), and
 * the pair reason column must keep a readable width (never squeezed into a
 * character-per-line strip by a long sibling button).
 */
async function expectNoClippedText(page: Page): Promise<void> {
  // Always rendered with the long-field snapshot.
  const always = [".status-item", ".pair-button", ".pair-reasons"];
  // Rendered only in specific states the matrix enters before this check.
  const conditional = [
    ".search-status",
    ".detail-title",
    ".detail-subtitle",
    ".def-table td",
    ".worktree-line",
    ".diag-item",
    ".filter-option",
  ];
  for (const selector of [...always, ...conditional]) {
    const elements = page.locator(selector);
    const count = await elements.count();
    for (let i = 0; i < count; i += 1) {
      const el = elements.nth(i);
      if (!(await el.isVisible())) {
        continue;
      }
      const metrics = await el.evaluate((node) => ({
        scrollWidth: node.scrollWidth,
        clientWidth: node.clientWidth,
        overflowX: getComputedStyle(node).overflowX,
        textOverflow: getComputedStyle(node).textOverflow,
      }));
      expect(
        metrics.scrollWidth <= metrics.clientWidth + 1 ||
          (metrics.overflowX === "hidden" && metrics.textOverflow === "ellipsis"),
        `${selector}#${i} is silently clipped (scrollWidth ${metrics.scrollWidth} > clientWidth ${metrics.clientWidth}, no ellipsis affordance)`,
      ).toBe(true);
      if (!(metrics.overflowX === "hidden" && metrics.textOverflow === "ellipsis")) {
        expect(metrics.scrollWidth, `${selector}#${i} content escapes its box`).toBeLessThanOrEqual(
          metrics.clientWidth + 1,
        );
      }
    }
  }
  // The reason text keeps a readable measure next to / below a long button.
  const reasons = page.locator(".pair-reasons");
  const reasonCount = await reasons.count();
  expect(reasonCount).toBeGreaterThan(0);
  for (let i = 0; i < reasonCount; i += 1) {
    const box = await reasons.nth(i).boundingBox();
    expect(box, ".pair-reasons must be laid out").not.toBeNull();
    expect(box!.width, `.pair-reasons#${i} squeezed to ${box!.width}px (character-per-line strip)`).toBeGreaterThanOrEqual(80);
  }
}

/** Region-level occlusion oracle: top-level regions never overlap. */
async function expectRegionsDisjoint(page: Page): Promise<void> {
  const pairs: [string, string][] = [
    [".status-bar", ".app-main"],
    [".status-bar", ".diag-drawer"],
    [".app-main", ".diag-drawer"],
    [".graph-area", ".detail-panel"],
  ];
  for (const [a, b] of pairs) {
    const boxA = await page.locator(a).boundingBox();
    const boxB = await page.locator(b).boundingBox();
    expect(boxA, `${a} must be laid out`).not.toBeNull();
    expect(boxB, `${b} must be laid out`).not.toBeNull();
    expect(intersects(boxA!, boxB!), `${a} overlaps ${b}`).toBe(false);
  }
}

/** SVG truncate oracle: the long node id is ellipsised inside the node box. */
async function expectNodeIdTruncated(page: Page): Promise<void> {
  const idText = page.locator(`.node[data-task-id="${LONG_ID}"] .node-id`);
  await expect(idText).toContainText("…");
  const width = await idText.evaluate((el) => (el as unknown as SVGGraphicsElement).getBBox().width);
  expect(width, "node-id text escapes the node frame").toBeLessThanOrEqual(NODE_TEXT_MAX_WIDTH);
}

const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 },
];

test.describe("extreme-length contract fields", () => {
  for (const { width, height } of VIEWPORTS) {
    test(`no overflow, clipping or occlusion across the state matrix at ${width}x${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await inject(page, buildLongFieldSnapshot());
      await expectNoHorizontalOverflow(page, width);
      await expectNoClippedText(page);
      await expectRegionsDisjoint(page);
      await expectNodeIdTruncated(page);
      await shot(page, `long-fields/matrix-${width}-default`);

      // Active search matching the long id.
      const search = page.getByPlaceholder("搜索任务 ID / 标题…");
      await search.fill("LONG");
      await expect(page.locator(".search-status")).toHaveText("匹配 1 / 共 5 个任务");
      await expect(page.locator(`.node[data-task-id="${LONG_ID}"]`)).toHaveClass(/node-match/);
      await expectNoHorizontalOverflow(page, width);
      await expectNoClippedText(page);
      await search.fill("");

      // Expanded filter panel (long worktree root is a filter option).
      await page.locator(".toolbar-filter-toggle").click();
      await expect(page.locator("#filter-lifecycles-Ready")).toBeVisible();
      await expectNoHorizontalOverflow(page, width);
      await expectNoClippedText(page);
      await page.locator(".toolbar-filter-toggle").click();

      // Open the long-field detail: title, source path, worktree evidence.
      await page.locator(`.node[data-task-id="${LONG_ID}"]`).click();
      await expect(page.locator(".detail-title")).toContainText("LONG");
      await expect(page.locator(".detail-panel")).toContainText("very-long-worktree-root-");
      await expectNoHorizontalOverflow(page, width);
      await expectNoClippedText(page);
      await expectRegionsDisjoint(page);

      // Expanded diagnostics drawer.
      await page.locator(".diag-drawer-toggle").click();
      await expect(page.locator(".diag-drawer-list")).toBeVisible();
      await expectNoHorizontalOverflow(page, width);
      await expectNoClippedText(page);
      await expectRegionsDisjoint(page);
      await shot(page, `long-fields/matrix-${width}`);
    });
  }

  for (const state of ["stale", "partial"] as const) {
    for (const { width, height } of VIEWPORTS) {
      test(`long-field ${state} snapshot stays clean at ${width}x${height}`, async ({ page }) => {
        await page.setViewportSize({ width, height });
        await inject(page, buildLongFieldStateSnapshot(state));
        await expect(page.locator(`.stale-strip-${state}`)).toBeVisible();
        await expect(page.locator(`.node[data-task-id="${LONG_ID}"]`)).toBeVisible();
        await expectNoHorizontalOverflow(page, width);
        await expectNoClippedText(page);
        await expectRegionsDisjoint(page);
        await expectNodeIdTruncated(page);
        // Open the long detail and the drawer in this state too.
        await page.locator(`.node[data-task-id="${LONG_ID}"]`).click();
        await expect(page.locator(".detail-title")).toContainText("LONG");
        await page.locator(".diag-drawer-toggle").click();
        await expect(page.locator(".diag-drawer-list")).toBeVisible();
        await expectNoHorizontalOverflow(page, width);
        await expectNoClippedText(page);
        await expectRegionsDisjoint(page);
        await shot(page, `long-fields/${state}-${width}`);
      });
    }
  }
});
