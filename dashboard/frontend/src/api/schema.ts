/**
 * Strict runtime validation of every API message against the versioned
 * contract schema (dashboard/contracts/dashboard-contracts-v1.schema.json).
 * The schema uses `additionalProperties: false` throughout, so any
 * undocumented field, missing field or enum drift is rejected here instead of
 * being silently consumed.
 */
import type { ErrorObject, ValidateFunction } from "ajv";
import type {
  DashboardSnapshot,
  ErrorEnvelope,
  Health,
  SnapshotEvent,
  TaskDetail,
} from "../generated/contracts.types";
import {
  validateDashboardSnapshot,
  validateErrorEnvelope,
  validateHealth,
  validateSnapshotEvent,
  validateTaskDetail,
} from "../generated/contracts.validators";

const validators = {
  DashboardSnapshot: validateDashboardSnapshot as ValidateFunction<DashboardSnapshot>,
  TaskDetail: validateTaskDetail as ValidateFunction<TaskDetail>,
  Health: validateHealth as ValidateFunction<Health>,
  ErrorEnvelope: validateErrorEnvelope as ValidateFunction<ErrorEnvelope>,
  SnapshotEvent: validateSnapshotEvent as ValidateFunction<SnapshotEvent>,
} as const;

export type ContractKind = keyof typeof validators;

export class SchemaViolationError extends Error {
  readonly kind: ContractKind;
  readonly issues: ErrorObject[];

  constructor(kind: ContractKind, issues: ErrorObject[]) {
    super(
      `schema validation failed for ${kind}: ` +
        issues
          .slice(0, 5)
          .map((issue) => `${issue.instancePath || "/"} ${issue.message ?? "invalid"}`)
          .join("; "),
    );
    this.name = "SchemaViolationError";
    this.kind = kind;
    this.issues = issues;
  }
}

/** Validate an unknown payload against a contract message type, or throw. */
export function validateContract<T>(kind: ContractKind, payload: unknown): T {
  const fn = validators[kind];
  if (!fn(payload)) {
    throw new SchemaViolationError(kind, fn.errors ? [...fn.errors] : []);
  }
  return payload as T;
}

/** Validate an error envelope; returns null when the payload is not one. */
export function tryParseErrorEnvelope(payload: unknown): ErrorEnvelope | null {
  try {
    return validateContract<ErrorEnvelope>("ErrorEnvelope", payload);
  } catch {
    return null;
  }
}
