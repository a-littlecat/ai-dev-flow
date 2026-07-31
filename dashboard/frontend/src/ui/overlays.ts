/**
 * Global overlays: loading / error / disconnected banners, stale-source
 * strip, diagnostics drawer and the aria-live announcer.
 *
 * Everything is normal document flow: banners and strips are full-width
 * bars between the status bar and the workspace (`root`), the diagnostics
 * drawer is a footer after the workspace (`drawerRoot`). No `position:
 * fixed` anywhere — a fixed element inside a transformed ancestor gets a
 * wrong containing block, and any overlay can cover graph content.
 */
import type { AppState } from "../state/store";
import type { Diagnostic } from "../generated/contracts.types";
import { el, clear } from "./dom";
import { SEVERITY_ICON, SEVERITY_LABEL } from "./labels";

const TASK_INGESTION_ERROR_CODES = new Set([
  "E_PARSE",
  "E_TASK_ID_CONFLICT",
  "E_UNKNOWN_VALUE",
  "E_LEGACY_CONFLICT",
]);

export class Overlays {
  /** Banner/strip container, mounted directly under the status bar. */
  readonly root: HTMLElement;
  /** Diagnostics drawer container, mounted after the workspace. */
  readonly drawerRoot: HTMLElement;
  readonly liveRegion: HTMLElement;
  private diagDrawerOpen = false;
  /** Content key of the rendered drawer; DOM persists while it is unchanged. */
  private diagKey: string | null = null;
  private diagToggle: HTMLButtonElement | null = null;
  private diagList: HTMLUListElement | null = null;

  constructor(private readonly onRetry: () => void) {
    this.root = el("div", "overlay-layer");
    this.drawerRoot = el("div", "diag-drawer-slot");
    this.liveRegion = el("div", "visually-hidden");
    this.liveRegion.setAttribute("aria-live", "polite");
    this.liveRegion.setAttribute("role", "status");
  }

  announce(message: string): void {
    this.liveRegion.textContent = message;
  }

  update(state: AppState): void {
    clear(this.root);

    if (state.phase === "loading" && !state.snapshot) {
      this.root.append(el("div", "overlay-banner overlay-loading", "正在加载本地任务快照…"));
      this.updateDrawer(null);
      return;
    }

    if (state.phaseError) {
      const banner = el("div", "overlay-banner overlay-error");
      banner.setAttribute("role", "alert");
      banner.append(el("span", null, state.phaseError));
      const retry = el("button", "overlay-retry", "重试");
      retry.type = "button";
      retry.addEventListener("click", this.onRetry);
      banner.append(retry);
      this.root.append(banner);
    }

    const snapshot = state.snapshot;
    if (snapshot) {
      const ingestionDiagnostics = snapshot.diagnostics.filter((diagnostic) =>
        TASK_INGESTION_ERROR_CODES.has(diagnostic.code),
      );
      if (ingestionDiagnostics.length > 0) {
        const totalErrors = snapshot.summary.counts_by_severity.error;
        const notice = el(
          "div",
          "overlay-banner task-ingestion-notice",
          `当前共检测到 ${totalErrors} 条错误，其中 ${ingestionDiagnostics.length} 条属于 TASK 解析或 Contract 不兼容错误，可能导致部分任务未纳入关系图；当前显示 ${snapshot.summary.task_total} 个已解析任务。请展开底部“诊断”查看具体原因。`,
        );
        notice.setAttribute("role", "status");
        this.root.append(notice);
      }
    }

    if (snapshot && snapshot.state !== "fresh") {
      const strip = el("div", `overlay-strip stale-strip-${snapshot.state}`);
      const reasons: string[] = [];
      if (snapshot.stale_sources.length > 0) {
        reasons.push(`过期来源：${snapshot.stale_sources.map((s) => s.source_path).join("、")}`);
      }
      const related = snapshot.diagnostics.filter((d) => d.severity === "error" || d.severity === "warning");
      if (related.length > 0) {
        reasons.push(related.map((d) => `${d.code}`).join("、"));
      }
      strip.append(
        el(
          "span",
          null,
          snapshot.state === "stale"
            ? `当前为过期快照（保留 last-known-good）。${reasons.join(" ｜ ")}`
            : `当前为不完整快照（部分来源不可用或解析失败）。${reasons.join(" ｜ ")}`,
        ),
      );
      this.root.append(strip);
    }

    this.updateDrawer(snapshot && snapshot.diagnostics.length > 0 ? snapshot.diagnostics : null);
  }

  /**
   * Incremental diagnostics drawer: the toggle and list keep their DOM
   * identity while the diagnostics are unchanged, so keyboard/screen-reader
   * focus and the expanded state survive snapshot and connection updates.
   */
  private updateDrawer(diagnostics: Diagnostic[] | null): void {
    if (!diagnostics) {
      if (this.diagKey !== null) {
        clear(this.drawerRoot);
        this.diagKey = null;
        this.diagToggle = null;
        this.diagList = null;
      }
      return;
    }
    const key = JSON.stringify(diagnostics);
    if (key === this.diagKey && this.diagToggle && this.diagList) {
      // Unchanged content: only re-affirm the expanded state.
      this.diagList.hidden = !this.diagDrawerOpen;
      this.diagToggle.setAttribute("aria-expanded", String(this.diagDrawerOpen));
      return;
    }
    const refocusToggle = document.activeElement !== null && this.drawerRoot.contains(document.activeElement);
    clear(this.drawerRoot);
    const drawer = el("div", "diag-drawer");
    const toggle = el(
      "button",
      "diag-drawer-toggle",
      `${this.diagDrawerOpen ? "▾" : "▸"} 诊断（${diagnostics.length}）`,
    );
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", String(this.diagDrawerOpen));
    const list = el("ul", "diag-drawer-list") as HTMLUListElement;
    list.hidden = !this.diagDrawerOpen;
    toggle.addEventListener("click", () => {
      this.diagDrawerOpen = !this.diagDrawerOpen;
      toggle.textContent = `${this.diagDrawerOpen ? "▾" : "▸"} 诊断（${diagnostics.length}）`;
      list.hidden = !this.diagDrawerOpen;
      toggle.setAttribute("aria-expanded", String(this.diagDrawerOpen));
    });
    for (const diag of diagnostics) {
      list.append(
        el(
          "li",
          `diag-item severity-${diag.severity}`,
          `${SEVERITY_ICON[diag.severity] ?? ""} ${SEVERITY_LABEL[diag.severity] ?? diag.severity} ｜ ${diag.code}：${diag.message}${diag.task_ids.length > 0 ? `（任务：${diag.task_ids.join("、")}）` : ""}`,
        ),
      );
    }
    drawer.append(toggle, list);
    this.drawerRoot.append(drawer);
    this.diagKey = key;
    this.diagToggle = toggle;
    this.diagList = list;
    // Content actually changed and the drawer had focus: return it to the
    // toggle (the only focusable drawer control) instead of dropping it.
    if (refocusToggle) {
      toggle.focus();
    }
  }
}
