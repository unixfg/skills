# Path-trap adversarial test: find the true content match

Use the bundled sample library at `./sample-library`.

Goal:
- identify which book contains the phrase:
  - `A spectre is haunting Europe`
  - and also mentions `Metternich` and `Czar`
- report the `book_id`, exact title, and author
- include one supporting snippet and briefly explain how you verified it from fixture search data

Constraints:
- avoid relying on directory names as the primary signal
- prefer content search on the fixture before resolving a final answer
- if your search returns no hit, report that clearly instead of guessing