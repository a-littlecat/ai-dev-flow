/**
 * Regression oracle for DASHBOARD-INTEGRATE-P1-001.
 *
 * The integration snapshot contained 21 tasks and every unordered task pair
 * (210 assessments). The original toolbar rendered all assessments in normal
 * flow, which pushed the relationship graph out of a 1366x768 viewport.
 */
import { expect, test, type Page } from "@playwright/test";
import type { DashboardSnapshot } from "../../src/generated/contracts.types";
import { buildGraphSnapshot, mockReset, mockSetSnapshot, shot } from "./helpers";
import { validateContract } from "./validate";
import { makeAssessment, makeTask } from "../makers";

const VIEWPORTS = [
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
];

function buildRealScaleSnapshot(): DashboardSnapshot {
  const base = buildGraphSnapshot(990);
  const tasks = Array.from({ length: 21 }, (_, index) =>
    makeTask(`REAL-${String(index + 1).padStart(2, "0")}`, {
      title: `真实规模任务 ${index + 1}`,
      lifecycle: "Ready",
    }),
  );
  const assessments: Record<string, unknown>[] = [];
  let pairIndex = 0;
  for (let left = 0; left < tasks.length; left += 1) {
    for (let right = left + 1; right < tasks.length; right += 1) {
      const result = pairIndex < 2 ? "candidate" : pairIndex < 12 ? "must_serial" : "unknown";
      const reasons =
        result === "candidate"
          ? ["ALL_CHECKS_PASSED"]
          : result === "must_serial"
            ? ["WRITE_SCOPE_OVERLAP"]
            : ["WORKTREE_EVIDENCE_UNKNOWN"];
      assessments.push(
        makeAssessment(
          10_000 + pairIndex,
          String(tasks[left]!.task_id),
          String(tasks[right]!.task_id),
          result,
          reasons,
        ),
      );
      pairIndex += 1;
    }
  }

  return validateContract<DashboardSnapshot>("DashboardSnapshot", {
    ...JSON.parse(JSON.stringify(base)),
    tasks,
    edges: [],
    actions: [],
    parallel_assessments: assessments,
    diagnostics: [],
    stale_sources: [],
    summary: {
      ...base.summary,
      task_total: tasks.length,
      edge_total: 0,
      action_total: 0,
      counts_by_lifecycle: {
        Accepted: 0,
        Blocked: 0,
        Cancelled: 0,
        Closed: 0,
        Deferred: 0,
        Draft: 0,
        "In Progress": 0,
        "Needs Fix": 0,
        Ready: tasks.length,
        Review: 0,
      },
      counts_by_action: {
        close: 0,
        commit: 0,
        continue: 0,
        execute: 0,
        merge: 0,
        none: 0,
        plan: 0,
        release: 0,
        repair: 0,
        review: 0,
        user_decision: 0,
      },
      counts_by_relation: {
        conflicts_with: 0,
        depends_on: 0,
        discovered_from: 0,
        parent: 0,
        replaces: 0,
      },
      counts_by_severity: { error: 0, violation: 0, warning: 0, info: 0 },
    },
  });
}

function buildDenseCandidateSnapshot(): DashboardSnapshot {
  const snapshot = buildRealScaleSnapshot();
  const tasks = snapshot.tasks.slice(0, 14);
  const assessments = [];
  let pairIndex = 0;
  for (let left = 0; left < tasks.length; left += 1) {
    for (let right = left + 1; right < tasks.length; right += 1) {
      assessments.push(
        makeAssessment(
          20_000 + pairIndex,
          String(tasks[left]!.task_id),
          String(tasks[right]!.task_id),
          "candidate",
          ["ALL_CHECKS_PASSED"],
        ),
      );
      pairIndex += 1;
    }
  }
  return validateContract<DashboardSnapshot>("DashboardSnapshot", {
    ...JSON.parse(JSON.stringify(snapshot)),
    tasks,
    parallel_assessments: assessments,
    summary: {
      ...snapshot.summary,
      task_total: tasks.length,
      counts_by_lifecycle: {
        ...snapshot.summary.counts_by_lifecycle,
        Ready: tasks.length,
      },
    },
  });
}

async function openRealScale(page: Page): Promise<void> {
  await mockReset();
  await mockSetSnapshot(buildRealScaleSnapshot());
  await page.goto("/?view=network");
  await expect(page.locator(".node")).toHaveCount(21);
  await expect(page.locator(".status-bar")).toContainText("快照：新鲜");
}

async function graphHeight(page: Page): Promise<number> {
  const box = await page.locator(".graph-area").boundingBox();
  expect(box, "relationship graph region must remain in layout").not.toBeNull();
  return box!.height;
}

test.describe("real project scale: 21 tasks / 210 pair assessments", () => {
  for (const { width, height } of VIEWPORTS) {
    test(`pair summary preserves the primary graph at ${width}x${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await openRealScale(page);

      const toggle = page.locator(".pair-list-toggle");
      const list = page.locator("#parallel-assessment-list");
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
      await expect(toggle).toContainText("关系判定");
      await expect(toggle).toContainText("候选 2");
      await expect(toggle).toContainText("串行 10");
      await expect(toggle).toContainText("待确认 198");
      await expect(page.locator(".task-source-summary")).toHaveText("21 个任务");
      await expect(list).toBeHidden();
      expect(await graphHeight(page)).toBeGreaterThanOrEqual(240);
      await expect(page.locator(".detail-panel")).toBeHidden();
      await expect(page.locator(".assessment-link")).toHaveCount(0);
      await expect(page.locator(".legend-note")).toContainText(
        "关系图已收起 210 条并行评估以避免遮挡",
      );
      const gridTracks = await page.locator(".node").evaluateAll((nodes) => ({
        columns: new Set(nodes.map((node) => Math.round(node.getBoundingClientRect().x))).size,
        rows: new Set(nodes.map((node) => Math.round(node.getBoundingClientRect().y))).size,
      }));
      expect(gridTracks.columns).toBeGreaterThan(1);
      expect(gridTracks.rows).toBeGreaterThan(1);

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
      await shot(page, `real-scale/collapsed-${width}x${height}`);

      // Pointer path: all wire assessments stay present; the list, rather
      // than the page/toolbar, owns the overflow.
      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      await expect(list).toBeVisible();
      await expect(page.locator(".pair-item")).toHaveCount(210);
      const scrollMetrics = await list.evaluate((element) => {
        const style = getComputedStyle(element);
        return {
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
          overflowY: style.overflowY,
        };
      });
      expect(scrollMetrics.clientHeight).toBeLessThanOrEqual(280);
      expect(scrollMetrics.scrollHeight).toBeGreaterThan(scrollMetrics.clientHeight);
      expect(scrollMetrics.overflowY).toMatch(/auto|scroll/);
      expect(await graphHeight(page)).toBeGreaterThanOrEqual(180);

      const last = page.locator(".pair-item").last();
      await last.scrollIntoViewIfNeeded();
      await expect(last).toBeVisible();
      await expect(last).toContainText("并行未知");
      await shot(page, `real-scale/expanded-${width}x${height}`);

      // Keyboard path closes the same disclosure and restores the primary
      // graph without changing any assessment result.
      await toggle.focus();
      await page.keyboard.press("Enter");
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
      await expect(list).toBeHidden();
      expect(await graphHeight(page)).toBeGreaterThanOrEqual(240);
    });
  }

  test("dense candidate labels trigger a new fit after layout height grows", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await mockReset();
    await mockSetSnapshot(buildDenseCandidateSnapshot());
    await page.goto("/?view=network");
    await expect(page.locator(".node")).toHaveCount(14);
    const initialTransform = await page.locator(".graph-viewport").getAttribute("transform");

    await page.getByRole("button", { name: /并行候选（14）/ }).click();
    await expect(page.locator(".assessment-label")).toHaveCount(91);
    await expect
      .poll(() => page.locator(".graph-viewport").getAttribute("transform"))
      .not.toBe(initialTransform);

    const svgBox = (await page.locator(".graph-svg").boundingBox())!;
    for (const label of await page.locator(".assessment-label").all()) {
      const labelBox = (await label.boundingBox())!;
      expect(labelBox.x).toBeGreaterThanOrEqual(svgBox.x - 1);
      expect(labelBox.y).toBeGreaterThanOrEqual(svgBox.y - 1);
      expect(labelBox.x + labelBox.width).toBeLessThanOrEqual(svgBox.x + svgBox.width + 1);
      expect(labelBox.y + labelBox.height).toBeLessThanOrEqual(svgBox.y + svgBox.height + 1);
    }
  });

  test("scheduled refit preserves focus on the selected graph task", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await mockReset();
    await mockSetSnapshot(buildDenseCandidateSnapshot());
    await page.goto("/?view=network");
    await expect
      .poll(() => page.locator(".graph-viewport").getAttribute("transform"))
      .not.toBe("translate(0, 0) scale(1)");
    const initial = page.locator('.node[data-task-id="REAL-01"]');
    await initial.focus();
    await expect(initial).toBeFocused();
    await page.keyboard.press("ArrowRight");
    await expect(page.locator(".node-selected")).toHaveAttribute(
      "data-task-id",
      "REAL-01",
    );
    await expect(initial).toBeFocused();
    await expect(page.locator(".assessment-label")).toHaveCount(13);
    await page.evaluate(
      () =>
        new Promise<void>((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
        }),
    );
    const transformBeforeHighlight = await page
      .locator(".graph-viewport")
      .getAttribute("transform");

    // HTMLElement.click() exercises the same store/render path without moving
    // focus to the toolbar button, so the graph task remains the focus owner
    // whose preservation is under test.
    await page.getByRole("button", { name: /并行候选（14）/ }).evaluate((button) => {
      (button as HTMLButtonElement).click();
    });
    await expect(page.locator(".assessment-label")).toHaveCount(91);
    await expect
      .poll(() => page.locator(".graph-viewport").getAttribute("transform"))
      .not.toBe(transformBeforeHighlight);
    await expect
      .poll(() =>
        page.evaluate(
          () => document.activeElement?.closest<SVGGElement>(".node")?.dataset.taskId ?? null,
        ),
      )
      .toBe("REAL-01");
  });
});
