import { defineConfig, type Plugin } from "vite";
import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { IncomingMessage, ServerResponse } from "node:http";
import Ajv2020 from "ajv/dist/2020.js";
import type { ValidateFunction } from "ajv";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const contractsRoot = path.resolve(frontendRoot, "../contracts");
const fixturesDir = path.join(contractsRoot, "fixtures", "v1");
const FIXTURE_NAME_RE = /^[a-z0-9-]+\.(json|sse)$/;

/**
 * Development-only read-only exposure of the versioned contract fixtures so
 * the app can run in `?fixture=<name>` mode without a backend. The contracts
 * directory itself is never modified.
 */
function contractFixturesPlugin(): Plugin {
  return {
    name: "contract-fixtures",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url || !req.url.startsWith("/fixtures/v1/")) {
          next();
          return;
        }
        const name = decodeURIComponent(req.url.slice("/fixtures/v1/".length).split("?")[0] ?? "");
        if (!FIXTURE_NAME_RE.test(name)) {
          res.statusCode = 404;
          res.end("not found");
          return;
        }
        const file = path.join(fixturesDir, name);
        if (!existsSync(file) || !statSync(file).isFile()) {
          res.statusCode = 404;
          res.end("not found");
          return;
        }
        res.setHeader(
          "Content-Type",
          name.endsWith(".sse") ? "text/event-stream; charset=utf-8" : "application/json; charset=utf-8",
        );
        createReadStream(file).pipe(res);
      });
    },
  };
}

/**
 * Browser-test mock backend (enabled only with DASHBOARD_MOCK_BACKEND=1).
 * Serves /api/v1/* from in-memory state controlled via /__mock__/* so
 * Playwright can drive snapshot, SSE, health and error scenarios without the
 * real backend. Every payload entering or leaving the mock is validated
 * against the same versioned contract schema the runtime uses.
 */
function mockBackendPlugin(): Plugin {
  const schemaPath = path.join(contractsRoot, "dashboard-contracts-v1.schema.json");
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  ajv.addSchema(JSON.parse(readFileSync(schemaPath, "utf-8")) as object, "ai-dev-flow/dashboard-contracts/v1");
  const validator = (def: string): ValidateFunction => {
    const fn = ajv.getSchema(`ai-dev-flow/dashboard-contracts/v1#/$defs/${def}`);
    if (!fn) {
      throw new Error(`contract schema is missing $defs.${def}`);
    }
    return fn;
  };
  const validateSnapshot = validator("DashboardSnapshot");
  const validateTaskDetail = validator("TaskDetail");
  const validateHealth = validator("Health");
  const validateEvent = validator("SnapshotEvent");
  const validateError = validator("ErrorEnvelope");
  const validateConsole = validator("ProjectConsole");

  interface MockState {
    snapshot: Record<string, unknown> | null;
    console: Record<string, unknown> | null;
    taskError: Record<string, unknown> | null;
    sseDown: boolean;
    truncateSnapshot: boolean;
    sseClients: Set<ServerResponse>;
  }
  const state: MockState = { snapshot: null, console: null, taskError: null, sseDown: false, truncateSnapshot: false, sseClients: new Set() };

  const sendJson = (res: ServerResponse, status: number, payload: unknown, headers: Record<string, string> = {}) => {
    res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", ...headers });
    res.end(JSON.stringify(payload));
  };

  const readBody = (req: IncomingMessage): Promise<unknown> =>
    new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];
      req.on("data", (chunk: Buffer) => chunks.push(chunk));
      req.on("end", () => {
        try {
          resolve(JSON.parse(Buffer.concat(chunks).toString("utf-8") || "null"));
        } catch (error) {
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      });
      req.on("error", reject);
    });

  const closeSseClients = () => {
    for (const client of state.sseClients) {
      client.socket?.destroy();
    }
    state.sseClients.clear();
  };

  const buildHealth = (): Record<string, unknown> => {
    const snapshot = state.snapshot;
    const summary = (snapshot?.summary ?? null) as { counts_by_severity?: unknown } | null;
    return {
      schema_version: "ai-dev-flow/dashboard-health/v1",
      server_state: "ready",
      watcher_state: "ready",
      last_refresh_at: (snapshot?.generated_at as string | undefined) ?? null,
      snapshot_state: (snapshot?.state as string | undefined) ?? null,
      revision: (snapshot?.revision as string | undefined) ?? null,
      diagnostic_counts: summary?.counts_by_severity ?? { error: 0, violation: 0, warning: 0, info: 0 },
    };
  };

  const buildTaskDetail = (taskId: string): Record<string, unknown> | null => {
    const snapshot = state.snapshot;
    if (!snapshot) {
      return null;
    }
    const tasks = (snapshot.tasks ?? []) as Record<string, unknown>[];
    const task = tasks.find((item) => item.task_id === taskId);
    if (!task) {
      return null;
    }
    const touches = (item: Record<string, unknown>, leftKey: string, rightKey: string) =>
      item[leftKey] === taskId || item[rightKey] === taskId;
    return {
      schema_version: "ai-dev-flow/dashboard-task-detail/v1",
      revision: snapshot.revision,
      task,
      edges: ((snapshot.edges ?? []) as Record<string, unknown>[]).filter((e) => touches(e, "source_task_id", "target_task_id")),
      actions: ((snapshot.actions ?? []) as Record<string, unknown>[]).filter((a) => a.task_id === taskId),
      parallel_assessments: ((snapshot.parallel_assessments ?? []) as Record<string, unknown>[]).filter((a) =>
        touches(a, "left_task_id", "right_task_id"),
      ),
      diagnostics: ((snapshot.diagnostics ?? []) as { task_ids?: string[] }[]).filter((d) =>
        (d.task_ids ?? []).includes(taskId),
      ),
    };
  };

  const buildConsole = (): Record<string, unknown> | null => {
    if (state.console) {
      return state.console;
    }
    const snapshot = state.snapshot;
    if (!snapshot) {
      return null;
    }
    const generatedAt = String(snapshot.generated_at);
    const revision = String(snapshot.revision);
    return {
      schema_version: "adf/project-console/v1",
      revision,
      snapshot_revision: revision,
      generated_at: generatedAt,
      state: snapshot.state,
      freshness: { task_facts_at: generatedAt, git_facts_at: generatedAt, runtime_facts_at: generatedAt },
      counts: { active_work: 0, human_attention: 0, ready_queue: 0, blocked: 0, stale_sessions: 0 },
      active_work: [],
      human_attention: [],
      ready_queue: [],
      blocked: [],
      stale_sessions: [],
      recent_changes: [],
      ambiguity: { has_unique_primary: false, candidate_count: 0, message: "当前没有唯一主任务" },
      disclaimer: "Project Console 是只读投影。",
    };
  };

  const sendEventFrame = (res: ServerResponse, payload: Record<string, unknown>): void => {
    res.write(`event: snapshot\nid: ${String(payload.revision)}\ndata: ${JSON.stringify(payload)}\n\n`);
  };

  const handleApi = (req: IncomingMessage, res: ServerResponse, url: string): void => {
    // Contract: with a current snapshot every error envelope carries the
    // current revision; only without any snapshot is revision null.
    const errorRevision = state.snapshot ? (state.snapshot.revision as string) : null;
    if (url === "/api/v1/snapshot") {
      if (!state.snapshot) {
        sendJson(res, 503, {
          error: { code: "SNAPSHOT_UNAVAILABLE", details: { server_state: "starting" }, message: "快照尚不可用", provenance: [] },
          revision: null,
          schema_version: "ai-dev-flow/dashboard-error/v1",
        });
        return;
      }
      // Contract-exact ETag: "sha256-<revision>".
      const etag = `"sha256-${String(state.snapshot.revision)}"`;
      if (req.headers["if-none-match"] === etag) {
        res.writeHead(304);
        res.end();
        return;
      }
      if (state.truncateSnapshot) {
        // Test-only hook: headers arrive, then the connection drops mid-body
        // so the client's body read rejects (network-failure mapping). The
        // headers and first bytes must actually reach the client before the
        // reset — otherwise Chrome silently retries the idempotent GET.
        state.truncateSnapshot = false;
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", ETag: etag });
        res.flushHeaders();
        res.write(JSON.stringify(state.snapshot).slice(0, 64), () => {
          setTimeout(() => res.socket?.destroy(), 50);
        });
        return;
      }
      sendJson(res, 200, state.snapshot, { ETag: etag, "Cache-Control": "private, no-cache" });
      return;
    }
    if (url === "/api/v1/health") {
      const health = buildHealth();
      if (!validateHealth(health)) {
        sendJson(res, 500, { ok: false, errors: validateHealth.errors });
        return;
      }
      sendJson(res, 200, health);
      return;
    }
    if (url === "/api/v1/console") {
      const console = buildConsole();
      if (!console) {
        sendJson(res, 503, {
          error: { code: "SNAPSHOT_UNAVAILABLE", details: { server_state: "starting" }, message: "快照尚不可用", provenance: [] },
          revision: null,
          schema_version: "ai-dev-flow/dashboard-error/v1",
        });
        return;
      }
      if (!validateConsole(console)) {
        sendJson(res, 500, { ok: false, errors: validateConsole.errors });
        return;
      }
      const etag = `"sha256-${String(console.revision)}"`;
      if (req.headers["if-none-match"] === etag) {
        res.writeHead(304);
        res.end();
        return;
      }
      sendJson(res, 200, console, { ETag: etag, "Cache-Control": "private, no-cache" });
      return;
    }
    if (url.startsWith("/api/v1/tasks/")) {
      const taskId = decodeURIComponent(url.slice("/api/v1/tasks/".length));
      if (state.taskError) {
        sendJson(res, 404, state.taskError);
        return;
      }
      const detail = buildTaskDetail(taskId);
      if (!detail) {
        sendJson(res, 404, {
          error: { code: "TASK_NOT_FOUND", details: { task_id: taskId }, message: "任务不存在", provenance: [] },
          revision: errorRevision,
          schema_version: "ai-dev-flow/dashboard-error/v1",
        });
        return;
      }
      if (!validateTaskDetail(detail)) {
        sendJson(res, 500, { ok: false, errors: validateTaskDetail.errors });
        return;
      }
      sendJson(res, 200, detail);
      return;
    }
    if (url === "/api/v1/events") {
      if (!state.snapshot) {
        // Contract: without any snapshot the events route answers 503.
        sendJson(res, 503, {
          error: { code: "SNAPSHOT_UNAVAILABLE", details: { server_state: "starting" }, message: "快照尚不可用", provenance: [] },
          revision: null,
          schema_version: "ai-dev-flow/dashboard-error/v1",
        });
        return;
      }
      if (state.sseDown) {
        req.socket.destroy();
        return;
      }
      res.writeHead(200, {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      });
      // Contract-exact reconnect directive.
      res.write("retry: 2000\n\n");
      state.sseClients.add(res);
      // Initial-connect / reconnect reset semantics: without a Last-Event-ID
      // the current revision is sent immediately with every task ID and
      // reset_required=true; a stale ID gets the current revision with an
      // empty change list and reset_required=true; a matching ID just waits.
      const revision = String(state.snapshot.revision);
      const lastEventId = req.headers["last-event-id"];
      if (lastEventId !== revision) {
        const allTaskIds = (state.snapshot.tasks as { task_id: string }[]).map((task) => task.task_id);
        const frame = {
          schema_version: "ai-dev-flow/dashboard-event/v1",
          revision,
          state: state.snapshot.state,
          changed_task_ids: lastEventId === undefined ? allTaskIds : [],
          reset_required: true,
        };
        sendEventFrame(res, frame);
      }
      req.on("close", () => state.sseClients.delete(res));
      return;
    }
    sendJson(res, 404, {
      error: { code: "ROUTE_NOT_FOUND", details: { path: url }, message: "路由不存在", provenance: [] },
      revision: errorRevision,
      schema_version: "ai-dev-flow/dashboard-error/v1",
    });
  };

  const handleControl = async (req: IncomingMessage, res: ServerResponse, url: string): Promise<void> => {
    const body = (await readBody(req)) as Record<string, unknown> | null;
    if (url === "/__mock__/reset") {
      state.snapshot = null;
      state.console = null;
      state.taskError = null;
      state.sseDown = false;
      state.truncateSnapshot = false;
      closeSseClients();
      sendJson(res, 200, { ok: true });
      return;
    }
    if (url === "/__mock__/truncate") {
      // Test-only: the next snapshot 200 reply drops the connection mid-body.
      state.truncateSnapshot = true;
      sendJson(res, 200, { ok: true });
      return;
    }
    if (url === "/__mock__/snapshot") {
      const payload = body?.snapshot;
      if (!validateSnapshot(payload)) {
        sendJson(res, 422, { ok: false, errors: validateSnapshot.errors });
        return;
      }
      state.snapshot = payload as Record<string, unknown>;
      sendJson(res, 200, { ok: true });
      return;
    }
    if (url === "/__mock__/console") {
      const payload = body?.console;
      if (!validateConsole(payload)) {
        sendJson(res, 422, { ok: false, errors: validateConsole.errors });
        return;
      }
      state.console = payload as Record<string, unknown>;
      sendJson(res, 200, { ok: true });
      return;
    }
    if (url === "/__mock__/event") {
      const payload = body?.event;
      if (!validateEvent(payload)) {
        sendJson(res, 422, { ok: false, errors: validateEvent.errors });
        return;
      }
      for (const client of state.sseClients) {
        sendEventFrame(client, payload as Record<string, unknown>);
      }
      sendJson(res, 200, { ok: true, delivered: state.sseClients.size });
      return;
    }
    if (url === "/__mock__/raw-event") {
      // Test-only hook: write an unvalidated raw SSE frame so browser tests
      // can drive protocol-error handling (malformed JSON / schema drift).
      const frame = body?.frame;
      if (typeof frame !== "string" || frame.length === 0) {
        sendJson(res, 422, { ok: false, error: "frame must be a non-empty string" });
        return;
      }
      for (const client of state.sseClients) {
        client.write(frame.endsWith("\n\n") ? frame : `${frame}\n\n`);
      }
      sendJson(res, 200, { ok: true, delivered: state.sseClients.size });
      return;
    }
    if (url === "/__mock__/sse") {
      state.sseDown = body?.down === true;
      if (state.sseDown) {
        closeSseClients();
      }
      sendJson(res, 200, { ok: true });
      return;
    }
    if (url === "/__mock__/task-error") {
      const payload = body?.envelope ?? null;
      if (payload !== null && !validateError(payload)) {
        sendJson(res, 422, { ok: false, errors: validateError.errors });
        return;
      }
      state.taskError = payload as Record<string, unknown> | null;
      sendJson(res, 200, { ok: true });
      return;
    }
    sendJson(res, 404, { ok: false, error: `unknown control route ${url}` });
  };

  return {
    name: "mock-backend",
    apply: "serve",
    configureServer(server) {
      if (process.env.DASHBOARD_MOCK_BACKEND !== "1") {
        return;
      }
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? "").split("?")[0] ?? "";
        if (url.startsWith("/api/v1/")) {
          handleApi(req, res, url);
          return;
        }
        if (url.startsWith("/__mock__/")) {
          handleControl(req, res, url).catch((error: unknown) => {
            sendJson(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) });
          });
          return;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [contractFixturesPlugin(), mockBackendPlugin()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    fs: { allow: [frontendRoot, contractsRoot] },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: false,
      },
    },
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
