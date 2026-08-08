import type { ConsoleItem, ProjectConsole } from "../generated/contracts.types";
import type { AppState, AppStore } from "../state/store";
import { clear, el } from "./dom";

const PHASE_LABEL: Record<string, string> = {
  planning: "规划中",
  implementing: "实现中",
  validating: "验证中",
  reviewing: "审查中",
  repairing: "修复中",
  waiting_user: "等待用户",
  blocked: "阻塞",
  done: "已结束",
};

const SOURCE_LABEL: Record<string, string> = {
  task: "TASK",
  git: "Git",
  runtime: "Runtime",
};

export class ProjectConsoleView {
  readonly root = el("section", "project-console");
  private readonly announcement = el("span", "visually-hidden");

  constructor(private readonly store: AppStore) {
    this.root.setAttribute("aria-label", "Project Console 项目总览");
    this.announcement.setAttribute("aria-live", "polite");
  }

  update(state: AppState): void {
    this.root.hidden = state.viewMode !== "console";
    if (this.root.hidden) {
      return;
    }
    const active = document.activeElement instanceof HTMLElement && this.root.contains(document.activeElement)
      ? document.activeElement
      : null;
    const focusKey = active?.dataset.consoleFocusKey ?? null;
    const focusTask = active?.dataset.consoleTaskId ?? null;
    clear(this.root);
    const data = state.console.data;
    if (!data) {
      const empty = el("div", "console-state-panel");
      empty.append(
        el("p", "console-kicker", "PROJECT CONSOLE · 只读"),
        el("h1", "console-state-title", state.console.status === "error" ? "项目总览暂不可用" : "正在读取项目事实"),
        el("p", "console-state-copy", state.console.message ?? "正在等待 Snapshot 与 Console revision 对齐…"),
      );
      this.root.append(empty, this.announcement);
      return;
    }

    this.root.classList.toggle("console-data-stale", state.console.status === "stale");
    this.root.append(this.hero(state, data));
    if (state.console.message) {
      const warning = el("div", "console-stale-banner", state.console.message);
      warning.setAttribute("role", "alert");
      this.root.append(warning);
    }

    const content = el("div", "console-content");
    content.append(
      this.queueSection("需要你处理", "human", data.human_attention, state),
      this.queueSection("正在进行", "active", data.active_work, state),
      this.readySection(data, state),
      this.queueSection("阻塞与风险", "blocked", data.blocked, state),
      this.queueSection("状态过期", "stale", data.stale_sessions, state),
      this.recentSection(data),
    );
    this.root.append(content, this.announcement);
    this.restoreFocus(focusKey, focusTask);
  }

  private hero(state: AppState, data: ProjectConsole): HTMLElement {
    const hero = el("header", "console-hero");
    const identity = el("div", "console-identity");
    identity.append(
      el("p", "console-kicker", "PROJECT CONSOLE · 只读事实投影"),
      el("h1", "console-title", projectName(state.snapshot?.project.root ?? "当前项目")),
      el("p", "console-branch", `分支 ${state.snapshot?.project.branch ?? "未知"} · revision ${data.revision.slice(0, 10)}`),
    );
    const factState = el("span", `console-fact-state fact-state-${data.state}`, consoleStateLabel(data.state));
    factState.setAttribute("role", "status");
    identity.append(factState);
    const connection = el(
      "span",
      `console-connection connection-${state.connection}`,
      state.connection === "connected" ? "● 实时连接" : state.connection === "reconnecting" ? "● 正在重连" : "● 连接已断开",
    );
    connection.setAttribute("role", "status");
    identity.append(connection);

    const freshness = el("div", "console-freshness");
    freshness.setAttribute("aria-label", "数据来源与新鲜度");
    freshness.append(
      freshnessItem("任务事实", data.freshness.task_facts_at, "TASK 派生"),
      freshnessItem("Git", data.freshness.git_facts_at, "Git 派生"),
      freshnessItem("Agent", data.freshness.runtime_facts_at, "Runtime"),
    );

    const counts = el("dl", "console-counts");
    for (const [label, value, tone] of [
      ["需要你", data.counts.human_attention, "human"],
      ["正在进行", data.counts.active_work, "active"],
      ["可开始", data.counts.ready_queue, "ready"],
      ["阻塞", data.counts.blocked, "blocked"],
      ["状态过期", data.counts.stale_sessions, "stale"],
    ] as const) {
      const item = el("div", `console-count count-${tone}`);
      item.append(el("dt", null, label), el("dd", null, String(value)));
      counts.append(item);
    }
    hero.append(identity, freshness, counts);
    return hero;
  }

  private queueSection(title: string, tone: string, items: ConsoleItem[], state: AppState): HTMLElement {
    const section = el("section", `console-section console-section-${tone}`);
    const heading = el("div", "console-section-heading");
    heading.append(el("h2", null, title), el("span", "console-section-count", String(items.length)));
    section.append(heading);
    if (items.length === 0) {
      section.append(el("p", "console-empty", emptyText(tone)));
      return section;
    }
    const list = el("ol", "console-card-list");
    for (const [index, item] of items.entries()) {
      list.append(this.card(item, tone, state, index));
    }
    section.append(list);
    return section;
  }

  private readySection(data: ProjectConsole, state: AppState): HTMLElement {
    const section = this.queueSection("下一步队列", "ready", data.ready_queue, state);
    const ambiguity = el(
      "p",
      `console-ambiguity${data.ambiguity.has_unique_primary ? " ambiguity-unique" : ""}`,
      data.ambiguity.has_unique_primary
        ? "当前存在唯一主候选。"
        : `当前没有唯一主任务，存在 ${data.ambiguity.candidate_count} 个可执行候选。`,
    );
    ambiguity.setAttribute("role", "status");
    section.insertBefore(ambiguity, section.children[1] ?? null);
    return section;
  }

  private card(item: ConsoleItem, tone: string, state: AppState, index: number): HTMLElement {
    const entry = el("li", `console-card card-${tone}`);
    const article = el("article");
    const head = el("div", "console-card-head");
    head.append(
      el("span", "console-order", String(index + 1).padStart(2, "0")),
      el("code", "console-task-id", item.task_id ?? item.session_id ?? "UNKNOWN"),
      el("span", `console-source source-${freshnessTone(item)}`, freshnessLabel(item)),
    );
    article.append(head, el("h3", "console-card-title", item.title));
    const meta = el("p", "console-card-meta");
    const metaParts = [
      item.harness_id,
      item.phase ? PHASE_LABEL[item.phase] ?? item.phase : null,
      item.last_activity_at ? ageLabel(item.last_activity_at) : null,
    ].filter(Boolean);
    const sources = `来源：${item.source_kinds.map((source) => SOURCE_LABEL[source] ?? source).join(" + ")}`;
    meta.textContent = metaParts.length ? `${metaParts.join(" · ")} · ${sources}` : sources;
    article.append(meta, labelledLine("下一步", item.next_step));
    if (item.blocking_task_ids.length > 0) {
      article.append(labelledLine("阻塞于", item.blocking_task_ids.join("、")));
    }
    if (item.why_now_codes.length > 0) {
      article.append(labelledLine("原因", item.why_now_codes.join(" · ")));
    }
    const actions = el("div", "console-card-actions");
    const context = [item.task_id ?? item.title, item.session_id].filter(Boolean).join(" · ");
    if (item.task_id) {
      actions.append(this.button("查看任务", `task:${item.task_id}`, item.task_id, () => this.store.openTaskRoute(item.task_id!), `查看任务 ${context}`));
      const path = state.snapshot?.tasks.find((task) => task.task_id === item.task_id)?.source_path;
      if (path) {
        actions.append(this.copyButton("复制 TASK 路径", `task-path:${item.task_id}`, item.task_id, path, `复制 TASK 路径 ${context}`));
      }
    }
    actions.append(this.copyButton("复制下一步", `next:${item.task_id ?? item.session_id}`, item.task_id, item.next_step, `复制下一步 ${context}`));
    if (item.worktree) {
      actions.append(this.copyButton("复制 Worktree", `worktree:${item.task_id ?? item.session_id}`, item.task_id, item.worktree, `复制 Worktree ${context}`));
    }
    article.append(actions);
    entry.append(article);
    return entry;
  }

  private recentSection(data: ProjectConsole): HTMLElement {
    const section = el("section", "console-section console-section-recent");
    const heading = el("div", "console-section-heading");
    heading.append(el("h2", null, "最近变化"), el("span", "console-section-count", String(data.recent_changes.length)));
    section.append(heading);
    if (data.recent_changes.length === 0) {
      section.append(el("p", "console-empty", "当前没有可确认的最近变化。"));
      return section;
    }
    const list = el("ul", "console-change-list");
    for (const change of data.recent_changes) {
      list.append(
        el(
          "li",
          null,
          `${change.task_id ?? change.session_id ?? "运行时"} · ${change.kind === "task_snapshot" ? "TASK/Snapshot 已变化" : "Runtime 会话已更新"} · ${ageLabel(change.at)}`,
        ),
      );
    }
    section.append(list, el("p", "console-disclaimer", data.disclaimer));
    return section;
  }

  private button(text: string, key: string, taskId: string | null, action: () => void, accessibleName?: string): HTMLButtonElement {
    const button = el("button", "console-action", text) as HTMLButtonElement;
    button.type = "button";
    button.dataset.consoleFocusKey = key;
    if (taskId) button.dataset.consoleTaskId = taskId;
    if (accessibleName) button.setAttribute("aria-label", accessibleName);
    button.addEventListener("click", action);
    return button;
  }

  private copyButton(text: string, key: string, taskId: string | null, value: string, accessibleName: string): HTMLButtonElement {
    return this.button(text, key, taskId, () => {
      void navigator.clipboard.writeText(value).then(
        () => { this.announcement.textContent = `${text}已复制。`; },
        () => { this.announcement.textContent = `${text}失败，请手动复制。`; },
      );
    }, accessibleName);
  }

  private restoreFocus(key: string | null, taskId: string | null): void {
    if (!key) return;
    const controls = [...this.root.querySelectorAll<HTMLElement>("[data-console-focus-key]")];
    const target = controls.find((item) => item.dataset.consoleFocusKey === key)
      ?? controls.find((item) => taskId && item.dataset.consoleTaskId === taskId)
      ?? controls[0];
    target?.focus({ preventScroll: true });
    if (target && target.dataset.consoleFocusKey !== key) {
      this.announcement.textContent = "项目总览已更新，焦点已移动到当前可用操作。";
    }
  }
}

function projectName(root: string): string {
  const normalized = root.replace(/[\\/]+$/, "");
  return normalized.split(/[\\/]/).pop() || root;
}

function freshnessTone(item: ConsoleItem): string {
  if (item.freshness === "stale" || item.freshness === "invalid") return "stale";
  if (item.freshness === "live") return "live";
  if (item.freshness === "partial") return "partial";
  if (item.freshness === "ended") return "ended";
  return "derived";
}

function freshnessLabel(item: ConsoleItem): string {
  if (item.freshness === "live") return "实时";
  if (item.freshness === "stale") return "状态过期";
  if (item.freshness === "partial") return "证据不完整";
  if (item.freshness === "ended") return "已结束";
  if (item.freshness === "invalid") return "状态无效";
  return `${item.source_kinds.map((source) => SOURCE_LABEL[source] ?? source).join(" + ")} 派生`;
}

function consoleStateLabel(state: ProjectConsole["state"]): string {
  return state === "fresh" ? "事实状态：新鲜" : state === "stale" ? "事实状态：陈旧" : "事实状态：证据不完整";
}

function freshnessItem(label: string, timestamp: string, source: string): HTMLElement {
  const item = el("div", "freshness-item");
  item.append(el("span", "freshness-label", label), el("strong", null, ageLabel(timestamp)), el("span", "freshness-source", source));
  return item;
}

function labelledLine(label: string, value: string): HTMLElement {
  const line = el("p", "console-card-line");
  line.append(el("span", "console-line-label", label), document.createTextNode(value));
  return line;
}

function ageLabel(timestamp: string): string {
  const elapsed = Math.max(0, Date.now() - new Date(timestamp).getTime());
  const seconds = Math.floor(elapsed / 1000);
  if (seconds < 5) return "刚刚";
  if (seconds < 60) return `${seconds} 秒前`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  return new Date(timestamp).toLocaleString("zh-CN", { hour12: false });
}

function emptyText(tone: string): string {
  return {
    human: "当前没有必须由你处理的事项。",
    active: "当前没有可确认的活跃工作。",
    ready: "当前没有可开始的任务。",
    blocked: "当前没有已知阻塞。",
    stale: "当前没有过期的 Runtime 状态。",
  }[tone] ?? "暂无项目。";
}
