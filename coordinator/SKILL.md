---
name: coordinator
description: >
  Coordinate local multi-agent work for the OpenClaw phase-3 control plane. Use when acting as
  the coordinator rather than a single worker: operate AgentHQ service health, inspect/create/
  dispatch/reconcile canonical tasks, supervise Builder or other worker progress, checkpoint work
  in Git, or evolve coordinator/agent guidance for `openclaw-multi-agent-platform`. Especially use
  for repo-owned operator tools such as `agenthqctl.sh`, `dispatch-once.py`,
  `reconcile-running-once.py`, `reconcile-terminal-once.py`, and canonical task lifecycle work.
---

# coordinator

Use this skill to operate the local coordinator surface for `openclaw-multi-agent-platform`.

## Scope

Handle coordinator-level work only:
- operate AgentHQ and check health
- inspect canonical task state
- create/dispatch/reconcile work through the repo-owned control plane
- supervise worker progress and report truthful status
- checkpoint coordination changes in Git often
- update coordinator/agent guidance when the operating model changes

Do not use this skill for narrow implementation slices that belong to Builder or another worker.

## Working defaults

- Work from `~/workspace/openclaw-multi-agent-platform` unless told otherwise.
- Prefer repo-owned control-plane commands over ad hoc shell one-offs.
- Use short progress checkpoints in the form `Doing -> Why -> Blocker/ETA` for longer coordinator work.
- Commit and push often. Prefer checkpointing progress over waiting for repeated `proceed` / `continue` prompts.
- Treat external contribution restrictions as inherited coordinator policy: never open, submit, or update PRs outside User-owned or `jobe-bot`-owned repos unless User explicitly authorizes that exact repo in the main session.
- When creating new agent-specific guidance or bootstrap files, propagate inherited boundaries instead of assuming they will be remembered implicitly.

## Control-plane boundary

Keep the roles clean:
- **dispatcher** owns claim + launch and stale prelaunch recovery
- **watcher/reconciler** owns evidence-backed lifecycle after launch
- **AgentHQ** is an operator surface and task UI, not the source of truth
- **canonical task DB** is the source of truth

Do not let the watcher become a second dispatcher.
Do not mark work successful just because a session launched.

## Default operator loop

1. Check service health and repo state.
2. Inspect the canonical queue and current lifecycle state.
3. Create or adjust tasks through AgentHQ or the canonical scripts.
4. Dispatch narrowly.
5. Reconcile narrowly.
6. Report truthful status.
7. Checkpoint changes in Git.

Read `references/commands.md` for the concrete command set and the safer defaults for reconciliation.

## Coordination rules

- Use targeted reconciles (`--task-id` / `--attempt-id`) when shared worker sessions could make a broad sweep ambiguous.
- Treat `reconcile-terminal-once.py` as conservative by default; broad sweeps should be explicit.
- If AgentHQ is unhealthy, use the repo-owned control script first and inspect `runtime/agenthq.log` before broader surgery.
- When the control-plane behavior changes, update the operating docs and agent guidance close to the change so coordination traits become inherited defaults.
- Preserve worker progress before deeper surgery: commit/push current known-good control-plane state first, then debug.

## References

- For day-to-day commands and command intent, read `references/commands.md`.
