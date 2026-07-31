/**
 * Responsive and accessibility coverage: three desktop widths with real
 * layout assertions and screenshots, keyboard focus visibility, basic
 * contrast checks, non-colour encoding under keyboard-only operation and
 * prefers-reduced-motion behaviour.
 */
import { expect, test, type Page } from "@playwright/test";
import { buildGraphSnapshot, mockReset, mockSetSnapshot, shot } from "./helpers";

async function openGraph(page: Page): Promise<void> {
  await mockReset();
  await mockSetSnapshot(buildGraphSnapshot());
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

async function expectNoRelationshipLabelOcclusion(page: Page, viewport: string): Promise<void> {
  const labels = page.locator(".edge-label, .assessment-label");
  const nodes = page.locator(".node");
  const labelCount = await labels.count();
  const nodeCount = await nodes.count();
  expect(labelCount).toBeGreaterThan(0);
  expect(nodeCount).toBeGreaterThan(0);

  for (let labelIndex = 0; labelIndex < labelCount; labelIndex += 1) {
    const label = labels.nth(labelIndex);
    const labelBox = await label.boundingBox();
    if (!labelBox) {
      continue;
    }
    const labelText = (await label.textContent())?.trim() || `#${labelIndex}`;
    for (let nodeIndex = 0; nodeIndex < nodeCount; nodeIndex += 1) {
      const node = nodes.nth(nodeIndex);
      const nodeBox = await node.boundingBox();
      if (!nodeBox) {
        continue;
      }
      const taskId = (await node.getAttribute("data-task-id")) ?? `#${nodeIndex}`;
      const labelPosition = {
        x: await label.getAttribute("x"),
        y: await label.getAttribute("y"),
        viewportTransform: await page.locator(".graph-viewport").getAttribute("transform"),
        nodeTransform: await node.getAttribute("transform"),
      };
      expect(
        intersects(labelBox, nodeBox),
        `relationship label "${labelText}" ${JSON.stringify(labelBox)} (${JSON.stringify(labelPosition)}) overlaps task card "${taskId}" ${JSON.stringify(nodeBox)} at ${viewport}`,
      ).toBe(false);
    }
    for (let otherIndex = labelIndex + 1; otherIndex < labelCount; otherIndex += 1) {
      const other = labels.nth(otherIndex);
      const otherBox = await other.boundingBox();
      if (!otherBox) {
        continue;
      }
      const otherText = (await other.textContent())?.trim() || `#${otherIndex}`;
      expect(
        intersects(labelBox, otherBox),
        `relationship label "${labelText}" overlaps relationship label "${otherText}" at ${viewport}`,
      ).toBe(false);
    }
  }
}

const VIEWPORTS = [
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
];

test.describe("responsive widths", () => {
  test("a one-node self-loop uses a visible, collision-free label lane", async ({ page }) => {
    const snapshot = buildGraphSnapshot();
    const task = snapshot.tasks[0]!;
    const selfLoop = snapshot.edges[0]!;
    selfLoop.source_task_id = task.task_id;
    selfLoop.target_task_id = task.task_id;
    snapshot.tasks = [task];
    snapshot.edges = [selfLoop];
    snapshot.actions = [];
    snapshot.parallel_assessments = [];
    snapshot.diagnostics = [];
    snapshot.summary.task_total = 1;
    snapshot.summary.edge_total = 1;
    await mockReset();
    await mockSetSnapshot(snapshot);
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");

    await expect(page.locator(".node")).toHaveCount(1);
    await expect(page.locator(".edge-label")).toHaveCount(1);
    await expectNoRelationshipLabelOcclusion(page, "1024x768 self-loop");
    const svgBox = (await page.locator(".graph-svg").boundingBox())!;
    const labelBox = (await page.locator(".edge-label").boundingBox())!;
    expect(labelBox.y).toBeGreaterThanOrEqual(svgBox.y);
    expect(labelBox.y + labelBox.height).toBeLessThanOrEqual(svgBox.y + svgBox.height);
  });

  test("multiple self-loop overflow rows stay inside the fitted viewport", async ({ page }) => {
    const snapshot = buildGraphSnapshot();
    const tasks = snapshot.tasks.slice(0, 2);
    const selfLoops = snapshot.edges.slice(0, 3).map((edge, index) => ({
      ...edge,
      source_task_id: tasks[index < 2 ? 0 : 1]!.task_id,
      target_task_id: tasks[index < 2 ? 0 : 1]!.task_id,
    }));
    snapshot.tasks = tasks;
    snapshot.edges = selfLoops;
    snapshot.actions = [];
    snapshot.parallel_assessments = [];
    snapshot.diagnostics = [];
    snapshot.summary.task_total = tasks.length;
    snapshot.summary.edge_total = selfLoops.length;
    await mockReset();
    await mockSetSnapshot(snapshot);
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");

    await expect(page.locator(".node")).toHaveCount(2);
    await expect(page.locator(".edge-label")).toHaveCount(3);
    await expectNoRelationshipLabelOcclusion(page, "1024x768 multi-self-loop");
    const firstFit = await page.locator(".graph-viewport").getAttribute("transform");
    const svgBox = (await page.locator(".graph-svg").boundingBox())!;
    for (const label of await page.locator(".edge-label").all()) {
      const labelBox = (await label.boundingBox())!;
      expect(labelBox.y).toBeGreaterThanOrEqual(svgBox.y);
      expect(labelBox.y + labelBox.height).toBeLessThanOrEqual(svgBox.y + svgBox.height);
    }

    snapshot.edges = [selfLoops[2]!, selfLoops[0]!, selfLoops[1]!];
    await mockSetSnapshot(snapshot);
    await page.reload();
    await expect(page.locator(".edge-label")).toHaveCount(3);
    expect(await page.locator(".graph-viewport").getAttribute("transform")).toBe(firstFit);
  });

  test("unknown parallel assessments stay in evidence views instead of obscuring the graph", async ({ page }) => {
    const snapshot = buildGraphSnapshot();
    const unknownAssessment = snapshot.parallel_assessments[0]!;
    unknownAssessment.result = "unknown";
    unknownAssessment.reason_codes = ["WORKTREE_EVIDENCE_UNKNOWN"];
    snapshot.parallel_assessments = [unknownAssessment];
    snapshot.edges = [];
    snapshot.summary.edge_total = 0;
    snapshot.summary.counts_by_relation = {
      depends_on: 0,
      parent: 0,
      replaces: 0,
      discovered_from: 0,
      conflicts_with: 0,
    };
    await mockReset();
    await mockSetSnapshot(snapshot);
    await page.goto("/");

    await expect(page.locator(".node")).toHaveCount(5);
    await expect(page.locator(".assessment-unknown")).toHaveCount(0);
    await expect(page.locator(".pair-item.pair-unknown")).toContainText("并行未知");
    await expect(page.locator(".pair-item.pair-unknown")).toContainText("Worktree 证据未知");
    const gridTracks = await page.locator(".node").evaluateAll((nodes) => ({
      columns: new Set(nodes.map((node) => Math.round(node.getBoundingClientRect().x))).size,
      rows: new Set(nodes.map((node) => Math.round(node.getBoundingClientRect().y))).size,
    }));
    expect(gridTracks.columns).toBeGreaterThan(1);
    expect(gridTracks.rows).toBeGreaterThan(1);
  });

  test("isolated tasks use a grid even when another component has a dependency", async ({ page }) => {
    const snapshot = buildGraphSnapshot();
    snapshot.edges = [snapshot.edges[0]!];
    snapshot.actions = [];
    snapshot.parallel_assessments = [];
    snapshot.diagnostics = [];
    snapshot.summary.edge_total = 1;
    snapshot.summary.counts_by_relation = {
      conflicts_with: 0,
      depends_on: 1,
      discovered_from: 0,
      parent: 0,
      replaces: 0,
    };
    await mockReset();
    await mockSetSnapshot(snapshot);
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto("/");

    await expect(page.locator(".node")).toHaveCount(5);
    await expect(page.locator(".edge-label")).toHaveCount(1);
    const isolatedTracks = await page
      .locator('.node[data-task-id="TASK-GAMMA"], .node[data-task-id="TASK-DELTA"], .node[data-task-id="TASK-EPSILON"]')
      .evaluateAll((nodes) => ({
        columns: new Set(nodes.map((node) => Math.round(node.getBoundingClientRect().x))).size,
        rows: new Set(nodes.map((node) => Math.round(node.getBoundingClientRect().y))).size,
      }));
    expect(isolatedTracks.columns).toBeGreaterThan(1);
    expect(isolatedTracks.rows).toBeGreaterThan(1);
    await expectNoRelationshipLabelOcclusion(page, "1024x768 mixed graph");
  });

  for (const { width, height } of VIEWPORTS) {
    test(`layout and interactions hold at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await openGraph(page);

      // No horizontal overflow; graph stays the primary visual at every width.
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
      const svgBox = (await page.locator(".graph-svg").boundingBox())!;
      expect(svgBox.width).toBeGreaterThan(width * 0.4);
      await expect(page.locator(".detail-panel")).toBeVisible();
      await expect(page.locator(".status-bar")).toBeVisible();

      // Interaction still works at this width.
      await page.locator('.node[data-task-id="TASK-ALPHA"]').click();
      await expect(page.locator(".detail-title")).toContainText("TASK-ALPHA");
      await page.getByRole("button", { name: "放大" }).click();
      await page.getByRole("button", { name: "适配视图（显示完整网络）" }).click();

      // Occlusion oracle: the legend strip must never intersect any visible
      // node, edge label or assessment label at the target widths.
      const legendBox = (await page.locator(".graph-legend").boundingBox())!;
      expect(legendBox).not.toBeNull();
      const drawn = page.locator(".node, .edge-label, .assessment-label");
      const drawnCount = await drawn.count();
      expect(drawnCount).toBeGreaterThan(0);
      for (let i = 0; i < drawnCount; i += 1) {
        const box = await drawn.nth(i).boundingBox();
        if (!box) {
          continue; // not visible at the current viewport
        }
        expect(
          intersects(legendBox, box),
          `legend overlaps drawn element #${i} at ${width}px`,
        ).toBe(false);
      }
      await expectNoRelationshipLabelOcclusion(page, `${width}x${height}`);
      await shot(page, `responsive/width-${width}`);
    });
  }

  for (const { width, height } of VIEWPORTS) {
    test(`diagnostics drawer stays a bottom footer in the stale scenario at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto("/?fixture=stale");
      await expect(page.locator(".diag-drawer-toggle")).toBeVisible();

      const drawer = (await page.locator(".diag-drawer").boundingBox())!;
      const statusBar = (await page.locator(".status-bar").boundingBox())!;
      const strip = (await page.locator(".stale-strip-stale").boundingBox())!;

      // Full-width footer anchored at the bottom of the viewport.
      expect(Math.abs(drawer.y + drawer.height - height)).toBeLessThanOrEqual(2);
      expect(drawer.x).toBeLessThanOrEqual(1);
      expect(Math.abs(drawer.width - width)).toBeLessThanOrEqual(2);
      // Never overlaps the global status bar or the stale strip.
      expect(intersects(drawer, statusBar), `drawer overlaps status bar at ${width}px`).toBe(false);
      expect(intersects(drawer, strip), `drawer overlaps stale strip at ${width}px`).toBe(false);
      // The stale strip itself stays clear of the status bar.
      expect(intersects(strip, statusBar), `stale strip overlaps status bar at ${width}px`).toBe(false);
      await shot(page, `responsive/drawer-${width}-stale`);

      // Expanded list stays inside the viewport and below the status bar.
      await page.locator(".diag-drawer-toggle").click();
      const expanded = (await page.locator(".diag-drawer").boundingBox())!;
      expect(expanded.y).toBeGreaterThanOrEqual(statusBar.y + statusBar.height - 1);
      expect(expanded.y + expanded.height).toBeLessThanOrEqual(height + 1);
      await shot(page, `responsive/drawer-${width}-stale-open`);
    });
  }
});

test.describe("frozen UA4 viewports", () => {
  // The two desktop widths frozen by the UA4-001-P1-002 closure contract.
  for (const { width, height } of [
    { width: 1440, height: 900 },
    { width: 1024, height: 768 },
  ]) {
    test(`no overflow and no legend occlusion at ${width}x${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await openGraph(page);

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
      const svgBox = (await page.locator(".graph-svg").boundingBox())!;
      expect(svgBox.width).toBeGreaterThan(width * 0.4);
      expect(svgBox.height).toBeGreaterThan(height * 0.4);
      await expect(page.locator(".detail-panel")).toBeVisible();
      await expect(page.locator(".status-bar")).toBeVisible();

      // Occlusion oracle identical to the regression widths above.
      const legendBox = (await page.locator(".graph-legend").boundingBox())!;
      expect(legendBox).not.toBeNull();
      const drawn = page.locator(".node, .edge-label, .assessment-label");
      const drawnCount = await drawn.count();
      expect(drawnCount).toBeGreaterThan(0);
      for (let i = 0; i < drawnCount; i += 1) {
        const box = await drawn.nth(i).boundingBox();
        if (!box) {
          continue;
        }
        expect(intersects(legendBox, box), `legend overlaps drawn element #${i} at ${width}px`).toBe(false);
      }
      await expectNoRelationshipLabelOcclusion(page, `${width}x${height}`);
      await shot(page, `responsive/width-${width}x${height}`);
    });
  }

  test("390x844 stacks vertically without horizontal scroll and keeps a non-empty canvas", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openGraph(page);

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);

    // The graph stays the primary visual: a tall, non-empty canvas with the
    // five fitted nodes actually inside the viewport.
    const svgBox = (await page.locator(".graph-svg").boundingBox())!;
    expect(svgBox.width).toBeGreaterThan(390 * 0.9);
    expect(svgBox.height).toBeGreaterThan(300);
    const nodes = page.locator(".node");
    await expect(nodes).toHaveCount(5);
    const nodeBox = (await nodes.first().boundingBox())!;
    expect(nodeBox).not.toBeNull();
    expect(nodeBox.y + nodeBox.height).toBeGreaterThan(0);
    expect(nodeBox.y).toBeLessThan(844);
    await expectNoRelationshipLabelOcclusion(page, "390x844");

    // Detail panel stacks below the graph instead of squeezing it sideways.
    await expect(page.locator(".detail-panel")).toBeVisible();
    const detailBox = (await page.locator(".detail-panel").boundingBox())!;
    expect(detailBox.width).toBeLessThanOrEqual(390 + 1);
    await shot(page, "responsive/width-390x844");
  });
});

test.describe("accessibility", () => {
  test("keyboard focus is always visible", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openGraph(page);

    const seen: string[] = [];
    for (let i = 0; i < 14; i += 1) {
      await page.keyboard.press("Tab");
      const info = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        if (!el) {
          return null;
        }
        const style = getComputedStyle(el);
        return {
          tag: el.tagName,
          cls: el.getAttribute("class") ?? "",
          outlineStyle: style.outlineStyle,
          outlineWidth: style.outlineWidth,
        };
      });
      if (!info) {
        continue;
      }
      seen.push(`${info.tag}.${info.cls}`);
      expect(
        info.outlineStyle !== "none" && info.outlineWidth !== "0px",
        `focused element ${info.tag}.${info.cls} must show a visible focus ring`,
      ).toBe(true);
    }
    expect(seen.length).toBeGreaterThan(3);
    await shot(page, "a11y/focus-visible");
  });

  test("core text meets basic contrast requirements", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openGraph(page);

    const ratios = await page.evaluate(() => {
      const channel = (value: number): number => {
        const c = value / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      };
      const luminance = (css: string): number => {
        const match = css.match(/rgba?\(([^)]+)\)/);
        if (!match || !match[1]) {
          throw new Error(`not a colour: ${css}`);
        }
        const parts = match[1].split(",").map((part) => Number.parseFloat(part));
        const [r = 0, g = 0, b = 0] = parts;
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
      };
      const ratio = (fg: string, bg: string): number => {
        const l1 = luminance(fg);
        const l2 = luminance(bg);
        const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
        return (hi + 0.05) / (lo + 0.05);
      };
      const status = getComputedStyle(document.querySelector(".status-bar")!);
      const nodeId = document.querySelector(".node .node-id")!;
      const nodeFrame = document.querySelector(".node .node-frame")!;
        const legend = getComputedStyle(document.querySelector(".graph-legend")!);
      return {
        statusText: ratio(status.color, status.backgroundColor),
        nodeId: ratio(getComputedStyle(nodeId).fill, getComputedStyle(nodeFrame).fill),
        legendText: ratio(legend.color, legend.backgroundColor),
      };
    });
    expect(ratios.statusText).toBeGreaterThanOrEqual(4.5);
    expect(ratios.nodeId).toBeGreaterThanOrEqual(4.5);
    expect(ratios.legendText).toBeGreaterThanOrEqual(4.5);
  });

  test("faint text and key strokes meet WCAG AA in both dark and light themes", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    for (const scheme of ["dark", "light"] as const) {
      await page.emulateMedia({ colorScheme: scheme });
      await openGraph(page);
      // Open a detail so every faint-text element below is actually rendered.
      await page.locator('.node[data-task-id="TASK-ALPHA"]').click();
      await expect(page.locator(".detail-disclaimer")).toBeVisible();

      const ratios = await page.evaluate(() => {
        const channel = (value: number): number => {
          const c = value / 255;
          return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        };
        const luminance = (css: string): number => {
          const match = css.match(/rgba?\(([^)]+)\)/);
          if (!match || !match[1]) {
            throw new Error(`not a colour: ${css}`);
          }
          const parts = match[1].split(",").map((part) => Number.parseFloat(part));
          const [r = 0, g = 0, b = 0] = parts;
          return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
        };
        const ratio = (fg: string, bg: string): number => {
          const l1 = luminance(fg);
          const l2 = luminance(bg);
          const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
          return (hi + 0.05) / (lo + 0.05);
        };
        // Effective background: first ancestor with a non-transparent fill.
        const climbBg = (el: Element): string => {
          let node: Element | null = el;
          while (node) {
            const bg = getComputedStyle(node).backgroundColor;
            if (bg && bg !== "transparent" && !bg.startsWith("rgba(0, 0, 0, 0)")) {
              return bg;
            }
            node = node.parentElement;
          }
          throw new Error("no background found");
        };
        const out: Record<string, number> = {};
        // Every small-text usage of --faint that this snapshot renders:
        // legend note, pair reasons and the detail disclaimer.
        for (const [key, selector] of [
          ["legend-note", ".legend-note"],
          ["pair-reasons", ".pair-reasons"],
          ["detail-disclaimer", ".detail-disclaimer"],
        ] as const) {
          const el = document.querySelector(selector);
          if (!el) {
            throw new Error(`missing element ${selector}`);
          }
          out[key] = ratio(getComputedStyle(el).color, climbBg(el));
        }
        // --faint inside the graph: node class label on the node frame.
        const nodeClass = document.querySelector(".node .node-class");
        const nodeFrame = document.querySelector(".node .node-frame");
        if (!nodeClass || !nodeFrame) {
          throw new Error("missing node class/frame");
        }
        out["node-class"] = ratio(getComputedStyle(nodeClass).fill, getComputedStyle(nodeFrame).fill);
        // Key non-text strokes on the graph background.
        const graphBg = climbBg(document.querySelector(".graph-svg")!);
        const edge = document.querySelector(".edge-depends_on .edge-line");
        const assessment = document.querySelector(".assessment-candidate .assessment-line");
        if (!edge || !assessment) {
          throw new Error("missing edge/assessment line");
        }
        out["edge-line"] = ratio(getComputedStyle(edge).stroke, graphBg);
        out["assessment-line"] = ratio(getComputedStyle(assessment).stroke, graphBg);
        return out;
      });

      for (const [key, value] of Object.entries(ratios)) {
        const min = key.endsWith("line") ? 3 : 4.5;
        expect(value, `${scheme} theme: ${key} contrast ${value.toFixed(2)} must be >= ${min}`).toBeGreaterThanOrEqual(min);
      }
    }
  });

  test("prefers-reduced-motion disables transitions and animates nothing", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openGraph(page);

    // CSS transitions are forced off.
    const transition = await page.evaluate(() => getComputedStyle(document.querySelector(".node")!).transitionDuration);
    expect(transition).toBe("0s");

    // Fit is applied synchronously instead of via a 220ms animation.
    const fitted = await page.locator(".graph-viewport").getAttribute("transform");
    await page.getByRole("button", { name: "放大" }).click();
    const zoomed = await page.locator(".graph-viewport").getAttribute("transform");
    expect(zoomed).not.toBe(fitted);
    await page.getByRole("button", { name: "适配视图（显示完整网络）" }).click();
    const refit = await page.locator(".graph-viewport").getAttribute("transform");
    expect(refit).toBe(fitted);
    await shot(page, "a11y/reduced-motion");
  });
});
