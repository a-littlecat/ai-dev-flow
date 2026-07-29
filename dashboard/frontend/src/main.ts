/**
 * Application entry point.
 *
 * Runtime contract:
 * - same-origin GET /api/v1/snapshot|tasks/{id}|health plus SSE /api/v1/events;
 * - every payload is strictly validated against the versioned contract schema;
 * - SSE is only an invalidation hint — each event triggers an ETag re-fetch;
 * - `reset_required` clears local view state first, even for the current
 *   revision; a subsequent 304 never undoes the reset;
 * - snapshot refreshes are serialized (request epoch + queue) and detail
 *   replies are bound to the triggering snapshot revision, so slower older
 *   responses can never overwrite newer facts;
 * - `?fixture=<name>` loads a versioned contract fixture instead (dev/tests),
 *   still strictly validated, with SSE disabled and a visible fixture badge.
 */
import { fetchFixtureSnapshot, fetchHealth, fetchSnapshot, fetchTaskDetail } from "./api/client";
import { SnapshotEventStream } from "./api/sse";
import { AppStore } from "./state/store";
import { filterTasks, resolveSelectionAfterFilter } from "./state/derive";
import "./styles.css";
import { StatusBar } from "./ui/statusBar";
import { Toolbar } from "./ui/toolbar";
import { GraphView } from "./ui/graph/graphView";
import { DetailPanel } from "./ui/detailPanel";
import { Overlays } from "./ui/overlays";
import { el } from "./ui/dom";
import { SNAPSHOT_STATE_LABEL } from "./ui/labels";

const HEALTH_POLL_MS = 4000;

class DashboardApp {
  private readonly store = new AppStore();
  private readonly statusBar = new StatusBar();
  private readonly toolbar: Toolbar;
  private readonly graph: GraphView;
  private readonly detail: DetailPanel;
  private readonly overlays: Overlays;
  private readonly events: SnapshotEventStream;
  private readonly fixtureName: string | null;
  private healthTimer: number | null = null;
  private lastAnnouncedRevision: string | null = null;
  /**
   * Snapshot refreshes are serialized through a promise chain and tagged
   * with a monotonically increasing epoch: a slower older response can
   * never overwrite a newer snapshot/ETag.
   */
  private snapshotEpoch = 0;
  private snapshotQueue: Promise<void> = Promise.resolve();
  /** Epoch guarding task-detail replies against out-of-order completion. */
  private detailEpoch = 0;

  constructor(mount: HTMLElement) {
    const params = new URLSearchParams(window.location.search);
    this.fixtureName = params.get("fixture");

    this.toolbar = new Toolbar(this.store);
    this.graph = new GraphView(this.store);
    this.detail = new DetailPanel(this.store);
    this.overlays = new Overlays(() => void this.retrySnapshot());

    const layout = el("div", "app-shell");
    const main = el("main", "app-main");
    const workspace = el("div", "app-workspace");
    workspace.append(this.graph.root, this.detail.root);
    main.append(this.toolbar.root, workspace);
    layout.append(this.statusBar.root, this.overlays.root, main, this.overlays.drawerRoot, this.overlays.liveRegion);
    mount.append(layout);

    this.store.subscribe((state, changed) => {
      if (changed.has("snapshot") || changed.has("connection") || changed.has("phase") || changed.has("phaseError")) {
        this.statusBar.update(state);
        this.overlays.update(state);
      }
      if (
        changed.has("snapshot") ||
        changed.has("filters") ||
        changed.has("highlight") ||
        changed.has("focus") ||
        changed.has("selectedTaskId") ||
        changed.has("viewport")
      ) {
        this.graph.update(state);
        this.toolbar.update(state);
      }
      if (changed.has("detail") || changed.has("panelCollapsed") || changed.has("snapshot")) {
        this.detail.update(state);
      }
      if (changed.has("selectedTaskId") && state.selectedTaskId) {
        void this.loadDetail(state.selectedTaskId);
      }
      if (changed.has("filters") && state.snapshot && state.derived) {
        // Keep the detail panel consistent with the visible result set: a
        // selection that the new filters hid is either switched to the single
        // unambiguous remaining task or cleared — never left showing a task
        // the user just filtered out. Nothing is auto-selected from scratch.
        const next = resolveSelectionAfterFilter(
          filterTasks(state.snapshot, state.derived, state.filters),
          state.selectedTaskId,
        );
        if (next !== undefined) {
          this.store.selectTask(next);
        }
      }
      if (
        changed.has("snapshot") &&
        !changed.has("selectedTaskId") &&
        state.selectedTaskId &&
        state.detail.taskId === state.selectedTaskId
      ) {
        // New revision arrived while a task is selected: refresh its detail so
        // the panel never shows facts from an older snapshot.
        void this.loadDetail(state.selectedTaskId);
      }
      if (changed.has("revisionCounter") && state.snapshot) {
        this.announceSnapshot(state);
      }
    });

    this.events = new SnapshotEventStream({
      onEvent: (event) => this.onSnapshotEvent(event.revision, event.reset_required),
      onStatus: (status) => {
        this.store.setConnection(status);
        if (status === "connected") {
          this.overlays.announce("实时连接已建立");
        } else if (status === "reconnecting") {
          this.overlays.announce("实时连接断开，正在自动重连");
        }
      },
      onProtocolError: (detail) => {
        // Never silent: visible degraded banner + controlled GET re-sync.
        this.store.setStreamProtocolError(detail);
        this.overlays.announce("实时事件流协议错误，正在重新同步");
        void this.queueSnapshotRefresh(false);
      },
    });

    // Paint the initial (loading) state; before this the subscriber only
    // reacts to changes, so the loading banner would never appear.
    const initial = this.store.get();
    this.statusBar.update(initial);
    this.overlays.update(initial);
  }

  async start(): Promise<void> {
    if (this.fixtureName) {
      await this.loadFixture();
    } else {
      await this.queueSnapshotRefresh(false);
    }
    // Fit the initial graph once content is laid out.
    requestAnimationFrame(() => this.graph.fitToContent(false));
  }

  private async loadFixture(): Promise<void> {
    this.stopHealthPolling();
    if (!this.fixtureName) {
      return;
    }
    const result = await fetchFixtureSnapshot(this.fixtureName);
    if (result.ok) {
      this.store.setSnapshot(result.value.snapshot, null, this.fixtureName);
      this.store.setConnection("fixture");
    } else {
      this.store.setPhaseError(result.failure);
      this.scheduleHealthPolling();
    }
  }

  private async retrySnapshot(): Promise<void> {
    if (this.fixtureName) {
      await this.loadFixture();
      return;
    }
    await this.queueSnapshotRefresh(false);
  }

  /**
   * Serialized snapshot refresh. Every trigger (initial load, retry, health
   * recovery, SSE invalidation, protocol-error re-sync) appends to the same
   * chain, so requests never overlap and completion order cannot regress
   * the visible snapshot. The epoch additionally discards a response that
   * was superseded while in flight.
   */
  private queueSnapshotRefresh(resetView: boolean): Promise<void> {
    const epoch = ++this.snapshotEpoch;
    const queued = this.snapshotQueue.then(() => this.refreshSnapshot(epoch, resetView));
    this.snapshotQueue = queued.catch(() => undefined);
    return queued;
  }

  private async refreshSnapshot(epoch: number, resetView: boolean): Promise<void> {
    this.stopHealthPolling();
    if (epoch !== this.snapshotEpoch) {
      return; // superseded before starting; the newest request owns the state
    }
    const result = await fetchSnapshot(this.store.get().etag ?? undefined);
    if (epoch !== this.snapshotEpoch) {
      return; // superseded in flight: drop this older response
    }
    if (result.ok) {
      if (result.value !== null) {
        this.store.setSnapshot(result.value.snapshot, result.value.etag ?? this.store.get().etag, null);
      } else {
        // 304: the local snapshot is current, so the re-sync succeeded —
        // a protocol-error banner may be cleared (genuine failures stay).
        this.store.clearProtocolError();
      }
      // 304: local snapshot already current; a requested reset still stands.
      if (resetView) {
        requestAnimationFrame(() => this.graph.fitToContent(false));
      }
      this.events.start();
      return;
    }
    this.store.setPhaseError(result.failure);
    // Snapshot unavailable (starting/degraded) or disconnected: poll health
    // and resume automatically when the backend recovers.
    this.scheduleHealthPolling();
  }

  private onSnapshotEvent(_revision: string, resetRequired: boolean): void {
    // reset_required always wins — even when the event carries the current
    // revision (initial connect / reconnect semantics). Per contract every
    // event is followed by an If-None-Match re-read; a 304 keeps the local
    // snapshot but never undoes the reset.
    if (resetRequired) {
      this.store.resetViewState();
    }
    void this.queueSnapshotRefresh(resetRequired);
  }

  private async loadDetail(taskId: string): Promise<void> {
    const epoch = ++this.detailEpoch;
    const snapshotRevision = this.store.get().snapshot?.revision ?? null;
    const result = await fetchTaskDetail(taskId);
    if (epoch !== this.detailEpoch) {
      return; // superseded by a newer selection/refresh: drop the old reply
    }
    if (result.ok) {
      if (result.value.revision !== snapshotRevision) {
        // The server answered with a detail from another revision: never
        // display cross-revision facts. Re-sync the snapshot instead — the
        // refresh re-triggers this detail load once revisions align again
        // (a 304 leaves the loading state; no loop is possible).
        void this.queueSnapshotRefresh(false);
        return;
      }
      this.store.setDetailReady(result.value, snapshotRevision);
      return;
    }
    const envelope = result.failure.kind === "http" ? result.failure.error : null;
    if (envelope && envelope.revision !== null && envelope.revision !== snapshotRevision) {
      // An error envelope from another revision says nothing about the
      // current one: discard and re-sync as above.
      void this.queueSnapshotRefresh(false);
      return;
    }
    this.store.setDetailError(taskId, envelope, snapshotRevision);
  }

  private scheduleHealthPolling(): void {
    if (this.healthTimer !== null || this.fixtureName) {
      return; // fixture mode has no backend to poll
    }
    this.healthTimer = window.setInterval(() => void this.pollHealth(), HEALTH_POLL_MS);
  }

  private stopHealthPolling(): void {
    if (this.healthTimer !== null) {
      window.clearInterval(this.healthTimer);
      this.healthTimer = null;
    }
  }

  private async pollHealth(): Promise<void> {
    const result = await fetchHealth();
    if (!result.ok) {
      this.store.setConnection("disconnected");
      return;
    }
    this.store.setHealth(result.value);
    const health = result.value;
    if (health.server_state === "ready" && health.snapshot_state !== null) {
      this.stopHealthPolling();
      await this.queueSnapshotRefresh(false);
    }
  }

  private announceSnapshot(state: ReturnType<AppStore["get"]>): void {
    const snapshot = state.snapshot;
    if (!snapshot || snapshot.revision === this.lastAnnouncedRevision) {
      return;
    }
    this.lastAnnouncedRevision = snapshot.revision;
    this.overlays.announce(
      `快照已更新：${SNAPSHOT_STATE_LABEL[snapshot.state] ?? snapshot.state}，任务 ${snapshot.tasks.length} 个，关系 ${snapshot.edges.length} 条`,
    );
  }
}

const mount = document.getElementById("app");
if (mount) {
  const app = new DashboardApp(mount);
  void app.start();
}
