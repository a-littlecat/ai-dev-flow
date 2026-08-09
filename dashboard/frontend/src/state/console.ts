import type { ProjectConsole } from "../generated/contracts.types";
import type { ApiFailure } from "../api/client";

export interface ConsoleState {
  status: "idle" | "loading" | "ready" | "stale" | "error";
  data: ProjectConsole | null;
  etag: string | null;
  message: string | null;
}

export function initialConsoleState(): ConsoleState {
  return { status: "idle", data: null, etag: null, message: null };
}

export function consoleFailureMessage(failure: ApiFailure): string {
  if (failure.kind === "network") {
    return `Project Console 无法连接本地 API（${failure.message}），正在保留上次数据。`;
  }
  if (failure.kind === "schema") {
    return `Project Console 响应未通过合同校验：${failure.error.message}`;
  }
  return failure.error
    ? `Project Console API ${failure.error.error.code}：${failure.error.error.message}`
    : `Project Console API 返回 HTTP ${failure.status}`;
}
