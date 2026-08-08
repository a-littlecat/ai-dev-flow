import { filterTasks } from "../state/derive";
import type { AppState, AppStore } from "../state/store";
import { clear, el } from "./dom";
import { GIT_STATE_LABEL, SEVERITY_LABEL, SNAPSHOT_STATE_LABEL, shortSha } from "./labels";

export class StatusBar {
  readonly root = el("header", "status-bar");
  private readonly summary = el("div", "status-summary");
  private readonly actions = el("div", "status-actions");
  private readonly search = el("input", "status-search") as HTMLInputElement;
  private readonly viewToggle = el("button", "status-view-toggle");
  private readonly legacyToggle = el("button", "status-legacy-toggle");
  private readonly consoleToggle = el("button", "status-console-toggle");

  constructor(private readonly store: AppStore) {
    this.root.setAttribute("aria-label", "全局状态栏");
    this.search.type = "search";
    this.search.placeholder = "搜索任务 ID / 标题…";
    this.search.setAttribute("aria-label", "搜索任务 ID 或标题");
    this.search.addEventListener("input", () => this.store.patchFilters({ text: this.search.value }));
    this.search.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") {
        return;
      }
      const state = this.store.get();
      if (!state.snapshot || !state.derived) {
        return;
      }
      const matched = [...filterTasks(state.snapshot, state.derived, state.filters)];
      if (matched.length === 1 && matched[0]) {
        this.store.openTaskRoute(matched[0]);
      } else {
        this.store.showFullNetwork();
      }
    });
    this.viewToggle.type = "button";
    this.viewToggle.addEventListener("click", () => {
      this.store.showFullNetwork();
    });
    this.legacyToggle.type = "button";
    this.legacyToggle.addEventListener("click", () => this.store.showLegacy());
    this.consoleToggle.type = "button";
    this.consoleToggle.addEventListener("click", () => this.store.showConsole());
    this.actions.append(this.search, this.consoleToggle, this.viewToggle, this.legacyToggle);
    this.root.append(this.summary, this.actions);
  }

  update(state: AppState): void {
    clear(this.summary);
    const brand = el("span", "status-brand", "Project Console");
    brand.append(el("span", "status-readonly", "只读"));
    this.summary.append(brand);

    const project = state.snapshot?.project ?? null;
    const projectInfo = el("span", "status-item status-project", project ? `项目：${projectName(project.root)}` : "项目：—");
    if (project) {
      projectInfo.title = project.root;
    }
    this.summary.append(projectInfo);

    const connection = el(
      "span",
      `status-item connection-${state.connection}`,
      state.connection === "connected"
        ? "● 连接正常"
        : state.connection === "reconnecting"
          ? "● 正在重连"
          : state.connection === "fixture"
            ? "● Fixture 数据"
            : "● 连接断开",
    );
    connection.setAttribute("role", "status");
    this.summary.append(connection);

    if (state.fixtureName) {
      this.summary.append(el("span", "status-fixture-badge", `Fixture：${state.fixtureName}`));
    }

    // Keep full operational provenance available to assistive technology and
    // diagnostics without returning the visual status wall to the header.
    const technical = el("span", "status-technical visually-hidden");
    const technicalParts: string[] = [];
    if (state.snapshot) {
      technicalParts.push(SNAPSHOT_STATE_LABEL[state.snapshot.state] ?? state.snapshot.state);
      technicalParts.push(`项目：${state.snapshot.project.root}`);
      technicalParts.push(`分支：${state.snapshot.project.branch ?? "未知"}`);
      technicalParts.push(`HEAD：${shortSha(state.snapshot.project.head)}`);
      technicalParts.push(GIT_STATE_LABEL[state.snapshot.project.git_state] ?? state.snapshot.project.git_state);
      technicalParts.push(`revision：${shortSha(state.snapshot.revision, 8)}`);
      for (const severity of ["error", "violation", "warning", "info"] as const) {
        technicalParts.push(`${SEVERITY_LABEL[severity]} ${state.snapshot.summary.counts_by_severity[severity]}`);
      }
    }
    if (state.fixtureName) {
      technicalParts.push(`fixture：${state.fixtureName}`);
    }
    technicalParts.push(
      state.connection === "connected"
        ? "实时连接：已连接"
        : state.connection === "reconnecting"
          ? "实时连接：断线重连中"
          : state.connection === "fixture"
            ? "实时连接：fixture 模式（无 SSE）"
            : "实时连接：已断开",
    );
    technical.textContent = technicalParts.join(" ｜ ");
    if (state.snapshot) {
      for (const severity of ["error", "violation", "warning", "info"] as const) {
        technical.append(
          el(
            "span",
            `severity-chip severity-${severity}`,
            `${SEVERITY_LABEL[severity]} ${state.snapshot.summary.counts_by_severity[severity]}`,
          ),
        );
      }
    }
    this.summary.append(technical);

    if (this.search.value !== state.filters.text) {
      this.search.value = state.filters.text;
    }
    this.consoleToggle.textContent = "项目总览";
    this.viewToggle.textContent = "关系诊断";
    this.legacyToggle.textContent = "旧版回退";
    this.consoleToggle.setAttribute("aria-pressed", String(state.viewMode === "console"));
    this.viewToggle.setAttribute("aria-pressed", String(state.viewMode === "network"));
    this.legacyToggle.setAttribute("aria-pressed", String(state.viewMode === "legacy"));
    this.consoleToggle.setAttribute("aria-label", "打开 Project Console 项目总览");
    this.viewToggle.setAttribute("aria-label", state.viewMode === "legacy" ? "打开完整关系图" : "打开完整任务关系诊断");
    this.legacyToggle.setAttribute("aria-label", state.viewMode === "network" ? "返回任务执行总览" : "打开旧版 Action Center 回退视图");
  }
}

function projectName(root: string): string {
  const normalized = root.replace(/[\\/]+$/, "");
  return normalized.split(/[\\/]/).pop() || root;
}
