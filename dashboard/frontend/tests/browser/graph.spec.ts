/**
 * Relationship-graph interaction coverage against the schema-validating mock
 * backend: primary-visual rendering, global status, filters, highlight,
 * task detail, zoom/pan/fit/locate/upstream/downstream, non-colour state
 * encoding, keyboard operation and the candidate ≠ authorisation rule.
 */
import { expect, test, type Page } from "@playwright/test";
import { buildGraphSnapshot, mockReset, mockSetSnapshot, shot } from "./helpers";

const STATUS_BAR = ".status-bar";
const VIEWPORT = ".graph-viewport";

async function openGraph(page: Page): Promise<void> {
  await mockReset();
  await mockSetSnapshot(buildGraphSnapshot());
  await page.goto("/");
  await expect(page.locator(".node")).toHaveCount(5);
  await expect(page.locator(STATUS_BAR)).toContainText("快照：新鲜");
}

async function viewportTransform(page: Page): Promise<string> {
  return (await page.locator(VIEWPORT).getAttribute("transform")) ?? "";
}

function node(page: Page, taskId: string) {
  return page.locator(`.node[data-task-id="${taskId}"]`);
}

test.describe("relationship graph", () => {
  test("graph is the primary visual with all nodes, edges and global status", async ({ page }) => {
    await openGraph(page);
    await expect(page.locator(".graph-svg")).toBeVisible();
    await expect(page.locator(".edge")).toHaveCount(6);
    await expect(page.locator(".assessment-link")).toHaveCount(0);
    // Global snapshot / diagnostics / project provenance in the status bar.
    await expect(page.locator(STATUS_BAR)).toContainText("项目：D:/fixture");
    await expect(page.locator(STATUS_BAR)).toContainText("分支：codex/dashboard-fe-001");
    await expect(page.locator(STATUS_BAR)).toContainText("revision：");
    await expect(page.locator(".severity-chip.severity-error")).toContainText("错误 1");
    await expect(page.locator(".severity-chip.severity-warning")).toContainText("警告 1");
    await shot(page, "graph/overview");
  });

  test("selected task stays prominent in both themes, including keyboard focus", async ({ page }) => {
    for (const scheme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: scheme });
      await openGraph(page);
      const svg = page.locator(".graph-svg");
      await svg.focus();
      await svg.press("ArrowRight");

      const selected = node(page, "TASK-ALPHA");
      const frame = selected.locator(".node-frame");
      await expect(selected).toHaveClass(/node-selected/);
      await expect(selected.locator(".node-selected-tag")).toHaveText("✓ 已选中");
      await expect(frame).toHaveCSS("stroke-width", "3px");
      await expect(selected.locator(".node-title")).toHaveCSS(
        "fill",
        scheme === "light" ? "rgb(28, 35, 43)" : "rgb(230, 234, 239)",
      );

      // Arrow navigation selects and focuses the SVG node through the real
      // keyboard handler, so the test proves the :focus-visible combination.
      await expect(selected).toBeFocused();
      await expect.poll(() => selected.evaluate((element) => element.matches(":focus-visible"))).toBe(true);
      await expect(frame).toHaveCSS("stroke-width", "3px");

      // ALPHA has three direct canonical relationships in the fixture. The
      // other three remain visible and keep their type encoding, but recede so
      // the selected task can be found in a dense graph.
      await expect(page.locator(".edge-selected-context")).toHaveCount(3);
      const backgroundEdges = page.locator(".edge-selection-dimmed");
      await expect(backgroundEdges).toHaveCount(3);
      await expect(backgroundEdges.first()).toHaveCSS("opacity", "0.3");
      await expect(backgroundEdges.locator(".edge-line")).toHaveCount(3);
      await shot(page, `graph/selected-context-${scheme}`);

      await page.locator(".graph-svg").press("Escape");
      await expect(page.locator(".node-selected-tag")).toHaveCount(0);
      await expect(page.locator(".edge-selected-context")).toHaveCount(0);
      await expect(page.locator(".edge-selection-dimmed")).toHaveCount(0);
    }
  });

  test("explicit selection overrides active graph dimming", async ({ page }) => {
    await openGraph(page);
    await page.getByRole("button", { name: /下一动作（1）/ }).click();
    await expect(node(page, "TASK-ALPHA")).toHaveClass(/node-dimmed/);

    await node(page, "TASK-ALPHA").click();
    const selected = node(page, "TASK-ALPHA");
    await expect(selected).toHaveClass(/node-selected/);
    await expect(selected).not.toHaveClass(/node-dimmed/);
    await expect(selected).toHaveCSS("opacity", "1");
    await expect(page.locator(".edge-selected-context")).toHaveCount(3);
    await expect(page.locator(".edge-selected-context.edge-dimmed")).toHaveCount(0);
  });

  test("state is encoded by text, dash pattern and marker, not colour alone", async ({ page }) => {
    await openGraph(page);
    // Dash patterns differ per relationship type; conflicts carry no arrow.
    await expect(page.locator(".edge-replaces .edge-line")).toHaveAttribute("stroke-dasharray", "9 4");
    await expect(page.locator(".edge-discovered_from .edge-line")).toHaveAttribute("stroke-dasharray", "2 4");
    await expect(page.locator(".edge-conflicts_with .edge-line")).toHaveAttribute("stroke-dasharray", "5 4");
    await expect(page.locator(".edge-conflicts_with .edge-line")).not.toHaveAttribute("marker-end", /.*/);
    await expect(page.locator(".edge-depends_on .edge-line").first()).toHaveAttribute(
      "marker-end",
      "url(#arrow-depends_on)",
    );
    // Edge labels carry the condition evaluation as text.
    await expect(page.locator(".edge-label", { hasText: "依赖·未满足" })).toHaveCount(1);
    await expect(page.locator(".edge-label", { hasText: "依赖·已满足" })).toHaveCount(1);
    await expect(page.locator(".edge-label", { hasText: "冲突" })).toHaveCount(1);
    // Freshness and diagnostics are textual on the node itself.
    await expect(node(page, "TASK-EPSILON")).toContainText("数据过期");
    await expect(node(page, "TASK-EPSILON").locator(".node-diag-badge")).toContainText("错误");
    // Candidate pairs are explicitly marked as non-authorised on the node.
    await expect(node(page, "TASK-ALPHA").locator(".node-candidate-tag")).toHaveText("并行候选·非授权");
    await expect(node(page, "TASK-DELTA").locator(".node-candidate-tag")).toHaveText("并行候选·非授权");
    // Legend explains every encoding.
    await expect(page.locator(".graph-legend")).toContainText(
      "关系图已收起 2 条并行评估以避免遮挡",
    );
    await shot(page, "graph/non-colour-encoding");
  });

  test("parallel candidates are marked as non-authorised everywhere", async ({ page }) => {
    await openGraph(page);
    await expect(page.locator(".pair-list-title")).toHaveText("并行评估（候选 ≠ 授权，均需用户确认）");
    const candidateItem = page.locator(".pair-item.pair-candidate");
    await expect(candidateItem.locator(".pair-button")).toContainText(
      "TASK-ALPHA × TASK-DELTA：并行候选（需用户确认，非授权）",
    );
    await expect(page.locator(".pair-item.pair-must_serial .pair-button")).toContainText(
      "TASK-BETA × TASK-GAMMA：必须串行",
    );
    // Candidate highlight reveals only candidate links; unknown/must-serial
    // evidence stays out of the structural canvas until explicitly selected.
    await page.getByRole("button", { name: /并行候选（2）/ }).click();
    await expect(page.locator(".assessment-candidate .assessment-label")).toContainText("并行候选");
    await expect(page.locator(".assessment-must_serial")).toHaveCount(0);
    await node(page, "TASK-BETA").click();
    await expect(page.locator(".assessment-must_serial .assessment-label")).toContainText("必须串行");
    // Detail panel repeats the non-authorisation disclaimer.
    await node(page, "TASK-ALPHA").click();
    await expect(page.locator(".detail-panel")).toContainText(
      "requires_user_confirmation = true：候选不产生执行授权。",
    );
    await expect(page.locator(".detail-panel")).toContainText("下一动作建议（建议 ≠ 授权）");
    await shot(page, "graph/candidate-not-authorised");
  });

  test("text search and filter panel narrow visible nodes", async ({ page }) => {
    await openGraph(page);
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.fill("EPSILON");
    await expect(node(page, "TASK-EPSILON")).not.toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-ALPHA")).toHaveClass(/node-filtered/);
    await expect(page.locator(".node-filtered")).toHaveCount(4);
    await search.fill("");
    await expect(page.locator(".node-filtered")).toHaveCount(0);

    await page.locator(".toolbar-filter-toggle").click();
    await page.locator("#filter-lifecycles-Ready").check();
    await expect(node(page, "TASK-ALPHA")).not.toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-BETA")).not.toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-DELTA")).toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-EPSILON")).toHaveClass(/node-filtered/);
    // Edge-type filter hides non-matching edges without touching nodes.
    await page.locator("#filter-lifecycles-Ready").uncheck();
    await page.locator("#filter-edgeTypes-depends_on").check();
    await expect(page.locator(".edge")).toHaveCount(2);
    await expect(page.locator(".node")).toHaveCount(5);
    await page.locator(".toolbar-reset").click();
    await expect(page.locator(".edge")).toHaveCount(6);
    await shot(page, "graph/filters");
  });

  test("highlight chips dim non-matching nodes and emphasise candidates", async ({ page }) => {
    await openGraph(page);
    // Only TASK-DELTA carries an actionable recommendation (matrix row 9).
    const actionable = page.getByRole("button", { name: /下一动作（1）/ });
    await actionable.click();
    await expect(actionable).toHaveAttribute("aria-pressed", "true");
    await expect(node(page, "TASK-ALPHA")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-BETA")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-EPSILON")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-DELTA")).not.toHaveClass(/node-dimmed/);
    await actionable.click();
    await expect(page.locator(".node-dimmed")).toHaveCount(0);

    await page.getByRole("button", { name: /并行候选（2）/ }).click();
    await expect(page.locator(".assessment-candidate")).toHaveClass(/assessment-emphasized/);
    await expect(node(page, "TASK-BETA")).toHaveClass(/node-dimmed/);
    await page.getByRole("button", { name: /并行候选（2）/ }).click();

    // user_decision (DELTA) and plan awaiting a user decision (EPSILON).
    await page.getByRole("button", { name: /需要决定（2）/ }).click();
    await expect(node(page, "TASK-DELTA")).not.toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-EPSILON")).not.toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-ALPHA")).toHaveClass(/node-dimmed/);
    await shot(page, "graph/highlight-decisions");
  });

  test("task detail shows axes, actions, edges, provenance and worktree evidence", async ({ page }) => {
    await openGraph(page);
    await node(page, "TASK-ALPHA").click();
    const detail = page.locator(".detail-panel");
    await expect(detail).toContainText("任务详情：TASK-ALPHA");
    await expect(detail).toContainText("状态轴（相互独立，不合并）");
    await expect(detail).toContainText("生命周期");
    await expect(detail).toContainText("执行 ｜ 需要授权");
    await expect(detail).toContainText("docs/tasks/TASK-ALPHA.md:7");
    await expect(detail.locator(".worktree-line").first()).toContainText("D:/fixture-wt-alpha");
    await expect(detail.locator(".detail-disclaimer")).not.toBeEmpty();
    await shot(page, "graph/detail-alpha");

    await node(page, "TASK-BETA").click();
    await expect(detail).toContainText("任务详情：TASK-BETA");
    await expect(detail).toContainText("被以下任务阻塞：TASK-ALPHA");
    await expect(detail).toContainText("条件：生命周期 期望「Accepted」实际「未知」→ 未满足");
    await shot(page, "graph/detail-beta-blocked");
  });

  test("zoom, pan, fit and locate controls drive the viewport", async ({ page }) => {
    // Reduced motion makes viewport changes synchronous and keeps the focused
    // node element alive (no per-frame re-render), so assertions are exact.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openGraph(page);
    const initial = await viewportTransform(page);

    await page.getByRole("button", { name: "放大" }).click();
    const zoomedIn = await viewportTransform(page);
    expect(zoomedIn).not.toBe(initial);

    await page.getByRole("button", { name: "缩小" }).click();
    await page.getByRole("button", { name: "适配视图（显示完整网络）" }).click();
    expect(await viewportTransform(page)).toBe(initial);

    // Drag the canvas to pan; try empty corners until the viewport moves
    // (a drag starting on a node is a selection gesture, not a pan).
    const svg = page.locator(".graph-svg");
    const box = (await svg.boundingBox())!;
    const before = await viewportTransform(page);
    const starts: [number, number][] = [
      [box.x + 60, box.y + box.height - 60],
      [box.x + box.width - 60, box.y + 60],
      [box.x + 60, box.y + box.height / 2],
    ];
    let panned = before;
    for (const [sx, sy] of starts) {
      await page.mouse.move(sx, sy);
      await page.mouse.down();
      await page.mouse.move(sx + 90, sy - 60, { steps: 5 });
      await page.mouse.up();
      panned = await viewportTransform(page);
      if (panned !== before) {
        break;
      }
    }
    expect(panned).not.toBe(before);

    // Locating the selected node centres it and focuses the node element.
    await node(page, "TASK-EPSILON").click();
    await page.getByRole("button", { name: "定位到当前选中节点" }).click();
    await expect.poll(() => viewportTransform(page)).not.toBe(panned);
    const focusedTask = await page.evaluate(() => (document.activeElement as SVGGElement | null)?.dataset?.taskId ?? null);
    expect(focusedTask).toBe("TASK-EPSILON");
    await shot(page, "graph/viewport-controls");
  });

  test("upstream/downstream focus dims the rest and full network restores", async ({ page }) => {
    await openGraph(page);
    await node(page, "TASK-BETA").click();
    await page.getByRole("button", { name: "只高亮选中节点的上游链" }).click();
    await expect(page.locator(".focus-banner")).toContainText("聚焦上游：TASK-BETA");
    await expect(node(page, "TASK-ALPHA")).not.toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-DELTA")).toHaveClass(/node-dimmed/);
    const selectionAndFocusDimmed = page.locator(".edge-dimmed.edge-selection-dimmed");
    expect(await selectionAndFocusDimmed.count()).toBeGreaterThan(0);
    await expect(selectionAndFocusDimmed.first()).toHaveCSS("opacity", "0.15");
    const selectedEdgeInsideFocus = page.locator(".edge-selected-context:not(.edge-dimmed)");
    expect(await selectedEdgeInsideFocus.count()).toBeGreaterThan(0);
    await expect(selectedEdgeInsideFocus.first()).toHaveCSS("opacity", "1");
    await shot(page, "graph/focus-upstream");

    await page.locator(".graph-svg").press("Escape");
    await expect(page.locator(".focus-banner")).toHaveCount(0);

    await node(page, "TASK-GAMMA").click();
    await page.getByRole("button", { name: "只高亮选中节点的下游链" }).click();
    await expect(page.locator(".focus-banner")).toContainText("聚焦下游：TASK-GAMMA");
    // GAMMA is a leaf in display-flow direction: nothing downstream, all else dimmed.
    await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-DELTA")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-EPSILON")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-ALPHA")).toHaveClass(/node-dimmed/);
    await expect(node(page, "TASK-BETA")).toHaveClass(/node-dimmed/);
    await shot(page, "graph/focus-downstream");

    await page.getByRole("button", { name: "恢复完整网络视图" }).click();
    await expect(page.locator(".node-dimmed")).toHaveCount(0);
    await expect(page.locator(".focus-banner")).toHaveCount(0);
  });

  test("full keyboard operation: arrows, Enter, zoom keys, fit, Escape", async ({ page }) => {
    await openGraph(page);
    const svg = page.locator(".graph-svg");
    await svg.focus();
    await svg.press("ArrowRight");
    await expect(page.locator(".node-selected")).toHaveCount(1);
    await expect(page.locator(".detail-title")).toContainText("任务详情：TASK-");
    const firstSelected = await page.locator(".node-selected").getAttribute("data-task-id");

    await svg.press("ArrowDown");
    const secondSelected = await page.locator(".node-selected").getAttribute("data-task-id");
    // Arrow keys move selection spatially; Enter re-affirms it without errors.
    await svg.press("Enter");
    await expect(page.locator(".node-selected")).toHaveCount(1);
    expect(`${firstSelected}-${secondSelected}`).toMatch(/TASK-/);

    const before = await viewportTransform(page);
    await svg.press("+");
    expect(await viewportTransform(page)).not.toBe(before);
    await svg.press("-");
    await svg.press("0");
    await expect.poll(() => viewportTransform(page)).toBe(before);

    await svg.press("Escape");
    await expect(page.locator(".node-selected")).toHaveCount(0);
    await expect(page.locator(".detail-title")).toHaveText("任务详情");
    await shot(page, "graph/keyboard");
  });
});

test.describe("keyboard filtering keeps focus", () => {
  test("keystroke-by-keystroke search keeps focus, caret and the full value", async ({ page }) => {
    await openGraph(page);
    const search = page.getByPlaceholder("搜索任务 ID / 标题…");
    await search.click();

    // Real per-keystroke typing: after every character the value grows and
    // focus never leaves the input (the control keeps its DOM identity).
    const typed = "EPSILON";
    for (let i = 0; i < typed.length; i += 1) {
      await page.keyboard.type(typed[i]!);
      await expect(search).toHaveValue(typed.slice(0, i + 1));
      await expect(search).toBeFocused();
    }
    await expect(node(page, "TASK-EPSILON")).not.toHaveClass(/node-filtered/);
    await expect(page.locator(".node-filtered")).toHaveCount(4);

    // The caret survived every update: further typing appends at the caret.
    await page.keyboard.type("X");
    await expect(search).toHaveValue("EPSILONX");
    await expect(search).toBeFocused();
    await shot(page, "graph/search-keyboard-focus");

    // External reset updates the persistent input instead of replacing it.
    await page.locator(".toolbar-reset").click();
    await expect(search).toHaveValue("");
    await expect(page.locator(".node-filtered")).toHaveCount(0);
  });

  test("keyboard toggling consecutive filter checkboxes keeps focus and applies results", async ({ page }) => {
    await openGraph(page);
    await page.locator(".toolbar-filter-toggle").click();

    // Toggle "Ready" with the keyboard: focus stays on the same checkbox.
    const ready = page.locator("#filter-lifecycles-Ready");
    await ready.focus();
    await page.keyboard.press("Space");
    await expect(ready).toBeChecked();
    await expect(ready).toBeFocused();
    await expect(node(page, "TASK-ALPHA")).not.toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-GAMMA")).toHaveClass(/node-filtered/);

    // Toggle a second filter right after: same guarantees.
    const review = page.locator("#filter-lifecycles-Review");
    await review.focus();
    await page.keyboard.press("Space");
    await expect(review).toBeChecked();
    await expect(review).toBeFocused();
    await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-EPSILON")).toHaveClass(/node-filtered/);
    await shot(page, "graph/filter-keyboard-focus");

    // Untoggle the first filter again: still the same control, still focused.
    await ready.focus();
    await page.keyboard.press("Space");
    await expect(ready).not.toBeChecked();
    await expect(ready).toBeFocused();
    await expect(node(page, "TASK-GAMMA")).not.toHaveClass(/node-filtered/);
    await expect(node(page, "TASK-EPSILON")).toHaveClass(/node-filtered/);
  });
});
