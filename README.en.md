# ai-dev-flow

[中文](README.md)

`ai-dev-flow` is a development-flow skill for AI coding assistants such as Claude Code and Codex. You talk only to its hub, and you own three things: **direction** (what you want), **taste** (whether results that need a human eye are right) and **one-way doors** (whether to do things that can't be undone). The hub handles building, proving, independent verification, merging and the daily retrospective.

v2 puts quality on machines rather than on process and questions:

- **The project's own verification.** One verify command decides pass or fail and can drive the real product. If the project has none, the hub helps build it first.
- **Mechanical constraints.** Anything that must happen every time becomes a hook, a test or a lint.
- **A daily retrospective.** The hub reviews what was merged; problems that keep recurring are promoted into rules.

For reversible work the hub doesn't stop to ask "should I?". It does the work, shows the result, and you can overrule it afterwards. Research and design notes (in Chinese) are in [docs/v2-design.md](docs/v2-design.md).

## Layout

```
skills/ai-dev-flow/
  SKILL.md                 hub (the only entry): tiers, trust levels, when to ask you, reports
  VERSION
  modules/harness.md       build the project's verification: verify, driving the product, feature map, hooks, slow-check queue
  modules/build.md         understand → build → prove (including breaking it on purpose)
  modules/verify.md        independent verification: only provable findings, cross-vendor rules
  modules/land.md          merging: commit-body template, fix forward or revert
  modules/diagnose.md      diagnosis: define a pass/fail signal before fixing
  modules/orchestrate.md   auto-advance: queue, background subagents in worktrees, parallel limits
  modules/garden.md        nightly retrospective, lesson promotion, daily digest, weekly cleanup
```

The modules are not separate skills. The hub reads only the one it needs at the moment.

## Usage

In daily work you mostly say one of these:

| You say | The hub |
|---|---|
| Build X / fix Y | picks a tier and works until it needs you |
| Continue / keep going | carries on, or works through the queue one item after another |
| Where are we? | gives a three-line report |
| OK / merge it | merges and lands the work |
| That's wrong / it errors | classifies first, then diagnoses |
| Retro | reviews today's merges and gives you a daily digest |
| Stop | stops at a safe point and writes what's left into the queue |

It interrupts you only in four cases:

- a one-way door needs your authorization
- something needs your eyes
- a direction must be chosen
- it is stuck

When it does, it asks everything at once and recommends an answer for each question.

### Tiers: can it be undone × can a machine prove it

| Tier | When | Who decides |
|---|---|---|
| Autonomous | reversible, and verify can prove it right or wrong | merged according to the trust level, listed in the daily digest |
| Take a look | reversible, but correctness needs a human eye (UI, copy, feel) | done with screenshots attached; waits for your OK |
| One-way door | push and release, real data, deletion, sending anything out, spending money, security settings, touching software you're using | plan confirmed first; runs only with your authorization |

### Trust levels

Each project records one level in its `AGENTS.md`. You change it; the agent can only suggest a change, with data, in the daily digest. With no level set, L0 applies.

| Level | How autonomous work is merged | Parallel limit |
|---|---|---|
| L0 | asks you every time | 2 |
| L1 | each item verified on its own, stacked, and you merge a batch at once | 3 |
| L2 | the agent merges to trunk; you spot-check afterwards | 5 |
| L3 | scheduled jobs pick work from the queue | set by budget |

Two lines are recommended in the project's `AGENTS.md`:

- a rule that all development requests go through the `ai-dev-flow` hub;
- the project facts: verify command, trust level, how the north-star number is measured, extra one-way doors, budget and prohibitions.

## Install

Copy `skills/ai-dev-flow/` to `~/.agents/skills/ai-dev-flow/`, which is the user-level skill directory for Codex.

Claude Code's user-level skill directory is `~/.claude/skills/` (project-level `.claude/skills/` also works). Add a directory junction that points at the same files (no admin rights needed on Windows):

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-dev-flow" -Target "$env:USERPROFILE\.agents\skills\ai-dev-flow"
```

For other tools, install into their own skill directory. Don't put two copies of the same skill where one tool scans both locations, or it will appear twice in the skill list.

## Upgrading from v1

- New work no longer creates TASK files or a board. Evidence goes into commit bodies; to-dos go into a queue (issues or `docs/queue.md`). Existing TASK files and boards stay as they are.
- Merges no longer ask you every time by default; the project's trust level decides. With no level set, L0 applies, which behaves like v1.
- Cross-vendor review is required only for one-way doors. Other tiers may use a same-vendor subagent that is not lower-tier than the executor.
- `plan.md`, `review.md`, `ship.md` and `compound.md` are replaced by `build.md`, `verify.md`, `land.md` and `garden.md`.

## Versions

- **2.0.0** (2026-10-29): reorganized around "harness + loops". Tiers are now based on reversibility × verifiability. New trust levels L0–L3. New `harness` (project verification) and `garden` (nightly retrospective, lesson promotion) modules. Evidence moves into commit bodies. Independent verification reports only provable P0–P2 findings. A red trunk after a merge is fixed forward or reverted.
- **1.1.0** (2026-10-18): new auto-advance module (background subagents in worktrees; a project can authorize merging after verification). The review module adds a fallback order for when the preferred reviewer is unavailable; the reviewer model must not be lower-tier than the executor.
- **1.0.0** (2026-10-15): rewritten as one hub plus five modules. The old repair counters and receipts, Lite / Tracked / Controlled routing, UA0–UA7 levels, `workflow_lint` and the Dashboard are gone.
- **0.9.2 and earlier**: the complete old version (Dashboard, lint, repair gate, references and tests) is at tag [`v0.9.2`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9.2). The last state of the v0.9 line is at tag [`v0.9-final`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9-final).

## License

[MIT](LICENSE)
