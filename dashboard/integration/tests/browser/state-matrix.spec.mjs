import { readFileSync, writeFileSync } from "node:fs";
import { request as httpRequest } from "node:http";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import playwright from "../../../frontend/node_modules/@playwright/test/index.js";

const { test, expect } = playwright;
const enabled = process.env.DASHBOARD_STATE_MATRIX === "1";
test.skip(!enabled, "only the isolated state-matrix runner enables this test");

const project = process.env.DASHBOARD_PROJECT_ROOT;
const python = process.env.DASHBOARD_PYTHON;
if (enabled && (!project || !python)) {
  throw new Error("state matrix requires DASHBOARD_PROJECT_ROOT and DASHBOARD_PYTHON");
}
const integrationRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const fixtureScript = path.join(integrationRoot, "state_fixture.py");
const statusBar = ".status-bar";

function scenario(name) {
  const result = spawnSync(
    python,
    ["-B", "-X", "utf8", fixtureScript, project, name],
    { encoding: "utf-8", cwd: path.resolve(integrationRoot, "../..") },
  );
  if (result.status !== 0) {
    throw new Error(`scenario ${name} failed: ${result.stderr}`);
  }
}

function readRealResetFrame(lastEventId) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const request = httpRequest(
      {
        hostname: "127.0.0.1",
        port: 8765,
        path: "/api/v1/events",
        method: "GET",
        headers: {
          Accept: "text/event-stream",
          "Last-Event-ID": lastEventId,
        },
      },
      (response) => {
        let body = "";
        response.setEncoding("utf-8");
        response.on("data", (chunk) => {
          body += chunk;
          if (!settled && body.includes("\n\n")) {
            settled = true;
            request.destroy();
            resolve(body);
          }
        });
        response.on("end", () => {
          if (!settled) {
            settled = true;
            reject(new Error(`real SSE ended before a complete frame: ${body}`));
          }
        });
      },
    );
    request.setTimeout(10_000, () => {
      if (!settled) {
        settled = true;
        request.destroy();
        reject(new Error("real SSE reset frame timed out"));
      }
    });
    request.on("error", (error) => {
      if (!settled) {
        settled = true;
        reject(error);
      }
    });
    request.end();
  });
}

test("real backend responses drive every abnormal UI state and recover", async ({
  page,
  request,
}) => {
  // Project Console is the v0.10 default; this graph-specific matrix keeps
  // exercising the retained diagnostic surface through its explicit route.
  await page.goto("/?view=network");
  await expect(page.locator(statusBar)).toContainText("快照：不完整");
  await expect(page.locator(".stale-strip-partial")).toContainText("SOURCE_UNAVAILABLE");

  scenario("valid");
  await expect(page.locator(statusBar)).toContainText("快照：新鲜");
  await expect(page.locator('.node[data-task-id="STACK-001"]')).toBeVisible();

  scenario("parallel-unknown");
  await expect(page.locator(".pair-item.pair-unknown")).toContainText("并行未知");

  scenario("dependency-cycle");
  await page.locator(".diag-drawer-toggle").click();
  await expect(page.locator(".diag-drawer-list")).toContainText("DEPENDENCY_CYCLE");

  scenario("parse-error");
  await expect(page.locator(".diag-drawer-list")).toContainText("SCHEDULING_PARSE_ERROR");

  scenario("valid");
  await expect(page.locator(statusBar)).toContainText("快照：新鲜");
  scenario("invalid-utf8");
  await expect(page.locator(statusBar)).toContainText("快照：过期");
  await expect(page.locator(".stale-strip-stale")).toContainText("last-known-good");
  await expect(page.locator(".stale-strip-stale")).toContainText("SOURCE_UNAVAILABLE");
  scenario("valid");
  await expect(page.locator(statusBar)).toContainText("快照：新鲜");

  const indexPath = path.join(project, ".git", "index");
  const index = readFileSync(indexPath);
  writeFileSync(indexPath, Buffer.from("invalid git index\n", "utf-8"));
  await expect(page.locator(statusBar)).toContainText("Git 降级");
  writeFileSync(indexPath, index);
  await expect(page.locator(statusBar)).toContainText("Git 正常");

  await page.route("**/api/v1/tasks/STACK-001", async (route) => {
    const envelope = await request.get("/api/v1/tasks/STACK-NOPE");
    await route.fulfill({ response: envelope });
  });
  await page.locator('.node[data-task-id="STACK-001"]').click();
  await expect(page.locator(".detail-error")).toContainText("TASK_NOT_FOUND");
  await page.unroute("**/api/v1/tasks/STACK-001");

  await page.route("**/api/v1/events", (route) => route.abort());
  await page.reload();
  await expect(page.locator(statusBar)).toContainText("实时连接：断线重连中");
  await page.unroute("**/api/v1/events");
  await expect(page.locator(statusBar)).toContainText("实时连接：已连接");
});

test("an expired SSE event id reaches the real reset branch and clears view state", async ({
  page,
  request,
}) => {
  scenario("valid");
  const snapshotResponse = await request.get("/api/v1/snapshot");
  expect(snapshotResponse.status()).toBe(200);
  const snapshot = await snapshotResponse.json();
  let eventRequests = 0;
  let resetFrameReceived = false;

  await page.route("**/api/v1/events", async (route) => {
    eventRequests += 1;
    if (eventRequests === 1) {
      const event = {
        schema_version: "ai-dev-flow/dashboard-event/v1",
        revision: snapshot.revision,
        state: snapshot.state,
        changed_task_ids: [],
        reset_required: false,
      };
      await route.fulfill({
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
        },
        body: [
          "retry: 5000",
          `id: ${snapshot.revision}`,
          "event: snapshot",
          `data: ${JSON.stringify(event)}`,
          "",
          "",
        ].join("\n"),
      });
      return;
    }
    const body = await readRealResetFrame("0".repeat(64));
    expect(body).toContain('"reset_required":true');
    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body,
    });
    resetFrameReceived = true;
  });

  await page.goto("/?view=network");
  await expect(page.locator(statusBar)).toContainText("快照：新鲜");
  await page.locator('.node[data-task-id="STACK-001"]').click();
  await expect(page.locator('.node[data-task-id="STACK-001"]')).toHaveClass(
    /node-selected/,
  );
  await expect(page.locator(".detail-subtitle")).toContainText("STACK-001");
  await page.getByRole("button", { name: "只高亮选中节点的下游链" }).click();
  await expect(page.locator(".focus-banner")).toContainText("聚焦下游");

  await expect.poll(() => eventRequests, { timeout: 15_000 }).toBeGreaterThan(1);
  await expect.poll(() => resetFrameReceived, { timeout: 15_000 }).toBe(true);
  await page.unroute("**/api/v1/events");
  await expect(page.locator(statusBar)).toContainText("实时连接：已连接");
  await expect(page.locator('.node[data-task-id="STACK-001"]')).not.toHaveClass(
    /node-selected/,
  );
  await expect(page.locator(".detail-title")).toHaveText("任务详情");
  await expect(page.locator(".focus-banner")).toHaveCount(0);
});
