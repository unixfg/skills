# Find a book by author and title clues in the sample Calibre library

Use the local `ebook-library` skill resources and the fixture library at `./sample-library/`.

Goal:
- identify the book by Jules Verne in the fixture library
- report the `book_id`, exact title, and author
- briefly explain which script or command you used

Constraints:
- use the local scripts in `./scripts/`
- prefer metadata lookup over global full-text search
- do not guess; use the fixture library data

Expected outcome:
- the correct book is `Twenty Thousand Leagues under the Sea`
- the correct author is Jules Verne
