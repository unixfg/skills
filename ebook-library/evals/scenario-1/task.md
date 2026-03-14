# Find the library, then find a content-only match

A local Calibre library is bundled with this skill.

A user asks for the book that discusses the relation between `sense-data` and `physical objects` and explicitly credits `G.E. Moore`.

Goal:
- locate the actual bundled Calibre library before searching
- identify the correct book from the library content
- report the `book_id`, exact title, and author
- include one short evidence snippet from the library lookup that supports the answer

Constraints:
- do not assume the library path without checking
- do not use title/author clues from directory names as the primary signal
- use library metadata or content lookup in the real bundled library data
- avoid guessing
- clearly state the lookup sequence you used, including how you found the library

Scoring should depend on the output being evidence-based and not based on file/folder names.
