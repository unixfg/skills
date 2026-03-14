# Manual evals for ebook-library

These evals assume a tiny deterministic Calibre library lives under:

`./sample-library/`

Expected library layout:

- `./sample-library/metadata.db`
- `./sample-library/full-text-search.db`
- adversarial placeholder book files mixed into the same library
- book files in normal Calibre per-author/per-book folders

Current library books (core):

1. `Twenty Thousand Leagues under the Sea` - Jules Verne
2. `The Problems of Philosophy` - Bertrand Russell
3. `The Communist Manifesto` - Karl Marx, Friedrich Engels

Known IDs in the current library:

- `1` -> `Twenty Thousand Leagues under the Sea`
- `4` -> `The Problems of Philosophy`
- `6` -> `The Communist Manifesto`

Why this library works well:

- mixed genres and authors for behavior coverage
- metadata IDs and searchable text are deterministic
- includes mixed-quality placeholder/variant files to test path-only shortcutting
- small enough for quick, repeatable scoring

Scenario coverage in this eval set (4 total):

1. content-driven identification without title-path clues
2. path-trap/global content match in a mixed library
3. honest no-result handling (must not hallucinate)
4. metadata-first file path resolution without guessing from folder names

Each scenario assumes the agent can use the skill's bundled scripts and point them at the sample library when needed.

Before running evals, verify the library exists and contains working Calibre databases.