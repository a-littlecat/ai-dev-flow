/**
 * Single UI-state store. The server snapshot is the only source of task
 * truth; this store holds the snapshot plus *view* state (selection, focus,
 * filters, viewport). Only filters, viewport and panel preferences are
 * persisted to localStorage — never task facts.
 */
import type { DashboardSnapshot, ErrorEnvelope, Health, TaskDetail } from "../generated/contracts.types";
import { derive, emptyFilters, type DerivedData, type FilterState, type HighlightMode } from "./derive";
import type { ApiFailure } from "../api/client";
import type { SseStatus } from "../api/sse";

export type Phase = "loading" | "ready" | "error";

export interface Viewport {
  x: number;
  y: number;
  k: number;
}

export type FocusMode = "all" | "upstream" | "downstream";

export interface DetailState {
  status: "idle" | "loading" | "ready" | "error";
  taskId: string | null;
  data: TaskDetail | null;
  error: ErrorEnvelope | null;
}

export interface AppState {
  phase: Phase;
  /** Human-readable reason when phase === "error" (API disconnected, 503, schema drift). */
  phaseError: string | null;
  snapshot: DashboardSnapshot | null;
  derived: DerivedData | null;
  etag: string | null;
  health: Health | null;
  connection: SseStatus | "disconnected" | "fixture";
  fixtureName: string | null;
  selectedTaskId: string | null;
  detail: DetailState;
  panelCollapsed: boolean;
  highlight: HighlightMode;
  focus: { mode: FocusMode; taskId: string | null };
  filters: FilterState;
  viewport: Viewport;
  viewportDirty: boolean;
  /** Bumped on every accepted snapshot so views can animate revision changes. */
  revisionCounter: number;
}

const PREFS_KEY = "adf-dashboard-ui-v1";

interface PersistedPrefs {
  filters?: FilterState;
  viewport?: Viewport;
  panelCollapsed?: boolean;
}

function loadPrefs(): PersistedPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as PersistedPrefs;
    return typeof parsed === "object" && parsed !== null ? parsed : {};
  } catch {
    return {};
  }
}

function savePrefs(state: AppState): void {
  try {
    const prefs: PersistedPrefs = {
      filters: state.filters,
      viewport: state.viewport,
      panelCollapsed: state.panelCollapsed,
    };
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    // storage may be unavailable; preferences are best-effort only
  }
}

export type Listener = (state: AppState, changed: ReadonlySet<keyof AppState>) => void;

export class AppStore {
  private state: AppState;
  private listeners = new Set<Listener>();
  /** True while the visible phaseError is an SSE protocol error (re-syncable). */
  private protocolErrorActive = false;

  constructor() {
    const prefs = loadPrefs();
    this.state = {
      phase: "loading",
      phaseError: null,
      snapshot: null,
      derived: null,
      etag: null,
      health: null,
      connection: "disconnected",
      fixtureName: null,
      selectedTaskId: null,
      detail: { status: "idle", taskId: null, data: null, error: null },
      panelCollapsed: prefs.panelCollapsed ?? false,
      highlight: "none",
      focus: { mode: "all", taskId: null },
      filters: { ...emptyFilters(), ...prefs.filters },
      viewport: prefs.viewport ?? { x: 0, y: 0, k: 1 },
      viewportDirty: false,
      revisionCounter: 0,
    };
  }

  get(): AppState {
    return this.state;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private update(patch: Partial<AppState>, persist = false): void {
    const changed = new Set<keyof AppState>();
    for (const key of Object.keys(patch) as (keyof AppState)[]) {
      if (this.state[key] !== patch[key]) {
        changed.add(key);
      }
    }
    if (changed.size === 0) {
      return;
    }
    this.state = { ...this.state, ...patch };
    if (persist) {
      savePrefs(this.state);
    }
    for (const listener of this.listeners) {
      listener(this.state, changed);
    }
  }

  setLoading(): void {
    this.update({ phase: "loading", phaseError: null });
  }

  setSnapshot(snapshot: DashboardSnapshot, etag: string | null, fixtureName: string | null): void {
    const previousRevision = this.state.snapshot?.revision ?? null;
    const isNew = previousRevision !== snapshot.revision;
    this.protocolErrorActive = false;
    const selectedTaskId =
      this.state.selectedTaskId && snapshot.tasks.some((task) => task.task_id === this.state.selectedTaskId)
        ? this.state.selectedTaskId
        : null;
    this.update({
      phase: "ready",
      phaseError: null,
      snapshot,
      derived: derive(snapshot),
      etag,
      fixtureName,
      selectedTaskId,
      revisionCounter: isNew ? this.state.revisionCounter + 1 : this.state.revisionCounter,
      ...(selectedTaskId === null
        ? { detail: { status: "idle", taskId: null, data: null, error: null }, focus: { mode: "all" as FocusMode, taskId: null } }
        : {}),
    });
  }

  setPhaseError(failure: ApiFailure): void {
    this.protocolErrorActive = false;
    let message: string;
    if (failure.kind === "network") {
      message = `无法连接本地 API（${failure.message}）。后端可能未启动或已断开。`;
    } else if (failure.kind === "schema") {
      message = `API 响应未通过合同 schema 校验：${failure.error.message}`;
    } else {
      const envelope = failure.error;
      message = envelope
        ? `API 错误 ${envelope.error.code}：${envelope.error.message}`
        : `API 返回 HTTP ${failure.status}`;
    }
    this.update({
      phase: this.state.snapshot ? this.state.phase : "error",
      phaseError: message,
      connection: failure.kind === "network" ? "disconnected" : this.state.connection,
    });
  }

  setConnection(connection: AppState["connection"]): void {
    this.update({ connection });
  }

  setHealth(health: Health): void {
    this.update({ health });
  }

  selectTask(taskId: string | null): void {
    if (taskId === this.state.selectedTaskId) {
      return;
    }
    this.update({
      selectedTaskId: taskId,
      detail:
        taskId === null
          ? { status: "idle", taskId: null, data: null, error: null }
          : { status: "loading", taskId, data: null, error: null },
      panelCollapsed: taskId === null ? this.state.panelCollapsed : false,
    });
  }

  setDetailReady(data: TaskDetail, snapshotRevision: string | null): void {
    if (this.state.detail.taskId !== data.task.task_id) {
      return;
    }
    // Bind the reply to the snapshot revision that triggered the request: a
    // detail fetched against an older snapshot must never overwrite facts
    // from the current one.
    if ((this.state.snapshot?.revision ?? null) !== snapshotRevision) {
      return;
    }
    // The payload itself must belong to the triggering revision: a detail
    // served from another revision is cross-generation data and is dropped.
    if (data.revision !== snapshotRevision) {
      return;
    }
    this.update({ detail: { status: "ready", taskId: data.task.task_id, data, error: null } });
  }

  setDetailError(taskId: string, error: ErrorEnvelope | null, snapshotRevision: string | null): void {
    if (this.state.detail.taskId !== taskId) {
      return;
    }
    if ((this.state.snapshot?.revision ?? null) !== snapshotRevision) {
      return;
    }
    // A non-null envelope revision must match the triggering revision; an
    // error from another revision must not surface as this task's state.
    if (error && error.revision !== null && error.revision !== snapshotRevision) {
      return;
    }
    this.update({ detail: { status: "error", taskId, data: null, error } });
  }

  /**
   * SSE protocol error (malformed / schema-drifting event frame): surfaces a
   * visible banner without touching the current snapshot or connection
   * state; the caller triggers a controlled re-sync afterwards.
   */
  setStreamProtocolError(detail: string): void {
    this.protocolErrorActive = true;
    this.update({
      phaseError: `实时事件流协议错误：${detail}。已触发受控重新同步。`,
    });
  }

  /**
   * Clear the protocol-error banner after a successful re-sync (a 200 or 304
   * snapshot reply). Genuine failures set via setPhaseError are untouched.
   */
  clearProtocolError(): void {
    if (!this.protocolErrorActive) {
      return;
    }
    this.protocolErrorActive = false;
    this.update({ phaseError: null });
  }

  togglePanel(): void {
    this.update({ panelCollapsed: !this.state.panelCollapsed }, true);
  }

  setHighlight(highlight: HighlightMode): void {
    this.update({ highlight: this.state.highlight === highlight ? "none" : highlight });
  }

  setFocus(mode: FocusMode, taskId: string | null): void {
    this.update({ focus: { mode, taskId } });
  }

  clearFocus(): void {
    this.update({ focus: { mode: "all", taskId: null } });
  }

  setFilters(filters: FilterState): void {
    this.update({ filters }, true);
  }

  patchFilters(patch: Partial<FilterState>): void {
    this.setFilters({ ...this.state.filters, ...patch });
  }

  resetFilters(): void {
    this.setFilters(emptyFilters());
  }

  setViewport(viewport: Viewport, dirty = true): void {
    this.update({ viewport, viewportDirty: dirty }, true);
  }

  /** Full local reset required by an SSE reset event: selection, focus, highlight. */
  resetViewState(): void {
    this.update({
      selectedTaskId: null,
      detail: { status: "idle", taskId: null, data: null, error: null },
      focus: { mode: "all", taskId: null },
      highlight: "none",
    });
  }
}
