---
name: git-managed-skills
description: Manage first-party skills that live in a Git repository and are later synced into runtime environments. Use when creating, editing, reviewing, or shipping durable skill changes for repos like `unixfg/skills`, especially when operators might confuse the checked-in source with runtime-synced copies such as `/home/node/.openclaw/skills`.
---

# git-managed-skills

Use this skill when the task is about the durable source of truth for first-party skills, not about a specific deployment system.

## Scope

Handle work such as:
- editing first-party skills in their Git repository
- clarifying source of truth versus runtime-synced copies
- preparing commits and PRs for skill changes
- documenting the correct operator workflow for skill updates
- preventing footguns where a live runtime copy is edited instead of the repo

Do not use this skill for general skill authoring patterns unless the problem is specifically about repo-managed skill operations. For generic skill creation or audits, use `skill-creator`.

## Working rules

- Treat the Git repository checkout as the durable source of truth.
- Treat runtime skill directories as materialized state unless explicitly documented otherwise.
- If a deployment syncs skills into a runtime path like `/home/node/.openclaw/skills`, do not edit that path for durable changes.
- Prefer documenting the operator workflow close to the repo that owns the skills.
- When changing both behavior and guidance, update the guidance in the same change.

## Durable update procedure

1. Locate the actual skills repository checkout.
2. Edit the skill there, not in a runtime-synced directory.
3. Validate any examples, scripts, or references you changed.
4. Review the diff in the repo checkout.
5. Commit with a GitHub-friendly multiline message.
6. Push or prepare a PR from the repo checkout.
7. Let the downstream sync/deployment mechanism deliver the updated skill.

## Commit message rule

Do not embed literal escaped newlines like `\n` inside a single `git commit -m` argument when you want a formatted body.

Prefer either:

```bash
git commit \
  -m "Short subject" \
  -m "Summary
- first bullet
- second bullet

Why
- concise rationale"
```

or:

```bash
git commit -F- <<'EOF'
Short subject

Summary
- first bullet
- second bullet

Why
- concise rationale
EOF
```

Avoid:

```bash
git commit -m "Short subject\n\nSummary\n- bullet"
```

GitHub will often show the backslash escapes literally, which makes the commit body ugly and harder to read.

## Operator checklist

Before saying a skill change is done, confirm:
- the edited path is inside the repo checkout
- the change is not only in a runtime sync target
- the diff includes both the behavior change and any needed operator guidance
- the commit message body renders as intended when read as plain text

## References

Add repo-specific notes in `references/` when a particular skills repo has special publish, sync, or validation steps.
