/**
 * Collapsible task detail panel. Shows every orthogonal status axis, edges
 * with dependency conditions, action recommendations with authority state,
 * parallel assessments, Git/Worktree evidence, diagnostics and provenance.
 * Nothing is merged or hidden; unknown values are shown as 未知.
 */
import type {
  ActionRecommendation,
  ParallelAssessment,
  Provenance,
  RelationshipEdge,
  TaskDetail,
  WorktreeSnapshot,
} from "../generated/contracts.types";
import type { AppState, AppStore } from "../state/store";
import { el, clear } from "./dom";
import {
  ACCEPTANCE_LABEL,
  ACTION_KIND_LABEL,
  ACTION_REASON_LABEL,
  AUTHORITY_STATE_LABEL,
  AXIS_LABEL,
  CLOSE_AUTHORITY_LABEL,
  COMMIT_LABEL,
  CONDITION_EVAL_LABEL,
  EDGE_TYPE_LABEL,
  ELIGIBILITY_LABEL,
  label,
  LIFECYCLE_LABEL,
  MERGE_AUTHORITY_LABEL,
  MERGE_LABEL,
  PARALLEL_INTENT_LABEL,
  PARALLEL_REASON_LABEL,
  PARALLEL_RESULT_LABEL,
  REQUIRED_AUTHORITY_LABEL,
  REVIEW_LABEL,
  SCHEDULING_STATE_LABEL,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  shortSha,
  TASK_TYPE_LABEL,
  UA_STATUS_LABEL,
  WORKTREE_REQ_LABEL,
} from "./labels";

export class DetailPanel {
  readonly root: HTMLElement;

  constructor(private readonly store: AppStore) {
    this.root = el("aside", "detail-panel");
    this.root.setAttribute("aria-label", "任务详情面板");
  }

  update(state: AppState): void {
    clear(this.root);
    const idle = state.detail.status === "idle";
    const collapsed = idle || state.panelCollapsed;
    const header = el("div", "detail-header");
    const title = el("h2", "detail-title", state.detail.taskId ? `任务详情：${state.detail.taskId}` : "任务详情");
    header.append(title);
    if (!idle) {
      const toggle = el("button", "detail-toggle", state.panelCollapsed ? "展开 ▸" : "收起 ◂");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", String(!state.panelCollapsed));
      toggle.addEventListener("click", () => this.store.togglePanel());
      header.append(toggle);
    }
    this.root.append(header);
    this.root.hidden = idle;
    this.root.classList.toggle("detail-collapsed", collapsed);
    this.root.classList.toggle("detail-idle", idle);
    if (collapsed) {
      return;
    }

    const body = el("div", "detail-body");
    this.root.append(body);
    const detail = state.detail;
    if (detail.status === "loading") {
      body.append(el("p", "detail-hint", "正在加载任务详情…"));
      return;
    }
    if (detail.status === "error") {
      const code = detail.error?.error.code ?? "UNKNOWN";
      const message = detail.error?.error.message ?? "任务详情加载失败";
      body.append(el("p", "detail-error", `错误 ${code}：${message}`));
      return;
    }
    if (detail.data) {
      this.renderDetail(body, detail.data, state);
    }
  }

  private renderDetail(body: HTMLElement, detail: TaskDetail, state: AppState): void {
    const task = detail.task;

    body.append(el("p", "detail-subtitle", `${task.title}（${task.source_path}）`));

    const axes = el("section", "detail-section");
    axes.append(el("h3", null, "状态轴（相互独立，不合并）"));
    const rows: [string, string][] = [
      ["任务类型", label(TASK_TYPE_LABEL, task.task_type)],
      ["任务等级", task.task_class ? `${task.task_class} 级` : "未知"],
      ["生命周期", label(LIFECYCLE_LABEL, task.lifecycle)],
      ["评审", label(REVIEW_LABEL, task.review_status)],
      ["用户验收", `${task.ua_level ?? "未知"} ｜ ${label(UA_STATUS_LABEL, task.ua_status)}`],
      ["验收授权", label(ACCEPTANCE_LABEL, task.acceptance_authority)],
      ["提交", label(COMMIT_LABEL, task.commit_status)],
      ["合并", label(MERGE_LABEL, task.merge_status)],
      ["合并授权", label(MERGE_AUTHORITY_LABEL, task.merge_authority)],
      ["关闭授权", label(CLOSE_AUTHORITY_LABEL, task.close_authority)],
      ["Scheduling", SCHEDULING_STATE_LABEL[task.scheduling_state] ?? task.scheduling_state],
      ["优先级", task.priority ?? "未知"],
      ["并行意图", label(PARALLEL_INTENT_LABEL, task.parallel_intent)],
      ["Worktree 要求", label(WORKTREE_REQ_LABEL, task.worktree_requirement)],
      ["分支提示", task.branch_hint ?? "无"],
      ["数据新鲜度", task.freshness],
    ];
    axes.append(defTable(rows));
    if (task.unsupported_axes.length > 0) {
      axes.append(el("p", "detail-note", `不支持的轴：${task.unsupported_axes.join("、")}`));
    }
    if (task.risk_flags.length > 0) {
      axes.append(el("p", "detail-note", `风险标记：${task.risk_flags.join("、")}`));
    }
    if (task.write_scope.length > 0) {
      axes.append(el("p", "detail-note", `写范围：${task.write_scope.join("、")}`));
    }
    if (task.module_locks.length > 0) {
      axes.append(el("p", "detail-note", `模块锁：${task.module_locks.join("、")}`));
    }
    body.append(axes);

    body.append(this.renderActions(detail.actions));
    body.append(this.renderEdges(detail.edges, task.task_id));
    body.append(this.renderAssessments(detail.parallel_assessments));
    body.append(this.renderWorktrees(state, detail));
    body.append(this.renderDiagnostics(detail));
    body.append(this.renderProvenance(task.provenance, "任务 provenance"));
    body.append(el("p", "detail-disclaimer", state.snapshot?.disclaimer ?? ""));
  }

  private renderActions(actions: ActionRecommendation[]): HTMLElement {
    const section = el("section", "detail-section");
    section.append(el("h3", null, "下一动作建议（建议 ≠ 授权）"));
    if (actions.length === 0) {
      section.append(el("p", "detail-hint", "无动作建议。"));
      return section;
    }
    for (const action of actions) {
      const card = el("div", `action-card eligibility-${action.eligibility}`);
      card.append(
        el(
          "p",
          "action-head",
          `${label(ACTION_KIND_LABEL, action.action_kind)} ｜ ${label(ELIGIBILITY_LABEL, action.eligibility)} ｜ 需要授权：${label(REQUIRED_AUTHORITY_LABEL, action.required_authority)}（${label(AUTHORITY_STATE_LABEL, action.authority_state)}）`,
        ),
      );
      if (action.reason_codes.length > 0) {
        card.append(el("p", "action-reasons", `原因：${action.reason_codes.map((code) => ACTION_REASON_LABEL[code] ?? code).join("；")}`));
      }
      if (action.blocking_task_ids.length > 0) {
        card.append(el("p", "action-blocking", `被以下任务阻塞：${action.blocking_task_ids.join("、")}`));
      }
      section.append(card);
    }
    return section;
  }

  private renderEdges(edges: RelationshipEdge[], taskId: string): HTMLElement {
    const section = el("section", "detail-section");
    section.append(el("h3", null, "关系与依赖条件"));
    if (edges.length === 0) {
      section.append(el("p", "detail-hint", "没有关系边。"));
      return section;
    }
    const list = el("ul", "edge-detail-list");
    for (const edge of edges) {
      const other = edge.source_task_id === taskId ? edge.target_task_id : edge.source_task_id;
      let text = `${EDGE_TYPE_LABEL[edge.type] ?? edge.type} ↔ ${other}（来源：${edge.origin}）`;
      if (edge.condition) {
        text += `；条件：${AXIS_LABEL[edge.condition.axis] ?? edge.condition.axis} 期望「${edge.condition.expected}」实际「${edge.condition.actual ?? "未知"}」→ ${CONDITION_EVAL_LABEL[edge.condition.evaluation] ?? edge.condition.evaluation}`;
      }
      list.append(el("li", `edge-detail edge-${edge.type}`, text));
    }
    section.append(list);
    return section;
  }

  private renderAssessments(assessments: ParallelAssessment[]): HTMLElement {
    const section = el("section", "detail-section");
    section.append(el("h3", null, "并行评估"));
    if (assessments.length === 0) {
      section.append(el("p", "detail-hint", "无并行评估。"));
      return section;
    }
    for (const assessment of assessments) {
      const card = el("div", `assessment-card assessment-${assessment.result}`);
      card.append(
        el(
          "p",
          "action-head",
          `${assessment.left_task_id} × ${assessment.right_task_id}：${PARALLEL_RESULT_LABEL[assessment.result] ?? assessment.result}`,
        ),
      );
      card.append(el("p", null, `原因：${assessment.reason_codes.map((c) => PARALLEL_REASON_LABEL[c] ?? c).join("；") || "无"}`));
      if (assessment.hard_conflicts.length > 0) {
        card.append(el("p", null, `硬冲突：${assessment.hard_conflicts.join("、")}`));
      }
      if (assessment.projection_conflicts.length > 0) {
        card.append(el("p", null, `投影冲突（须串行写回）：${assessment.projection_conflicts.join("、")}`));
      }
      card.append(el("p", "detail-note", "requires_user_confirmation = true：候选不产生执行授权。"));
      for (const wt of assessment.worktree_evidence) {
        card.append(worktreeLine(wt));
      }
      section.append(card);
    }
    return section;
  }

  private renderWorktrees(state: AppState, detail: TaskDetail): HTMLElement {
    const section = el("section", "detail-section");
    section.append(el("h3", null, "Git / Worktree 证据"));
    const related = state.snapshot?.project.worktrees.filter(
      (wt) => detail.task.branch_hint && wt.branch === `refs/heads/${detail.task.branch_hint}`,
    );
    if (!related || related.length === 0) {
      section.append(el("p", "detail-hint", "没有与该任务 branch_hint 唯一匹配的 Worktree 证据（未知）。"));
      return section;
    }
    for (const wt of related) {
      section.append(worktreeLine(wt));
    }
    return section;
  }

  private renderDiagnostics(detail: TaskDetail): HTMLElement {
    const section = el("section", "detail-section");
    section.append(el("h3", null, "诊断"));
    if (detail.diagnostics.length === 0) {
      section.append(el("p", "detail-hint", "无诊断。"));
      return section;
    }
    const list = el("ul", "diag-list");
    for (const diag of detail.diagnostics) {
      list.append(
        el(
          "li",
          `diag-item severity-${diag.severity}`,
          `${SEVERITY_ICON[diag.severity] ?? ""} ${SEVERITY_LABEL[diag.severity] ?? diag.severity} ｜ ${diag.code}：${diag.message}`,
        ),
      );
    }
    section.append(list);
    return section;
  }

  private renderProvenance(provenance: Provenance[], titleText: string): HTMLElement {
    const section = el("section", "detail-section");
    section.append(el("h3", null, titleText));
    if (provenance.length === 0) {
      section.append(el("p", "detail-hint", "无 provenance 记录。"));
      return section;
    }
    const list = el("ul", "provenance-list");
    for (const item of provenance) {
      list.append(
        el(
          "li",
          "provenance-item",
          `${item.source_path}:${item.line} ｜ ${item.heading ?? "-"} / ${item.field ?? "-"} = ${item.raw_value ?? "（空）"} ｜ 来源 ${item.source_type}`,
        ),
      );
    }
    section.append(list);
    return section;
  }
}

function defTable(rows: [string, string][]): HTMLElement {
  const table = el("table", "def-table");
  const tbody = el("tbody");
  for (const [key, value] of rows) {
    const tr = el("tr");
    tr.append(el("th", null, key));
    tr.getElementsByTagName("th")[0]?.setAttribute("scope", "row");
    tr.append(el("td", null, value));
    tbody.append(tr);
  }
  table.append(tbody);
  return table;
}

function worktreeLine(wt: WorktreeSnapshot): HTMLElement {
  const dirty = wt.dirty_state === "clean" ? "干净" : wt.dirty_state === "dirty" ? "脏" : "未知";
  return el(
    "p",
    "worktree-line",
    `Worktree：${wt.root} ｜ 分支 ${wt.branch ?? "未知"} ｜ HEAD ${shortSha(wt.head)} ｜ ${dirty}${wt.locked ? " ｜ 已锁定" : ""}${wt.prunable ? " ｜ 可清理" : ""}${wt.detached ? " ｜ detached" : ""}${wt.dirty_paths.length > 0 ? ` ｜ 脏文件：${wt.dirty_paths.join("、")}` : ""}`,
  );
}
