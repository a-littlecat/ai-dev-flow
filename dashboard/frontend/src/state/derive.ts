/**
 * Derived, read-only indexes over the snapshot. Nothing here mutates the
 * snapshot or invents facts: every view is a pure projection of wire data.
 */
import type {
  ActionRecommendation,
  DashboardSnapshot,
  Diagnostic,
  ParallelAssessment,
  RelationshipEdge,
  TaskNode,
  WorktreeSnapshot,
} from "../generated/contracts.types";

export interface DerivedData {
  actionsByTask: Map<string, ActionRecommendation[]>;
  primaryActionByTask: Map<string, ActionRecommendation | null>;
  assessmentsByTask: Map<string, ParallelAssessment[]>;
  diagnosticsByTask: Map<string, Diagnostic[]>;
  worstSeverityByTask: Map<string, "error" | "violation" | "warning" | "info">;
  worktreeByTask: Map<string, WorktreeSnapshot>;
  /** task -> upstream task ids (prerequisites / parents / replaced / origins). */
  upstream: Map<string, Set<string>>;
  /** task -> downstream task ids (dependents / children / replacements / discoveries). */
  downstream: Map<string, Set<string>>;
}

const SEVERITY_ORDER = ["error", "violation", "warning", "info"] as const;

export function derive(snapshot: DashboardSnapshot): DerivedData {
  const actionsByTask = new Map<string, ActionRecommendation[]>();
  for (const action of snapshot.actions) {
    const list = actionsByTask.get(action.task_id) ?? [];
    list.push(action);
    actionsByTask.set(action.task_id, list);
  }
  const primaryActionByTask = new Map<string, ActionRecommendation | null>();
  for (const task of snapshot.tasks) {
    // The server emits recommendations in canonical wire order (task ID,
    // action-matrix order, action ID). The frontend must not re-rank them:
    // the "primary" action is simply the first recommendation on the wire.
    primaryActionByTask.set(task.task_id, actionsByTask.get(task.task_id)?.[0] ?? null);
  }

  const assessmentsByTask = new Map<string, ParallelAssessment[]>();
  for (const assessment of snapshot.parallel_assessments) {
    for (const taskId of [assessment.left_task_id, assessment.right_task_id]) {
      const list = assessmentsByTask.get(taskId) ?? [];
      list.push(assessment);
      assessmentsByTask.set(taskId, list);
    }
  }

  const diagnosticById = new Map(snapshot.diagnostics.map((item) => [item.diagnostic_id, item]));
  const diagnosticsByTask = new Map<string, Diagnostic[]>();
  for (const task of snapshot.tasks) {
    const merged = new Map<string, Diagnostic>();
    for (const id of task.diagnostic_ids) {
      const item = diagnosticById.get(id);
      if (item) {
        merged.set(id, item);
      }
    }
    for (const item of snapshot.diagnostics) {
      if (item.task_ids.includes(task.task_id)) {
        merged.set(item.diagnostic_id, item);
      }
    }
    diagnosticsByTask.set(task.task_id, [...merged.values()]);
  }
  const worstSeverityByTask = new Map<string, (typeof SEVERITY_ORDER)[number]>();
  for (const [taskId, items] of diagnosticsByTask) {
    const worst = SEVERITY_ORDER.find((severity) => items.some((item) => item.severity === severity));
    if (worst) {
      worstSeverityByTask.set(taskId, worst);
    }
  }

  const worktreeByTask = new Map<string, WorktreeSnapshot>();
  for (const task of snapshot.tasks) {
    if (!task.branch_hint) {
      continue;
    }
    const expected = `refs/heads/${task.branch_hint}`;
    const matches = snapshot.project.worktrees.filter((wt) => wt.branch === expected);
    if (matches.length === 1 && matches[0]) {
      worktreeByTask.set(task.task_id, matches[0]);
    }
  }

  const upstream = new Map<string, Set<string>>();
  const downstream = new Map<string, Set<string>>();
  const add = (map: Map<string, Set<string>>, key: string, value: string) => {
    const set = map.get(key) ?? new Set<string>();
    set.add(value);
    map.set(key, set);
  };
  for (const edge of snapshot.edges) {
    if (edge.type === "conflicts_with") {
      continue; // symmetric conflict is neither upstream nor downstream
    }
    // Display flow for every directional edge type is target -> source.
    add(upstream, edge.source_task_id, edge.target_task_id);
    add(downstream, edge.target_task_id, edge.source_task_id);
  }

  return {
    actionsByTask,
    primaryActionByTask,
    assessmentsByTask,
    diagnosticsByTask,
    worstSeverityByTask,
    worktreeByTask,
    upstream,
    downstream,
  };
}

/**
 * Text-search predicate shared by the structural filter (`filterTasks`) and
 * the graph search affordance: case-insensitive substring match on the task
 * id or the title. An empty/blank needle matches everything.
 */
export function taskMatchesText(task: TaskNode, text: string): boolean {
  const needle = text.trim().toLowerCase();
  if (needle === "") {
    return true;
  }
  return task.task_id.toLowerCase().includes(needle) || task.title.toLowerCase().includes(needle);
}

/**
 * Reconcile the current selection with the visible task set after a filter
 * change, so the detail panel never shows a task the search just filtered out:
 * - no selection, or the selected task is still visible -> `undefined`
 *   (leave the selection untouched);
 * - the selected task left the visible set and exactly one task remains ->
 *   that task id (switch to the single unambiguous result);
 * - otherwise -> `null` (clear the selection).
 * Never auto-selects when nothing was selected.
 */
export function resolveSelectionAfterFilter(
  visible: Set<string>,
  selectedTaskId: string | null,
): string | null | undefined {
  if (selectedTaskId === null || visible.has(selectedTaskId)) {
    return undefined;
  }
  if (visible.size === 1) {
    return [...visible][0]!;
  }
  return null;
}

export interface FilterState {
  text: string;
  lifecycles: string[];
  actionKinds: string[];
  riskFlags: string[];
  taskClasses: string[];
  moduleLocks: string[];
  worktreeRoots: string[];
  edgeTypes: string[];
  severities: string[];
}

export function emptyFilters(): FilterState {
  return {
    text: "",
    lifecycles: [],
    actionKinds: [],
    riskFlags: [],
    taskClasses: [],
    moduleLocks: [],
    worktreeRoots: [],
    edgeTypes: [],
    severities: [],
  };
}

export function filtersActive(filters: FilterState): boolean {
  return (
    filters.text.trim() !== "" ||
    filters.lifecycles.length > 0 ||
    filters.actionKinds.length > 0 ||
    filters.riskFlags.length > 0 ||
    filters.taskClasses.length > 0 ||
    filters.moduleLocks.length > 0 ||
    filters.worktreeRoots.length > 0 ||
    filters.edgeTypes.length > 0 ||
    filters.severities.length > 0
  );
}

/** Visible task ids under the current filter (AND across groups, OR within a group).
 *  Note: `edgeTypes` is an edge-level filter applied by the graph view, not a
 *  node-level filter, so it is intentionally not consulted here. */
export function filterTasks(snapshot: DashboardSnapshot, derived: DerivedData, filters: FilterState): Set<string> {
  const text = filters.text;
  const visible = new Set<string>();
  for (const task of snapshot.tasks) {
    if (!taskMatchesText(task, text)) {
      continue;
    }
    if (filters.lifecycles.length > 0 && !filters.lifecycles.includes(task.lifecycle ?? "null")) {
      continue;
    }
    if (filters.actionKinds.length > 0) {
      const kinds = (derived.actionsByTask.get(task.task_id) ?? []).map((a) => a.action_kind);
      if (!filters.actionKinds.some((kind) => kinds.includes(kind as ActionRecommendation["action_kind"]))) {
        continue;
      }
    }
    if (filters.riskFlags.length > 0 && !filters.riskFlags.some((flag) => task.risk_flags.includes(flag))) {
      continue;
    }
    if (filters.taskClasses.length > 0 && !filters.taskClasses.includes(task.task_class ?? "null")) {
      continue;
    }
    if (filters.moduleLocks.length > 0 && !filters.moduleLocks.some((lock) => task.module_locks.includes(lock))) {
      continue;
    }
    if (filters.worktreeRoots.length > 0) {
      const wt = derived.worktreeByTask.get(task.task_id);
      if (!wt || !filters.worktreeRoots.includes(wt.root)) {
        continue;
      }
    }
    if (filters.severities.length > 0) {
      const severities = (derived.diagnosticsByTask.get(task.task_id) ?? []).map((d) => d.severity);
      if (!filters.severities.some((severity) => severities.includes(severity as Diagnostic["severity"]))) {
        continue;
      }
    }
    visible.add(task.task_id);
  }
  return visible;
}

export type HighlightMode = "none" | "actionable" | "candidates" | "decisions";

/** Task ids matched by a quick-highlight entry. */
export function highlightTasks(snapshot: DashboardSnapshot, derived: DerivedData, mode: HighlightMode): Set<string> {
  const matched = new Set<string>();
  if (mode === "actionable") {
    for (const action of snapshot.actions) {
      if (action.eligibility === "actionable" && action.action_kind !== "none") {
        matched.add(action.task_id);
      }
    }
  } else if (mode === "candidates") {
    for (const assessment of snapshot.parallel_assessments) {
      if (assessment.result === "candidate") {
        matched.add(assessment.left_task_id);
        matched.add(assessment.right_task_id);
      }
    }
  } else if (mode === "decisions") {
    for (const action of snapshot.actions) {
      if (action.action_kind === "user_decision" || action.required_authority === "user_decision") {
        matched.add(action.task_id);
      }
    }
  }
  void derived;
  return matched;
}

export function highlightCounts(snapshot: DashboardSnapshot, derived: DerivedData): Record<Exclude<HighlightMode, "none">, number> {
  return {
    actionable: highlightTasks(snapshot, derived, "actionable").size,
    candidates: highlightTasks(snapshot, derived, "candidates").size,
    decisions: highlightTasks(snapshot, derived, "decisions").size,
  };
}

/** Transitive upstream/downstream closure (cycle-safe) including the task itself. */
export function focusClosure(
  derived: DerivedData,
  taskId: string,
  direction: "upstream" | "downstream",
): Set<string> {
  const adjacency = direction === "upstream" ? derived.upstream : derived.downstream;
  const visited = new Set<string>([taskId]);
  const queue = [taskId];
  while (queue.length > 0) {
    const current = queue.pop();
    if (!current) {
      break;
    }
    for (const next of adjacency.get(current) ?? []) {
      if (!visited.has(next)) {
        visited.add(next);
        queue.push(next);
      }
    }
  }
  return visited;
}

export function edgeLabelKey(edge: RelationshipEdge): string {
  return edge.type;
}

export function taskSortKey(task: TaskNode): string {
  return task.task_id;
}
