# Manual evals for ebook-library

These evals assume a tiny deterministic Calibre fixture library lives under:

`./sample-library/`

Expected fixture layout:

- `./sample-library/metadata.db`
- `./sample-library/full-text-search.db`
- book files in normal Calibre per-author/per-book folders

Current fixture books:

1. `Twenty Thousand Leagues under the Sea` - Jules Verne
2. `The Problems of Philosophy` - Bertrand Russell
3. `The Communist Manifesto` - Karl Marx, Friedrich Engels

Known IDs in the current fixture:

- `1` -> `Twenty Thousand Leagues under the Sea`
- `4` -> `The Problems of Philosophy`
- `6` -> `The Communist Manifesto`

Why this fixture works well:

- distinctive titles and authors for metadata lookup
- distinctive searchable terms such as `Leyden` and `bourgeois`
- both `EPUB` and `TXT` formats present for every book, which is useful for format-aware flows
- small enough that fallback behavior can be evaluated cleanly

Scenario coverage in this eval set:

1. metadata lookup from title/author clues
2. fallback from failed metadata search to browsing the library
3. scoped full-text search within a known book
4. global content search when the title is unknown
5. longer excerpt retrieval after an initial hit
6. path resolution for a preferred readable format
7. honest no-match handling without hallucination

Each scenario assumes the agent can use the skill's bundled resources and point them at the sample library when needed.

Before running evals, verify the fixture exists and contains working Calibre databases.
