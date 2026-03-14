# Release checks

Use this file for the detailed release validation and troubleshooting steps.

## Pre-publish checks

Run these from the skill directory before publishing:

```bash
env -u NODE_OPTIONS npx --yes tessl@latest skill lint ./tile.json
env -u NODE_OPTIONS npx --yes tessl@latest skill review --json .
env -u NODE_OPTIONS npx --yes tessl@latest skill publish --dry-run .
```

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
