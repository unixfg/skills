# Famous-quote miss in fixture (no match should be reported)

Use the bundled sample library at `./sample-library`.

A user asks for the famous quote from a famous book:

`It was the best of times, it was the worst of times`

Goal:
- search fixture content for that exact quote
- report that no book in the fixture contains this quote
- include brief evidence of the lookup results proving no match

Constraints:
- use fixture lookup tools only
- explicitly report an empty result if that is what the search returns
- do not invent a book title, author, or excerpt
- if uncertain, report no match rather than guessing