# Expand a match into a longer passage in a known book

Use the bundled sample library at `./sample-library`.

Goal:
- locate `Twenty Thousand Leagues under the Sea` by Jules Verne
- find a match for `Leyden` in that book
- then retrieve a longer passage around that same match
- return:
  - the `book_id`
  - the book title
  - a longer excerpt centered on the match
  - a brief note on how you found it

Constraints:
- prefer finding the correct `book_id` first
- use a two-step workflow: identify a hit, then expand it
- use the skill's excerpt-expansion workflow rather than returning only the initial search snippet
