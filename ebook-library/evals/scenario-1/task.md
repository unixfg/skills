# Find a content-only match, not a filename match

Use the bundled sample library at `./sample-library`.

A user asks for the book that discusses the relation between `sense-data` and `physical objects` and explicitly credits `G.E. Moore`.

Goal:
- identify the correct book from the fixture library content
- report the `book_id`, exact title, and author
- include one short evidence snippet from the fixture lookup that supports the answer

Constraints:
- do not use title/author clues from directory names
- use library metadata or content lookup in the fixture data
- avoid guessing
- clearly state the lookup sequence you used

Scoring should depend on the output being evidence-based and not based on file/folder names.