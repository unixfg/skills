# Identify a philosophy book and resolve its file path in the sample Calibre library

Use the fixture library at `./sample-library/`.

Goal:
- identify which book in the fixture library is primarily about philosophy
- report the title and author
- resolve and return a concrete file path for the preferred readable format (EPUB if available)
- briefly explain which script(s) you used

Expected book:
- `The Problems of Philosophy` by Bertrand Russell

Constraints:
- use the local `ebook-library` scripts
- use metadata and/or content search to confirm the correct title
- use `resolve_book.py` to get the final path rather than inventing the path manually
