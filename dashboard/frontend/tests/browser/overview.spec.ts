import { expect, test } from "@playwright/test";
import {
  buildGraphSnapshot,
  makeEvent,
  mockReset,
  mockSendEvent,
  mockSetSnapshot,
  rev,
  reviseSnapshot,
  shot,
} from "./helpers";

test.beforeEach(async () => {
  await mockReset();
  await mockSetSnapshot(buildGraphSnapshot());
});

test("default workbench prioritises current action and evidence-backed parallel advice", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?view=legacy");

  await expect(page.getByRole("region", { name: "任务执行总览" })).toBeVisible();
  await expect(page.locator(".network-view")).toBeHidden();
  await expect(page.locator(".current-action")).toContainText("TASK-DELTA");
  await expect(page.locator(".current-action")).toContainText("用户决定 · 可执行");
  await expect(page.locator(".overview-parallel")).toContainText("TASK-ALPHA");
  await expect(page.locator(".overview-parallel")).toContainText("候选 ≠ 已授权");
  await expect(page.locator(".overview-parallel")).not.toContainText("并行未知");
  await expect(page.locator(".overview-item")).toHaveCount(2);
  await shot(page, "overview/default-1440");

  await page.getByRole("button", { name: "打开完整关系图" }).click();
  await expect(page.locator(".graph-svg")).toBeVisible();
  await expect(page.getByRole("button", { name: "返回任务执行总览" })).toBeVisible();
});

test("current action opens a focused task route and can return to overview", async ({ page }) => {
  await page.goto("/?view=legacy");
  await page.getByRole("button", { name: "查看并决定" }).click();

  await expect(page.locator(".graph-svg")).toBeVisible();
  await expect(page.locator(".focus-banner")).toContainText("任务路线：TASK-DELTA");
  await expect(page.locator('.node[data-task-id="TASK-DELTA"]')).toHaveClass(/node-selected/);
  await expect(page.locator(".detail-panel")).toContainText("下一动作建议");

  await page.getByRole("button", { name: "返回任务执行总览" }).click();
  await expect(page.getByRole("region", { name: "任务执行总览" })).toBeVisible();

  await page.getByRole("button", { name: "查看并决定" }).click();
  await expect(page.locator(".detail-panel")).toContainText("下一动作建议");
  await expect(page.locator(".detail-panel")).not.toContainText("正在加载任务详情");
});

test("mobile defaults to a readable vertical workbench instead of a miniature graph", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?view=legacy");

  await expect(page.locator(".action-center")).toBeVisible();
  await expect(page.locator(".graph-svg")).toBeHidden();
  const columns = await page.locator(".overview-primary-grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns);
  expect(columns.trim().split(/\s+/)).toHaveLength(1);
  await expect(page.locator(".current-task-id")).toHaveCSS("font-size", "20px");
  await shot(page, "overview/default-390");
});

test("live snapshot refresh preserves the focused overview action", async ({ page }) => {
  const revA = buildGraphSnapshot();
  await mockSetSnapshot(revA);
  await page.goto("/?view=legacy");

  const action = page.locator('[data-overview-focus-key="current:TASK-DELTA"]');
  await action.focus();
  await expect(action).toBeFocused();

  const revB = reviseSnapshot(revA, rev("b"));
  await mockSetSnapshot(revB);
  await mockSendEvent(makeEvent(rev("b"), "fresh", false));

  await expect(page.locator(".status-bar")).toContainText(`revision：${"b".repeat(8)}`);
  await expect(action).toBeFocused();
});

test("live snapshot refresh follows the same task when it moves between sections", async ({ page }) => {
  const revA = buildGraphSnapshot();
  await mockSetSnapshot(revA);
  await page.goto("/?view=legacy");

  const currentDelta = page.locator('[data-overview-focus-key="current:TASK-DELTA"]');
  await currentDelta.focus();
  await expect(currentDelta).toBeFocused();

  const revB = reviseSnapshot(revA, rev("c"));
  revB.tasks.find((task) => task.task_id === "TASK-DELTA")!.lifecycle = "In Progress";
  revB.actions = revB.actions.filter((action) => action.task_id !== "TASK-DELTA");
  revB.parallel_assessments = revB.parallel_assessments.filter(
    (assessment) => assessment.left_task_id !== "TASK-DELTA" && assessment.right_task_id !== "TASK-DELTA",
  );
  await mockSetSnapshot(revB);
  await mockSendEvent(makeEvent(rev("c"), "fresh", false));

  const movedDelta = page.locator('[data-overview-focus-key="row:active:TASK-DELTA"]');
  await expect(movedDelta).toBeFocused();
  await expect(page.locator('.action-center [aria-live="polite"]')).toBeEmpty();
});

test("live snapshot refresh uses a deterministic fallback and announces a removed task", async ({ page }) => {
  const revA = buildGraphSnapshot();
  await mockSetSnapshot(revA);
  await page.goto("/?view=legacy");

  const currentDelta = page.locator('[data-overview-focus-key="current:TASK-DELTA"]');
  await currentDelta.focus();
  await expect(currentDelta).toBeFocused();

  const revB = reviseSnapshot(revA, rev("d"));
  revB.tasks = revB.tasks.filter((task) => task.task_id !== "TASK-DELTA");
  revB.actions = revB.actions.filter((action) => action.task_id !== "TASK-DELTA");
  revB.parallel_assessments = revB.parallel_assessments.filter(
    (assessment) => assessment.left_task_id !== "TASK-DELTA" && assessment.right_task_id !== "TASK-DELTA",
  );
  await mockSetSnapshot(revB);
  await mockSendEvent(makeEvent(rev("d"), "fresh", false));

  await expect(page.locator('[data-overview-focus-key="current:TASK-ALPHA"]')).toBeFocused();
  await expect(page.locator('.action-center [aria-live="polite"]')).toHaveText(
    "任务总览已更新，原操作已不可用，焦点已移动到当前可用操作。",
  );
});

test("authority denial is shown as an action block, not an invented task dependency", async ({ page }) => {
  const snapshot = buildGraphSnapshot();
  const betaAction = snapshot.actions.find((action) => action.task_id === "TASK-BETA");
  expect(betaAction).toBeDefined();
  Object.assign(betaAction!, {
    action_kind: "merge",
    eligibility: "blocked",
    required_authority: "merge",
    authority_state: "denied",
    reason_codes: ["MERGE_AUTHORITY_DENIED"],
    blocking_task_ids: [],
    blocking_condition_ids: [],
  });
  await mockSetSnapshot(snapshot);
  await page.goto("/?view=legacy");

  const waiting = page.locator(".overview-waiting");
  await expect(waiting).toContainText("动作受阻");
  await expect(waiting).toContainText("合并授权被拒");
  await expect(waiting).not.toContainText("未知任务");
});
