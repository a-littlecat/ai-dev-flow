# ai-dev-flow

[中文](README.md)

A reusable AI-assisted development workflow for solo developers who want coding agents to work on real projects without turning the repo into a mystery box.

`ai-dev-flow` is a Markdown-first Skill that helps Codex, Claude Code, Gemini CLI, Cursor, DeepSeek, and other coding agents manage long-running software work with clear task files, Git baselines, diff reviews, validation evidence, and human acceptance decisions.

The goal is simple: let AI move faster, but keep the project understandable, reviewable, and under your control.

## Why This Exists

AI coding agents are excellent at making changes, but long-running projects need more than code edits.

Without a workflow, it is easy to lose track of:

- what task the agent is doing;
- which files were supposed to change;
- what diff belongs to which task;
- whether a task was reviewed or only "looked done";
- what the human actually needs to verify;
- whether multiple agents are about to edit the same module;
- when it is safe to merge.

`ai-dev-flow` turns those fuzzy moments into explicit project files and reusable checklists.

## What You Get

- Task decomposition for long-running solo projects.
- A `TASK_BOARD` and per-task Markdown records.
- Git baseline and precheck rules.
- A/B/C/D task risk levels.
- Branch / Worktree guidance without forcing every tiny task into a branch.
- Diff-based code review instead of vague file reading.
- Review severity levels: `P0 / P1 / P2 / P3`.
- User action levels: `UA0` through `UA7`.
- Batch flow for small A/B tasks.
- Parallel Wave flow for safe multi-agent scheduling.
- v0.6.0 Unreleased design-level guides for Intake, Loop Engineering, Review-Repair Loop, Roles, Project Constitution, Memory, optional GitHub Issues backend, and harness compatibility.
- Safety rules for merge, push, release, deletion, secrets, and local config.
- Prompt templates that work even in agents without native Skill support.

## Core Idea

`TASK` is always the smallest responsibility unit.

Batch, Wave, and Loop are only organization strategies:

- `Single Task`: one session works on one task.
- `Batch`: one session sequentially completes several low-risk A/B tasks.
- `Parallel Wave`: multiple sessions work on multiple non-conflicting tasks after lock and dependency checks.
- `Loop`: an outer orchestration layer for existing modes; it does not replace task state.

No Batch, Wave, or Loop is allowed to hide task boundaries. Reviews, diffs, validation, and user action levels stay per task.

## Roles Are Not Sessions

The v0.6.0 role model constrains responsibilities. It does not require one separate session for every role.

The default minimal session model is:

- Overview session: Orchestrator / Planner / Archivist.
- Execution session: Engineer / Verifier / Repairer.
- Review session: Reviewer.

One session may switch roles across different phases, but each round should declare the current role and mode. Reviewer does not repair, and Engineer / Repairer do not self-approve.

ai-dev-flow does not forbid a model or harness from automatically using subagents, including ultra mode-like internal acceleration. Subagents are optional capability, not a default dependency. Agents without subagent support can still run the workflow through Markdown, Git, and TASK files.

Read-only subagents are a good fit for review, validation, status triage, documentation checks, log cleanup, and test result summarization. Coding subagents are allowed only with boundaries: task id, role, mode, allowed scope, forbidden scope, validation method, and final Reviewer review. Parallel coding subagents require user confirmation, independent branches or Worktrees by default, lock checks, and per-task diff review. Subagents must not automatically merge, push, release, or delete.

## Who It Is For

Use this if you are a solo developer who:

- uses AI agents for real software projects;
- wants persistent task state outside chat history;
- wants AI edits to be diff-reviewable;
- wants to avoid accidental broad refactors;
- wants clear rules for when humans need to read, run, test, or decide;
- sometimes uses multiple AI sessions and needs conflict control.

It is intentionally generic. It does not assume a specific language, framework, product domain, or coding agent.

## Who It Is Not For

This is probably too much process for:

- one-off scripts;
- throwaway demos;
- quick experiments;
- pure Q&A with no project files;
- projects where you do not want Git, task records, or review checkpoints.

## Install

This repository contains the Skill at:

```text
skills/ai-dev-flow/
```

### Codex

Copy the Skill folder into your Codex skills directory:

```text
~/.codex/skills/ai-dev-flow/
```

On Windows, this is usually:

```text
C:\Users\<you>\.codex\skills\ai-dev-flow\
```

Then ask Codex:

```text
Use ai-dev-flow to initialize this project workflow.
```

You can also use Chinese trigger phrases such as:

```text
用 AI开发流程，帮我拆任务。
```

### Claude Code, Gemini CLI, Cursor, DeepSeek, or Other Agents

If your agent supports Skills or custom instruction packs, copy `skills/ai-dev-flow/` to that agent's Skill directory.

If it does not support Skills, ask the agent to read these files as plain Markdown:

```text
skills/ai-dev-flow/SKILL.md
skills/ai-dev-flow/references/WORKFLOW.md
skills/ai-dev-flow/references/PROMPTS.md
```

That is enough to use the workflow manually.

## Quick Start

### 1. Initialize a Project Workflow

```text
Use ai-dev-flow to initialize the workflow for this project.
Read the existing README, AGENTS.md, docs/, and key config files first.
Do not modify business code.
```

The agent should create or suggest a minimal structure like:

```text
docs/
├── PROJECT_INDEX.md
├── TASK_BOARD.md
├── DECISIONS.md
├── CODE_REVIEW_CHECKLIST.md
├── batches/
├── plans/
├── tasks/
└── waves/
```

Optional v0.6.0 structure for long-running projects that need Intake, Loop, Memory, or project-level hard rules. These files and folders are not required for initialization:

```text
docs/
├── intake/
├── loops/
├── memory/
└── PROJECT_CONSTITUTION.md
```

### 2. Break a Requirement Into Tasks

```text
Use ai-dev-flow to split this requirement into small tasks:
<paste requirement>
```

The agent should create task entries with goals, non-goals, validation, risk level, and execution boundaries.

### 3. Execute One Task

```text
Use ai-dev-flow to execute docs/tasks/TASK-001.md.
```

The agent should check Git status, record the base commit, follow the task boundary, update the task file, and provide validation evidence.

### 4. Review the Diff

```text
Use ai-dev-flow to review docs/tasks/TASK-001.md based on its diff.
```

The review should be based on the task diff, not a vague read-through of files.

### 5. Decide the Human Action Level

Every task should end with a clear `UA` recommendation:

- `UA0`: no user acceptance needed; agent evidence is enough.
- `UA1`: user only reads the summary.
- `UA2`: user reads the document or plan.
- `UA3`: user checks evidence, not local runtime.
- `UA4`: user runs locally.
- `UA5`: user tests in a real business environment.
- `UA6`: user performs regression acceptance.
- `UA7`: user decision required.

The agent should not simply say "needs human acceptance." It must say what the human actually needs to do.

## Batch and Parallel Wave

### Batch

Batch is for small low-risk tasks.

One execution session sequentially completes several A/B tasks, then one review session reviews them in a batch.

Rules:

- A/B tasks only.
- C/D tasks stay separate.
- The diff must stay clear and separable per task.
- A-level documentation Batch may use one commit.
- B-level small code Batch should preferably use one commit per TASK; if not, record per-task diff ownership.
- If multiple B-level tasks modify the same file, split them by default or require explicit user confirmation.
- Review must output a conclusion for every task.

### Parallel Wave

Parallel Wave is for safe parallel execution.

Multiple sessions work on multiple non-conflicting tasks after checking:

- expected modified files;
- affected modules;
- dependencies;
- file locks;
- module locks;
- task risk level;
- user action level.

Rules:

- Parallel execution is not automatic.
- The user must confirm it.
- D-level and `UA5 / UA6 / UA7` code tasks do not enter code parallelism by default.
- Code tasks in a Parallel Wave should use an independent branch or Worktree by default.
- Multiple code execution sessions must not share the same workspace by default.
- Review Hub may review a Wave, but must output per-task conclusions.

## v0.6.0 Unreleased: Design-Level Guides

v0.6.0 adds Markdown-first design-level workflow guides for:

- Intake before task creation.
- Loop Engineering for triage, goal, review-repair, and status loops.
- Review-Repair Loop with bounded repair rounds.
- Role Guide for Orchestrator, Planner, Engineer, Reviewer, Verifier, Repairer, and Archivist.
- Project Constitution using MUST / SHOULD / MUST NOT rules.
- Memory under `docs/memory/`.
- Optional GitHub Issues backend mapping without automatic sync.
- Harness compatibility for Codex, Claude Code, Cursor, Gemini CLI, DeepSeek, and generic agents.

These are documents, templates, prompts, and roadmap notes. They do not mean ai-dev-flow now has automatic scripts, automatic GitHub sync, automatic subagent scheduling, automatic multi-agent scheduling, automatic merge, or automatic release.

## Repository Structure

```text
ai-dev-flow/
├── README.md
├── skills/
│   └── ai-dev-flow/
│       ├── SKILL.md
│       ├── README.md
│       ├── CHANGELOG.md
│       ├── VERSION
│       ├── references/
│       └── scripts/
└── .gitignore
```

The root `README.md` is the public project introduction.

The Skill's detailed manual is here:

```text
skills/ai-dev-flow/README.md
```

## Important Safety Defaults

`ai-dev-flow` is intentionally conservative:

- no automatic merge;
- no automatic push;
- no automatic release;
- no blind `git add .`;
- no branch deletion without confirmation;
- no Worktree deletion without confirmation;
- no secret, local config, build artifact, dependency folder, or log submission;
- no code task without Git baseline;
- no review without a clear diff;
- no task completion claim without validation evidence.

## Version

Current Skill version:

```text
0.5.2
```

`0.6.0` is currently tracked as an Unreleased documentation upgrade in `skills/ai-dev-flow/CHANGELOG.md`.

See:

```text
skills/ai-dev-flow/CHANGELOG.md
```

## License

This project is released under the MIT License.

See:

```text
LICENSE
```

## Contributing

Issues and pull requests are welcome.

Good contributions should keep the workflow:

- generic;
- Markdown-first;
- agent-neutral;
- Git-aware;
- safe by default;
- clear about human confirmation;
- free of project-specific business rules.
