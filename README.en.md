# ai-dev-flow

[中文](README.md)

A risk-activated workflow for AI-assisted software development. It uses project rules, Git/diff, deterministic validation, and task records when they add value without forcing the full process onto every small change.

The v0.8 behavior is simple:

- low-risk work exits the Skill and proceeds with project rules and validation;
- work that needs durable evidence uses a Tracked TASK;
- high-risk, real-environment, or delivery work uses Controlled governance and mandatory review at enforcement points.

## Why v0.8

Earlier releases could govern complex projects, but their default documentation and prompt surface became too large. With frontier models, that can consume context, add Reviewer calls, and interrupt users without improving the result.

The v0.8 default runtime is only:

```text
skills/ai-dev-flow/SKILL.md
skills/ai-dev-flow/references/CORE.md
```

All other guides remain available on demand.

## Routing outcomes

| Outcome | Use when | Default behavior |
|---|---|---|
| `DoNotUseSkill` | Low risk, one session, few files, complete deterministic validation | No TASK, Reviewer, or repair loop |
| `Tracked` | Cross-session work, broader scope, or durable evidence is needed | TASK; read-only Reviewer only when risk flags trigger |
| `Controlled` | Class D, high-risk, real-environment, delivery, or irreversible actions | Full TASK; mandatory independent Review at enforcement points |
| `Blocked` | Input, authority, capability, or evidence is missing | Stop and report the minimum blocking information |

The exact rules have one source: `references/CORE.md` → `POLICY_JSON`.

## Quick start

Install `skills/ai-dev-flow/` in the agent's Skill directory, then ask:

```text
Use ai-dev-flow for this task. First route it to DoNotUseSkill, Tracked, Controlled, or Blocked.
```

A Skill-capable agent reads only `SKILL.md + CORE.md` by default. Projects without Skill support can merge the minimal rules from `references/AGENTS_COMPAT.md` into their existing `AGENTS.md`.

## What remains core

- User intent and project rules take precedence.
- Git state, base commit, diff ownership, and rollback boundaries.
- TASK as the source of truth for Tracked and Controlled work.
- Validation evidence covering completion criteria.
- Authority, real-environment, sensitive-data, and side-effect gates.
- An isolated, read-only Reviewer when policy requires it.
- Separate Review, UA, Accepted, commit, merge, release, and Closed states.

## What leaves the default path

These materials remain compatible but are no longer loaded by default:

- the long prompt library;
- Batch, Parallel Wave, and general Loop orchestration;
- Memory, Project Constitution, and role declarations;
- provider and harness branches;
- universal Reviewer calls and unconditional repair loops.

v0.8 does not add a scheduler, database, telemetry, billing, or model adapter. It never auto-merges, pushes, releases, deletes, or performs external synchronization.

## TASK and v0.7 compatibility

- Lite creates no TASK.
- New Tracked or Controlled work uses `references/TASK_TEMPLATE.md`.
- Existing TASK files keep their format and are not batch-migrated.
- `TASK_TEMPLATE_COMPACT.md` remains only for v0.7 Writer/Reader compatibility.
- The Skill package is `0.8.0`; the Workflow Contract schema remains `adf/v0.7.0`.

See `skills/ai-dev-flow/references/V0.8_MIGRATION.md` for the migration guide.

## Reviewer and the third repair round

- Tracked uses one isolated, read-only Reviewer only when deterministic risk flags trigger.
- Controlled requires Review before acceptance recommendation, delivery, merge, and release.
- The repair budget starts at two rounds. A third round is allowed only when all progress conditions pass.
- Three is the absolute maximum. Changing models does not reset the budget, and external side effects are never automatically retried.

## Read-only checks

The v0.7 standard-library Reader, `workflow_lint`, and TASK_BOARD drift checks remain available:

```powershell
python skills/ai-dev-flow/scripts/workflow_lint.py docs/tasks/TASK-001.md --format human
python skills/ai-dev-flow/scripts/workflow_lint.py . --format human
```

A passing lint result does not imply Review, UA, merge, release, or task closure.

## Repository layout

```text
ai-dev-flow/
├── README.md
├── README.en.md
├── docs/
├── evaluations/v0.8/
└── skills/ai-dev-flow/
    ├── SKILL.md
    ├── VERSION
    ├── references/
    ├── scripts/
    └── tests/
```

See `skills/ai-dev-flow/README.md` for the detailed Chinese guide.

## Current version

```text
0.8.0
```

- Current release candidate: `0.8.0`.
- Workflow Contract: `adf/v0.7.0`, still compatible.
- Release status: the repository `v0.8.0` tag and GitHub Release are the authoritative publication evidence.
- The historical v0.7.0 tag remains unchanged.

See `skills/ai-dev-flow/CHANGELOG.md` for changes.

## License

MIT License. See [LICENSE](LICENSE).
