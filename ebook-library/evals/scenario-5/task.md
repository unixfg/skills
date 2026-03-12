# Expand a match into a longer passage in a known book

Use the fixture library at `./sample-library/` and the local scripts in `./scripts/`.

Goal:
- locate `Twenty Thousand Leagues under the Sea` by Jules Verne
- find a match for `Leyden` in that book
- then retrieve a longer passage around that same match
- return:
  - the `book_id`
  - the book title
  - a longer excerpt centered on the match
  - a brief note on which scripts you used

Constraints:
- prefer finding the correct `book_id` first
- use a two-step workflow: identify a hit, then expand it
- use `get_excerpt.py` for the longer passage rather than returning only the initial search snippet
