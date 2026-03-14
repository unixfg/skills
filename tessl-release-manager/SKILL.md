---
name: tessl-release-manager
description: >
  Manage the lifecycle of Tessl skills and tiles stored in a git repository. Use when creating,
  refining, evaluating, versioning, tagging, publishing, validating, or troubleshooting Tessl-managed
  skills across a repository. Covers when to bump versions, when to create release tags, when a new
  eval is warranted, how to verify publish state, and how to keep repository changes, Tessl registry
  state, and GitHub workflows aligned.
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
4. Run Tessl checks before publishing:

```bash
env -u NODE_OPTIONS npx --yes tessl@latest skill lint ./tile.json
env -u NODE_OPTIONS npx --yes tessl@latest skill review --json .
env -u NODE_OPTIONS npx --yes tessl@latest skill publish --dry-run .
```

5. If publishable, bump `tile.json`.
6. Commit the change.
7. Create and push the release tags.
8. Verify publish state using both GitHub and Tessl CLI.

## Publish verification

Check recent GitHub workflow runs:

```bash
gh run list --repo <owner/repo> --workflow "Publish <skill-name>" --limit 10
```

Check Tessl registry state:

```bash
env -u NODE_OPTIONS npx --yes tessl@latest search "<workspace>/<skill-name>"
env -u NODE_OPTIONS npx --yes tessl@latest skill publish --dry-run .
```

Interpretation:
- if dry-run says `<workspace>/<skill>@version already exists`, that version is already live
- if GitHub publish succeeded and registry search shows the new version, publish worked
- do not chase a suspected moderation failure without confirming those two facts first

## Troubleshooting heuristics

### Suspected moderation failure

Before concluding moderation failed, check:
- registry search for the target version
- GitHub publish run conclusion
- local `skill publish --dry-run`

If the version already exists in Tessl, there is no current publish block.

### Suspected auth failure in CI

Distinguish publish-action auth from Tessl CLI auth.
A GitHub action using `tesslio/publish@main` can succeed even when a separate Tessl CLI command in Actions fails.
Validate with logs before assuming the token is universally valid.

### Suspected quality regression

Use Tessl review output to target the complaint precisely.
If the complaint is about redundancy, reduce overlap instead of adding more guidance.
If the complaint is about actionability, inline the essential commands before adding more prose.

## Boundaries

- Do not add skill-specific benchmark details to a meta-process skill.
- Do not claim publish failure causes without CLI or workflow evidence.
- Do not change versions or create tags for unrelated skills.
- Do not add evals just to increase count; add them to cover a real gap.
