# Verify publish state before claiming moderation failure

A teammate says a Tessl publish probably failed moderation because they do not immediately see a new version in the UI.

You have these facts:
- `skill publish --dry-run .` says `jobe-skills/search-helper@1.4.3 already exists`
- a recent GitHub workflow run for `Publish search-helper` completed successfully
- Tessl registry search shows `jobe-skills/search-helper` version `1.4.3`

What is the most accurate diagnosis, and what should you do next?

Answer briefly. Focus on whether there is evidence of an active moderation problem.
