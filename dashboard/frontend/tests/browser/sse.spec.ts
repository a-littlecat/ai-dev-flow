/**
 * Live-update coverage: initial connect, snapshot refresh on SSE events,
 * reset_required semantics (including the same-revision + 304 case),
 * out-of-order response protection, disconnection and automatic reconnect,
 * wire-exact mock oracles and SSE protocol-error visibility — all against
 * the schema-validating mock backend.
 */
import { expect, test } from "@playwright/test";
import {
  BASE,
  buildGraphSnapshot,
  GRAPH_TASKS,
  makeEvent,
  makeTaskDetail,
  mockReset,
  mockSendEvent,
  mockSendRawEvent,
  mockSetSnapshot,
  mockSetSseDown,
  mockTruncateSnapshot,
  rev,
  reviseSnapshot,
  shot,
} from "./helpers";
import { makeDiagnostic } from "../makers";

const STATUS_BAR = ".status-bar";

test.describe("SSE live updates", () => {
  test("connects, applies revision updates and announces them", async ({ page }) => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);
    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await shot(page, "sse/connected");

    // Revision jump a → b via an SSE invalidation event (ETag re-fetch follows).
    const revB = reviseSnapshot(revA, rev("b"));
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"b".repeat(8)}`);
    await expect(page.locator(".visually-hidden[aria-live]")).toContainText("快照已更新");
    await shot(page, "sse/revision-updated");

    // Revision jump b → d (skipping c): any newer revision is accepted.
    const revD = reviseSnapshot(revA, rev("d"));
    await mockSetSnapshot(revD);
    await mockSendEvent(makeEvent(rev("d"), "fresh", false));
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"d".repeat(8)}`);
    await shot(page, "sse/revision-jump");
  });

  test("reset_required clears selection, focus and highlight", async ({ page }) => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);
    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");

    await page.locator('.node[data-task-id="TASK-BETA"]').click();
    await expect(page.locator(".detail-title")).toContainText("TASK-BETA");
    await page.getByRole("button", { name: "只高亮选中节点的上游链" }).click();
    await expect(page.locator(".focus-banner")).toContainText("聚焦上游：TASK-BETA");
    await page.getByRole("button", { name: /并行候选（2）/ }).click();

    const revE = reviseSnapshot(revA, rev("e"));
    await mockSetSnapshot(revE);
    await mockSendEvent(makeEvent(rev("e"), "fresh", true));
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"e".repeat(8)}`);
    await expect(page.locator(".node-selected")).toHaveCount(0);
    await expect(page.locator(".focus-banner")).toHaveCount(0);
    await expect(page.locator(".detail-title")).toHaveText("任务详情");
    await expect(page.getByRole("button", { name: /并行候选（2）/ })).toHaveAttribute("aria-pressed", "false");
    await shot(page, "sse/reset-required");
  });

  test("same-revision reset_required clears view state even when GET answers 304", async ({ page }) => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);
    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");

    await page.locator('.node[data-task-id="TASK-BETA"]').click();
    await expect(page.locator(".detail-title")).toContainText("TASK-BETA");
    await page.getByRole("button", { name: "只高亮选中节点的上游链" }).click();
    await expect(page.locator(".focus-banner")).toContainText("聚焦上游：TASK-BETA");
    await page.getByRole("button", { name: /并行候选（2）/ }).click();

    // Reconnect-style frame: current revision + reset_required. The ETag
    // re-fetch answers 304, which must not undo the reset.
    await mockSendEvent(makeEvent(revA.revision, "fresh", true));
    await expect(page.locator(".node-selected")).toHaveCount(0);
    await expect(page.locator(".focus-banner")).toHaveCount(0);
    await expect(page.locator(".detail-title")).toHaveText("任务详情");
    await expect(page.getByRole("button", { name: /并行候选（2）/ })).toHaveAttribute("aria-pressed", "false");
    // Snapshot itself is untouched (304): same revision, same nodes.
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${revA.revision.slice(0, 8)}`);
    await expect(page.locator(".node")).toHaveCount(5);
    await shot(page, "sse/same-revision-reset-304");
  });

  test("disconnection shows reconnecting state and recovers automatically", async ({ page }) => {
    await mockReset();
    await mockSetSnapshot(buildGraphSnapshot());
    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");

    // Select a node: a clean reconnect (Last-Event-ID == current revision)
    // must not trigger a spurious reset.
    await page.locator('.node[data-task-id="TASK-BETA"]').click();
    await expect(page.locator(".detail-title")).toContainText("TASK-BETA");

    await mockSetSseDown(true);
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：断线重连中");
    await shot(page, "sse/reconnecting");

    await mockSetSseDown(false);
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await expect(page.locator(".visually-hidden[aria-live]")).toContainText("实时连接已建立");
    await expect(page.locator(".detail-title")).toContainText("TASK-BETA");
    await expect(page.locator(".node-selected")).toHaveCount(1);
    await shot(page, "sse/reconnected");
  });

  test("snapshot unavailable shows a retryable error and recovers via retry", async ({ page }) => {
    await mockReset(); // no snapshot: /api/v1/snapshot answers 503
    await page.goto("/?view=network");
    const banner = page.locator(".overlay-error");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("SNAPSHOT_UNAVAILABLE");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已断开");
    await shot(page, "sse/snapshot-unavailable");

    await mockSetSnapshot(buildGraphSnapshot());
    await page.locator(".overlay-retry").click();
    await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await expect(page.locator(".node")).toHaveCount(5);
    await shot(page, "sse/retry-recovered");
  });
});

test.describe("out-of-order response protection", () => {
  test("a slower older snapshot response never overwrites a newer revision", async ({ page }) => {
    const revA = buildGraphSnapshot();
    const revB = reviseSnapshot(revA, rev("b"));
    const revC = reviseSnapshot(revA, rev("c"));
    await mockReset();
    await mockSetSnapshot(revA);

    // Controlled disorder: the first SSE-triggered GET is artificially slow
    // and returns revision B; the next GET returns C immediately. Without
    // serialization B would complete last and regress the UI.
    let getCount = 0;
    await page.route("**/api/v1/snapshot", async (route) => {
      getCount += 1;
      if (getCount === 1) {
        await route.continue(); // initial load
        return;
      }
      if (getCount === 2) {
        await route.fulfill({ status: 304, body: "" }); // initial-connect reset re-fetch
        return;
      }
      if (getCount === 3) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          headers: { ETag: `"sha256-${revB.revision}"` },
          body: JSON.stringify(revB),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { ETag: `"sha256-${revC.revision}"` },
        body: JSON.stringify(revC),
      });
    });

    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    await mockSendEvent(makeEvent(rev("c"), "fresh", false));

    // The UI settles on the newest revision and never regresses to B, even
    // after the slow B response has completed.
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"c".repeat(8)}`);
    await page.waitForTimeout(1200);
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"c".repeat(8)}`);
    await expect(page.locator(STATUS_BAR)).not.toContainText(`revision：${"b".repeat(8)}`);
    await shot(page, "sse/out-of-order-snapshot");
  });

  test("a slower older task detail never overwrites newer detail facts", async ({ page }) => {
    const revA = buildGraphSnapshot();
    const revB = reviseSnapshot(revA, rev("b"));
    const oldDetail = makeTaskDetail(revA, "TASK-ALPHA", { title: "旧详情标题" });
    const newDetail = makeTaskDetail(revB, "TASK-ALPHA", { title: "新详情标题" });
    await mockReset();
    await mockSetSnapshot(revA);

    let detailCount = 0;
    await page.route("**/api/v1/tasks/**", async (route) => {
      detailCount += 1;
      if (detailCount === 1) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(oldDetail) });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(newDetail) });
    });

    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await page.locator('.node[data-task-id="TASK-ALPHA"]').click();

    // A new snapshot revision arrives while the first detail request is
    // still in flight; it triggers a second detail fetch bound to revision B.
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));

    const detail = page.locator(".detail-panel");
    await expect(detail).toContainText("新详情标题");
    // The stale reply completes around 800ms later and must be dropped.
    await page.waitForTimeout(1200);
    await expect(detail).toContainText("新详情标题");
    await expect(detail).not.toContainText("旧详情标题");
    await shot(page, "sse/out-of-order-detail");
  });

  test("a current reply whose payload revision mismatches is discarded and the panel recovers", async ({ page }) => {
    const revA = buildGraphSnapshot();
    const revB = reviseSnapshot(revA, rev("b"));
    // The same payload is first cross-revision (served while the snapshot is
    // A) and later current (once the snapshot has moved to B).
    const crossDetail = makeTaskDetail(revB, "TASK-ALPHA", { title: "跨代详情标题" });
    await mockReset();
    await mockSetSnapshot(revA);

    await page.route("**/api/v1/tasks/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(crossDetail) });
    });

    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await page.locator('.node[data-task-id="TASK-ALPHA"]').click();

    // The reply carries revision B while the snapshot is A: it must never be
    // displayed (no cross-revision facts), the panel stays in loading.
    const detail = page.locator(".detail-panel");
    await page.waitForTimeout(600);
    await expect(detail).toContainText("正在加载任务详情");
    await expect(detail).not.toContainText("跨代详情标题");
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${revA.revision.slice(0, 8)}`);
    await shot(page, "sse/detail-revision-mismatch-dropped");

    // Recovery: the snapshot moves to B; the re-triggered fetch now returns
    // a payload whose revision matches, and the panel shows it.
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"b".repeat(8)}`);
    await expect(detail).toContainText("跨代详情标题");
    await shot(page, "sse/detail-revision-mismatch-recovered");
  });
});

test.describe("mock wire contract oracles", () => {
  test("snapshot ETag is exactly \"sha256-<revision>\" and 304 semantics hold", async () => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);

    const response = await fetch(`${BASE}/api/v1/snapshot`);
    expect(response.status).toBe(200);
    expect(response.headers.get("etag")).toBe(`"sha256-${revA.revision}"`);
    expect(response.headers.get("cache-control")).toContain("no-cache");

    const matched = await fetch(`${BASE}/api/v1/snapshot`, {
      headers: { "If-None-Match": `"sha256-${revA.revision}"` },
    });
    expect(matched.status).toBe(304);
  });

  test("events stream declares retry 2000 and the contract initial-connect reset", async () => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);

    // Initial connect (no Last-Event-ID): retry 2000, then the current
    // revision with every task ID and reset_required=true.
    const first = await readSseHead(`${BASE}/api/v1/events`);
    expect(first).toContain("retry: 2000");
    expect(first).toContain("event: snapshot");
    expect(first).toContain(`id: ${revA.revision}`);
    const initial = parseSseData(first);
    expect(initial.reset_required).toBe(true);
    expect(initial.revision).toBe(revA.revision);
    expect([...initial.changed_task_ids].sort()).toEqual([...GRAPH_TASKS].sort());

    // Reconnect with a matching Last-Event-ID: only the retry directive, no frame.
    const waiting = await readSseHead(`${BASE}/api/v1/events`, { "Last-Event-ID": revA.revision });
    expect(waiting).toContain("retry: 2000");
    expect(waiting).not.toContain("event: snapshot");

    // Reconnect with a stale Last-Event-ID: immediate reset, empty change list.
    const stale = await readSseHead(`${BASE}/api/v1/events`, { "Last-Event-ID": rev("f") });
    const reset = parseSseData(stale);
    expect(reset.reset_required).toBe(true);
    expect(reset.revision).toBe(revA.revision);
    expect(reset.changed_task_ids).toEqual([]);
  });

  test("events route answers 503 while no snapshot exists", async () => {
    await mockReset();
    const response = await fetch(`${BASE}/api/v1/events`);
    expect(response.status).toBe(503);
  });

  test("error envelopes carry the current revision with a snapshot, null without", async () => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);

    // Unknown task with a current snapshot: envelope revision == revision.
    const unknownTask = await fetch(`${BASE}/api/v1/tasks/TASK-NOPE`);
    expect(unknownTask.status).toBe(404);
    expect(unknownTask.headers.get("content-type")).toContain("application/json");
    const taskEnvelope = (await unknownTask.json()) as { error: { code: string }; revision: string | null };
    expect(taskEnvelope.error.code).toBe("TASK_NOT_FOUND");
    expect(taskEnvelope.revision).toBe(revA.revision);

    // Unknown route with a current snapshot: same rule.
    const unknownRoute = await fetch(`${BASE}/api/v1/nope`);
    expect(unknownRoute.status).toBe(404);
    const routeEnvelope = (await unknownRoute.json()) as { error: { code: string }; revision: string | null };
    expect(routeEnvelope.error.code).toBe("ROUTE_NOT_FOUND");
    expect(routeEnvelope.revision).toBe(revA.revision);

    // Without any snapshot the envelope revision is null.
    await mockReset();
    const noSnapTask = await fetch(`${BASE}/api/v1/tasks/TASK-NOPE`);
    expect(noSnapTask.status).toBe(404);
    expect(((await noSnapTask.json()) as { revision: string | null }).revision).toBeNull();
    const noSnapRoute = await fetch(`${BASE}/api/v1/nope`);
    expect(noSnapRoute.status).toBe(404);
    expect(((await noSnapRoute.json()) as { revision: string | null }).revision).toBeNull();
  });
});

test.describe("SSE protocol errors", () => {
  test("malformed frames surface a visible protocol error, do not pollute state and recover", async ({ page }) => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);

    // Slow down post-startup snapshot GETs so the (transient) protocol banner
    // is observable before the controlled re-sync clears it.
    let getCount = 0;
    await page.route("**/api/v1/snapshot", async (route) => {
      getCount += 1;
      if (getCount <= 2) {
        await route.continue(); // initial load + initial-connect reset re-fetch
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 400));
      await route.continue();
    });

    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");

    // Malformed JSON frame, then a schema-drifting frame: both must be
    // visible, neither may corrupt the displayed snapshot.
    await mockSendRawEvent("event: snapshot\nid: bad\ndata: {not json");
    const banner = page.locator(".overlay-error");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("协议错误");
    const drifted = { ...makeEvent(revA.revision, "fresh", false), state: "half-fresh" };
    await mockSendRawEvent(`event: snapshot\nid: bad2\ndata: ${JSON.stringify(drifted)}`);
    await expect(banner).toBeVisible();
    await expect(page.locator(".visually-hidden[aria-live]")).toContainText("实时事件流协议错误");
    await shot(page, "sse/protocol-error");

    // Local state is untouched: same revision, same graph, still connected.
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${revA.revision.slice(0, 8)}`);
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await expect(page.locator(".node")).toHaveCount(5);

    // Recovery: a valid frame carrying a new revision clears the banner.
    const revB = reviseSnapshot(revA, rev("b"));
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    await expect(banner).toHaveCount(0);
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"b".repeat(8)}`);
    await shot(page, "sse/protocol-error-recovered");
  });

  test("a controlled 304 re-sync clears the protocol banner but never a genuine failure", async ({ page }) => {
    const revA = buildGraphSnapshot();
    const revB = reviseSnapshot(revA, rev("b"));
    await mockReset();
    await mockSetSnapshot(revA);

    let getCount = 0;
    let abortNext = false;
    await page.route("**/api/v1/snapshot", async (route) => {
      getCount += 1;
      if (getCount <= 2) {
        await route.continue();
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 300));
      if (abortNext) {
        abortNext = false;
        await route.abort();
        return;
      }
      await route.continue();
    });

    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");

    // Protocol error: the banner renders, then the controlled re-sync (ETag
    // GET answered 304) counts as a successful re-sync and clears it — the
    // snapshot, graph and connection stay untouched.
    await mockSendRawEvent("event: snapshot\nid: bad\ndata: {not json");
    const banner = page.locator(".overlay-error");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("协议错误");
    await expect(banner).toHaveCount(0);
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${revA.revision.slice(0, 8)}`);
    await expect(page.locator(".node")).toHaveCount(5);
    await shot(page, "sse/protocol-error-recovered-304");

    // A genuine failure (aborted GET) is NOT cleared by a later 304: the
    // banner survives a same-revision re-read and only a real 200 clears it.
    abortNext = true;
    await mockSendEvent(makeEvent(revA.revision, "fresh", false));
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("无法连接本地 API");
    const notModified = page.waitForResponse(
      (response) => response.url().includes("/api/v1/snapshot") && response.status() === 304,
    );
    await mockSendEvent(makeEvent(revA.revision, "fresh", false));
    await notModified;
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("无法连接本地 API");
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    await expect(banner).toHaveCount(0);
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"b".repeat(8)}`);
  });
});

test.describe("response body read failures", () => {
  test("a snapshot reply that drops mid-body surfaces a network error and the event chain recovers", async ({
    page,
  }) => {
    const revA = buildGraphSnapshot();
    const revB = reviseSnapshot(revA, rev("b"));
    const revC = reviseSnapshot(revA, rev("c"));
    await mockReset();
    await mockSetSnapshot(revA);

    // Wait for the initial-connect reset re-fetch (304) before arming the
    // truncation hook, so exactly the event-triggered GET is truncated.
    const startupRefetch = page.waitForResponse(
      (response) => response.url().includes("/api/v1/snapshot") && response.status() === 304,
    );
    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await startupRefetch;

    // Headers arrive, then the connection dies mid-body: the refresh must
    // surface a visible network failure instead of silently keeping stale facts.
    await mockTruncateSnapshot();
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    const banner = page.locator(".overlay-error");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("无法连接本地 API");
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${revA.revision.slice(0, 8)}`);
    await shot(page, "sse/body-read-failure");

    // The chain continues: the next event re-syncs successfully, clears the
    // banner and applies the newest revision.
    await mockSetSnapshot(revC);
    await mockSendEvent(makeEvent(rev("c"), "fresh", false));
    await expect(banner).toHaveCount(0);
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"c".repeat(8)}`);
    await expect(page.locator(".node")).toHaveCount(5);
    await shot(page, "sse/body-read-recovered");
  });
});

test.describe("diagnostics drawer accessibility under live updates", () => {
  test("drawer keeps focus and expanded state across snapshot and connection updates", async ({ page }) => {
    const revA = buildGraphSnapshot();
    await mockReset();
    await mockSetSnapshot(revA);
    await page.goto("/?view=network");
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");

    const toggle = page.locator(".diag-drawer-toggle");
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".diag-drawer-list")).toBeVisible();
    await toggle.focus();

    // Revision update with unchanged diagnostics: the drawer DOM survives.
    const revB = reviseSnapshot(revA, rev("b"));
    await mockSetSnapshot(revB);
    await mockSendEvent(makeEvent(rev("b"), "fresh", false));
    await expect(page.locator(STATUS_BAR)).toContainText(`revision：${"b".repeat(8)}`);
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".diag-drawer-list")).toBeVisible();

    // Connection updates: focus and expanded state survive as well.
    await mockSetSseDown(true);
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：断线重连中");
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await mockSetSseDown(false);
    await expect(page.locator(STATUS_BAR)).toContainText("实时连接：已连接");
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await shot(page, "sse/drawer-focus-kept");

    // Genuinely changed diagnostics rebuild the drawer: focus returns to the
    // toggle (the only focusable drawer control) and aria-expanded stays true.
    const revC = reviseSnapshot(revA, rev("c"));
    revC.diagnostics.push(makeDiagnostic(403, "info", ["TASK-ALPHA"]) as unknown as (typeof revC.diagnostics)[number]);
    await mockSetSnapshot(revC);
    await mockSendEvent(makeEvent(rev("c"), "fresh", false));
    await expect(toggle).toContainText("诊断（3）");
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".diag-drawer-list")).toBeVisible();
    await shot(page, "sse/drawer-focus-restored-after-rebuild");
  });
});

/** Read the first SSE chunk(s) until a full line batch arrives, then abort. */
async function readSseHead(url: string, headers: Record<string, string> = {}): Promise<string> {
  const controller = new AbortController();
  try {
    const response = await fetch(url, { headers, signal: controller.signal });
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let text = "";
    for (let i = 0; i < 4 && !text.includes("\n\n"); i += 1) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      text += decoder.decode(value, { stream: true });
    }
    return text;
  } finally {
    controller.abort();
  }
}

/** Extract and parse the single JSON `data:` payload from an SSE head. */
function parseSseData(text: string): {
  revision: string;
  reset_required: boolean;
  changed_task_ids: string[];
} {
  const dataLine = text.split(/\r?\n/).find((line) => line.startsWith("data:"));
  expect(dataLine, `SSE head carries a data line: ${text}`).toBeDefined();
  return JSON.parse(dataLine!.slice("data:".length).trim()) as {
    revision: string;
    reset_required: boolean;
    changed_task_ids: string[];
  };
}
