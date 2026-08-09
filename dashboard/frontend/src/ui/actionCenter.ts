import type { AppState, AppStore } from "../state/store";
import { deriveOverview, type WaitingItem } from "../state/overview";
import { clear, el } from "./dom";
import {
  ACTION_KIND_LABEL,
  ACTION_REASON_LABEL,
  ELIGIBILITY_LABEL,
  LIFECYCLE_LABEL,
  PARALLEL_REASON_LABEL,
  label,
} from "./labels";

export class ActionCenter {
  readonly root = el("section", "action-center");

  constructor(private readonly store: AppStore) {
    this.root.setAttribute("aria-label", "任务执行总览");
  }

  update(state: AppState): void {
    this.root.hidden = state.viewMode !== "legacy";
    if (this.root.hidden) {
      return;
    }
    const focusedControl =
      document.activeElement instanceof HTMLElement && this.root.contains(document.activeElement)
        ? document.activeElement
        : null;
    const focusedKey = focusedControl?.dataset.overviewFocusKey ?? null;
    const focusedTaskId = focusedControl?.dataset.overviewTaskId ?? null;
    clear(this.root);
    if (!state.snapshot || !state.derived) {
      this.root.append(el("p", "overview-empty", state.phase === "error" ? "执行总览暂不可用。" : "正在加载执行总览…"));
      return;
    }

    const overview = deriveOverview(state.snapshot, state.derived);
    const primaryGrid = el("div", "overview-primary-grid");
    primaryGrid.append(this.renderCurrent(state, overview.current), this.renderParallel(overview.parallelSuggestions));

    const secondaryGrid = el("div", "overview-secondary-grid");
    const active = this.section("同时进行", overview.activeTasks.length, "active");
    if (overview.activeTasks.length === 0) {
      active.append(el("p", "overview-empty", "暂无明确处于“进行中”的其他任务。"));
    } else {
      const list = el("ul", "overview-list");
      for (const item of overview.activeTasks) {
        const next = item.action ? ACTION_KIND_LABEL[item.action.action_kind] ?? item.action.action_kind : "未给出动作";
        list.append(
          this.taskRow(
            item.task.task_id,
            item.task.title,
            `状态：${label(LIFECYCLE_LABEL, item.task.lifecycle)} · 下一步：${next}`,
            "进行中",
            "active",
          ),
        );
      }
      active.append(list);
    }

    const waiting = this.section("等待与串行", overview.waiting.length, "waiting");
    if (overview.waiting.length === 0) {
      waiting.append(el("p", "overview-empty", "暂无明确阻塞或必须串行关系。"));
    } else {
      const list = el("ul", "overview-list");
      for (const item of overview.waiting) {
        list.append(this.renderWaiting(item));
      }
      waiting.append(list);
    }
    secondaryGrid.append(active, waiting);

    const footer = el("button", "overview-footer");
    footer.type = "button";
    footer.dataset.overviewFocusKey = "full-network";
    footer.textContent = `其他 ${overview.hiddenTaskCount} 个任务 · 诊断 ${overview.diagnosticCount} · 查看全部`;
    footer.addEventListener("click", () => this.store.showFullNetwork());

    const focusAnnouncement = el("span", "visually-hidden");
    focusAnnouncement.setAttribute("aria-live", "polite");
    this.root.append(primaryGrid, secondaryGrid, footer, focusAnnouncement);
    this.restoreFocus(focusedKey, focusedTaskId, focusAnnouncement);
  }

  private renderCurrent(state: AppState, current: ReturnType<typeof deriveOverview>["current"]): HTMLElement {
    const card = el("article", "current-action");
    card.append(el("h1", "overview-heading", "当前行动"));
    if (!current) {
      card.append(
        el("p", "overview-empty overview-empty-prominent", "当前快照没有可展示的下一动作。可进入完整关系图检查全部任务与诊断。"),
      );
      return card;
    }
    const identity = el("div", "current-identity");
    identity.append(el("span", "overview-dot current-dot", "当前"), el("code", "current-task-id", current.task.task_id));
    card.append(identity, el("p", "current-title", current.task.title));

    const status = el("p", "current-status");
    status.append(
      el("span", "overview-key", "状态"),
      el(
        "span",
        `overview-badge eligibility-${current.action.eligibility}`,
        `${ACTION_KIND_LABEL[current.action.action_kind] ?? current.action.action_kind} · ${ELIGIBILITY_LABEL[current.action.eligibility] ?? current.action.eligibility}`,
      ),
    );
    card.append(status);

    const reasons = current.action.reason_codes.map((reason) => ACTION_REASON_LABEL[reason] ?? reason);
    card.append(el("p", "current-reason", `原因：${reasons.length > 0 ? reasons.join("、") : "快照未提供补充原因"}`));

    const button = el(
      "button",
      "current-action-button",
      current.action.action_kind === "user_decision" ? "查看并决定" : "查看任务路线",
    );
    button.type = "button";
    button.dataset.overviewFocusKey = `current:${current.task.task_id}`;
    button.dataset.overviewTaskId = current.task.task_id;
    button.addEventListener("click", () => this.store.openTaskRoute(current.task.task_id));
    card.append(button);

    const meta = el("div", "current-meta");
    meta.append(
      this.metaLine("下一步", ACTION_KIND_LABEL[current.action.action_kind] ?? current.action.action_kind),
      this.metaLine(
        "相关下游",
        [...(state.derived?.downstream.get(current.task.task_id) ?? [])].slice(0, 2).join("、") || "暂无明确下游",
      ),
    );
    card.append(meta);
    return card;
  }

  private renderParallel(suggestions: ReturnType<typeof deriveOverview>["parallelSuggestions"]): HTMLElement {
    const panel = this.section("并行建议", suggestions.length, "parallel");
    panel.append(el("p", "section-note", "候选 ≠ 已授权；未知证据保持待确认。"));
    if (suggestions.length === 0) {
      panel.append(
        el("p", "overview-empty", "暂无通过现有证据确认的并行候选。待确认项目不会自动转成建议。"),
      );
      return panel;
    }
    const list = el("ul", "overview-list");
    for (const suggestion of suggestions) {
      const item = el("li", "overview-item parallel-item");
      const head = el("div", "overview-item-head");
      head.append(el("code", "overview-task-id", suggestion.task.task_id), el("span", "overview-badge candidate", "可并行候选"));
      const title = el("p", "overview-item-title", suggestion.task.title);
      const reasons = suggestion.assessment.reason_codes.map((reason) => PARALLEL_REASON_LABEL[reason] ?? reason);
      const basis = el(
        "p",
        "overview-item-meta",
        `可与 ${suggestion.counterpart.task_id} 并行 · 依据：${reasons.join("、") || "候选评估"}`,
      );
      const button = el("button", "overview-link", "查看依据");
      button.type = "button";
      button.dataset.overviewFocusKey = `parallel:${suggestion.task.task_id}`;
      button.dataset.overviewTaskId = suggestion.task.task_id;
      button.addEventListener("click", () => {
        this.store.openTaskRoute(suggestion.task.task_id);
        this.store.setHighlight("candidates");
      });
      item.append(head, title, basis, button);
      list.append(item);
    }
    panel.append(list);
    return panel;
  }

  private renderWaiting(item: WaitingItem): HTMLElement {
    if (item.kind === "action_blocked") {
      const reasons = item.action?.reason_codes.map((reason) => ACTION_REASON_LABEL[reason] ?? reason).join("、");
      return this.taskRow(
        item.task.task_id,
        item.task.title,
        `动作受阻 · 原因：${reasons || "快照未提供补充原因"}`,
        "动作受阻",
        "waiting",
      );
    }
    const counterpart = item.counterpart?.task_id;
    const meta =
      item.kind === "blocked"
        ? `被 ${counterpart} 阻塞`
        : `必须与 ${counterpart} 串行 · ${item.assessment?.reason_codes.map((reason) => PARALLEL_REASON_LABEL[reason] ?? reason).join("、") || "存在串行证据"}`;
    return this.taskRow(item.task.task_id, item.task.title, meta, item.kind === "blocked" ? "等待中" : "必须串行", "waiting");
  }

  private section(title: string, count: number, tone: string): HTMLElement {
    const section = el("section", `overview-section overview-${tone}`);
    section.append(el("h2", "overview-section-title", `${title}（${count}）`));
    return section;
  }

  private taskRow(taskId: string, title: string, meta: string, badge: string, tone: string): HTMLLIElement {
    const item = el("li", `overview-item ${tone}-item`);
    const button = el("button", "overview-row-button");
    button.type = "button";
    button.dataset.overviewFocusKey = `row:${tone}:${taskId}`;
    button.dataset.overviewTaskId = taskId;
    const head = el("span", "overview-item-head");
    head.append(el("code", "overview-task-id", taskId), el("span", `overview-badge ${tone}`, badge));
    button.append(head, el("span", "overview-item-title", title), el("span", "overview-item-meta", meta));
    button.addEventListener("click", () => this.store.openTaskRoute(taskId));
    item.append(button);
    return item;
  }

  private restoreFocus(focusedKey: string | null, focusedTaskId: string | null, announcement: HTMLElement): void {
    if (!focusedKey) {
      return;
    }
    const controls = [...this.root.querySelectorAll<HTMLElement>("[data-overview-focus-key]")];
    const exact = controls.find((control) => control.dataset.overviewFocusKey === focusedKey);
    const sameTask = focusedTaskId
      ? controls.find((control) => control.dataset.overviewTaskId === focusedTaskId)
      : undefined;
    const target = exact ?? sameTask ?? controls[0];
    target?.focus({ preventScroll: true });
    if (!exact && !sameTask && target) {
      announcement.textContent = "任务总览已更新，原操作已不可用，焦点已移动到当前可用操作。";
    }
  }

  private metaLine(key: string, value: string): HTMLElement {
    const line = el("p", "current-meta-line");
    line.append(el("span", "overview-key", key), el("span", null, value));
    return line;
  }
}
