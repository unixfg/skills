# Manual evals for ebook-library

These evals assume a tiny deterministic Calibre fixture library lives under:

`./sample-library/`

Expected fixture layout:

- `./sample-library/metadata.db`
- `./sample-library/full-text-search.db`
- adversarial placeholder book files mixed into the same fixture
- book files in normal Calibre per-author/per-book folders

Current fixture books (core):

1. `Twenty Thousand Leagues under the Sea` - Jules Verne
2. `The Problems of Philosophy` - Bertrand Russell
3. `The Communist Manifesto` - Karl Marx, Friedrich Engels

Known IDs in the current fixture:

- `1` -> `Twenty Thousand Leagues under the Sea`
- `4` -> `The Problems of Philosophy`
- `6` -> `The Communist Manifesto`

Why this fixture works well:

- mixed genres and authors for behavior coverage
- metadata IDs and searchable text are deterministic
- includes mixed-quality placeholder/variant files to test path-only shortcutting
- small enough for quick, repeatable scoring

Scenario coverage in this eval set (3 total):

1. content-driven identification without title-path clues
2. path-trap/global content match in a mixed fixture
3. honest no-result handling (must not hallucinate)

Each scenario assumes the agent can use the skill's bundled scripts and point them at the sample library when needed.

Before running evals, verify the fixture exists and contains working Calibre databases.