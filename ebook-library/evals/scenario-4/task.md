# Resolve the actual book file from Calibre metadata

Use the bundled sample library at `./sample-library`.

A user asks:

`Find Bertrand Russell's The Problems of Philosophy in the library and give me the actual EPUB path.`

Goal:
- identify the correct Calibre record from library metadata
- report the `book_id`, exact title, and author
- return the resolved EPUB file path from the real library
- mention briefly how you verified the path came from Calibre metadata rather than guessing from folder names

Constraints:
- do not guess the path from author/title directory structure alone
- use the real library metadata first, then resolve the file path
- if EPUB is unavailable, report the available formats instead of inventing a path
- avoid guessing
