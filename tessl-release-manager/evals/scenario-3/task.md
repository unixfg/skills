# Decide whether a new eval scenario is warranted

A Tessl-managed skill recently failed in a way that current benchmarks did not catch.

Observed problem:
- the agent succeeded on existing evals by shortcutting around the intended method
- an important discovery/validation step is required in real use, but no current scenario checks it
- the skill itself did not gain a brand-new user-facing feature

Should you add a new eval scenario, update an existing one, or do nothing?

Return a short recommendation that explains:
- which option is best
- why that choice fits this failure mode
- what kind of benchmark gap it covers

Keep the answer generic; do not invent benchmark-specific fixture details.
