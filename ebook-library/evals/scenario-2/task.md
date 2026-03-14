# Subtle phrase match in noisy librarys

Use the bundled sample library at `./sample-library`.

Goal:
- identify which book contains both phrases:
  - `all that is solid melts into air`
  - `all that is holy is profaned`
- report the `book_id`, exact title, and author
- include one supporting snippet and briefly explain how you verified it from library search data

Constraints:
- avoid relying on directory names as the primary signal
- prefer content search on the library before resolving a final answer
- if your search returns no hit, report that clearly instead of guessing
