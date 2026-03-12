# Subtle phrase match in noisy fixtures

Use the bundled sample library at `./sample-library`.

Goal:
- identify which book contains the phrase:
  - `all that is solid melts into air`
  - and also includes `bourgeois property`
- report the `book_id`, exact title, and author
- include one supporting snippet and briefly explain how you verified it from fixture search data

Constraints:
- avoid relying on directory names as the primary signal
- prefer content search on the fixture before resolving a final answer
- if your search returns no hit, report that clearly instead of guessing