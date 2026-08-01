/**
 * SVG relationship graph — the primary visual of the dashboard.
 * Every state is expressed with text + line style + symbol; colour is only a
 * supplement. Supports zoom, pan, fit, locate, upstream/downstream focus,
 * full-network restore and full keyboard operation.
 */
import type { ParallelAssessment, RelationshipEdge, TaskNode } from "../../generated/contracts.types";
import type { DerivedData } from "../../state/derive";
import { filterTasks, focusClosure, highlightTasks } from "../../state/derive";
import type { AppState, AppStore, Viewport } from "../../state/store";
import { el, svgEl, svgText, clear } from "../dom";
import {
  ACTION_KIND_LABEL,
  CONDITION_EVAL_LABEL,
  EDGE_TYPE_LABEL,
  ELIGIBILITY_LABEL,
  FRESHNESS_LABEL,
  label,
  LIFECYCLE_LABEL,
  PARALLEL_RESULT_LABEL,
  PARALLEL_RESULT_SHORT,
  PARALLEL_REASON_LABEL,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from "../labels";
import { layoutGraph, NODE_HEIGHT, NODE_WIDTH, type GraphLayout, type LayoutNode } from "./layout";

const ZOOM_MIN = 0.15;
const ZOOM_MAX = 2.5;

const EDGE_DASH: Record<string, string | null> = {
  depends_on: null,
  parent: null,
  replaces: "9 4",
  discovered_from: "2 4",
  conflicts_with: "5 4",
};

export class GraphView {
  readonly root: HTMLElement;
  private svg: SVGSVGElement;
  private viewportGroup: SVGGElement;
  private edgeLayer: SVGGElement;
  private assessmentLayer: SVGGElement;
  private nodeLayer: SVGGElement;
  private legendNote: HTMLElement;
  private selectionControls: HTMLButtonElement[] = [];
  private fullNetworkControl: HTMLButtonElement | null = null;
  private layout: GraphLayout | null = null;
  private nodeElements = new Map<string, SVGGElement>();
  private relationshipLabelRects: LayoutRect[] = [];
  private renderedSnapshotRevision: string | null = null;
  private renderedLayoutExtent: string | null = null;
  private autoFitRequest = 0;
  private reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  private panState: { pointerId: number; startX: number; startY: number; origin: Viewport } | null = null;

  constructor(private readonly store: AppStore) {
    this.root = el("section", "graph-area");
    this.root.setAttribute("aria-label", "任务关系图区域");

    const controls = el("div", "graph-controls");
    controls.setAttribute("role", "toolbar");
    controls.setAttribute("aria-label", "关系图视图控制");
    const buttons: [string, string, () => void, "always" | "selection" | "focus"][] = [
      ["＋", "放大", () => this.zoomBy(1.25), "always"],
      ["－", "缩小", () => this.zoomBy(0.8), "always"],
      ["适配", "适配视图（显示完整网络）", () => this.fitToContent(), "always"],
      ["定位", "定位到当前选中节点", () => this.locateSelected(), "selection"],
      ["聚焦上游", "只高亮选中节点的上游链", () => this.focus("upstream"), "selection"],
      ["聚焦下游", "只高亮选中节点的下游链", () => this.focus("downstream"), "selection"],
      ["完整网络", "恢复完整网络视图", () => this.store.clearFocus(), "focus"],
    ];
    for (const [text, aria, handler, visibility] of buttons) {
      const button = el("button", "graph-control-btn", text);
      button.type = "button";
      button.setAttribute("aria-label", aria);
      button.title = aria;
      button.addEventListener("click", handler);
      if (visibility === "selection") {
        this.selectionControls.push(button);
      } else if (visibility === "focus") {
        this.fullNetworkControl = button;
      }
      controls.append(button);
    }

    this.svg = svgEl("svg", { class: "graph-svg", role: "group", tabindex: "0" });
    this.svg.setAttribute("aria-label", "任务关系图。使用方向键在节点间移动，回车打开详情，加号减号缩放，0 适配视图。");
    const defs = svgEl("defs");
    defs.append(...buildMarkers());
    this.viewportGroup = svgEl("g", { class: "graph-viewport" });
    this.edgeLayer = svgEl("g", { class: "edge-layer" });
    this.assessmentLayer = svgEl("g", { class: "assessment-layer" });
    this.nodeLayer = svgEl("g", { class: "node-layer" });
    this.viewportGroup.append(this.edgeLayer, this.assessmentLayer, this.nodeLayer);
    this.svg.append(defs, this.viewportGroup);

    const legend = buildLegend();
    this.legendNote = legend.querySelector<HTMLElement>(".legend-note")!;
    this.root.append(this.svg, controls, legend);
    this.bindPointer();
    this.bindKeyboard();
  }

  // ---- rendering -------------------------------------------------------

  update(state: AppState): void {
    for (const control of this.selectionControls) {
      control.hidden = state.selectedTaskId === null;
    }
    if (this.fullNetworkControl) {
      this.fullNetworkControl.hidden = state.focus.mode === "all";
    }
    const focusedTaskIdBeforeRender = this.focusedTaskId();
    clear(this.edgeLayer);
    clear(this.assessmentLayer);
    clear(this.nodeLayer);
    this.nodeElements.clear();
    this.relationshipLabelRects = [];
    const snapshot = state.snapshot;
    const derived = state.derived;
    if (!snapshot || !derived || snapshot.tasks.length === 0) {
      this.layout = null;
      this.renderedSnapshotRevision = null;
      this.renderedLayoutExtent = null;
      this.legendNote.textContent = "图中关系均带文字/符号；候选不代表已授权执行。";
      this.renderEmptyHint(snapshot !== null);
      this.applyViewport(state.viewport);
      return;
    }

    const taskIds = snapshot.tasks.map((task) => task.task_id);
    this.layout = layoutGraph(taskIds, snapshot.edges);

    const visible = filterTasks(snapshot, derived, state.filters);
    const highlighted =
      state.highlight !== "none" ? highlightTasks(snapshot, derived, state.highlight) : null;
    let focusSet: Set<string> | null = null;
    if (state.focus.mode !== "all" && state.focus.taskId) {
      if (state.focus.mode === "context") {
        focusSet = new Set([
          ...focusClosure(derived, state.focus.taskId, "upstream"),
          ...focusClosure(derived, state.focus.taskId, "downstream"),
        ]);
      } else {
        focusSet = focusClosure(derived, state.focus.taskId, state.focus.mode);
      }
    }
    const searchText = state.filters.text.trim();
    const searchMatched = searchText !== "" ? visible : null;
    // Search matches and an explicitly requested focus chain are both direct
    // user intent, so keep their union prominent. Structural filters still
    // win: clearing only the text term gives the maximum node set that focus
    // is allowed to reveal.
    const structurallyVisible =
      searchMatched !== null
        ? filterTasks(snapshot, derived, { ...state.filters, text: "" })
        : visible;
    const selectedTaskId = state.selectedTaskId;
    const dimmed = (taskId: string): boolean => {
      // Explicit selection is the strongest graph intent. Keeping the selected
      // node prominent prevents search/highlight/focus opacity from hiding the
      // very task whose detail is open.
      if (taskId === selectedTaskId) {
        return false;
      }
      return searchMatched !== null
        ? !structurallyVisible.has(taskId) ||
            (!searchMatched.has(taskId) && (focusSet === null || !focusSet.has(taskId)))
        : !visible.has(taskId) ||
            (highlighted !== null && !highlighted.has(taskId)) ||
            (focusSet !== null && !focusSet.has(taskId));
    };

    for (const edge of snapshot.edges) {
      // 关系类型筛选只隐藏不匹配的边，不改变节点可见性。
      if (state.filters.edgeTypes.length > 0 && !state.filters.edgeTypes.includes(edge.type)) {
        continue;
      }
      const selectedContext =
        selectedTaskId !== null &&
        (edge.source_task_id === selectedTaskId || edge.target_task_id === selectedTaskId);
      this.renderEdge(
        edge,
        selectedContext ? false : dimmed(edge.source_task_id) || dimmed(edge.target_task_id),
        selectedContext,
        selectedTaskId !== null && !selectedContext,
      );
    }
    let renderedAssessmentCount = 0;
    for (const assessment of snapshot.parallel_assessments) {
      // Unknown parallelism is evidence, not a structural graph relation.
      // Rendering every unknown pair produces N*(N-1)/2 arcs and labels that
      // obscure the task cards; the list and detail panel retain the evidence.
      if (assessment.result === "unknown") {
        continue;
      }
      const selectedContext =
        selectedTaskId !== null &&
        (assessment.left_task_id === selectedTaskId ||
          assessment.right_task_id === selectedTaskId);
      const candidateHighlight =
        state.highlight === "candidates" && assessment.result === "candidate";
      if (!selectedContext && !candidateHighlight) {
        continue;
      }
      const outsideFocus =
        focusSet !== null &&
        (!focusSet.has(assessment.left_task_id) || !focusSet.has(assessment.right_task_id));
      this.renderAssessment(
        assessment,
        selectedContext || candidateHighlight,
        outsideFocus,
      );
      renderedAssessmentCount += 1;
    }
    const hiddenAssessmentCount =
      snapshot.parallel_assessments.length - renderedAssessmentCount;
    const focusExplanation =
      focusSet !== null
        ? "聚焦仅沿正式上下游关系；链外并行评估线已淡化，不代表上下游。"
        : "";
    const assessmentExplanation =
      hiddenAssessmentCount > 0
        ? `关系图已收起 ${hiddenAssessmentCount} 条并行评估以避免遮挡；选择任务或点击“并行候选”查看候选 / 必须串行连线，“并行未知”仅在列表 / 详情中显示。`
        : "图中关系均带文字/符号。";
    this.legendNote.textContent = `${focusExplanation}${assessmentExplanation}候选不代表已授权执行。`;
    for (const task of snapshot.tasks) {
      const layoutNode = this.layout.nodes.get(task.task_id);
      if (!layoutNode) {
        continue;
      }
      this.renderNode(
        task,
        layoutNode,
        state,
        derived,
        dimmed(task.task_id),
        !visible.has(task.task_id),
        searchMatched?.has(task.task_id) ?? false,
      );
    }
    if (searchMatched !== null && searchMatched.size === 0) {
      this.renderSearchEmptyHint(searchText);
    }
    const layoutExtent = `${this.layout.width}:${this.layout.height}`;
    const shouldRefit =
      this.renderedSnapshotRevision === snapshot.revision &&
      this.renderedLayoutExtent !== null &&
      this.renderedLayoutExtent !== layoutExtent;
    this.renderedSnapshotRevision = snapshot.revision;
    this.renderedLayoutExtent = layoutExtent;
    this.applyViewport(state.viewport);
    if (shouldRefit) {
      this.scheduleContentFit(focusedTaskIdBeforeRender);
    }
  }

  private renderSearchEmptyHint(searchText: string): void {
    const cx = this.layout ? this.layout.width / 2 : 200;
    const cy = this.layout ? this.layout.height / 2 : 120;
    const text = svgText(
      { x: String(cx), y: String(cy), class: "graph-empty-text", "text-anchor": "middle" },
      `没有匹配「${searchText}」的任务`,
    );
    this.nodeLayer.append(text);
  }

  private renderEmptyHint(hasSnapshot: boolean): void {
    const text = svgText(
      { x: "40", y: "60", class: "graph-empty-text" },
      hasSnapshot ? "当前快照中没有任何任务。" : "正在等待快照数据…",
    );
    this.nodeLayer.append(text);
  }

  private renderNode(
    task: TaskNode,
    layoutNode: LayoutNode,
    state: AppState,
    derived: DerivedData,
    dimmedOut: boolean,
    filteredOut: boolean,
    searchMatch: boolean,
  ): void {
    const group = svgEl("g", {
      class: "node",
      transform: `translate(${layoutNode.x}, ${layoutNode.y})`,
      role: "button",
      tabindex: "-1",
    });
    group.dataset.taskId = task.task_id;
    const classes = ["node"];
    const selected = state.selectedTaskId === task.task_id;
    if (selected) {
      classes.push("node-selected");
    }
    if (searchMatch) {
      // Search matches are never dimmed, even when they sit outside the
      // active highlight/focus set — the search is the user's explicit intent.
      classes.push("node-match");
    } else if (dimmedOut) {
      classes.push("node-dimmed");
    }
    if (filteredOut) {
      classes.push("node-filtered");
    }
    classes.push(`freshness-${task.freshness}`);
    const worst = derived.worstSeverityByTask.get(task.task_id);
    if (worst) {
      classes.push(`has-${worst}`);
    }
    group.setAttribute("class", classes.join(" "));
    group.setAttribute("aria-pressed", String(selected));

    const action = derived.primaryActionByTask.get(task.task_id) ?? null;
    const diagnostics = derived.diagnosticsByTask.get(task.task_id) ?? [];
    const ariaParts = [
      `任务 ${task.task_id}，${task.title}`,
      `生命周期 ${label(LIFECYCLE_LABEL, task.lifecycle)}`,
      action ? `下一动作 ${label(ACTION_KIND_LABEL, action.action_kind)}，${label(ELIGIBILITY_LABEL, action.eligibility)}` : "无动作建议",
      diagnostics.length > 0 ? `诊断 ${diagnostics.length} 条` : "无诊断",
      task.freshness !== "fresh" ? FRESHNESS_LABEL[task.freshness] ?? task.freshness : "",
      searchMatch ? "搜索匹配" : "",
      selected ? "当前选中" : "",
    ].filter(Boolean);
    group.setAttribute("aria-label", ariaParts.join("；"));
    const title = svgEl("title");
    title.textContent = ariaParts.join("；");
    group.append(title);

    group.append(svgEl("rect", { class: "node-frame", width: String(NODE_WIDTH), height: String(NODE_HEIGHT), rx: "6" }));

    group.append(svgText({ x: "12", y: "20", class: "node-id" }, truncate(task.task_id, 26)));
    if (task.task_class) {
      group.append(svgText({ x: String(NODE_WIDTH - 12), y: "20", class: "node-class", "text-anchor": "end" }, `${task.task_class} 级`));
    }
    group.append(svgText({ x: "12", y: "38", class: "node-title" }, truncate(task.title, 22)));
    if (searchMatch) {
      // Non-colour match badge (symbol + text) on the otherwise-quiet action
      // row, so the match is also perceivable without colour perception.
      group.append(
        svgText(
          { x: String(NODE_WIDTH - 12), y: "74", class: "node-match-tag", "text-anchor": "end" },
          "◈ 搜索匹配",
        ),
      );
    }

    const lifecycleText = label(LIFECYCLE_LABEL, task.lifecycle);
    const freshnessTag = task.freshness === "fresh" ? "" : ` ｜ ${FRESHNESS_LABEL[task.freshness] ?? task.freshness}`;
    group.append(svgText({ x: "12", y: "56", class: `node-lifecycle lc-${cssSafe(task.lifecycle)}` }, `状态：${lifecycleText}${freshnessTag}`));

    const actionText = action
      ? action.action_kind === "none"
        ? "下一步：无动作"
        : `下一步：${label(ACTION_KIND_LABEL, action.action_kind)} · ${label(ELIGIBILITY_LABEL, action.eligibility)}`
      : "下一步：无建议";
    group.append(svgText({ x: "12", y: "74", class: `node-action eligibility-${action?.eligibility ?? "none"}` }, actionText));
    if (selected) {
      group.append(svgText({ x: "12", y: "92", class: "node-selected-tag" }, "✓ 已选中"));
    }

    if (diagnostics.length > 0 && worst) {
      const badge = svgEl("g", { class: `node-diag-badge severity-${worst}` });
      badge.append(svgEl("rect", { x: String(NODE_WIDTH - 64), y: String(NODE_HEIGHT - 24), width: "56", height: "16", rx: "3" }));
      badge.append(
        svgText(
          { x: String(NODE_WIDTH - 36), y: String(NODE_HEIGHT - 12), class: "node-diag-text", "text-anchor": "middle" },
          `${SEVERITY_ICON[worst] ?? ""} ${SEVERITY_LABEL[worst] ?? worst}${diagnostics.length}`,
        ),
      );
      group.append(badge);
    }

    const assessments = derived.assessmentsByTask.get(task.task_id) ?? [];
    const candidate = assessments.some((item) => item.result === "candidate");
    if (candidate) {
      group.append(
        svgText({ x: String(NODE_WIDTH - 12), y: String(NODE_HEIGHT - 30), class: "node-candidate-tag", "text-anchor": "end" }, "并行候选·非授权"),
      );
    }

    group.addEventListener("click", () => this.store.selectTask(task.task_id));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        this.store.selectTask(task.task_id);
      }
    });
    this.nodeLayer.append(group);
    this.nodeElements.set(task.task_id, group);
  }

  private renderEdge(
    edge: RelationshipEdge,
    dimmedOut: boolean,
    selectedContext: boolean,
    selectionDimmed: boolean,
  ): void {
    if (!this.layout) {
      return;
    }
    const source = this.layout.nodes.get(edge.source_task_id);
    const target = this.layout.nodes.get(edge.target_task_id);
    if (!source || !target) {
      return;
    }
    // Display flow is target -> source for directional edges.
    const from = edge.type === "conflicts_with" ? source : target;
    const to = edge.type === "conflicts_with" ? target : source;
    const path = edgePath(from, to, edge.type === "conflicts_with");

    const classes = ["edge", `edge-${edge.type}`];
    if (dimmedOut) {
      classes.push("edge-dimmed");
    }
    if (selectedContext) {
      classes.push("edge-selected-context");
    } else if (selectionDimmed) {
      classes.push("edge-selection-dimmed");
    }
    if (this.layout.cycleEdgeIds.has(edge.edge_id)) {
      classes.push("edge-cycle");
    }
    if (edge.type === "depends_on" && edge.condition && edge.condition.evaluation !== "satisfied") {
      classes.push(`edge-condition-${edge.condition.evaluation}`);
    }
    const group = svgEl("g", { class: classes.join(" ") });
    const pathEl = svgEl("path", { d: path.d, class: "edge-line" });
    const dash = EDGE_DASH[edge.type];
    if (dash) {
      pathEl.setAttribute("stroke-dasharray", dash);
    }
    if (edge.directional) {
      pathEl.setAttribute("marker-end", `url(#arrow-${edge.type})`);
    }
    group.append(pathEl);

    const labelText = edgeLabelText(edge);
    const labelPlacement = placeGraphLabel(
      path,
      labelText,
      this.layout,
      this.relationshipLabelRects,
    );
    this.relationshipLabelRects.push(labelPlacement.rect);
    const labelNode = svgText(
      {
        x: String(labelPlacement.point.x),
        y: String(labelPlacement.point.y),
        class: "edge-label",
        "text-anchor": "middle",
      },
      labelText,
    );
    group.append(labelNode);
    const titleEl = svgEl("title");
    titleEl.textContent = edgeAriaText(edge);
    group.append(titleEl);
    this.edgeLayer.append(group);
  }

  private renderAssessment(
    assessment: ParallelAssessment,
    emphasize: boolean,
    outsideFocus: boolean,
  ): void {
    if (!this.layout) {
      return;
    }
    const left = this.layout.nodes.get(assessment.left_task_id);
    const right = this.layout.nodes.get(assessment.right_task_id);
    if (!left || !right) {
      return;
    }
    const classes = ["assessment-link", `assessment-${assessment.result}`];
    if (emphasize) {
      classes.push("assessment-emphasized");
    }
    if (outsideFocus) {
      classes.push("assessment-focus-dimmed");
    }
    const group = svgEl("g", { class: classes.join(" ") });
    const path = assessmentArc(left, right);
    const line = svgEl("path", { d: path.d, class: "assessment-line" });
    group.append(line);
    const resultText = PARALLEL_RESULT_SHORT[assessment.result] ?? assessment.result;
    const reasonCode = assessment.reason_codes[0];
    const labelText = reasonCode
      ? `${resultText}·${PARALLEL_REASON_LABEL[reasonCode] ?? reasonCode}`
      : resultText;
    const labelPlacement = placeGraphLabel(
      path,
      labelText,
      this.layout,
      this.relationshipLabelRects,
    );
    this.relationshipLabelRects.push(labelPlacement.rect);
    group.append(
      svgText(
        {
          x: String(labelPlacement.point.x),
          y: String(labelPlacement.point.y),
          class: "assessment-label",
          "text-anchor": "middle",
        },
        labelText,
      ),
    );
    const fullResultText = PARALLEL_RESULT_LABEL[assessment.result] ?? assessment.result;
    const titleEl = svgEl("title");
    titleEl.textContent = `${assessment.left_task_id} × ${assessment.right_task_id}：${fullResultText}；原因：${assessment.reason_codes.map((code) => PARALLEL_REASON_LABEL[code] ?? code).join("、") || "无"}；requires_user_confirmation=true`;
    group.append(titleEl);
    this.assessmentLayer.append(group);
  }

  // ---- viewport --------------------------------------------------------

  private applyViewport(viewport: Viewport): void {
    this.viewportGroup.setAttribute(
      "transform",
      `translate(${viewport.x}, ${viewport.y}) scale(${viewport.k})`,
    );
  }

  private focusedTaskId(): string | null {
    const activeElement = document.activeElement;
    return activeElement instanceof Element && this.nodeLayer.contains(activeElement)
      ? (activeElement.closest<SVGGElement>(".node")?.dataset.taskId ?? null)
      : null;
  }

  private scheduleContentFit(focusedTaskIdBeforeRender: string | null): void {
    const request = ++this.autoFitRequest;
    requestAnimationFrame(() => {
      if (request !== this.autoFitRequest) {
        return;
      }
      const currentFocusedTaskId = this.focusedTaskId();
      const focusedTaskId =
        currentFocusedTaskId ??
        (document.activeElement === document.body ? focusedTaskIdBeforeRender : null);
      this.fitToContent(false);
      if (focusedTaskId) {
        this.nodeElements.get(focusedTaskId)?.focus();
      }
    });
  }

  private zoomBy(factor: number, center?: { x: number; y: number }): void {
    const state = this.store.get();
    const rect = this.svg.getBoundingClientRect();
    const cx = center?.x ?? rect.width / 2;
    const cy = center?.y ?? rect.height / 2;
    const k = clamp(state.viewport.k * factor, ZOOM_MIN, ZOOM_MAX);
    const scale = k / state.viewport.k;
    const x = cx - (cx - state.viewport.x) * scale;
    const y = cy - (cy - state.viewport.y) * scale;
    this.store.setViewport({ x, y, k });
  }

  fitToContent(animate = true): void {
    if (!this.layout || this.layout.nodes.size === 0) {
      return;
    }
    const rect = this.svg.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
      return;
    }
    const pad = 48;
    const k = clamp(
      Math.min((rect.width - pad) / this.layout.width, (rect.height - pad) / this.layout.height, 1.4),
      ZOOM_MIN,
      ZOOM_MAX,
    );
    const target: Viewport = {
      k,
      x: (rect.width - this.layout.width * k) / 2,
      y: (rect.height - this.layout.height * k) / 2,
    };
    if (!animate || this.reduceMotion.matches) {
      this.store.setViewport(target);
      return;
    }
    this.animateViewport(target);
  }

  private animateViewport(target: Viewport): void {
    const start = this.store.get().viewport;
    const started = performance.now();
    const duration = 220;
    const step = (now: number) => {
      const t = Math.min(1, (now - started) / duration);
      const eased = 1 - (1 - t) * (1 - t);
      this.store.setViewport({
        x: start.x + (target.x - start.x) * eased,
        y: start.y + (target.y - start.y) * eased,
        k: start.k + (target.k - start.k) * eased,
      });
      if (t < 1) {
        requestAnimationFrame(step);
      }
    };
    requestAnimationFrame(step);
  }

  locateSelected(): void {
    const state = this.store.get();
    if (!state.selectedTaskId || !this.layout) {
      return;
    }
    const node = this.layout.nodes.get(state.selectedTaskId);
    if (!node) {
      return;
    }
    const rect = this.svg.getBoundingClientRect();
    const k = Math.max(state.viewport.k, 0.9);
    const target: Viewport = {
      k,
      x: rect.width / 2 - (node.x + NODE_WIDTH / 2) * k,
      y: rect.height / 2 - (node.y + NODE_HEIGHT / 2) * k,
    };
    if (this.reduceMotion.matches) {
      this.store.setViewport(target);
    } else {
      this.animateViewport(target);
    }
    this.focusNodeElement(state.selectedTaskId);
  }

  private focus(direction: "upstream" | "downstream"): void {
    const selected = this.store.get().selectedTaskId;
    if (selected) {
      this.store.setFocus(direction, selected);
    }
  }

  focusNodeElement(taskId: string): void {
    this.nodeElements.get(taskId)?.focus();
  }

  // ---- input -----------------------------------------------------------

  private bindPointer(): void {
    this.svg.addEventListener("wheel", (event) => {
      event.preventDefault();
      const rect = this.svg.getBoundingClientRect();
      this.zoomBy(event.deltaY < 0 ? 1.15 : 1 / 1.15, {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
    }, { passive: false });

    this.svg.addEventListener("pointerdown", (event) => {
      if ((event.target as Element).closest(".node")) {
        return; // node click handles selection
      }
      this.panState = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        origin: this.store.get().viewport,
      };
      this.svg.setPointerCapture(event.pointerId);
    });
    this.svg.addEventListener("pointermove", (event) => {
      if (!this.panState || this.panState.pointerId !== event.pointerId) {
        return;
      }
      const dx = event.clientX - this.panState.startX;
      const dy = event.clientY - this.panState.startY;
      this.store.setViewport({
        x: this.panState.origin.x + dx,
        y: this.panState.origin.y + dy,
        k: this.panState.origin.k,
      });
    });
    const endPan = (event: PointerEvent) => {
      if (this.panState?.pointerId === event.pointerId) {
        this.panState = null;
      }
    };
    this.svg.addEventListener("pointerup", endPan);
    this.svg.addEventListener("pointercancel", endPan);
  }

  private bindKeyboard(): void {
    this.svg.addEventListener("keydown", (event) => {
      const state = this.store.get();
      if (!this.layout || !state.snapshot) {
        return;
      }
      const key = event.key;
      if (key === "+" || key === "=") {
        event.preventDefault();
        this.zoomBy(1.25);
      } else if (key === "-") {
        event.preventDefault();
        this.zoomBy(0.8);
      } else if (key === "0") {
        event.preventDefault();
        this.fitToContent();
      } else if (key === "Escape") {
        event.preventDefault();
        if (state.focus.mode !== "all") {
          this.store.clearFocus();
        } else {
          this.store.selectTask(null);
        }
      } else if (key === "Enter" || key === " ") {
        if (state.selectedTaskId && state.detail.status === "idle") {
          event.preventDefault();
          this.store.selectTask(state.selectedTaskId);
        }
      } else if (key.startsWith("Arrow")) {
        event.preventDefault();
        this.moveSelection(key, state.selectedTaskId);
      }
    });
  }

  private moveSelection(key: string, currentId: string | null): void {
    if (!this.layout || this.layout.nodes.size === 0) {
      return;
    }
    const nodes = [...this.layout.nodes.values()];
    if (!currentId || !this.layout.nodes.has(currentId)) {
      const first = nodes.sort((a, b) => a.x - b.x || a.y - b.y)[0];
      if (first) {
        this.store.selectTask(first.taskId);
        this.focusNodeElement(first.taskId);
      }
      return;
    }
    const current = this.layout.nodes.get(currentId)!;
    const cx = current.x + NODE_WIDTH / 2;
    const cy = current.y + NODE_HEIGHT / 2;
    let best: LayoutNode | null = null;
    let bestScore = Number.POSITIVE_INFINITY;
    for (const candidate of nodes) {
      if (candidate.taskId === currentId) {
        continue;
      }
      const tx = candidate.x + NODE_WIDTH / 2;
      const ty = candidate.y + NODE_HEIGHT / 2;
      const dx = tx - cx;
      const dy = ty - cy;
      const directional =
        (key === "ArrowRight" && dx > 8) ||
        (key === "ArrowLeft" && dx < -8) ||
        (key === "ArrowDown" && dy > 8) ||
        (key === "ArrowUp" && dy < -8);
      if (!directional) {
        continue;
      }
      const primary = key === "ArrowRight" || key === "ArrowLeft" ? Math.abs(dx) : Math.abs(dy);
      const secondary = key === "ArrowRight" || key === "ArrowLeft" ? Math.abs(dy) : Math.abs(dx);
      const score = primary + secondary * 2.5;
      if (score < bestScore) {
        bestScore = score;
        best = candidate;
      }
    }
    if (best) {
      this.store.selectTask(best.taskId);
      this.focusNodeElement(best.taskId);
    }
  }
}

// ---- helpers ------------------------------------------------------------

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function cssSafe(value: string | null): string {
  return (value ?? "unknown").toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

interface EdgeGeometry {
  d: string;
  labelX: number;
  labelY: number;
}

interface Point {
  x: number;
  y: number;
}

interface LayoutRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

const EDGE_LABEL_HEIGHT = 14;
const EDGE_LABEL_NODE_CLEARANCE = 4;

/**
 * Keep relationship labels out of every task-card rectangle. Long edges can
 * cross an intermediate layer, so their geometric midpoint is not guaranteed
 * to be free even when both endpoint gaps are clear.
 */
function placeGraphLabel(
  path: EdgeGeometry,
  text: string,
  layout: GraphLayout,
  occupiedLabels: LayoutRect[],
): { point: Point; rect: LayoutRect } {
  const textWidth = [...text].reduce(
    (width, character) => width + ((character.codePointAt(0) ?? 0) <= 0xff ? 6.5 : 10.5),
    8,
  );
  const nodes: LayoutRect[] = [...layout.nodes.values()].map((node) => ({
    left: node.x - EDGE_LABEL_NODE_CLEARANCE,
    top: node.y - EDGE_LABEL_NODE_CLEARANCE,
    right: node.x + NODE_WIDTH + EDGE_LABEL_NODE_CLEARANCE,
    bottom: node.y + NODE_HEIGHT + EDGE_LABEL_NODE_CLEARANCE,
  }));
  const horizontalOffsets = symmetricOffsets(18, NODE_WIDTH);
  const verticalOffsets = symmetricOffsets(16, NODE_HEIGHT + EDGE_LABEL_HEIGHT);

  for (const verticalOffset of verticalOffsets) {
    for (const horizontalOffset of horizontalOffsets) {
      const candidate = {
        x: path.labelX + horizontalOffset,
        y: path.labelY + verticalOffset,
      };
      const candidateRect = graphLabelRect(candidate, textWidth);
      if (
        candidateRect.left < 0 ||
        candidateRect.top < 0 ||
        candidateRect.right > layout.width ||
        candidateRect.bottom > layout.height
      ) {
        continue;
      }
      if (
        !nodes.some((nodeRect) => rectsIntersect(candidateRect, nodeRect)) &&
        !occupiedLabels.some((labelRect) => rectsIntersect(candidateRect, labelRect))
      ) {
        return { point: candidate, rect: candidateRect };
      }
    }
  }

  // Dense or degenerate graphs (notably a one-node self-loop) can exhaust the
  // in-bounds search. Extend the layout with a checked overflow lane rather
  // than returning the original, known-unsafe midpoint.
  const horizontalPadding = EDGE_LABEL_NODE_CLEARANCE * 2;
  layout.width = Math.max(layout.width, textWidth + horizontalPadding);
  const minimumX = textWidth / 2 + EDGE_LABEL_NODE_CLEARANCE;
  const maximumX = layout.width - textWidth / 2 - EDGE_LABEL_NODE_CLEARANCE;
  const nodeBottom = nodes.reduce(
    (bottom, nodeRect) => Math.max(bottom, nodeRect.bottom),
    0,
  );
  const fallbackPoint = {
    x: clamp(path.labelX, minimumX, maximumX),
    y: nodeBottom + EDGE_LABEL_HEIGHT + 2,
  };
  let fallbackRect = graphLabelRect(fallbackPoint, textWidth);
  while (
    nodes.some((nodeRect) => rectsIntersect(fallbackRect, nodeRect)) ||
    occupiedLabels.some((labelRect) => rectsIntersect(fallbackRect, labelRect))
  ) {
    fallbackPoint.y += EDGE_LABEL_HEIGHT + EDGE_LABEL_NODE_CLEARANCE * 2;
    fallbackRect = graphLabelRect(fallbackPoint, textWidth);
  }
  layout.height = Math.max(
    layout.height,
    fallbackRect.bottom + EDGE_LABEL_NODE_CLEARANCE,
  );
  return { point: fallbackPoint, rect: fallbackRect };
}

function graphLabelRect(point: Point, textWidth: number): LayoutRect {
  return {
    left: point.x - textWidth / 2,
    top: point.y - EDGE_LABEL_HEIGHT - 2,
    right: point.x + textWidth / 2,
    bottom: point.y + 6,
  };
}

function symmetricOffsets(step: number, maximum: number): number[] {
  const offsets = [0];
  for (let offset = step; offset <= maximum; offset += step) {
    offsets.push(-offset, offset);
  }
  return offsets;
}

function rectsIntersect(a: LayoutRect, b: LayoutRect): boolean {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

function edgePath(from: LayoutNode, to: LayoutNode, arc: boolean): EdgeGeometry {
  const x1 = from.x + NODE_WIDTH;
  const y1 = from.y + NODE_HEIGHT / 2;
  const x2 = to.x;
  const y2 = to.y + NODE_HEIGHT / 2;
  if (arc) {
    const cx = (x1 + x2) / 2;
    const cy = Math.min(from.y, to.y) - 46;
    return { d: `M ${from.x + NODE_WIDTH / 2} ${from.y} Q ${cx} ${cy} ${to.x + NODE_WIDTH / 2} ${to.y}`, labelX: cx, labelY: cy + 12 };
  }
  if (x2 > x1 + 12) {
    const bend = Math.max(30, (x2 - x1) / 2);
    return {
      d: `M ${x1} ${y1} C ${x1 + bend} ${y1} ${x2 - bend} ${y2} ${x2} ${y2}`,
      labelX: (x1 + x2) / 2,
      labelY: (y1 + y2) / 2 - 6,
    };
  }
  // Backward / same-layer edge: route above the nodes.
  const sx = from.x + NODE_WIDTH / 2;
  const tx = to.x + NODE_WIDTH / 2;
  const top = Math.min(from.y, to.y) - 34;
  return {
    d: `M ${sx} ${from.y} C ${sx} ${top - 40} ${tx} ${top - 40} ${tx} ${to.y}`,
    labelX: (sx + tx) / 2,
    labelY: top - 22,
  };
}

function assessmentArc(left: LayoutNode, right: LayoutNode): EdgeGeometry {
  const x1 = left.x + NODE_WIDTH / 2;
  const y1 = left.y + NODE_HEIGHT;
  const x2 = right.x + NODE_WIDTH / 2;
  const y2 = right.y + NODE_HEIGHT;
  const cx = (x1 + x2) / 2;
  const cy = Math.max(y1, y2) + 60;
  return { d: `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`, labelX: cx, labelY: cy - 26 };
}

function edgeLabelText(edge: RelationshipEdge): string {
  const base = EDGE_TYPE_LABEL[edge.type] ?? edge.type;
  if (edge.type === "depends_on" && edge.condition) {
    const evalLabel = CONDITION_EVAL_LABEL[edge.condition.evaluation] ?? edge.condition.evaluation;
    return `${base}·${evalLabel}`;
  }
  return base;
}

function edgeAriaText(edge: RelationshipEdge): string {
  const base = `${edge.source_task_id} 与 ${edge.target_task_id}：${EDGE_TYPE_LABEL[edge.type] ?? edge.type}`;
  if (edge.type === "depends_on" && edge.condition) {
    return `${base}，条件 ${edge.condition.axis} 期望 ${edge.condition.expected} 实际 ${edge.condition.actual ?? "未知"}，${CONDITION_EVAL_LABEL[edge.condition.evaluation] ?? edge.condition.evaluation}`;
  }
  return base;
}

function buildMarkers(): SVGMarkerElement[] {
  const specs: [string, string][] = [
    ["arrow-depends_on", "marker-arrow"],
    ["arrow-parent", "marker-arrow marker-parent"],
    ["arrow-replaces", "marker-arrow marker-open"],
    ["arrow-discovered_from", "marker-arrow marker-open"],
  ];
  return specs.map(([id, cls]) => {
    const marker = svgEl("marker", {
      id,
      viewBox: "0 0 10 10",
      refX: "9",
      refY: "5",
      markerWidth: "7",
      markerHeight: "7",
      orient: "auto-start-reverse",
    });
    marker.append(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", class: cls }));
    return marker;
  });
}

function buildLegend(): HTMLElement {
  const legend = document.createElement("details");
  legend.className = "graph-legend";
  legend.setAttribute("aria-label", "图例");
  legend.append(el("summary", "legend-summary", "图例与说明"));
  const content = el("div", "legend-content");
  content.append(el("h3", "legend-title visually-hidden", "图例"));
  const items: [string, string][] = [
    ["— 依赖（实线箭头，标注条件满足状态）", "legend-line legend-depends"],
    ["— 父子（细实线箭头）", "legend-line legend-parent"],
    ["- - 替代（长虚线箭头）", "legend-line legend-replaces"],
    ["· · 派生（点线箭头）", "legend-line legend-discovered"],
    ["⋯ 冲突（点划线，无箭头）", "legend-line legend-conflict"],
    ["～ 并行评估连线（按选择显示候选 / 必须串行；未知见列表 / 详情）", "legend-line legend-assessment"],
  ];
  for (const [text, cls] of items) {
    content.append(el("div", cls, text));
  }
  content.append(el("div", "legend-note", "图中关系均带文字/符号；候选不代表已授权执行。"));
  legend.append(content);
  return legend;
}
