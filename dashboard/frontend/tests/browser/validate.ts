/**
 * Node-side contract validation for Playwright tests. Loads the same
 * versioned schema file as src/api/schema.ts (via fs, because Playwright's
 * module loader cannot resolve JSON imports outside the package root) and
 * exposes the same validateContract semantics against the same $defs.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import type { ErrorObject, ValidateFunction } from "ajv";

const SCHEMA_ID = "ai-dev-flow/dashboard-contracts/v1";
const SCHEMA_PATH = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../contracts/dashboard-contracts-v1.schema.json",
);

const ajv = new Ajv2020({ allErrors: true, strict: true });
ajv.addSchema(JSON.parse(readFileSync(SCHEMA_PATH, "utf-8")) as object, SCHEMA_ID);

function validator<T>(def: string): ValidateFunction<T> {
  const fn = ajv.getSchema<T>(`${SCHEMA_ID}#/$defs/${def}`);
  if (!fn) {
    throw new Error(`contract schema is missing $defs.${def}`);
  }
  return fn;
}

const validators = {
  DashboardSnapshot: validator("DashboardSnapshot"),
  TaskDetail: validator("TaskDetail"),
  Health: validator("Health"),
  ErrorEnvelope: validator("ErrorEnvelope"),
  SnapshotEvent: validator("SnapshotEvent"),
  ProjectConsole: validator("ProjectConsole"),
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
