import type {
  ActionRecommendation,
  DashboardSnapshot,
  ParallelAssessment,
  TaskNode,
} from "../generated/contracts.types";
import type { DerivedData } from "./derive";

export interface CurrentActionItem {
  task: TaskNode;
  action: ActionRecommendation;
}

export interface ParallelSuggestionItem {
  task: TaskNode;
  counterpart: TaskNode;
  assessment: ParallelAssessment;
}

export interface ActiveTaskItem {
  task: TaskNode;
  action: ActionRecommendation | null;
}

export interface WaitingItem {
  task: TaskNode;
  counterpart: TaskNode | null;
  action: ActionRecommendation | null;
  assessment: ParallelAssessment | null;
  kind: "blocked" | "action_blocked" | "serial";
}

export interface OverviewData {
  current: CurrentActionItem | null;
  parallelSuggestions: ParallelSuggestionItem[];
  activeTasks: ActiveTaskItem[];
  waiting: WaitingItem[];
  hiddenTaskCount: number;
  diagnosticCount: number;
}

const TASK_PRIORITY: Record<NonNullable<TaskNode["priority"]>, number> = {
  high: 0,
  medium: 1,
  low: 2,
  TBD: 3,
};

/**
 * Pure, conservative projection for the default workbench.
 *
 * It never invents scheduling facts:
 * - current action comes from snapshot.actions;
 * - parallel suggestions come only from candidate assessments;
 * - active work comes only from lifecycle === In Progress;
 * - waiting rows come from blocked actions or must_serial assessments.
 */
export function deriveOverview(snapshot: DashboardSnapshot, derived: DerivedData): OverviewData {
  const taskById = new Map(snapshot.tasks.map((task) => [task.task_id, task]));
  // The backend owns action ordering. The workbench may project that order,
  // but must not invent a client-side priority or scheduling decision.
  const first = snapshot.actions
    .map((action) => ({ action, task: taskById.get(action.task_id) ?? null }))
    .find(
      (entry): entry is { action: ActionRecommendation; task: TaskNode } =>
        entry.task !== null && entry.action.action_kind !== "none",
    );
  const current: CurrentActionItem | null = first ? { task: first.task, action: first.action } : null;

  const occupied = new Set<string>();
  if (current) {
    occupied.add(current.task.task_id);
  }

  const candidateAssessments = snapshot.parallel_assessments
    .filter((assessment) => assessment.result === "candidate")
    .sort((left, right) => {
      const currentId = current?.task.task_id ?? null;
      const leftTouchesCurrent =
        currentId !== null && (left.left_task_id === currentId || left.right_task_id === currentId);
      const rightTouchesCurrent =
        currentId !== null && (right.left_task_id === currentId || right.right_task_id === currentId);
      if (leftTouchesCurrent !== rightTouchesCurrent) {
        return leftTouchesCurrent ? -1 : 1;
      }
      return pairKey(left).localeCompare(pairKey(right));
    });
  const parallelSuggestions: ParallelSuggestionItem[] = [];
  for (const assessment of candidateAssessments) {
    const left = taskById.get(assessment.left_task_id);
    const right = taskById.get(assessment.right_task_id);
    if (!left || !right) {
      continue;
    }
    const suggested = current?.task.task_id === left.task_id ? right : left;
    const counterpart = suggested.task_id === left.task_id ? right : left;
    if (occupied.has(suggested.task_id)) {
      continue;
    }
    parallelSuggestions.push({ task: suggested, counterpart, assessment });
    occupied.add(suggested.task_id);
    if (parallelSuggestions.length === 2) {
      break;
    }
  }

  const activeTasks = snapshot.tasks
    .filter((task) => task.lifecycle === "In Progress" && !occupied.has(task.task_id))
    .sort(compareTasks)
    .slice(0, 2)
    .map((task) => ({ task, action: derived.primaryActionByTask.get(task.task_id) ?? null }));
  for (const item of activeTasks) {
    occupied.add(item.task.task_id);
  }

  const waiting: WaitingItem[] = [];
  for (const action of snapshot.actions) {
    if (action.eligibility !== "blocked" || occupied.has(action.task_id)) {
      continue;
    }
    const task = taskById.get(action.task_id);
    if (!task) {
      continue;
    }
    const counterpart = action.blocking_task_ids.map((id) => taskById.get(id)).find(Boolean) ?? null;
    waiting.push({
      task,
      counterpart,
      action,
      assessment: null,
      kind: counterpart ? "blocked" : "action_blocked",
    });
    occupied.add(task.task_id);
    if (waiting.length === 2) {
      break;
    }
  }

  if (waiting.length < 2) {
    const serialAssessments = snapshot.parallel_assessments
      .filter((assessment) => assessment.result === "must_serial")
      .sort((left, right) => {
        const currentId = current?.task.task_id ?? null;
        const leftTouchesCurrent =
          currentId !== null && (left.left_task_id === currentId || left.right_task_id === currentId);
        const rightTouchesCurrent =
          currentId !== null && (right.left_task_id === currentId || right.right_task_id === currentId);
        if (leftTouchesCurrent !== rightTouchesCurrent) {
          return leftTouchesCurrent ? -1 : 1;
        }
        return pairKey(left).localeCompare(pairKey(right));
      });
    for (const assessment of serialAssessments) {
      const left = taskById.get(assessment.left_task_id);
      const right = taskById.get(assessment.right_task_id);
      if (!left || !right) {
        continue;
      }
      const task = current?.task.task_id === left.task_id ? right : left;
      const counterpart = task.task_id === left.task_id ? right : left;
      if (occupied.has(task.task_id)) {
        continue;
      }
      waiting.push({ task, counterpart, action: null, assessment, kind: "serial" });
      occupied.add(task.task_id);
      if (waiting.length === 2) {
        break;
      }
    }
  }

  return {
    current,
    parallelSuggestions,
    activeTasks,
    waiting,
    hiddenTaskCount: Math.max(0, snapshot.tasks.length - occupied.size),
    diagnosticCount: snapshot.diagnostics.length,
  };
}

function compareTasks(left: TaskNode, right: TaskNode): number {
  const leftPriority = left.priority ? TASK_PRIORITY[left.priority] : 4;
  const rightPriority = right.priority ? TASK_PRIORITY[right.priority] : 4;
  return leftPriority - rightPriority || left.task_id.localeCompare(right.task_id);
}

function pairKey(assessment: ParallelAssessment): string {
  return `${assessment.left_task_id}\u0000${assessment.right_task_id}`;
}
