# ai-dev-flow

[中文](README.md)

`ai-dev-flow` is a development-flow skill for AI coding assistants such as Claude Code and Codex. You talk only to its hub. You say what you want, look at results and make the key decisions. The hub handles tiering, tasks, verification, independent review, merging and records.

It is built for frontier models and has two goals:

- **Keep the key safeguards.** Nothing is called done without evidence. Product code is reviewed read-only by a different model. Merges, releases and other actions that need your authorization are confirmed first.
- **Spare your attention.** The hub decides what it can by itself. When it must ask, it asks everything in one message. Reports are three lines.

## Layout

```
skills/ai-dev-flow/
  SKILL.md              hub (the only entry)
  VERSION
  modules/plan.md       planning and tasks
  modules/diagnose.md   diagnosis: define a pass/fail signal before fixing
  modules/review.md     independent review: request, output format, handling findings
  modules/ship.md       merge and landing
  modules/compound.md   capturing lessons and handoff
```

The modules are not separate skills. The hub reads only the one it needs at the moment.

## Usage

In daily work you mostly say one of these:

| You say | The hub |
|---|---|
| Build X / fix Y | picks a tier and works until it needs you |
| Continue | does the next step |
| Where are we? | gives a three-line report |
| Accepted / merge it | merges and lands the work |
| That's wrong / it errors | classifies first, then diagnoses |
| Stop | stops at a safe point and writes a handoff |

It interrupts you only in four cases:

- a direction must be chosen
- something needs your eyes
- an action needs your authorization (merge, push, release, deletion)
- it is stuck

When it does, it asks everything at once and recommends an answer for each question.

### Tiers

| Tier | When | Flow |
|---|---|---|
| Direct | Q&A, docs, small style tweaks, validation scripts, local fixes | change → verify → report |
| Standard | product code, interfaces, build config, or multi-session work | plan → worktree → tiered verification → independent review → merge → capture lessons |
| High risk | packaging and releases, writing user files, real business data, migrations, irreversible actions | the standard flow, plus a confirmed plan, full verification and user acceptance |

A project's own `AGENTS.md` can override tiers, verification commands and the review setup. Two lines are recommended there:

- a rule that all development requests go through the `ai-dev-flow` hub;
- the project facts: verification commands, who does what, merge authorization and project-specific skills.

## Install

Copy `skills/ai-dev-flow/` to `~/.agents/skills/ai-dev-flow/`, which is the user-level skill directory for Codex.

Claude Code's user-level skill directory is `~/.claude/skills/` (project-level `.claude/skills/` also works). Add a directory junction that points at the same files (no admin rights needed on Windows):

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-dev-flow" -Target "$env:USERPROFILE\.agents\skills\ai-dev-flow"
```

For other tools, install into their own skill directory. Don't put two copies of the same skill where one tool scans both locations, or it will appear twice in the skill list.

## Versions

- **1.0.0** (2026-10-15): rewritten as one hub plus five modules. The old repair counters and receipts, Lite / Tracked / Controlled routing, UA0–UA7 levels, `workflow_lint` and the Dashboard are gone.
- **0.9.2 and earlier**: the complete old version (Dashboard, lint, repair gate, references and tests) is at tag [`v0.9.2`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9.2). The last state of the v0.9 line is at tag [`v0.9-final`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9-final).

## License

[MIT](LICENSE)
