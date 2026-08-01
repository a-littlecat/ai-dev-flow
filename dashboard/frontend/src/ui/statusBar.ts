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
      if (this.store.get().viewMode === "overview") {
        this.store.showFullNetwork();
      } else {
        this.store.showOverview();
      }
    });
    this.actions.append(this.search, this.viewToggle);
    this.root.append(this.summary, this.actions);
  }

  update(state: AppState): void {
    clear(this.summary);
    const brand = el("span", "status-brand", "任务关系仪表盘");
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
    this.viewToggle.textContent = state.viewMode === "overview" ? "完整关系图 →" : "← 执行总览";
    this.viewToggle.setAttribute(
      "aria-label",
      state.viewMode === "overview" ? "打开完整关系图" : "返回任务执行总览",
    );
  }
}

function projectName(root: string): string {
  const normalized = root.replace(/[\\/]+$/, "");
  return normalized.split(/[\\/]/).pop() || root;
}
