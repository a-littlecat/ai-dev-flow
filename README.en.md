# ai-dev-flow

[中文](README.md)

`ai-dev-flow` is a development-flow skill for AI coding assistants such as Claude Code and Codex. You talk only to its hub, and you own three things: **direction** (what you want), **taste** (whether results that need a human eye are right) and **one-way doors** (whether to do things that can't be undone). The hub handles building, proving, independent verification, merging and the retrospective.

v2 puts quality on machines rather than on process and questions:

- **The project's own verification.** One verify command decides pass or fail and can drive the real product. If the project has none, the hub helps build it first.
- **Mechanical constraints.** Anything that must happen every time becomes a hook, a test or a lint.
- **Regular retrospectives.** Once a batch has landed, the hub reviews what was merged; problems that keep recurring are promoted into rules.

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
  modules/garden.md        retrospective, lesson promotion, retro digest, cleanup
  modules/portfolio.md     several projects at once: project list, status page and notifications, inbox, weekly review, cross-project lessons
  scripts/dispatch.ps1     hand an item to an external CLI agent (Codex, DSH, ...) to build or review
  scripts/status.ps1       collect every project's status from the portfolio repo's project list (read-only)
  scripts/daily.ps1        write the status as one HTML page and send a notification; meant for a scheduled task
  scripts/notify.ps1       desktop notification; things that need you also go to your phone (Bark)
  scripts/watch.ps1        stall check every 15 minutes; only projects that newly stalled go to your phone
skills/next/SKILL.md       /next: in a project, work through the queue item after item until you are needed, then wrap up and notify
skills/week/SKILL.md       /week: the weekly review, in the portfolio repo
tests/status.tests.ps1     checks for status.ps1, daily.ps1, notify.ps1 and watch.ps1: pwsh -NoProfile -File tests/status.tests.ps1
```

The modules are not separate skills. The hub reads only the one it needs at the moment.

## Usage

In daily work you mostly say one of these:

| You say | The hub |
|---|---|
| `/next` (optionally with an answer, e.g. `/next #7 go with yours`) | works through the queue item after item (build, verify, merge) and wraps up with a notification when it needs you |
| Build X / fix Y | picks a tier and works until it needs you |
| Continue / keep going | carries on, or works through the queue one item after another |
| Where are we? | gives a three-line report |
| OK / merge it | merges and lands the work |
| That's wrong / it errors | classifies first, then diagnoses |
| Retro | reviews recent merges and gives you a retro digest |
| Stop | stops at a safe point and writes what's left into the queue |
| `/week`, weekly review (in the portfolio repo) | collects every project's week and proposes next week's goals |

It interrupts you only in four cases:

- a one-way door needs your authorization
- something needs your eyes
- a direction must be chosen
- it is stuck

When it does, it asks everything at once and recommends an answer for each question.

### Tiers: can it be undone × can a machine prove it

| Tier | When | Who decides |
|---|---|---|
| Autonomous | reversible, and verify can prove it right or wrong | merged according to the trust level, listed in the retro digest |
| Take a look | reversible, but correctness needs a human eye (UI, copy, feel) | done with screenshots attached; waits for your OK |
| One-way door | push and release, real data, deletion, sending anything out, spending money, security settings, touching software you're using | plan confirmed first; runs only with your authorization |

### Trust levels

Each project records one level in its `AGENTS.md`. You change it; the agent can only suggest a change, with data, in the retro digest. With no level set, L0 applies.

| Level | How autonomous work is merged | Parallel limit |
|---|---|---|
| L0 | asks you every time | 2 |
| L1 | each item verified on its own, stacked, and you merge a batch at once | 3 |
| L2 | the agent merges to trunk; you spot-check afterwards | 5 |
| L3 | scheduled jobs pick work from the queue | set by budget |

Two lines are recommended in the project's `AGENTS.md`:

- a rule that all development requests go through the `ai-dev-flow` hub;
- the project facts: verify command, trust level, how the north-star number is measured, extra one-way doors, budget and prohibitions.

### Several projects at once

There are no long-running sessions. In a project you open a new session and type `/next`; it works through the queue item after item and wraps up only when it needs you, is stuck, runs low on quota or has finished 5 items. Progress lives in the queue, so any account or any new session can pick it up. Add one local-only portfolio repository that holds your intent (`INTENT.md`), the project list (`projects.json`, including this week's goals), a decision log and cross-project lessons:

- **Daily**: a scheduled task runs `scripts/daily.ps1`, which writes one status page (what needs you, which projects have free work, each project's goals and progress) and sends a notification that opens it. No model usage.
- **In between**: every session sends a notification when it wraps up; when it needs you or is stuck, the notification also goes to your phone. Questions about a project are answered in that project (`/next #id <answer>`).
- **Weekly**: type `/week` in the portfolio repo to review the week and set next week's goals. A lesson that shows up in several projects is promoted into the skill or user-level config.

See `modules/portfolio.md`.

## Install

Copy the three directories under `skills/` (`ai-dev-flow`, `next`, `week`) to `~/.agents/skills/`, which is the user-level skill directory for Codex.

Claude Code's user-level skill directory is `~/.claude/skills/` (project-level `.claude/skills/` also works). Add one directory junction per skill that points at the same files (no admin rights needed on Windows):

```powershell
foreach ($n in 'ai-dev-flow', 'next', 'week') {
    New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\$n" -Target "$env:USERPROFILE\.agents\skills\$n"
}
```

Notifications and the status page (optional):

- To reach your phone, write `%APPDATA%\ai-dev-flow\notify.json` locally (never commit it): `{ "bark": "https://api.day.app/<key>", "barkLevels": ["user", "stuck"] }`. Without it, only desktop notifications are shown.
- To be notified when a session waits for a permission or for input, add the command `pwsh -NoProfile -File <full path of ~/.agents/skills/ai-dev-flow>/scripts/notify.ps1 -Hook` under `hooks.Notification` in `~/.claude/settings.json`.
- For the daily status page, have Windows Task Scheduler run `pwsh -NoProfile -File <same path>/scripts/daily.ps1 -Config <portfolio repo>\projects.json`.
- For stall alerts, also have it run `pwsh -NoProfile -File <same path>/scripts/watch.ps1 -Config <portfolio repo>\projects.json` every 15 minutes.

For other tools, install into their own skill directory. Don't put two copies of the same skill where one tool scans both locations, or it will appear twice in the skill list.

## Upgrading from v1

- New work no longer creates TASK files or a board. Evidence goes into commit bodies; to-dos go into a queue (issues or `docs/queue.md`). Existing TASK files and boards stay as they are.
- Merges no longer ask you every time by default; the project's trust level decides. With no level set, L0 applies, which behaves like v1.
- Cross-vendor review is required only for one-way doors. Other tiers may use a same-vendor subagent that is not lower-tier than the executor.
- `plan.md`, `review.md`, `ship.md` and `compound.md` are replaced by `build.md`, `verify.md`, `land.md` and `garden.md`.

## Versions

- **2.4.1** (2026-11-01): `/next` no longer wraps up after one context compaction: it rereads the project's `AGENTS.md`, the queue and the `/next` rules, then carries on; it wraps up after the second compaction.
- **2.4.0** (2026-11-01): fewer notifications, stalls caught sooner. `notify.ps1 -Hook` now looks at the event type: the "waiting for your input" reminder after a minute of no input is dropped, and a session that failed to resume after the usage limit reset goes to your phone. New `scripts/watch.ps1`, run every 15 minutes by a scheduled task, pushes to your phone only when a project newly looks stalled.
- **2.3.0** (2026-11-01): `/next` keeps going by default: when an item is done it takes the next one; when an item needs you it notifies you first and carries on with work that doesn't depend on the answer. It wraps up when nothing is left to take, after 5 items, when quota runs low or when the context gets long. The retrospective is a quick step before starting work instead of taking a whole session, and review, fixes, re-review and merge of one item all happen in the same session. `/next 连做` is replaced by `/next 只做一项` (one item only).
- **2.2.0** (2026-11-01): day-to-day work becomes "one item per session". New `/next` and `/week` entries; no more long-running lead sessions, portfolio session or nightly scheduled tasks. Work handed to other agents is awaited inside the session, and every wrap-up updates the queue and sends a notification. New `scripts/daily.ps1` (status page plus notification, for a scheduled task) and `scripts/notify.ps1` (desktop notifications plus Bark push). `status.ps1` adds last activity, available items, this week's goals and a "may have stalled" hint. Retrospectives now run when 20 commits or 7 days have piled up, triggered by `/next`; the daily digest is now the retro digest.
- **2.1.0** (2026-10-31): new `portfolio` module (several projects at once: project list, one inbox with a global cap, merged digest, cross-project lesson promotion) and a read-only status script, `scripts/status.ps1`. Related projects agree on a contract before building, and the contract tests live in the provider's verify. The daily digest is also written to `.agents/digest/`, and approval prompts that keep recurring get a concrete permission-rule suggestion. The dispatch script `scripts/dispatch.ps1`, added after 2.0.0, is counted in this release.
- **2.0.0** (2026-10-29): reorganized around "harness + loops". Tiers are now based on reversibility × verifiability. New trust levels L0–L3. New `harness` (project verification) and `garden` (nightly retrospective, lesson promotion) modules. Evidence moves into commit bodies. Independent verification reports only provable P0–P2 findings. A red trunk after a merge is fixed forward or reverted.
- **1.1.0** (2026-10-18): new auto-advance module (background subagents in worktrees; a project can authorize merging after verification). The review module adds a fallback order for when the preferred reviewer is unavailable; the reviewer model must not be lower-tier than the executor.
- **1.0.0** (2026-10-15): rewritten as one hub plus five modules. The old repair counters and receipts, Lite / Tracked / Controlled routing, UA0–UA7 levels, `workflow_lint` and the Dashboard are gone.
- **0.9.2 and earlier**: the complete old version (Dashboard, lint, repair gate, references and tests) is at tag [`v0.9.2`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9.2). The last state of the v0.9 line is at tag [`v0.9-final`](https://github.com/a-littlecat/ai-dev-flow/tree/v0.9-final).

## License

[MIT](LICENSE)
