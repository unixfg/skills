# Named-book content question

Use the bundled sample library at `./sample-library`.

A user asks:

`I just read Twenty Thousand Leagues under the Sea. What is the Nautilus?`

Goal:
- resolve the named title from Calibre metadata
- search inside that resolved book for the requested term
- answer from the returned local text evidence
- report the `book_id`, exact title, and author
- include one short supporting snippet from scoped content search

Constraints:
- do not answer from title metadata alone
- do not use online lookup or outside knowledge
- prefer `search_content.py --book-id` after resolving the title
- if the scoped content search returns no hit, report that clearly instead of guessing
