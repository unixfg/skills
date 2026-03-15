# Decide the release actions for a changed Tessl skill

You are reviewing changes to a Tessl-managed skill in a git repository.

Observed repo changes since the last published version:
- `SKILL.md` wording changed in a user-visible way
- one reference file changed and now gives different agent guidance
- `evals/scenario-2/criteria.json` was updated to score a newly important behavior
- `tile.json` still shows version `1.4.2`
- no release tags have been created for the new work yet

What should happen next?

Return a short release plan that states:
- whether a version bump is needed
- which version bump is the default choice
- whether Tessl release tags are needed
- the exact tag names that should be created for skill `search-helper` after the bump to `1.4.3`
- which common Tessl validation commands should be run before publishing

Do not talk about unrelated skills.
