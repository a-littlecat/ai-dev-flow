import { expect, test } from "@playwright/test";
import {
  buildGraphSnapshot,
  makeConsoleItem,
  makeProjectConsole,
  mockReset,
  mockSetConsole,
  mockSetSnapshot,
} from "./helpers";
import { makeTask } from "../makers";

test.beforeEach(async () => {
  await mockReset();
  const snapshot = buildGraphSnapshot();
  snapshot.tasks.push(makeTask("TASK-ZETA", { lifecycle: "In Progress" }) as unknown as (typeof snapshot.tasks)[number]);
  await mockSetSnapshot(snapshot);
  await mockSetConsole(
    makeProjectConsole(snapshot, {
      human_attention: [
        makeConsoleItem({
          task_id: "TASK-DELTA",
          title: "确认打印预览方案",
          queue: "human_attention",
          actor: "user",
          next_step: "查看 TASK 中两个选项及影响",
          status_summary: "方案已准备，正在等待用户选择",
          why_now_codes: ["USER_DECISION_PENDING"],
          action_kind: "user_decision",
          action_eligibility: "needs_authority",
          action_kinds: ["user_decision"],
          action_eligibilities: ["needs_authority"],
        }),
      ],
      active_work: [
        makeConsoleItem({
          task_id: "TASK-GAMMA",
          title: "主流程闭环",
          queue: "active_work",
          session_id: "codex-live",
          harness_id: "codex",
          phase: "validating",
          next_step: "运行真实 smoke test",
          why_now_codes: ["ACTIVE_RUNTIME_SESSION"],
          freshness: "live",
          source_kinds: ["task", "git", "runtime"],
          last_activity_at: new Date(Date.now() - 12_000).toISOString(),
        }),
        makeConsoleItem({
          task_id: "TASK-ZETA",
          title: "已声明但无 Runtime 的工作",
          queue: "active_work",
          next_step: "核对 TASK 与运行时状态",
          action_kind: "continue",
          action_eligibility: "needs_authority",
          action_kinds: ["continue"],
          action_eligibilities: ["needs_authority"],
        }),
      ],
      ready_queue: [
        makeConsoleItem({ task_id: "TASK-BETA", title: "第二候选（保持服务端第一位）", priority: "medium" }),
        makeConsoleItem({ task_id: "TASK-ALPHA", title: "第一候选（保持服务端第二位）", priority: "high" }),
      ],
      blocked: [
        makeConsoleItem({
          task_id: "TASK-EPSILON",
          title: "缺真实环境证据",
          queue: "blocked",
          next_step: "在指定版本执行 smoke test",
          blocking_task_ids: ["TASK-BETA"],
          action_eligibility: "blocked",
          action_eligibilities: ["blocked"],
        }),
      ],
      stale_sessions: [
        makeConsoleItem({
          task_id: "TASK-GAMMA",
          title: "中断的 Agent 会话",
          queue: "stale_sessions",
          session_id: "codex-old",
          harness_id: "codex",
          phase: "implementing",
          freshness: "stale",
          last_activity_at: new Date(Date.now() - 360_000).toISOString(),
          source_kinds: ["runtime"],
        }),
      ],
      recent_changes: [
        { task_id: "TASK-GAMMA", session_id: "codex-live", kind: "runtime_session", at: new Date().toISOString() },
        { task_id: "TASK-ALPHA", session_id: null, kind: "task_snapshot", at: new Date(Date.now() - 5_000).toISOString() },
      ],
      ambiguity: { has_unique_primary: false, candidate_count: 2, message: "当前没有唯一主任务" },
    }),
  );
});

test("console is the default and preserves server queue order with explicit freshness", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/");

  await expect(page).toHaveURL(/127\.0\.0\.1:5173\/$/);
  await expect(page.getByRole("region", { name: "Project Console 项目总览" })).toBeVisible();
  await expect(page.getByRole("region", { name: "任务执行总览" })).toBeHidden();
  await expect(page.locator(".network-view")).toBeHidden();
  const headings = await page.locator(".console-section-heading h2").allTextContents();
  expect(headings.slice(0, 3)).toEqual(["需要你处理", "正在进行", "下一步队列"]);
  await expect(page.locator(".console-section-human")).toContainText("确认打印预览方案");
  await expect(page.locator(".console-section-human")).toContainText("状态方案已准备，正在等待用户选择");
  await expect(page.locator(".console-section-human .console-card-line").filter({ hasText: "原因" })).toContainText("正在等待用户决策");
  await expect(page.locator(".console-section-human .console-card-line").filter({ hasText: "原因" })).not.toContainText("USER_DECISION_PENDING");
  await expect(page.locator(".console-section-human .console-diagnostics")).toContainText("USER_DECISION_PENDING");
  await expect(page.locator(".console-section-active .console-source")).toHaveText(["实时", "TASK + Git 派生"]);
  await expect(page.locator(".console-section-active .console-card-meta").first()).toContainText("来源：TASK + Git + Runtime");
  await expect(page.locator(".console-section-active .console-card-line").filter({ hasText: "原因" }).first()).toContainText("Runtime 会话正在活跃执行");
  await expect(page.locator(".console-section-stale")).toContainText("状态过期");
  await expect(page.locator(".console-ambiguity")).toHaveText("当前没有唯一主任务，存在 2 个可执行候选。");
  await expect(page.locator(".console-section-ready .console-task-id")).toHaveText(["TASK-BETA", "TASK-ALPHA"]);
  await expect(page.locator(".console-freshness")).toContainText("TASK 派生");
  await expect(page.locator(".console-freshness")).toContainText("Git 派生");
  await expect(page.locator(".console-freshness")).toContainText("Runtime");
  await expect(page.locator(".console-fact-state")).toHaveText("事实状态：新鲜");
});

test("network and legacy remain explicit read-only fallback routes", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "打开完整任务关系诊断" }).click();
  await expect(page).toHaveURL(/\?view=network$/);
  await expect(page.locator(".graph-svg")).toBeVisible();

  await page.getByRole("button", { name: "返回任务执行总览" }).click();
  await expect(page).toHaveURL(/\?view=legacy$/);
  await expect(page.getByRole("region", { name: "任务执行总览" })).toBeVisible();

  await page.getByRole("button", { name: "打开 Project Console 项目总览" }).click();
  await expect(page).toHaveURL(/127\.0\.0\.1:5173\/$/);
  await expect(page.getByRole("region", { name: "Project Console 项目总览" })).toBeVisible();
});

test("console retains last data and exposes a stale banner when polling disconnects", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".console-section-human")).toContainText("确认打印预览方案");
  await page.route("**/api/v1/console", (route) => route.abort("connectionrefused"));
  await expect(page.locator(".console-stale-banner")).toContainText("保留上次数据", { timeout: 8_000 });
  await expect(page.locator(".console-section-human")).toContainText("确认打印预览方案");
});

test("console has no horizontal overflow across frozen viewports and keeps keyboard controls", async ({ page }) => {
  for (const viewport of [
    { width: 1366, height: 768 },
    { width: 1920, height: 1080 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.locator(".project-console")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const firstTask = page.locator(".console-section-human .console-action").first();
    await firstTask.focus();
    await expect(firstTask).toBeFocused();
    await expect(firstTask).toHaveAccessibleName(/查看任务|复制/);
  }
});

test("empty queues remain explicit instead of inventing a primary task", async ({ page }) => {
  const snapshot = buildGraphSnapshot();
  await mockSetSnapshot(snapshot);
  await mockSetConsole(makeProjectConsole(snapshot));
  await page.goto("/");

  await expect(page.locator(".console-ambiguity")).toContainText("没有唯一主任务");
  await expect(page.locator(".console-section-human .console-empty")).toBeVisible();
  await expect(page.locator(".console-section-active .console-empty")).toBeVisible();
  await expect(page.locator(".console-section-ready .console-empty")).toBeVisible();
  await expect(page.locator(".console-section-blocked .console-empty")).toBeVisible();
  await expect(page.locator(".console-section-stale .console-empty")).toBeVisible();
  await expect(page.locator(".console-section-ready")).toContainText("当前没有可开始的任务");
});

test("real-scale queues and extreme identifiers stay readable without browser errors", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" && !message.location().url.endsWith("/favicon.ico")) {
      browserErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  const snapshot = buildGraphSnapshot();
  const ready = Array.from({ length: 24 }, (_, index) =>
    makeConsoleItem({
      task_id: `TASK-${String(index).padStart(2, "0")}-${"VERY-LONG-ID-".repeat(5)}`,
      title: `真实规模候选 ${index + 1}：${"需要保留完整事实来源与下一步说明".repeat(6)}`,
      priority: index % 2 === 0 ? "high" : "medium",
      next_step: "核对 TASK、Git 与 Runtime 证据后再执行，不由前端重排。".repeat(3),
    }),
  );
  await mockSetSnapshot(snapshot);
  await mockSetConsole(
    makeProjectConsole(snapshot, {
      ready_queue: ready,
      ambiguity: { has_unique_primary: false, candidate_count: ready.length, message: "当前没有唯一主任务" },
    }),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.locator(".console-section-ready .console-card")).toHaveCount(24);
  await expect(page.locator(".console-section-ready .console-task-id").first()).toContainText("TASK-00-");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  expect(browserErrors).toEqual([]);
});

test("console keeps transport status separate from fact state and maps every freshness value", async ({ page }) => {
  const snapshot = buildGraphSnapshot();
  const freshnessValues = ["fresh", "stale", "partial", "live", "ended", "invalid"] as const;
  await mockSetSnapshot(snapshot);
  await mockSetConsole(
    makeProjectConsole(snapshot, {
      state: "partial",
      ready_queue: freshnessValues.map((freshness, index) =>
        makeConsoleItem({
          task_id: `FRESHNESS-${index}`,
          title: `新鲜度 ${freshness}`,
          freshness,
          source_kinds: ["runtime"],
          session_id: freshness === "live" || freshness === "ended" ? `session-${index}` : null,
        }),
      ),
      ambiguity: { has_unique_primary: false, candidate_count: freshnessValues.length, message: "当前没有唯一主任务" },
    }),
  );
  await page.goto("/");

  await expect(page.locator(".console-connection")).toHaveText("● 实时连接");
  await expect(page.locator(".console-fact-state")).toHaveText("事实状态：证据不完整");
  await expect(page.locator(".console-section-ready .console-source")).toHaveText([
    "Runtime 派生",
    "状态过期",
    "证据不完整",
    "实时",
    "已结束",
    "状态无效",
  ]);
  await expect(page.locator(".console-section-ready .console-card-meta")).toHaveText(
    freshnessValues.map(() => "来源：Runtime"),
  );

  await mockSetConsole(makeProjectConsole(snapshot, { state: "stale", revision: "7".repeat(64) }));
  await page.reload();
  await expect(page.locator(".console-fact-state")).toHaveText("事实状态：陈旧");
});

test("a console response slower than the polling interval still becomes visible", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/v1/console", async (route) => {
    calls += 1;
    await new Promise((resolve) => setTimeout(resolve, 5_500));
    await route.continue();
  });
  await page.goto("/");

  await expect(page.locator(".console-section-human")).toContainText("确认打印预览方案", { timeout: 8_000 });
  expect(calls).toBeGreaterThanOrEqual(1);
});

test("console polling switches from visible 2s to hidden 10s", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/v1/console", async (route) => {
    calls += 1;
    await route.continue();
  });
  await page.goto("/");
  await expect(page.locator(".console-section-human")).toContainText("确认打印预览方案");
  const visibleBaseline = calls;
  await expect.poll(() => calls, { timeout: 3_500 }).toBeGreaterThan(visibleBaseline);

  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  const hiddenBaseline = calls;
  await page.waitForTimeout(3_000);
  expect(calls).toBe(hiddenBaseline);
  await expect.poll(() => calls, { timeout: 9_000 }).toBeGreaterThan(hiddenBaseline);
});

test("snapshot-only fixture mode falls back to the explicit network diagnostic route", async ({ page }) => {
  await page.goto("/?fixture=fresh");

  await expect(page).toHaveURL(/fixture=fresh&view=network|view=network&fixture=fresh/);
  await expect(page.locator(".graph-svg")).toBeVisible();
  await expect(page.locator(".project-console")).toBeHidden();
});

test("card actions expose unique task context to assistive technology", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("button", { name: "查看任务 TASK-DELTA", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看任务 TASK-GAMMA · codex-live", exact: true })).toBeVisible();
  const names = await page.locator(".console-card-actions button").evaluateAll((buttons) =>
    buttons.map((button) => button.getAttribute("aria-label")),
  );
  expect(names.every((name) => Boolean(name))).toBe(true);
  expect(new Set(names).size).toBe(names.length);
});

test("copy actions fall back when navigator.clipboard is unavailable", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
    document.execCommand = () => true;
  });
  await page.goto("/");

  await page.getByRole("button", { name: "复制下一步 TASK-DELTA", exact: true }).click();
  await expect(page.locator(".project-console [aria-live='polite']")).toHaveText("复制下一步已复制。");
});
