/**
 * SSE subscription to /api/v1/events. The stream is only an invalidation
 * hint: consumers must re-read the snapshot via GET (with ETag) on every
 * event, and must fully reset local view state when `reset_required` is true.
 * Reconnection is delegated to the browser (`retry: 2000` from the server);
 * this wrapper only reports connection state.
 */
import type { SnapshotEvent } from "../generated/contracts.types";
import { validateContract } from "./schema";

export type SseStatus = "connecting" | "connected" | "reconnecting";

export interface SseCallbacks {
  onEvent(event: SnapshotEvent): void;
  onStatus(status: SseStatus): void;
  /**
   * A frame arrived but failed JSON parsing or strict contract validation.
   * The frame is dropped (local state is never polluted) and the consumer
   * must surface a visible degraded/protocol-error state and re-sync.
   */
  onProtocolError(detail: string): void;
}

export type EventSourceFactory = (url: string) => EventSource;

export class SnapshotEventStream {
  private source: EventSource | null = null;

  constructor(
    private readonly callbacks: SseCallbacks,
    private readonly factory: EventSourceFactory = (url) => new EventSource(url),
  ) {}

  start(): void {
    if (this.source) {
      return;
    }
    this.callbacks.onStatus("connecting");
    const source = this.factory("/api/v1/events");
    this.source = source;
    source.addEventListener("open", () => this.callbacks.onStatus("connected"));
    source.addEventListener("error", () => {
      // EventSource reconnects automatically using the server-provided retry.
      if (source.readyState !== EventSource.CLOSED) {
        this.callbacks.onStatus("reconnecting");
      }
    });
    source.addEventListener("snapshot", (message) => {
      const data = (message as MessageEvent).data;
      let parsed: unknown;
      try {
        parsed = JSON.parse(typeof data === "string" ? data : "");
      } catch {
        this.callbacks.onProtocolError("事件帧不是合法 JSON");
        return;
      }
      let event: SnapshotEvent;
      try {
        event = validateContract<SnapshotEvent>("SnapshotEvent", parsed);
      } catch (error) {
        // Schema drift on the stream must not corrupt local state, but it
        // must be visible — never silently ignored.
        this.callbacks.onProtocolError(error instanceof Error ? error.message : String(error));
        return;
      }
      this.callbacks.onEvent(event);
    });
  }

  stop(): void {
    if (this.source) {
      this.source.close();
      this.source = null;
    }
  }
}
