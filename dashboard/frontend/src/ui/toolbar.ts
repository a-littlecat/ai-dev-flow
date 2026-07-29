/**
 * Filter / highlight toolbar. Quick entries (next action / parallel
 * candidates / decisions) highlight on the graph; the filter panel narrows
 * visible nodes by lifecycle, action kind, risk, class, module, worktree,
 * edge type and diagnostic severity.
 */
import type { AppState, AppStore } from "../state/store";
import { filterTasks, filtersActive, highlightCounts, type FilterState, type HighlightMode } from "../state/derive";
import { el, clear } from "./dom";
import {
  ACTION_KIND_LABEL,
  EDGE_TYPE_LABEL,
  LIFECYCLE_LABEL,
  PARALLEL_REASON_LABEL,
  PARALLEL_RESULT_LABEL,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from "./labels";

const HIGHLIGHT_ENTRIES: { mode: Exclude<HighlightMode, "none">; text: string; hint: string }[] = [
  { mode: "actionable", text: "下一动作", hint: "高亮当前可执行动作的节点" },
  { mode: "candidates", text: "并行候选", hint: "高亮并行候选 pair（候选不代表已授权）" },
  { mode: "decisions", text: "需要决定", hint: "高亮等待用户决定的节点" },
];

const PAIR_DISCLOSURE_THRESHOLD = 12;

export class Toolbar {
  readonly root: HTMLElement;
  private chipsRow: HTMLElement;
  private readonly search: HTMLInputElement;
  private filterPanel: HTMLElement;
  private filterToggle: HTMLButtonElement;
  private pairList: HTMLElement;
  private expanded = false;
  /** null preserves the compact-list default; a user toggle overrides it. */
  private pairExpanded: boolean | null = null;
  /** Structure key of the rendered filter panel; inputs persist across updates. */
  private filterStructureKey: string | null = null;
  private filterInputs = new Map<string, { input: HTMLInputElement; key: keyof FilterState; option: string }>();

  constructor(private readonly store: AppStore) {
    this.root = el("div", "toolbar");
    this.chipsRow = el("div", "toolbar-chips");
    this.filterPanel = el("div", "filter-panel");
    this.filterPanel.hidden = true;
    this.pairList = el("div", "pair-list");
    this.filterToggle = el("button", "toolbar-filter-toggle", "筛选 ▾");
    this.filterToggle.type = "button";
    this.filterToggle.setAttribute("aria-expanded", "false");
    this.filterToggle.addEventListener("click", () => {
      this.expanded = !this.expanded;
      this.filterPanel.hidden = !this.expanded;
      this.filterToggle.setAttribute("aria-expanded", String(this.expanded));
      this.filterToggle.textContent = this.expanded ? "筛选 ▴" : "筛选 ▾";
      // Re-render immediately: the panel content only rebuilds in update().
      this.update(this.store.get());
    });
    // The search input is created once and never rebuilt: keystroke-by-
    // keystroke typing keeps focus, caret and selection across updates.
    this.search = el("input", "toolbar-search") as HTMLInputElement;
    this.search.type = "search";
    this.search.placeholder = "搜索任务 ID / 标题…";
    this.search.setAttribute("aria-label", "搜索任务 ID 或标题");
    this.search.addEventListener("input", () => this.store.patchFilters({ text: this.search.value }));
    this.chipsRow.append(this.search);
    this.root.append(this.chipsRow, this.filterToggle, this.filterPanel, this.pairList);
  }

  update(state: AppState): void {
    // Remove transient chips but keep the persistent search input in place.
    for (const child of [...this.chipsRow.children]) {
      if (child !== this.search) {
        child.remove();
      }
    }
    // Sync the value only on external changes (e.g. 清除筛选); while the
    // user types, value and filter state are already identical.
    if (this.search.value !== state.filters.text) {
      this.search.value = state.filters.text;
    }
    const snapshot = state.snapshot;
    const derived = state.derived;

    if (snapshot && derived) {
      // Search result count right beside the (persistent) search input: a
      // non-empty search always produces an explicit, screen-reader-visible
      // outcome — the size of the combined result set (structure AND text,
      // the exact set the graph highlights) or an explicit no-result message.
      const searchText = state.filters.text.trim();
      if (searchText !== "") {
        const matched = filterTasks(snapshot, derived, state.filters).size;
        const status = el(
          "span",
          `search-status${matched === 0 ? " search-status-empty" : ""}`,
          matched === 0 ? "无匹配结果" : `匹配 ${matched} / 共 ${snapshot.tasks.length} 个任务`,
        );
        status.setAttribute("role", "status");
        this.chipsRow.append(status);
      }

      const counts = highlightCounts(snapshot, derived);
      for (const entry of HIGHLIGHT_ENTRIES) {
        const chip = el(
          "button",
          `highlight-chip${state.highlight === entry.mode ? " highlight-chip-active" : ""}`,
          `${entry.text}（${counts[entry.mode]}）`,
        );
        chip.type = "button";
        chip.title = entry.hint;
        chip.setAttribute("aria-pressed", String(state.highlight === entry.mode));
        chip.addEventListener("click", () => this.store.setHighlight(entry.mode));
        this.chipsRow.append(chip);
      }
    }

    if (filtersActive(state.filters)) {
      const reset = el("button", "toolbar-reset", "清除筛选");
      reset.type = "button";
      reset.addEventListener("click", () => this.store.resetFilters());
      this.chipsRow.append(reset);
    }

    if (state.focus.mode !== "all" && state.focus.taskId) {
      const banner = el(
        "span",
        "focus-banner",
        `聚焦${state.focus.mode === "upstream" ? "上游" : "下游"}：${state.focus.taskId}（Esc 或“完整网络”恢复）`,
      );
      banner.setAttribute("role", "status");
      this.chipsRow.append(banner);
    }

    if (this.expanded && snapshot) {
      this.renderFilterPanel(state);
    } else if (this.filterStructureKey !== null) {
      clear(this.filterPanel);
      this.filterStructureKey = null;
      this.filterInputs.clear();
    }

    this.renderPairList(state);
  }

  private renderFilterPanel(state: AppState): void {
    const snapshot = state.snapshot!;
    const filters = state.filters;

    const lifecycles = [...new Set(snapshot.tasks.map((t) => t.lifecycle ?? "null"))];
    const actionKinds = [...new Set(snapshot.actions.map((a) => a.action_kind))];
    const riskFlags = [...new Set(snapshot.tasks.flatMap((t) => t.risk_flags))];
    const taskClasses = [...new Set(snapshot.tasks.map((t) => t.task_class ?? "null"))];
    const moduleLocks = [...new Set(snapshot.tasks.flatMap((t) => t.module_locks))];
    const worktreeRoots = [...new Set(snapshot.project.worktrees.map((w) => w.root))];
    const edgeTypes = [...new Set(snapshot.edges.map((e) => e.type))];

    const groups: { title: string; options: string[]; labelOf: (value: string) => string; key: keyof FilterState }[] = [
      { title: "生命周期", options: lifecycles, labelOf: (v) => LIFECYCLE_LABEL[v] ?? (v === "null" ? "未知" : v), key: "lifecycles" },
      { title: "动作类型", options: actionKinds, labelOf: (v) => ACTION_KIND_LABEL[v] ?? v, key: "actionKinds" },
      { title: "风险", options: riskFlags, labelOf: (v) => v, key: "riskFlags" },
      { title: "任务等级", options: taskClasses, labelOf: (v) => (v === "null" ? "未知" : `${v} 级`), key: "taskClasses" },
      { title: "模块锁", options: moduleLocks, labelOf: (v) => v, key: "moduleLocks" },
      { title: "Worktree", options: worktreeRoots, labelOf: (v) => v, key: "worktreeRoots" },
      { title: "关系类型", options: edgeTypes, labelOf: (v) => EDGE_TYPE_LABEL[v] ?? v, key: "edgeTypes" },
      {
        title: "诊断严重度",
        options: ["error", "violation", "warning", "info"],
        labelOf: (v) => `${SEVERITY_ICON[v] ?? ""} ${SEVERITY_LABEL[v] ?? v}`,
        key: "severities",
      },
    ];

    // Rebuild only when the option structure changes; otherwise update the
    // checked state in place so keyboard focus is never lost.
    const structureKey = JSON.stringify(groups.map((g) => [g.key, [...g.options].sort()]));
    if (structureKey !== this.filterStructureKey) {
      const activeId =
        document.activeElement instanceof HTMLElement && this.filterPanel.contains(document.activeElement)
          ? document.activeElement.id
          : null;
      clear(this.filterPanel);
      this.filterInputs.clear();
      for (const g of groups) {
        this.filterPanel.append(this.group(g.title, g.options, g.labelOf, g.key));
      }
      this.filterStructureKey = structureKey;
      if (activeId) {
        this.filterInputs.get(activeId)?.input.focus();
      }
    }
    for (const { input, key, option } of this.filterInputs.values()) {
      input.checked = ((filters[key] as string[]) ?? []).includes(option);
    }
  }

  private group(
    title: string,
    options: string[],
    labelOf: (value: string) => string,
    key: keyof FilterState,
  ): HTMLElement {
    const fieldset = el("fieldset", "filter-group");
    fieldset.append(el("legend", "filter-group-title", title));
    if (options.length === 0) {
      fieldset.append(el("span", "filter-empty", "（无）"));
      return fieldset;
    }
    for (const option of options.sort()) {
      const id = `filter-${key}-${option.replace(/[^A-Za-z0-9_-]+/g, "_")}`;
      const wrapper = el("label", "filter-option");
      wrapper.htmlFor = id;
      const input = el("input") as HTMLInputElement;
      input.type = "checkbox";
      input.id = id;
      input.checked = ((this.store.get().filters[key] as string[]) ?? []).includes(option);
      input.addEventListener("change", () => {
        const current = new Set((this.store.get().filters[key] as string[]) ?? []);
        if (input.checked) {
          current.add(option);
        } else {
          current.delete(option);
        }
        this.store.patchFilters({ [key]: [...current] } as Partial<FilterState>);
      });
      this.filterInputs.set(id, { input, key, option });
      wrapper.append(input, document.createTextNode(labelOf(option)));
      fieldset.append(wrapper);
    }
    return fieldset;
  }

  /** Parallel assessment list: candidate / must_serial / unknown with textual reasons. */
  private renderPairList(state: AppState): void {
    clear(this.pairList);
    const snapshot = state.snapshot;
    if (!snapshot || snapshot.parallel_assessments.length === 0) {
      return;
    }
    const counts = { candidate: 0, must_serial: 0, unknown: 0 };
    for (const assessment of snapshot.parallel_assessments) {
      counts[assessment.result] += 1;
    }
    const pairIsExpanded =
      this.pairExpanded ?? snapshot.parallel_assessments.length <= PAIR_DISCLOSURE_THRESHOLD;
    const header = el("div", "pair-list-header");
    const title = el("h3", "pair-list-title", "并行评估（候选 ≠ 授权，均需用户确认）");
    const toggle = el(
      "button",
      "pair-list-toggle",
      `共 ${snapshot.parallel_assessments.length}：候选 ${counts.candidate} / 必须串行 ${counts.must_serial} / 未知 ${counts.unknown}，候选不等于授权 ${pairIsExpanded ? "▴" : "▾"}`,
    );
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", String(pairIsExpanded));
    toggle.setAttribute("aria-controls", "parallel-assessment-list");
    toggle.addEventListener("click", () => {
      this.pairExpanded = !pairIsExpanded;
      this.renderPairList(this.store.get());
    });
    header.append(title, toggle);
    this.pairList.append(header);
    const list = el("ul", "pair-list-items");
    list.id = "parallel-assessment-list";
    list.hidden = !pairIsExpanded;
    for (const assessment of snapshot.parallel_assessments) {
      const item = el("li", `pair-item pair-${assessment.result}`);
      const button = el(
        "button",
        "pair-button",
        `${assessment.left_task_id} × ${assessment.right_task_id}：${PARALLEL_RESULT_LABEL[assessment.result] ?? assessment.result}`,
      );
      button.type = "button";
      button.addEventListener("click", () => {
        this.store.selectTask(assessment.left_task_id);
        if (assessment.result === "candidate") {
          this.store.setHighlight("candidates");
        }
      });
      item.append(button);
      if (assessment.reason_codes.length > 0) {
        item.append(
          el(
            "span",
            "pair-reasons",
            `原因：${assessment.reason_codes.map((code) => PARALLEL_REASON_LABEL[code] ?? code).join("、")}`,
          ),
        );
      }
      list.append(item);
    }
    this.pairList.append(list);
  }
}
