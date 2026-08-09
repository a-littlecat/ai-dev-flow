/**
 * Unit tests for the AppStore: snapshot acceptance, selection/detail flow,
 * error phases, highlight/focus/filters and the SSE reset semantics.
 * Node environment: localStorage is absent, so persistence is exercised only
 * through its best-effort try/catch path.
 */
import { describe, expect, it } from "vitest";
import { AppStore } from "../src/state/store";
import { emptyFilters } from "../src/state/derive";
import type { ErrorEnvelope, TaskDetail } from "../src/generated/contracts.types";
import { validateContract } from "../src/api/schema";
import { makeAction, makeAssessment, makeProjectConsole, makeSnapshot, makeTask, sha } from "./support";

function twoTaskSnapshot(revision = sha(900)) {
  return makeSnapshot({
    revision,
    tasks: [makeTask("TASK-A"), makeTask("TASK-B")],
    actions: [makeAction(910, "TASK-A")],
  });
}

describe("AppStore snapshot handling", () => {
  it("starts in loading phase with no snapshot", () => {
    const store = new AppStore();
    const state = store.get();
    expect(state.phase).toBe("loading");
    expect(state.snapshot).toBeNull();
    expect(state.derived).toBeNull();
    expect(state.connection).toBe("disconnected");
  });

  it("accepts a snapshot, derives indexes and enters ready phase", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), "etag-1", null);
    const state = store.get();
    expect(state.phase).toBe("ready");
    expect(state.etag).toBe("etag-1");
    expect(state.derived?.actionsByTask.get("TASK-A")?.length).toBe(1);
    expect(state.revisionCounter).toBe(1);
  });

  it("bumps revisionCounter only when the revision actually changes", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.setSnapshot(twoTaskSnapshot(), null, null);
    expect(store.get().revisionCounter).toBe(1);
    store.setSnapshot(twoTaskSnapshot(sha(901)), null, null);
    expect(store.get().revisionCounter).toBe(2);
  });

  it("drops selection, detail and focus when the selected task disappears", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    store.setFocus("upstream", "TASK-A");
    expect(store.get().selectedTaskId).toBe("TASK-A");

    store.setSnapshot(makeSnapshot({ revision: sha(902), tasks: [makeTask("TASK-B")] }), null, null);
    const state = store.get();
    expect(state.selectedTaskId).toBeNull();
    expect(state.detail.status).toBe("idle");
    expect(state.focus.mode).toBe("all");
  });

  it("keeps selection when the selected task survives a revision change", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    store.setSnapshot(twoTaskSnapshot(sha(903)), null, null);
    expect(store.get().selectedTaskId).toBe("TASK-A");
  });

  it("records fixture mode on the state", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, "fresh");
    expect(store.get().fixtureName).toBe("fresh");
  });
});

describe("AppStore Project Console generation guards", () => {
  it("defaults to console and exposes explicit network and legacy modes", () => {
    const store = new AppStore();
    expect(store.get().viewMode).toBe("console");
    store.showFullNetwork();
    expect(store.get().viewMode).toBe("network");
    store.showLegacy();
    expect(store.get().viewMode).toBe("legacy");
    store.showConsole();
    expect(store.get().viewMode).toBe("console");
  });

  it("rejects a console reply from another snapshot revision", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(sha(900)), null, null);
    expect(store.setConsoleReady(makeProjectConsole(sha(899)), "old-etag")).toBe(false);
    expect(store.get().console.data).toBeNull();
    expect(store.setConsoleReady(makeProjectConsole(sha(900)), "new-etag")).toBe(true);
    expect(store.get().console.etag).toBe("new-etag");
  });

  it("retains last-good console data and marks it stale on disconnect", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(sha(900)), null, null);
    const console = makeProjectConsole(sha(900));
    store.setConsoleReady(console, "etag");
    store.setConsoleFailure({ kind: "network", message: "lost" });
    expect(store.get().console.status).toBe("stale");
    expect(store.get().console.data).toBe(console);
    expect(store.get().console.message).toContain("保留上次数据");
  });

  it("invalidates a console ETag when the snapshot generation changes", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(sha(900)), null, null);
    const previous = makeProjectConsole(sha(900));
    store.setConsoleReady(previous, "console-etag");

    store.setSnapshot(twoTaskSnapshot(sha(901)), null, null);

    expect(store.get().console.data).toBe(previous);
    expect(store.get().console.status).toBe("stale");
    expect(store.get().console.etag).toBeNull();
    expect(store.get().console.message).toContain("项目事实已更新");
    expect(store.setConsoleNotModified()).toBe(false);
  });

  it("accepts 304 only when console and snapshot generations still match", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(sha(900)), null, null);
    store.setConsoleReady(makeProjectConsole(sha(900)), "console-etag");
    store.setConsoleFailure({ kind: "network", message: "lost" });

    expect(store.setConsoleNotModified()).toBe(true);
    expect(store.get().console.status).toBe("ready");
    expect(store.get().console.message).toBeNull();
  });
});

describe("AppStore error phases", () => {
  it("network failure without a snapshot enters the error phase", () => {
    const store = new AppStore();
    store.setPhaseError({ kind: "network", message: "connection refused" });
    const state = store.get();
    expect(state.phase).toBe("error");
    expect(state.phaseError).toContain("无法连接本地 API");
    expect(state.connection).toBe("disconnected");
  });

  it("http failure surfaces the error envelope code and message", () => {
    const store = new AppStore();
    store.setPhaseError({
      kind: "http",
      status: 503,
      error: validateContract<ErrorEnvelope>("ErrorEnvelope", {
        schema_version: "ai-dev-flow/dashboard-error/v1",
        error: {
          code: "SNAPSHOT_UNAVAILABLE",
          message: "快照尚不可用",
          details: { server_state: "starting" },
          provenance: [],
        },
        revision: null,
      }),
    });
    expect(store.get().phaseError).toContain("SNAPSHOT_UNAVAILABLE");
  });

  it("keeps the last-good snapshot visible when a refresh fails", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.setPhaseError({ kind: "network", message: "lost" });
    const state = store.get();
    expect(state.phase).toBe("ready");
    expect(state.snapshot).not.toBeNull();
    expect(state.phaseError).toContain("无法连接本地 API");
  });
});

describe("AppStore detail flow", () => {
  it("selectTask opens a loading detail and deselect resets it", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    expect(store.get().detail).toEqual({ status: "loading", taskId: "TASK-A", data: null, error: null });
    store.selectTask(null);
    expect(store.get().detail.status).toBe("idle");
  });

  it("setDetailReady ignores a reply for a different task", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    const staleDetail = validateContract<TaskDetail>("TaskDetail", {
      schema_version: "ai-dev-flow/dashboard-task-detail/v1",
      revision: sha(920),
      task: makeTask("TASK-B"),
      edges: [],
      actions: [],
      parallel_assessments: [],
      diagnostics: [],
    });
    store.setDetailReady(staleDetail, sha(900));
    expect(store.get().detail.status).toBe("loading");
  });

  it("setDetailReady ignores a reply bound to an older snapshot revision", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    const detail = validateContract<TaskDetail>("TaskDetail", {
      schema_version: "ai-dev-flow/dashboard-task-detail/v1",
      revision: sha(900),
      task: makeTask("TASK-A"),
      edges: [],
      actions: [],
      parallel_assessments: [],
      diagnostics: [],
    });
    // The reply was requested against sha(899), but the store already moved
    // to sha(900): it must not overwrite newer facts.
    store.setDetailReady(detail, sha(899));
    expect(store.get().detail.status).toBe("loading");
    store.setDetailReady(detail, sha(900));
    expect(store.get().detail.status).toBe("ready");
  });

  it("setDetailError only applies to the pending task and revision", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    store.setDetailError("TASK-B", null, sha(900));
    expect(store.get().detail.status).toBe("loading");
    store.setDetailError("TASK-A", null, sha(899));
    expect(store.get().detail.status).toBe("loading");
    store.setDetailError("TASK-A", null, sha(900));
    expect(store.get().detail.status).toBe("error");
  });

  it("setDetailReady ignores a payload whose own revision is not the triggering revision", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    const detail = (revision: string) =>
      validateContract<TaskDetail>("TaskDetail", {
        schema_version: "ai-dev-flow/dashboard-task-detail/v1",
        revision,
        task: makeTask("TASK-A"),
        edges: [],
        actions: [],
        parallel_assessments: [],
        diagnostics: [],
      });
    // The request was triggered at sha(900) and the store is still at
    // sha(900), but the payload itself is from sha(901): cross-revision data
    // must never be displayed.
    store.setDetailReady(detail(sha(901)), sha(900));
    expect(store.get().detail.status).toBe("loading");
    store.setDetailReady(detail(sha(900)), sha(900));
    expect(store.get().detail.status).toBe("ready");
  });

  it("setDetailError ignores an envelope whose non-null revision is not the triggering revision", () => {
    const envelope = (revision: string | null) =>
      validateContract<ErrorEnvelope>("ErrorEnvelope", {
        schema_version: "ai-dev-flow/dashboard-error/v1",
        error: { code: "TASK_NOT_FOUND", message: "任务不存在", details: { task_id: "TASK-A" }, provenance: [] },
        revision,
      });
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    // An error from another revision says nothing about this one.
    store.setDetailError("TASK-A", envelope(sha(901)), sha(900));
    expect(store.get().detail.status).toBe("loading");
    // A null revision (no current snapshot) or the matching revision applies.
    store.setDetailError("TASK-A", envelope(null), sha(900));
    expect(store.get().detail.status).toBe("error");
    store.selectTask("TASK-B");
    store.setDetailError("TASK-B", envelope(sha(900)), sha(900));
    expect(store.get().detail.status).toBe("error");
  });
});

describe("AppStore stream protocol errors", () => {
  it("surfaces a visible protocol error while keeping the last-good snapshot", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.setConnection("connected");
    store.setStreamProtocolError("事件帧不是合法 JSON");
    const state = store.get();
    expect(state.phase).toBe("ready");
    expect(state.snapshot).not.toBeNull();
    expect(state.phaseError).toContain("协议错误");
    expect(state.phaseError).toContain("事件帧不是合法 JSON");
    // The protocol error must not tear down the connection state.
    expect(state.connection).toBe("connected");
  });

  it("a successful snapshot refresh clears the protocol error banner", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.setStreamProtocolError("schema drift");
    expect(store.get().phaseError).not.toBeNull();
    store.setSnapshot(twoTaskSnapshot(sha(901)), null, null);
    expect(store.get().phaseError).toBeNull();
  });

  it("a successful 304-class re-sync clears the protocol error but never a genuine failure", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    // Protocol error: a successful re-sync (200 or 304) clears it.
    store.setStreamProtocolError("事件帧不是合法 JSON");
    expect(store.get().phaseError).toContain("协议错误");
    store.clearProtocolError();
    expect(store.get().phaseError).toBeNull();
    // Genuine failure: clearProtocolError must not touch it.
    store.setPhaseError({ kind: "network", message: "lost" });
    expect(store.get().phaseError).toContain("无法连接本地 API");
    store.clearProtocolError();
    expect(store.get().phaseError).toContain("无法连接本地 API");
    // A real failure supersedes a protocol error: the flag does not survive.
    store.setStreamProtocolError("schema drift");
    store.setPhaseError({ kind: "network", message: "lost" });
    store.clearProtocolError();
    expect(store.get().phaseError).toContain("无法连接本地 API");
  });
});

describe("AppStore view state", () => {
  it("highlight toggles on and off", () => {
    const store = new AppStore();
    store.setHighlight("candidates");
    expect(store.get().highlight).toBe("candidates");
    store.setHighlight("candidates");
    expect(store.get().highlight).toBe("none");
  });

  it("clears a stale focus anchor when selection moves to another task", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    store.setFocus("upstream", "TASK-A");

    store.selectTask("TASK-B");
    expect(store.get().selectedTaskId).toBe("TASK-B");
    expect(store.get().focus).toEqual({ mode: "all", taskId: null });

    store.setFocus("downstream", "TASK-B");
    store.selectTask("TASK-B");
    expect(store.get().focus).toEqual({ mode: "downstream", taskId: "TASK-B" });
  });

  it("resetViewState clears selection, focus and highlight (SSE reset semantics)", () => {
    const store = new AppStore();
    store.setSnapshot(twoTaskSnapshot(), null, null);
    store.selectTask("TASK-A");
    store.setFocus("downstream", "TASK-A");
    store.setHighlight("actionable");
    store.resetViewState();
    const state = store.get();
    expect(state.selectedTaskId).toBeNull();
    expect(state.detail.status).toBe("idle");
    expect(state.focus).toEqual({ mode: "all", taskId: null });
    expect(state.highlight).toBe("none");
  });

  it("patchFilters merges into existing filters and resetFilters clears them", () => {
    const store = new AppStore();
    store.patchFilters({ text: "abc" });
    store.patchFilters({ lifecycles: ["Ready"] });
    expect(store.get().filters.text).toBe("abc");
    expect(store.get().filters.lifecycles).toEqual(["Ready"]);
    store.resetFilters();
    expect(store.get().filters).toEqual(emptyFilters());
  });

  it("parallel assessments flow through unchanged for display", () => {
    const store = new AppStore();
    store.setSnapshot(
      makeSnapshot({
        tasks: [makeTask("PAIR-A"), makeTask("PAIR-B")],
        parallel_assessments: [makeAssessment(930, "PAIR-A", "PAIR-B", "unknown", ["WORKTREE_EVIDENCE_UNKNOWN"])],
      }),
      null,
      null,
    );
    const assessments = store.get().snapshot?.parallel_assessments ?? [];
    expect(assessments[0]?.result).toBe("unknown");
    expect(assessments[0]?.requires_user_confirmation).toBe(true);
  });
});
