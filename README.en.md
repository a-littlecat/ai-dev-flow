# ai-dev-flow

[中文](README.md)

`ai-dev-flow` is a risk-activated governance Skill for AI-assisted development, with a read-only local task relationship Dashboard.

It keeps small tasks lightweight while applying TASK records, independent Review, and authority gates to high-risk, cross-session, real-environment, and delivery work. The Dashboard turns TASK, TASK_BOARD, Git, and Worktree facts into an interactive view of next actions, dependencies, parallel candidates, and decisions.

## What is new in v0.9.2

- **Chinese Codex Goal presets**: phrases such as “启动受控目标”, “启动自动落地目标”, and “我去休息，自动修好并交付” keep native Goal persistence while the Skill governs scope, verification, Review, UA, and delivery authority.
- **Historical task closeout**: repair six legacy Contracts; close 24 of 27 historical tasks with complete evidence, while keeping UA deferred and legally cancelling the three tasks that lack independent UA3 acceptance.
- **Secure development dependencies**: upgrade Vite, Vitest, ESLint, and TypeScript ESLint while keeping 89 browser tests and 91 frontend unit tests green with zero `npm audit` findings.
- **Compatible cross-project Dashboard**: retain the self-contained, read-only, multi-instance runtime with automatic port selection; installed use still requires no Node.js.
- **Preserved safety boundary**: loopback only, no write API, no project/Skill/Git mutations, no Worktree creation, and no authority to accept, commit, merge, release, or close tasks.

## How it works

```text
Project root                     Installed Skill
├─ docs/tasks/*.md              ├─ Workflow Contract Reader
├─ docs/TASK_BOARD.md           ├─ schemas and governance rules
└─ .git / Worktrees             └─ Dashboard runtime and frontend
          │                                  │
          └──────── read-only composition ───┘
                           │
                 http://127.0.0.1:<dynamic-port>
```

TASK is the detailed source of truth and TASK_BOARD is a projection. Insufficient evidence remains `unknown`; the Dashboard never guesses that tasks are parallel-safe or strictly serial.

## Quick start

### Start from an installed Skill

The supported baseline is Windows 11, Python 3.11+, Git 2.40+, and a modern browser. The project must be a Git repository with at least one `docs/tasks/*.md` TASK; keeping `docs/TASK_BOARD.md` is recommended. The installed runtime does not require Node.js.

```powershell
py -3 -B -X utf8 `
  "$env:USERPROFILE\.agents\skills\ai-dev-flow\scripts\dashboard.py" `
  --project-root "D:\projects\your-project"
```

The launcher discovers its Skill root and selects an available port. To be explicit:

```powershell
py -3 -B -X utf8 `
  "$env:USERPROFILE\.agents\skills\ai-dev-flow\scripts\dashboard.py" `
  --project-root "D:\projects\your-project" `
  --skill-root "$env:USERPROFILE\.agents\skills\ai-dev-flow" `
  --port 5084
```

Open only the printed `127.0.0.1` URL. `Ctrl+C` stops that instance only.

### Start from this repository

The source launcher additionally requires Node.js 22.13+ on the 22.x line, or Node.js 24+. Install the locked frontend dependencies before the first run in a clean checkout:

```powershell
Set-Location dashboard/frontend
npm ci
Set-Location ../..
```

```powershell
py -3 -B -X utf8 dashboard/integration/launcher.py `
  --project-root "D:\projects\your-project"
```

The source launcher remains compatible and also supports `--skill-root`, automatic ports, and isolated instances.

## Install or update the Skill

Copy `skills/ai-dev-flow/` into the harness Skill directory, for example:

```text
C:\Users\<user>\.agents\skills\ai-dev-flow
```

The complete Skill directory already contains the Dashboard runtime. Target projects need no copy, junction, or symlink.

## Governance routing

| Outcome | Use when | Default behavior |
|---|---|---|
| `DoNotUseSkill` | Low risk, one session, complete validation | No TASK or Reviewer |
| `Tracked` | Cross-session, broader scope, or durable evidence | TASK; read-only Review when risk triggers |
| `Controlled` | Class D, high-risk, real-environment, or delivery work | Full TASK; independent Review at enforcement points |
| `Blocked` | Input, authority, capability, or evidence is missing | Stop and report the minimum blocker |

The canonical policy lives only in `skills/ai-dev-flow/references/CORE.md` → `POLICY_JSON`.

## Versions and compatibility

- Skill: `0.9.2`
- Dashboard-supported Skill series: `0.9.x`
- Workflow Contract: `adf/v0.7.0`
- Scheduling: `ai-dev-flow/scheduling/v1`
- Supported environment: `Windows 11`, `Git 2.40+`, modern browser
- Python: `3.11+`

After a Skill update, running Dashboard instances keep their startup version and request a restart.

## Development validation

```powershell
py -3 -B -X utf8 -m unittest discover -s dashboard/backend/tests -p "test_*.py"
py -3 -B -X utf8 -m unittest discover -s dashboard/integration/tests -p "test_*.py"
py -3 -B -X utf8 -m unittest discover -s skills/ai-dev-flow/tests -p "test_*.py"
py -3 -B -X utf8 skills/ai-dev-flow/scripts/workflow_lint.py . --format human

cd dashboard/frontend
npm ci
npm run verify
```

See [Dashboard documentation](dashboard/README.md) and the [Skill guide](skills/ai-dev-flow/README.md) for details.

## License

MIT License. See [LICENSE](LICENSE).
