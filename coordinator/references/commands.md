# coordinator command reference

Use these commands as the default coordinator surface for `~/workspace/openclaw-multi-agent-platform`.

## Repo root

```bash
cd ~/workspace/openclaw-multi-agent-platform
```

## AgentHQ service control

Prefer `agenthqctl.sh` for day-to-day operations.

```bash
./scripts/agenthqctl.sh status
./scripts/agenthqctl.sh health
./scripts/agenthqctl.sh restart
./scripts/agenthqctl.sh stop
./scripts/agenthqctl.sh start
```

Use `setup-agenthq.sh` when you need the full setup/build/start path:

```bash
./scripts/setup-agenthq.sh sqlite
```

Key live files:
- PID: `runtime/agenthq.pid`
- Log: `runtime/agenthq.log`
- Canonical DB: `runtime/tasks.sqlite`

## Canonical task operations

Create a task through the UI when possible:
- AgentHQ -> `/tasks` -> `Add Task`

Use scripts when you need deterministic smoke tests or lower-level control:

```bash
python3 scripts/enqueue-task.py --task-kind builder --summary 'Example task' --source manual --requested-by User
python3 scripts/list-tasks.py --json
```

## Dispatch + reconciliation loop

Dispatch one task:

```bash
python3 scripts/dispatch-once.py --dispatcher-id local-operator
```

Promote claimed work to running when transcript evidence exists:

```bash
python3 scripts/reconcile-running-once.py
```

Reconcile running work to conservative terminal states:

```bash
python3 scripts/reconcile-terminal-once.py
```

### Terminal reconcile safety rules

`reconcile-terminal-once.py` is intentionally safe by default:
- no args -> reconcile **one** most-recent matching running attempt
- `--task-id <id>` -> reconcile one specific task
- `--attempt-id <id>` -> reconcile one specific attempt
- `--agent builder` -> narrow by assigned agent
- `--all` -> broad sweep only when explicitly intended

Use targeted reconcile whenever workers share one session, especially Builder.

Examples:

```bash
python3 scripts/reconcile-terminal-once.py --task-id task-ui-smoke-001
python3 scripts/reconcile-terminal-once.py --attempt-id attempt_b2166daf59a9
python3 scripts/reconcile-terminal-once.py --agent builder
```

## Quick inspection

Inspect counts by status:

```bash
sqlite3 runtime/tasks.sqlite "select status, count(*) from tasks group by status order by status;"
```

Inspect recent tasks:

```bash
sqlite3 runtime/tasks.sqlite ".mode column" ".headers on" \
  "select id, status, summary, target_agent, updated_at from tasks order by updated_at desc limit 10;"
```

Inspect recent task events:

```bash
sqlite3 runtime/tasks.sqlite ".mode column" ".headers on" \
  "select task_id, event_type, from_status, to_status, summary, created_at from task_events order by id desc limit 20;"
```

## Git checkpointing

Checkpoint before and after meaningful coordinator changes.

```bash
git status --short
git add <paths>
git commit -m "Describe the coordinator/control-plane checkpoint"
git push origin main
```

Prefer small, truthful checkpoints over large uncommitted coordinator drift.

## Coordination reminders

- Dispatcher owns claim + launch.
- Watcher/reconciler owns evidence-backed lifecycle after launch.
- AgentHQ is an operator UI, not the source of truth.
- The canonical DB is the source of truth.
- External contribution boundaries are inherited defaults for new coordinator/agent guidance.
