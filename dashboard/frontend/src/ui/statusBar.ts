/**
 * Always-visible global status bar: project root, branch/HEAD, snapshot time
 * and revision, fresh/stale/partial, diagnostic counts, git state and the
 * SSE connection state. All values are text; colour is only supplemental.
 */
import type { AppState } from "../state/store";
import { el, clear } from "./dom";
import {
  GIT_STATE_LABEL,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  shortSha,
  SNAPSHOT_STATE_LABEL,
} from "./labels";

const CONNECTION_LABEL: Record<string, string> = {
  connecting: "实时连接：连接中",
  connected: "实时连接：已连接",
  reconnecting: "实时连接：断线重连中",
  disconnected: "实时连接：已断开",
  fixture: "实时连接：fixture 模式（无 SSE）",
};

export class StatusBar {
  readonly root: HTMLElement;

  constructor() {
    this.root = el("header", "status-bar");
    this.root.setAttribute("aria-label", "全局状态栏");
  }

  update(state: AppState): void {
    clear(this.root);
    const snapshot = state.snapshot;
    const project = snapshot?.project ?? null;

    const brand = el("div", "status-brand", "任务关系仪表盘");
    brand.append(el("span", "status-readonly", "只读"));
    this.root.append(brand);

    if (state.fixtureName) {
      const badge = el("span", "status-fixture-badge", `fixture：${state.fixtureName}`);
      this.root.append(badge);
    }

    const projectInfo = el(
      "span",
      "status-item status-project",
      project
        ? `项目：${project.root} ｜ 分支：${project.branch ?? "未知"} ｜ HEAD：${shortSha(project.head)}`
        : "项目：—",
    );
    this.root.append(projectInfo);

    if (project) {
      const gitState = el("span", `status-item git-${project.git_state}`, GIT_STATE_LABEL[project.git_state] ?? project.git_state);
      this.root.append(gitState);
      if (project.dirty !== null) {
        this.root.append(el("span", "status-item", project.dirty ? "工作区：有脏文件" : "工作区：干净"));
      }
    }

    if (snapshot) {
      const snapshotState = el(
        "span",
        `status-item snapshot-${snapshot.state}`,
        `${SNAPSHOT_STATE_LABEL[snapshot.state] ?? snapshot.state}`,
      );
      this.root.append(snapshotState);
      this.root.append(
        el("span", "status-item", `快照时间：${snapshot.generated_at} ｜ revision：${shortSha(snapshot.revision, 8)}`),
      );
      const counts = snapshot.summary.counts_by_severity;
      const severity = el("span", "status-item status-severity");
      for (const key of ["error", "violation", "warning", "info"] as const) {
        const chip = el(
          "span",
          `severity-chip severity-${key}`,
          `${SEVERITY_ICON[key]} ${SEVERITY_LABEL[key]} ${counts[key]}`,
        );
        severity.append(chip);
      }
      this.root.append(severity);
    }

    const connection = el(
      "span",
      `status-item connection-${state.connection}`,
      CONNECTION_LABEL[state.connection] ?? state.connection,
    );
    connection.setAttribute("role", "status");
    this.root.append(connection);
  }
}
