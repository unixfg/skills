---
name: tessl-release-manager
description: >
  Manage the lifecycle of Tessl skills and tiles stored in a git repository. Use when creating,
  refining, evaluating, versioning, tagging, publishing, releasing, deploying, updating, validating,
  or troubleshooting Tessl-managed skills across a repository. Covers when to bump versions, when to
  create release tags, when a new eval is warranted, how to verify publish state, and how to keep
  repository changes, Tessl registry state, and GitHub workflows aligned.
---

# Tessl Release Manager

Use this skill to manage Tessl skills as repository assets and registry releases.

## Scope

Cover repository-level skill management only:
- create or refine skills
- decide whether a change needs a version bump
- decide whether a Tessl release tag is needed
- decide whether a new eval or eval update is warranted
- run Tessl validation/review/publish checks
- verify registry state after publish
- inspect GitHub publish workflow behavior

Do not put skill-specific domain rules here. This is meta-process guidance.

## Core rules

- Treat the repository as source of truth for files; treat Tessl as source of truth for published versions.
- Keep skill instructions generic; put benchmark-specific traps and discovery requirements in `evals/`, not `SKILL.md`.
- If a change affects user-visible skill behavior, eval behavior, or published artifacts, assume a version bump is needed.
- If a version bump is made for a Tessl-managed skill, create the corresponding Tessl release tag.
- Do not assume a failed-looking publish is moderation-related until registry state and publish logs confirm it.
- Prefer Tessl CLI verification over guesswork.

## Local source map for this workspace

Distinguish the local sources before changing anything:

- `~/workspace/skills` is the messy local skills root. It contains OpenClaw-installed skills and other local skill folders.
- `~/workspace/skills/unixfg/skills` is the git repo for original Tessl skills created and published from this workspace.
- `~/workspace/tessl` is the intended home for Tessl-managed third-party skills tied to `~/workspace/tessl.json`; manage those with the Tessl CLI while logged in as `jobe-bot`.

Default behavior:
- when editing or releasing an original Tessl skill, work in `~/workspace/skills/unixfg/skills`
- when checking available OpenClaw skills, inspect `~/workspace/skills`
- when adding, removing, or updating third-party Tessl dependencies, use the Tessl CLI against the Tessl-managed area instead of hand-editing vendored files
- do not treat scratch repos or `/tmp` workdirs as the source of truth for installed or managed skills

## When to version bump

Bump the skill version in `tile.json` when any of the following changes after the last published version:

- `SKILL.md` content changes
- bundled scripts change behavior or interface
- references materially change agent guidance
- eval scenarios, rubrics, or capabilities change
- manifest fields that affect published behavior change
- workflow/config changes alter what gets published for that skill

Do not skip the bump just because a change is "internal" if it changes what Tessl will package or score.

Usually do not bump for:
- local investigation with no committed file changes
- comments or whitespace-only edits that truly do not affect behavior
- failed experiments reverted before release

Default bump policy:
- increment the patch version unless there is a strong reason for minor/major semantics

## When to tag

Create Tessl release tags whenever a bumped version should publish.

For a skill named `<skill-name>` at version `X.Y.Z`, create both:

```bash
git tag "vX.Y.Z"
git tag "tessl-<skill-name>-X.Y.Z"
```

Then push the branch and both tags.

Do not create a Tessl release tag without first updating `tile.json` to the matching version.
Do not forget to re-bump and re-tag if more changes land after a prior release.

## When a new eval is warranted

Add a new eval scenario when one of these is true:

- a recent failure mode was not caught by existing evals
- the skill gained a new capability or important workflow branch
- an agent can succeed by shortcutting around the intended method
- the skill needs a new honesty/no-fabrication check
- path resolution, discovery, validation, or error handling is important but currently untested
- a quality regression points to a missing benchmark dimension

Update an existing eval instead of adding a new one when:
- the capability is already covered but wording/rubric is weak
- the scenario intent is correct but the scoring emphasis is wrong
- the task should be made more precise without expanding scope

Keep eval concerns in eval files:
- `task.md` for the actual assignment
- `criteria.json` for scoring
- `capability.txt` for the short capability summary

## Release workflow

1. Identify which skill changed.
2. Inspect repo diff for user-visible, eval, or packaging changes.
3. Decide whether the skill needs:
   - no release,
   - version bump only for pending release prep,
   - version bump plus Tessl release tag.
4. Run the common Tessl checks:

```bash
env -u NODE_OPTIONS npx --yes tessl@latest skill lint ./tile.json
env -u NODE_OPTIONS npx --yes tessl@latest skill review --json .
env -u NODE_OPTIONS npx --yes tessl@latest skill publish --dry-run .
```

5. If publishable, bump `tile.json`.
6. Commit the change.
7. Create and push the release tags.
8. Verify publish state using the checks in [references/release-checks.md](references/release-checks.md).

Read [references/release-checks.md](references/release-checks.md) when you need the detailed GitHub verification commands or troubleshooting flow for moderation, auth, or quality-review complaints.

## Boundaries

- Do not add skill-specific benchmark details to a meta-process skill.
- Do not claim publish failure causes without CLI or workflow evidence.
- Do not change versions or create tags for unrelated skills.
- Do not add evals just to increase count; add them to cover a real gap.
